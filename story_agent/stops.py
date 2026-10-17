import json
from dataclasses import dataclass
from pathlib import Path

DEMO_LINES = Path("data/demo_lines.json")
MAX_DURATION_S = 45
MIN_DURATION_S = 20
MARGIN_S = 10
SAME_MINUTE_S = 30


@dataclass(frozen=True)
class DemoStop:
    group_id: str
    name: str
    lines: tuple[str, ...]
    target_duration_s: int


def _neighbour_gaps(data: dict) -> dict[str, list[int]]:
    gaps: dict[str, list[int]] = {}
    for line in data["lines"]:
        for direction in line["directions"]:
            stops = direction["stops"]
            for before, after in zip(stops, stops[1:], strict=False):
                seconds = (after["minutes"] - before["minutes"]) * 60 or SAME_MINUTE_S
                gaps.setdefault(before["group_id"], []).append(seconds)
                gaps.setdefault(after["group_id"], []).append(seconds)
    return gaps


def target_duration(gaps: list[int]) -> int:
    if not gaps:
        return MAX_DURATION_S
    return max(MIN_DURATION_S, min(MAX_DURATION_S, min(gaps) - MARGIN_S))


def demo_stops(path: Path = DEMO_LINES) -> dict[str, DemoStop]:
    data = json.loads(path.read_text(encoding="utf-8"))
    gaps = _neighbour_gaps(data)
    return {
        group["group_id"]: DemoStop(
            group_id=group["group_id"],
            name=group["name"],
            lines=tuple(group["lines"]),
            target_duration_s=target_duration(gaps.get(group["group_id"], [])),
        )
        for group in data["stop_groups"]
    }


def demo_stop(group_id: str, path: Path = DEMO_LINES) -> DemoStop:
    stops = demo_stops(path)
    if group_id not in stops:
        raise KeyError(f"stop group {group_id} is not in {path}")
    return stops[group_id]
