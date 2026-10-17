import time

from django.conf import settings
from django.core.management.base import BaseCommand

from transit.services import ingest_readings
from transit.warsaw_api import WarsawApiError, fetch_vehicle_positions


class Command(BaseCommand):
    help = "Poll live vehicle positions from api.um.warszawa.pl every N seconds."

    def add_arguments(self, parser):
        parser.add_argument("--line", default=settings.POC_LINE)
        parser.add_argument("--type", type=int, default=settings.POC_VEHICLE_TYPE, help="1=bus, 2=tram")
        parser.add_argument("--interval", type=int, default=settings.POLL_INTERVAL_SECONDS)
        parser.add_argument("--once", action="store_true", help="Fetch once and exit")

    def handle(self, line, type, interval, once, **_):
        self.stdout.write(f"Polling line {line} (type {type}) every {interval}s. Ctrl+C to stop.")
        while True:
            started = time.monotonic()
            try:
                readings = fetch_vehicle_positions(line=line, vehicle_type=type)
                new = ingest_readings(readings)
                self.stdout.write(f"{len(readings)} vehicles, {new} new readings")
            except (WarsawApiError, Exception) as e:  # keep polling through API hiccups
                self.stderr.write(f"poll failed: {e}")
            if once:
                return
            time.sleep(max(0, interval - (time.monotonic() - started)))
