import hashlib
import json
import time
from pathlib import Path

import requests

from story_agent.files import CACHE

USER_AGENT = "Sluchowisko/0.1 (https://github.com/GGrzesiek/opendatahackathon42; hackathon project)"
TIMEOUT_S = 60
PAUSE_S = {"overpass-api.de": 2.0, "www.wikidata.org": 0.5}
_last_call: dict[str, float] = {}


class FetchError(Exception):
    pass


def _key(method: str, url: str, params: dict | None, body: str | None) -> str:
    raw = json.dumps([method, url, params or {}, body or ""], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _wait(url: str) -> None:
    host = url.split("/")[2]
    pause = PAUSE_S.get(host, 0.2)
    elapsed = time.monotonic() - _last_call.get(host, 0)
    if elapsed < pause:
        time.sleep(pause - elapsed)
    _last_call[host] = time.monotonic()


def fetch_text(
    url: str,
    params: dict | None = None,
    method: str = "GET",
    data: str | None = None,
    cache_dir: Path | None = None,
) -> tuple[str, str]:
    cache_dir = cache_dir or CACHE / "http"
    path = cache_dir / f"{_key(method, url, params, data)}.json"
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        return cached["body"], cached["retrieved_at"]
    _wait(url)
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(3):
        try:
            response = requests.request(method, url, params=params, data=data, headers=headers, timeout=TIMEOUT_S)
        except requests.RequestException as error:
            if attempt == 2:
                raise FetchError(f"{url}: {error}") from error
            time.sleep(2 * (attempt + 1))
            continue
        if response.status_code in (429, 502, 503, 504) and attempt < 2:
            time.sleep(5 * (attempt + 1))
            continue
        if response.status_code >= 400:
            raise FetchError(f"{url}: HTTP {response.status_code} {response.text[:200]}")
        break
    retrieved_at = time.strftime("%Y-%m-%d")
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"url": url, "params": params, "method": method, "retrieved_at": retrieved_at, "body": response.text}
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return response.text, retrieved_at


def fetch_json(url: str, params: dict | None = None, method: str = "GET", data: str | None = None):
    body, retrieved_at = fetch_text(url, params, method, data)
    return json.loads(body), retrieved_at


def download(url: str, target: Path) -> Path:
    if target.exists():
        return target
    _wait(url)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)
    if response.status_code >= 400:
        raise FetchError(f"{url}: HTTP {response.status_code}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    return target
