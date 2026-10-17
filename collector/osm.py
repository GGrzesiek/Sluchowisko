import re
from dataclasses import dataclass

from collector import cache
from collector.geo import distance_m, distance_to_line_m, inside_ring
from collector.schema import RADIUS_M, NearbyObject

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
NEIGHBOURHOOD_RADIUS_M = 1000
DISTRICT_LEVELS = ("9", "8", "7")
NEIGHBOURHOOD_LEVEL = "10"
NEIGHBOURHOOD_PLACES = ("neighbourhood", "quarter")
OBJECT_FILTERS = (
    '["historic"]',
    '["memorial"]',
    '["name:etymology:wikidata"]',
    '["heritage"]',
    '["ref:nid"]',
    '["building"]["wikidata"]',
    '["amenity"]["wikidata"]',
    '["tourism"]["wikidata"]',
    '["leisure"]["wikidata"]',
    '["landuse"]["wikidata"]',
)
IGNORED_HIGHWAYS = {"platform", "bus_stop", "proposed", "construction", "abandoned", "razed", "elevator", "corridor"}
KEPT_TAG = re.compile(
    r"^(name|old_name|alt_name|official_name|short_name|loc_name)(:.+)?$"
    r"|^(highway|place|wikidata|wikipedia|start_date|ref:nid|heritage.*|historic.*|memorial.*|.*etymology.*)$"
    r"|^(building|amenity|tourism|leisure|landuse|religion|denomination|architect|artist_name|subject.*)$"
)
INSTITUTIONS = {
    "amenity": {"school", "college", "university", "library", "hospital", "theatre", "cinema", "arts_centre"},
    "tourism": {"museum", "gallery"},
}
QID = re.compile(r"^Q\d+$")
WIKIPEDIA = re.compile(r"^[a-z]{2,3}:.+$")


class OverpassError(RuntimeError):
    pass


@dataclass(frozen=True)
class Area:
    district: str
    district_tags: dict[str, str]
    neighbourhood: str | None
    neighbourhood_tags: dict[str, str]
    objects: list[NearbyObject]
    street_ids: set[str]


def stop_query(lat: float, lon: float) -> str:
    point = f"{lat:.6f},{lon:.6f}"
    places = "|".join(NEIGHBOURHOOD_PLACES)
    objects = "".join(f"nwr(around:{RADIUS_M},{point}){tags};" for tags in OBJECT_FILTERS)
    return (
        "[out:json][timeout:120];"
        f"is_in({point})->.a;"
        'area.a["boundary"="administrative"];out tags;'
        f'area.a["place"~"^({places})$"];out tags;'
        f'nwr(around:{NEIGHBOURHOOD_RADIUS_M},{point})["place"~"^({places})$"];out tags center;'
        f'way(around:{RADIUS_M},{point})["highway"]["name"];out tags geom;'
        f"({objects});out tags geom;"
    )


def overpass(query: str) -> dict:
    for url in OVERPASS_URLS:
        stored = cache.lookup("POST", url, form={"data": query})
        if stored:
            return stored.json()
    errors = []
    for url in OVERPASS_URLS:
        try:
            return cache.fetch("POST", url, form={"data": query}).json()
        except cache.FetchError as error:
            errors.append(str(error))
    raise OverpassError("All Overpass servers failed:\n" + "\n".join(errors))


def load_area(lat: float, lon: float) -> Area:
    elements = overpass(stop_query(lat, lon))["elements"]
    boundaries = [e["tags"] for e in elements if e["type"] == "area" and "boundary" in e["tags"]]
    containing = [e["tags"] for e in elements if e["type"] == "area" and "place" in e["tags"]]
    found = _unique([e for e in elements if e["type"] != "area" and e.get("tags", {}).get("name")])
    places = [e for e in found if e["tags"].get("place") in NEIGHBOURHOOD_PLACES]
    ways = [e for e in found if e["type"] == "way" and "highway" in e["tags"] and "geometry" in e]
    others = [e for e in found if e not in places and "highway" not in e["tags"]]

    district_tags = _district(boundaries)
    neighbourhood_tags = _neighbourhood(boundaries, containing, places, lat, lon)
    streets = _streets(ways, lat, lon)
    candidates = [(street, True) for street in streets] + [(_object(e, lat, lon), False) for e in others]
    candidates.sort(key=lambda candidate: (candidate[0].distance_m, candidate[0].name, candidate[0].osm_id))
    objects = [candidate.model_copy(update={"id": f"o{n}"}) for n, (candidate, _) in enumerate(candidates, start=1)]
    street_ids = {o.id for o, (_, is_street) in zip(objects, candidates, strict=True) if is_street}
    return Area(
        district=district_tags["name"],
        district_tags=district_tags,
        neighbourhood=neighbourhood_tags.get("name"),
        neighbourhood_tags=neighbourhood_tags,
        objects=objects,
        street_ids=street_ids,
    )


def _unique(elements: list[dict]) -> list[dict]:
    seen: dict[tuple[str, int], dict] = {}
    for element in elements:
        seen.setdefault((element["type"], element["id"]), element)
    return list(seen.values())


