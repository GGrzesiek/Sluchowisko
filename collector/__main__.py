import argparse
import sys
import time

from collector.collect import collect_many, demo_groups

DEFAULT_JOBS = 4


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m collector", description="Collect facts about stop groups.")
    parser.add_argument("group_ids", nargs="*", help="stop group ids (zespol), e.g. 5086")
    parser.add_argument("--demo", action="store_true", help="every stop group of the demo lines")
    parser.add_argument(
        "--jobs", type=int, default=DEFAULT_JOBS, help=f"stop groups collected at once, default {DEFAULT_JOBS}"
    )
    args = parser.parse_args()
    group_ids = list(dict.fromkeys([*args.group_ids, *(demo_groups() if args.demo else [])]))
    if not group_ids:
        parser.error("give stop group ids or --demo")

    started = time.monotonic()
    failed = 0
    for group_id, result in collect_many(group_ids, jobs=args.jobs):
        if isinstance(result, Exception):
            failed += 1
            print(f"error: {group_id}: {result}", file=sys.stderr, flush=True)
        else:
            print(result, flush=True)
    if len(group_ids) > 1:
        print(
            f"{len(group_ids) - failed} of {len(group_ids)} stop groups in {time.monotonic() - started:.0f} s",
            file=sys.stderr,
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
