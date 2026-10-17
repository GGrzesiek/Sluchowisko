import math

EARTH_RADIUS_M = 6_371_000


def _to_metres(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    scale = math.radians(1) * EARTH_RADIUS_M
    return (lon - origin_lon) * scale * math.cos(math.radians(origin_lat)), (lat - origin_lat) * scale


def distance_m(lat: float, lon: float, other_lat: float, other_lon: float) -> int:
    x, y = _to_metres(other_lat, other_lon, lat, lon)
    return round(math.hypot(x, y))


def distance_to_line_m(lat: float, lon: float, line: list[tuple[float, float]]) -> int:
    points = [_to_metres(point_lat, point_lon, lat, lon) for point_lat, point_lon in line]
    if len(points) == 1:
        return round(math.hypot(*points[0]))
    return round(min(_distance_to_segment(start, end) for start, end in zip(points, points[1:], strict=False)))


def inside_ring(lat: float, lon: float, ring: list[tuple[float, float]]) -> bool:
    if len(ring) < 4 or ring[0] != ring[-1]:
        return False
    inside = False
    for (lat1, lon1), (lat2, lon2) in zip(ring, ring[1:], strict=False):
        if (lat1 > lat) != (lat2 > lat) and lon < lon1 + (lat - lat1) * (lon2 - lon1) / (lat2 - lat1):
            inside = not inside
    return inside


def _distance_to_segment(start: tuple[float, float], end: tuple[float, float]) -> float:
    (x1, y1), (x2, y2) = start, end
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    t = 0.0 if length_sq == 0 else max(0.0, min(1.0, -(x1 * dx + y1 * dy) / length_sq))
    return math.hypot(x1 + t * dx, y1 + t * dy)
