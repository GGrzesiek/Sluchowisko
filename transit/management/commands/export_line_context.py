import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from transit.llm_context import build_line_context
from transit.models import Line


class Command(BaseCommand):
    help = "Write the LLM context for a line to a JSON file, e.g. export_line_context 17 -o line17.json"

    def add_arguments(self, parser):
        parser.add_argument("line")
        parser.add_argument("-o", "--output")
        parser.add_argument("--route", help="Route code, default = longest main route")
        parser.add_argument("--bare", action="store_true", help="Only data, without task/rules/output_format")
        parser.add_argument("--corridor", type=int, help="Metres around the route (default FACT_RADIUS_M)")

    def handle(self, line, output, route, bare, corridor, **_):
        obj = Line.objects.filter(number=line).first()
        if not obj:
            raise CommandError(f"Line {line} not found, run sync_city_data first")
        ctx = build_line_context(obj, route_code=route, include_task=not bare, corridor_m=corridor)
        if ctx is None:
            raise CommandError("No route found for this line")
        text = json.dumps(ctx, ensure_ascii=False, indent=2)
        if output:
            Path(output).write_text(text, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(
                f"Wrote {output}: {ctx['route']['stop_count']} stops, {ctx['route']['length_km']} km"))
        else:
            self.stdout.write(text)
