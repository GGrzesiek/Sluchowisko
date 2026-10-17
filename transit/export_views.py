from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .aggregate import COLUMNS, build_snapshot
from .warsaw_api import WarsawApiError

TYPES = {"tram": 2, "bus": 1, "2": 2, "1": 1}


@api_view(["GET"])
def snapshot(request):
    """Flat JSON array: stops + live vehicles joined by location. Not paginated on purpose.

    ?type=tram|bus  ?line=17  ?only=stops|vehicles  ?radius=500  ?download=1
    """
    q = request.query_params
    vtype = TYPES.get(q.get("type", "tram"))
    if vtype is None:
        return Response({"detail": "type must be tram or bus"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        rows = build_snapshot(vehicle_type=vtype, line=q.get("line") or None, only=q.get("only"),
                              radius_m=min(int(q.get("radius", 500)), 2000))
    except WarsawApiError as e:
        return Response({"detail": f"City API unavailable: {e}"}, status=status.HTTP_502_BAD_GATEWAY)
    except ValueError:
        return Response({"detail": "radius must be a number"}, status=status.HTTP_400_BAD_REQUEST)
    resp = Response(rows)
    if q.get("download"):
        resp["Content-Disposition"] = f'attachment; filename="snapshot_{q.get("line") or q.get("type", "tram")}.json"'
    return resp


@api_view(["GET"])
def snapshot_schema(request):
    """Column list, so Kuba knows the keys without reading code."""
    return Response({"columns": COLUMNS})

@api_view(["GET"])
def active_lines(request):
    """Lines with vehicles on the road right now, from live positions (trams + buses).

    ?type=tram|bus (default both)  ?max_age=300 seconds  ?vehicles=1 to include each vehicle
    """
    from collections import defaultdict

    from django.core.cache import cache
    from django.utils import timezone

    from .sync import classify_line
    from .warsaw_api import fetch_vehicle_positions

    q = request.query_params
    wanted = [TYPES[q["type"]]] if q.get("type") in TYPES else [2, 1]
    max_age = int(q.get("max_age", 300))
    now = timezone.now()

    groups = defaultdict(list)
    try:
        for vtype in wanted:
            key = f"active:{vtype}"
            readings = cache.get(key)
            if readings is None:
                readings = fetch_vehicle_positions(vehicle_type=vtype)  # no line = whole city
                cache.set(key, readings, 10)
            for r in readings:
                if (now - r.time).total_seconds() <= max_age:  # drop vehicles that stopped reporting
                    groups[(r.line, vtype)].append(r)
    except WarsawApiError as e:
        return Response({"detail": f"City API unavailable: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

    rows = []
    for (line, vtype), rs in groups.items():
        row = {
            "line": line,
            "type": "tram" if vtype == 2 else "bus",
            "kind": classify_line(line),  # tram / bus / night / suburban / express / replacement
            "vehicles_active": len(rs),
            "last_update": max(r.time for r in rs).isoformat(timespec="seconds"),
        }
        if q.get("vehicles"):
            row["vehicles"] = [{"vehicle_number": r.vehicle_number, "brigade": r.brigade, "lat": r.lat,
                                "lon": r.lon, "time": r.time.isoformat(timespec="seconds")} for r in rs]
        rows.append(row)
    rows.sort(key=lambda x: (x["type"] != "tram", len(x["line"]), x["line"]))
    return Response({
        "fetched_at": now.isoformat(timespec="seconds"),
        "lines_active": len(rows),
        "trams": sum(r["vehicles_active"] for r in rows if r["type"] == "tram"),
        "buses": sum(r["vehicles_active"] for r in rows if r["type"] == "bus"),
        "lines": rows,
    })