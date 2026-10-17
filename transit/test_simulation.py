import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import CommandError, call_command
from django.test import TestCase

from transit.models import Stop
from transit.simulation import detect_passes, load_config, merge_groups, read_recording, tracks_by_vehicle

STOPS = [("7001", "01", "Alfa", 52.2000), ("7002", "01", "Beta", 52.2050), ("7003", "01", "Gamma", 52.2100)]
STEP = 0.0008


def row(vehicle, lat, second, lon=21.0, line="22"):
    return {
        "Lines": line,
        "VehicleNumber": vehicle,
        "Brigade": "5",
        "Lat": lat,
        "Lon": lon,
        "Time": f"2026-10-17 {8 + second // 3600:02d}:{second // 60 % 60:02d}:{second % 60:02d}",
    }


def drive(vehicle, start_lat, steps, start_s=0, step=STEP, lon=21.0, every_s=10):
    return [row(vehicle, start_lat + i * step, start_s + i * every_s, lon) for i in range(steps)]


def drive_north(vehicle="1001", lon=21.0, start_s=0):
    return drive(vehicle, 52.1980, 20, start_s, lon=lon)


class TmpDirTestCase(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)


class SimulateRideTest(TmpDirTestCase):
    def setUp(self):
        super().setUp()
        for group_id, pole, name, lat in STOPS:
            Stop.objects.create(zespol=group_id, slupek=pole, name=name, lat=lat, lon=21.0)
            Stop.objects.create(zespol=group_id, slupek="02", name=name, lat=lat, lon=21.0004)
        north = [{"group_id": g, "pole": p, "name": n, "minutes": i} for i, (g, p, n, _) in enumerate(STOPS)]
        south = [{**s, "pole": "02", "minutes": 2 - s["minutes"]} for s in reversed(north)]
        self.write_demo(
            [{"from": "Alfa", "to": "Gamma", "stops": north}, {"from": "Gamma", "to": "Alfa", "stops": south}]
        )
        self.config = self.tmp / "line.yaml"
        self.config.write_text('defaults:\n  trigger_radius_m: 30\n  padding_s: 10\nlines:\n  "22":\n    speedup: 4\n')

    def write_demo(self, directions):
        self.demo = self.tmp / "demo_lines.json"
        self.demo.write_text(json.dumps({"lines": [{"line": "22", "directions": directions}]}))

    def record(self, records):
        path = self.tmp / "raw" / "22" / "positions-test.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        return path

    def run_command(self, path, *extra):
        out = self.tmp / "ride.json"
        args = [str(path), "--out", str(out), "--config", str(self.config), "--demo-lines", str(self.demo)]
        call_command("simulate_ride", *args, *extra, stdout=StringIO())
        return json.loads(out.read_text())

    def test_builds_ride_with_arrive_events(self):
        noise = [row("2002", 52.30, i * 10) for i in range(5)] + [row("3003", 52.20, 0, line="9")]
        records = [{"result": drive_north()[:10]}] + drive_north()[10:] + noise + [drive_north()[3]]
        ride = self.run_command(self.record(records))
        self.assertEqual((ride["line"], ride["vehicle"], ride["speedup"]), ("22", "1001", 4))
        self.assertEqual(ride["direction"], {"from": "Alfa", "to": "Gamma"})
        self.assertEqual(
            [(e["type"], e["name"]) for e in ride["events"]], [("arrive", n) for n in ("Alfa", "Beta", "Gamma")]
        )
        times = [e["t"] for e in ride["events"]]
        self.assertEqual(times, sorted(times))
        self.assertAlmostEqual(times[0], 10, delta=2)
        self.assertEqual(ride["points"][0]["t"], 0)
        self.assertAlmostEqual(ride["points"][-1]["t"], ride["durationS"], delta=0.1)
        self.assertEqual(ride["recordedAt"], "2026-10-17T08:00:15+02:00")

    def test_first_stop_from_an_earlier_pass_is_not_used(self):
        early = drive("1001", 52.1990, 4)
        away = drive("1001", 52.1960, 240, start_s=40, step=-0.00001)
        trip = drive_north(start_s=40 * 60)
        ride = self.run_command(self.record(early + away + trip))
        self.assertEqual([e["name"] for e in ride["events"]], ["Alfa", "Beta", "Gamma"])
        self.assertLess(ride["durationS"], 200)

    def test_opposite_pole_long_before_the_trip_is_ignored(self):
        opposite = drive("1001", 52.2010, 3, step=-STEP, lon=21.0004)
        trip = drive_north(start_s=35 * 60)
        ride = self.run_command(self.record(opposite + trip))
        self.assertEqual(ride["direction"]["to"], "Gamma")
        self.assertEqual([e["pole"] for e in ride["events"]], ["01", "01", "01"])
        self.assertLess(ride["durationS"], 3 * 60)

    def test_picks_direction_from_movement(self):
        south = drive("1001", 52.2120, 20, step=-STEP, lon=21.0004)
        ride = self.run_command(self.record(south))
        self.assertEqual(ride["direction"]["to"], "Alfa")
        self.assertEqual([e["name"] for e in ride["events"]], ["Gamma", "Beta", "Alfa"])

    def test_tie_goes_to_shorter_clip(self):
        slow = drive("1000", 52.1980, 40, every_s=20, step=STEP / 2)
        fast = drive_north("2000")
        ride = self.run_command(self.record(slow + fast))
        self.assertEqual(ride["vehicle"], "2000")

    def test_two_poles_of_one_group_give_one_event(self):
        Stop.objects.create(zespol="7002", slupek="05", name="Beta", lat=52.2056, lon=21.0)
        stops = [
            {"group_id": "7001", "pole": "01", "name": "Alfa", "minutes": 0},
            {"group_id": "7002", "pole": "01", "name": "Beta", "minutes": 1},
            {"group_id": "7002", "pole": "05", "name": "Beta", "minutes": 1},
            {"group_id": "7003", "pole": "01", "name": "Gamma", "minutes": 2},
        ]
        self.write_demo([{"from": "Alfa", "to": "Gamma", "stops": stops}])
        ride = self.run_command(self.record(drive_north()))
        self.assertEqual([e["name"] for e in ride["events"]], ["Alfa", "Beta", "Gamma"])

    def test_missed_stop_and_radius(self):
        Stop.objects.filter(zespol="7002", slupek="01").update(lon=21.0010)
        ride = self.run_command(self.record(drive_north()))
        self.assertEqual([e["name"] for e in ride["events"]], ["Alfa", "Gamma"])
        ride = self.run_command(self.record(drive_north()), "--radius", "100")
        self.assertEqual([e["name"] for e in ride["events"]], ["Alfa", "Beta", "Gamma"])
        with self.assertRaises(CommandError):
            self.run_command(self.record(drive_north(lon=21.00005)), "--radius", "0")

    def test_missing_pole_fails(self):
        Stop.objects.filter(zespol="7002", slupek="01").delete()
        with self.assertRaisesMessage(CommandError, "Beta 7002/01"):
            self.run_command(self.record(drive_north()))

    def test_errors(self):
        with self.assertRaises(CommandError):
            self.run_command(self.record([row("1001", 52.5, 0), row("1001", 52.51, 10)]))
        with self.assertRaises(CommandError):
            self.run_command(self.record(drive_north()), "--line", "99")


