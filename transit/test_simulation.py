import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase

from transit.models import Stop
from transit.simulation import detect_passes, load_config, read_recording, tracks_by_vehicle

STOPS = [("7001", "01", "Alfa", 52.2000), ("7002", "01", "Beta", 52.2050), ("7003", "01", "Gamma", 52.2100)]


def row(vehicle, lat, second, lon=21.0, line="22"):
    return {
        "Lines": line,
        "VehicleNumber": vehicle,
        "Brigade": "5",
        "Lat": lat,
        "Lon": lon,
        "Time": f"2026-10-17 08:{second // 60:02d}:{second % 60:02d}",
    }


def drive_north(vehicle="1001", lon=21.0):
    return [row(vehicle, 52.1980 + i * 0.0008, i * 10, lon) for i in range(20)]


class SimulateRideTest(TestCase):
    def setUp(self):
        for group_id, pole, name, lat in STOPS:
            Stop.objects.create(zespol=group_id, slupek=pole, name=name, lat=lat, lon=21.0)
            Stop.objects.create(zespol=group_id, slupek="02", name=name, lat=lat, lon=21.0004)
        self.tmp = Path(tempfile.mkdtemp())
        north = [{"group_id": g, "pole": p, "name": n, "minutes": i} for i, (g, p, n, _) in enumerate(STOPS)]
        south = [{**s, "pole": "02"} for s in reversed(north)]
        demo = {
            "lines": [
                {
                    "line": "22",
                    "directions": [
                        {"from": "Alfa", "to": "Gamma", "stops": north},
                        {"from": "Gamma", "to": "Alfa", "stops": south},
                    ],
                }
            ]
        }
        self.demo = self.tmp / "demo_lines.json"
        self.demo.write_text(json.dumps(demo))
        self.config = self.tmp / "line.yaml"
        self.config.write_text('defaults:\n  trigger_radius_m: 30\n  padding_s: 10\nlines:\n  "22":\n    speedup: 4\n')

    def record(self, records):
        path = self.tmp / "raw" / "22" / "positions-test.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        return path

    def run_command(self, path, *extra):
        out = self.tmp / "ride.json"
        args = [str(path), "--out", str(out), "--config", str(self.config), "--demo-lines", str(self.demo)]
        call_command("simulate_ride", *args, *extra, verbosity=0, stdout=StringIO())
        return json.loads(out.read_text())

    def test_builds_ride_with_passed_stops(self):
        noise = [row("2002", 52.30, i * 10) for i in range(5)] + [row("3003", 52.20, 0, line="9")]
        records = [{"result": drive_north()[:10]}] + drive_north()[10:] + noise + [drive_north()[3]]
        ride = self.run_command(self.record(records))
        self.assertEqual(ride["line"], "22")
        self.assertEqual(ride["vehicle"], "1001")
        self.assertEqual(ride["direction"], {"from": "Alfa", "to": "Gamma"})
        self.assertEqual(ride["speedup"], 4)
        self.assertEqual([e["name"] for e in ride["events"]], ["Alfa", "Beta", "Gamma"])
        times = [e["t"] for e in ride["events"]]
        self.assertEqual(times, sorted(times))
        self.assertAlmostEqual(times[0], 10, delta=2)
        self.assertEqual(ride["points"][0]["t"], 0)
        self.assertAlmostEqual(ride["points"][-1]["t"], ride["durationS"], delta=0.1)
        self.assertEqual(ride["recordedAt"], "2026-10-17T08:00:15+02:00")

    def test_line_comes_from_path_and_picks_direction(self):
        south = [row("1001", 52.2120 - i * 0.0008, i * 10, lon=21.0004) for i in range(20)]
        ride = self.run_command(self.record(south))
        self.assertEqual(ride["direction"]["to"], "Alfa")
        self.assertEqual([e["name"] for e in ride["events"]], ["Gamma", "Beta", "Alfa"])

    def test_missed_stop_and_radius(self):
        Stop.objects.filter(zespol="7002", slupek="01").update(lon=21.0010)
        ride = self.run_command(self.record(drive_north()))
        self.assertEqual([e["name"] for e in ride["events"]], ["Alfa", "Gamma"])
        ride = self.run_command(self.record(drive_north()), "--radius", "100")
        self.assertEqual([e["name"] for e in ride["events"]], ["Alfa", "Beta", "Gamma"])

    def test_errors(self):
        with self.assertRaises(CommandError):
            self.run_command(self.record([row("1001", 52.5, 0), row("1001", 52.51, 10)]))
        with self.assertRaises(CommandError):
            self.run_command(self.record(drive_north()), "--line", "99")


class SimulationUnitTest(TestCase):
    def test_reads_api_rows_and_dedupes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write(json.dumps([row("1", 52.2, 0), row("1", 52.2, 0)]) + "\nnot json\n")
            fh.write(json.dumps({"result": [row("1", 52.21, 10), {"Lines": "22"}]}) + "\n")
        tracks = tracks_by_vehicle(read_recording(Path(fh.name)), "22")
        self.assertEqual(len(tracks["1"]), 2)

    def test_pass_between_samples_is_interpolated(self):
        track = tracks_by_vehicle(read_recording_rows([row("1", 52.199, 0), row("1", 52.201, 10)]), "22")["1"]
        passes, missed = detect_passes(track, [{"name": "A", "lat": 52.2, "lon": 21.0}], 20)
        self.assertAlmostEqual(passes[0].t, 5, delta=0.1)
        self.assertEqual(missed, [])

    def test_config_defaults(self):
        self.assertEqual(load_config("22", Path("/nonexistent.yaml"))["trigger_radius_m"], 60)


def read_recording_rows(rows):
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        fh.write("\n".join(json.dumps(r) for r in rows))
    return read_recording(Path(fh.name))
