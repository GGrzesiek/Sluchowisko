from django.core.cache import cache
from django.db.models import Count, Prefetch
from django.db.models.functions import Length
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import warsaw_api
from .llm_context import build_line_context
from .models import Line, Route, RouteStop

LIVE_CACHE_SECONDS = 10  # the city refreshes positions every ~10 s, no point asking more often


# ---------- serializers ----------

class RouteStopSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="stop.name", default=None)
    lat = serializers.FloatField(source="stop.lat", default=None)
    lon = serializers.FloatField(source="stop.lon", default=None)

    class Meta:
        model = RouteStop
        fields = ["order", "zespol", "slupek", "name", "lat", "lon", "stop_type", "distance_m"]


class RouteSerializer(serializers.ModelSerializer):
    is_main = serializers.BooleanField(read_only=True)

    class Meta:
        model = Route
        fields = ["code", "first_stop_name", "last_stop_name", "stop_count", "is_main"]


class RouteDetailSerializer(RouteSerializer):
    stops = RouteStopSerializer(many=True)

    class Meta(RouteSerializer.Meta):
        fields = RouteSerializer.Meta.fields + ["stops"]


class LineSerializer(serializers.ModelSerializer):
    route_count = serializers.IntegerField(read_only=True)
    directions = serializers.SerializerMethodField()

    class Meta:
        model = Line
        fields = ["number", "kind", "route_count", "directions", "synced_at"]

    def get_directions(self, line):
        # Terminus names of the main routes, e.g. ["Tarchomin Kościelny", "Woronicza"]
        return sorted({r.last_stop_name for r in line.routes.all() if r.is_main and r.last_stop_name})


class LineDetailSerializer(LineSerializer):
    routes = RouteSerializer(many=True)

    class Meta(LineSerializer.Meta):
        fields = LineSerializer.Meta.fields + ["routes"]


# ---------- views ----------

class LineViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/lines/                         all lines (paginated) ?kind=tram|bus|night|...  ?search=1
    GET /api/lines/17/                      one line with its route variants
    GET /api/lines/17/routes/TP-TAR/        ordered stops with coordinates
    GET /api/lines/17/routes/TP-TAR/geojson/  same as GeoJSON (for Leaflet / Mapbox)
    GET /api/lines/17/vehicles/             live positions straight from the city API
    GET /api/lines/17/llm-context/          compact JSON to give an LLM (?route=CODE &bare=1 &corridor=400)
    POST /api/lines/17/validate-places/     check LLM output (JSON array) against the route, nothing is saved
    """

    lookup_field = "number"
    lookup_value_regex = "[^/]+"

    def get_queryset(self):
        qs = (Line.objects.annotate(route_count=Count("routes")).prefetch_related("routes")
              .order_by("kind", Length("number"), "number"))  # 4, 17, 105 (not 105, 17, 4)
        if kind := self.request.query_params.get("kind"):
            qs = qs.filter(kind=kind)
        if search := self.request.query_params.get("search"):
            qs = qs.filter(number__istartswith=search)
        return qs

    def get_serializer_class(self):
        return LineDetailSerializer if self.action == "retrieve" else LineSerializer

    def _route(self, number, code):
        return get_object_or_404(
            Route.objects.prefetch_related(Prefetch("stops", RouteStop.objects.select_related("stop"))),
            line_id=number, code=code,
        )

    @action(detail=True, url_path=r"routes/(?P<code>[^/]+)")
    def route(self, request, number=None, code=None):
        return Response(RouteDetailSerializer(self._route(number, code)).data)

    @action(detail=True, url_path=r"routes/(?P<code>[^/]+)/geojson")
    def route_geojson(self, request, number=None, code=None):
        route = self._route(number, code)
        pts = [rs for rs in route.stops.all() if rs.stop]
        features = [{
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[p.stop.lon, p.stop.lat] for p in pts]},
            "properties": {"line": number, "route": code, "direction": route.last_stop_name},
        }] + [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [p.stop.lon, p.stop.lat]},
            "properties": {"order": p.order, "name": p.stop.name, "zespol": p.zespol, "slupek": p.slupek},
        } for p in pts]
        return Response({"type": "FeatureCollection", "features": features})

    @action(detail=True)
    def vehicles(self, request, number=None):
        line = get_object_or_404(Line, number=number)
        key = f"live:{line.number}"
        data = cache.get(key)
        if data is None:
            try:
                readings = warsaw_api.fetch_vehicle_positions(line=line.number, vehicle_type=line.vehicle_type)
            except warsaw_api.WarsawApiError as e:
                return Response({"detail": f"City API unavailable: {e}"}, status=status.HTTP_502_BAD_GATEWAY)
            data = [{"vehicle_number": r.vehicle_number, "brigade": r.brigade, "lat": r.lat,
                     "lon": r.lon, "time": r.time.isoformat()} for r in readings]
            cache.set(key, data, LIVE_CACHE_SECONDS)
        return Response({"line": line.number, "count": len(data), "vehicles": data})

    @action(detail=True, url_path="llm-context")
    def llm_context(self, request, number=None):
        line = get_object_or_404(Line, number=number)
        corridor = request.query_params.get("corridor")
        ctx = build_line_context(line, route_code=request.query_params.get("route"),
                                 include_task=request.query_params.get("bare") != "1",
                                 corridor_m=int(corridor) if corridor and corridor.isdigit() else None)
        if ctx is None:
            return Response({"detail": "No route for this line, run sync_city_data"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ctx)

    @action(detail=True, methods=["post"], url_path="validate-places")
    def validate_places(self, request, number=None):
        from facts.validation import validate_places  # avoid an import cycle at module load

        line = get_object_or_404(Line, number=number)
        ctx = build_line_context(line, route_code=request.query_params.get("route"), include_task=False)
        report = validate_places(request.data, ctx["stops"] if ctx else None,
                                 corridor_m=ctx["corridor_m"] if ctx else 400)
        return Response({"valid_count": len(report["valid"]), **report})
