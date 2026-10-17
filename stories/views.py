from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from transit.models import Line, Route

from .models import Story
from .permissions import WriteTokenOrReadOnly
from .serializers import StorySerializer, story_content


def _upsert(data, group_id=None):
    if group_id is not None:
        data = {**data, "group_id": group_id}
    instance = Story.objects.filter(group_id=data.get("group_id")).first()
    serializer = StorySerializer(instance, data=data)
    return instance is None, serializer


@api_view(["GET", "POST"])
@permission_classes([WriteTokenOrReadOnly])
def story_list(request):
    if request.method == "GET":
        qs = Story.objects.all()
        if wanted := request.query_params.get("status"):
            qs = qs.filter(status=wanted)
        return Response(
            [{"groupId": s.group_id, "title": s.title, "status": s.status, "updatedAt": s.updated_at} for s in qs]
        )

    items = request.data if isinstance(request.data, list) else [request.data]
    checked = [_upsert(item) for item in items]
    errors = {str(i): s.errors for i, (_, s) in enumerate(checked) if not s.is_valid()}
    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
    created, updated = [], []
    with transaction.atomic():
        for is_new, serializer in checked:
            story = serializer.save()
            (created if is_new else updated).append(story.group_id)
    return Response({"created": created, "updated": updated})


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([WriteTokenOrReadOnly])
def story_detail(request, group_id):
    if request.method == "GET":
        qs = Story.objects.all()
        if request.query_params.get("draft") != "1":
            qs = qs.filter(status=Story.Status.VERIFIED)
        return Response(story_content(get_object_or_404(qs, group_id=group_id)))

    if request.method == "PATCH":
        story = get_object_or_404(Story, group_id=group_id)
        serializer = StorySerializer(story, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StorySerializer(story).data)

    is_new, serializer = _upsert(request.data, group_id)
    serializer.is_valid(raise_exception=True)
    story = serializer.save()
    return Response(StorySerializer(story).data, status=status.HTTP_201_CREATED if is_new else status.HTTP_200_OK)


@api_view(["GET"])
def line_stories(request, number):
    line = get_object_or_404(Line, number=number)
    routes = Route.objects.filter(line=line).order_by("code")
    if request.query_params.get("all_routes") != "1":
        routes = routes.filter(code__startswith="TP")
    groups = {}
    for route in routes:
        for rs in route.stops.select_related("stop").order_by("order"):
            if rs.stop and rs.stop.zespol not in groups:
                groups[rs.stop.zespol] = rs.stop
    stories = {s.group_id: s for s in Story.objects.filter(group_id__in=groups)}
    return Response(
        {
            "line": line.number,
            "stopGroups": [
                {
                    "groupId": group_id,
                    "name": stop.name,
                    "lat": stop.lat,
                    "lon": stop.lon,
                    "storyStatus": stories[group_id].status if group_id in stories else None,
                }
                for group_id, stop in groups.items()
            ],
        }
    )
