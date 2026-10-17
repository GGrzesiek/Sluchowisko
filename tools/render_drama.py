import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO.parent
CACHE = REPO / "cache" / "elevenlabs"
API = "https://api.elevenlabs.io"
RATE = 44100
BYTES_PER_S = RATE * 2
MODELS = ("eleven_v4", "eleven_v3")
VOICES = {
    "narrator": "H5xTcsAIeS5RAykjz57a",
    "male_bg": "xsSg7GkDPDhaGZpbKOLn",
    "female_bg": "N0GCuK2B0qwWozQNTS8F",
}
LEVEL_DB = {"low": -21.0, "medium": -17.0, "solo": -12.0}
VOICE_DB = -9.0
FADE_S = 2.0


def secret(name):
    value = os.getenv(name, "").strip()
    if value:
        return value
    for path in (REPO / ".env", ROOT / ".env", ROOT / "klucze_api.txt"):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"')
    return ""


def ffmpeg():
    for candidate in (secret("FFMPEG_PATH"), str(ROOT / "tools" / "ffmpeg" / "ffmpeg.exe"), shutil.which("ffmpeg")):
        if candidate and Path(candidate).exists():
            return candidate
    sys.exit("ffmpeg not found: set FFMPEG_PATH or put ffmpeg.exe in tools/ffmpeg")


def run(args):
    subprocess.run([ffmpeg(), "-v", "error", "-y", *args], check=True)


def post(path, payload, key):
    request = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{path}: HTTP {error.code} {error.read()[:400].decode('utf-8', 'replace')}") from None


def cached(kind, payload, suffix):
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    path = CACHE / kind / f"{digest}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def tone(path, seconds, source):
    run(["-f", "lavfi", "-i", f"{source}:d={seconds:.2f}" if "=" in source else f"{source}=d={seconds:.2f}", str(path)])
    return path


def dialogue(inputs, key, dry, workdir, name):
    if dry:
        segments, cursor = [], 0.0
        for index, item in enumerate(inputs):
            length = max(1.0, len(item["text"].split()) / 2.3)
            segments.append(
                {"dialogue_input_index": index, "start_time_seconds": cursor, "end_time_seconds": cursor + length}
            )
            cursor += length + 0.15
        return tone(workdir / f"{name}.wav", cursor, "sine=frequency=220"), segments, "dry-run"
    last_error = None
    for model in MODELS:
        payload = {"inputs": inputs, "model_id": model, "language_code": "pl"}
        audio = cached("dialogue", payload, ".mp3")
        meta = audio.with_suffix(".json")
        if audio.exists() and meta.exists():
            return audio, json.loads(meta.read_text(encoding="utf-8")), model
        try:
            data = json.loads(post("/v1/text-to-dialogue/with-timestamps?output_format=mp3_44100_128", payload, key))
        except RuntimeError as error:
            last_error = error
            print(f"  {model} failed: {error}")
            continue
        audio.write_bytes(base64.b64decode(data["audio_base64"]))
        meta.write_text(json.dumps(data.get("voice_segments") or []), encoding="utf-8")
        return audio, json.loads(meta.read_text(encoding="utf-8")), model
    raise last_error


def speech(text, voice_id, model, key, dry, workdir, name):
    if dry:
        return tone(workdir / f"{name}.wav", max(1.0, len(text.split()) / 2.3), "sine=frequency=440")
    payload = {"text": text, "model_id": model, "language_code": "pl", "voice_id": voice_id}
    audio = cached("speech", payload, ".mp3")
    if not audio.exists():
        body = {k: v for k, v in payload.items() if k != "voice_id"}
        audio.write_bytes(post(f"/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128", body, key))
    return audio


def sound(prompt, seconds, key, dry, workdir, name):
    if dry:
        return tone(workdir / f"{name}.wav", min(30.0, seconds), "anoisesrc=c=pink")
    payload = {
        "text": prompt,
        "duration_seconds": round(min(30.0, max(0.5, seconds)), 1),
        "loop": True,
        "prompt_influence": 0.5,
        "model_id": "eleven_text_to_sound_v2",
    }
    audio = cached("sfx", payload, ".mp3")
    if not audio.exists():
        audio.write_bytes(post("/v1/sound-generation?output_format=mp3_44100_128", payload, key))
    return audio


