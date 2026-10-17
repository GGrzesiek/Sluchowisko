import math
import mimetypes
import os
import shutil
import subprocess
from pathlib import Path

import mutagen

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".ogg", ".opus", ".wav")


def find_recordings(source: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS or not path.stem.isdigit():
            continue
        current = found.get(path.stem)
        if current is None or AUDIO_EXTENSIONS.index(path.suffix.lower()) < AUDIO_EXTENSIONS.index(
            current.suffix.lower()
        ):
            found[path.stem] = path
    return found


def duration_seconds(path: Path) -> int:
    audio = mutagen.File(path)
    if audio is None or not getattr(audio.info, "length", 0):
        raise ValueError(f"{path} is not a readable audio file")
    return max(1, math.floor(audio.info.length + 0.5))


MEDIA_BUCKET = os.getenv("GCS_MEDIA_BUCKET", "muzeum-w-autobusie-2026-media")


def object_name(group_id: str, suffix: str) -> str:
    return f"audio/{group_id}{suffix.lower()}"


def public_url(name: str) -> str:
    return f"https://storage.googleapis.com/{MEDIA_BUCKET}/{name}"


class UploadError(RuntimeError):
    pass


def upload_public(path: Path, name: str) -> str:
    gcloud = shutil.which("gcloud")
    if gcloud is None:
        raise UploadError("gcloud is not installed.")
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    command = [
        gcloud,
        "storage",
        "cp",
        f"--content-type={content_type}",
        "--cache-control=no-cache",
        str(path),
        f"gs://{MEDIA_BUCKET}/{name}",
    ]
    if subprocess.run(command, check=False).returncode != 0:
        raise UploadError(f"Upload of {path.name} to gs://{MEDIA_BUCKET}/{name} failed.")
    return public_url(name)
