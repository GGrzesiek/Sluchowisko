from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("stories.urls")),
    path("api/", include("transit.urls")),
    path("api/", include("facts.urls")),
]
