import json
from pathlib import Path

from django.core.management.base import BaseCommand

from stories.models import Story
from stories.serializers import story_content


class Command(BaseCommand):
    help = "Write verified stories as static JSON files for the app."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="out/stories")
        parser.add_argument("--include-drafts", action="store_true")

    def handle(self, *args, **opts):
        out = Path(opts["out"])
        out.mkdir(parents=True, exist_ok=True)
        qs = Story.objects.all()
        if not opts["include_drafts"]:
            qs = qs.filter(status=Story.Status.VERIFIED)
        index = []
        for story in qs:
            content = story_content(story)
            (out / f"{story.group_id}.json").write_text(
                json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            index.append({"groupId": story.group_id, "title": story.title})
        (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Exported {len(index)} stories to {out}"))
