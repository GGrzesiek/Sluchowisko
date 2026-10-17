"""Check what the LLM returned before it reaches the database. LLMs invent coordinates and links."""
from urllib.parse import urlparse

from transit.llm_context import WARSAW_BBOX, distance_to_route_m

MAX_TEXT = 600
MAX_TITLE = 120


def _is_url(v) -> bool:
    try:
        u = urlparse(str(v))
        return u.scheme in ("http", "https") and bool(u.netloc)
    except ValueError:
        return False


def validate_places(data, route_stops: list[dict] | None = None, corridor_m: int = 400) -> dict:
    """Returns {"valid": [...places...], "rejected": [{"place": name, "errors": [...]}], "warnings": [...]}.

    A place is rejected if its location is wrong; individual bad facts are dropped with a warning.
    """
    if not isinstance(data, list):
        return {"valid": [], "rejected": [{"place": None, "errors": ["Top level must be a JSON array"]}],
                "warnings": []}

    valid, rejected, warnings = [], [], []
    seen_names = set()
    for i, p in enumerate(data):
        name = (p.get("name") or "").strip() if isinstance(p, dict) else ""
        label = name or f"#{i}"
        errors = []
        if not isinstance(p, dict):
            rejected.append({"place": label, "errors": ["Not an object"]})
            continue
        if not name:
            errors.append("missing name")
        if name.lower() in seen_names:
            errors.append("duplicate place")
        try:
            lat, lon = float(p["lat"]), float(p["lon"])
        except (KeyError, TypeError, ValueError):
            errors.append("missing or invalid lat/lon")
            lat = lon = None
        if lat is not None:
            b = WARSAW_BBOX
            if not (b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]):
                errors.append(f"outside Warsaw ({lat}, {lon}) - lat/lon swapped?")
            elif route_stops:
                d = distance_to_route_m(lat, lon, route_stops)
                if d > corridor_m:
                    errors.append(f"{round(d)} m from the route (limit {corridor_m} m)")

        good_facts = []
        for j, f in enumerate(p.get("facts") or []):
            problems = []
            if not isinstance(f, dict):
                warnings.append(f"{label}: fact #{j} is not an object")
                continue
            title, text = (f.get("title") or "").strip(), (f.get("text") or "").strip()
            if not title or len(title) > MAX_TITLE:
                problems.append("title missing/too long")
            if not text or len(text) > MAX_TEXT:
                problems.append(f"text missing/too long ({len(text)} chars)")
            if not _is_url(f.get("source_url")):
                problems.append("no valid source_url")
            try:
                f["priority"] = max(0, min(5, int(f.get("priority", 0))))
            except (TypeError, ValueError):
                f["priority"] = 0
            if problems:
                warnings.append(f"{label}: fact '{title[:40]}' dropped ({', '.join(problems)})")
            else:
                good_facts.append(f)
        if not good_facts and not errors:
            errors.append("no valid facts")

        if errors:
            rejected.append({"place": label, "errors": errors})
        else:
            seen_names.add(name.lower())
            valid.append({**p, "name": name, "lat": lat, "lon": lon, "facts": good_facts})
    return {"valid": valid, "rejected": rejected, "warnings": warnings}
