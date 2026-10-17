from django.urls import path

from .consumers import RideConsumer

websocket_urlpatterns = [
    path("ws/ride/<str:vehicle_number>/", RideConsumer.as_asgi()),
]
