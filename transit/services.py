from django.db import transaction

from .geo import bearing_deg, haversine_m
from .models import PositionLog, Vehicle
from .warsaw_api import VehicleReading

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
