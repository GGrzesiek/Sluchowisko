import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from stories.models import Story
from stories.serializers import StorySerializer

GENERATED_BY = "stop-story-writer"


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CommandError(f"Missing {path}.") from None
    except json.JSONDecodeError as error:
        raise CommandError(f"{path} is not valid JSON: {error}") from error


def discover(out: Path) -> list[str]:
    return sorted(path.stem for path in (out / "drafts").glob("*.json"))


class Command(BaseCommand):
    help = "Load the stop-story-writer output (out/drafts and out/photos) into Story as a draft."

    def add_arguments(self, parser):
        parser.add_argument("groups", nargs="*")
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--out", default="out")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        out = Path(opts["out"])
        groups = discover(out) if opts["all"] else opts["groups"]
        if not groups:
            raise CommandError("Pass stop group ids or --all.")
        imported, skipped, failed = [], [], []
        for group_id in groups:
            try:
                outcome = self._import(out, group_id, opts["force"], opts["dry_run"])
            except CommandError as error:
                failed.append(f"{group_id}: {error}")
                continue
            (imported if outcome is None else skipped).append(group_id if outcome is None else f"{group_id}: {outcome}")
        verb = "Would import" if opts["dry_run"] else "Imported"
        self.stdout.write(self.style.SUCCESS(f"{verb} {len(imported)} drafts"))
        for line in skipped:
            self.stdout.write(self.style.WARNING(f"Skipped {line}"))
        if failed:
            raise CommandError("Failed:\n  " + "\n  ".join(failed))

    def _import(self, out: Path, group_id: str, force: bool, dry_run: bool) -> str | None:
        draft = read_json(out / "drafts" / f"{group_id}.json")
        photos = read_json(out / "photos" / f"{group_id}.json")
        if not isinstance(draft, dict):
            raise CommandError("the draft must be a JSON object.")
        existing = Story.objects.filter(group_id=group_id).first()
        if existing and existing.status != Story.Status.DRAFT and not force:
            return f"already {existing.status}, use --force to replace it with a draft"
        data = {
            **{
                key: draft[key]
                for key in ("title", "lead", "card", "source_note", "narration", "text", "blocks", "sources")
                if key in draft
            },
            "group_id": group_id,
            "photos": photos,
            "status": Story.Status.DRAFT,
            "generated_by": GENERATED_BY,
        }
        serializer = StorySerializer(existing, data=data)
        if not serializer.is_valid():
            raise CommandError(json.dumps(serializer.errors, ensure_ascii=False))
        if not dry_run:
            serializer.save()
        return None
