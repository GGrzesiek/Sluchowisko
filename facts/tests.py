import asyncio
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from config.asgi import application
from stories.models import Story
from transit.models import Line, Route, RouteStop, Stop, Vehicle
from transit.services import ingest_readings
from transit.warsaw_api import VehicleReading, WarsawApiError, fetch_vehicle_positions


def reading(lat, lon, seconds_ago):
    return VehicleReading("3201", "17", "5", lat, lon, timezone.now() - timedelta(seconds=seconds_ago))


class RideSocketTestCase(TransactionTestCase):
    def connect(self, number, query=""):
        communicator = WebsocketCommunicator(application, f"/ws/ride/{number}/{query}")
        return communicator

    async def receive(self, communicator):
        return await communicator.receive_json_from(timeout=5)


def story(group_id, **extra):
    return Story.objects.create(
        group_id=group_id,
        title=f"Historia {group_id}",
        narration="Narracja.",
        text="Tekst do przeczytania.",
        photos=[
            {
                "src": "https://upload.wikimedia.org/a.jpg",
                "alt": "Hala",
                "year": "1936",
                "caption": "Hala Mirowska",
                "author": "Jan Kowalski",
                "license": "domena publiczna",
                "source_url": "https://commons.wikimedia.org/wiki/File:A.jpg",
            }
        ],
        blocks=[{"type": "paragraph", "text": "Tekst do przeczytania."}],
        sources=[{"label": "Wikipedia", "href": "https://pl.wikipedia.org/wiki/Hale_Mirowskie"}],
        status=extra.pop("status", Story.Status.VERIFIED),
        **extra,
    )


@override_settings(CITY_API_LIVE=False, WS_PUSH_INTERVAL_SECONDS=3600)
class RideFlowTest(RideSocketTestCase):
    def setUp(self):
        ingest_readings([reading(52.2355, 21.0080, 12)])
        ingest_readings([reading(52.2345, 21.0078, 2)])

    def test_heading_and_speed_computed(self):
        v = Vehicle.objects.get(number="3201")
        self.assertTrue(150 < v.heading < 210)
        self.assertGreater(v.speed_mps, 5)

    async def test_unknown_vehicle_closes_with_error(self):
        c = self.connect("nope")
        await c.connect()
        self.assertEqual((await self.receive(c))["data"], {"code": "vehicle_not_found"})
        out = await c.receive_output(timeout=5)
        self.assertEqual((out["type"], out["code"]), ("websocket.close", 4404))

    async def test_bad_client_messages_do_not_kill_connection(self):
        c = self.connect("3201")
        await c.connect()
        await c.send_to(text_data="not json")
        await c.send_to(bytes_data=b"\x00")
        await c.send_json_to({"type": "seen", "fact_id": 1})
        await c.send_json_to({"type": "ping"})
        codes = []
        while True:
            m = await self.receive(c)
            if m["type"] == "pong":
                break
            if m["type"] == "error":
                codes.append(m["data"]["code"])
        self.assertEqual([c for c in codes if c != "no_route"], ["invalid_json", "unknown_message"])
        await c.disconnect()

    async def test_disconnect_stops_push_loop(self):
        c = self.connect("3201")
        await c.connect()
        await self.receive(c)
        await c.disconnect()
        await asyncio.sleep(0.1)
        self.assertEqual([t for t in asyncio.all_tasks() if "_push_loop" in repr(t)], [])

    @patch("facts.consumers._collect", side_effect=[RuntimeError("boom"), {"errors": []}])
    @override_settings(WS_PUSH_INTERVAL_SECONDS=0.05)
    async def test_push_failure_is_reported_and_loop_survives(self, collect):
        c = self.connect("3201")
        await c.connect()
        self.assertEqual((await self.receive(c))["data"], {"code": "internal"})
        await asyncio.sleep(0.2)
        self.assertGreaterEqual(collect.call_count, 2)
        await c.disconnect()


