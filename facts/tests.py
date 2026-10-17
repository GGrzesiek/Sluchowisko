from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from transit.models import Line, Route, RouteStop, Stop, Vehicle
from transit.services import ingest_readings
from transit.warsaw_api import VehicleReading, WarsawApiError, fetch_vehicle_positions


def reading(lat, lon, seconds_ago):
    return VehicleReading("3201", "17", "5", lat, lon, timezone.now() - timedelta(seconds=seconds_ago))


class RideFlowTest(TestCase):
    def setUp(self):
        call_command("load_facts", "--approve", verbosity=0)
        # Tram on Marszałkowska heading south, ~300 m north of PKiN, 10 s between readings
        ingest_readings([reading(52.2355, 21.0080, 12)])
        ingest_readings([reading(52.2345, 21.0078, 2)])
        self.client = APIClient()

    def test_heading_and_speed_computed(self):
        v = Vehicle.objects.get(number="3201")
        self.assertTrue(150 < v.heading < 210)  # roughly south
        self.assertGreater(v.speed_mps, 5)

    def test_ride_returns_fact_ahead_and_hides_seen(self):
        r = self.client.get("/api/ride/3201/", HTTP_X_DEVICE_ID="dev-1")
        self.assertEqual(r.status_code, 200)
        titles = [f["title"] for f in r.json()["facts"]]
        self.assertIn("Prezent, o który nikt nie prosił", titles)

        fact_id = r.json()["facts"][0]["id"]
        self.assertEqual(self.client.post(f"/api/facts/{fact_id}/seen/", HTTP_X_DEVICE_ID="dev-1").status_code, 204)
        r2 = self.client.get("/api/ride/3201/", HTTP_X_DEVICE_ID="dev-1")
        self.assertNotIn(fact_id, [f["id"] for f in r2.json()["facts"]])

    def test_place_behind_is_skipped(self):
        # Tram now heading north, away from PKiN, and far enough not to "always show"
        Vehicle.objects.filter(number="3201").update(heading=0)
        r = self.client.get("/api/ride/3201/")
        self.assertEqual(r.json()["facts"], [])

    def test_unknown_vehicle_404(self):
        self.assertEqual(self.client.get("/api/ride/nope/").status_code, 404)


@override_settings(WARSAW_API_KEY="x")
class ApiClientTest(TestCase):
    @patch("transit.warsaw_api.requests.post")
    def test_parses_feed_and_skips_bad_rows(self, get):
        get.return_value = MagicMock(
            json=lambda: {
                "result": [
                    {
                        "Lines": "17",
                        "Lon": 21.0,
                        "VehicleNumber": "3201",
                        "Time": "2026-10-17 12:00:00",
                        "Lat": 52.2,
                        "Brigade": "5",
                    },
                    {"Lines": "17", "VehicleNumber": "bad"},
                ]
            }
        )
        out = fetch_vehicle_positions(line="17")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].vehicle_number, "3201")


def live(number, line, lat, lon, seconds_ago=5):
    return VehicleReading(number, line, "1", lat, lon, timezone.now() - timedelta(seconds=seconds_ago))


