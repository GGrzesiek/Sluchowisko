from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .config import LineCfg, read_json, write_json
from .geo import haversine_m


def load_tracks(recording: Path) -> dict[str, list[dict]]:
    points: dict[str, dict[str, tuple[float, float]]] = defaultdict(dict)
    with recording.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            for v in json.loads(line).get("vehicles", []):
                try:
                    points[str(v["VehicleNumber"])][v["Time"]] = (float(v["Lat"]), float(v["Lon"]))
                except (KeyError, TypeError, ValueError):
                    continue
    return {
        vehicle: [{"time": t, "lat": la, "lon": lo} for t, (la, lo) in sorted(pts.items())]
        for vehicle, pts in points.items()
    }


def detect_arrivals(track: list[dict], stops: list[dict], radius_m: float, lookahead: int = 2) -> list[dict]:
    events: list[dict] = []
    next_stop = 0
    for p in track:
        if next_stop >= len(stops):
            break
        candidates = range(len(stops)) if not events else range(next_stop, min(next_stop + 1 + lookahead, len(stops)))
        for j in candidates:
            if haversine_m(p["lat"], p["lon"], stops[j]["lat"], stops[j]["lon"]) <= radius_m:
                events.append({"time": p["time"], "stop_index": j})
                next_stop = j + 1
                break
    return events


def _seconds(t: str, t0: str) -> float:
    return (datetime.fromisoformat(t) - datetime.fromisoformat(t0)).total_seconds()


def build_ride(route: dict, tracks: dict[str, list[dict]], radius_m: float) -> dict:
    stops = route["stops"]
    best_vehicle, best_events = None, []
    for vehicle, track in tracks.items():
        events = detect_arrivals(track, stops, radius_m)
        if len(events) > len(best_events):
            best_vehicle, best_events = vehicle, events
    if len(best_events) < 2:
        raise RuntimeError(
            "No vehicle in the recording passed at least 2 stops of the route. "
            "Record longer or check the line and direction."
        )

    track = tracks[best_vehicle]
    t0, t_end = best_events[0]["time"], best_events[-1]["time"]
    points = [p for p in track if t0 <= p["time"] <= t_end]
    return {
        "line": route["line"],
        "slug": route["slug"],
        "vehicle": best_vehicle,
        "started_at": t0,
        "duration_s": _seconds(t_end, t0),
        "points": [{"t": _seconds(p["time"], t0), "lat": p["lat"], "lon": p["lon"]} for p in points],
        "events": [
            {
                "t": _seconds(e["time"], t0),
                "type": "arrive",
                "stop_order": stops[e["stop_index"]]["order"],
                "stop_slug": stops[e["stop_index"]]["slug"],
                "stop_name": stops[e["stop_index"]]["name"],
                "story": stops[e["stop_index"]].get("story", False),
            }
            for e in best_events
        ],
    }


def simulate(line: LineCfg, recording: Path) -> Path:
    route = read_json(line.out_dir / "route.json")
    ride = build_ride(route, load_tracks(recording), line.trigger_radius_m)
    out = write_json(line.out_dir / "ride.json", ride)
    print(f"Vehicle {ride['vehicle']}: {len(ride['events'])} stops, {ride['duration_s'] / 60:.1f} min → {out}")
    return out