@override_settings(CITY_API_LIVE=False, WS_PUSH_INTERVAL_SECONDS=0.05)
class StoryLocationTest(RideSocketTestCase):
    def setUp(self):
        line = Line.objects.create(number="22", kind=Line.TRAM)
        route = Route.objects.create(line=line, code="TP-WIA", last_stop_name="Wiatraczna", stop_count=3)
        for order, (name, lat) in enumerate([("Powązkowska", 52.2480), ("Niska", 52.2460), ("Okopowa", 52.2440)], 1):
            stop = Stop.objects.create(zespol=str(5000 + order), slupek="01", name=name, lat=lat, lon=20.9860)
            RouteStop.objects.create(route=route, order=order, zespol=stop.zespol, slupek="01", stop=stop)
        self.set_position(52.2461)

    def set_position(self, lat):
        ingest_readings([live("3122", "22", lat + 0.0003, 20.9860, seconds_ago=10)])
        ingest_readings([live("3122", "22", lat, 20.9860, seconds_ago=1)])

    async def messages(self, communicator, count):
        received = []
        while len(received) < count:
            message = await self.receive(communicator)
            if message["type"] != "audio":
                received.append(message)
        return received

    async def test_sends_route_then_story_of_the_current_stop_group(self):
        await database_sync_to_async(story)("5002")
        c = self.connect("3122")
        await c.connect()
        route, location = await self.messages(c, 2)
        self.assertEqual(route["type"], "route")
        self.assertEqual(location["type"], "location")
        self.assertEqual(location["data"]["groupId"], "5002")
        content = location["data"]["story"]
        self.assertEqual(content["title"], "Historia 5002")
        self.assertEqual(content["body"], {"format": "plain", "text": "Tekst do przeczytania."})
        self.assertEqual(content["photos"][0]["credit"], "Fot. Jan Kowalski · domena publiczna")
        self.assertNotIn("narration", content)
        self.assertEqual(content["blocks"], [{"type": "paragraph", "text": "Tekst do przeczytania."}])
        self.assertEqual(content["sources"][0]["label"], "Wikipedia")
        await c.disconnect()

    async def test_story_is_sent_once_per_stop_group(self):
        await database_sync_to_async(story)("5002")
        c = self.connect("3122")
        await c.connect()
        await self.messages(c, 2)
        self.assertTrue(await c.receive_nothing(timeout=0.5))
        await c.disconnect()

    async def test_stop_group_without_story_gets_an_empty_location(self):
        c = self.connect("3122")
        await c.connect()
        _, location = await self.messages(c, 2)
        self.assertEqual(location["data"], {"groupId": "5002", "story": None})
        await c.disconnect()

    async def test_draft_and_rejected_stories_are_not_sent(self):
        await database_sync_to_async(story)("5002", status=Story.Status.DRAFT)
        c = self.connect("3122")
        await c.connect()
        _, location = await self.messages(c, 2)
        self.assertIsNone(location["data"]["story"])
        await c.disconnect()

    async def test_both_poles_of_a_stop_group_return_the_same_story(self):
        def add_opposite_direction():
            line = Line.objects.get(number="22")
            back = Route.objects.create(line=line, code="TP-POW", last_stop_name="Powązkowska", stop_count=2)
            for order, (slupek, lat) in enumerate([("06", 52.2441), ("07", 52.2461)], 1):
                zespol = "5003" if slupek == "06" else "5002"
                stop = Stop.objects.create(zespol=zespol, slupek=slupek, name="Okopowa", lat=lat, lon=20.9861)
                RouteStop.objects.create(route=back, order=order, zespol=zespol, slupek=slupek, stop=stop)
            story("5003")
            self.set_position(52.2441)
            ingest_readings([live("4001", "22", 52.2444, 20.9861, seconds_ago=10)])
            ingest_readings([live("4001", "22", 52.2441, 20.9861, seconds_ago=1)])

        await database_sync_to_async(add_opposite_direction)()
        results = []
        for number in ("3122", "4001"):
            c = self.connect(number)
            await c.connect()
            messages = await self.messages(c, 2)
            results.append(messages[1]["data"])
            await c.disconnect()
        self.assertEqual(results[0]["groupId"], results[1]["groupId"])
        self.assertIsNotNone(results[1]["story"])

    async def test_new_story_is_sent_when_the_vehicle_reaches_the_next_stop_group(self):
        await database_sync_to_async(story)("5002")
        await database_sync_to_async(story)("5003")
        c = self.connect("3122")
        await c.connect()
        await self.messages(c, 2)
        await database_sync_to_async(self.set_position)(52.2440)
        route, location = await self.messages(c, 2)
        self.assertEqual(route["type"], "route")
        self.assertEqual(location["data"]["groupId"], "5003")
        self.assertEqual(location["data"]["story"]["title"], "Historia 5003")
        await c.disconnect()


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


