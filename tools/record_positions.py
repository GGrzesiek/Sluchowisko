import argparse
import gzip
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

API_URL = "https://dane.um.warszawa.pl/api/action/get_ztm_lokalizacja_pojazdow"
VEHICLE_TYPES = {1: "bus", 2: "tram"}
WARSAW = ZoneInfo("Europe/Warsaw")
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
ALL_DIR = RAW_DIR / "all"
DEMO_LINES = ROOT / "data" / "demo_lines.json"


def load_api_key() -> str:
    key = os.environ.get("ZTM_API_KEY", "").strip()
    env_file = ROOT / ".env"
    if not key and env_file.exists():
        for line in env_file.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "ZTM_API_KEY":
                key = value.strip().strip("\"'")
    if not key:
        sys.exit("ZTM_API_KEY is not set. Copy .env.example to .env and fill it in.")
    return key


def fetch(key: str, vehicle_type: int) -> list[dict]:
    request = urllib.request.Request(
        API_URL,
        data=json.dumps({"type": vehicle_type}).encode(),
        headers={"Authorization": key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError(f"unexpected response: {str(payload)[:200]}")
    return payload


def record(minutes: float, interval: float) -> Path:
    key = load_api_key()
    ALL_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(WARSAW)
    path = ALL_DIR / f"positions-{started:%Y%m%d-%H%M}.jsonl.gz"
    deadline = time.monotonic() + minutes * 60
    stop = False

    def handle_signal(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    polls = errors = 0
    print(f"Recording all vehicles to {path.relative_to(ROOT)} for {minutes:g} min. Ctrl+C stops early.")
    with gzip.open(path, "at", encoding="utf-8") as out:
        while not stop and time.monotonic() < deadline:
            tick = time.monotonic()
            for vehicle_type, mode in VEHICLE_TYPES.items():
                polled_at = datetime.now(WARSAW).isoformat(timespec="seconds")
                try:
                    vehicles = fetch(key, vehicle_type)
                except (urllib.error.URLError, TimeoutError, ValueError) as error:
                    errors += 1
                    print(f"{polled_at} {mode}: {error}", file=sys.stderr)
                    continue
                out.write(json.dumps({"polled_at": polled_at, "mode": mode, "vehicles": vehicles}) + "\n")
            out.flush()
            polls += 1
            if polls % 6 == 0:
                print(f"{datetime.now(WARSAW):%H:%M:%S} polls={polls} errors={errors}")
            time.sleep(max(0.0, interval - (time.monotonic() - tick)))
    print(f"Done: {polls} polls, {errors} errors, {path.stat().st_size / 1e6:.1f} MB")
    return path


def is_fresh(vehicle: dict, polled_at: datetime, max_age: timedelta) -> bool:
    try:
        seen = datetime.strptime(vehicle["Time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=WARSAW)
    except (KeyError, TypeError, ValueError):
        return False
    return -timedelta(minutes=1) <= polled_at - seen <= max_age


def extract(source: Path, lines: list[str], max_age_s: int) -> list[Path]:
    wanted = set(lines)
    max_age = timedelta(seconds=max_age_s)
    stamp = source.name.removeprefix("positions-").split(".")[0]
    outputs = {line: RAW_DIR / line / f"positions-{stamp}.jsonl" for line in wanted}
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    handles = {line: path.open("w", encoding="utf-8") for line, path in outputs.items()}
    counts = dict.fromkeys(wanted, 0)
    try:
        with gzip.open(source, "rt", encoding="utf-8") as raw:
            for row in raw:
                poll = json.loads(row)
                polled_at = datetime.fromisoformat(poll["polled_at"])
                for vehicle in poll["vehicles"]:
                    line = str(vehicle.get("Lines", "")).strip()
                    if line in wanted and is_fresh(vehicle, polled_at, max_age):
                        record_row = {"polled_at": poll["polled_at"], "mode": poll["mode"], **vehicle}
                        handles[line].write(json.dumps(record_row, ensure_ascii=False) + "\n")
                        counts[line] += 1
    finally:
        for handle in handles.values():
            handle.close()
    for line in sorted(wanted, key=lambda value: (len(value), value)):
        print(f"line {line}: {counts[line]} positions -> {outputs[line].relative_to(ROOT)}")
    return list(outputs.values())


def demo_lines() -> list[str]:
    return [entry["line"] for entry in json.loads(DEMO_LINES.read_text())["lines"]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Record live vehicle positions of the whole city and cut out lines.")
    commands = parser.add_subparsers(dest="command", required=True)
    rec = commands.add_parser("record", help="poll positions of all buses and trams")
    rec.add_argument("--minutes", type=float, default=60)
    rec.add_argument("--interval", type=float, default=10)
    ext = commands.add_parser("extract", help="cut lines out of a recording into data/raw/<line>/")
    ext.add_argument("source", type=Path, nargs="?", help="recording, default: the newest one")
    ext.add_argument("--lines", nargs="+", help="default: the demo lines from data/demo_lines.json")
    ext.add_argument("--max-age", type=int, default=120, help="drop positions older than this many seconds")
    args = parser.parse_args()
    if args.command == "record":
        record(args.minutes, args.interval)
        return
    source = args.source or max(ALL_DIR.glob("positions-*.jsonl.gz"), default=None)
    if source is None:
        sys.exit("No recording found in data/raw/all/. Run the record command first.")
    extract(source, args.lines or demo_lines(), args.max_age)


if __name__ == "__main__":
    main()
