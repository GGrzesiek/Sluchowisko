import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from transit.models import Line, Route, RouteStop, Stop, Vehicle

from .models import Story

TOKEN = "test-token"


def story_payload(group_id="7001", **extra):
    return {
        "group_id": group_id,
        "narration": "Krótka narracja.",
        "text": "Dłuższy tekst do przeczytania.",
        "photos": [
            {
                "src": "https://upload.wikimedia.org/a.jpg",
                "alt": "Hala",
                "year": "1936",
                "caption": "Hala Mirowska",
                "author": "NN",
                "license": "domena publiczna",
            }
        ],
        "sources": [{"label": "Hale Mirowskie · Wikipedia", "href": "https://pl.wikipedia.org/wiki/Hale_Mirowskie"}],
        "generated_by": "claude",
        **extra,
    }


@override_settings(STORIES_WRITE_TOKEN=TOKEN)
class StoryApiTest(TestCase):
    def setUp(self):
        for group_id, name, lat in (("7001", "Alfa", 52.20), ("7002", "Beta", 52.21), ("7003", "Gamma", 52.22)):
            Stop.objects.create(zespol=group_id, slupek="01", name=name, lat=lat, lon=21.0)
        self.client = APIClient()
        self.agent = APIClient(HTTP_AUTHORIZATION=f"Bearer {TOKEN}")

    def test_write_needs_token(self):
        self.assertEqual(self.client.put("/api/stories/7001/", story_payload(), format="json").status_code, 403)
        bad = APIClient(HTTP_AUTHORIZATION="Bearer nope")
        self.assertEqual(bad.post("/api/stories/", [story_payload()], format="json").status_code, 403)

    @override_settings(STORIES_WRITE_TOKEN="")
    def test_write_closed_without_configured_token(self):
        self.assertEqual(self.agent.put("/api/stories/7001/", story_payload(), format="json").status_code, 403)

    def test_put_creates_then_updates(self):
        r = self.agent.put("/api/stories/7001/", story_payload(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["title"], "Alfa")
        self.assertEqual(r.json()["status"], "draft")
        r = self.agent.put("/api/stories/7001/", story_payload(text="Nowy tekst."), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Story.objects.get().text, "Nowy tekst.")

    def test_bulk_post_is_all_or_nothing(self):
        r = self.agent.post("/api/stories/", [story_payload("7001"), story_payload("9999")], format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("1", r.json()["errors"])
        self.assertFalse(Story.objects.exists())
        r = self.agent.post("/api/stories/", [story_payload("7001"), story_payload("7002")], format="json")
        self.assertEqual(r.json(), {"created": ["7001", "7002"], "updated": []})

    def test_validation(self):
        cases = [
            story_payload(sources=[]),
            story_payload(photos=[]),
            story_payload(photos=story_payload()["photos"] * 6),
            story_payload(sources=[{"label": "x", "href": "not-a-url"}]),
            story_payload(photos=[{**story_payload()["photos"][0], "license": ""}]),
            story_payload(status="published"),
        ]
        for payload in cases:
            self.assertEqual(self.agent.put("/api/stories/7001/", payload, format="json").status_code, 400)

    def test_frontend_sees_only_verified(self):
        self.agent.put("/api/stories/7001/", story_payload(), format="json")
        self.assertEqual(self.client.get("/api/stories/7001/").status_code, 404)
        self.assertEqual(self.agent.get("/api/stories/7001/?draft=1").status_code, 200)
        r = self.agent.patch("/api/stories/7001/", {"status": "verified"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        body = self.client.get("/api/stories/7001/").json()
        self.assertEqual(body["title"], "Alfa")
        self.assertEqual(body["body"], {"format": "plain", "text": "Dłuższy tekst do przeczytania."})
        self.assertEqual(body["photos"][0]["credit"], "Fot. NN · domena publiczna")
        self.assertIsNone(body["audio"])

    def test_line_stories_lists_groups_in_route_order(self):
        line = Line.objects.create(number="99", kind="tram")
        route = Route.objects.create(line=line, code="TP-X", stop_count=3)
        for i, stop in enumerate(Stop.objects.order_by("lat")):
            RouteStop.objects.create(route=route, order=i + 1, zespol=stop.zespol, slupek=stop.slupek, stop=stop)
        self.agent.put("/api/stories/7002/", story_payload("7002"), format="json")
        groups = self.client.get("/api/lines/99/stories/").json()["stopGroups"]
        self.assertEqual([g["groupId"] for g in groups], ["7001", "7002", "7003"])
        self.assertEqual([g["storyStatus"] for g in groups], [None, "draft", None])

    def test_drafts_need_token(self):
        self.agent.put("/api/stories/7001/", story_payload(), format="json")
        self.assertEqual(self.client.get("/api/stories/7001/?draft=1").status_code, 403)
        self.assertEqual(self.agent.get("/api/stories/7001/?draft=1").status_code, 200)

    def test_line_stories_without_main_route_uses_service_variants(self):
        line = Line.objects.create(number="117", kind="bus")
        detour = Route.objects.create(line=line, code="TO-GOC", stop_count=2)
        depot = Route.objects.create(line=line, code="TD-ZAJ", stop_count=1)
        alfa, beta, gamma = Stop.objects.order_by("lat")
        for i, stop in enumerate((alfa, beta)):
            RouteStop.objects.create(route=detour, order=i + 1, zespol=stop.zespol, slupek=stop.slupek, stop=stop)
        RouteStop.objects.create(route=depot, order=1, zespol=gamma.zespol, slupek=gamma.slupek, stop=gamma)
        groups = self.client.get("/api/lines/117/stories/").json()["stopGroups"]
        self.assertEqual([g["groupId"] for g in groups], ["7001", "7002"])

    def test_ride_has_story_only_for_verified(self):
        line = Line.objects.create(number="99", kind="tram")
        route = Route.objects.create(line=line, code="TP-X", last_stop_name="Gamma", stop_count=3)
        for i, stop in enumerate(Stop.objects.order_by("lat")):
            RouteStop.objects.create(route=route, order=i + 1, zespol=stop.zespol, slupek=stop.slupek, stop=stop)
        Vehicle.objects.create(number="1", line="99", lat=52.205, lon=21.0, heading=0, reported_at=timezone.now())
        self.agent.put("/api/stories/7002/", story_payload("7002", status="verified"), format="json")
        self.agent.put("/api/stories/7003/", story_payload("7003"), format="json")
        stops = self.client.get("/api/ride/1/stops/").json()["stops"]
        self.assertEqual([s.get("hasStory", False) for s in stops], [False, True, False])
        self.assertEqual(stops[1]["groupId"], "7002")

    def test_export_writes_static_files(self):
        self.agent.put("/api/stories/7001/", story_payload(status="verified"), format="json")
        self.agent.put("/api/stories/7002/", story_payload("7002"), format="json")
        with tempfile.TemporaryDirectory() as out:
            call_command("export_stories", "--out", out, verbosity=0)
            self.assertEqual(json.loads((Path(out) / "index.json").read_text()), [{"groupId": "7001", "title": "Alfa"}])
            self.assertFalse((Path(out) / "7002.json").exists())
