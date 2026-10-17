import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from transit.models import Stop
from transit.simulation import best_match, build_ride, load_config, merge_groups, read_recording, tracks_by_vehicle


def _line_from_path(path: Path) -> str | None:
    parts = path.parts
    if "raw" in parts and parts.index("raw") + 1 < len(parts) - 1:
        return parts[parts.index("raw") + 1]
    return None


def _with_coords(stops: list[dict]) -> list[dict]:
    out, missing = [], []
    for stop in stops:
        pole = Stop.objects.filter(zespol=stop["group_id"], slupek=stop["pole"]).first()
        if pole is None:
            missing.append(f"{stop['name']} {stop['group_id']}/{stop['pole']}")
            continue
        out.append({**stop, "lat": pole.lat, "lon": pole.lon})
    if missing:
        raise CommandError(f"Poles missing from the stops table: {', '.join(missing)}. Run sync_city_data.")
    return out


class Command(BaseCommand):
    help = "Turn a recorded positions .jsonl file into ride.json (vehicle points over time and passed stops)."

    def add_arguments(self, parser):
        parser.add_argument("recording")
        parser.add_argument("--line")
        parser.add_argument("--vehicle")
        parser.add_argument("--radius", type=float)
        parser.add_argument("--out")
        parser.add_argument("--config", default=str(settings.BASE_DIR / "config" / "line.yaml"))
        parser.add_argument("--demo-lines", default=str(settings.BASE_DIR / "data" / "demo_lines.json"))

    def handle(self, *args, **opts):
        recording = Path(opts["recording"])
        if not recording.exists():
            raise CommandError(f"No such file: {recording}")
        line = opts["line"] or _line_from_path(recording)
        if not line:
            raise CommandError("Cannot tell the line from the path. Pass --line.")

        demo = json.loads(Path(opts["demo_lines"]).read_text(encoding="utf-8"))
        entry = next((item for item in demo["lines"] if str(item["line"]) == str(line)), None)
        if entry is None:
            raise CommandError(f"Line {line} is not in {opts['demo_lines']}.")
        directions = [{**d, "stops": _with_coords(d["stops"])} for d in entry["directions"]]

        config = load_config(line, Path(opts["config"]))
        if opts["radius"] is not None:
            config["trigger_radius_m"] = opts["radius"]

        tracks = tracks_by_vehicle(read_recording(recording), line)
        if opts["vehicle"]:
            tracks = {k: v for k, v in tracks.items() if k == opts["vehicle"]}
        if not tracks:
            raise CommandError(f"No positions of line {line} in {recording}.")

        match = best_match(tracks, directions, config["trigger_radius_m"])
        if match is None:
            raise CommandError(
                f"No vehicle passed any stop of the segment within {config['trigger_radius_m']} m. "
                "Increase trigger_radius_m in config/line.yaml."
            )

        ride = build_ride(match, line, config)
        out = Path(opts["out"] or settings.BASE_DIR / "web" / "public" / "rides" / f"{line}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(ride, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        groups = merge_groups(match.direction["stops"])
        first, last = match.passes[0].stop["group_id"], match.passes[-1].stop["group_id"]
        minutes = {g["group_id"]: g.get("minutes") for g in groups}
        expected = ""
        if minutes.get(first) is not None and minutes.get(last) is not None:
            expected = f" (timetable {(minutes[last] - minutes[first]) * 60} s + {2 * config['padding_s']} s padding)"
        self.stdout.write(
            self.style.SUCCESS(
                f"Vehicle {match.vehicle}, {match.direction['from']} -> {match.direction['to']}: "
                f"{len(match.passes)}/{len(groups)} stop groups, {ride['durationS']} s{expected} -> {out}"
            )
        )
        if match.missed:
            names = ", ".join(g["name"] for g in match.missed)
            self.stdout.write(
                self.style.WARNING(f"Missed: {names}. Increase trigger_radius_m in config/line.yaml or pass --radius.")
            )