class LiveRideStopsTest(RideSocketTestCase):
    def setUp(self):
        cache.clear()
        line = Line.objects.create(number="22", kind=Line.TRAM)
        route = Route.objects.create(line=line, code="TP-WIA", last_stop_name="Wiatraczna", stop_count=3)
        for order, (name, lat) in enumerate([("Powązkowska", 52.2480), ("Niska", 52.2460), ("Okopowa", 52.2440)], 1):
            stop = Stop.objects.create(zespol=str(5000 + order), slupek="01", name=name, lat=lat, lon=20.9860)
            RouteStop.objects.create(route=route, order=order, zespol=stop.zespol, slupek="01", stop=stop)
        Line.objects.create(number="999", kind=Line.BUS)

    def feed(self, *readings):
        return lambda vehicle_type=2, line=None, **_: [r for r in readings if (r.line == "999") == (vehicle_type == 1)]

    async def first_message(self, number):
        c = self.connect(number)
        await c.connect()
        msg = await self.receive(c)
        await c.disconnect()
        return msg

    @patch("transit.services.fetch_vehicle_positions")
    async def test_pushes_route_first(self, fetch):
        fetch.side_effect = self.feed(live("3122", "22", 52.2461, 20.9860))
        msg = await self.first_message("3122")
        self.assertEqual(msg["type"], "route")
        self.assertEqual(msg["data"]["line"], "22")
        self.assertEqual(msg["data"]["destination"], "Wiatraczna")
        self.assertEqual([s["name"] for s in msg["data"]["stops"]], ["Powązkowska", "Niska", "Okopowa"])

    @patch("transit.services.fetch_vehicle_positions")
    async def test_unknown_vehicle(self, fetch):
        fetch.side_effect = self.feed()
        msg = await self.first_message("4040")
        self.assertEqual((msg["type"], msg["data"]["code"]), ("error", "vehicle_not_found"))

    @patch("transit.services.fetch_vehicle_positions")
    async def test_line_without_route(self, fetch):
        fetch.side_effect = self.feed(live("1000", "999", 52.20, 21.00))
        msg = await self.first_message("1000")
        self.assertEqual((msg["type"], msg["data"]), ("error", {"code": "no_route", "line": "999"}))

    @patch("transit.services.fetch_vehicle_positions", side_effect=WarsawApiError("down"))
    async def test_city_api_down_keeps_connection_open(self, fetch):
        c = self.connect("3122")
        await c.connect()
        self.assertEqual((await self.receive(c))["data"], {"code": "city_api"})
        self.assertTrue(await c.receive_nothing(timeout=0.5))
        await c.disconnect()

    @patch("transit.services.fetch_vehicle_positions")
    async def test_falls_back_to_recent_position_when_city_api_fails(self, fetch):
        await database_sync_to_async(ingest_readings)([live("3122", "22", 52.2461, 20.9860, seconds_ago=20)])
        fetch.side_effect = WarsawApiError("down")
        msg = await self.first_message("3122")
        self.assertEqual((msg["type"], msg["data"]["vehicle"]), ("route", "3122"))

    @patch("transit.services.fetch_vehicle_positions")
    async def test_stale_position_is_not_served_when_city_api_fails(self, fetch):
        await database_sync_to_async(ingest_readings)([live("3122", "22", 52.2461, 20.9860, seconds_ago=3600)])
        fetch.side_effect = WarsawApiError("down")
        msg = await self.first_message("3122")
        self.assertEqual((msg["type"], msg["data"]["code"]), ("error", "no_live_data"))

    @patch("transit.services.fetch_vehicle_positions", side_effect=WarsawApiError("down"))
    async def test_failure_is_cached_so_city_api_is_not_hammered(self, fetch):
        await self.first_message("3122")
        await self.first_message("3122")
        self.assertEqual(fetch.call_count, 1)


