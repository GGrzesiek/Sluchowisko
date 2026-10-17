from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from transit.models import Vehicle
from transit.services import ingest_readings
from transit.warsaw_api import VehicleReading, fetch_vehicle_positions


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
        self.assertEqual(
            self.client.post(f"/api/facts/{fact_id}/seen/", HTTP_X_DEVICE_ID="dev-1").status_code, 204
        )
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
