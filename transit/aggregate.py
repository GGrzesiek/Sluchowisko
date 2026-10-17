"""Aggregate two city datasets into ONE flat JSON table:
  - stop coordinates      (dbstore_get, paginated)  -> rows with "type": "stop"
  - live vehicle positions (busestrams_get)          -> rows with "type": "vehicle"

Every row has exactly the same keys (null when not applicable), no nesting.
  vehicle -> nearest stop (+ distance)
  stop    -> how many vehicles are near it now, which one is closest, which lines serve it
"""

import math
from collections import defaultdict

from django.core.cache import cache
from django.utils import timezone

from . import warsaw_api
from .geo import haversine_m
from .models import RouteStop, Stop, Vehicle
from .services import ingest_readings

CELL_DEG = 0.005  # ~550 m x 350 m grid cells for fast nearest-neighbour search
LIVE_CACHE_SECONDS = 10

COLUMNS = [
    "type",  # "stop" | "vehicle"
    "id",  # stop: "zespol-slupek", vehicle: fleet number
    "name",  # stop name / "Tram 17 #3201"
    "lines",  # stop: lines serving it "17,33"; vehicle: its line
    "lat",
    "lon",
    "time",  # vehicle: GPS time from the API; stop: null
    "brigade",
    "heading_deg",
    "speed_kmh",  # vehicle, computed from the last two readings
    "direction",  # stop: direction from the API
    "nearest_stop_id",
    "nearest_stop_name",
    "nearest_stop_distance_m",  # vehicle -> stop
    "vehicles_nearby",
    "nearest_vehicle_id",
    "nearest_vehicle_distance_m",  # stop -> vehicles
    "fetched_at",
]


class _Grid:
    """Bucket points into lat/lon cells so lookups only check neighbouring cells."""

    def __init__(self, items, key=lambda x: (x.lat, x.lon)):
        self.key = key
        self.cells = defaultdict(list)
        for it in items:
            lat, lon = key(it)
            self.cells[(int(lat // CELL_DEG), int(lon // CELL_DEG))].append(it)

    def near(self, lat, lon, radius_m):
        r = max(1, math.ceil(radius_m / 350))
        cy, cx = int(lat // CELL_DEG), int(lon // CELL_DEG)
        out = []
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                for it in self.cells.get((cy + dy, cx + dx), ()):
                    d = haversine_m(lat, lon, *self.key(it))
                    if d <= radius_m:
                        out.append((d, it))
        return sorted(out, key=lambda x: x[0])


def _row(**kw):
    return {c: kw.get(c) for c in COLUMNS}


def live_readings(vehicle_type: int, line: str | None):
    """Live positions from the city, cached 10 s, and stored so heading/speed build up over time."""
    key = f"agg:{vehicle_type}:{line or 'all'}"
    readings = cache.get(key)
    if readings is None:
        readings = warsaw_api.fetch_vehicle_positions(line=line, vehicle_type=vehicle_type)
        ingest_readings(readings)
        cache.set(key, readings, LIVE_CACHE_SECONDS)
    return readings


def build_snapshot(
    vehicle_type: int = 2,
    line: str | None = None,
    only: str | None = None,
    radius_m: int = 500,
    max_age_s: int = 300,
) -> list[dict]:
    """vehicle_type: 1 = bus, 2 = tram. line: restrict to one line (and the stops it serves)."""
    now = timezone.now()
    fetched_at = now.isoformat(timespec="seconds")

    # ALL lines per stop post, from the imported routes (even when filtering by one line)
    lines_at = defaultdict(set)
    for z, s, ln in RouteStop.objects.values_list("zespol", "slupek", "route__line_id"):
        lines_at[(z, s)].add(ln)

    stops = list(Stop.objects.all())
    if line:
        on_line = {k for k, lns in lines_at.items() if line in lns}
        if on_line:
            stops = [s for s in stops if (s.zespol, s.slupek) in on_line]

    readings = [
        r for r in live_readings(vehicle_type, line) if (now - r.time).total_seconds() <= max_age_s
    ]  # the feed contains old ghosts
    state = {v.number: v for v in Vehicle.objects.filter(number__in=[r.vehicle_number for r in readings])}
    kind = "Tram" if vehicle_type == 2 else "Bus"

    stop_grid = _Grid(stops)
    vehicle_grid = _Grid(readings)
    rows = []

    if only != "stops":
        for r in readings:
            near = stop_grid.near(r.lat, r.lon, radius_m)
            d, s = near[0] if near else (None, None)
            v = state.get(r.vehicle_number)
            rows.append(
                _row(
                    type="vehicle",
                    id=r.vehicle_number,
                    name=f"{kind} {r.line} #{r.vehicle_number}",
                    lines=r.line,
                    lat=r.lat,
                    lon=r.lon,
                    time=r.time.isoformat(timespec="seconds"),
                    brigade=r.brigade,
                    heading_deg=round(v.heading) if v and v.heading is not None else None,
                    speed_kmh=round(v.speed_mps * 3.6, 1) if v and v.speed_mps is not None else None,
                    nearest_stop_id=f"{s.zespol}-{s.slupek}" if s else None,
                    nearest_stop_name=s.name if s else None,
                    nearest_stop_distance_m=round(d) if s else None,
                    fetched_at=fetched_at,
                )
            )

    if only != "vehicles":
        for s in stops:
            near = vehicle_grid.near(s.lat, s.lon, radius_m)
            rows.append(
                _row(
                    type="stop",
                    id=f"{s.zespol}-{s.slupek}",
                    name=s.name,
                    lines=",".join(sorted(lines_at.get((s.zespol, s.slupek), ()), key=lambda x: (len(x), x))) or None,
                    lat=s.lat,
                    lon=s.lon,
                    direction=s.direction or None,
                    vehicles_nearby=len(near),
                    nearest_vehicle_id=near[0][1].vehicle_number if near else None,
                    nearest_vehicle_distance_m=round(near[0][0]) if near else None,
                    fetched_at=fetched_at,
                )
            )
    return rows