def pcm(path):
    return subprocess.run(
        [ffmpeg(), "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(RATE), "-"],
        check=True,
        capture_output=True,
    ).stdout


def at(byte_seconds):
    offset = int(byte_seconds * RATE) * 2
    return max(0, offset)


def line_bounds(segments, count):
    bounds = {}
    for segment in segments:
        index = segment.get("dialogue_input_index")
        if index is None:
            return None
        start, end = segment["start_time_seconds"], segment["end_time_seconds"]
        current = bounds.setdefault(index, [start, end])
        current[0], current[1] = min(current[0], start), max(current[1], end)
    if sorted(bounds) != list(range(count)):
        return None
    return [bounds[i] for i in range(count)]


def narration(script, key, dry, workdir):
    lines = {line["id"]: line for line in script["lines"]}
    pieces, model_used = {}, None
    for chunk in script["chunks"]:
        ids = chunk["line_ids"]
        inputs = [{"text": lines[i]["tts"], "voice_id": VOICES["narrator"]} for i in ids]
        print(f"  narration {chunk['id']}: {sum(len(x['text']) for x in inputs)} chars")
        audio, segments, model_used = dialogue(inputs, key, dry, workdir, chunk["id"])
        raw = pcm(audio)
        total = len(raw) / BYTES_PER_S
        bounds = line_bounds(segments, len(ids))
        if bounds is None:
            print(f"  {chunk['id']}: no per-line timestamps, voicing lines one by one")
            for i in ids:
                pieces[i] = pcm(speech(lines[i]["tts"], VOICES["narrator"], model_used, key, dry, workdir, i))
            continue
        cuts = [0.0] + [(bounds[n][1] + bounds[n + 1][0]) / 2 for n in range(len(ids) - 1)] + [total]
        for n, i in enumerate(ids):
            pieces[i] = raw[at(cuts[n]) : at(cuts[n + 1])]
    return pieces, model_used


def anchor(point, placed):
    start, end = placed[point["line_id"]]
    return (start if point["edge"] == "start" else end) + point["offset_s"]


def render(script_path, target, dry):
    script = json.loads(Path(script_path).read_text(encoding="utf-8"))
    key = "" if dry else secret("ELEVENLABS_API_KEY")
    if not dry and not key:
        sys.exit("ELEVENLABS_API_KEY not found in environment, .env or klucze_api.txt")
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        pieces, model = narration(script, key, dry, workdir)
        lead = max(
            [0.0]
            + [-a["start"]["offset_s"] for a in script["ambience"] if a["start"]["line_id"] == script["lines"][0]["id"]]
        )
        voice_track, placed, cursor = bytearray(at(lead)), {}, lead
        for line in script["lines"]:
            piece = pieces[line["id"]]
            length = len(piece) / BYTES_PER_S
            placed[line["id"]] = (cursor, cursor + length)
            voice_track += piece + bytes(at(line["pause_after_s"]))
            cursor += length + line["pause_after_s"]
        total = cursor + 2.0
        voice_track += bytes(at(2.0))
        voice_wav = workdir / "voice.wav"
        raw = workdir / "voice.raw"
        raw.write_bytes(bytes(voice_track))
        run(["-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", str(raw), str(voice_wav)])
        layers, background = [], []
        for item in script["ambience"]:
            start = max(0.0, anchor(item["start"], placed))
            end = min(total, anchor(item["end"], placed)) if item.get("end") else start + 5.0
            length = end - start
            if length <= 0.5:
                continue
            print(f"  ambience {item['id']}: {start:.1f}-{end:.1f} s")
            source = sound(item["prompt_en"], length, key, dry, workdir, item["id"])
            fade = min(FADE_S, length / 3)
            gain = LEVEL_DB.get(item.get("level", "low"), -21.0)
            if item["shape"] == "swell":
                ramp, low, high = length * 0.6, 10 ** ((gain - 14) / 20), 10 ** (gain / 20)
                rise = (
                    f"volume='if(lt(t,{ramp:.2f}),{low:.4f}+({high:.4f}-{low:.4f})*t/{ramp:.2f},{high:.4f})':eval=frame"
                )
            else:
                rise = f"volume={gain}dB"
            out = workdir / f"{item['id']}_layer.wav"
            run(
                [
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(source),
                    "-af",
                    ",".join(
                        [
                            f"atrim=0:{length:.2f}",
                            "asetpts=PTS-STARTPTS",
                            rise,
                            f"afade=t=in:d={fade:.2f}",
                            f"afade=t=out:st={length - fade:.2f}:d={fade:.2f}",
                            f"adelay={int(start * 1000)}:all=1",
                            f"apad=whole_dur={total:.2f}",
                        ]
                    ),
                    "-ar",
                    str(RATE),
                    "-ac",
                    "1",
                    str(out),
                ]
            )
            layers.append(out)
            for voice in item.get("voices", []):
                when = max(0.0, anchor(voice["at"], placed))
                kind = "female_bg" if voice["voice"].startswith("kobieta") else "male_bg"
                print(f"  voice {voice['id']} at {when:.1f} s")
                spoken = speech(voice["tts"], VOICES[kind], model if not dry else "dry", key, dry, workdir, voice["id"])
                color = (
                    "highpass=f=350,lowpass=f=3200"
                    if "radio" in voice["tts"]
                    else "highpass=f=200,lowpass=f=4500,aecho=0.8:0.6:40:0.25"
                )
                out_voice = workdir / f"{voice['id']}_layer.wav"
                run(
                    [
                        "-i",
                        str(spoken),
                        "-af",
                        f"{color},volume={VOICE_DB}dB,adelay={int(when * 1000)}:all=1,apad=whole_dur={total:.2f}",
                        "-ar",
                        str(RATE),
                        "-ac",
                        "1",
                        str(out_voice),
                    ]
                )
                background.append(out_voice)
        inputs = ["-i", str(voice_wav)]
        for path in layers + background:
            inputs += ["-i", str(path)]
        amb = "".join(f"[{n + 1}:a]" for n in range(len(layers)))
        bg = "".join(f"[{n + 1 + len(layers)}:a]" for n in range(len(background)))
        graph = [f"{amb}amix=inputs={len(layers)}:normalize=0[amb]", "[0:a]asplit=2[v][key]"]
        graph.append("[amb][key]sidechaincompress=threshold=0.03:ratio=6:attack=60:release=700:makeup=1[ducked]")
        if background:
            graph.append(f"{bg}amix=inputs={len(background)}:normalize=0[bg]")
            graph.append("[v][ducked][bg]amix=inputs=3:normalize=0[mix]")
        else:
            graph.append("[v][ducked]amix=inputs=2:normalize=0[mix]")
        graph.append(f"[mix]atrim=0:{total:.2f},loudnorm=I=-16:TP=-1.5:LRA=11[out]")
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        run(
            [
                *inputs,
                "-filter_complex",
                ";".join(graph),
                "-map",
                "[out]",
                "-ar",
                str(RATE),
                "-b:a",
                "128k",
                str(target),
            ]
        )
    timeline = {
        "model": model,
        "seconds": round(total, 1),
        "lines": {k: [round(a, 2), round(b, 2)] for k, (a, b) in placed.items()},
    }
    Path(target).with_suffix(".timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    print(f"done: {target} ({total:.1f} s, model {model})")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if not args:
        sys.exit("usage: python tools/render_drama.py <script.json> [output.mp3] [--dry-run]")
    source = args[0]
    output = args[1] if len(args) > 1 else str(Path(source).with_suffix(".mp3"))
    render(source, output, "--dry-run" in sys.argv)
