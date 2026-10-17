import json
from pathlib import Path

from pydantic import BaseModel

OUT = Path("out")
CACHE = Path("cache")


def collected_path(group_id: str) -> Path:
    return OUT / "collected" / f"{group_id}.json"


def extra_path(group_id: str) -> Path:
    return OUT / "collected" / f"{group_id}.extra.json"


def plan_path(group_id: str) -> Path:
    return OUT / "plans" / f"{group_id}.json"


def script_path(group_id: str) -> Path:
    return OUT / "scripts" / f"{group_id}.json"


def voiced_path(group_id: str) -> Path:
    return OUT / "voiced" / f"{group_id}.json"


def audio_path(group_id: str) -> Path:
    return OUT / "audio" / f"{group_id}.mp3"


def timeline_path(group_id: str) -> Path:
    return OUT / "audio" / f"{group_id}.timeline.json"


def record_path(group_id: str) -> Path:
    return OUT / "stories" / f"{group_id}.json"


def check_path(group_id: str, stage: str) -> Path:
    return OUT / "checks" / f"{group_id}.{stage}.json"


def write_json(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_model[M: BaseModel](model: type[M], path: Path) -> M:
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist yet")
    return model.model_validate_json(path.read_text(encoding="utf-8"))
