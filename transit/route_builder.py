"""Build lines and ordered routes from the three dane.um.warszawa.pl transport datasets:

  1. Lokalizacja przystanków         -> Stop (coordinates)              [sync.sync_stops]
  2. Linie dostępne na przystanku    -> StopLine (which line stops where) [crawl_stop_lines]
  3. Odjazdy linii z przystanku      -> stop ORDER for each route        [build_line_routes]

There is no "routes" dataset, so the order of stops is reconstructed from the timetable:
one brigade drives a route variant ("trasa", e.g. TP-FSO) stop after stop, so sorting the stops
by that brigade's earliest departure time gives the stops in driving order.
"""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import warsaw_api
from .models import Line, Route, RouteStop, Stop, StopLine
from .sync import classify_line


def parse_czas(value: str) -> int | None:
    """'05:12:00' -> seconds. ZTM uses hours >= 24 for trips after midnight ('24:10:00')."""
    try:
        parts = [int(p) for p in str(value).split(":")]
        return parts[0] * 3600 + parts[1] * 60 + (parts[2] if len(parts) > 2 else 0)
    except (ValueError, IndexError):
        return None


def _parallel(func, items, workers):
    """Run func(item) in a small thread pool. Yields (item, result, error)."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(func, it): it for it in items}
        for f in as_completed(futures):
            try:
                yield futures[f], f.result(), None
            except Exception as e:  # noqa: BLE001 - keep crawling, report at the end
                yield futures[f], None, e


def crawl_stop_lines(
    stops=None, workers: int | None = None, max_age_hours: float | None = None, progress=None
) -> dict:
    """Ask "which lines stop here?" for every stop post. ~1 request per stop post, run in parallel.

    max_age_hours: skip stops checked more recently than this (makes the crawl resumable).
    """
    workers = workers or settings.WARSAW_API_WORKERS
    stops = list(stops if stops is not None else Stop.objects.all())
    if max_age_hours is not None:
        cutoff = timezone.now() - timedelta(hours=max_age_hours)
        stops = [s for s in stops if not s.lines_checked_at or s.lines_checked_at < cutoff]

    done = errors = 0
    first_error = None
    for stop, lines, err in _parallel(
        lambda s: warsaw_api.fetch_lines_at_stop(s.zespol, s.slupek), stops, workers
    ):
        if err:
            errors += 1
            first_error = first_error or err
            continue
        with transaction.atomic():  # DB writes stay in the main thread
            StopLine.objects.filter(stop=stop).delete()
            StopLine.objects.bulk_create([StopLine(stop=stop, line=ln) for ln in set(lines)])
            stop.lines_checked_at = timezone.now()
            stop.save(update_fields=["lines_checked_at"])
        done += 1
        if progress and done % 200 == 0:
            progress(done, len(stops))

    # every line seen anywhere becomes a Line row
    for number in StopLine.objects.values_list("line", flat=True).distinct():
        Line.objects.update_or_create(number=number, defaults={"kind": classify_line(number)})
    return {
        "stops_checked": done,
        "errors": errors,
        "first_error": str(first_error) if first_error else None,
        "lines": Line.objects.count(),
    }


def order_route(times_by_brigade: dict) -> list:
    """times_by_brigade: {brigade: {stop_key: [seconds, ...]}} for ONE route variant.

    Pick the brigade that covers the most stops and sort those stops by its earliest time.
    """
    if not times_by_brigade:
        return []
    best = max(
        times_by_brigade.values(), key=lambda by_stop: (len(by_stop), -min(min(t) for t in by_stop.values()))
    )
    return [stop for stop, _ in sorted(best.items(), key=lambda kv: min(kv[1]))]


def build_line_routes(line_number: str, workers: int | None = None) -> dict:
    """Rebuild Route + ordered RouteStop rows for one line from the departures timetable."""
    workers = workers or settings.WARSAW_API_WORKERS
    stops = list(Stop.objects.filter(stop_lines__line=line_number))
    if not stops:
        raise warsaw_api.WarsawApiError(
            f"No stops known for line {line_number}. Run crawl_stop_lines (sync_city_data) first."
        )

    # route code -> brigade -> stop -> [times];  route code -> direction name
    times = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    direction = {}
    errors = 0
    for stop, deps, err in _parallel(
        lambda s: warsaw_api.fetch_departures(s.zespol, s.slupek, line_number), stops, workers
    ):
        if err:
            errors += 1
            continue
        for d in deps:
            t = parse_czas(d.get("czas"))
            code = (d.get("trasa") or "").strip()
            if t is None or not code:
                continue
            times[code][str(d.get("brygada") or "")][stop.pk].append(t)
            direction.setdefault(code, (d.get("kierunek") or "").strip())

    by_pk = {s.pk: s for s in stops}
    with transaction.atomic():
        line, _ = Line.objects.update_or_create(
            number=line_number, defaults={"kind": classify_line(line_number)}
        )
        line.routes.all().delete()
        built = []
        for code, by_brigade in sorted(times.items()):
            ordered = [by_pk[pk] for pk in order_route(by_brigade)]
            if len(ordered) < 2:
                continue
            route = Route.objects.create(
                line=line,
                code=code,
                stop_count=len(ordered),
                first_stop_name=ordered[0].name,
                last_stop_name=direction.get(code) or ordered[-1].name,
            )
            RouteStop.objects.bulk_create(
                [
                    RouteStop(route=route, order=i + 1, zespol=s.zespol, slupek=s.slupek, stop=s)
                    for i, s in enumerate(ordered)
                ]
            )
            built.append({"code": code, "direction": route.last_stop_name, "stops": len(ordered)})
    return {"line": line_number, "stops_queried": len(stops), "errors": errors, "routes": built}
