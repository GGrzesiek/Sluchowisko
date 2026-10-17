import io
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from transit.models import Line, Route, RouteStop, Stop, Vehicle

from .audio import UploadError, upload_public
from .models import Story
from .serializers import story_content

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
                "source_url": "https://commons.wikimedia.org/wiki/File:A.jpg",
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
            story_payload(photos=[{**story_payload()["photos"][0], "author": ""}]),
            story_payload(photos=[{**story_payload()["photos"][0], "source_url": ""}]),
            story_payload(status="published"),
        ]
        for payload in cases:
            self.assertEqual(self.agent.put("/api/stories/7001/", payload, format="json").status_code, 400)

    def test_blocks_are_stored_and_a_plain_text_is_derived(self):
        blocks = [
            {"type": "paragraph", "text": "Tu stała brama.", "sources": [1]},
            {"type": "image", "photo": 0},
            {
                "type": "timeline",
                "items": [{"year": "1790", "text": "Założenie cmentarza"}, {"year": "1944", "text": "Powstanie"}],
            },
        ]
        payload = story_payload(blocks=blocks, status="verified")
        del payload["text"]
        r = self.agent.put("/api/stories/7001/", payload, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        body = self.client.get("/api/stories/7001/").json()
        self.assertEqual([b["type"] for b in body["blocks"]], ["paragraph", "image", "timeline"])
        self.assertEqual(body["body"]["text"], "Tu stała brama.\n\n1790: Założenie cmentarza\n1944: Powstanie")

    def test_story_without_blocks_has_an_empty_list(self):
        self.agent.put("/api/stories/7001/", story_payload(status="verified"), format="json")
        self.assertEqual(self.client.get("/api/stories/7001/").json()["blocks"], [])

    def test_invalid_blocks_are_rejected(self):
        bad = [
            [{"type": "video", "src": "x"}],
            [{"type": "paragraph"}],
            [{"type": "paragraph", "text": "x", "sources": [2]}],
            [{"type": "image", "photo": 1}],
            [{"type": "timeline", "items": []}],
            [{"type": "timeline", "items": [{"year": "około 1790", "text": "x"}]}],
            "not a list",
            ["paragraph"],
        ]
        for blocks in bad:
            r = self.agent.put("/api/stories/7001/", story_payload(blocks=blocks), format="json")
            self.assertEqual(r.status_code, 400, blocks)

    def test_text_or_blocks_is_required(self):
        payload = story_payload()
        del payload["text"]
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
        self.assertNotIn("audio", body)

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


def write_wav(path, seconds, rate=8000):
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))


URL = "https://storage.googleapis.com/muzeum-w-autobusie-2026-media/audio/"


