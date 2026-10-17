import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

WARSAW = ZoneInfo("Europe/Warsaw")
DEFAULTS = {"trigger_radius_m": 60, "speedup": 10, "padding_s": 20}
MAX_GAP_FACTOR = 3
MAX_GAP_SLACK_S = 120


@dataclass
class Reading:
    vehicle: str
    line: str
    brigade: str
    time: datetime
    lat: float
    lon: float


@dataclass
class Pass:
    stop: dict
    t: float
    distance_m: float


@dataclass
class Match:
    vehicle: str
    direction: dict
    track: list
    passes: list[Pass] = field(default_factory=list)
    missed: list[dict] = field(default_factory=list)


def load_config(line: str, path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    lines = data.get("lines") or {}
    return {**DEFAULTS, **(data.get("defaults") or {}), **(lines.get(str(line)) or {})}


def _rows(record):
    if isinstance(record, list):
        for item in record:
            yield from _rows(item)
    elif isinstance(record, dict):
        for key in ("result", "data", "positions"):
            if isinstance(record.get(key), list):
                yield from _rows(record[key])
                return
        yield record


def _reading(row) -> Reading | None:
    try:
        lat, lon = float(row.get("Lat", row.get("lat"))), float(row.get("Lon", row.get("lon")))
        raw_time = str(row.get("Time", row.get("time")))
        time = datetime.fromisoformat(raw_time.replace(" ", "T"))
        if time.tzinfo is None:
            time = time.replace(tzinfo=WARSAW)
        return Reading(
            vehicle=str(row.get("VehicleNumber", row.get("vehicle_number"))).strip(),
            line=str(row.get("Lines", row.get("line"))).strip(),
            brigade=str(row.get("Brigade", row.get("brigade")) or "").strip(),
            time=time,
            lat=lat,
            lon=lon,
        )
    except (TypeError, ValueError):
        return None


def read_recording(path: Path) -> list[Reading]:
    readings = []
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                continue
            for row in _rows(record):
                reading = _reading(row)
                if reading and reading.lat and reading.lon:
                    readings.append(reading)
    return readings


def tracks_by_vehicle(readings: list[Reading], line: str) -> dict[str, list[Reading]]:
    tracks: dict[str, dict[datetime, Reading]] = {}
    for r in readings:
        if r.line == str(line):
            tracks.setdefault(r.vehicle, {})[r.time] = r
    return {v: sorted(points.values(), key=lambda r: r.time) for v, points in tracks.items() if len(points) > 1}


def _closest_on_segment(a: Reading, b: Reading, lat: float, lon: float):
    k = 111_320 * math.cos(math.radians(lat))
    ax, ay = (a.lon - lon) * k, (a.lat - lat) * 111_320
    bx, by = (b.lon - lon) * k, (b.lat - lat) * 111_320
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    u = 0.0 if seg2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / seg2))
    return math.hypot(ax + u * dx, ay + u * dy), u


def merge_groups(stops: list[dict]) -> list[dict]:
    groups: list[dict] = []
    for stop in stops:
        poles = stop.get("poles") or [{"pole": stop.get("pole"), "lat": stop["lat"], "lon": stop["lon"]}]
        if groups and groups[-1]["group_id"] == stop.get("group_id"):
            groups[-1]["poles"] += poles
            continue
        groups.append(
            {
                "group_id": stop.get("group_id"),
                "name": stop["name"],
                "minutes": stop.get("minutes"),
                "poles": list(poles),
            }
        )
    return groups


def _approaches(track: list[Reading], group: dict, radius_m: float) -> list[Pass]:
    start = track[0].time
    found, best = [], None
    for i in range(len(track) - 1):
        a, b = track[i], track[i + 1]
        dist, u, pole = min((*_closest_on_segment(a, b, p["lat"], p["lon"]), p["pole"]) for p in group["poles"])
        if dist <= radius_m:
            if best is None or dist < best[0]:
                t = (a.time - start).total_seconds() + u * (b.time - a.time).total_seconds()
                best = (dist, t, pole)
        elif best is not None:
            found.append(best)
            best = None
    if best is not None:
        found.append(best)
    stop = {"group_id": group["group_id"], "name": group["name"]}
    return [Pass(stop={**stop, "pole": pole}, t=t, distance_m=dist) for dist, t, pole in found]


