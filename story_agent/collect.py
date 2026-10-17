import json
import math
import os
import re
from pathlib import Path

from collector.schema import (
    MAX_NEARBY_ARTICLES,
    RADIUS_M,
    Area,
    CollectedStop,
    Fragment,
    Image,
    NearbyArticle,
    NearbyObject,
    Pole,
    Source,
    Stop,
    StreetName,
    normalize_text,
    save,
)
from story_agent.sources import (
    SourceDraft,
    commons_images,
    label,
    plwiki_title,
    warszawikia_article,
    warszawikia_search,
    wikidata_entities,
    wikidata_entity,
    wikipedia_article,
    wikipedia_geosearch,
)
from story_agent.stops import demo_stop
from story_agent.web import FetchError, download, fetch_json, fetch_text

BACKEND_URL = os.getenv("BACKEND_URL", "https://backend-6s5kkpohyq-lm.a.run.app").rstrip("/")
OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
NEAREST_ARTICLES = 12
MAX_ARTICLES = 25
MAX_PATRONS = 12
MAX_IMAGES = 15
MAX_OBJECTS = 80
KEPT_TAGS = (
    "highway",
    "historic",
    "memorial",
    "building",
    "amenity",
    "tourism",
    "leisure",
    "heritage",
    "start_date",
    "architect",
    "name:etymology",
    "old_name",
    "place",
    "subject",
)


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)))


def resolve_stop(group_id: str, lines: tuple[str, ...], name: str) -> Stop:
    poles: dict[str, tuple[float, float]] = {}
    for line in lines:
        detail, _ = fetch_json(f"{BACKEND_URL}/api/lines/{line}/")
        for route in detail.get("routes", []):
            data, _ = fetch_json(f"{BACKEND_URL}/api/lines/{line}/routes/{route['code']}/")
            for stop in data.get("stops", []):
                if str(stop.get("zespol")) == group_id and stop.get("lat") is not None:
                    poles[str(stop["slupek"])] = (stop["lat"], stop["lon"])
    if not poles:
        raise FetchError(f"no poles for stop group {group_id} in {BACKEND_URL}; pass --lat and --lon")
    lat = sum(p[0] for p in poles.values()) / len(poles)
    lon = sum(p[1] for p in poles.values()) / len(poles)
    return Stop(
        group_id=group_id,
        name=name,
        lat=round(lat, 6),
        lon=round(lon, 6),
        poles=[Pole(pole=k, lat=v[0], lon=v[1]) for k, v in sorted(poles.items())],
    )


def overpass(lat: float, lon: float) -> dict:
    around = f"around:{RADIUS_M},{lat},{lon}"
    query = f"""[out:json][timeout:90];
is_in({lat},{lon})->.inside;
area.inside[boundary=administrative][admin_level~"^(9|10)$"]->.admin;
area.inside[place~"^(quarter|neighbourhood|suburb)$"]->.places;
.admin out tags;
.places out tags;
(
  way({around})[highway][name];
  nwr({around})[place=square][name];
  nwr({around})[historic];
  nwr({around})[memorial];
  nwr({around})["name:etymology:wikidata"];
  nwr({around})[heritage];
  nwr({around})["ref:nid"];
  nwr({around})[building][wikidata];
  nwr({around})[amenity][wikidata];
  nwr({around})[tourism][wikidata];
  nwr({around})[leisure][wikidata];
);
out tags geom;"""
    body, _ = fetch_text(OVERPASS_URL, method="POST", data=query)
    return json.loads(body)


def object_kind(tags: dict) -> str:
    if tags.get("place") == "square":
        return "square"
    if "highway" in tags:
        return "street"
    if tags.get("historic") == "memorial" or "memorial" in tags:
        return "memorial"
    if tags.get("historic") == "monument":
        return "monument"
    if tags.get("amenity") == "place_of_worship" or tags.get("building") in ("church", "chapel", "cathedral"):
        return "church"
    if tags.get("leisure") in ("park", "garden"):
        return "park"
    if tags.get("amenity") in ("school", "university", "college", "hospital", "library", "theatre") or tags.get(
        "tourism"
    ) in ("museum", "gallery"):
        return "institution"
    if "building" in tags or tags.get("historic") in ("building", "manor", "castle", "industrial"):
        return "building"
    return "other"


def _qid(value: str | None) -> str | None:
    match = re.match(r"^(Q\d+)", value or "")
    return match.group(1) if match else None