@patch("stories.management.commands.sync_audio.upload_public")
class SyncAudioTest(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.source = Path(tmp.name) / "bucket"
        base = {"narration": "n", "text": "t", "photos": [], "sources": []}
        for group_id, status in (("7001", "verified"), ("7002", "verified"), ("7003", "draft"), ("7004", "verified")):
            Story.objects.create(group_id=group_id, title=group_id, status=status, **base)
        write_wav(self.source / "line22" / "7001.wav", 2.6)
        write_wav(self.source / "7003.wav", 1)
        (self.source / "7004.mp3").write_bytes(b"not audio")
        write_wav(self.source / "notes.wav", 1)

    def sync(self, *extra):
        out = StringIO()
        call_command("sync_audio", "--source", str(self.source), *extra, stdout=out)
        return out.getvalue()

    def test_uploads_verified_recordings_and_sets_public_url(self, upload):
        report = self.sync()
        upload.assert_called_once_with(self.source / "line22" / "7001.wav", "audio/7001.wav")
        story = Story.objects.get(group_id="7001")
        self.assertEqual((story.audio_url, story.audio_seconds), (URL + "7001.wav", 3))
        self.assertIn("No recording: 7002", report)
        self.assertIn("Unreadable recording: 7004", report)

    def test_missing_recording_clears_old_audio(self, upload):
        Story.objects.filter(group_id="7002").update(audio_url=URL + "7002.mp3", audio_seconds=9)
        self.sync()
        story = Story.objects.get(group_id="7002")
        self.assertEqual((story.audio_url, story.audio_seconds), ("", None))

    def test_drafts_are_not_uploaded(self, upload):
        self.sync()
        self.assertNotIn("audio/7003.wav", [c.args[1] for c in upload.call_args_list])
        self.assertEqual(Story.objects.get(group_id="7003").audio_url, "")

    def test_dry_run_changes_nothing(self, upload):
        report = self.sync("--dry-run")
        upload.assert_not_called()
        self.assertEqual(Story.objects.get(group_id="7001").audio_url, "")
        self.assertIn("Would upload 1", report)

    def test_failed_upload_leaves_story_without_audio(self, upload):
        upload.side_effect = UploadError("bucket down")
        with self.assertRaises(CommandError):
            self.sync()
        self.assertEqual(Story.objects.get(group_id="7001").audio_url, "")

    def test_draft_and_new_narration_clear_audio(self, upload):
        self.sync()
        story = Story.objects.get(group_id="7001")
        story.status = Story.Status.DRAFT
        story.save()
        self.assertEqual(Story.objects.get(group_id="7001").audio_url, "")

        Story.objects.filter(group_id="7001").update(status="verified")
        self.sync()
        Stop.objects.create(zespol="7001", slupek="01", name="Alfa", lat=52.2, lon=21.0)
        agent = APIClient(HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
        with override_settings(STORIES_WRITE_TOKEN=TOKEN):
            agent.patch("/api/stories/7001/", {"text": "new text"}, format="json")
            self.assertEqual(Story.objects.get(group_id="7001").audio_url, URL + "7001.wav")
            r = agent.patch("/api/stories/7001/", {"narration": "new"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Story.objects.get(group_id="7001").audio_url, "")

    def test_agent_cannot_overwrite_audio(self, upload):
        self.sync()
        Stop.objects.create(zespol="7001", slupek="01", name="Alfa", lat=52.2, lon=21.0)
        agent = APIClient(HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
        payload = story_payload("7001", narration="n", audio_url="x", audio_seconds=1, status="verified")
        with override_settings(STORIES_WRITE_TOKEN=TOKEN):
            r = agent.put("/api/stories/7001/", payload, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Story.objects.get(group_id="7001").audio_url, URL + "7001.wav")

    def test_story_content_audio_matches_frontend_type(self, upload):
        self.sync()
        content = story_content(Story.objects.get(group_id="7001"))
        self.assertEqual((content["audio"], content["audioSeconds"], content["aiVoice"]), (URL + "7001.wav", 3, True))
        self.assertNotIn("audio", story_content(Story.objects.get(group_id="7002")))


class UploadPublicTest(TestCase):
    @patch("stories.audio.subprocess.run")
    @patch("stories.audio.shutil.which", return_value="/usr/bin/gcloud")
    def test_uploads_with_content_type_and_returns_public_url(self, which, run):
        run.return_value.returncode = 0
        url = upload_public(Path("/tmp/5087.mp3"), "audio/5087.mp3")
        self.assertEqual(url, "https://storage.googleapis.com/muzeum-w-autobusie-2026-media/audio/5087.mp3")
        self.assertEqual(
            run.call_args.args[0],
            [
                "/usr/bin/gcloud",
                "storage",
                "cp",
                "--content-type=audio/mpeg",
                "--cache-control=no-cache",
                "/tmp/5087.mp3",
                "gs://muzeum-w-autobusie-2026-media/audio/5087.mp3",
            ],
        )

    @patch("stories.audio.subprocess.run")
    @patch("stories.audio.shutil.which", return_value="/usr/bin/gcloud")
    def test_failed_upload_raises(self, which, run):
        run.return_value.returncode = 1
        with self.assertRaises(UploadError):
            upload_public(Path("/tmp/5087.mp3"), "audio/5087.mp3")

    @patch("stories.audio.shutil.which", return_value=None)
    def test_missing_gcloud_raises(self, which):
        with self.assertRaises(UploadError):
            upload_public(Path("/tmp/5087.mp3"), "audio/5087.mp3")
