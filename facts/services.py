import math
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from transit.models import Vehicle

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