class RideStopsRestTest(TestCase):
    def setUp(self):
        cache.clear()
        line = Line.objects.create(number="22", kind=Line.TRAM)
        route = Route.objects.create(line=line, code="TP-WIA", last_stop_name="Wiatraczna", stop_count=2)
        for order, (name, lat) in enumerate([("Powązkowska", 52.2480), ("Niska", 52.2460)], 1):
            stop = Stop.objects.create(zespol=str(5000 + order), slupek="01", name=name, lat=lat, lon=20.9860)
            RouteStop.objects.create(route=route, order=order, zespol=stop.zespol, slupek="01", stop=stop)

    @patch("transit.services.fetch_vehicle_positions", side_effect=lambda **_: [live("3122", "22", 52.2461, 20.9860)])
    def test_returns_ride_info(self, fetch):
        r = APIClient().get("/api/ride/3122/stops/")
        self.assertEqual((r.status_code, r.json()["line"], r.json()["destination"]), (200, "22", "Wiatraczna"))


class DepotRouteTest(TestCase):
    def setUp(self):
        cache.clear()
        line = Line.objects.create(number="161", kind=Line.BUS)
        stops = [
            Stop.objects.create(zespol=str(7000 + i), slupek="01", name=f"P{i}", lat=52.2 - i * 0.002, lon=21.2)
            for i in range(3)
        ]
        for code, last in (("TD-DEPOT", "Zajezdnia"), ("TO-REAL", "Pasażerska")):
            route = Route.objects.create(line=line, code=code, last_stop_name=last, stop_count=3)
            for order, stop in enumerate(stops, 1):
                RouteStop.objects.create(route=route, order=order, zespol=stop.zespol, slupek="01", stop=stop)
        ingest_readings([live("1012", "161", 52.2, 21.2, seconds_ago=20)])

    @override_settings(CITY_API_LIVE=False)
    def test_depot_route_is_not_picked_when_a_passenger_route_exists(self):
        r = APIClient().get("/api/ride/1012/stops/")
        self.assertEqual((r.status_code, r.json()["destination"]), (200, "Pasażerska"))

    @override_settings(CITY_API_LIVE=False)
    def test_depot_route_is_used_when_it_is_the_only_one(self):
        Route.objects.filter(code="TO-REAL").delete()
        r = APIClient().get("/api/ride/1012/stops/")
        self.assertEqual(r.json()["destination"], "Zajezdnia")


class LiveHealthTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch("transit.services.fetch_vehicle_positions", return_value=[live("3122", "22", 52.2461, 20.9860)])
    def test_health(self, fetch):
        r = APIClient().get("/api/health/")
        self.assertEqual((r.status_code, r.json()), (200, {"db": True, "city_api": True}))

    @patch("transit.services.fetch_vehicle_positions", side_effect=WarsawApiError("down"))
    def test_health_reports_city_api_down(self, fetch):
        r = APIClient().get("/api/health/")
        self.assertEqual((r.status_code, r.json()), (503, {"db": True, "city_api": False}))


