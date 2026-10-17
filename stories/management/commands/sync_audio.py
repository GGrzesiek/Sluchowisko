import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from stories.audio import UploadError, duration_seconds, find_recordings, object_name, public_url, upload_public
from stories.models import Story


class Command(BaseCommand):
    help = "Upload recordings of verified stories to the public media bucket and fill audio_url and audio_seconds."

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument("--source")
        source.add_argument("--download", action="store_true")
        parser.add_argument("--bucket", default=os.getenv("GCS_AUDIO_BUCKET", ""))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        if opts["download"]:
            with tempfile.TemporaryDirectory() as tmp:
                self._download(opts["bucket"], Path(tmp))
                self._sync(Path(tmp), opts["dry_run"])
            return
        source = Path(opts["source"])
        if not source.is_dir():
            raise CommandError(f"No recordings in {source}.")
        self._sync(source, opts["dry_run"])

    def _sync(self, source: Path, dry_run: bool):
        recordings = find_recordings(source)
        uploaded, missing, broken, cleared = [], [], [], 0
        for story in Story.objects.filter(status=Story.Status.VERIFIED):
            path = recordings.get(story.group_id)
            if path is None:
                missing.append(story.group_id)
            else:
                try:
                    seconds = duration_seconds(path)
                except Exception:
                    broken.append(story.group_id)
                    path = None
            if path is None:
                if story.audio_url and not dry_run:
                    Story.objects.filter(pk=story.pk).update(audio_url="", audio_seconds=None)
                    cleared += 1
                continue
            name = object_name(story.group_id, path.suffix)
            if not dry_run:
                try:
                    upload_public(path, name)
                except UploadError as e:
                    raise CommandError(f"{e} Stories after {story.group_id} were not synced.") from e
                Story.objects.filter(pk=story.pk).update(audio_url=public_url(name), audio_seconds=seconds)
            uploaded.append(story.group_id)

        prefix = "Would upload" if dry_run else "Uploaded"
        self.stdout.write(self.style.SUCCESS(f"{prefix} {len(uploaded)} recordings, cleared {cleared}."))
        if missing:
            self.stdout.write(self.style.WARNING(f"No recording: {', '.join(missing)}"))
        if broken:
            self.stdout.write(self.style.ERROR(f"Unreadable recording: {', '.join(broken)}"))

    def _download(self, bucket, target):
        if not bucket:
            raise CommandError("Set GCS_AUDIO_BUCKET in .env or pass --bucket.")
        gcloud = shutil.which("gcloud")
        if gcloud is None:
            raise CommandError("gcloud is not installed. Download the bucket yourself and pass --source.")
        result = subprocess.run([gcloud, "storage", "cp", "-r", f"gs://{bucket}/*", str(target)], check=False)
        if result.returncode != 0:
            raise CommandError(f"gcloud storage cp failed with exit code {result.returncode}.")
