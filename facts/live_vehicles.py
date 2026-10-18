from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone

from transit.models import Line, Route, Vehicle
from transit.services import city_positions, ingest_readings
from transit.warsaw_api import WarsawApiError

from .ride_progress import NoRouteError, line_routes, ride_state
from .services import is_stale


def app_url(line: str, number: str) -> str:
    return f"{settings.APP_URL.rstrip('/')}/?{urlencode({'line': line, 'vehicle': number})}"


def _stop_named(info: dict, state: str) -> str | None:
    return next((s["name"] for s in info["stops"] if s["state"] == state), None)


def _describe(v: Vehicle, now, routes: list[tuple]) -> dict:
    item = {
        "number": v.number,
        "line": v.line,
        "brigade": v.brigade,
        "route": None,
        "destination": None,
        "stop": None,
        "nextStop": None,
        "ageS": round((now - v.reported_at).total_seconds()),
        "lat": v.lat,
        "lon": v.lon,
        "appUrl": app_url(v.line, v.number),
    }
    try:
        route, info = ride_state(v, routes)
    except NoRouteError:
        return item
    item.update(
        route=route.code,
        destination=info["destination"],
        stop=_stop_named(info, "current"),
        nextStop=_stop_named(info, "next"),
    )
    return item


def _why_empty(line: str, route: str | None, city_api_error: str | None = None) -> str:
    codes = sorted(Route.objects.filter(line_id=line).values_list("code", flat=True))
    if not Line.objects.filter(number=line).exists() or not codes:
        return f"Line {line} has no routes in the database. Run: python manage.py build_routes --line {line}"
    if route and route.upper() not in {c.upper() for c in codes}:
        return f"Line {line} has no route {route}. Its routes: {', '.join(codes)}."
    newest = Vehicle.objects.filter(line=line).order_by("-reported_at").first()
    max_age = settings.POSITION_MAX_AGE_SECONDS
    if newest is None and city_api_error:
        return f"The city feed could not be reached ({city_api_error}) and no vehicle of line {line} is stored."
    if newest is None:
        return f"No vehicle of line {line} is on the road right now (the city feed has none)."
    minutes = round((timezone.now() - newest.reported_at).total_seconds() / 60)
    where = f" on route {route}" if route else ""
    return (
        f"No vehicle of line {line}{where} has a position from the last {max_age} s. "
        f"The newest one ({newest.number}) is {minutes} min old."
    )


def live_vehicles(line: str, route: str | None = None, refresh: bool = True) -> dict:
    line = line.strip().upper()
    result = {"line": line, "route": route, "refreshed": False, "maxAgeS": settings.POSITION_MAX_AGE_SECONDS}
    if refresh:
        try:
            ingest_readings([r for r in city_positions() if r.line.upper() == line])
            result["refreshed"] = True
        except WarsawApiError as e:
            result["cityApiError"] = str(e)
    now = timezone.now()
    routes = line_routes(line)
    vehicles = []
    for v in Vehicle.objects.filter(line=line).order_by("number"):
        if is_stale(v):
            continue
        item = _describe(v, now, routes)
        if route and (item["route"] or "").upper() != route.upper():
            continue
        vehicles.append(item)
    result["vehicles"] = vehicles
    if not vehicles:
        result["detail"] = _why_empty(line, route, result.get("cityApiError"))
    return result
