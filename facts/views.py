from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from transit.geo import bbox, haversine_m
from transit.models import Stop, Vehicle
from transit.services import refresh_vehicle
from transit.warsaw_api import WarsawApiError

from .models import Fact, SeenFact
from .serializers import FactSerializer, StopSerializer, VehicleSerializer
from .services import is_stale, upcoming_facts


def _device_id(request):
    # The frontend generates a random UUID once and sends it with every request
    return request.headers.get("X-Device-Id") or request.query_params.get("device_id")


@api_view(["GET"])
def ride(request, vehicle_number):
    """Main endpoint: the QR code opens /ride/<vehicle_number>, the app polls this every ~10 s."""
    v = get_object_or_404(Vehicle, number=vehicle_number)
    (lat, lon), items = upcoming_facts(v, _device_id(request), limit=int(request.query_params.get("limit", 5)))
    return Response(
        {
            "vehicle": VehicleSerializer(v).data,
            "stale": is_stale(v),
            "estimated_position": {"lat": lat, "lon": lon},
            "facts": [{**FactSerializer(f).data, "distance_m": d, "eta_s": eta} for f, d, eta in items],
        }
    )


@api_view(["POST"])
def mark_seen(request, fact_id):
    device = _device_id(request)
    if not device:
        return Response({"detail": "X-Device-Id header required"}, status=status.HTTP_400_BAD_REQUEST)
    fact = get_object_or_404(Fact, id=fact_id)
    SeenFact.objects.get_or_create(
        device_id=device, fact=fact, defaults={"vehicle_number": request.data.get("vehicle_number", "")}
    )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def vehicles(request):
    """Live vehicles, optionally filtered by ?line=17. Useful for a map view / debugging."""
    qs = Vehicle.objects.all()
    if line := request.query_params.get("line"):
        qs = qs.filter(line=line)
    return Response(VehicleSerializer(qs, many=True).data)


@api_view(["GET"])
def nearby_stops(request):
    """?lat=&lon=&radius=  -> stops sorted by distance."""
    try:
        lat, lon = float(request.query_params["lat"]), float(request.query_params["lon"])
    except (KeyError, ValueError):
        return Response({"detail": "lat and lon required"}, status=status.HTTP_400_BAD_REQUEST)
    radius = int(request.query_params.get("radius", 500))
    a, b, c, d = bbox(lat, lon, radius)
    stops = [
        (s, haversine_m(lat, lon, s.lat, s.lon)) for s in Stop.objects.filter(lat__range=(a, b), lon__range=(c, d))
    ]
    stops = sorted([x for x in stops if x[1] <= radius], key=lambda x: x[1])
    return Response([{**StopSerializer(s).data, "distance_m": round(dist)} for s, dist in stops])


@api_view(["GET"])
def ride_stops(request, vehicle_number):
    from .ride_progress import NoRouteError, build_ride_info

    city_api_failed = False
    if settings.CITY_API_LIVE:
        try:
            refresh_vehicle(vehicle_number)
        except WarsawApiError:
            city_api_failed = True
    vehicle = Vehicle.objects.filter(number=vehicle_number).first()
    if vehicle is None:
        if city_api_failed:
            return Response({"code": "city_api"}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"code": "vehicle_not_found"}, status=status.HTTP_404_NOT_FOUND)
    if is_stale(vehicle):
        return Response({"code": "no_live_data"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    try:
        return Response(build_ride_info(vehicle))
    except NoRouteError:
        return Response({"code": "no_route"}, status=status.HTTP_404_NOT_FOUND)
