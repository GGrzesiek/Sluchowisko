import asyncio
import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from stories.models import Story
from stories.serializers import audio_info
from transit.models import Vehicle
from transit.services import refresh_vehicle
from transit.warsaw_api import WarsawApiError

from .models import Fact, SeenFact
from .ride_progress import NoRouteError, build_ride_info
from .serializers import FactSerializer
from .services import is_stale, upcoming_facts

logger = logging.getLogger(__name__)

CLOSE_UNKNOWN_VEHICLE = 4404


def _location_payload(vehicle, device_id, sent_fact_ids):
    (lat, lon), items = upcoming_facts(vehicle, device_id)
    facts = []
    for fact, distance_m, eta_s in items:
        if fact.id in sent_fact_ids:
            continue
        data = FactSerializer(fact).data
        image_url = data["place"].pop("image_url")
        facts.append(
            {**data, "images": [{"url": image_url}] if image_url else [], "distance_m": distance_m, "eta_s": eta_s}
        )
    return {"estimated_position": {"lat": lat, "lon": lon}, "stale": is_stale(vehicle), "facts": facts}


def _upcoming_group(route):
    stop = next((s for s in route["stops"] if s["state"] == "next"), None)
    return (stop["groupId"], stop["name"]) if stop else None


def _audio_message(group_id, name):
    story = Story.objects.filter(group_id=group_id, status=Story.Status.VERIFIED).first()
    audio = audio_info(story)
    base = {"groupId": group_id, "name": name}
    return {**base, "available": True, **audio} if audio else {**base, "available": False}


def _collect(vehicle_number, device_id, sent_fact_ids):
    city_api_failed = False
    if settings.CITY_API_LIVE:
        try:
            refresh_vehicle(vehicle_number)
        except WarsawApiError:
            city_api_failed = True
    vehicle = Vehicle.objects.filter(number=vehicle_number).first()
    if vehicle is None:
        return {"errors": ["city_api" if city_api_failed else "vehicle_not_found"]}
    if is_stale(vehicle):
        return {"errors": ["no_live_data"]}
    result = {"errors": []}
    try:
        result["route"] = build_ride_info(vehicle)
        result["upcoming"] = _upcoming_group(result["route"])
    except NoRouteError:
        result["errors"].append("no_route")
        result["line"] = vehicle.line
    result["location"] = _location_payload(vehicle, device_id, sent_fact_ids)
    return result


def _mark_seen(device_id, fact_id, vehicle_number):
    fact = Fact.objects.filter(id=fact_id).first()
    if fact is None:
        return False
    SeenFact.objects.get_or_create(device_id=device_id, fact=fact, defaults={"vehicle_number": vehicle_number})
    return True


class RideConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.vehicle_number = self.scope["url_route"]["kwargs"]["vehicle_number"]
        query = parse_qs(self.scope.get("query_string", b"").decode(errors="replace"))
        self.device_id = (query.get("device_id") or [None])[0]
        self.sent_fact_ids = set()
        self.sent_audio_groups = set()
        self.last_route = None
        self.last_errors = set()
        self.push_task = None
        await self.accept()
        self.push_task = asyncio.create_task(self._push_loop())

    async def disconnect(self, code):
        task, self.push_task = getattr(self, "push_task", None), None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("push loop failed during disconnect")

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return
        try:
            message = json.loads(text_data)
            kind = message.get("type") if isinstance(message, dict) else None
            if kind == "ping":
                await self._send("pong", {})
            elif kind == "seen":
                await self._handle_seen(message)
            else:
                await self._send("error", {"code": "unknown_message", "detail": "expected type ping or seen"})
        except json.JSONDecodeError:
            await self._send("error", {"code": "invalid_json", "detail": "message must be JSON"})
        except Exception:
            logger.exception("failed to handle client message")
            await self._send("error", {"code": "internal", "detail": "could not handle message"})

    async def _handle_seen(self, message):
        fact_id = message.get("fact_id")
        if not self.device_id:
            await self._send("error", {"code": "device_id_required", "detail": "connect with ?device_id="})
        elif not isinstance(fact_id, int) or isinstance(fact_id, bool):
            await self._send("error", {"code": "invalid_fact_id", "detail": "fact_id must be an integer"})
        elif not await database_sync_to_async(_mark_seen)(self.device_id, fact_id, self.vehicle_number):
            await self._send("error", {"code": "unknown_fact", "detail": f"no fact {fact_id}"})

    async def _send(self, kind, data):
        try:
            await self.send(text_data=json.dumps({"type": kind, "data": data}, ensure_ascii=False))
        except Exception:
            logger.debug("send failed, client is gone", exc_info=True)

    async def _push_loop(self):
        while True:
            try:
                if not await self._push_once():
                    await self.close(code=CLOSE_UNKNOWN_VEHICLE)
                    return
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("push failed for vehicle %s", self.vehicle_number)
                await self._send("error", {"code": "internal"})
            await asyncio.sleep(settings.WS_PUSH_INTERVAL_SECONDS)

    async def _push_once(self):
        result = await database_sync_to_async(_collect, thread_sensitive=False)(
            self.vehicle_number, self.device_id, self.sent_fact_ids
        )
        for code in result["errors"]:
            if code not in self.last_errors:
                detail = {"code": code}
                if code == "no_route":
                    detail["line"] = result["line"]
                await self._send("error", detail)
        self.last_errors = set(result["errors"])
        if "vehicle_not_found" in result["errors"]:
            return False
        if "route" in result and result["route"] != self.last_route:
            self.last_route = result["route"]
            await self._send("route", result["route"])
        upcoming = result.get("upcoming")
        if upcoming and upcoming[0] not in self.sent_audio_groups:
            self.sent_audio_groups.add(upcoming[0])
            await self._send("audio", await database_sync_to_async(_audio_message)(*upcoming))
        location = result.get("location")
        if location and location["facts"]:
            await self._send("location", location)
            self.sent_fact_ids.update(f["id"] for f in location["facts"])
        return True
