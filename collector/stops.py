import os

import django
from django.apps import apps

from collector.schema import Pole, Stop


class UnknownStopGroup(LookupError):
    pass


def load_stop(group_id: str) -> Stop:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if not apps.ready:
        django.setup()
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
