import json
import threading
import time as clock
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from collector import cache, city, commons, images, osm, warszawikia, web, wikidata, wikipedia
from collector.check import check
from collector.collect import collect, collect_many, demo_groups
from collector.geo import distance_m, distance_to_line_m
from collector.html_text import to_text
from collector.pl2000 import from_pl2000, to_pl2000
from collector.schema import load
from collector.sources import Book
from collector.stops import UnknownStopGroup, load_stop
from transit.models import Stop as StopRow

LAT, LON = 52.2447, 20.9772


def way(way_id, name, line, **tags):
    return {
        "type": "way",
        "id": way_id,
        "tags": {"highway": "residential", "name": name, **tags},
        "geometry": [{"lat": lat, "lon": lon} for lat, lon in line],
    }


def boundary(area_id, level, name, **tags):
    return {
        "type": "area",
        "id": area_id,
        "tags": {"boundary": "administrative", "admin_level": level, "name": name, **tags},
    }


OVERPASS = {
    "elements": [
        boundary(3600000001, "8", "Warszawa"),
        boundary(3600000002, "9", "Wola", wikipedia="pl:Wola (Warszawa)"),
        {"type": "node", "id": 10, "lat": 52.2480, "lon": 20.9772, "tags": {"place": "neighbourhood", "name": "Dalej"}},
        {"type": "node", "id": 11, "lat": 52.2460, "lon": 20.9772, "tags": {"place": "quarter", "name": "Bliżej"}},
        way(1, "Okopowa", [(52.2440, 20.9770), (52.2450, 20.9770)], old_name="Okopowa Wałowa"),
        way(2, "Okopowa", [(52.2480, 20.9770), (52.2490, 20.9770)], **{"name:etymology:wikidata": "Q1"}),
        way(3, "Młynarska", [(52.2470, 20.9750), (52.2470, 20.9800)], wikipedia="pl:Ulica Młynarska w Warszawie"),
        way(4, "Cm. Żydowski", [(52.2447, 20.9772), (52.2448, 20.9772)], highway="platform"),
        {
            "type": "way",
            "id": 20,
            "tags": {"building": "yes", "name": "Hala Testowa", "wikidata": "Q100", "surface": "asphalt"},
            "geometry": [
                {"lat": lat, "lon": lon}
                for lat, lon in [(52.2446, 20.9771), (52.2446, 20.9773), (52.2448, 20.9773), (52.2446, 20.9771)]
            ],
        },
        {"type": "node", "id": 21, "lat": 52.2452, "lon": 20.9772, "tags": {"historic": "memorial", "name": "Tablica"}},
        {"type": "node", "id": 22, "lat": 52.2449, "lon": 20.9772, "tags": {"historic": "memorial"}},
        {
            "type": "relation",
            "id": 23,
            "tags": {"leisure": "park", "name": "Park Testowy", "wikidata": "Q200"},
            "members": [
                {
                    "type": "way",
                    "role": "outer",
                    "geometry": [{"lat": 52.2470, "lon": 20.9750}, {"lat": 52.2470, "lon": 20.98}],
                }
            ],
        },
    ]
}


def test_distance_to_a_point_and_to_a_line():
    assert distance_m(LAT, LON, LAT + 0.001, LON) == 111
    assert distance_to_line_m(LAT, LON, [(LAT + 0.001, LON - 0.01), (LAT + 0.001, LON + 0.01)]) == 111
    assert distance_to_line_m(LAT, LON, [(LAT + 0.001, LON)]) == 111


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(cache, "MIN_INTERVAL_S", 0)
    monkeypatch.setattr(cache, "RETRY_WAITS_S", (0, 0))
    return tmp_path / "cache"


class FakeResponse:
    def __init__(self, status_code, body, content_type="application/json"):
        self.status_code = status_code
        self.ok = status_code < 400
        self.content = body if isinstance(body, bytes) else body.encode()
        self.text = self.content.decode(errors="replace")
        self.headers = {"Content-Type": content_type}
        self.encoding = content_type.split("charset=")[1] if "charset=" in content_type else None


