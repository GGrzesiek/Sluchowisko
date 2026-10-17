"""Client for the Warsaw open data API (new portal: dane.um.warszawa.pl).

Every call is: POST {WARSAW_API_BASE}/{action}
               headers: Authorization: <token>, Content-Type: application/json
               body:    JSON with the parameters, e.g. {"type": 2}

Responses are tolerated in several shapes: a plain list (what positions return), or
{"result": [...]} / {"data": [...]} like the old api.um.warszawa.pl platform.
"""
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

import requests
from django.conf import settings
from django.utils import timezone

DEFAULT_PAGE_SIZE = 1000
MAX_PAGES = 500  # safety stop so a misbehaving API can't loop forever
RETRIES = 3


class WarsawApiError(Exception):
    pass


@dataclass
class VehicleReading:
    vehicle_number: str
    line: str
    brigade: str
    lat: float
    lon: float
    time: datetime


def _request(action: str, body: dict | None = None, timeout: int = 20):
    """POST to the city API and return the payload (list or dict). Retries network hiccups."""
    if not settings.WARSAW_API_KEY:
        raise WarsawApiError("WARSAW_API_KEY is not set (see .env.example)")
    if not action:
        raise WarsawApiError("API action name is empty, set it in .env (see config/settings.py)")
    headers = {"Authorization": settings.WARSAW_API_KEY, "Content-Type": "application/json"}
    last_error = None
    for attempt in range(RETRIES):
        try:
            resp = requests.post(f"{settings.WARSAW_API_BASE}/{action}", json=body or {},
                                 headers=headers, timeout=timeout)
            if resp.status_code in (401, 403):
                raise WarsawApiError(f"Token rejected ({resp.status_code}): {resp.text[:200]}")
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                if payload.get("error") or payload.get("result") in ("false", False):
                    raise WarsawApiError(f"API error: {payload.get('error') or payload}")
                for key in ("result", "data", "results"):
                    if key in payload:
                        if isinstance(payload[key], str):
                            raise WarsawApiError(f"API error: {payload[key]}")
                        return payload[key]
                return payload
            raise WarsawApiError(f"Unexpected response: {str(payload)[:200]}")
        except (requests.RequestException, ValueError, WarsawApiError) as e:
            last_error = e
            msg = str(e).lower()
            if "token" in msg or "apikey" in msg or "action name" in msg:
                break  # a wrong token or config won't fix itself
            time.sleep(1.5 * (attempt + 1))
    raise WarsawApiError(str(last_error))


def _get_list(action: str, body: dict | None = None) -> list:
    result = _request(action, body)
    if not isinstance(result, list):
        raise WarsawApiError(f"Expected a list from {action}, got {type(result).__name__}")
    return result


def _flat(row) -> dict:
    """Turn the city's key/value rows into a plain dict. Handles all shapes seen so far:
    {"values": [{"key": k, "value": v}, ...]}   (stops, lines at stop)
    [{"key": k, "value": v}, ...]               (departures)
    {"Lines": ..., "Lat": ...}                  (positions, already flat)
    """
    if isinstance(row, dict) and isinstance(row.get("values"), list):
        row = row["values"]
    if isinstance(row, list):
        return {i["key"]: i.get("value") for i in row if isinstance(i, dict) and "key" in i}
    return row


def iter_paged(action: str, body: dict | None = None, page_size: int = DEFAULT_PAGE_SIZE) -> Iterator[dict]:
    """Yield all rows, following page/size pagination.

    Stops when a page is empty, shorter than page_size, or identical to the previous one
    (an endpoint without pagination just returns everything on page 1).
    """
    previous_first = None
    for page in range(1, MAX_PAGES + 1):
        rows = _get_list(action, {**(body or {}), "page": page, "size": page_size})
        if not rows or rows[0] == previous_first:
            return
        previous_first = rows[0]
        for row in rows:
            yield _flat(row)
        if len(rows) < page_size:
            return
    raise WarsawApiError(f"More than {MAX_PAGES} pages for {action}, stopping")


# ---------- Live positions ----------

def fetch_vehicle_positions(line: str | None = None, vehicle_type: int = 2) -> list[VehicleReading]:
    """Live positions, refreshed roughly every 10 s. type: 1 = bus, 2 = tram.

    The new API ignores the `line` parameter, so we also filter here.
    """
    body = {"type": vehicle_type}
    if line:
        body["line"] = str(line)
    readings = []
    for r in _get_list(settings.WARSAW_POSITIONS_ACTION, body):
        try:
            if line and str(r["Lines"]).strip() != str(line):
                continue
            t = datetime.strptime(r["Time"], "%Y-%m-%d %H:%M:%S")
            readings.append(
                VehicleReading(
                    vehicle_number=str(r["VehicleNumber"]),
                    line=str(r["Lines"]).strip(),
                    brigade=str(r.get("Brigade", "")).strip(),
                    lat=float(r["Lat"]),
                    lon=float(r["Lon"]),
                    time=timezone.make_aware(t),  # API returns Warsaw local time
                )
            )
        except (KeyError, ValueError, TypeError):
            continue  # skip malformed rows, the feed has some
    return readings


# ---------- Stops, lines at stop, departures ----------
# Body parameter names follow the old API (busstopId / busstopNr / line).
# If the docs' "Parametry API" tab says otherwise, change them here.
STOP_ID_PARAM, STOP_NR_PARAM, LINE_PARAM = "busstopId", "busstopNr", "line"


def fetch_stops() -> list[dict]:
    """All stop posts: zespol, slupek, nazwa_zespolu, id_ulicy, szer_geo, dlug_geo, kierunek, ..."""
    if settings.WARSAW_STOPS_PAGE_SIZE:
        return list(iter_paged(settings.WARSAW_STOPS_ACTION, page_size=settings.WARSAW_STOPS_PAGE_SIZE))
    return [_flat(r) for r in _get_list(settings.WARSAW_STOPS_ACTION, {})]


def fetch_lines_at_stop(zespol: str, slupek: str) -> list[str]:
    """Lines that stop at one stop post, e.g. ["17", "33"]."""
    rows = _get_list(settings.WARSAW_LINES_AT_STOP_ACTION, {STOP_ID_PARAM: zespol, STOP_NR_PARAM: slupek})
    return [str(r["linia"]).strip() for r in map(_flat, rows) if r.get("linia")]


def fetch_departures(zespol: str, slupek: str, line: str) -> list[dict]:
    """Departures of a line from a stop post: brygada, kierunek, trasa, czas ("HH:MM:SS", can be >24h)."""
    rows = _get_list(settings.WARSAW_DEPARTURES_ACTION,
                     {STOP_ID_PARAM: zespol, STOP_NR_PARAM: slupek, LINE_PARAM: line})
    return [r for r in map(_flat, rows) if r.get("czas")]