def _element_distance(element: dict, lat: float, lon: float) -> int:
    points = []
    if "lat" in element:
        points.append((element["lat"], element["lon"]))
    points += [(p["lat"], p["lon"]) for p in element.get("geometry", []) or [] if p]
    for member in element.get("members", []):
        points += [(p["lat"], p["lon"]) for p in member.get("geometry", []) or [] if p]
    if not points:
        return RADIUS_M
    return min(distance_m(lat, lon, plat, plon) for plat, plon in points)


def build_objects(elements: list[dict], lat: float, lon: float) -> list[dict]:
    merged: dict[tuple[str, str], dict] = {}
    for element in elements:
        if element.get("type") == "area":
            continue
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        kind = object_kind(tags)
        key = (kind, name) if kind == "street" else (kind, f"{name}#{element['type']}/{element['id']}")
        dist = _element_distance(element, lat, lon)
        current = merged.get(key)
        candidate = {
            "name": name,
            "kind": kind,
            "distance_m": dist,
            "osm_id": f"{element['type']}/{element['id']}",
            "wikidata": _qid(tags.get("wikidata")),
            "wikipedia": tags.get("wikipedia") if re.match(r"^[a-z]{2,3}:.+$", tags.get("wikipedia", "")) else None,
            "named_after": _qid(tags.get("name:etymology:wikidata")),
            "old_names": [n.strip() for n in tags.get("old_name", "").split(";") if n.strip()],
            "heritage_ref": tags.get("ref:nid"),
            "tags": {k: v for k, v in sorted(tags.items()) if k in KEPT_TAGS},
        }
        if current is None:
            merged[key] = candidate
            continue
        for field in ("wikidata", "wikipedia", "named_after", "heritage_ref"):
            current[field] = current[field] or candidate[field]
        current["old_names"] = sorted(set(current["old_names"]) | set(candidate["old_names"]))
        if dist < current["distance_m"]:
            current["distance_m"] = dist
            current["osm_id"] = candidate["osm_id"]
    objects = sorted(merged.values(), key=lambda o: (o["distance_m"], o["name"]))
    return [o for o in objects if o["distance_m"] <= RADIUS_M][:MAX_OBJECTS]


def admin_names(elements: list[dict]) -> tuple[str, str | None, list[str]]:
    district, neighbourhood, articles = None, None, []
    for element in elements:
        if element.get("type") != "area":
            continue
        tags = element.get("tags", {})
        name = tags.get("name")
        if tags.get("admin_level") == "9" and not district:
            district = name
        elif (tags.get("admin_level") == "10" or "place" in tags) and not neighbourhood:
            neighbourhood = name
        else:
            continue
        if tags.get("wikipedia", "").startswith("pl:"):
            articles.append(tags["wikipedia"][3:])
    return district or "Warszawa", neighbourhood, articles


class Builder:
    def __init__(self, group_id: str):
        self.group_id = group_id
        self.sources: list[Source] = []
        self.fragments: list[Fragment] = []
        self.titles: set[str] = set()

    def add(self, draft: SourceDraft | None, object_id: str | None = None) -> list[str]:
        if draft is None or draft.url in self.titles:
            return []
        self.titles.add(draft.url)
        source_id = f"s{len(self.sources) + 1}"
        self.sources.append(
            Source(
                id=source_id,
                type=draft.type,
                title=draft.title,
                publisher=draft.publisher,
                url=draft.url,
                license=draft.license,
                license_url=draft.license_url,
                author=draft.author,
                author_death_year=draft.author_death_year,
                retrieved_at=draft.retrieved_at or "1970-01-01",
            )
        )
        ids = []
        for n, (section, text) in enumerate(draft.sections, start=1):
            fragment_id = f"{source_id}#{n}"
            self.fragments.append(
                Fragment(
                    id=fragment_id,
                    source_id=source_id,
                    section=section,
                    text=normalize_text(text),
                    object_id=object_id,
                    derived=False,
                )
            )
            ids.append(fragment_id)
        offset = len(draft.sections)
        for n, (text, template, values) in enumerate(draft.derived, start=offset + 1):
            fragment_id = f"{source_id}#{n}"
            self.fragments.append(
                Fragment(
                    id=fragment_id,
                    source_id=source_id,
                    section=None,
                    text=normalize_text(text),
                    object_id=object_id,
                    derived=True,
                    template=template,
                    values=values,
                )
            )
            ids.append(fragment_id)
        return ids


def _safe(call, *args):
    try:
        return call(*args)
    except FetchError as error:
        print(f"skipped: {error}")
        return None


