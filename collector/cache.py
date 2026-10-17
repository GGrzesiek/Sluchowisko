import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

USER_AGENT = "MuzeumWAutobusie/0.1 (https://github.com/GGrzesiek/opendatahackathon42)"
CACHE_DIR = REPO_ROOT / "cache"
MIN_INTERVAL_S = 1.0
RETRY_STATUSES = {429, 502, 503, 504}
RETRY_WAITS_S = (10, 30, 90)
TIMEOUT_S = 120

_last_request_at: dict[str, float] = {}


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class Cached:
    body: str
    retrieved_at: date

    def json(self) -> Any:
        return json.loads(self.body)


def describe(method: str, url: str, params: dict | None, form: dict | None, json_body: Any) -> dict:
    return {"method": method, "url": url, "params": params or {}, "form": form or {}, "json": json_body}


def cache_path(request: dict) -> Path:
    key = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return CACHE_DIR / urlsplit(request["url"]).hostname / f"{key}.json"


def lookup(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    form: dict | None = None,
    json_body: Any = None,
) -> Cached | None:
    path = cache_path(describe(method, url, params, form, json_body))
    if not path.exists():
        return None
    stored = json.loads(path.read_text(encoding="utf-8"))
    return Cached(stored["body"], date.fromisoformat(stored["retrieved_at"]))


def fetch(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    form: dict | None = None,
    json_body: Any = None,
    headers: dict | None = None,
) -> Cached:
    stored = lookup(method, url, params=params, form=form, json_body=json_body)
    if stored:
        return stored

    request = describe(method, url, params, form, json_body)
    path = cache_path(request)
    body = _download(request, headers or {})
    retrieved_at = date.today()
    stored = {**request, "retrieved_at": retrieved_at.isoformat(), "body": body}
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    partial.write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")
    partial.replace(path)
    return Cached(body, retrieved_at)


def _download(request: dict, headers: dict) -> str:
    method, url = request["method"], request["url"]
    host = urlsplit(url).hostname
    for attempt, wait in enumerate((0, *RETRY_WAITS_S)):
        time.sleep(wait)
        _respect_interval(host)
        try:
            response = requests.request(
                method,
                url,
                params=request["params"] or None,
                data=request["form"] or None,
                json=request["json"],
                headers={"User-Agent": USER_AGENT, **headers},
                timeout=TIMEOUT_S,
            )
        except requests.RequestException as error:
            if attempt == len(RETRY_WAITS_S):
                raise FetchError(f"{method} {url}: {error}") from error
            continue
        if response.status_code in RETRY_STATUSES and attempt < len(RETRY_WAITS_S):
            continue
        if not response.ok:
            raise FetchError(f"{method} {url}: HTTP {response.status_code} {response.text[:200]}")
        charset_given = "charset" in response.headers.get("Content-Type", "").lower()
        return response.content.decode(response.encoding if charset_given else "utf-8")
    raise FetchError(f"{method} {url}: no response")


def _respect_interval(host: str) -> None:
    elapsed = time.monotonic() - _last_request_at.get(host, float("-inf"))
    if elapsed < MIN_INTERVAL_S:
        time.sleep(MIN_INTERVAL_S - elapsed)
    _last_request_at[host] = time.monotonic()