def _max_gap_s(earlier: dict, later: dict) -> float:
    if earlier.get("minutes") is None or later.get("minutes") is None:
        return math.inf
    return MAX_GAP_FACTOR * max(0, later["minutes"] - earlier["minutes"]) * 60 + MAX_GAP_SLACK_S


def detect_passes(track: list[Reading], stops: list[dict], radius_m: float):
    groups = merge_groups(stops)
    candidates = [_approaches(track, g, radius_m) for g in groups]
    best: dict[tuple[int, int], tuple] = {}
    for g, cands in enumerate(candidates):
        for c, cand in enumerate(cands):
            chain = ((1, 0.0, cand.distance_m), cand.t, None)
            for h in range(g):
                for d, prev in enumerate(candidates[h]):
                    if (h, d) not in best or not 0 <= cand.t - prev.t <= _max_gap_s(groups[h], groups[g]):
                        continue
                    (count, _, dist_sum), first_t, _ = best[(h, d)]
                    score = (count + 1, cand.t - first_t, dist_sum + cand.distance_m)
                    if _better(score, chain[0]):
                        chain = (score, first_t, (h, d))
            best[(g, c)] = chain
    if not best:
        return [], groups
    key = max(best, key=lambda k: (best[k][0][0], -best[k][0][1], -best[k][0][2]))
    chosen = []
    while key is not None:
        chosen.append(key)
        key = best[key][2]
    chosen.reverse()
    passes = [candidates[g][c] for g, c in chosen]
    matched = {g for g, _ in chosen}
    return passes, [groups[g] for g in range(len(groups)) if g not in matched]


def _better(score, other) -> bool:
    return (score[0], -score[1], -score[2]) > (other[0], -other[1], -other[2])


def _duration(passes: list[Pass]) -> float:
    return passes[-1].t - passes[0].t if passes else math.inf


def best_match(tracks: dict[str, list[Reading]], directions: list[dict], radius_m: float) -> Match | None:
    best = None
    for vehicle, track in sorted(tracks.items()):
        for direction in directions:
            passes, missed = detect_passes(track, direction["stops"], radius_m)
            if not passes:
                continue
            match = Match(vehicle, direction, track, passes, missed)
            if best is None or (len(passes), -_duration(passes)) > (len(best.passes), -_duration(best.passes)):
                best = match
    return best


def _interpolate(track: list[Reading], t: float) -> tuple[float, float]:
    start = track[0].time
    for a, b in zip(track, track[1:], strict=False):
        ta, tb = (a.time - start).total_seconds(), (b.time - start).total_seconds()
        if ta <= t <= tb:
            u = 0.0 if tb == ta else (t - ta) / (tb - ta)
            return a.lat + u * (b.lat - a.lat), a.lon + u * (b.lon - a.lon)
    last = track[0] if t < 0 else track[-1]
    return last.lat, last.lon


def build_ride(match: Match, line: str, config: dict) -> dict:
    track = match.track
    start = track[0].time
    times = [(r.time - start).total_seconds() for r in track]
    window_start = max(0.0, match.passes[0].t - config["padding_s"])
    window_end = min(times[-1], match.passes[-1].t + config["padding_s"])

    points = [(window_start, *_interpolate(track, window_start))]
    points += [(t, r.lat, r.lon) for t, r in zip(times, track, strict=True) if window_start < t < window_end]
    points.append((window_end, *_interpolate(track, window_end)))

    recorded_at = start.astimezone(WARSAW).replace(microsecond=0) + timedelta(seconds=round(window_start))
    return {
        "line": str(line),
        "vehicle": match.vehicle,
        "brigade": track[0].brigade,
        "direction": {"from": match.direction["from"], "to": match.direction["to"]},
        "recordedAt": recorded_at.isoformat(),
        "durationS": round(window_end - window_start, 1),
        "speedup": config["speedup"],
        "triggerRadiusM": config["trigger_radius_m"],
        "points": [
            {"t": round(t - window_start, 1), "lat": round(lat, 6), "lon": round(lon, 6)} for t, lat, lon in points
        ],
        "events": [
            {
                "t": round(p.t - window_start, 1),
                "type": "arrive",
                "groupId": p.stop["group_id"],
                "pole": p.stop["pole"],
                "name": p.stop["name"],
                "distanceM": round(p.distance_m),
            }
            for p in match.passes
        ],
    }
