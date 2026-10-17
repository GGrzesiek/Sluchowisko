import shutil
import subprocess
from pathlib import Path

from django.conf import settings


class MediaError(Exception):
    pass


def base_url() -> str:
    bucket = settings.GCS_MEDIA_BUCKET
    return f"https://storage.googleapis.com/{bucket}" if bucket else ""


def is_media_url(url: str) -> bool:
    base = base_url()
    return bool(base) and url.startswith(f"{base}/")


def _gcloud(*args: str) -> None:
    gcloud = shutil.which("gcloud")
    if gcloud is None:
        raise MediaError("gcloud is not installed.")
    result = subprocess.run([gcloud, "storage", *args], check=False)
    if result.returncode != 0:
        raise MediaError(f"gcloud storage {args[0]} failed with exit code {result.returncode}.")


def upload(path: Path, object_name: str) -> str:
    if not settings.GCS_MEDIA_BUCKET:
        raise MediaError("Set GCS_MEDIA_BUCKET in .env.")
    _gcloud("cp", str(path), f"gs://{settings.GCS_MEDIA_BUCKET}/{object_name}")
    return f"{base_url()}/{object_name}"


def download(bucket: str, prefix: str, target: Path) -> None:
    if not bucket:
        raise MediaError("Set GCS_DATA_BUCKET in .env or pass --data-bucket.")
    target.mkdir(parents=True, exist_ok=True)
    _gcloud("rsync", "-r", f"gs://{bucket}/{prefix}", str(target))
