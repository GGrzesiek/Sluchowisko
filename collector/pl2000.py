import math

SEMI_MAJOR_AXIS = 6_378_137.0
FLATTENING = 1 / 298.257222101
CENTRAL_MERIDIAN = 21.0
SCALE = 0.999923
FALSE_EASTING = 7_500_000.0

_N = FLATTENING / (2 - FLATTENING)
_E = math.sqrt(FLATTENING * (2 - FLATTENING))
_A = SEMI_MAJOR_AXIS / (1 + _N) * (1 + _N**2 / 4 + _N**4 / 64)
_ALPHA = (
    _N / 2 - 2 * _N**2 / 3 + 5 * _N**3 / 16 + 41 * _N**4 / 180,
    13 * _N**2 / 48 - 3 * _N**3 / 5 + 557 * _N**4 / 1440,
    61 * _N**3 / 240 - 103 * _N**4 / 140,
    49561 * _N**4 / 161280,
)
_BETA = (
    _N / 2 - 2 * _N**2 / 3 + 37 * _N**3 / 96 - _N**4 / 360,
    _N**2 / 48 + _N**3 / 15 - 437 * _N**4 / 1440,
    17 * _N**3 / 480 - 37 * _N**4 / 840,
    4397 * _N**4 / 161280,
)
_DELTA = (
    2 * _N - 2 * _N**2 / 3 - 2 * _N**3 + 116 * _N**4 / 45,
    7 * _N**2 / 3 - 8 * _N**3 / 5 - 227 * _N**4 / 45,
    56 * _N**3 / 15 - 136 * _N**4 / 35,
    4279 * _N**4 / 630,
)


def to_pl2000(lat: float, lon: float) -> tuple[float, float]:
    phi, lam = math.radians(lat), math.radians(lon - CENTRAL_MERIDIAN)
    t = math.sinh(math.atanh(math.sin(phi)) - _E * math.atanh(_E * math.sin(phi)))
    xi0, eta0 = math.atan2(t, math.cos(lam)), math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    xi = xi0 + sum(a * math.sin(2 * j * xi0) * math.cosh(2 * j * eta0) for j, a in enumerate(_ALPHA, 1))
    eta = eta0 + sum(a * math.cos(2 * j * xi0) * math.sinh(2 * j * eta0) for j, a in enumerate(_ALPHA, 1))
    return SCALE * _A * xi, FALSE_EASTING + SCALE * _A * eta


def from_pl2000(northing: float, easting: float) -> tuple[float, float]:
    xi, eta = northing / (SCALE * _A), (easting - FALSE_EASTING) / (SCALE * _A)
    xi0 = xi - sum(b * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    eta0 = eta - sum(b * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, b in enumerate(_BETA, 1))
    chi = math.asin(math.sin(xi0) / math.cosh(eta0))
    phi = chi + sum(d * math.sin(2 * j * chi) for j, d in enumerate(_DELTA, 1))
    return math.degrees(phi), CENTRAL_MERIDIAN + math.degrees(math.atan2(math.sinh(eta0), math.cos(xi0)))