def test_fetch_downloads_once_then_reads_the_cache(cache_dir, monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        calls.append(kwargs)
        return FakeResponse(200, '{"nazwa": "Żytnia"}')

    monkeypatch.setattr(requests, "request", request)
    first = cache.fetch("POST", "https://example.org/api", form={"data": "q"})
    second = cache.fetch("POST", "https://example.org/api", form={"data": "q"})

    assert first == second
    assert second.json() == {"nazwa": "Żytnia"}
    assert len(calls) == 1
    assert calls[0]["headers"]["User-Agent"] == cache.USER_AGENT


def test_fetch_keeps_headers_out_of_the_cache(cache_dir, monkeypatch):
    monkeypatch.setattr(requests, "request", lambda method, url, **kwargs: FakeResponse(200, "{}"))
    cache.fetch("POST", "https://example.org/api", json_body={"rok": 2022}, headers={"Authorization": "sekret"})

    stored = next(cache_dir.rglob("*.json")).read_text(encoding="utf-8")
    assert "sekret" not in stored
    assert json.loads(stored)["json"] == {"rok": 2022}


def test_fetch_retries_a_busy_server_and_never_caches_an_error(cache_dir, monkeypatch):
    replies = iter([FakeResponse(504, "busy"), FakeResponse(504, "busy"), FakeResponse(504, "busy")])
    monkeypatch.setattr(requests, "request", lambda method, url, **kwargs: next(replies))

    with pytest.raises(cache.FetchError, match="HTTP 504"):
        cache.fetch("GET", "https://example.org/api")
    assert not cache_dir.exists()


@pytest.fixture
def stop_rows(db):
    StopRow.objects.create(zespol="5086", slupek="02", name="Cm. Żydowski", lat=52.2448, lon=20.9775)
    StopRow.objects.create(zespol="5086", slupek="01", name="Cm. Żydowski", lat=52.2446, lon=20.9769)
    StopRow.objects.create(zespol="5087", slupek="01", name="Niska", lat=52.2470, lon=20.9800)


def test_load_stop_takes_all_poles_of_the_group_and_their_mean(stop_rows):
    stop = load_stop("5086")

    assert stop.name == "Cm. Żydowski"
    assert [pole.pole for pole in stop.poles] == ["01", "02"]
    assert (stop.lat, stop.lon) == (52.2447, 20.9772)


def test_load_stop_rejects_an_unknown_group(stop_rows):
    with pytest.raises(UnknownStopGroup, match="9999"):
        load_stop("9999")


def test_area_has_the_district_the_nearest_neighbourhood_and_nearby_objects(monkeypatch):
    monkeypatch.setattr(osm, "overpass", lambda query: OVERPASS)
    area = osm.load_area(LAT, LON)

    assert area.district == "Wola"
    assert area.neighbourhood == "Bliżej"
    assert [(o.id, o.name, o.kind, o.distance_m) for o in area.objects] == [
        ("o1", "Hala Testowa", "building", 0),
        ("o2", "Okopowa", "street", 14),
        ("o3", "Tablica", "memorial", 56),
        ("o4", "Młynarska", "street", 256),
        ("o5", "Park Testowy", "park", 256),
    ]
    assert area.street_ids == {"o2", "o4"}
    hala, okopowa, _, mlynarska, park = area.objects
    assert hala.tags == {"building": "yes", "name": "Hala Testowa", "wikidata": "Q100"}
    assert okopowa.osm_id == "way/1"
    assert okopowa.old_names == ["Okopowa Wałowa"]
    assert okopowa.named_after == "Q1"
    assert mlynarska.wikipedia == "pl:Ulica Młynarska w Warszawie"
    assert park.osm_id == "relation/23"


def test_area_prefers_the_city_neighbourhood_boundary(monkeypatch):
    msi = boundary(3600000004, "10", "Powązki")
    containing = {"type": "area", "id": 3600000003, "tags": {"place": "neighbourhood", "name": "Mirów"}}
    monkeypatch.setattr(osm, "overpass", lambda query: {"elements": [*OVERPASS["elements"], containing, msi]})

    assert osm.load_area(LAT, LON).neighbourhood == "Powązki"


def test_area_prefers_a_neighbourhood_that_contains_the_stop(monkeypatch):
    containing = {"type": "area", "id": 3600000003, "tags": {"place": "neighbourhood", "name": "Mirów"}}
    monkeypatch.setattr(osm, "overpass", lambda query: {"elements": [*OVERPASS["elements"], containing]})

    assert osm.load_area(LAT, LON).neighbourhood == "Mirów"


def test_overpass_uses_any_cached_server_before_the_network(cache_dir, monkeypatch):
    query = osm.stop_query(LAT, LON)
    path = cache.cache_path(cache.describe("POST", osm.OVERPASS_URLS[1], None, {"data": query}, None))
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"retrieved_at": "2026-10-17", "body": json.dumps(OVERPASS)}), encoding="utf-8")
    monkeypatch.setattr(requests, "request", pytest.fail)

    assert osm.overpass(query) == OVERPASS


def item(qid):
    return {"rank": "normal", "mainsnak": {"snaktype": "value", "datavalue": {"value": {"id": qid}}}}


def time(value, precision):
    return {
        "rank": "normal",
        "mainsnak": {"snaktype": "value", "datavalue": {"value": {"time": value, "precision": precision}}},
    }


def entity(qid, label=None, description=None, sitelinks=(), **claims):
    found = {
        "id": qid,
        "claims": claims,
        "sitelinks": {site: {"site": site, "title": title} for site, title in sitelinks},
    }
    if label:
        found["labels"] = {"pl": {"language": "pl", "value": label}}
    if description:
        found["descriptions"] = {"pl": {"language": "pl", "value": description}}
    return found


WIKIDATA = {
    "Q100": entity(
        "Q100",
        "Hala Testowa",
        "hala targowa w Warszawie",
        [("plwiki", "Hala Testowa"), ("enwiki", "Test Hall"), ("dewiki", "Testhalle"), ("commonswiki", "Hala")],
        P138=[item("Q300")],
        P1435=[item("Q400")],
        P571=[time("+1902-00-00T00:00:00Z", 9)],
    ),
    "Q1": entity(
        "Q1",
        "Jan Testowy",
        "architekt",
        [("plwiki", "Jan Testowy")],
        P569=[time("+1850-03-07T00:00:00Z", 11)],
        P570=[time("+1910-00-00T00:00:00Z", 9)],
    ),
    "Q300": entity("Q300", "Anna Testowa"),
    "Q400": entity("Q400", "zabytek rejestrowy"),
    "Q200": entity("Q200", None, "park w Warszawie"),
}


REDIRECTED_ITEMS = {"Q101": "Q100"}


