import io
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from transit.models import Line, Route, RouteStop, Stop, Vehicle

from .models import Story

TOKEN = "test-token"
MEDIA_BUCKET = "test-media"
MEDIA = f"https://storage.googleapis.com/{MEDIA_BUCKET}"
COMMONS = "https://commons.wikimedia.org/wiki/File:Hala.jpg"


def story_payload(group_id="7001", **extra):
    return {
        "group_id": group_id,
        "narration": "Krótka narracja.",
        "text": "Dłuższy tekst do przeczytania.",
        "photos": [
            {
                "src": f"{MEDIA}/photos/{group_id}/i1.jpg",
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


@override_settings(STORIES_WRITE_TOKEN=TOKEN, GCS_MEDIA_BUCKET=MEDIA_BUCKET)
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

    def test_ride_lists_each_stop_group_once(self):
        Stop.objects.create(zespol="7002", slupek="02", name="Beta", lat=52.2105, lon=21.0)
        line = Line.objects.create(number="99", kind="tram")
        route = Route.objects.create(line=line, code="TP-X", last_stop_name="Gamma", stop_count=4)
        for i, stop in enumerate(Stop.objects.order_by("lat")):
            RouteStop.objects.create(route=route, order=i + 1, zespol=stop.zespol, slupek=stop.slupek, stop=stop)
        Vehicle.objects.create(number="1", line="99", lat=52.2102, lon=21.0, heading=0, reported_at=timezone.now())
        stops = self.client.get("/api/ride/1/stops/").json()["stops"]
        self.assertEqual([s["groupId"] for s in stops], ["7001", "7002", "7003"])
        self.assertEqual([s["state"] for s in stops], ["passed", "current", "next"])

    def test_export_writes_static_files(self):
        self.agent.put("/api/stories/7001/", story_payload(status="verified"), format="json")
        self.agent.put("/api/stories/7002/", story_payload("7002"), format="json")
        with tempfile.TemporaryDirectory() as out:
            call_command("export_stories", "--out", out, verbosity=0)
            self.assertEqual(json.loads((Path(out) / "index.json").read_text()), [{"groupId": "7001", "title": "Alfa"}])
            self.assertFalse((Path(out) / "7002.json").exists())


def external_photo(**extra):
    return {**story_payload()["photos"][0], "src": f"{COMMONS}?raw", "source_url": COMMONS, **extra}


@override_settings(STORIES_WRITE_TOKEN=TOKEN, GCS_MEDIA_BUCKET=MEDIA_BUCKET)
class PublishPhotosTest(TestCase):
    def setUp(self):
        Stop.objects.create(zespol="7001", slupek="01", name="Alfa", lat=52.20, lon=21.0)
        self.agent = APIClient(HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
        self.out = Path(tempfile.mkdtemp()) / "out"
        (self.out / "collected").mkdir(parents=True)
        (self.out / "images" / "7001").mkdir(parents=True)
        (self.out / "images" / "7001" / "i7.jpg").write_bytes(b"\xff\xd8\xff photo")
        collected = {"images": [{"id": "i7", "url": COMMONS, "file": "out/images/7001/i7.jpg"}]}
        (self.out / "collected" / "7001.json").write_text(json.dumps(collected))

    def publish(self, *args):
        stdout = io.StringIO()
        with (
            patch("stories.media.shutil.which", return_value="/usr/bin/gcloud"),
            patch("stories.media.subprocess.run", return_value=MagicMock(returncode=0)) as run,
        ):
            call_command("publish_photos", "--out", str(self.out), *args, stdout=stdout)
        return run, stdout.getvalue()

    def test_uploads_collector_file_and_points_src_at_media(self):
        Story.objects.create(group_id="7001", title="Alfa", narration="n", text="t", photos=[external_photo()])
        run, _ = self.publish()
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[1:3], ["storage", "cp"])
        self.assertEqual(Path(cmd[3]), self.out / "images" / "7001" / "i7.jpg")
        self.assertEqual(cmd[4], f"gs://{MEDIA_BUCKET}/photos/7001/i7.jpg")
        photo = Story.objects.get().photos[0]
        self.assertEqual(photo["src"], f"{MEDIA}/photos/7001/i7.jpg")
        self.assertEqual(photo["source_url"], COMMONS)
        self.assertEqual(photo["license"], "domena publiczna")

    def test_skips_published_photos(self):
        Story.objects.create(group_id="7001", title="Alfa", narration="n", text="t", photos=story_payload()["photos"])
        run, _ = self.publish()
        run.assert_not_called()

    def test_reports_photo_without_collector_file(self):
        other = external_photo(source_url="https://commons.wikimedia.org/wiki/File:Inny.jpg")
        Story.objects.create(group_id="7001", title="Alfa", narration="n", text="t", photos=[other])
        run, output = self.publish()
        run.assert_not_called()
        self.assertIn("File:Inny.jpg", output)
        self.assertEqual(Story.objects.get().photos[0]["src"], other["src"])

    def test_dry_run_uploads_nothing(self):
        Story.objects.create(group_id="7001", title="Alfa", narration="n", text="t", photos=[external_photo()])
        run, output = self.publish("--dry-run")
        run.assert_not_called()
        self.assertIn("photos/7001/i7.jpg", output)
        self.assertEqual(Story.objects.get().photos[0]["src"], f"{COMMONS}?raw")

    def test_rejected_stories_are_left_alone(self):
        Story.objects.create(
            group_id="7001", title="Alfa", narration="n", text="t", photos=[external_photo()], status="rejected"
        )
        run, _ = self.publish()
        run.assert_not_called()

    def test_verify_needs_photos_in_media_bucket(self):
        self.agent.put("/api/stories/7001/", story_payload(photos=[external_photo()]), format="json")
        r = self.agent.patch("/api/stories/7001/", {"status": "verified"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("photos", r.json())
        self.publish()
        r = self.agent.patch("/api/stories/7001/", {"status": "verified"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    @override_settings(GCS_MEDIA_BUCKET="")
    def test_verify_without_configured_bucket_keeps_any_src(self):
        self.agent.put("/api/stories/7001/", story_payload(photos=[external_photo()]), format="json")
        r = self.agent.patch("/api/stories/7001/", {"status": "verified"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