def collect_basic(group_id: str, lat: float | None = None, lon: float | None = None, out: Path = Path("out")) -> Path:
    demo = demo_stop(group_id)
    if lat is not None and lon is not None:
        stop = Stop(group_id=group_id, name=demo.name, lat=lat, lon=lon, poles=[Pole(pole="00", lat=lat, lon=lon)])
    else:
        stop = resolve_stop(group_id, demo.lines, demo.name)
    data = overpass(stop.lat, stop.lon)
    elements = data.get("elements", [])
    district, neighbourhood, area_articles = admin_names(elements)
    raw_objects = build_objects(elements, stop.lat, stop.lon)
    objects_with_ids = [{"id": f"o{n}", **o} for n, o in enumerate(raw_objects, start=1)]

    qids = sorted({o["named_after"] for o in objects_with_ids if o["named_after"]})
    qids += sorted({o["wikidata"] for o in objects_with_ids if o["wikidata"]} - set(qids))
    entities, wd_retrieved = wikidata_entities(qids) if qids else ({}, "")
    for o in objects_with_ids:
        patron = entities.get(o["named_after"] or "")
        o["named_after_label"] = None
        if patron:
            o["named_after_label"] = label(patron)
    objects = [NearbyObject(**o) for o in objects_with_ids]

    builder = Builder(group_id)
    area_fragments: list[str] = []
    for title in area_articles:
        area_fragments += builder.add(_safe(wikipedia_article, title))

    geo = _safe(wikipedia_geosearch, stop.lat, stop.lon, RADIUS_M, MAX_NEARBY_ARTICLES) or []
    fetched_titles: set[str] = set()
    for title, _dist in geo[:NEAREST_ARTICLES]:
        if builder.add(_safe(wikipedia_article, title)):
            fetched_titles.add(title)
    for o in objects:
        if len(builder.sources) >= MAX_ARTICLES:
            break
        if o.wikipedia and o.wikipedia.startswith("pl:"):
            ids = builder.add(_safe(wikipedia_article, o.wikipedia[3:]), o.id)
            if ids:
                fetched_titles.add(o.wikipedia[3:])
    patrons = [o for o in objects if o.named_after and o.named_after in entities][:MAX_PATRONS]
    for o in patrons:
        entity = entities[o.named_after]
        builder.add(wikidata_entity(o.named_after, entities, wd_retrieved), o.id)
        title = plwiki_title(entity)
        if title and len(builder.sources) < MAX_ARTICLES + MAX_PATRONS:
            builder.add(_safe(wikipedia_article, title), o.id)
    for title in (_safe(warszawikia_search, f"{demo.name}") or [])[:2]:
        builder.add(_safe(warszawikia_article, title))

    nearby = [
        NearbyArticle(title=title, distance_m=min(dist, RADIUS_M), fetched=title in fetched_titles)
        for title, dist in geo
        if dist <= RADIUS_M
    ][:MAX_NEARBY_ARTICLES]
    streets = {}
    for o in objects:
        if o.kind == "street" and o.name not in streets:
            streets[o.name] = StreetName(
                name=o.name, object_id=o.id, named_after=o.named_after, distance_m=o.distance_m
            )

    images = []
    for candidate in _safe(commons_images, stop.lat, stop.lon, RADIUS_M) or []:
        if len(images) >= MAX_IMAGES:
            break
        image_id = f"i{len(images) + 1}"
        file = f"out/images/{group_id}/{image_id}.jpg"
        if not candidate["url"] or not candidate["thumb"]:
            continue
        if _safe(download, candidate["thumb"], out / "images" / group_id / f"{image_id}.jpg") is None:
            continue
        images.append(
            Image(
                id=image_id,
                kind="photo",
                file=file,
                url=candidate["url"],
                caption=candidate["caption"][:500],
                author=candidate["author"],
                year=candidate["year"],
                license=candidate["license"],
                license_url=candidate["license_url"] if (candidate["license_url"] or "").startswith("http") else None,
                non_commercial=bool(re.search(r"\bNC\b", candidate["license"].upper())),
                source_id=None,
                object_id=None,
            )
        )

    collected = CollectedStop(
        stop=stop,
        area=Area(
            district=district,
            neighbourhood=neighbourhood,
            fragment_ids=area_fragments,
            street_names=sorted(streets.values(), key=lambda s: (s.distance_m, s.name)),
            nearby_articles=nearby,
        ),
        objects=objects,
        sources=builder.sources,
        fragments=builder.fragments,
        images=images,
    )
    return save(collected, out / "collected")


def collect(group_id: str, lat: float | None = None, lon: float | None = None) -> Path:
    if lat is None:
        from django.db import DatabaseError

        from collector.collect import collect as team_collect
        from collector.stops import UnknownStopGroup

        try:
            return team_collect(group_id)
        except (UnknownStopGroup, DatabaseError) as error:
            print(f"{error}\nUsing the basic collector from story_agent instead.")
    return collect_basic(group_id, lat, lon)
