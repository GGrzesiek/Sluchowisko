from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .config import LineCfg, env, read_json, write_json
from .geo import norm_name, slugify

VEHICLE_POSITIONS_RESOURCE = "f2e5503e-927d-4ad3-9500-4ab9e55deb59"
STOP_COORDINATES_RESOURCE = "ab75c33d-3a26-4342-b36a-6e5fef0a3ac3"


class ZtmError(RuntimeError):
    pass


def _get(endpoint: str, params: dict[str, Any]) -> Any:
    base = env("ZTM_API_BASE", "https://api.um.warszawa.pl/api/action").rstrip("/")
    query = {**params, "apikey": env("ZTM_API_KEY", required=True)}
    resp = requests.get(f"{base}/{endpoint}/", params=query, timeout=30)
    resp.raise_for_status()
    result = resp.json().get("result")
    error_reported_as_text = isinstance(result, str)
    if error_reported_as_text:
        raise ZtmError(f"{endpoint}: {result}")
    return result


def flatten_values(rows: list[dict]) -> list[dict]:
    return [{v["key"]: v["value"] for v in row.get("values", [])} for row in rows]


def fetch_stops() -> list[dict]:
    return flatten_values(_get("dbstore_get", {"id": STOP_COORDINATES_RESOURCE}))


def fetch_routes() -> dict:
    return _get("public_transport_routes", {})


def fetch_positions(line: str, vehicle_type: int) -> list[dict]:
    return _get("busestrams_get", {"resource_id": VEHICLE_POSITIONS_RESOURCE, "type": vehicle_type, "line": line})


def build_stop_index(stops: list[dict]) -> dict[tuple[str, str], dict]:
    index: dict[tuple[str, str], dict] = {}
    for s in sorted(stops, key=lambda s: s.get("obowiazuje_od") or ""):
        try:
            key = (str(s["zespol"]), str(s["slupek"]).zfill(2))
            index[key] = {
                "name": s["nazwa_zespolu"],
                "zespol": key[0],
                "slupek": key[1],
                "lat": float(s["szer_geo"]),
                "lon": float(s["dlug_geo"]),
                "direction": s.get("kierunek"),
            }
        except (KeyError, TypeError, ValueError):
            continue
    return index


def variant_stops(variant: dict, stop_index: dict[tuple[str, str], dict]) -> list[dict]:
    out: list[dict] = []
    for _, item in sorted(variant.items(), key=lambda kv: int(kv[0])):
        key = (str(item.get("nr_zespolu")), str(item.get("nr_przystanku")).zfill(2))
        stop = stop_index.get(key)
        if stop is None or (out and out[-1]["zespol"] == stop["zespol"]):
            continue
        out.append(stop)
    return out


def match_score(names: list[str], wanted: list[str]) -> int:
    names_n = [norm_name(n) for n in names]
    pos, score = 0, 0
    for w in (norm_name(x) for x in wanted):
        try:
            pos = names_n.index(w, pos) + 1
            score += 1
        except ValueError:
            continue
    return score


def pick_variant(
    line_routes: dict, stop_index: dict[tuple[str, str], dict], wanted: list[str]
) -> tuple[str, list[dict]]:
    candidates = [(code, variant_stops(v, stop_index)) for code, v in line_routes.items()]
    if not candidates:
        raise ZtmError("No route variants for this line")
    return max(candidates, key=lambda c: match_score([s["name"] for s in c[1]], wanted))


def cut_segment(stops: list[dict], origin: str, destination: str) -> list[dict]:
    names = [norm_name(s["name"]) for s in stops]
    try:
        start = names.index(norm_name(origin))
        end = names.index(norm_name(destination), start)
    except ValueError as e:
        raise ZtmError(
            f"Segment {origin} → {destination} not found in the chosen route variant. "
            f"Variant stops: {', '.join(s['name'] for s in stops)}"
        ) from e
    return stops[start : end + 1]


def build_route(line: LineCfg, use_cache: bool = False) -> Path:
    stops_cache, routes_cache = line.raw_dir / "stops.json", line.raw_dir / "routes.json"
    if use_cache and stops_cache.exists() and routes_cache.exists():
        stops, routes = read_json(stops_cache), read_json(routes_cache)
    else:
        stops, routes = fetch_stops(), fetch_routes()
        write_json(stops_cache, stops)
        write_json(routes_cache, routes)

    line_routes = routes.get(line.line)
    if not line_routes:
        raise ZtmError(f"Line {line.line} is not in public_transport_routes")

    wanted = [s.name for s in line.stops]
    code, vstops = pick_variant(line_routes, build_stop_index(stops), wanted)
    segment = cut_segment(vstops, line.origin, line.destination)

    story_names = {norm_name(s.name) for s in line.stops if s.story}
    found = {norm_name(s["name"]) for s in segment}
    missing = [s.name for s in line.stops if norm_name(s.name) not in found]
    if missing:
        print(f"WARNING: stops from the config are not on the ZTM route: {', '.join(missing)}")

    route = {
        "line": line.line,
        "slug": line.slug,
        "variant": code,
        "origin": line.origin,
        "destination": line.destination,
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "stops": [
            {
                "order": i,
                "slug": slugify(s["name"]),
                **s,
                "story": norm_name(s["name"]) in story_names,
            }
            for i, s in enumerate(segment, start=1)
        ],
    }
    out = write_json(line.out_dir / "route.json", route)
    print(f"Line {line.line} ({code}): {len(segment)} stops → {out}")
    return out


def record(line: LineCfg, minutes: float, interval: float, out_path: Path | None = None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out_path = out_path or line.raw_dir / f"positions-{stamp}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    end = time.time() + minutes * 60
    snapshots = 0
    with out_path.open("a", encoding="utf-8") as f:
        while time.time() < end:
            try:
                vehicles = fetch_positions(line.line, line.vehicle_type)
                snap = {"fetched_at": datetime.now().isoformat(timespec="seconds"), "vehicles": vehicles}
                f.write(json.dumps(snap, ensure_ascii=False) + "\n")
                f.flush()
                snapshots += 1
                print(f"[{snap['fetched_at']}] vehicles: {len(vehicles)}")
            except (requests.RequestException, ZtmError) as e:
                print(f"Failed to fetch positions, retrying: {e}")
            time.sleep(interval)
    print(f"Saved {snapshots} snapshots → {out_path}")
    return out_path