def _district(boundaries: list[dict]) -> dict[str, str]:
    for level in DISTRICT_LEVELS:
        if found := _first_named(boundaries, "admin_level", level):
            return found
    raise OverpassError("The point is not inside any OSM administrative boundary of level 7–9")


def _neighbourhood(
    boundaries: list[dict], containing: list[dict], nearby: list[dict], lat: float, lon: float
) -> dict[str, str]:
    if found := _first_named(boundaries, "admin_level", NEIGHBOURHOOD_LEVEL):
        return found
    for place in NEIGHBOURHOOD_PLACES:
        if found := _first_named(containing, "place", place):
            return found
    candidates = []
    for element in nearby:
        point = element.get("center") or element
        if "lat" in point:
            candidates.append((distance_m(lat, lon, point["lat"], point["lon"]), element["tags"]["name"], element))
    if not candidates:
        return {}
    return min(candidates, key=lambda c: (c[0], c[1], c[2]["id"]))[2]["tags"]


def _first_named(tag_sets: list[dict], key: str, value: str) -> dict[str, str] | None:
    named = sorted((tags for tags in tag_sets if tags.get(key) == value and tags.get("name")), key=lambda t: t["name"])
    return named[0] if named else None


def _streets(ways: list[dict], lat: float, lon: float) -> list[NearbyObject]:
    by_name: dict[str, list[tuple[int, dict]]] = {}
    for way in ways:
        if way["tags"]["highway"] in IGNORED_HIGHWAYS:
            continue
        by_name.setdefault(way["tags"]["name"], []).append((_distance(way, lat, lon), way))

    streets = []
    for name, segments in by_name.items():
        segments.sort(key=lambda segment: (segment[0], segment[1]["id"]))
        distance, nearest = segments[0]
        tags = _merge_tags([way["tags"] for _, way in segments])
        kind = "square" if tags.get("place") == "square" else "street"
        streets.append(_nearby_object(name, kind, distance, f"way/{nearest['id']}", tags))
    return streets


def _object(element: dict, lat: float, lon: float) -> NearbyObject:
    tags = _merge_tags([element["tags"]])
    osm_id = f"{element['type']}/{element['id']}"
    return _nearby_object(tags["name"], _kind(tags), _distance(element, lat, lon), osm_id, tags)


def _nearby_object(name: str, kind: str, distance: int, osm_id: str, tags: dict[str, str]) -> NearbyObject:
    return NearbyObject(
        id="o0",
        name=name,
        kind=kind,
        distance_m=distance,
        osm_id=osm_id,
        wikidata=_single(tags.get("wikidata"), QID),
        wikipedia=_single(tags.get("wikipedia"), WIKIPEDIA),
        named_after=_single(tags.get("name:etymology:wikidata"), QID),
        named_after_label=None,
        old_names=_split(tags.get("old_name")),
        heritage_ref=tags.get("ref:nid"),
        tags=tags,
    )


def _kind(tags: dict[str, str]) -> str:
    if tags.get("historic") in {"memorial", "wayside_shrine", "wayside_cross"} or "memorial" in tags:
        return "memorial"
    if tags.get("historic") == "monument":
        return "monument"
    if tags.get("amenity") == "place_of_worship" or tags.get("building") in {"church", "chapel", "cathedral"}:
        return "church"
    if tags.get("leisure") in {"park", "garden"}:
        return "park"
    if tags.get("place") == "square":
        return "square"
    if any(tags.get(key) in values for key, values in INSTITUTIONS.items()):
        return "institution"
    if "building" in tags:
        return "building"
    return "other"


def _distance(element: dict, lat: float, lon: float) -> int:
    if element["type"] == "node":
        return distance_m(lat, lon, element["lat"], element["lon"])
    lines = [element["geometry"]] if element["type"] == "way" else _member_lines(element)
    rings = [[(p["lat"], p["lon"]) for p in line if p] for line in lines]
    rings = [ring for ring in rings if ring]
    if any(inside_ring(lat, lon, ring) for ring in rings):
        return 0
    return min((distance_to_line_m(lat, lon, ring) for ring in rings), default=RADIUS_M)


def _member_lines(relation: dict) -> list[list[dict]]:
    lines = []
    for member in relation.get("members", []):
        if member.get("geometry"):
            lines.append(member["geometry"])
        elif "lat" in member:
            lines.append([{"lat": member["lat"], "lon": member["lon"]}])
    return lines


def _merge_tags(tag_sets: list[dict[str, str]]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for tags in tag_sets:
        for key, value in tags.items():
            if KEPT_TAG.match(key):
                merged.setdefault(key, value)
    old_names = sorted({name for tags in tag_sets for name in _split(tags.get("old_name"))})
    if old_names:
        merged["old_name"] = ";".join(old_names)
    return dict(sorted(merged.items()))


def _split(value: str | None) -> list[str]:
    return [part.strip() for part in (value or "").split(";") if part.strip()]


def _single(value: str | None, pattern: re.Pattern) -> str | None:
    parts = _split(value)
    return parts[0] if len(parts) == 1 and pattern.match(parts[0]) else None
