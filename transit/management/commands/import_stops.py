from django.core.management.base import BaseCommand

from transit.sync import sync_stops


class Command(BaseCommand):
    help = "Import all stop posts with coordinates (dbstore_get, paginated)."

    def handle(self, **_):
        n = sync_stops()
        self.stdout.write(self.style.SUCCESS(f"Imported {n} stops"))
