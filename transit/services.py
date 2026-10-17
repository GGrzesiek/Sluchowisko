from django.core.cache import cache
from django.db import transaction

from .geo import bearing_deg, haversine_m
from .models import PositionLog, Vehicle
from .warsaw_api import VehicleReading, fetch_vehicle_positions

CITY_POSITIONS_CACHE_KEY = "city:positions"
CITY_POSITIONS_CACHE_SECONDS = 10

# Below this movement we keep the old heading (GPS jitter while standing at a stop)
MIN_MOVE_FOR_HEADING_M = 15


@transaction.atomic
def ingest_readings(readings: list[VehicleReading]) -> int:
    """Upsert latest vehicle state + append to the log. Returns number of new readings."""
    new = 0
    for r in readings:
        v = Vehicle.objects.filter(number=r.vehicle_number).first()
        if v and r.time <= v.reported_at:
            continue  # same or older reading, the API often repeats them
        new += 1
        PositionLog.objects.get_or_create(
            vehicle_number=r.vehicle_number,
            reported_at=r.time,
            defaults={"line": r.line, "lat": r.lat, "lon": r.lon},
        )
        if v is None:
            Vehicle.objects.create(
                number=r.vehicle_number,
                line=r.line,
                brigade=r.brigade,
                lat=r.lat,
                lon=r.lon,
                reported_at=r.time,
            )
            continue
        moved = haversine_m(v.lat, v.lon, r.lat, r.lon)
        dt = (r.time - v.reported_at).total_seconds()
        if moved >= MIN_MOVE_FOR_HEADING_M:
            v.heading = bearing_deg(v.lat, v.lon, r.lat, r.lon)
        v.speed_mps = moved / dt if dt > 0 else v.speed_mps
        v.prev_lat, v.prev_lon, v.prev_reported_at = v.lat, v.lon, v.reported_at
        v.lat, v.lon, v.reported_at = r.lat, r.lon, r.time
        v.line, v.brigade = r.line, r.brigade
        v.save()
    return new


def city_positions() -> list[VehicleReading]:
    readings = cache.get(CITY_POSITIONS_CACHE_KEY)
    if readings is None:
        readings = [*fetch_vehicle_positions(vehicle_type=1), *fetch_vehicle_positions(vehicle_type=2)]
        cache.set(CITY_POSITIONS_CACHE_KEY, readings, CITY_POSITIONS_CACHE_SECONDS)
    return readings


def refresh_vehicle(number: str) -> bool:
    matches = [r for r in city_positions() if r.vehicle_number == number]
    if matches:
        ingest_readings([max(matches, key=lambda r: r.time)])
    return bool(matches)
