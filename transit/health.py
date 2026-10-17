from django.conf import settings
from django.db import DatabaseError, connection
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services import city_positions
from .warsaw_api import WarsawApiError


def _database_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except DatabaseError:
        return False


def _city_api_ok() -> bool:
    try:
        return bool(city_positions())
    except WarsawApiError:
        return False


@api_view(["GET"])
def health(request):
    checks = {"db": _database_ok()}
    if settings.CITY_API_LIVE:
        checks["city_api"] = _city_api_ok()
    return Response(checks, status=200 if all(checks.values()) else 503)
