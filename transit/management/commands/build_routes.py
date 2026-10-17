from django.core.management.base import BaseCommand, CommandError

from transit.models import Line
from transit.route_builder import build_line_routes
from transit.warsaw_api import WarsawApiError


class Command(BaseCommand):
    help = (
        "Build ordered routes from the departures timetable. "
        "build_routes --line 17 --line 4  |  build_routes --all [--kind tram] [--skip-built]"
    )

    def add_arguments(self, parser):
        parser.add_argument("--line", action="append", help="Line number, can be repeated")
        parser.add_argument("--all", action="store_true", help="Every line found by sync_city_data")
        parser.add_argument("--kind", help="With --all: only tram / bus / night / suburban / ...")
        parser.add_argument(
            "--skip-built",
            action="store_true",
            help="With --all: skip lines that already have routes (resume an interrupted run)",
        )
        parser.add_argument("--workers", type=int)

    def handle(self, line, all, kind, skip_built, workers, **_):
        if all:
            qs = Line.objects.all()
            if kind:
                qs = qs.filter(kind=kind)
            if skip_built:
                qs = qs.filter(routes__isnull=True)
            numbers = sorted(qs.values_list("number", flat=True).distinct(), key=lambda n: (len(n), n))
        elif line:
            numbers = line
        else:
            raise CommandError("Give --line 17 (repeatable) or --all")
        if not numbers:
            self.stdout.write("Nothing to build (run sync_city_data first, or everything is already built).")
            return

        ok, failed = 0, []
        for i, number in enumerate(numbers, 1):
            try:
                r = build_line_routes(number, workers=workers)
            except WarsawApiError as e:
                failed.append(number)
                self.stderr.write(f"[{i}/{len(numbers)}] line {number}: {e}")
                continue
            except Exception as e:  # noqa: BLE001 - one broken line must not stop the whole run
                failed.append(number)
                self.stderr.write(f"[{i}/{len(numbers)}] line {number}: unexpected error {e!r}")
                continue
            ok += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{i}/{len(numbers)}] line {number}: {len(r['routes'])} routes from "
                    f"{r['stops_queried']} stop posts ({r['errors']} errors)"
                )
            )
            if len(numbers) == 1 or not all:
                for rt in r["routes"]:
                    self.stdout.write(f"    {rt['code']:<10} -> {rt['direction']:<30} {rt['stops']} stops")

        self.stdout.write(
            f"Done: {ok} lines built, {len(failed)} failed"
            + (f" ({', '.join(failed[:20])}{'...' if len(failed) > 20 else ''})" if failed else "")
        )
        if failed and all:
            self.stdout.write("Re-run with --all --skip-built to retry only the missing ones.")
