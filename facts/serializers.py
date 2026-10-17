from rest_framework import serializers

from transit.models import Stop, Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ["number", "line", "brigade", "lat", "lon", "heading", "speed_mps", "reported_at"]


class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = ["zespol", "slupek", "name", "lat", "lon", "direction"]