class SimulationUnitTest(TmpDirTestCase):
    def write(self, text):
        path = self.tmp / "rec.jsonl"
        path.write_text(text)
        return read_recording(path)

    def test_reads_api_rows_and_dedupes(self):
        text = json.dumps([row("1", 52.2, 0), row("1", 52.2, 0)]) + "\nnot json\n"
        text += json.dumps({"result": [row("1", 52.21, 10), {"Lines": "22"}]}) + "\n"
        self.assertEqual(len(tracks_by_vehicle(self.write(text), "22")["1"]), 2)

    def test_pass_between_samples_is_interpolated(self):
        readings = self.write("\n".join(json.dumps(r) for r in [row("1", 52.199, 0), row("1", 52.201, 10)]))
        track = tracks_by_vehicle(readings, "22")["1"]
        passes, missed = detect_passes(track, [{"name": "A", "lat": 52.2, "lon": 21.0}], 20)
        self.assertAlmostEqual(passes[0].t, 5, delta=0.1)
        self.assertEqual(missed, [])

    def test_merge_groups_keeps_order(self):
        stops = [
            {"group_id": "1", "pole": "01", "name": "A", "lat": 0, "lon": 0},
            {"group_id": "2", "pole": "01", "name": "B", "lat": 0, "lon": 0},
            {"group_id": "2", "pole": "03", "name": "B", "lat": 0, "lon": 0},
        ]
        self.assertEqual([(g["group_id"], len(g["poles"])) for g in merge_groups(stops)], [("1", 1), ("2", 2)])

    def test_config_defaults(self):
        self.assertEqual(load_config("22", Path("/nonexistent.yaml"))["trigger_radius_m"], 60)