@override_settings(CITY_API_LIVE=False)
class FedRideStopsTest(LiveRideStopsTest):
    @patch("transit.services.fetch_vehicle_positions")
    async def test_pushes_route_first(self, fetch):
        await database_sync_to_async(ingest_readings)([live("3122", "22", 52.2461, 20.9860)])
        msg = await self.first_message("3122")
        self.assertEqual((msg["type"], msg["data"]["destination"]), ("route", "Wiatraczna"))
        fetch.assert_not_called()

    @patch("transit.services.fetch_vehicle_positions")
    async def test_line_without_route(self, fetch):
        await database_sync_to_async(ingest_readings)([live("1000", "999", 52.20, 21.00)])
        msg = await self.first_message("1000")
        self.assertEqual((msg["type"], msg["data"]["code"]), ("error", "no_route"))

    @patch("transit.services.fetch_vehicle_positions")
    async def test_city_api_down_keeps_connection_open(self, fetch):
        msg = await self.first_message("3122")
        self.assertEqual(msg["data"]["code"], "vehicle_not_found")
        fetch.assert_not_called()

    @patch("transit.services.fetch_vehicle_positions")
    async def test_falls_back_to_recent_position_when_city_api_fails(self, fetch):
        await database_sync_to_async(ingest_readings)([live("3122", "22", 52.2461, 20.9860, seconds_ago=20)])
        msg = await self.first_message("3122")
        self.assertEqual(msg["type"], "route")

    @patch("transit.services.fetch_vehicle_positions")
    async def test_stale_position_is_not_served_when_city_api_fails(self, fetch):
        await database_sync_to_async(ingest_readings)([live("3122", "22", 52.2461, 20.9860, seconds_ago=3600)])
        msg = await self.first_message("3122")
        self.assertEqual(msg["data"]["code"], "no_live_data")

    @patch("transit.services.fetch_vehicle_positions")
    async def test_failure_is_cached_so_city_api_is_not_hammered(self, fetch):
        await self.first_message("3122")
        fetch.assert_not_called()


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


class StableRouteTest(TestCase):
    def setUp(self):
        cache.clear()
        self.line = Line.objects.create(number="22", kind=Line.TRAM)
        self.stops = [
            Stop.objects.create(zespol=str(6000 + i), slupek="01", name=f"S{i}", lat=52.2400, lon=21.0000 + i * 0.003)
            for i in range(5)
        ]
        self.main = self.route("TP-EAST", "Wschód", self.stops)
        self.depot = self.route("TZ-DEPOT", "Zajezdnia", self.stops[:3])
        self.west = self.route("TP-WEST", "Zachód", list(reversed(self.stops)))

    def route(self, code, last, stops):
        route = Route.objects.create(line=self.line, code=code, last_stop_name=last, stop_count=len(stops))
        for order, stop in enumerate(stops, 1):
            RouteStop.objects.create(route=route, order=order, zespol=stop.zespol, slupek="01", stop=stop)
        return route

    def vehicle(self, lon, heading=None, speed=0.0, seconds_ago=5):
        return Vehicle.objects.create(
            number="3157",
            line="22",
            brigade="1",
            lat=52.2400,
            lon=lon,
            heading=heading,
            speed_mps=speed,
            reported_at=timezone.now() - timedelta(seconds=seconds_ago),
        )

    def test_depot_run_never_wins_on_a_shared_main_segment(self):
        from .ride_progress import build_ride_info

        v = self.vehicle(21.0040, heading=90)
        destinations = set()
        for _ in range(5):
            cache.delete("ride:route:3157")
            destinations.add(build_ride_info(v)["destination"])
        self.assertEqual(destinations, {"Wschód"})

    def test_remembered_direction_survives_a_stationary_vehicle(self):
        from .ride_progress import build_ride_info

        v = self.vehicle(21.0040, heading=270)
        self.assertEqual(build_ride_info(v)["destination"], "Zachód")
        Vehicle.objects.filter(pk=v.pk).update(heading=None)
        v.refresh_from_db()
        self.assertEqual(build_ride_info(v)["destination"], "Zachód")

    def test_turning_around_switches_direction(self):
        from .ride_progress import build_ride_info

        v = self.vehicle(21.0040, heading=90)
        self.assertEqual(build_ride_info(v)["destination"], "Wschód")
        Vehicle.objects.filter(pk=v.pk).update(heading=270)
        v.refresh_from_db()
        self.assertEqual(build_ride_info(v)["destination"], "Zachód")

    def test_position_moves_along_the_route_since_the_reading(self):
        from .ride_progress import build_ride_info

        v = self.vehicle(21.0040, heading=90, speed=6.0, seconds_ago=25)
        current = [s["name"] for s in build_ride_info(v)["stops"] if s["state"] == "current"]
        self.assertEqual(current, ["S2"])
        Vehicle.objects.filter(pk=v.pk).update(speed_mps=0.0)
        v.refresh_from_db()
        current = [s["name"] for s in build_ride_info(v)["stops"] if s["state"] == "current"]
        self.assertEqual(current, ["S1"])


