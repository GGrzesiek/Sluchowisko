import argparse
import json
import sys

from story_agent import files
from story_agent.checks import check_plan, check_script, check_voiced
from story_agent.models import StoryPlan, StoryScript, VoicedScript
from story_agent.stops import demo_stop, demo_stops

STAGES = [
    ("collected", files.collected_path, "python -m story_agent collect {g}"),
    ("plan", files.plan_path, "skill planning-stop-stories → out/plans/{g}.json, potem check-plan"),
    ("script", files.script_path, "skill writing-stop-stories → out/scripts/{g}.json, potem check-script"),
    ("voiced", files.voiced_path, "skill voicing-stop-stories → out/voiced/{g}.json, potem check-voiced"),
    ("audio", files.audio_path, "python -m story_agent render {g}"),
    ("record", files.record_path, "python -m story_agent record {g}"),
]


def _print(text: str) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)


def _report(group_id: str, stage: str, report) -> int:
    files.write_json(files.check_path(group_id, stage), report.as_dict())
    _print(str(report))
    return 0 if report.ok else 1


def cmd_targets(args) -> int:
    for stop in demo_stops().values():
        _print(f"{stop.group_id}\t{stop.target_duration_s}s\t{','.join(stop.lines)}\t{stop.name}")
    return 0


def cmd_collect(args) -> int:
    from story_agent.collect import collect

    path = collect(args.group_id, args.lat, args.lon)
    _print(str(path))
    return 0


def cmd_show(args) -> int:
    from story_agent.material import load_material, render_material

    _print(render_material(load_material(args.group_id)))
    return 0


def cmd_fetch(args) -> int:
    from story_agent.material import fetch_more

    _print(fetch_more(args.group_id, args.tool, args.query, args.why))
    return 0


def cmd_fetch_log(args) -> int:
    from story_agent.material import fetch_log

    _print(json.dumps(fetch_log(args.group_id), ensure_ascii=False, indent=2))
    return 0


def cmd_check_plan(args) -> int:
    from story_agent.material import load_material

    plan = files.load_model(StoryPlan, files.plan_path(args.group_id))
    try:
        target = demo_stop(args.group_id).target_duration_s
    except KeyError:
        target = None
    return _report(args.group_id, "plan", check_plan(plan, load_material(args.group_id), target))


def cmd_check_script(args) -> int:
    from story_agent.material import load_material

    plan = files.load_model(StoryPlan, files.plan_path(args.group_id))
    script = files.load_model(StoryScript, files.script_path(args.group_id))
    return _report(args.group_id, "script", check_script(script, plan, load_material(args.group_id)))


def cmd_check_voiced(args) -> int:
    script = files.load_model(StoryScript, files.script_path(args.group_id))
    voiced = files.load_model(VoicedScript, files.voiced_path(args.group_id))
    return _report(args.group_id, "voiced", check_voiced(voiced, script))


def cmd_render(args) -> int:
    from story_agent.audio import render

    script = files.load_model(StoryScript, files.script_path(args.group_id))
    voiced = files.load_model(VoicedScript, files.voiced_path(args.group_id))
    report = check_voiced(voiced, script)
    if not report.ok:
        _print(str(report))
        return 1
    target = files.audio_path(args.group_id)
    if args.dry_run:
        target = target.with_name(f"{args.group_id}.dry-run.mp3")
    timeline = render(script, voiced, target, dry_run=args.dry_run)
    files.write_json(files.timeline_path(args.group_id), timeline)
    _print(json.dumps(timeline, ensure_ascii=False, indent=2))
    if timeline["over_target"]:
        _print(f"ZA DŁUGO: {timeline['seconds']} s przy celu {timeline['target_duration_s']} s — skróć scenariusz")
        return 1
    return 0


def cmd_record(args) -> int:
    from story_agent.material import load_material
    from story_agent.record import build_record

    plan = files.load_model(StoryPlan, files.plan_path(args.group_id))
    script = files.load_model(StoryScript, files.script_path(args.group_id))
    timeline_file = files.timeline_path(args.group_id)
    seconds = None
    if timeline_file.exists():
        timeline = files.read_json(timeline_file)
        if not timeline.get("dry_run"):
            seconds = timeline["seconds"]
    record = build_record(script, plan, load_material(args.group_id), seconds, args.media_base)
    path = files.write_json(files.record_path(args.group_id), record)
    _print(str(path))
    if not record["photos"]:
        _print("UWAGA: backend wymaga co najmniej jednego zdjęcia")
    if not seconds:
        _print("UWAGA: brak prawdziwego nagrania (render bez --dry-run)")
    return 0


def cmd_next(args) -> int:
    group_id = args.group_id
    for stage, path_of, todo in STAGES:
        path = path_of(group_id)
        if not path.exists():
            _print(f"{group_id}: brak „{stage}”. Następny krok: {todo.format(g=group_id)}")
            return 0
        check = files.check_path(group_id, stage)
        if stage in ("plan", "script", "voiced"):
            if not check.exists() or path.stat().st_mtime > check.stat().st_mtime:
                _print(f"{group_id}: „{stage}” niesprawdzony. Uruchom: python -m story_agent check-{stage} {group_id}")
                return 0
            if not files.read_json(check)["ok"]:
                _print(f"{group_id}: „{stage}” ma błędy w {check}. Popraw plik i sprawdź ponownie.")
                return 0
    _print(f"{group_id}: gotowe → {files.record_path(group_id)}")
    return 0


def cmd_status(args) -> int:
    for stop in demo_stops().values():
        marks = []
        for stage, path_of, _ in STAGES:
            marks.append(stage if path_of(stop.group_id).exists() else "·")
        _print(f"{stop.group_id}\t{stop.name[:28]:28}\t{' '.join(marks)}")
    return 0


def cmd_voices(args) -> int:
    from story_agent.elevenlabs import list_voices

    for voice in list_voices():
        labels = voice.get("labels") or {}
        info = ", ".join(f"{k}: {v}" for k, v in labels.items())
        _print(f"{voice['voice_id']}\t{voice['name']}\t{info}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m story_agent", description="Agent historii przystanków")
    sub = parser.add_subparsers(dest="command", required=True)

    def group(name, func, help_text):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("group_id")
        p.set_defaults(func=func)
        return p

    sub.add_parser("targets", help="docelowe długości nagrań").set_defaults(func=cmd_targets)
    sub.add_parser("status", help="stan wszystkich 50 przystanków").set_defaults(func=cmd_status)
    sub.add_parser("voices", help="głosy z konta ElevenLabs").set_defaults(func=cmd_voices)
    p = group("collect", cmd_collect, "zbieracz: out/collected/<id>.json")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    group("show", cmd_show, "materiał przystanku w czytelnej formie")
    p = group("fetch", cmd_fetch, "dociągnij źródło")
    p.add_argument("tool", choices=["wikipedia", "search", "wikidata", "warszawikia", "warszawikia-search", "url"])
    p.add_argument("query")
    p.add_argument("--why", required=True)
    group("fetch-log", cmd_fetch_log, "lista dociągnięć")
    group("check-plan", cmd_check_plan, "sprawdź plan")
    group("check-script", cmd_check_script, "sprawdź scenariusz")
    group("check-voiced", cmd_check_voiced, "sprawdź tekst dla TTS")
    p = group("render", cmd_render, "nagraj i zmiksuj audio")
    p.add_argument("--dry-run", action="store_true", help="bez ElevenLabs: dźwięki zastępcze")
    p = group("record", cmd_record, "rekord dla backendu: out/stories/<id>.json")
    p.add_argument("--media-base")
    group("next", cmd_next, "co dalej z tym przystankiem")
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
