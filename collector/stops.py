import os

import django
from django.apps import apps

from collector.schema import Pole, Stop

NEAREST_STOP_RADIUS_M = 300


class UnknownStopGroup(LookupError):
    pass


def setup_backend() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if not apps.ready:
        django.setup()


def group_near(lat: float, lon: float, radius_m: int = NEAREST_STOP_RADIUS_M) -> str | None:
    setup_backend()
    from transit.geo import bbox, haversine_m
    from transit.models import Stop as StopRow

    south, north, west, east = bbox(lat, lon, radius_m)
    poles = StopRow.objects.filter(lat__range=(south, north), lon__range=(west, east))
    found = sorted(
        (haversine_m(lat, lon, pole.lat, pole.lon), pole.zespol, pole.slupek) for pole in poles if pole.zespol.isdigit()
    )
    return found[0][1] if found and found[0][0] <= radius_m else None


def load_stop(group_id: str) -> Stop:
    setup_backend()
    from transit.models import Stop as StopRow

    rows = list(StopRow.objects.filter(zespol=group_id).order_by("slupek"))
    if not rows:
        raise UnknownStopGroup(
            f"Stop group {group_id} is not in the backend's stop table. "
            "Check the id, or fill the table with: python manage.py import_stops"
        )
    return Stop(
        group_id=group_id,
        name=rows[0].name,
        lat=round(sum(row.lat for row in rows) / len(rows), 6),
        lon=round(sum(row.lon for row in rows) / len(rows), 6),
        poles=[Pole(pole=row.slupek, lat=row.lat, lon=row.lon) for row in rows],
    )
