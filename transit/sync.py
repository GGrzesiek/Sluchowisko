"""Import static city data (stops, lines, routes) into the DB. Run daily: routes change with roadworks."""
import re

from django.db import transaction

from . import warsaw_api
from .models import Line, Route, RouteStop, Stop


def classify_line(number: str) -> str:
    """Warsaw line numbering: 1-79 trams, 100-999 buses, N night, L suburban, E express, Z replacement."""
    n = number.upper()
    if n.isdigit():
        return Line.TRAM if int(n) < 100 else Line.BUS
    if n.startswith("N"):
        return Line.NIGHT
    if n.startswith("L"):
        return Line.SUBURBAN
    if n.startswith("E"):
        return Line.EXPRESS
    if n.startswith("Z") or re.fullmatch(r"T\d+", n):
        return Line.REPLACEMENT  # Z = replacement bus, T = temporary tram
    return Line.OTHER


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@transaction.atomic
def sync_stops(rows: list[dict] | None = None) -> int:
    rows = rows if rows is not None else warsaw_api.fetch_stops()
    existing = {(s.zespol, s.slupek): s for s in Stop.objects.all()}
    to_create, to_update = [], []
    for r in rows:
        lat, lon = _float(r.get("szer_geo")), _float(r.get("dlug_geo"))
        key = (str(r.get("zespol", "")), str(r.get("slupek", "")))
        if not all(key) or lat is None or lon is None:
            continue
        fields = {"name": r.get("nazwa_zespolu", ""), "lat": lat, "lon": lon,
                  "direction": r.get("kierunek") or ""}
        if key in existing:
            s = existing[key]
            for k, v in fields.items():
                setattr(s, k, v)
            to_update.append(s)
        else:
            s = Stop(zespol=key[0], slupek=key[1], **fields)
            existing[key] = s  # dedupe within the same import
            to_create.append(s)
    Stop.objects.bulk_create(to_create, batch_size=1000)
    Stop.objects.bulk_update(to_update, ["name", "lat", "lon", "direction"], batch_size=1000)
    return len(to_create) + len(to_update)


@transaction.atomic
def sync_routes(data: dict) -> dict:
    """Replace lines/routes from a {line: {route_code: {order: stop}}} dict. Atomic.
    (Used by tests and for importing route files; live routes come from route_builder.)"""
    stops = {(s.zespol, s.slupek): s for s in Stop.objects.all()}

    seen_lines = []
    route_stops = []
    route_count = 0
    for line_no, routes in data.items():
        line_no = str(line_no).strip()
        if not line_no or not isinstance(routes, dict):
            continue
        line, _ = Line.objects.update_or_create(number=line_no, defaults={"kind": classify_line(line_no)})
        seen_lines.append(line_no)
        line.routes.all().delete()  # cascades to RouteStop
        for code, points in routes.items():
            if not isinstance(points, dict):
                continue
            ordered = sorted(points.items(), key=lambda kv: int(kv[0]))
            route = Route.objects.create(line=line, code=code, stop_count=len(ordered))
            route_count += 1
            names = []
            for order, p in ordered:
                key = (str(p.get("nr_zespolu", "")), str(p.get("nr_przystanku", "")))
                stop = stops.get(key)
                if stop:
                    names.append(stop.name)
                dist = _float(p.get("odleglosc"))
                route_stops.append(RouteStop(
                    route=route, order=int(order), zespol=key[0], slupek=key[1], stop=stop,
                    street_id=str(p.get("ulica_id") or ""), stop_type=str(p.get("typ") or ""),
                    distance_m=int(dist) if dist is not None else None,
                ))
            if names:
                route.first_stop_name, route.last_stop_name = names[0], names[-1]
                route.save(update_fields=["first_stop_name", "last_stop_name"])

    RouteStop.objects.bulk_create(route_stops, batch_size=2000)
    removed, _ = Line.objects.exclude(number__in=seen_lines).delete()  # lines that no longer exist
    return {"lines": len(seen_lines), "routes": route_count, "route_stops": len(route_stops),
            "unmatched_stops": sum(1 for rs in route_stops if rs.stop is None), "removed": removed}
