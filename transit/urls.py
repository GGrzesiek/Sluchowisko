from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import LineViewSet
from .export_views import active_lines, snapshot, snapshot_schema
from .health import health

router = DefaultRouter()
router.register("lines", LineViewSet, basename="line")

urlpatterns = [
    path("health/", health, name="health"),
    path("active-lines/", active_lines, name="active-lines"),
    path("export/snapshot/", snapshot, name="export-snapshot"),
    path("export/snapshot/schema/", snapshot_schema, name="export-snapshot-schema"),
] + router.urls
