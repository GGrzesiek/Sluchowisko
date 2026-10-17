import pytest

from pipeline.ztm import (
    ZtmError,
    build_stop_index,
    cut_segment,
    flatten_values,
    match_score,
    pick_variant,
    variant_stops,
)


def _stop(zespol, slupek, name, lat=52.0, lon=21.0, since="2024-01-01 00:00:00.0"):
    return {
        "zespol": zespol,
        "slupek": slupek,
        "nazwa_zespolu": name,
        "szer_geo": str(lat),
        "dlug_geo": str(lon),
        "obowiazuje_od": since,
    }


def test_flatten_values():
    rows = [{"values": [{"key": "zespol", "value": "1001"}, {"key": "slupek", "value": "01"}]}]
    assert flatten_values(rows) == [{"zespol": "1001", "slupek": "01"}]


def test_stop_index_prefers_newest_version():
    stops = [
        _stop("1", "01", "Stara", since="2020-01-01 00:00:00.0"),
        _stop("1", "01", "Nowa", since="2025-01-01 00:00:00.0"),
    ]
    assert build_stop_index(stops)[("1", "01")]["name"] == "Nowa"


INDEX = build_stop_index(
    [
        _stop("1", "01", "Rondo Żaba"),
        _stop("2", "01", "Julianowska"),
        _stop("3", "01", "Metro Bródno"),
        _stop("4", "01", "Żerań Wschodni"),
        _stop("4", "02", "Żerań Wschodni"),
        _stop("3", "02", "Metro Bródno"),
        _stop("2", "02", "Julianowska"),
        _stop("1", "02", "Rondo Żaba"),
    ]
)


def _variant(*pairs):
    return {str(i): {"nr_zespolu": z, "nr_przystanku": s} for i, (z, s) in enumerate(pairs, start=1)}


ROUTES = {
    "TP-ZER": _variant(("1", "01"), ("2", "01"), ("3", "01"), ("4", "01")),
    "TP-ZAB": _variant(("4", "02"), ("3", "02"), ("2", "02"), ("1", "02")),
}


def test_variant_stops_keeps_order():
    names = [s["name"] for s in variant_stops(ROUTES["TP-ZER"], INDEX)]
    assert names == ["Rondo Żaba", "Julianowska", "Metro Bródno", "Żerań Wschodni"]


def test_match_score_counts_in_order_only():
    assert match_score(["A", "B", "C"], ["A", "C"]) == 2
    assert match_score(["C", "B", "A"], ["A", "C"]) == 1


def test_pick_variant_chooses_direction():
    code, _ = pick_variant(ROUTES, INDEX, ["Rondo Żaba", "Metro Bródno", "Żerań Wschodni"])
    assert code == "TP-ZER"
    code, _ = pick_variant(ROUTES, INDEX, ["Żerań Wschodni", "Rondo Żaba"])
    assert code == "TP-ZAB"


def test_cut_segment():
    stops = variant_stops(ROUTES["TP-ZER"], INDEX)
    seg = cut_segment(stops, "Julianowska", "Żerań Wschodni")
    assert [s["name"] for s in seg] == ["Julianowska", "Metro Bródno", "Żerań Wschodni"]


def test_cut_segment_wrong_direction_raises():
    stops = variant_stops(ROUTES["TP-ZER"], INDEX)
    with pytest.raises(ZtmError):
        cut_segment(stops, "Żerań Wschodni", "Rondo Żaba")
