from __future__ import annotations

import time
from pathlib import Path

import requests
import yaml

from .config import LineCfg, env, read_json, write_json

USER_AGENT = {"User-Agent": "MuzeumWAutobusie/0.1 (Warsaw Open Data Hackathon 2026)"}
WIKI_API = "https://pl.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
MAX_DOC_CHARS = 1500
ID_PREFIX = {"wikipedia": "w", "osm": "o", "wikidata": "d"}


def load_manual(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [
        {
            "id": f["id"],
            "kind": "manual",
            "title": f.get("title") or raw.get("stop", ""),
            "text": f["text"],
            "url": f.get("url"),
            "status": f.get("status", "confirmed"),
        }
        for f in raw.get("facts", [])
    ]


def load_documents(line: LineCfg, stop_slug: str) -> list[dict]:
    docs = load_manual(line.sources_dir / "manual" / f"{stop_slug}.yaml")
    auto = line.sources_dir / "auto" / f"{stop_slug}.json"
    if auto.exists():
        docs += read_json(auto)
    return docs


def _get(url: str, params: dict) -> dict:
    resp = requests.get(url, params=params, headers=USER_AGENT, timeout=30)
    resp.raise_for_status()
    return resp.json()


def wikipedia_nearby(lat: float, lon: float, radius_m: int = 500, limit: int = 6) -> list[dict]:
    geo = _get(
        WIKI_API,
        {
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{lat}|{lon}",
            "gsradius": radius_m,
            "gslimit": limit,
            "format": "json",
        },
    )["query"]["geosearch"]
    if not geo:
        return []
    pages = _get(
        WIKI_API,
        {
            "action": "query",
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "exlimit": "max",
            "inprop": "url",
            "pageids": "|".join(str(p["pageid"]) for p in geo),
            "format": "json",
        },
    )["query"]["pages"]
    distance = {p["pageid"]: p["dist"] for p in geo}
    docs = []
    for page in sorted(pages.values(), key=lambda p: distance.get(p["pageid"], 1e9)):
        text = (page.get("extract") or "").strip()
        if text:
            docs.append(
                {
                    "kind": "wikipedia",
                    "title": page["title"],
                    "text": text[:MAX_DOC_CHARS],
                    "url": page.get("fullurl"),
                    "distance_m": distance.get(page["pageid"]),
                }
            )
    return docs


def osm_streets(lat: float, lon: float, radius_m: int = 300) -> list[dict]:
    query = f'[out:json][timeout:25];way(around:{radius_m},{lat},{lon})["highway"]["name"];out tags;'
    url = env("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    resp = requests.post(url, data={"data": query}, headers=USER_AGENT, timeout=60)
    resp.raise_for_status()
    streets: dict[str, dict] = {}
    for el in resp.json().get("elements", []):
        tags = el.get("tags", {})
        name = tags["name"]
        if name in streets:
            continue
        parts = [f"Ulica {name}."]
        if tags.get("old_name"):
            parts.append(f"Dawna nazwa: {tags['old_name']}.")
        if tags.get("name:etymology"):
            parts.append(f"Patron: {tags['name:etymology']}.")
        streets[name] = {
            "kind": "osm",
            "title": name,
            "text": " ".join(parts),
            "url": f"https://www.openstreetmap.org/way/{el['id']}",
            "etymology_qid": tags.get("name:etymology:wikidata"),
        }
    return list(streets.values())


def wikidata_labels(qids: list[str]) -> list[dict]:
    if not qids:
        return []
    entities = _get(
        WIKIDATA_API,
        {
            "action": "wbgetentities",
            "ids": "|".join(qids[:50]),
            "props": "labels|descriptions",
            "languages": "pl",
            "format": "json",
        },
    ).get("entities", {})
    docs = []
    for qid, ent in entities.items():
        label = ent.get("labels", {}).get("pl", {}).get("value")
        desc = ent.get("descriptions", {}).get("pl", {}).get("value")
        if label:
            docs.append(
                {
                    "kind": "wikidata",
                    "title": label,
                    "text": f"{label} — {desc}" if desc else label,
                    "url": f"https://www.wikidata.org/wiki/{qid}",
                }
            )
    return docs


def assign_ids(docs: list[dict]) -> list[dict]:
    counters: dict[str, int] = {}
    for d in docs:
        counters[d["kind"]] = counters.get(d["kind"], 0) + 1
        d["id"] = f"{ID_PREFIX[d['kind']]}{counters[d['kind']]}"
        d.pop("etymology_qid", None)
    return docs


def collect_auto(line: LineCfg, pause_s: float = 1.0) -> None:
    route = read_json(line.out_dir / "route.json")
    for stop in (s for s in route["stops"] if s.get("story")):
        docs: list[dict] = []
        for name, fetch in (
            ("Wikipedia", lambda s=stop: wikipedia_nearby(s["lat"], s["lon"])),
            ("OSM", lambda s=stop: osm_streets(s["lat"], s["lon"])),
        ):
            try:
                docs += fetch()
            except requests.RequestException as e:
                print(f"  {stop['name']}: {name} unavailable ({e})")
            time.sleep(pause_s)
        qids = sorted({d["etymology_qid"] for d in docs if d.get("etymology_qid")})
        try:
            docs += wikidata_labels(qids)
        except requests.RequestException as e:
            print(f"  {stop['name']}: Wikidata unavailable ({e})")

        out = write_json(line.sources_dir / "auto" / f"{stop['slug']}.json", assign_ids(docs))
        print(f"{stop['name']}: {len(docs)} documents → {out}")
