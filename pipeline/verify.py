from __future__ import annotations

from datetime import datetime

from .config import LineCfg, read_json, write_json
from .sources import load_documents

MIN_WORDS, MAX_WORDS = 60, 130


def word_count(story: dict) -> int:
    return sum(len(s["text"].split()) for s in story.get("sentences", []))


def structural_check(
    story: dict, docs: list[dict], min_words: int = MIN_WORDS, max_words: int = MAX_WORDS
) -> list[str]:
    sentences = story.get("sentences") or []
    if not sentences:
        return ["No sentences"]
    by_id = {d["id"]: d for d in docs}
    problems = []
    for i, s in enumerate(sentences, start=1):
        ids = s.get("source_ids") or []
        if not ids:
            problems.append(f"Sentence {i}: no source")
        for sid in ids:
            doc = by_id.get(sid)
            if doc is None:
                problems.append(f"Sentence {i}: unknown source {sid}")
            elif not doc.get("url"):
                problems.append(f"Sentence {i}: source {sid} has no link")
    wc = word_count(story)
    if not min_words <= wc <= max_words:
        problems.append(f"Length {wc} words is outside {min_words}–{max_words}")
    return problems


def verify(line: LineCfg) -> int:
    path = line.out_dir / "stories.json"
    data = read_json(path)
    failing = 0
    for story in data["stories"]:
        if story.get("skip"):
            continue
        problems = structural_check(story, load_documents(line, story["stop_slug"]))
        story["verification"] = {
            "status": "ok" if not problems else "needs_review",
            "problems": problems,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }
        failing += bool(problems)
        mark = "OK" if not problems else f"NEEDS REVIEW ({len(problems)})"
        print(f"{story['stop_name']}: {mark}")
        for p in problems:
            print(f"   - {p}")
    write_json(path, data)
    return failing
