import base64
import hashlib
import json
from pathlib import Path

import requests

from story_agent.files import CACHE, env

API = "https://api.elevenlabs.io"
TIMEOUT_S = 180
MAX_DIALOGUE_CHARS = 2000


class ElevenLabsError(Exception):
    pass


def api_key() -> str:
    key = env("ELEVENLABS_API_KEY")
    if not key:
        raise ElevenLabsError("ELEVENLABS_API_KEY is not set (put it in .env, never commit it)")
    return key


def _cache_file(kind: str, payload: dict, suffix: str) -> Path:
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return CACHE / "elevenlabs" / kind / f"{digest}{suffix}"


def _post(path: str, payload: dict, params: dict | None = None) -> requests.Response:
    response = requests.post(
        f"{API}{path}",
        params=params,
        json=payload,
        headers={"xi-api-key": api_key(), "Content-Type": "application/json"},
        timeout=TIMEOUT_S,
    )
    if response.status_code >= 400:
        raise ElevenLabsError(f"{path}: HTTP {response.status_code} {response.text[:300]}")
    return response


def dialogue(inputs: list[dict], model_id: str, seed: int | None = None) -> tuple[Path, list[dict]]:
    payload = {"inputs": inputs, "model_id": model_id, "language_code": "pl"}
    if seed is not None:
        payload["seed"] = seed
    audio = _cache_file("dialogue", payload, ".mp3")
    meta = audio.with_suffix(".json")
    if audio.exists() and meta.exists():
        return audio, json.loads(meta.read_text(encoding="utf-8"))
    params = {"output_format": "mp3_44100_128"}
    data = _post("/v1/text-to-dialogue/with-timestamps", payload, params).json()
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(base64.b64decode(data["audio_base64"]))
    segments = data.get("voice_segments") or []
    meta.write_text(json.dumps(segments), encoding="utf-8")
    return audio, segments


def speech(text: str, voice_id: str, model_id: str) -> Path:
    payload = {"text": text, "model_id": model_id, "language_code": "pl", "voice_id": voice_id}
    audio = _cache_file("speech", payload, ".mp3")
    if audio.exists():
        return audio
    body = {k: v for k, v in payload.items() if k != "voice_id"}
    response = _post(f"/v1/text-to-speech/{voice_id}", body, {"output_format": "mp3_44100_128"})
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(response.content)
    return audio


def sound_effect(prompt: str, duration_s: float, loop: bool) -> Path:
    payload = {
        "text": prompt,
        "duration_seconds": round(min(30.0, max(0.5, duration_s)), 1),
        "loop": loop,
        "prompt_influence": 0.5,
        "model_id": "eleven_text_to_sound_v2",
    }
    audio = _cache_file("sfx", payload, ".mp3")
    if audio.exists():
        return audio
    response = _post("/v1/sound-generation", payload, {"output_format": "mp3_44100_128"})
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(response.content)
    return audio


def music(prompt: str, length_s: float) -> Path:
    payload = {"prompt": prompt, "music_length_ms": int(max(3000, length_s * 1000)), "force_instrumental": True}
    audio = _cache_file("music", payload, ".mp3")
    if audio.exists():
        return audio
    response = _post("/v1/music", payload, {"output_format": "mp3_44100_128"})
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(response.content)
    return audio


def list_voices() -> list[dict]:
    response = requests.get(f"{API}/v1/voices", headers={"xi-api-key": api_key()}, timeout=TIMEOUT_S)
    if response.status_code >= 400:
        raise ElevenLabsError(f"/v1/voices: HTTP {response.status_code} {response.text[:300]}")
    return response.json().get("voices", [])
