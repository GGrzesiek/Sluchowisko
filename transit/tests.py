from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from transit import warsaw_api
from transit.models import Line, Route
from transit.sync import classify_line, sync_routes, sync_stops


def stop_row(zespol, slupek, name, lat, lon):
    return {"values": [
        {"key": "zespol", "value": zespol}, {"key": "slupek", "value": slupek},
        {"key": "nazwa_zespolu", "value": name}, {"key": "id_ulicy", "value": "1"},
        {"key": "szer_geo", "value": str(lat)}, {"key": "dlug_geo", "value": str(lon)},
        {"key": "kierunek", "value": "x"},
    ]}


def fake_response(result):
    return MagicMock(json=lambda: {"result": result}, raise_for_status=lambda: None)


ROUTES = {
    "17": {
        "TP-TAR": {"1": {"nr_zespolu": "7001", "nr_przystanku": "01", "typ": "1", "odleglosc": 0},
                   "2": {"nr_zespolu": "7002", "nr_przystanku": "01", "typ": "1", "odleglosc": 500},
                   "3": {"nr_zespolu": "7003", "nr_przystanku": "01", "typ": "1", "odleglosc": 900}},
        "TP-WOR": {"1": {"nr_zespolu": "7003", "nr_przystanku": "02", "typ": "1", "odleglosc": 0},
                   "2": {"nr_zespolu": "7001", "nr_przystanku": "02", "typ": "1", "odleglosc": 1400}},
        "TX-ZJ": {"1": {"nr_zespolu": "7002", "nr_przystanku": "01", "typ": "1", "odleglosc": 0}},
    },
    "180": {"TP-A": {"1": {"nr_zespolu": "7001", "nr_przystanku": "01", "typ": "1", "odleglosc": 0}}},
    "N37": {"TP-B": {"1": {"nr_zespolu": "9999", "nr_przystanku": "01", "typ": "1", "odleglosc": 0}}},
}

STOPS = [
    {"zespol": "7001", "slupek": "01", "nazwa_zespolu": "Woronicza", "szer_geo": "52.19", "dlug_geo": "21.01"},
    {"zespol": "7001", "slupek": "02", "nazwa_zespolu": "Woronicza", "szer_geo": "52.19", "dlug_geo": "21.01"},
    {"zespol": "7002", "slupek": "01", "nazwa_zespolu": "Centrum", "szer_geo": "52.23", "dlug_geo": "21.01"},
    {"zespol": "7003", "slupek": "01", "nazwa_zespolu": "Tarchomin", "szer_geo": "52.32", "dlug_geo": "20.95"},
    {"zespol": "7003", "slupek": "02", "nazwa_zespolu": "Tarchomin", "szer_geo": "52.32", "dlug_geo": "20.95"},
]


@override_settings(WARSAW_API_KEY="x")
class PaginationTest(TestCase):
    @patch("transit.warsaw_api.time.sleep")
    @patch("transit.warsaw_api.requests.get")
    def test_follows_pages_until_short_page(self, get, _sleep):
        pages = {1: [stop_row(str(i), "01", "s", 52, 21) for i in range(3)],
                 2: [stop_row(str(i), "01", "s", 52, 21) for i in range(3, 6)],
                 3: [stop_row("6", "01", "s", 52, 21)]}
        get.side_effect = lambda url, params, timeout: fake_response(pages[params["page"]])
        rows = list(warsaw_api.iter_dbstore("res", page_size=3))
        self.assertEqual([r["zespol"] for r in rows], [str(i) for i in range(7)])
        self.assertEqual(get.call_count, 3)

    @patch("transit.warsaw_api.requests.get")
    def test_stops_if_api_ignores_page(self, get):
        same = [stop_row("1", "01", "s", 52, 21), stop_row("2", "01", "s", 52, 21)]
        get.return_value = fake_response(same)
        self.assertEqual(len(list(warsaw_api.iter_dbstore("res", page_size=2))), 2)
        self.assertEqual(get.call_count, 2)

    @patch("transit.warsaw_api.requests.get")
    def test_wrong_key_raises_without_retry(self, get):
        get.return_value = MagicMock(json=lambda: {"result": "false", "error": "Błędny apikey lub jego brak"},
                                     raise_for_status=lambda: None)
        with self.assertRaises(warsaw_api.WarsawApiError):
            warsaw_api.fetch_stops()
        self.assertEqual(get.call_count, 1)


class ClassifyTest(TestCase):
    def test_kinds(self):
        cases = {"17": "tram", "4": "tram", "180": "bus", "N37": "night", "L-1": "suburban",
                 "E-2": "express", "Z-9": "replacement", "T1": "replacement"}
        for number, kind in cases.items():
            self.assertEqual(classify_line(number), kind, number)


