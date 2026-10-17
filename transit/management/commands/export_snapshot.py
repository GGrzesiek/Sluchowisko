import json
from pathlib import Path

from django.core.management.base import BaseCommand

from transit.aggregate import build_snapshot


class Command(BaseCommand):
    help = "Write a flat JSON of stops + live vehicles, e.g. export_snapshot --line 17 -o snapshot17.json"

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", default="snapshot.json")
        parser.add_argument("--type", choices=["tram", "bus"], default="tram")
        parser.add_argument("--line")
        parser.add_argument("--only", choices=["stops", "vehicles"])
        parser.add_argument("--radius", type=int, default=500)

    def handle(self, output, type, line, only, radius, **_):
        rows = build_snapshot(vehicle_type=2 if type == "tram" else 1, line=line, only=only, radius_m=radius)
        Path(output).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        n_v = sum(r["type"] == "vehicle" for r in rows)
        self.stdout.write(self.style.SUCCESS(f"Wrote {output}: {len(rows) - n_v} stops, {n_v} vehicles"))