def page(title, extract, coordinates=None, image=None):
    found = {"pageid": 1, "ns": 0, "title": title, "extract": extract}
    if image:
        found["pageimage"] = image
    if coordinates:
        found["coordinates"] = [{"lat": coordinates[0], "lon": coordinates[1], "primary": True, "globe": "earth"}]
    return found


HALA_TEXT = (
    "Hala Testowa – hala targowa.\n\n\n== Historia ==\nZbudowana w 1902.\nDruga  linia.\n\n\n"
    "== Przypisy ==\nPrzypis.\n\n\n=== Uwagi ===\nUkryte.\n\n\n== Architektura ==\nCegła."
)
WIKIPEDIA = {
    "Hala Testowa": page("Hala Testowa", HALA_TEXT, (52.2447, 20.9772), "Hala_Testowa.jpg"),
    "Jan Testowy": page(
        "Jan Testowy", "Jan Testowy – architekt.\n\n\n== Życiorys ==\nUrodził się w Warszawie.", image="Jan_Testowy.png"
    ),
    "Wola (Warszawa)": page("Wola (Warszawa)", "Wola – dzielnica Warszawy."),
    "Młynarska (Warszawa)": page("Młynarska (Warszawa)", "Młynarska – ulica na Woli."),
    "Cm. Żydowski": page("Cm. Żydowski", "Cm. Żydowski – wzgórze w Sudetach.", (50.29, 17.55)),
}
REDIRECTS = {"Ulica Młynarska w Warszawie": "Młynarska (Warszawa)"}
GEOSEARCH = [{"title": "Hala Testowa", "dist": 10.4}, {"title": "Pomnik Daleki", "dist": 390.0}]


def commons_file(title, license, description=None, artist=None, date=None, mime="image/jpeg"):
    meta = {"LicenseShortName": license, "ImageDescription": description, "Artist": artist, "DateTimeOriginal": date}
    page_name = title.replace(" ", "_")
    return {
        "ns": 6,
        "title": title,
        "imageinfo": [
            {
                "mime": mime,
                "thumbmime": mime,
                "url": f"https://upload.wikimedia.org/{page_name}",
                "thumburl": f"https://upload.wikimedia.org/thumb/{page_name}",
                "descriptionurl": f"https://commons.wikimedia.org/wiki/{page_name}",
                "extmetadata": {key: {"value": value} for key, value in meta.items() if value is not None},
            }
        ],
    }


COMMONS = {
    "File:Hala Testowa.jpg": commons_file(
        "File:Hala Testowa.jpg",
        "Public domain",
        "<b>Hala</b> w&nbsp;1910 r.",
        '<a href="//commons.wikimedia.org/wiki/User:X">Jan Fotograf</a><span style="display: none;">hidden</span>',
        "około 1910",
    ),
    "File:Jan Testowy.png": commons_file("File:Jan Testowy.png", "CC BY 4.0", mime="image/png"),
    "File:Ulica nocą.jpg": commons_file("File:Ulica nocą.jpg", "CC BY-NC-SA 4.0", date="2019-05-01 22:00:00"),
    "File:Zakazane.jpg": commons_file("File:Zakazane.jpg", "CC BY-ND 4.0", "Nie wolno przerabiać"),
}
COMMONS_GEOSEARCH = [
    {"title": "File:Ulica nocą.jpg", "dist": 50.0},
    {"title": "File:Zakazane.jpg", "dist": 60.0},
    {"title": "File:Hala Testowa.jpg", "dist": 70.0},
]


def at(lat_offset_m, lon_offset_m=0):
    north, east = to_pl2000(LAT + lat_offset_m / 111_320, LON + lon_offset_m / 68_200)
    return east, north


def flat(offset_m, price, area, market="wolnyRynek", function="mieszkalna"):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": list(at(offset_m))},
        "properties": {
            "funkcjaLokalu": function,
            "powUzytkowaLokalu": area,
            "cenaLokaluBrutto": price,
            "nieruchomosc": {"transakcja": {"rodzajTransakcji": market}},
        },
    }


FLATS = [flat(10 * n, 15_000 * (50 + n), 50 + n) for n in range(5)] + [
    flat(20, 1_000_000, 10, market="bezprzetargowa"),
    flat(20, 1_000_000, 10, function="usługowa"),
    flat(900, 1_000_000, 10),
]
PROJECT = {
    "id": 18469,
    "title": "Nowy  plac zabaw",
    "url": "http://bo.um.warszawa.pl/processes/na-rok-2020/f/6/projects/18469",
    "cost": "930000.0",
    "firstName": "Anna",
    "lastName": "Kowalska",
    "lat": "52.30",
    "lng": "21.10",
    "pins": [{"lat": LAT + 100 / 111_320, "lng": LON}],
}
TREES = [
    ("1", 50, "lipa drobnolistna", "Tilia cordata Mill.", "289", "17", "2026-01-02T00:00:00"),
    ("2", 120, "robinia biała", "Robinia pseudoacacia L.", "55, 300", "18", "2023-05-01T00:00:00"),
    ("3", 150, "topola czarna", "Populus nigra L.", "241", "34", "2012-12-17T00:00:00"),
    ("4", 160, "klon", "Acer L.", "100", "8", "2012-12-17T00:00:00"),
    ("5", 380, "dąb", "Quercus L.", "500", "", "2012-12-17T00:00:00"),
    ("6", 700, "buk", "Fagus L.", "600", "20", "2012-12-17T00:00:00"),
]


