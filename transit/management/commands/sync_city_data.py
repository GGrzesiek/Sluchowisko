from django.core.management.base import BaseCommand, CommandError

from transit.models import Line, Stop
from transit.route_builder import crawl_stop_lines
from transit.sync import sync_stops
from transit.warsaw_api import WarsawApiError


class Command(BaseCommand):
    help = (
        "1) import all stops with coordinates, 2) ask every stop which lines stop there "
        "-> every line in Warsaw. Then run build_routes --line 17 for ordered routes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--skip-stops", action="store_true", help="Don't re-import stop coordinates")
        parser.add_argument("--limit", type=int, help="Only crawl N stops (quick test)")
        parser.add_argument(
            "--max-age-hours",
            type=float,
            default=24,
            help="Skip stops crawled within this many hours (resume an interrupted run)",
        )
        parser.add_argument("--workers", type=int, help="Parallel requests (default WARSAW_API_WORKERS)")

    def handle(self, skip_stops, limit, max_age_hours, workers, **_):
        try:
            if not skip_stops:
                self.stdout.write("1/2 Fetching stop locations...")
                self.stdout.write(f"    {sync_stops()} stop posts")
            stops = Stop.objects.order_by("zespol", "slupek")
            if limit:
                stops = stops[:limit]
            self.stdout.write("2/2 Asking each stop which lines stop there (takes a few minutes)...")
            stats = crawl_stop_lines(
                stops,
                workers=workers,
                max_age_hours=max_age_hours,
                progress=lambda d, t: self.stdout.write(f"    {d}/{t}"),
            )
        except WarsawApiError as e:
            raise CommandError(f"City API: {e}") from e
        self.stdout.write(
            self.style.SUCCESS(
                f"    {stats['stops_checked']} stops checked, {stats['errors']} errors, {stats['lines']} lines"
            )
        )
        if stats["first_error"]:
            self.stderr.write(f"    first error: {stats['first_error']}")
        for kind, _ in Line.KIND_CHOICES:
            if n := Line.objects.filter(kind=kind).count():
                self.stdout.write(f"    {kind}: {n}")
