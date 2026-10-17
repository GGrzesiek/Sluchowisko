import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from facts.models import Fact, Place
from facts.validation import validate_places
from transit.llm_context import build_line_context
from transit.models import Line

DEFAULT = Path(__file__).resolve().parents[2] / "data" / "sample_facts.json"


class Command(BaseCommand):
    help = ("Load places + facts from JSON (the LLM output). "
            "With --line, places too far from that line's route are rejected.")

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(DEFAULT))
        parser.add_argument("--line", help="Validate against this line's route, e.g. 17")
        parser.add_argument("--approve", action="store_true", help="Mark imported facts as approved")
        parser.add_argument("--generated-by", default="human")
        parser.add_argument("--dry-run", action="store_true", help="Only print the validation report")

    def handle(self, path, line, approve, generated_by, dry_run, **opts):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise CommandError(f"Cannot read {path}: {e}")

        stops, corridor = None, 400
        if line:
            obj = Line.objects.filter(number=line).first()
            ctx = build_line_context(obj, include_task=False) if obj else None
            if not ctx:
                raise CommandError(f"Line {line} has no route, run sync_city_data first")
            stops, corridor = ctx["stops"], ctx["corridor_m"]

        report = validate_places(data, stops, corridor)
        verbose = opts.get("verbosity", 1) > 0
        if verbose:
            for r in report["rejected"]:
                self.stderr.write(f"REJECTED {r['place']}: {'; '.join(r['errors'])}")
            for w in report["warnings"]:
                self.stderr.write(f"warning: {w}")
        if dry_run:
            self.stdout.write(f"{len(report['valid'])} valid, {len(report['rejected'])} rejected (dry run)")
            return

        n = 0
        for p in report["valid"]:
            place, _ = Place.objects.update_or_create(
                name=p["name"],
                defaults={"lat": p["lat"], "lon": p["lon"], "category": p.get("category", ""),
                          "image_url": p.get("image_url", "")},
            )
            for f in p["facts"]:
                Fact.objects.update_or_create(
                    place=place, title=f["title"].strip(),
                    defaults={"text": f["text"].strip(), "source_url": f["source_url"],
                              "language": f.get("language", "pl"), "priority": f["priority"],
                              "generated_by": generated_by, "approved": approve},
                )
                n += 1
        if verbose:
            self.stdout.write(self.style.SUCCESS(
                f"Loaded {len(report['valid'])} places, {n} facts ({len(report['rejected'])} places rejected)"))
