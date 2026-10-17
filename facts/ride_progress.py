"""Where is the vehicle on its route? Builds the RideInfo contract for the frontend:

{ "vehicle": "1234", "destination": "Dworzec Wileński",
  "stops": [ {"name": "...", "state": "passed" | "current" | "next" | "upcoming",
              "etaMinutes": 4, "hasStory": true}, ... ] }

How:
1. pick the route (direction) of the vehicle's line whose path is closest to the vehicle
   and points the same way as the vehicle's heading;
2. project the vehicle onto that path -> distance travelled along the route;
3. stops behind = passed, the stop at/just behind = current, the next 3 = next, the rest = upcoming;
4. ETA = remaining distance along the route / average speed (instant speed is useless at a red light);
5. hasStory = the stop group has a verified story.
"""

import math
from bisect import bisect_right

from django.core.cache import cache
from django.utils import timezone

from stories.models import Story
from transit.geo import angle_diff, bearing_deg, haversine_m
from transit.models import Route, Vehicle

NEXT_COUNT = 3  # how many stops are "next" (the rest are "upcoming")
AT_STOP_M = 100  # this close to the following stop = we are "at" it already
AVG_SPEED_MPS = 5.0  # ~18 km/h: typical Warsaw tram/bus average including stops
WRONG_WAY_PENALTY_M = 1000  # route pointing against the vehicle's heading
OTHER_VARIANT_PENALTY_M = 50
MAIN_ROUTE_MAX_DISTANCE_M = 150
ROUTE_MEMORY_SECONDS = 600
MAX_EXTRAPOLATE_S = 30
MAX_SPEED_MPS = 20.0


class NoRouteError(Exception):
    pass


def _xy(lat, lon, lat0, lon0):
    """Flat metres around (lat0, lon0); accurate enough at city scale."""
    return (lon - lon0) * 111_320 * math.cos(math.radians(lat0)), (lat - lat0) * 111_320


def _project(lat, lon, pts):
    """Closest point of the polyline `pts` [(lat, lon)] to (lat, lon).
    Returns (distance_to_path_m, segment_index, t in 0..1)."""
    best = (float("inf"), 0, 0.0)
    for i, (a, b) in enumerate(zip(pts, pts[1:], strict=False)):
        ax, ay = _xy(a[0], a[1], lat, lon)
        bx, by = _xy(b[0], b[1], lat, lon)
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / seg2))
        d = math.hypot(ax + t * dx, ay + t * dy)
        if d < best[0]:
            best = (d, i, t)
    return best


def _route_points(route):
    stops = [rs.stop for rs in route.stops.select_related("stop").order_by("order") if rs.stop]
    return stops, [(s.lat, s.lon) for s in stops]


def _fit(v: Vehicle, lat: float, lon: float, route):
    stops, pts = _route_points(route)
    if len(pts) < 2:
        return None
    dist, i, t = _project(lat, lon, pts)
    wrong_way = v.heading is not None and angle_diff(bearing_deg(*pts[i], *pts[i + 1]), v.heading) > 90
    return dist, wrong_way, route, stops, pts, i, t


def _route_memory_key(v: Vehicle) -> str:
    return f"ride:route:{v.number}"


def pick_route(v: Vehicle, lat: float, lon: float):
    fits = [f for f in (_fit(v, lat, lon, r) for r in Route.objects.filter(line_id=v.line)) if f]
    if not fits:
        raise NoRouteError(f"No route built for line {v.line}. Run: python manage.py build_routes --line {v.line}")
    key = _route_memory_key(v)
    remembered = cache.get(key)
    for dist, wrong_way, route, *rest in fits:
        if route.pk == remembered and dist <= MAIN_ROUTE_MAX_DISTANCE_M and not wrong_way:
            cache.set(key, route.pk, ROUTE_MEMORY_SECONDS)
            return (route, *rest)
    main = [f for f in fits if f[2].is_main and f[0] <= MAIN_ROUTE_MAX_DISTANCE_M]
    best = min(
        main or fits,
        key=lambda f: f[0] + (WRONG_WAY_PENALTY_M if f[1] else 0) + (0 if f[2].is_main else OTHER_VARIANT_PENALTY_M),
    )
    cache.set(key, best[2].pk, ROUTE_MEMORY_SECONDS)
    return best[2:]


def _travelled_since_reading(v: Vehicle) -> float:
    if not v.speed_mps:
        return 0.0
    age = min(max(0.0, (timezone.now() - v.reported_at).total_seconds()), MAX_EXTRAPOLATE_S)
    return min(v.speed_mps, MAX_SPEED_MPS) * age


def _stops_with_stories(stops) -> set[int]:
    groups = set(
        Story.objects.filter(status=Story.Status.VERIFIED, group_id__in={s.zespol for s in stops}).values_list(
            "group_id", flat=True
        )
    )
    return {s.pk for s in stops if s.zespol in groups}


def _group_runs(stops) -> list[tuple[int, int]]:
    runs = []
    for idx, s in enumerate(stops):
        if runs and stops[runs[-1][0]].zespol == s.zespol:
            runs[-1] = (runs[-1][0], idx)
        else:
            runs.append((idx, idx))
    return runs


def build_ride_info(v: Vehicle) -> dict:
    route, stops, pts, seg, t = pick_route(v, v.lat, v.lon)

    # cumulative distance of each stop along the route, and of the vehicle
    cum = [0.0]
    for a, b in zip(pts, pts[1:], strict=False):
        cum.append(cum[-1] + haversine_m(*a, *b))
    here = min(cum[-1], cum[seg] + t * (cum[seg + 1] - cum[seg]) + _travelled_since_reading(v))
    seg = min(bisect_right(cum, here) - 1, len(cum) - 2)

    # current = the stop we are at; otherwise the last one we passed
    current = seg + 1 if cum[seg + 1] - here <= AT_STOP_M else seg
    stories = _stops_with_stories(stops)

    out = []
    ahead = 0
    for first, last in _group_runs(stops):
        s = stops[first]
        item = {"name": s.name, "groupId": s.zespol}
        if last < current:
            item["state"] = "passed"
        elif first <= current:
            item["state"] = "current"
        else:
            ahead += 1
            item["state"] = "next" if ahead <= NEXT_COUNT else "upcoming"
            remaining = max(0.0, cum[first] - here)
            item["etaMinutes"] = max(1, round(remaining / AVG_SPEED_MPS / 60))
        if s.pk in stories:
            item["hasStory"] = True
        out.append(item)

    return {"vehicle": v.number, "line": v.line, "destination": route.last_stop_name or stops[-1].name, "stops": out}
