import json
from datetime import date

import pytest
import requests

from collector import cache, osm, wikidata
from collector.collect import collect
from collector.geo import distance_m, distance_to_line_m
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


def boundary(area_id, level, name):
    return {"type": "area", "id": area_id, "tags": {"boundary": "administrative", "admin_level": level, "name": name}}


OVERPASS = {
    "elements": [
        boundary(3600000001, "8", "Warszawa"),
        boundary(3600000002, "9", "Wola"),
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
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.ok = status_code < 400
        self.content = body.encode()
        self.text = body
        self.headers = {"Content-Type": "application/json"}
        self.encoding = None


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


def entity(qid, label, description=None, wikipedias=0, **claims):
    return wikidata.Entity(qid, label, description, claims, wikipedias, date(2026, 10, 17))


ENTITIES = {
    "Q100": entity(
        "Q100",
        "Hala Testowa",
        "hala targowa w Warszawie",
        3,
        P138=[item("Q300")],
        P1435=[item("Q400")],
        P571=[time("+1902-00-00T00:00:00Z", 9)],
    ),
    "Q1": entity(
        "Q1",
        "Jan Testowy",
        "architekt",
        1,
        P569=[time("+1850-03-07T00:00:00Z", 11)],
        P570=[time("+1910-00-00T00:00:00Z", 9)],
    ),
    "Q300": entity("Q300", "Anna Testowa"),
    "Q200": entity("Q200", None, "park w Warszawie"),
}


@pytest.fixture
def fake_wikidata(monkeypatch):
    monkeypatch.setattr(wikidata, "entity", ENTITIES.get)
    monkeypatch.setattr(wikidata, "labels", lambda qids: {"Q400": "zabytek rejestrowy"} if "Q400" in qids else {})


def test_wikidata_dates_keep_only_the_known_precision():
    assert wikidata.format_time({"time": "+1850-03-07T00:00:00Z", "precision": 11}) == "7.03.1850"
    assert wikidata.format_time({"time": "+1850-03-00T00:00:00Z", "precision": 10}) == "03.1850"
    assert wikidata.format_time({"time": "+1850-00-00T00:00:00Z", "precision": 9}) == "1850"
    assert wikidata.format_time({"time": "+1800-00-00T00:00:00Z", "precision": 7}) is None
    assert wikidata.format_time({"time": "-0500-00-00T00:00:00Z", "precision": 9}) is None


def test_wikidata_adds_patrons_and_facts_as_template_fragments(monkeypatch, fake_wikidata):
    monkeypatch.setattr(osm, "overpass", lambda query: OVERPASS)
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


def test_collect_writes_a_file_that_loads_back(stop_rows, monkeypatch, fake_wikidata, tmp_path):
    monkeypatch.setattr(osm, "overpass", lambda query: OVERPASS)
    path = collect("5086", root=tmp_path)

    assert path == tmp_path / "5086.json"
    collected = load(path)
    assert collected.stop.group_id == "5086"
    assert collected.area.district == "Wola"
    assert [o.name for o in collected.objects] == ["Hala Testowa", "Okopowa", "Tablica", "Młynarska", "Park Testowy"]
    assert [(s.name, s.object_id, s.named_after) for s in collected.area.street_names] == [
        ("Okopowa", "o2", "Q1"),
        ("Młynarska", "o4", None),
    ]
    assert len(collected.fragments) == 9
    assert collect("5086", root=tmp_path).read_text(encoding="utf-8") == path.read_text(encoding="utf-8")
