import hmac

from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission


def has_write_token(request) -> bool:
    expected = settings.STORIES_WRITE_TOKEN
    given = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


class WriteTokenOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or has_write_token(request)
