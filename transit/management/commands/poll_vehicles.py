import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from transit.services import ingest_readings
from transit.warsaw_api import WarsawApiError, fetch_vehicle_positions

DEMO_LINES_FILE = settings.BASE_DIR / "data" / "demo_lines.json"


def demo_lines() -> set[str]:
    return {entry["line"] for entry in json.loads(DEMO_LINES_FILE.read_text())["lines"]}


class Command(BaseCommand):
    help = "Poll live positions of buses and trams and store them for the given lines."

    def add_arguments(self, parser):
        parser.add_argument("--line", action="append", dest="lines", default=[], help="Repeat for more lines")
        parser.add_argument("--demo", action="store_true", help="Add the lines from data/demo_lines.json")
        parser.add_argument("--interval", type=int, default=settings.POLL_INTERVAL_SECONDS)
        parser.add_argument("--once", action="store_true", help="Fetch once and exit")

    def handle(self, lines, demo, interval, once, **_):
        wanted = set(lines) | (demo_lines() if demo else set())
        if not wanted:
            raise CommandError("Give --line N (repeatable) or --demo")
        self.stdout.write(f"Polling lines {', '.join(sorted(wanted, key=lambda n: (len(n), n)))} every {interval}s.")
        while True:
            started = time.monotonic()
            try:
                readings = [
                    reading
                    for vehicle_type in (1, 2)
                    for reading in fetch_vehicle_positions(vehicle_type=vehicle_type)
                    if reading.line in wanted
                ]
                new = ingest_readings(readings)
                self.stdout.write(f"{time.strftime('%H:%M:%S')} {len(readings)} vehicles, {new} new readings")
            except WarsawApiError as error:
                self.stderr.write(f"poll failed: {error}")
            if once:
                return
            time.sleep(max(0, interval - (time.monotonic() - started)))
