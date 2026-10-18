from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from transit.models import Line, Route, RouteStop, Stop
from transit.services import ingest_readings
from transit.warsaw_api import VehicleReading, WarsawApiError

from . import ride_progress

STOPS = [("6001", "Alfa", 52.2480), ("6002", "Beta", 52.2460), ("6003", "Gamma", 52.2440)]


def reading(number, line, lat, seconds_ago, lon=20.9860):
    return VehicleReading(number, line, "1", lat, lon, timezone.now() - timedelta(seconds=seconds_ago))


def build_line(number, kind, routes):
    line = Line.objects.create(number=number, kind=kind)
    for code, last, pole, names in routes:
        route = Route.objects.create(line=line, code=code, last_stop_name=last, stop_count=len(names))
        for order, (group, name, lat) in enumerate(names, 1):
            lon = 20.9860 if pole == "01" else 20.9864
            stop, _ = Stop.objects.get_or_create(
                zespol=group, slupek=pole, defaults={"name": name, "lat": lat, "lon": lon}
            )
            RouteStop.objects.create(route=route, order=order, zespol=group, slupek=pole, stop=stop)


@override_settings(CITY_API_LIVE=False, APP_URL="http://localhost:5173")
class LiveVehiclesTest(TestCase):
    def setUp(self):
        cache.clear()
        build_line("22", Line.TRAM, [("TP-GAM", "Gamma", "01", STOPS), ("TP-ALF", "Alfa", "02", STOPS[::-1])])
        ingest_readings([reading("3001", "22", 52.2479, 20), reading("3002", "22", 52.2442, 20, lon=20.9864)])
        ingest_readings([reading("3001", "22", 52.2476, 5), reading("3002", "22", 52.2450, 5, lon=20.9864)])
        ingest_readings([reading("3003", "22", 52.2460, 3600)])
        self.client = APIClient()

    def live(self, query):
        return self.client.get(f"/api/vehicles/?{query}").json()

    def test_two_directions_are_told_apart_and_stale_vehicle_is_skipped(self):
        data = self.live("line=22&live=1")
        rows = {v["number"]: v for v in data["vehicles"]}
        self.assertEqual(sorted(rows), ["3001", "3002"])
        self.assertEqual((rows["3001"]["route"], rows["3001"]["destination"]), ("TP-GAM", "Gamma"))
        self.assertEqual((rows["3002"]["route"], rows["3002"]["destination"]), ("TP-ALF", "Alfa"))
        self.assertEqual((rows["3001"]["stop"], rows["3001"]["nextStop"]), ("Alfa", "Beta"))
        self.assertAlmostEqual(rows["3001"]["ageS"], 5, delta=2)
        self.assertEqual(rows["3001"]["appUrl"], "http://localhost:5173/?line=22&vehicle=3001")

    def test_route_filter(self):
        data = self.live("line=22&live=1&route=tp-alf")
        self.assertEqual([v["number"] for v in data["vehicles"]], ["3002"])

    def test_unknown_route_is_explained(self):
        data = self.live("line=22&live=1&route=TP-XYZ")
        self.assertEqual(data["vehicles"], [])
        self.assertIn("no route TP-XYZ", data["detail"])
        self.assertIn("TP-ALF, TP-GAM", data["detail"])

    def test_only_stale_vehicles_is_explained(self):
        Line.objects.create(number="7", kind=Line.TRAM)
        build_line("9", Line.TRAM, [("TP-GAM", "Gamma", "01", STOPS)])
        ingest_readings([reading("3900", "9", 52.2460, 3600)])
        data = self.live("line=9&live=1")
        self.assertEqual(data["vehicles"], [])
        self.assertIn("newest one (3900) is 60 min old", data["detail"])
        self.assertIn("no routes", self.live("line=7&live=1")["detail"])

    def test_live_needs_line_and_old_listing_still_works(self):
        self.assertEqual(self.client.get("/api/vehicles/?live=1").status_code, 400)
        self.assertEqual(len(self.client.get("/api/vehicles/?line=22").json()), 3)

    @override_settings(CITY_API_LIVE=True)
    @patch("transit.services.fetch_vehicle_positions")
    def test_refreshes_from_city_feed(self, fetch):
        fetch.side_effect = lambda vehicle_type=2, **_: [reading("3004", "22", 52.2470, 2)] if vehicle_type == 2 else []
        data = self.live("line=22&live=1")
        self.assertTrue(data["refreshed"])
        self.assertIn("3004", [v["number"] for v in data["vehicles"]])

    @override_settings(CITY_API_LIVE=True)
    @patch("transit.services.fetch_vehicle_positions", side_effect=WarsawApiError("down"))
    def test_city_feed_down_still_lists_database(self, fetch):
        data = self.live("line=22&live=1")
        self.assertFalse(data["refreshed"])
        self.assertEqual(data["cityApiError"], "down")
        self.assertEqual(len(data["vehicles"]), 2)

    @override_settings(CITY_API_LIVE=True)
    @patch("transit.services.fetch_vehicle_positions", side_effect=WarsawApiError("down"))
    def test_city_feed_down_with_no_vehicles_says_so(self, fetch):
        build_line("179", Line.BUS, [("TP-GAM", "Gamma", "01", STOPS)])
        data = self.live("line=179&live=1")
        self.assertEqual(data["vehicles"], [])
        self.assertIn("could not be reached", data["detail"])

    def test_routes_are_loaded_once_per_line(self):
        with patch("facts.ride_progress._route_points", wraps=ride_progress._route_points) as points:
            data = self.live("line=22&live=1")
        self.assertEqual(len(data["vehicles"]), 2)
        self.assertEqual(points.call_count, 2)


@override_settings(CITY_API_LIVE=False, APP_URL="http://localhost:5173")
class DebugEndpointsTest(TestCase):
    def setUp(self):
        cache.clear()
        night = [("6101", "Metro Wilanowska", 52.1800), ("6102", "Skolimów", 52.1700)]
        build_line("N50", Line.NIGHT, [("TO-SKL", "Skolimów", "01", night)])
        build_line("161", Line.BUS, [("TO-OLE", "Olecka", "01", STOPS)])
        ingest_readings([reading("9083", "N50", 52.1790, 3)])
        self.client = APIClient()

    def test_night_lists_n50_with_app_url(self):
        data = self.client.get("/api/debug/night/").json()
        self.assertEqual(data["line"], "N50")
        self.assertEqual(data["vehicles"][0]["appUrl"], "http://localhost:5173/?line=N50&vehicle=9083")

    def test_day_without_vehicles_points_to_night(self):
        data = self.client.get("/api/debug/day/").json()
        self.assertEqual((data["line"], data["vehicles"]), ("161", []))
        self.assertIn("/api/debug/night/", data["detail"])

    def test_command_lists_vehicle_and_lowercase_line_works(self):
        out = StringIO()
        call_command("live_vehicles", "--line", "n50", "--no-refresh", stdout=out)
        self.assertIn("9083", out.getvalue())
        self.assertIn("TO-SKL -> Skolimów", out.getvalue())
        self.assertIn("http://localhost:5173/?line=N50&vehicle=9083", out.getvalue())

    def test_command_explains_empty_line(self):
        out = StringIO()
        call_command("live_vehicles", "--line", "161", "--no-refresh", stdout=out)
        self.assertIn("No vehicle of line 161", out.getvalue())
