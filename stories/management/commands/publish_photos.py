import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from stories import media
from stories.models import Story


def collector_images(out: Path, group_id: str) -> dict[str, Path]:
    collected = out / "collected" / f"{group_id}.json"
    if not collected.is_file():
        return {}
    images = {}
    for image in json.loads(collected.read_text()).get("images", []):
        parts = Path(image["file"]).parts
        images[image["url"]] = out.joinpath(*parts[1:]) if parts and parts[0] == "out" else out / image["file"]
    return images


class Command(BaseCommand):
    help = "Upload the photos of stories to the media bucket and point photos[].src at them."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="out")
        parser.add_argument("--download", action="store_true")
        parser.add_argument("--data-bucket", default=settings.GCS_DATA_BUCKET)
        parser.add_argument("--group", action="append", dest="groups")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        out = Path(opts["out"])
        try:
            if opts["download"]:
                media.download(opts["data_bucket"], "out", out)
            stories = Story.objects.exclude(status=Story.Status.REJECTED)
            if opts["groups"]:
                stories = stories.filter(group_id__in=opts["groups"])
            uploaded, published, missing = 0, 0, []
            for story in stories:
                images = collector_images(out, story.group_id)
                photos, changed = [], False
                for photo in story.photos:
                    if media.is_media_url(photo["src"]):
                        published += 1
                        photos.append(photo)
                        continue
                    path = images.get(photo.get("source_url", ""))
                    if path is None or not path.is_file():
                        missing.append(f"{story.group_id}: {photo.get('source_url') or photo['src']}")
                        photos.append(photo)
                        continue
                    object_name = f"photos/{story.group_id}/{path.name}"
                    if opts["dry_run"]:
                        self.stdout.write(f"would upload {path} -> {object_name}")
                        photos.append(photo)
                        continue
                    photos.append({**photo, "src": media.upload(path, object_name)})
                    changed = True
                    uploaded += 1
                if changed:
                    Story.objects.filter(pk=story.pk).update(photos=photos)
        except media.MediaError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(self.style.SUCCESS(f"Uploaded {uploaded} photos, {published} already in the media bucket"))
        if missing:
            self.stdout.write(self.style.WARNING("No collector file for:\n  " + "\n  ".join(missing)))