@override_settings(WARSAW_API_KEY="x")
class LinesApiTest(TestCase):
    def setUp(self):
        cache.clear()
        sync_stops(STOPS)
        self.stats = sync_routes(ROUTES)
        self.client = APIClient()

    def test_sync_stats_and_directions(self):
        self.assertEqual(self.stats["lines"], 3)
        self.assertEqual(self.stats["routes"], 5)
        self.assertEqual(self.stats["unmatched_stops"], 1)  # 9999 doesn't exist
        r = Route.objects.get(line_id="17", code="TP-TAR")
        self.assertEqual((r.first_stop_name, r.last_stop_name), ("Woronicza", "Tarchomin"))

    def test_resync_is_idempotent_and_removes_old_lines(self):
        sync_routes({"17": ROUTES["17"]})
        self.assertEqual(list(Line.objects.values_list("number", flat=True)), ["17"])
        self.assertEqual(Route.objects.filter(line_id="17").count(), 3)

    def test_list_filter_and_paginate(self):
        r = self.client.get("/api/lines/?kind=tram").json()
        self.assertEqual(r["count"], 1)
        line = r["results"][0]
        self.assertEqual(line["number"], "17")
        self.assertEqual(line["directions"], ["Tarchomin", "Woronicza"])  # TX-ZJ (depot run) ignored
        self.assertEqual(self.client.get("/api/lines/?page_size=2").json()["count"], 3)

    def test_route_stops_and_geojson(self):
        r = self.client.get("/api/lines/17/routes/TP-TAR/").json()
        self.assertEqual([s["name"] for s in r["stops"]], ["Woronicza", "Centrum", "Tarchomin"])
        g = self.client.get("/api/lines/17/routes/TP-TAR/geojson/").json()
        self.assertEqual(g["features"][0]["geometry"]["type"], "LineString")
        self.assertEqual(len(g["features"]), 4)
        self.assertEqual(self.client.get("/api/lines/N37/").status_code, 200)
        self.assertEqual(self.client.get("/api/lines/17/routes/NOPE/").status_code, 404)

    @patch("transit.warsaw_api.requests.get")
    def test_live_vehicles_cached(self, get):
        get.return_value = fake_response([{"Lines": "17", "Lon": 21.0, "Lat": 52.2, "VehicleNumber": "3201",
                                           "Time": "2026-10-17 12:00:00", "Brigade": "5"}])
        for _ in range(3):
            r = self.client.get("/api/lines/17/vehicles/").json()
        self.assertEqual(r["count"], 1)
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["params"]["type"], 2)  # tram


class LlmContextTest(TestCase):
    def setUp(self):
        sync_stops(STOPS)
        sync_routes(ROUTES)
        self.client = APIClient()

    def test_context_is_compact_and_ordered(self):
        ctx = self.client.get("/api/lines/17/llm-context/").json()
        self.assertEqual(ctx["route"]["code"], "TP-TAR")  # longest main route
        self.assertEqual([s["name"] for s in ctx["stops"]], ["Woronicza", "Centrum", "Tarchomin"])
        self.assertNotIn("zespol", ctx["stops"][0])  # no internal ids for the model
        self.assertEqual(len(ctx["segments"]), 2)
        self.assertGreater(ctx["route"]["length_km"], 10)
        self.assertIn("output_format", ctx)
        self.assertNotIn("rules", self.client.get("/api/lines/17/llm-context/?bare=1").json())

    def test_validate_places_against_route(self):
        llm_output = [
            {"name": "Near Centrum", "lat": 52.2305, "lon": 21.0105,
             "facts": [{"title": "Ok", "text": "Real fact.", "source_url": "https://pl.wikipedia.org/wiki/X"}]},
            {"name": "Far away", "lat": 52.10, "lon": 21.25,
             "facts": [{"title": "Ok", "text": "Fact.", "source_url": "https://pl.wikipedia.org/wiki/Y"}]},
            {"name": "Swapped", "lat": 21.01, "lon": 52.23,
             "facts": [{"title": "Ok", "text": "Fact.", "source_url": "https://pl.wikipedia.org/wiki/Z"}]},
            {"name": "No source", "lat": 52.2305, "lon": 21.0105, "facts": [{"title": "t", "text": "x"}]},
        ]
        r = self.client.post("/api/lines/17/validate-places/", llm_output, format="json").json()
        self.assertEqual(r["valid_count"], 1)
        errors = {x["place"]: " ".join(x["errors"]) for x in r["rejected"]}
        self.assertIn("from the route", errors["Far away"])
        self.assertIn("swapped", errors["Swapped"])
        self.assertIn("no valid facts", errors["No source"])
        self.assertTrue(any("source_url" in w for w in r["warnings"]))

    def test_export_command(self):
        import json
        import os
        import tempfile

        from django.core.management import call_command
        path = os.path.join(tempfile.mkdtemp(), "l17.json")
        call_command("export_line_context", "17", "-o", path, verbosity=0)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["line"], "17")
