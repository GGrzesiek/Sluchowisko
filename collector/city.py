import os
import statistics
import unicodedata
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from datetime import date

from collector import cache
from collector.geo import distance_m
from collector.pl2000 import from_pl2000, to_pl2000
from collector.schema import RADIUS_M, Stop, normalize_text

API = "https://dane.um.warszawa.pl/api/action"
TERMS = "https://dane.um.warszawa.pl/terms-of-use"
LICENSE = (
    "Dane nieobjęte prawem autorskim, ponowne wykorzystywanie bez ograniczeń "
    "(Regulamin portalu Otwarte dane m.st. Warszawy, §8)"
)
WFS = "https://wfs.um.warszawa.pl/serwis"
WFS_CAPABILITIES = f"{WFS}?SERVICE=WFS&REQUEST=GetCapabilities"
WFS_LICENSE = "Usługa WFS m.st. Warszawy: AccessConstraints „none”"
WFS_MAX_FEATURES = 1000
RCN_YEAR = 2025
RCN_MARKETS = ("rynekPierwotny", "rynekWtorny")
MIN_TRANSACTIONS = 5
BUDGET_YEARS = range(2015, 2027)
LARGEST_TREES = 3


@dataclass(frozen=True)
class Fact:
    title: str
    url: str
    license: str
    license_url: str
    retrieved_at: date
    template: str
    values: dict[str, str]


def facts(stop: Stop) -> list[Fact]:
    return flat_prices(stop) + budget_projects(stop) + largest_trees(stop)


def thousands(value: float) -> str:
    return f"{round(value):,}".replace(",", " ")


def api_district(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name.replace("ł", "l").replace("Ł", "L"))
    return "".join(char for char in plain if not unicodedata.combining(char) and char.isalnum())


def _api(action: str, body: dict) -> cache.Cached:
    headers = {"Authorization": os.environ.get("ZTM_API_KEY", ""), "Content-Type": "application/json"}
    return cache.fetch("POST", f"{API}/{action}", json_body=body, headers=headers)


def _wfs(type_name: str, east: tuple[float, float], north: tuple[float, float]) -> tuple[ElementTree.Element, date]:
    response = cache.fetch(
        "GET",
        WFS,
        params={
            "SERVICE": "WFS",
            "VERSION": "1.1.0",
            "REQUEST": "GetFeature",
            "TYPENAME": type_name,
            "BBOX": f"{east[0]:.0f},{north[0]:.0f},{east[1]:.0f},{north[1]:.0f}",
        },
    )
    return ElementTree.fromstring(response.body.encode()), response.retrieved_at


def _features(root: ElementTree.Element) -> list[dict[str, str]]:
    found = []
    for member in root.iter("{http://www.opengis.net/gml}featureMember"):
        for feature in member:
            fields = {child.tag.split("}")[1]: (child.text or "") for child in feature if len(child) == 0}
            position = feature.find(".//{http://www.opengis.net/gml}pos")
            if position is not None:
                fields["pos"] = position.text or ""
            found.append(fields)
    return found


def districts(stop: Stop) -> list[str]:
    north, east = to_pl2000(stop.lat, stop.lon)
    root, _ = _wfs(
        "ns92528565:GRANICE_DZIELNIC", (east - RADIUS_M, east + RADIUS_M), (north - RADIUS_M, north + RADIUS_M)
    )
    return sorted({fields["DZIELNICA"] for fields in _features(root) if fields.get("DZIELNICA")})


def flat_prices(stop: Stop) -> list[Fact]:
    prices: list[float] = []
    retrieved: list[date] = []
    for district in districts(stop):
        for market in RCN_MARKETS:
            response = _api(
                "get_bgk_rcn",
                {
                    "dzielnica": api_district(district),
                    "rodzajNieruchomosci": "nieruchomoscLokalowa",
                    "rodzajRynku": market,
                    "rok": RCN_YEAR,
                },
            )
            retrieved.append(response.retrieved_at)
            for feature in response.json().get("features", []):
                if price := _price_per_m2(feature, stop):
                    prices.append(price)
    if len(prices) < MIN_TRANSACTIONS:
        return []
    return [
        Fact(
            title=f"Rejestr cen nieruchomości m.st. Warszawy: lokale, {RCN_YEAR} r.",
            url=f"{API}/get_bgk_rcn",
            license=LICENSE,
            license_url=TERMS,
            retrieved_at=min(retrieved),
            template="city.flat_prices",
            values={
                "year": str(RCN_YEAR),
                "name": stop.name,
                "price": thousands(statistics.median(prices)),
                "count": str(len(prices)),
            },
        )
    ]


