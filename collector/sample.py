import argparse
import random
import sys
import time
from datetime import timedelta
from pathlib import Path

from collector.collect import collect
from collector.schema import load
from collector.stops import group_near, setup_backend

MAX_AGE = timedelta(minutes=5)
VEHICLE_TYPES = (1, 2)


def live_vehicles() -> list:
    setup_backend()
    from django.utils import timezone

    from transit.warsaw_api import fetch_vehicle_positions

    now = timezone.now()
    readings = [reading for kind in VEHICLE_TYPES for reading in fetch_vehicle_positions(vehicle_type=kind)]
    return sorted(
        (reading for reading in readings if now - reading.time <= MAX_AGE), key=lambda reading: reading.vehicle_number
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m collector.sample", description="Collect facts for the stops where random live vehicles are."
    )
    parser.add_argument("count", type=int, nargs="?", default=10, help="number of stop groups, default 10")
    parser.add_argument("--seed", type=int, default=int(time.time()), help="random seed, printed to repeat a run")
    args = parser.parse_args()

    vehicles = live_vehicles()
    random.Random(args.seed).shuffle(vehicles)
    print(f"seed {args.seed}, {len(vehicles)} vehicles reported in the last {MAX_AGE.seconds // 60} min")

    done: dict[str, str] = {}
    failed = 0
    for vehicle in vehicles:
        if len(done) == args.count:
            break
        group_id = group_near(vehicle.lat, vehicle.lon)
        label = f"vehicle {vehicle.vehicle_number} (line {vehicle.line})"
        if not group_id:
            print(f"skip  {label}: no stop group within 300 m")
            continue
        if group_id in done:
            continue
        started = time.monotonic()
        try:
            collected = load(collect(group_id))
        except Exception as error:
            failed += 1
            done[group_id] = "failed"
            print(f"FAIL  {label} -> {group_id}: {type(error).__name__}: {str(error)[:300]}")
            continue
        done[group_id] = collected.stop.name
        print(
            f"ok    {label} -> {group_id} {collected.stop.name} ({collected.area.district}): "
            f"{len(collected.objects)} objects, {len(collected.sources)} sources, "
            f"{len(collected.fragments)} fragments, {len(collected.images)} images, "
            f"{time.monotonic() - started:.0f} s"
        )
    print(f"{len(done) - failed} of {len(done)} stop groups collected and checked; files in {Path('out/collected')}")
    return 1 if failed or len(done) < args.count else 0


if __name__ == "__main__":
    sys.exit(main())