def wfs_answer(params):
    east_min, north_min, east_max, north_max = (float(value) for value in params["BBOX"].split(","))
    if params["TYPENAME"].endswith("GRANICE_DZIELNIC"):
        members = ["<ns:GRANICE_DZIELNIC><ns:DZIELNICA>Śródmieście</ns:DZIELNICA></ns:GRANICE_DZIELNIC>"]
    else:
        members = []
        for object_id, offset, species, latin, girth, height, updated in TREES:
            east, north = at(offset)
            if east_min <= east < east_max and north_min <= north < north_max:
                members.append(
                    f"<ns:ZIELEN_DRZEWA><ns:OBJECTID>{object_id}</ns:OBJECTID><ns:NAZWA_POLSKA>{species}</ns:NAZWA_POLSKA>"
                    f"<ns:NAZWA_LACINSKA>{latin}</ns:NAZWA_LACINSKA><ns:WYSOKOSC>{height}</ns:WYSOKOSC>"
                    f"<ns:OBWOD_PNIA_W_CM>{girth}</ns:OBWOD_PNIA_W_CM><ns:AKTUALNOSC_DANYCH>{updated}</ns:AKTUALNOSC_DANYCH>"
                    f"<ns:SHAPE><gml:Point><gml:pos>{east} {north}</gml:pos></gml:Point></ns:SHAPE></ns:ZIELEN_DRZEWA>"
                )
    body = "".join(f"<gml:featureMember>{member}</gml:featureMember>" for member in members)
    return (
        '<wfs:FeatureCollection xmlns:gml="http://www.opengis.net/gml" xmlns:wfs="http://www.opengis.net/wfs" '
        f'xmlns:ns="http://fdo.osgeo.org/schemas/feature/ns">{body}</wfs:FeatureCollection>'
    )


FANDOM_HTML = (
    '<div class="mw-parser-output"><div id="disambig"><figure>ikona</figure><i>Ten artykuł dotyczy ulicy.</i></div>'
    '<aside class="portable-infobox">długość 2 200</aside>'
    '<p><b>Ulica Okopowa</b> – ulica na <a>Woli</a>.<sup class="reference">[1]</sup></p>'
    '<div class="toc">Spis treści</div>'
    '<h2><span class="mw-headline">Historia</span></h2><p>Podczas okupacji: <i>Dammstrasse</i>.</p>'
    '<h2><span class="mw-headline">Galeria</span></h2><div class="wikia-gallery">zdjęcie</div>'
    '<h2><span class="mw-headline">Przypisy</span></h2><ol class="references"><li>przypis</li></ol></div>'
)
WARSZAWIKIA_SEARCH = {
    "Zespół przystankowy Cm. Żydowski": ["Zespół przystankowy Inny", "Zespół przystankowy Cmentarz Żydowski"],
    "Okopowa": ["Ulica Przyokopowa", "Ulica Okopowa"],
    "Młynarska": ["Młynarska (osiedle)"],
}
WARSZAWIKIA_WIKITEXT = {
    "Zespół przystankowy Inny": "{{Zespół|Inny|9999}} – inny zespół.",
    "Zespół przystankowy Cmentarz Żydowski": "{{Zespół|Cmentarz Żydowski|5086}} – zespół przystanków.",
}
WARSZAWIKIA_HTML = {
    "Ulica Okopowa": FANDOM_HTML,
    "Zespół przystankowy Cmentarz Żydowski": '<div class="mw-parser-output"><p>Zespół nr 5086 przy Okopowej.</p></div>',
}
WARSZAWA1939_HTML = (
    "<html><head><title>Chłodna 3 | Warszawa 1939</title></head><body><header>Menu</header>"
    "<main><h1>Chłodna 3</h1><p>Budowa: 1730-32.</p><h2>Losy</h2><p>Spłonęła w 1944.</p></main>"
    "<footer>Materiały na licencji CC BY-NC.</footer></body></html>"
)


def warszawikia_answer(params):
    if params.get("meta") == "siteinfo":
        return {"query": {"rightsinfo": {"url": "https://www.fandom.com/pl/licensing-pl", "text": "CC-BY-SA"}}}
    if params.get("list") == "search":
        return {"query": {"search": [{"title": title} for title in WARSZAWIKIA_SEARCH.get(params["srsearch"], [])]}}
    if params.get("prop") == "revisions":
        content = WARSZAWIKIA_WIKITEXT.get(params["titles"], "")
        return {
            "query": {"pages": [{"title": params["titles"], "revisions": [{"slots": {"main": {"content": content}}}]}]}
        }
    if params["page"] in WARSZAWIKIA_HTML:
        return {"parse": {"title": params["page"], "text": WARSZAWIKIA_HTML[params["page"]]}}
    return {"error": {"code": "missingtitle"}}