@override_settings(CITY_API_LIVE=False, WS_PUSH_INTERVAL_SECONDS=0.05)
class RideAudioTest(RideSocketTestCase):
    def setUp(self):
        LiveRideStopsTest.setUp(self)
        ingest_readings([live("3122", "22", 52.2478, 20.9860)])

    def story(self, group_id, title, **extra):
        from stories.models import Story

        fields = {"title": title, "narration": "n", "text": "t", "status": Story.Status.VERIFIED, **extra}
        return Story.objects.create(group_id=group_id, **fields)

    async def audio_message(self, communicator):
        while True:
            msg = await self.receive(communicator)
            if msg["type"] == "audio":
                return msg["data"]

    async def test_sends_audio_of_next_stop_group_once(self):
        await database_sync_to_async(self.story)("5002", "Niska", audio_url="audio/5002.mp3", audio_seconds=42)
        c = self.connect("3122")
        await c.connect()
        self.assertEqual((await self.receive(c))["type"], "route")
        audio = await self.audio_message(c)
        self.assertEqual(
            audio,
            {
                "groupId": "5002",
                "name": "Niska",
                "available": True,
                "src": "audio/5002.mp3",
                "seconds": 42,
                "aiVoice": True,
            },
        )
        self.assertEqual((await self.receive(c))["type"], "location")
        self.assertTrue(await c.receive_nothing(timeout=0.3))
        await c.disconnect()

    async def test_stop_already_passed_gets_no_audio(self):
        await database_sync_to_async(self.story)("5001", "Powązkowska", audio_url="audio/5001.mp3", audio_seconds=9)
        c = self.connect("3122")
        await c.connect()
        self.assertEqual((await self.audio_message(c))["groupId"], "5002")
        await c.disconnect()

    async def test_stop_group_without_recording_keeps_connection(self):
        await database_sync_to_async(self.story)("5002", "Niska")
        c = self.connect("3122")
        await c.connect()
        audio = await self.audio_message(c)
        self.assertEqual(audio, {"groupId": "5002", "name": "Niska", "available": False})
        self.assertEqual((await self.receive(c))["type"], "location")
        self.assertTrue(await c.receive_nothing(timeout=0.3))
        await c.send_json_to({"type": "ping"})
        self.assertEqual((await self.receive(c))["type"], "pong")
        await c.disconnect()

    async def test_draft_story_audio_is_not_sent(self):
        await database_sync_to_async(self.story)("5002", "Niska", status="draft")
        c = self.connect("3122")
        await c.connect()
        self.assertFalse((await self.audio_message(c))["available"])
        await c.disconnect()

    async def test_reconnect_after_dropped_connection_sends_audio_again(self):
        await database_sync_to_async(self.story)("5002", "Niska", audio_url="audio/5002.mp3", audio_seconds=42)
        first = self.connect("3122")
        await first.connect()
        await self.receive(first)
        await first.disconnect()
        await asyncio.sleep(0.1)
        self.assertEqual([t for t in asyncio.all_tasks() if "_push_loop" in repr(t)], [])
        second = self.connect("3122")
        await second.connect()
        self.assertTrue((await self.audio_message(second))["available"])
        await second.disconnect()

    async def test_database_is_asked_only_when_the_group_changes(self):
        await database_sync_to_async(self.story)("5002", "Niska", audio_url="audio/5002.mp3", audio_seconds=42)
        await database_sync_to_async(self.story)("5003", "Okopowa", audio_url="audio/5003.mp3", audio_seconds=30)
        with patch(
            "facts.consumers._audio_message", wraps=__import__("facts.consumers").consumers._audio_message
        ) as spy:
            c = self.connect("3122")
            await c.connect()
            self.assertEqual((await self.audio_message(c))["groupId"], "5002")
            await asyncio.sleep(0.3)
            self.assertEqual(spy.call_count, 1)
            await database_sync_to_async(ingest_readings)([live("3122", "22", 52.2458, 20.9860, seconds_ago=1)])
            self.assertEqual((await self.audio_message(c))["groupId"], "5003")
            self.assertEqual(spy.call_count, 2)
            await c.disconnect()
