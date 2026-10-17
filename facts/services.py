import math
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from transit.geo import angle_diff, bbox, bearing_deg, haversine_m
from transit.models import Vehicle

from .models import Fact, SeenFact

AHEAD_CONE_DEG = 70  # a place counts as "ahead" if within ±70° of the heading
ALWAYS_SHOW_WITHIN_M = 120  # very close places are shown even if slightly behind
MAX_EXTRAPOLATE_S = 30


def estimate_position(v: Vehicle):
    """The feed lags 10 s+, so project the vehicle forward along its heading."""
    if v.heading is None or not v.speed_mps:
        return v.lat, v.lon
    age = min((timezone.now() - v.reported_at).total_seconds(), MAX_EXTRAPOLATE_S)
    dist = max(0.0, v.speed_mps * age)
    h = math.radians(v.heading)
    dlat = dist * math.cos(h) / 111_320
    dlon = dist * math.sin(h) / (111_320 * math.cos(math.radians(v.lat)))
    return v.lat + dlat, v.lon + dlon


def is_stale(v: Vehicle) -> bool:
    return timezone.now() - v.reported_at > timedelta(seconds=settings.POSITION_MAX_AGE_SECONDS)


def upcoming_facts(v: Vehicle, device_id: str | None, limit: int = 5, radius_m: int | None = None):
    radius_m = radius_m or settings.FACT_RADIUS_M
    lat, lon = estimate_position(v)
    min_lat, max_lat, min_lon, max_lon = bbox(lat, lon, radius_m)

    qs = Fact.objects.filter(
        approved=True,
        place__lat__range=(min_lat, max_lat),
        place__lon__range=(min_lon, max_lon),
    ).select_related("place")
    if device_id:
        qs = qs.exclude(id__in=SeenFact.objects.filter(device_id=device_id).values("fact_id"))

    results = []
    for f in qs:
        d = haversine_m(lat, lon, f.place.lat, f.place.lon)
        if d > radius_m:
            continue
        ahead = True
        if v.heading is not None and d > ALWAYS_SHOW_WITHIN_M:
            ahead = angle_diff(v.heading, bearing_deg(lat, lon, f.place.lat, f.place.lon)) <= AHEAD_CONE_DEG
        if not ahead:
            continue
        eta = round(d / v.speed_mps) if v.speed_mps and v.speed_mps > 1 else None
        results.append((f, round(d), eta))

    # nearest first, then the most surprising
    results.sort(key=lambda x: (x[1] // 100, -x[0].priority))
    return (lat, lon), results[:limit]
