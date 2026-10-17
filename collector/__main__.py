import argparse
import sys

from collector.cache import FetchError
from collector.check import CheckError
from collector.collect import collect
from collector.osm import OverpassError
from collector.stops import UnknownStopGroup


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m collector", description="Collect facts about one stop group.")
    parser.add_argument("group_id", help="stop group id (zespol), e.g. 5086")
    args = parser.parse_args()
    try:
        print(collect(args.group_id))
    except (UnknownStopGroup, OverpassError, FetchError, CheckError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
