"""Compact, LLM-friendly description of a line: what Kuba feeds the model to generate places + facts.

Design choices (what makes it "nice" for an LLM):
- one direction of the main route only (both directions pass the same places)
- one entry per stop (the API has a post per direction, e.g. "Centrum 01" and "Centrum 02")
- no internal ids, coordinates rounded to 5 decimals (~1 m) to save tokens
- km from the start + segments with midpoints, so the model can place things *between* stops
- the exact output format we can import (`output_format`), plus rules against made-up places
"""
import math

from django.conf import settings

from .geo import haversine_m
from .models import Line, Route

WARSAW_BBOX = {"min_lat": 52.09, "max_lat": 52.37, "min_lon": 20.85, "max_lon": 21.28}

OUTPUT_FORMAT = [{
    "name": "Name of the place (building, monument, square, street, park...)",
    "lat": 52.0,
    "lon": 21.0,
    "category": "history | architecture | street-name | nature | culture | curiosity",
    "near_stop": "Name of the nearest stop from `stops`",
    "facts": [{
        "title": "Short catchy title (max 60 chars)",
        "text": "1-3 sentences, max 400 chars, surprising for someone who lives in Warsaw",
        "language": "pl",
        "source_url": "https://... page the fact comes from",
        "priority": "0-5, higher = more surprising",
    }],
}]

RULES = [
    "Only include real places that exist today or whose location is documented.",
    "Every place must be within `corridor_m` metres of the route (use the stops and segments).",
    "Every fact needs a real source_url (Wikipedia, zabytki registry, um.warszawa.pl...). If unsure, skip the fact.",
    "Prefer lesser-known facts over things every Warsaw resident knows.",
    "Return only a JSON array in `output_format`, no extra text.",
]


def pick_route(line: Line, code: str | None = None) -> Route | None:
    routes = line.routes.all()
    if code:
        return routes.filter(code=code).first()
    main = [r for r in routes if r.is_main] or list(routes)
    return max(main, key=lambda r: r.stop_count, default=None)


def build_line_context(line: Line, route_code: str | None = None, include_task: bool = True,
                       corridor_m: int | None = None) -> dict | None:
    route = pick_route(line, route_code)
    if route is None:
        return None
    corridor_m = corridor_m or settings.FACT_RADIUS_M

    # unique stops in route order, skipping consecutive posts of the same stop group
    stops, last_zespol, km = [], None, 0.0
    for rs in route.stops.select_related("stop").order_by("order"):
        if not rs.stop or rs.zespol == last_zespol:
            continue
        if stops:
            km += haversine_m(stops[-1]["lat"], stops[-1]["lon"], rs.stop.lat, rs.stop.lon) / 1000
        stops.append({"seq": len(stops) + 1, "name": rs.stop.name,
                      "lat": round(rs.stop.lat, 5), "lon": round(rs.stop.lon, 5), "km": round(km, 2)})
        last_zespol = rs.zespol

    segments = [{
        "from": a["name"], "to": b["name"],
        "length_m": round((b["km"] - a["km"]) * 1000),
        "midpoint": {"lat": round((a["lat"] + b["lat"]) / 2, 5), "lon": round((a["lon"] + b["lon"]) / 2, 5)},
    } for a, b in zip(stops, stops[1:])]

    ctx = {
        "city": "Warszawa",
        "line": line.number,
        "kind": line.kind,
        "route": {"code": route.code, "from": route.first_stop_name, "to": route.last_stop_name,
                  "length_km": round(km, 1), "stop_count": len(stops)},
        "corridor_m": corridor_m,
        "bbox": _bbox(stops, corridor_m),
        "stops": stops,
        "segments": segments,
    }
    if include_task:
        ctx["task"] = (f"Find interesting places along Warsaw {line.kind} line {line.number} "
                       f"({route.first_stop_name} → {route.last_stop_name}) and write short facts about them.")
        ctx["rules"] = RULES
        ctx["output_format"] = OUTPUT_FORMAT
    return ctx


def _bbox(stops, margin_m):
    if not stops:
        return None
    lat = [s["lat"] for s in stops]
    lon = [s["lon"] for s in stops]
    dlat = margin_m / 111_320
    dlon = margin_m / (111_320 * math.cos(math.radians(sum(lat) / len(lat))))
    return {"min_lat": round(min(lat) - dlat, 5), "max_lat": round(max(lat) + dlat, 5),
            "min_lon": round(min(lon) - dlon, 5), "max_lon": round(max(lon) + dlon, 5)}


def distance_to_route_m(lat: float, lon: float, stops: list[dict]) -> float:
    """Shortest distance from a point to the polyline through the stops (flat-earth approx, fine at city scale)."""
    if not stops:
        return float("inf")
    kx = 111_320 * math.cos(math.radians(lat))
    ky = 111_320

    def xy(p_lat, p_lon):
        return (p_lon - lon) * kx, (p_lat - lat) * ky  # point of interest = origin

    pts = [xy(s["lat"], s["lon"]) for s in stops]
    if len(pts) == 1:
        return math.hypot(*pts[0])
    best = float("inf")
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        dx, dy = x2 - x1, y2 - y1
        seg2 = dx * dx + dy * dy
        t = 0 if seg2 == 0 else max(0, min(1, -(x1 * dx + y1 * dy) / seg2))
        best = min(best, math.hypot(x1 + t * dx, y1 + t * dy))
    return best
