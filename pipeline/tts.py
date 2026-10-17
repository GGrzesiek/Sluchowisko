from __future__ import annotations

import base64

import requests

from .config import LineCfg, env, read_json, write_json


def sentence_timings(sentences: list[str], alignment: dict) -> list[dict]:
    chars = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    full = "".join(chars)
    out, pos = [], 0
    for s in sentences:
        idx = full.find(s, pos)
        if idx == -1:
            idx = min(pos, len(chars) - 1)
        last = min(idx + len(s), len(chars)) - 1
        out.append({"text": s, "start": round(starts[idx], 3), "end": round(ends[last], 3)})
        pos = idx + len(s)
    return out


def synthesize(text: str) -> tuple[bytes, dict]:
    voice = env("ELEVENLABS_VOICE_ID", required=True)
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps",
        headers={"xi-api-key": env("ELEVENLABS_API_KEY", required=True)},
        json={"text": text, "model_id": env("ELEVENLABS_MODEL", "eleven_multilingual_v2")},
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    return base64.b64decode(data["audio_base64"]), data["alignment"]


def tts(line: LineCfg, include_unverified: bool = False) -> None:
    path = line.out_dir / "stories.json"
    data = read_json(path)
    audio_dir = line.out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    for story in data["stories"]:
        if story.get("skip"):
            continue
        verified = story.get("verification", {}).get("status") == "ok"
        if not verified and not include_unverified:
            print(f"{story['stop_name']}: skipped, not verified (use --include-unverified)")
            continue
        texts = [s["text"] for s in story["sentences"]]
        audio, alignment = synthesize(" ".join(texts))
        file = audio_dir / f"{story['stop_slug']}.mp3"
        file.write_bytes(audio)
        timings = sentence_timings(texts, alignment)
        for t, s in zip(timings, story["sentences"], strict=True):
            t["source_ids"] = s.get("source_ids", [])
        story["audio"] = f"audio/{file.name}"
        story["subtitles"] = timings
        story["duration_s"] = timings[-1]["end"] if timings else 0
        print(f"{story['stop_name']}: {story['duration_s']:.0f} s → {file}")
    write_json(path, data)