def answer(method, url, params=None, **kwargs):
    params = params or {}
    if url == warszawikia.API:
        return FakeResponse(200, json.dumps(warszawikia_answer(params)))
    if url.startswith("https://www.warszawa1939.pl/"):
        return FakeResponse(200, WARSZAWA1939_HTML, "text/html; charset=utf-8")
    if url == city.WFS:
        return FakeResponse(200, wfs_answer(params), "text/xml; charset=utf-8")
    if url == f"{city.API}/get_bgk_rcn":
        if kwargs["json"]["dzielnica"] != "Srodmiescie":
            return FakeResponse(500, '{"message":"Service unavailable"}')
        body = {
            "type": "FeatureCollection",
            "features": FLATS if kwargs["json"]["rodzajRynku"] == "rynekWtorny" else [],
        }
    elif url == f"{city.API}/get_cks_budzet_obywatelski":
        body = [PROJECT] if kwargs["json"]["rok"] == 2020 else []
    elif url in osm.OVERPASS_URLS:
        body = OVERPASS
    elif url == wikidata.API:
        found = WIKIDATA.get(REDIRECTED_ITEMS.get(params["ids"], params["ids"]), {"id": params["ids"], "missing": ""})
        if params["props"] == "labels":
            found = {"id": found["id"], "labels": found.get("labels", {})}
        body = {"entities": {params["ids"]: found}}
    elif url == wikipedia.api("pl") and params.get("list") == "geosearch":
        body = {"query": {"geosearch": GEOSEARCH}}
    elif url == wikipedia.api("pl") and params.get("list") == "search":
        body = {"query": {"search": [{"title": title} for title in WIKIPEDIA if params["srsearch"] in title]}}
    elif url == wikipedia.api("pl"):
        title = REDIRECTS.get(params["titles"], params["titles"])
        body = {"query": {"pages": [WIKIPEDIA.get(title, {"ns": 0, "title": title, "missing": True})]}}
    elif url == commons.API and params.get("list") == "geosearch":
        body = {"query": {"geosearch": COMMONS_GEOSEARCH}}
    elif url == commons.API:
        body = {
            "query": {"pages": [COMMONS.get(params["titles"], {"ns": 6, "title": params["titles"], "missing": True})]}
        }
    elif url == images.WMS or url.startswith("https://upload.wikimedia.org/"):
        return FakeResponse(200, f"jpeg {url} {params.get('LAYERS', '')}".encode(), "image/jpeg")
    else:
        pytest.fail(f"unexpected request {method} {url}")
    return FakeResponse(200, json.dumps(body))


@pytest.fixture
def fake_web(cache_dir, monkeypatch):
    monkeypatch.setattr(requests, "request", answer)


def test_wikidata_dates_keep_only_the_known_precision():
    assert wikidata.format_time({"time": "+1850-03-07T00:00:00Z", "precision": 11}) == "7.03.1850"
    assert wikidata.format_time({"time": "+1850-03-00T00:00:00Z", "precision": 10}) == "03.1850"
    assert wikidata.format_time({"time": "+1850-00-00T00:00:00Z", "precision": 9}) == "1850"
    assert wikidata.format_time({"time": "+1800-00-00T00:00:00Z", "precision": 7}) is None
    assert wikidata.format_time({"time": "-0500-00-00T00:00:00Z", "precision": 9}) is None


def test_wikidata_adds_patrons_and_facts_as_template_fragments(fake_web):
    book = Book()
    objects = wikidata.enrich(osm.load_area(LAT, LON).objects, book)

    hala, okopowa = objects[0], objects[1]
    assert (hala.named_after, hala.named_after_label) == ("Q300", "Anna Testowa")
    assert (okopowa.named_after, okopowa.named_after_label) == ("Q1", "Jan Testowy")
    assert [(s.id, s.title, s.url, s.license) for s in book.sources] == [
        ("s1", "Hala Testowa", "https://www.wikidata.org/wiki/Q100", "CC0 1.0"),
        ("s2", "Jan Testowy", "https://www.wikidata.org/wiki/Q1", "CC0 1.0"),
    ]
    assert [(f.id, f.object_id, f.text) for f in book.fragments] == [
        ("s1#1", "o1", "Hala Testowa: hala targowa w Warszawie."),
        ("s1#2", "o1", "Hala Testowa – pochodzenie nazwy: Anna Testowa."),
        ("s1#3", "o1", "Hala Testowa – status ochrony: zabytek rejestrowy."),
        ("s1#4", "o1", "Hala Testowa – data powstania: 1902."),
        ("s1#5", "o1", "Hala Testowa – liczba artykułów w Wikipedii w różnych językach: 3."),
        ("s2#1", "o2", "Jan Testowy: architekt."),
        ("s2#2", "o2", "Jan Testowy – data urodzenia: 7.03.1850."),
        ("s2#3", "o2", "Jan Testowy – data śmierci: 1910."),
        ("s2#4", "o2", "Jan Testowy – liczba artykułów w Wikipedii w różnych językach: 1."),
    ]
    assert book.fragments[3].derived
    assert book.fragments[3].template == "wikidata.inception"
    assert book.fragments[3].values == {"label": "Hala Testowa", "inception": "1902"}


def test_wikipedia_sections_skip_reference_sections_and_long_ones_split_at_paragraphs(monkeypatch):
    assert wikipedia.sections(HALA_TEXT) == [
        (None, "Hala Testowa – hala targowa.\n\n\n"),
        ("Historia", "\nZbudowana w 1902.\nDruga  linia.\n\n\n"),
        ("Architektura", "\nCegła."),
    ]
    monkeypatch.setattr(wikipedia, "MAX_FRAGMENT_CHARS", 20)
    assert wikipedia.chunks("\nAla ma kota.\nKot ma  Alę.\nKoniec.") == ["Ala ma kota.", "Kot ma Alę. Koniec."]


