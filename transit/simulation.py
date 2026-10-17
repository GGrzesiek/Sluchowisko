import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

WARSAW = ZoneInfo("Europe/Warsaw")
DEFAULTS = {"trigger_radius_m": 60, "speedup": 1, "padding_s": 20}


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


def detect_passes(track: list[Reading], stops: list[dict], radius_m: float):
    start = track[0].time
    passes, missed = [], []
    cursor = 0
    for stop in stops:
        best = None
        for i in range(cursor, len(track) - 1):
            dist, u = _closest_on_segment(track[i], track[i + 1], stop["lat"], stop["lon"])
            if dist <= radius_m:
                if best is None or dist < best[0]:
                    best = (dist, i, u)
            elif best is not None:
                break
        if best is None:
            missed.append(stop)
            continue
        dist, i, u = best
        a, b = track[i], track[i + 1]
        t = (a.time - start).total_seconds() + u * (b.time - a.time).total_seconds()
        if passes:
            t = max(t, passes[-1].t)
        passes.append(Pass(stop=stop, t=t, distance_m=dist))
        cursor = i
    return passes, missed


def best_match(tracks: dict[str, list[Reading]], directions: list[dict], radius_m: float) -> Match | None:
    best = None
    for vehicle, track in sorted(tracks.items()):
        for direction in directions:
            passes, missed = detect_passes(track, direction["stops"], radius_m)
            if not passes:
                continue
            match = Match(vehicle, direction, track, passes, missed)
            if best is None or len(match.passes) > len(best.passes):
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
                "type": "passStop",
                "groupId": p.stop["group_id"],
                "pole": p.stop["pole"],
                "name": p.stop["name"],
                "distanceM": round(p.distance_m),
            }
            for p in match.passes
        ],
    }
