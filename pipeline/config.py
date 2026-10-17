from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_LINE = ROOT / "config" / "line.yaml"

load_dotenv(ROOT / ".env")


class ConfigError(RuntimeError):
    pass


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.getenv(name) or default
    if required and not value:
        raise ConfigError(f"Missing variable {name}: set it in .env (see .env.example)")
    return value


@dataclass
class StopCfg:
    name: str
    story: bool = False


@dataclass
class LineCfg:
    slug: str
    line: str
    vehicle_type: int
    origin: str
    destination: str
    stops: list[StopCfg] = field(default_factory=list)
    trigger_radius_m: float = 150.0

    @property
    def raw_dir(self) -> Path:
        return DATA / "raw" / self.slug

    @property
    def out_dir(self) -> Path:
        return DATA / "processed" / self.slug

    @property
    def sources_dir(self) -> Path:
        return DATA / "sources" / self.slug


def load_line(path: Path | str = DEFAULT_LINE) -> LineCfg:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    stops = [StopCfg(**s) if isinstance(s, dict) else StopCfg(name=str(s)) for s in raw["stops"]]
    return LineCfg(
        slug=raw["slug"],
        line=str(raw["line"]),
        vehicle_type=int(raw["vehicle_type"]),
        origin=raw["origin"],
        destination=raw["destination"],
        stops=stops,
        trigger_radius_m=float(raw.get("trigger_radius_m", 150)),
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
