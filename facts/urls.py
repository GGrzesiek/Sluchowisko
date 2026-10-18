from django.urls import path

from . import views

urlpatterns = [
    path("ride/<str:vehicle_number>/stops/", views.ride_stops, name="ride-stops"),
    path("vehicles/", views.vehicles, name="vehicles"),
    path("debug/day/", views.debug_vehicles, {"period": "day"}, name="debug-day"),
    path("debug/night/", views.debug_vehicles, {"period": "night"}, name="debug-night"),
    path("stops/nearby/", views.nearby_stops, name="nearby-stops"),
]