def test_wikipedia_article_follows_redirects(fake_web):
    found = wikipedia.article("Ulica Młynarska w Warszawie")

    assert found.title == "Młynarska (Warszawa)"
    assert found.url == "https://pl.wikipedia.org/wiki/M%C5%82ynarska_%28Warszawa%29"
    assert wikipedia.cached_text(found.url) == "Młynarska – ulica na Woli."


def test_agent_functions_return_sources_and_fragments(fake_web):
    sources, fragments = wikipedia.wikipedia_article("Jan Testowy")
    assert [s.id for s in sources] == ["s1"]
    assert [(f.id, f.section, f.text) for f in fragments] == [
        ("s1#1", None, "Jan Testowy – architekt."),
        ("s1#2", "Życiorys", "Urodził się w Warszawie."),
    ]
    assert wikipedia.wikipedia_search("Testow") == ["Hala Testowa", "Jan Testowy"]
    sources, fragments = wikidata.wikidata_entity("Q1")
    assert [(s.id, s.publisher) for s in sources] == [("s1", "Wikidata")]
    assert len(fragments) == 4


def test_collect_writes_a_checked_file_that_a_rerun_without_network_repeats(stop_rows, fake_web, tmp_path):
    path = collect("5086", root=tmp_path, images_root=tmp_path / "images")

    assert path == tmp_path / "5086.json"
    collected = load(path)
    assert collected.stop.group_id == "5086"
    assert collected.area.district == "Wola"
    assert [o.name for o in collected.objects] == ["Hala Testowa", "Okopowa", "Tablica", "Młynarska", "Park Testowy"]
    assert [(s.name, s.object_id, s.named_after) for s in collected.area.street_names] == [
        ("Okopowa", "o2", "Q1"),
        ("Młynarska", "o4", None),
    ]
    assert [(s.id, s.publisher, s.title) for s in collected.sources[2:6]] == [
        ("s3", "Wikipedia", "Wola (Warszawa)"),
        ("s4", "Wikipedia", "Hala Testowa"),
        ("s5", "Wikipedia", "Jan Testowy"),
        ("s6", "Wikipedia", "Młynarska (Warszawa)"),
    ]
    assert [(f.id, f.object_id, f.section, f.text) for f in collected.fragments if f.source_id != "s1"][4:11] == [
        ("s3#1", None, None, "Wola – dzielnica Warszawy."),
        ("s4#1", "o1", None, "Hala Testowa – hala targowa."),
        ("s4#2", "o1", "Historia", "Zbudowana w 1902. Druga linia."),
        ("s4#3", "o1", "Architektura", "Cegła."),
        ("s5#1", "o2", None, "Jan Testowy – architekt."),
        ("s5#2", "o2", "Życiorys", "Urodził się w Warszawie."),
        ("s6#1", "o4", None, "Młynarska – ulica na Woli."),
    ]
    assert collected.area.fragment_ids == ["s3#1"]
    assert [(a.title, a.distance_m, a.fetched) for a in collected.area.nearby_articles] == [
        ("Hala Testowa", 10, True),
        ("Pomnik Daleki", 390, False),
    ]
    assert check(collected) == []

    first = path.read_text(encoding="utf-8")
    with cache.offline():
        assert collect("5086", root=tmp_path, images_root=tmp_path / "images").read_text(encoding="utf-8") == first


def test_images_are_four_city_maps_and_licensed_photos_with_captions_from_the_source(stop_rows, fake_web, tmp_path):
    collected = load(collect("5086", root=tmp_path, images_root=tmp_path / "images"))

    assert [(i.id, i.kind, i.year, i.caption) for i in collected.images[:4]] == [
        ("i1", "photo_map_1935", "1935", "Fotoplan Warszawy 1935, okolice przystanku Cm. Żydowski"),
        ("i2", "plan_1939", "1939", "Plan Warszawy 1939, okolice przystanku Cm. Żydowski"),
        ("i3", "photo_map_1945", "1945", "Fotoplan Warszawy 1945, okolice przystanku Cm. Żydowski"),
        ("i4", "orthophoto", "2021", "Fotoplan Warszawy 2021, okolice przystanku Cm. Żydowski"),
    ]
    assert "LAYERS=RASTER_FOTOPLAN_1935" in collected.images[0].url
    assert "BBOX=20.971331%2C52.241107%2C20.983069%2C52.248293" in collected.images[0].url
    hala, night = collected.images[4:]
    assert (hala.id, hala.caption, hala.author, hala.year, hala.license, hala.non_commercial) == (
        "i5",
        "Hala w 1910 r.",
        "Jan Fotograf",
        "1910",
        "public domain",
        False,
    )
    assert (hala.url, hala.source_id, hala.object_id) == (
        "https://commons.wikimedia.org/wiki/File:Hala_Testowa.jpg",
        "s4",
        "o1",
    )
    assert (night.id, night.caption, night.license, night.non_commercial, night.source_id) == (
        "i6",
        "Źródło: Wikimedia Commons",
        "CC BY-NC-SA 4.0",
        True,
        None,
    )
    files = sorted(path.name for path in (tmp_path / "images" / "5086").iterdir())
    assert files == ["i1.jpg", "i2.jpg", "i3.jpg", "i4.jpg", "i5.jpg", "i6.jpg"]
    assert (
        tmp_path / "images" / "5086" / "i5.jpg"
    ).read_bytes() == b"jpeg https://upload.wikimedia.org/thumb/File:Hala_Testowa.jpg "


