import copy

import pytest
from pydantic import ValidationError

from collector.schema import CollectedStop, dumps, load, normalize_text, save

VALID = {
    "stop": {
        "group_id": "9001",
        "name": "Przystanek Testowy",
        "lat": 52.23,
        "lon": 21.01,
        "poles": [{"pole": "01", "lat": 52.2301, "lon": 21.0101}, {"pole": "02", "lat": 52.2299, "lon": 21.0099}],
    },
    "area": {
        "district": "Dzielnica Testowa",
        "neighbourhood": None,
        "fragment_ids": ["s1#1"],
        "street_names": [{"name": "Testowa", "object_id": "o1", "named_after": None, "distance_m": 0}],
        "nearby_articles": [
            {"title": "Artykuł A", "distance_m": 10, "fetched": True},
            {"title": "Artykuł B", "distance_m": 350, "fetched": False},
        ],
    },
    "objects": [
        {
            "id": "o1",
            "name": "ulica Testowa",
            "kind": "street",
            "distance_m": 0,
            "osm_id": "way/1",
            "wikidata": None,
            "wikipedia": None,
            "named_after": None,
            "named_after_label": None,
            "old_names": [],
            "heritage_ref": None,
            "tags": {"highway": "residential"},
        },
        {
            "id": "o2",
            "name": "Pomnik Testowy",
            "kind": "monument",
            "distance_m": 120,
            "osm_id": "node/2",
            "wikidata": "Q1",
            "wikipedia": "pl:Pomnik Testowy",
            "named_after": None,
            "named_after_label": None,
            "old_names": ["Pomnik Stary"],
            "heritage_ref": None,
            "tags": {},
        },
    ],
    "sources": [
        {
            "id": "s1",
            "type": "encyclopedia",
            "title": "Artykuł A",
            "publisher": "Wikipedia",
            "url": "https://pl.wikipedia.org/wiki/Artyku%C5%82_A",
            "license": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "author": None,
            "author_death_year": None,
            "retrieved_at": "2026-10-17",
        },
        {
            "id": "s2",
            "type": "city_data",
            "title": "Rejestr Cen Nieruchomości",
            "publisher": "m.st. Warszawa",
            "url": "https://dane.um.warszawa.pl/",
            "license": "CC0",
            "license_url": None,
            "author": None,
            "author_death_year": None,
            "retrieved_at": "2026-10-14",
        },
    ],
    "fragments": [
        {
            "id": "s1#1",
            "source_id": "s1",
            "section": "Historia",
            "text": "Tekst sekcji w jednej linii.",
            "object_id": "o1",
            "derived": False,
        },
        {
            "id": "s2#1",
            "source_id": "s2",
            "section": None,
            "text": "Mediana wyniosła 10 000 zł (3 transakcji).",
            "object_id": None,
            "derived": True,
            "template": "rcn_median_price",
            "values": {"price": "10 000", "n": 3, "year": 2022},
        },
    ],
    "images": [
        {
            "id": "i1",
            "kind": "photo_map_1935",
            "file": "out/images/9001/i1.jpg",
            "url": "https://wms.um.warszawa.pl/serwis",
            "caption": "Fotoplan Warszawy 1935, okolice przystanku Przystanek Testowy",
            "author": None,
            "year": "1935",
            "license": "public domain",
            "license_url": None,
            "non_commercial": False,
            "source_id": None,
            "object_id": None,
        },
        {
            "id": "i2",
            "kind": "photo",
            "file": "out/images/9001/i2.jpg",
            "url": "https://commons.wikimedia.org/wiki/File:Test.jpg",
            "caption": "Podpis ze źródła",
            "author": "Autor",
            "year": None,
            "license": "CC BY-NC 4.0",
            "license_url": "https://creativecommons.org/licenses/by-nc/4.0/",
            "non_commercial": True,
            "source_id": "s1",
            "object_id": "o2",
        },
    ],
}


def changed(**edits):
    data = copy.deepcopy(VALID)
    for path, value in edits.items():
        *keys, last = path.split("__")
        target = data
        for key in keys:
            target = target[int(key)] if key.isdigit() else target[key]
        target[int(last) if last.isdigit() else last] = value
    return data


def test_valid_file():
    collected = CollectedStop.model_validate(VALID)
    assert collected.stop.group_id == "9001"


def test_round_trip_is_identical(tmp_path):
    collected = CollectedStop.model_validate(VALID)
    path = save(collected, tmp_path)
    assert path == tmp_path / "9001.json"
    assert load(path) == collected
    assert dumps(load(path)) == path.read_text(encoding="utf-8")


def test_plain_fragment_has_no_template_in_output():
    text = dumps(CollectedStop.model_validate(VALID))
    assert text.count('"template"') == 1
    assert '"author": null' in text


def test_normalize_text():
    assert normalize_text("  Ul. Książęca\n\n w  Warszawie ") == "Ul. Książęca w Warszawie"


@pytest.mark.parametrize(
    "edits",
    [
        {"stop__poles": []},
        {"objects__1__distance_m": 0, "objects__0__distance_m": 5},
        {"objects__1__id": "o1"},
        {"fragments__0__object_id": "o9"},
        {"fragments__0__source_id": "s2"},
        {"fragments__0__text": "Dwie  spacje"},
        {"fragments__0__template": "x"},
        {"fragments__1__values": None},
        {"area__fragment_ids": ["s3#1"]},
        {"area__nearby_articles__0__distance_m": 500},
        {"images__1__license": "CC BY-NC-ND 4.0"},
        {"images__1__non_commercial": False},
        {"images__0__file": "out/images/1/i1.jpg"},
        {"sources__0__type": "wiki"},
        {"sources__0__url": "pl.wikipedia.org"},
        {"objects__0__wikidata": "123"},
        {"stop__extra": 1},
    ],
)
def test_invalid_file(edits):
    with pytest.raises(ValidationError):
        CollectedStop.model_validate(changed(**edits))


def test_fragments_must_be_sorted_by_number():
    data = copy.deepcopy(VALID)
    data["sources"].append({**data["sources"][0], "id": "s10"})
    data["fragments"] = [
        data["fragments"][0],
        {**data["fragments"][0], "id": "s10#1", "source_id": "s10"},
        data["fragments"][1],
    ]
    with pytest.raises(ValidationError):
        CollectedStop.model_validate(data)
    data["fragments"] = [data["fragments"][0], data["fragments"][2], data["fragments"][1]]
    CollectedStop.model_validate(data)
