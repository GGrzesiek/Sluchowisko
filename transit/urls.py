from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import LineViewSet
from .export_views import active_lines, snapshot, snapshot_schema

router = DefaultRouter()
router.register("lines", LineViewSet, basename="line")

urlpatterns = [
    path("active-lines/", active_lines, name="active-lines"),
    path("export/snapshot/", snapshot, name="export-snapshot"),
    path("export/snapshot/schema/", snapshot_schema, name="export-snapshot-schema"),
] + router.urls