import json

import pytest

from pipeline.simulate import build_ride, detect_arrivals, load_tracks

STOPS = [
    {
        "order": i + 1,
        "slug": f"s{i + 1}",
        "name": f"S{i + 1}",
        "lat": 52.0 + 0.005 * i,
        "lon": 21.0,
        "story": i == 1,
    }
    for i in range(3)
]
ROUTE = {"line": "4", "slug": "tram-4", "stops": STOPS}


def _track(lats, start_s=0):
    return [
        {
            "time": f"2026-10-16 07:{(start_s + 10 * i) // 60:02d}:{(start_s + 10 * i) % 60:02d}",
            "lat": lat,
            "lon": 21.0,
        }
        for i, lat in enumerate(lats)
    ]


def test_arrivals_in_route_direction():
    track = _track([52.0 + 0.001 * i for i in range(12)])
    events = detect_arrivals(track, STOPS, radius_m=100)
    assert [e["stop_index"] for e in events] == [0, 1, 2]


def test_opposite_direction_catches_at_most_one_stop():
    track = _track([52.011 - 0.001 * i for i in range(12)])
    assert len(detect_arrivals(track, STOPS, radius_m=100)) <= 1


def test_vehicle_starting_mid_route():
    track = _track([52.004 + 0.001 * i for i in range(8)])
    assert [e["stop_index"] for e in detect_arrivals(track, STOPS, 100)] == [1, 2]


def _write_recording(path, tracks):
    snapshots = max(len(t) for t in tracks.values())
    with path.open("w", encoding="utf-8") as f:
        for i in range(snapshots):
            vehicles = [
                {
                    "VehicleNumber": v,
                    "Lines": "4",
                    "Lat": t[i]["lat"],
                    "Lon": t[i]["lon"],
                    "Time": t[i]["time"],
                }
                for v, t in tracks.items()
                if i < len(t)
            ]
            f.write(json.dumps({"vehicles": vehicles}) + "\n")


def test_build_ride_picks_vehicle_covering_route(tmp_path):
    rec = tmp_path / "rec.jsonl"
    _write_recording(
        rec,
        {
            "1001": _track([52.0 + 0.001 * i for i in range(12)]),
            "2002": _track([52.011 - 0.001 * i for i in range(12)]),
        },
    )
    ride = build_ride(ROUTE, load_tracks(rec), radius_m=100)
    assert ride["vehicle"] == "1001"
    assert [e["stop_slug"] for e in ride["events"]] == ["s1", "s2", "s3"]
    assert ride["events"][0]["t"] == 0
    assert ride["events"][1]["story"] is True
    assert ride["duration_s"] == 100


def test_build_ride_fails_without_movement(tmp_path):
    rec = tmp_path / "rec.jsonl"
    _write_recording(rec, {"1001": _track([52.0] * 5)})
    with pytest.raises(RuntimeError):
        build_ride(ROUTE, load_tracks(rec), radius_m=100)
