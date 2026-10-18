import hashlib
import tempfile
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from stories import media
from stories.models import Story

USER_AGENT = "Sluchowisko/1.0 (https://github.com/GGrzesiek/opendatahackathon42)"
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


def object_name(group_id: str, src: str, content_type: str) -> str:
    digest = hashlib.sha256(src.encode()).hexdigest()[:16]
    return f"photos/{group_id}/{digest}{EXTENSIONS[content_type]}"


def fetch(src: str, target: Path) -> str:
    request = urllib.request.Request(src, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        content_type = response.headers.get_content_type()
        if content_type not in EXTENSIONS:
            raise ValueError(f"{content_type}, not an image")
        target.write_bytes(response.read())
    return content_type


class Command(BaseCommand):
    help = "Download the photos of stories, upload them to the media bucket and point photos[].src at them."

    def add_arguments(self, parser):
        parser.add_argument("--group", action="append", dest="groups")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        stories = Story.objects.exclude(status=Story.Status.REJECTED)
        if opts["groups"]:
            stories = stories.filter(group_id__in=opts["groups"])
        uploaded, published, failed = 0, 0, []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "photo"
            for story in stories:
                photos, changed = [], False
                for photo in story.photos:
                    src = photo["src"]
                    if media.is_media_url(src):
                        published += 1
                        photos.append(photo)
                        continue
                    if not src.startswith(("https://", "http://")):
                        failed.append(f"{story.group_id}: {src[:80]} (not a web address)")
                        photos.append(photo)
                        continue
                    if opts["dry_run"]:
                        self.stdout.write(f"would upload {src} for {story.group_id}")
                        photos.append(photo)
                        continue
                    try:
                        content_type = fetch(src, path)
                    except (OSError, ValueError) as error:
                        failed.append(f"{story.group_id}: {src} ({error})")
                        photos.append(photo)
                        continue
                    typed = path.replace(path.with_suffix(EXTENSIONS[content_type]))
                    try:
                        url = media.upload(typed, object_name(story.group_id, src, content_type))
                    except media.MediaError as error:
                        raise CommandError(str(error)) from error
                    photos.append({**photo, "src": url})
                    changed = True
                    uploaded += 1
                if changed:
                    Story.objects.filter(pk=story.pk).update(photos=photos)

        self.stdout.write(self.style.SUCCESS(f"Uploaded {uploaded} photos, {published} already in the media bucket"))
        if failed:
            self.stdout.write(self.style.WARNING("Not uploaded:\n  " + "\n  ".join(failed)))
