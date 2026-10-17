import json
import math
import shutil
import subprocess
import tempfile
from array import array
from dataclasses import dataclass
from pathlib import Path

from story_agent import elevenlabs
from story_agent.checks import strip_tags, words
from story_agent.models import Sound, StoryScript, VoicedScript

RATE = 44100
BLOCK = 441
VOICES = Path(__file__).with_name("voices.json")
MAX_LEAD_S = 3.0
MAX_TAIL_S = 3.0
DUCK_ATTACK_S = 0.25
LEVELS_DB = {
    "bed": (-24.0, -12.0),
    "swell": (-16.0, -6.0),
    "spot": (-12.0, -4.0),
    "music": (-27.0, -16.0),
}
SWELL_FROM_DB = -34.0
FADES_S = {"bed": (0.8, 1.2), "swell": (1.5, 0.8), "spot": (0.03, 0.3), "music": (1.5, 2.0)}


@dataclass
class Placed:
    start: float
    end: float


def ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("ffmpeg is not installed (Windows: winget install Gyan.FFmpeg)")
    return path


def decode(path: Path) -> array:
    raw = subprocess.run(
        [ffmpeg(), "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(RATE), "-"],
        check=True,
        capture_output=True,
    ).stdout
    samples = array("f")
    samples.frombytes(raw)
    return samples


def synth(kind: str, seconds: float, workdir: Path, name: str) -> Path:
    target = workdir / f"{name}.wav"
    source = f"sine=frequency=220:duration={seconds:.2f}" if kind == "voice" else f"anoisesrc=d={seconds:.2f}:c=pink"
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", source, str(target)], check=True)
    return target


def silence(seconds: float) -> array:
    return array("f", bytes(4 * int(seconds * RATE)))


def db(value: float) -> float:
    return 10 ** (value / 20)


def load_voices() -> dict:
    return json.loads(VOICES.read_text(encoding="utf-8"))


def _segments_by_line(segments: list[dict], count: int) -> list[tuple[float, float]] | None:
    bounds: dict[int, list[float]] = {}
    for segment in segments:
        index = segment.get("dialogue_input_index")
        if index is None:
            return None
        start, end = segment["start_time_seconds"], segment["end_time_seconds"]
        current = bounds.setdefault(index, [start, end])
        current[0], current[1] = min(current[0], start), max(current[1], end)
    if sorted(bounds) != list(range(count)):
        return None
    return [(bounds[i][0], bounds[i][1]) for i in range(count)]


def chunks(lines: list[dict], limit: int = elevenlabs.MAX_DIALOGUE_CHARS) -> list[list[int]]:
    groups, current, size = [], [], 0
    for index, line in enumerate(lines):
        length = len(line["text"])
        if current and size + length > limit:
            groups.append(current)
            current, size = [], 0
        current.append(index)
        size += length
    if current:
        groups.append(current)
    return groups


def voice_pieces(script: StoryScript, voiced: VoicedScript, workdir: Path, dry_run: bool) -> list[array]:
    config = load_voices()
    model_id = config["model_id"]
    inputs = [{"text": line.tts_text, "voice_id": config["voices"][line.voice]["voice_id"]} for line in voiced.lines]
    if dry_run:
        return [
            decode(synth("voice", max(1.0, len(words(strip_tags(line.tts_text)))) / 2.3, workdir, f"v{i}"))
            for i, line in enumerate(voiced.lines)
        ]
    pieces: list[array] = []
    for group in chunks(inputs):
        audio_path, segments = elevenlabs.dialogue([inputs[i] for i in group], model_id)
        audio = decode(audio_path)
        bounds = _segments_by_line(segments, len(group))
        if bounds is None:
            for i in group:
                pieces.append(decode(elevenlabs.speech(inputs[i]["text"], inputs[i]["voice_id"], model_id)))
            continue
        total = len(audio) / RATE
        cuts = [0.0] + [(bounds[i][1] + bounds[i + 1][0]) / 2 for i in range(len(group) - 1)] + [total]
        for i in range(len(group)):
            start, end = int(cuts[i] * RATE), int(cuts[i + 1] * RATE)
            pieces.append(audio[start:end])
    return pieces


def anchor_time(anchor, lines: dict[str, Placed]) -> float:
    placed = lines[anchor.line_id]
    return (placed.start if anchor.edge == "start" else placed.end) + anchor.offset_s


def speech_gain(t: float, speech: list[Placed]) -> float:
    closeness = 0.0
    for span in speech:
        if span.start - DUCK_ATTACK_S <= t <= span.end + DUCK_ATTACK_S:
            if t < span.start:
                closeness = max(closeness, 1 - (span.start - t) / DUCK_ATTACK_S)
            elif t > span.end:
                closeness = max(closeness, 1 - (t - span.end) / DUCK_ATTACK_S)
            else:
                return 1.0
    return closeness


def envelope(shape: str, t: float, start: float, end: float, speech: list[Placed]) -> float:
    if t < start or t > end:
        return 0.0
    under, free = LEVELS_DB[shape]
    duck = speech_gain(t, speech)
    if shape == "swell":
        progress = (t - start) / max(end - start, 0.01)
        ramp = SWELL_FROM_DB + (free - SWELL_FROM_DB) * progress
        level = min(ramp, under) * duck + ramp * (1 - duck)
    else:
        level = under * duck + free * (1 - duck)
    fade_in, fade_out = FADES_S[shape]
    gain = db(level)
    if t - start < fade_in:
        gain *= (t - start) / fade_in
    if end - t < fade_out:
        gain *= max(0.0, (end - t) / fade_out)
    return gain


def place_layer(mix: array, source: array, start: float, end: float, shape: str, speech: list[Placed]) -> None:
    first = max(0, int(start * RATE))
    last = min(len(mix), int(end * RATE))
    if not source or last <= first:
        return
    length = len(source)
    for block_start in range(first, last, BLOCK):
        block_end = min(block_start + BLOCK, last)
        gain = envelope(shape, block_start / RATE, start, end, speech)
        if gain <= 0:
            continue
        for i in range(block_start, block_end):
            mix[i] += source[(i - first) % length] * gain


def sound_audio(sound: Sound, prompt: dict, seconds: float, workdir: Path, dry_run: bool) -> array:
    if dry_run:
        return decode(synth("sound", min(seconds, 30.0), workdir, sound.id))
    if sound.shape == "spot":
        return decode(elevenlabs.sound_effect(prompt["prompt"], prompt["duration_s"], False))
    return decode(elevenlabs.sound_effect(prompt["prompt"], min(30.0, seconds), seconds > 30 or prompt["loop"]))


def render(script: StoryScript, voiced: VoicedScript, target: Path, dry_run: bool = False) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        pieces = voice_pieces(script, voiced, workdir, dry_run)
        raw_lines: dict[str, Placed] = {}
        cursor = 0.0
        for line, piece in zip(script.lines, pieces, strict=True):
            length = len(piece) / RATE
            raw_lines[line.id] = Placed(cursor, cursor + length)
            cursor += length + line.pause_after_s
        starts = [anchor_time(s.start, raw_lines) for s in script.sounds]
        lead = min(MAX_LEAD_S, max(0.0, -min(starts, default=0.0)))
        lines = {k: Placed(v.start + lead, v.end + lead) for k, v in raw_lines.items()}
        speech = list(lines.values())
        last_word = max(p.end for p in speech)
        prompts = {s.id: s.model_dump() for s in voiced.sounds}
        placed_sounds = {}
        for sound in script.sounds:
            start = max(0.0, anchor_time(sound.start, lines))
            is_spot = sound.shape == "spot"
            end = start + prompts[sound.id]["duration_s"] if is_spot else anchor_time(sound.end, lines)
            end = min(end, last_word + MAX_TAIL_S)
            if end > start:
                placed_sounds[sound.id] = Placed(start, end)
        total = max([last_word + 0.6] + [p.end for p in placed_sounds.values()])
        mix = silence(total + 0.1)
        for line, piece in zip(script.lines, pieces, strict=True):
            offset = int(lines[line.id].start * RATE)
            for i, value in enumerate(piece):
                if offset + i < len(mix):
                    mix[offset + i] += value
        for sound in script.sounds:
            if sound.id not in placed_sounds:
                continue
            span = placed_sounds[sound.id]
            audio = sound_audio(sound, prompts[sound.id], span.end - span.start, workdir, dry_run)
            place_layer(mix, audio, span.start, span.end, sound.shape, speech)
        if script.music and voiced.music:
            audio = (
                decode(synth("music", total, workdir, "music"))
                if dry_run
                else decode(elevenlabs.music(voiced.music.prompt, total))
            )
            place_layer(mix, audio, 0.0, total, "music", speech)
        raw = workdir / "mix.f32"
        raw.write_bytes(mix.tobytes())
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                ffmpeg(),
                "-v",
                "error",
                "-y",
                "-f",
                "f32le",
                "-ar",
                str(RATE),
                "-ac",
                "1",
                "-i",
                str(raw),
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar",
                str(RATE),
                "-b:a",
                "128k",
                str(target),
            ],
            check=True,
        )
    seconds = round(total, 2)
    return {
        "group_id": script.group_id,
        "file": target.as_posix(),
        "seconds": seconds,
        "target_duration_s": script.target_duration_s,
        "over_target": seconds > script.target_duration_s + 2,
        "dry_run": dry_run,
        "lead_s": round(lead, 2),
        "lines": {k: [round(v.start, 2), round(v.end, 2)] for k, v in lines.items()},
        "sounds": {k: [round(v.start, 2), round(v.end, 2)] for k, v in placed_sounds.items()},
        "peak": round(max((abs(x) for x in mix), default=0.0), 3),
        "rms_db": round(20 * math.log10(max(1e-9, math.sqrt(sum(x * x for x in mix) / max(len(mix), 1)))), 1),
    }