class LiveRideStopsTest(TestCase):
    def setUp(self):
        cache.clear()
        line = Line.objects.create(number="22", kind=Line.TRAM)
        route = Route.objects.create(line=line, code="TP-WIA", last_stop_name="Wiatraczna", stop_count=3)
        for order, (name, lat) in enumerate([("Powązkowska", 52.2480), ("Niska", 52.2460), ("Okopowa", 52.2440)], 1):
            stop = Stop.objects.create(zespol=str(5000 + order), slupek="01", name=name, lat=lat, lon=20.9860)
            RouteStop.objects.create(route=route, order=order, zespol=stop.zespol, slupek="01", stop=stop)
        Line.objects.create(number="999", kind=Line.BUS)
        self.client = APIClient()

    def feed(self, *readings):
        return lambda vehicle_type=2, line=None, **_: [r for r in readings if (r.line == "999") == (vehicle_type == 1)]

    @patch("transit.services.fetch_vehicle_positions")
    def test_returns_ride_info_and_caches_city_feed(self, fetch):
        fetch.side_effect = self.feed(live("3122", "22", 52.2461, 20.9860))
        first = self.client.get("/api/ride/3122/stops/")
        second = self.client.get("/api/ride/3122/stops/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["destination"], "Wiatraczna")
        self.assertEqual(first.json()["line"], "22")
        self.assertEqual([s["name"] for s in first.json()["stops"]], ["Powązkowska", "Niska", "Okopowa"])
        self.assertEqual(fetch.call_count, 2)

    @patch("transit.services.fetch_vehicle_positions")
    def test_unknown_vehicle(self, fetch):
        fetch.side_effect = self.feed()
        r = self.client.get("/api/ride/4040/stops/")
        self.assertEqual((r.status_code, r.json()["code"]), (404, "vehicle_not_found"))

    @patch("transit.services.fetch_vehicle_positions")
    def test_line_without_route(self, fetch):
        fetch.side_effect = self.feed(live("1000", "999", 52.20, 21.00))
        r = self.client.get("/api/ride/1000/stops/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {"code": "no_route", "line": "999"})

    @patch("transit.services.fetch_vehicle_positions", side_effect=WarsawApiError("down"))
    def test_city_api_down(self, fetch):
        r = self.client.get("/api/ride/3122/stops/")
        self.assertEqual((r.status_code, r.json()["code"]), (502, "city_api"))

    @patch("transit.services.fetch_vehicle_positions")
    def test_health(self, fetch):
        fetch.side_effect = self.feed(live("3122", "22", 52.2461, 20.9860))
        r = self.client.get("/api/health/")
        self.assertEqual((r.status_code, r.json()), (200, {"db": True, "city_api": True}))

    @patch("transit.services.fetch_vehicle_positions")
    def test_falls_back_to_recent_position_when_city_api_fails(self, fetch):
        ingest_readings([live("3122", "22", 52.2461, 20.9860, seconds_ago=20)])
        fetch.side_effect = WarsawApiError("down")
        r = self.client.get("/api/ride/3122/stops/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["vehicle"], "3122")

    @patch("transit.services.fetch_vehicle_positions")
    def test_stale_position_is_not_served_when_city_api_fails(self, fetch):
        ingest_readings([live("3122", "22", 52.2461, 20.9860, seconds_ago=3600)])
        fetch.side_effect = WarsawApiError("down")
        r = self.client.get("/api/ride/3122/stops/")
        self.assertEqual((r.status_code, r.json()["code"]), (503, "no_live_data"))

    @patch("transit.services.fetch_vehicle_positions", side_effect=WarsawApiError("down"))
    def test_failure_is_cached_so_city_api_is_not_hammered(self, fetch):
        self.client.get("/api/ride/3122/stops/")
        self.client.get("/api/ride/3122/stops/")
        self.assertEqual(fetch.call_count, 1)

    @patch("transit.services.fetch_vehicle_positions", side_effect=WarsawApiError("down"))
    def test_health_reports_city_api_down(self, fetch):
        r = self.client.get("/api/health/")
        self.assertEqual((r.status_code, r.json()), (503, {"db": True, "city_api": False}))


@override_settings(CITY_API_LIVE=False)
class FedRideStopsTest(LiveRideStopsTest):
    @patch("transit.services.fetch_vehicle_positions")
    def test_returns_ride_info_and_caches_city_feed(self, fetch):
        ingest_readings([live("3122", "22", 52.2461, 20.9860)])
        r = self.client.get("/api/ride/3122/stops/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["destination"], "Wiatraczna")
        fetch.assert_not_called()

    @patch("transit.services.fetch_vehicle_positions")
    def test_line_without_route(self, fetch):
        ingest_readings([live("1000", "999", 52.20, 21.00)])
        r = self.client.get("/api/ride/1000/stops/")
        self.assertEqual((r.status_code, r.json()["code"]), (404, "no_route"))

    @patch("transit.services.fetch_vehicle_positions")
    def test_city_api_down(self, fetch):
        r = self.client.get("/api/ride/3122/stops/")
        self.assertEqual((r.status_code, r.json()["code"]), (404, "vehicle_not_found"))
        fetch.assert_not_called()

    @patch("transit.services.fetch_vehicle_positions")
    def test_falls_back_to_recent_position_when_city_api_fails(self, fetch):
        ingest_readings([live("3122", "22", 52.2461, 20.9860, seconds_ago=20)])
        self.assertEqual(self.client.get("/api/ride/3122/stops/").status_code, 200)

    @patch("transit.services.fetch_vehicle_positions")
    def test_stale_position_is_not_served_when_city_api_fails(self, fetch):
        ingest_readings([live("3122", "22", 52.2461, 20.9860, seconds_ago=3600)])
        r = self.client.get("/api/ride/3122/stops/")
        self.assertEqual((r.status_code, r.json()["code"]), (503, "no_live_data"))

    @patch("transit.services.fetch_vehicle_positions")
    def test_failure_is_cached_so_city_api_is_not_hammered(self, fetch):
        self.client.get("/api/ride/3122/stops/")
        fetch.assert_not_called()

    @patch("transit.services.fetch_vehicle_positions")
    def test_health(self, fetch):
        r = self.client.get("/api/health/")
        self.assertEqual((r.status_code, r.json()), (200, {"db": True}))
        fetch.assert_not_called()

    @patch("transit.services.fetch_vehicle_positions")
    def test_health_reports_city_api_down(self, fetch):
        self.test_health()


class PollVehiclesTest(TestCase):
    @patch("transit.management.commands.poll_vehicles.fetch_vehicle_positions")
    def test_stores_only_requested_lines(self, fetch):
        fetch.side_effect = lambda vehicle_type=2, **_: (
            [live("3122", "22", 52.2461, 20.9860), live("3300", "17", 52.2, 21.0)] if vehicle_type == 2 else []
        )
        call_command("poll_vehicles", "--line", "22", "--once", stdout=StringIO())
        self.assertEqual(list(Vehicle.objects.values_list("number", flat=True)), ["3122"])

    def test_demo_lines_come_from_data_file(self):
        from transit.management.commands.poll_vehicles import demo_lines

        self.assertEqual(demo_lines(), {"22", "18", "179", "169", "117"})


class FetchAttemptsTest(TestCase):
    @override_settings(WARSAW_API_KEY="x")
    @patch("transit.warsaw_api.time.sleep")
    @patch("transit.warsaw_api.requests.post")
    def test_single_attempt_does_not_retry_or_sleep(self, post, sleep):
        post.side_effect = requests.ConnectionError("boom")
        with self.assertRaises(WarsawApiError):
            fetch_vehicle_positions(vehicle_type=2, timeout=5, attempts=1)
        self.assertEqual(post.call_count, 1)
        sleep.assert_not_called()
        self.assertEqual(post.call_args.kwargs["timeout"], 5)
