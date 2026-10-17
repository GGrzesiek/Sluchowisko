from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import DEFAULT_LINE, ConfigError, load_line


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mwa", description="Muzeum w autobusie data pipeline")
    parser.add_argument("--line", default=str(DEFAULT_LINE), help="line config file")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("route", help="stops and route of the line from the ZTM API → route.json")
    p.add_argument("--cache", action="store_true", help="use saved responses from data/raw")

    p = sub.add_parser("record", help="record vehicle positions of the line to JSONL")
    p.add_argument("--minutes", type=float, default=60)
    p.add_argument("--interval", type=float, default=10, help="seconds between snapshots")

    sub.add_parser("context", help="automatic sources: Wikipedia, OSM, Wikidata")

    p = sub.add_parser("verify", help="check that every story sentence has a linked source")
    p.add_argument("--strict", action="store_true", help="exit with code 1 if any story needs review")

    p = sub.add_parser("tts", help="voice-over and subtitles for verified stories")
    p.add_argument("--include-unverified", action="store_true")

    p = sub.add_parser("simulate", help="ride simulation from a recording → ride.json")
    p.add_argument("recording", type=Path, help="JSONL file from `mwa record`")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        line = load_line(args.line)
        if args.cmd == "route":
            from .ztm import build_route

            build_route(line, use_cache=args.cache)
        elif args.cmd == "record":
            from .ztm import record

            record(line, args.minutes, args.interval)
        elif args.cmd == "context":
            from .sources import collect_auto

            collect_auto(line)
        elif args.cmd == "verify":
            from .verify import verify

            failing = verify(line)
            if args.strict and failing:
                return 1
        elif args.cmd == "tts":
            from .tts import tts

            tts(line, include_unverified=args.include_unverified)
        elif args.cmd == "simulate":
            from .simulate import simulate

            simulate(line, args.recording)
    except ConfigError as e:
        print(f"Config: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"Missing file: {e.filename}. Run the earlier pipeline step first.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