def test_check_finds_a_changed_quote_value_and_caption(stop_rows, fake_web, tmp_path):
    collected = load(collect("5086", root=tmp_path, images_root=tmp_path / "images"))
    changed = []
    for fragment in collected.fragments:
        if fragment.id == "s4#2":
            fragment = fragment.model_copy(update={"text": "Zbudowana w 1903."})
        if fragment.id == "s1#4":
            fragment = fragment.model_copy(
                update={
                    "text": "Hala Testowa – data powstania: 1903.",
                    "values": {"label": "Hala Testowa", "inception": "1903"},
                }
            )
        changed.append(fragment)

    captions = [i.model_copy(update={"caption": "Piękna hala"}) if i.id == "i5" else i for i in collected.images]

    problems = check(collected.model_copy(update={"fragments": changed, "images": captions}))

    assert [problem.split(":")[0] for problem in problems] == ["s1#4", "s4#2", "i5"]


def test_pl2000_gives_the_same_point_as_the_city_wgs84_layer():
    lat, lon = from_pl2000(5790772.7476, 7501699.1632)

    assert distance_m(lat, lon, 52.250516, 21.024882) == 0
    assert [round(value, 7) for value in from_pl2000(*to_pl2000(52.2447, 20.9772))] == [52.2447, 20.9772]


def test_city_api_district_names_have_no_polish_letters_hyphens_or_spaces():
    assert city.api_district("Śródmieście") == "Srodmiescie"
    assert city.api_district("Białołęka") == "Bialoleka"
    assert city.api_district("Praga-Północ") == "PragaPolnoc"


def test_city_data_becomes_template_facts(stop_rows, fake_web, monkeypatch):
    monkeypatch.setattr(city, "WFS_MAX_FEATURES", 2)
    stop = load_stop("5086")
    found = city.facts(stop)

    assert [(fact.template, fact.values) for fact in found] == [
        ("city.flat_prices", {"year": "2025", "name": "Cm. Żydowski", "price": "15 000", "count": "5"}),
        (
            "city.budget",
            {"year": "2020", "title": "Nowy plac zabaw", "distance": "100", "name": "Cm. Żydowski", "cost": "930 000"},
        ),
        (
            "city.tree",
            {
                "distance": "120",
                "name": "Cm. Żydowski",
                "species": "robinia biała",
                "latin": "Robinia pseudoacacia L.",
                "girth": "55, 300",
                "height": "18",
                "year": "2023",
            },
        ),
        (
            "city.tree",
            {
                "distance": "50",
                "name": "Cm. Żydowski",
                "species": "lipa drobnolistna",
                "latin": "Tilia cordata Mill.",
                "girth": "289",
                "height": "17",
                "year": "2026",
            },
        ),
        (
            "city.tree",
            {
                "distance": "150",
                "name": "Cm. Żydowski",
                "species": "topola czarna",
                "latin": "Populus nigra L.",
                "girth": "241",
                "height": "34",
                "year": "2012",
            },
        ),
    ]
    assert found[1].url == PROJECT["url"]
    assert "Kowalska" not in json.dumps([fact.values for fact in found], ensure_ascii=False)


def test_collected_city_facts_pass_the_check_and_a_changed_price_does_not(stop_rows, fake_web, tmp_path):
    collected = load(collect("5086", root=tmp_path, images_root=tmp_path / "images"))
    city_fragments = [f for f in collected.fragments if f.template and f.template.startswith("city.")]

    assert [f.text for f in city_fragments][:1] == [
        "Mediana ceny 1 m² lokalu mieszkalnego w transakcjach rynkowych z 2025 r. w promieniu 400 m od przystanku "
        "Cm. Żydowski wyniosła 15 000 zł (liczba lokali: 5)."
    ]
    changed = city_fragments[0].model_copy(
        update={
            "text": city_fragments[0].text.replace("15 000", "9 000"),
            "values": {**city_fragments[0].values, "price": "9 000"},
        }
    )
    fragments = [changed if f.id == changed.id else f for f in collected.fragments]

    assert [p.split(":")[0] for p in check(collected.model_copy(update={"fragments": fragments}))] == [changed.id]


def test_html_text_keeps_the_article_and_its_headings_and_drops_the_rest():
    def readable(html):
        title, text = to_text(html)
        return title, [(heading, wikipedia.chunks(body)) for heading, body in wikipedia.sections(text)]

    assert readable(FANDOM_HTML) == (
        "",
        [(None, ["Ulica Okopowa – ulica na Woli."]), ("Historia", ["Podczas okupacji: Dammstrasse."])],
    )
    assert readable(WARSZAWA1939_HTML) == (
        "Chłodna 3 | Warszawa 1939",
        [(None, ["Chłodna 3 Budowa: 1730-32."]), ("Losy", ["Spłonęła w 1944."])],
    )


def test_warszawikia_takes_the_stop_article_with_the_group_id_and_streets_with_the_same_name(stop_rows, fake_web):
    stop = load_stop("5086")
    streets = [o for o in osm.load_area(LAT, LON).objects if o.kind == "street"]
    book = Book()
    warszawikia.collect_articles(stop, streets, book)

    assert [(s.title, s.publisher, s.type, s.license) for s in book.sources] == [
        ("Zespół przystankowy Cmentarz Żydowski", "Warszawikia", "varsaviana", "CC-BY-SA"),
        ("Ulica Okopowa", "Warszawikia", "varsaviana", "CC-BY-SA"),
    ]
    assert [(f.id, f.object_id, f.section, f.text) for f in book.fragments] == [
        ("s1#1", None, None, "Zespół nr 5086 przy Okopowej."),
        ("s2#1", "o2", None, "Ulica Okopowa – ulica na Woli."),
        ("s2#2", "o2", "Historia", "Podczas okupacji: Dammstrasse."),
    ]
    assert warszawikia.cached_text(book.sources[1].url).count("Dammstrasse") == 1