def _price_per_m2(feature: dict, stop: Stop) -> float | None:
    properties = feature.get("properties") or {}
    transaction = (properties.get("nieruchomosc") or {}).get("transakcja") or {}
    area, price = properties.get("powUzytkowaLokalu"), properties.get("cenaLokaluBrutto")
    coordinates = (feature.get("geometry") or {}).get("coordinates") or []
    if (
        properties.get("funkcjaLokalu") != "mieszkalna"
        or transaction.get("rodzajTransakcji") != "wolnyRynek"
        or not area
        or not price
        or len(coordinates) != 2
    ):
        return None
    lat, lon = from_pl2000(coordinates[1], coordinates[0])
    return price / area if distance_m(stop.lat, stop.lon, lat, lon) <= RADIUS_M else None


def budget_projects(stop: Stop) -> list[Fact]:
    found = []
    for year in BUDGET_YEARS:
        response = _api("get_cks_budzet_obywatelski", {"rok": year, "status": "zrealizowane"})
        for project in response.json():
            distances = [distance_m(stop.lat, stop.lon, lat, lon) for lat, lon in _points(project)]
            distance = min(distances, default=RADIUS_M + 1)
            title = normalize_text(project.get("title") or "")
            if distance > RADIUS_M or not title or not str(project.get("url") or "").startswith("http"):
                continue
            values = {"year": str(year), "title": title, "distance": str(distance), "name": stop.name}
            template = "city.budget_no_cost"
            if project.get("cost"):
                values["cost"] = thousands(float(project["cost"]))
                template = "city.budget"
            found.append(
                (
                    year,
                    distance,
                    project["id"],
                    Fact(
                        title=title,
                        url=project["url"],
                        license=LICENSE,
                        license_url=TERMS,
                        retrieved_at=response.retrieved_at,
                        template=template,
                        values=values,
                    ),
                )
            )
    return [fact for *_, fact in sorted(found, key=lambda item: item[:3])]


def _points(project: dict) -> list[tuple[float, float]]:
    points = []
    for point in [project, *(project.get("pins") or [])]:
        try:
            points.append((float(point["lat"]), float(point["lng"])))
        except (KeyError, TypeError, ValueError):
            continue
    return points


def largest_trees(stop: Stop) -> list[Fact]:
    north, east = to_pl2000(stop.lat, stop.lon)
    trees: dict[str, tuple[dict[str, str], int]] = {}
    retrieved: list[date] = []
    square = ((east - RADIUS_M, east + RADIUS_M), (north - RADIUS_M, north + RADIUS_M))
    for fields, retrieved_at in _tile("ns92528565:ZIELEN_DRZEWA", *square):
        retrieved.append(retrieved_at)
        tree_east, tree_north = (float(value) for value in fields["pos"].split())
        distance = distance_m(stop.lat, stop.lon, *from_pl2000(tree_north, tree_east))
        if distance <= RADIUS_M and _complete(fields):
            trees[fields["OBJECTID"]] = (fields, distance)

    largest = sorted(trees.values(), key=lambda tree: (-_girth(tree[0]), int(tree[0]["OBJECTID"])))
    return [
        Fact(
            title="Rejestr drzew m.st. Warszawy (usługa WFS, warstwa ZIELEN_DRZEWA)",
            url=WFS_CAPABILITIES,
            license=WFS_LICENSE,
            license_url=WFS_CAPABILITIES,
            retrieved_at=min(retrieved),
            template="city.tree",
            values={
                "distance": str(distance),
                "name": stop.name,
                "species": fields["NAZWA_POLSKA"],
                "latin": fields["NAZWA_LACINSKA"],
                "girth": fields["OBWOD_PNIA_W_CM"],
                "height": fields["WYSOKOSC"],
                "year": fields["AKTUALNOSC_DANYCH"][:4],
            },
        )
        for fields, distance in largest[:LARGEST_TREES]
    ]


def _complete(fields: dict[str, str]) -> bool:
    keys = ("OBJECTID", "NAZWA_POLSKA", "NAZWA_LACINSKA", "OBWOD_PNIA_W_CM", "WYSOKOSC", "AKTUALNOSC_DANYCH")
    return all(fields.get(key) for key in keys) and fields["AKTUALNOSC_DANYCH"][:4].isdigit() and _girth(fields) > 0


def _girth(fields: dict[str, str]) -> float:
    trunks = []
    for part in fields["OBWOD_PNIA_W_CM"].split(","):
        try:
            trunks.append(float(part))
        except ValueError:
            return 0
    return max(trunks)


def _tile(type_name: str, east: tuple[float, float], north: tuple[float, float]) -> list[tuple[dict, date]]:
    root, retrieved_at = _wfs(type_name, east, north)
    features = _features(root)
    if len(features) < WFS_MAX_FEATURES:
        return [(fields, retrieved_at) for fields in features]
    mid_east, mid_north = sum(east) / 2, sum(north) / 2
    return [
        found
        for half_east in ((east[0], mid_east), (mid_east, east[1]))
        for half_north in ((north[0], mid_north), (mid_north, north[1]))
        for found in _tile(type_name, half_east, half_north)
    ]