def test_allowed_urls_give_sources_with_the_site_licence_and_other_urls_are_refused(fake_web):
    sources, fragments = web.fetch_allowed_url("https://www.warszawa1939.pl/obiekt/chlodna-3")

    assert [(s.title, s.publisher, s.type, s.license) for s in sources] == [
        ("Chłodna 3 | Warszawa 1939", "warszawa1939.pl", "varsaviana", "CC BY-NC")
    ]
    assert [(f.section, f.text) for f in fragments] == [
        (None, "Chłodna 3 Budowa: 1730-32."),
        ("Losy", "Spłonęła w 1944."),
    ]
    assert web.fetch_allowed_url("https://pl.wikipedia.org/wiki/Jan_Testowy")[0][0].publisher == "Wikipedia"
    with pytest.raises(web.NotAllowed):
        web.fetch_allowed_url("https://example.com/historia")


def test_a_redirected_wikidata_item_is_cached_under_its_final_id(fake_web):
    found = wikidata.entity("Q101")
    sources, fragments = wikidata.wikidata_entity("Q101")

    assert found.qid == "Q100"
    assert sources[0].url == "https://www.wikidata.org/wiki/Q100"
    with cache.offline():
        assert wikidata.check_values(sources[0].url, fragments[0].template, fragments[0].values) is None


def test_requests_wait_between_calls_to_the_same_server_only_where_it_asks_for_it(monkeypatch):
    clock = [100.0]
    waits = []
    monkeypatch.setattr(cache.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(cache.time, "sleep", waits.append)
    monkeypatch.setattr(cache, "_last_request_at", {})

    for host in ("pl.wikipedia.org", "pl.wikipedia.org", "overpass-api.de", "overpass-api.de", "www.warszawa1939.pl"):
        cache._respect_interval(host)
    cache._respect_interval("www.warszawa1939.pl")

    assert waits == [1.0, 10.0]


def test_each_server_gets_one_request_at_a_time_while_different_servers_work_together(cache_dir, monkeypatch):
    active: dict[str, int] = {}
    most: dict[str, int] = {}
    overlapping = []
    guard = threading.Lock()

    def request(method, url, **kwargs):
        host = url.split("/")[2]
        with guard:
            active[host] = active.get(host, 0) + 1
            most[host] = max(most.get(host, 0), active[host])
            overlapping.append(sum(active.values()))
        clock.sleep(0.05)
        with guard:
            active[host] -= 1
        return FakeResponse(200, "{}")

    monkeypatch.setattr(requests, "request", request)
    urls = [f"https://{host}/api/{n}" for n in range(4) for host in ("a.example", "b.example")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda url: cache.fetch("GET", url), urls))

    assert most == {"a.example": 1, "b.example": 1}
    assert max(overlapping) == 2


def test_the_same_request_from_two_stops_is_downloaded_once(cache_dir, monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        calls.append(url)
        clock.sleep(0.05)
        return FakeResponse(200, '{"rok": 2025}')

    monkeypatch.setattr(requests, "request", request)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: cache.fetch("POST", "https://example.org/rcn", json_body={"rok": 2025}), range(4))
        )

    assert len(calls) == 1
    assert {result.body for result in results} == {'{"rok": 2025}'}


def test_one_stop_checking_offline_does_not_stop_another_from_downloading(cache_dir, monkeypatch):
    monkeypatch.setattr(requests, "request", lambda method, url, **kwargs: FakeResponse(200, "{}"))
    checking = threading.Event()
    downloaded = threading.Event()

    def check_offline():
        with cache.offline():
            checking.set()
            downloaded.wait(timeout=5)
            with pytest.raises(cache.FetchError, match="not in the cache"):
                cache.fetch("GET", "https://example.org/never-downloaded")

    def download():
        checking.wait(timeout=5)
        cache.fetch("GET", "https://example.org/new")
        downloaded.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in [pool.submit(check_offline), pool.submit(download)]:
            future.result()


def test_several_stops_at_once_give_the_same_files_as_one_by_one(stop_rows, fake_web, tmp_path):
    together = dict(collect_many(["5086", "5087"], jobs=2, root=tmp_path / "together", images_root=tmp_path / "i1"))
    alone = {group_id: collect(group_id, root=tmp_path / "alone", images_root=tmp_path / "i2") for group_id in together}

    assert sorted(together) == ["5086", "5087"]
    for group_id, path in together.items():
        assert path.read_text(encoding="utf-8") == alone[group_id].read_text(encoding="utf-8")


def test_a_failed_stop_does_not_stop_the_others(stop_rows, fake_web, tmp_path):
    results = dict(collect_many(["9999", "5086"], jobs=2, root=tmp_path, images_root=tmp_path / "images"))

    assert isinstance(results["9999"], UnknownStopGroup)
    assert results["5086"] == tmp_path / "5086.json"


def test_demo_groups_are_the_fifty_stop_groups_of_the_demo_lines():
    groups = demo_groups()

    assert len(groups) == len(set(groups)) == 50
    assert groups[:3] == ["5159", "5087", "5086"]
