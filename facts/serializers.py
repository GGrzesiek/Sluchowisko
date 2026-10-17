from rest_framework import serializers

from transit.models import Stop, Vehicle

from .models import Fact, Place


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ["id", "name", "lat", "lon", "category", "image_url"]


class FactSerializer(serializers.ModelSerializer):
    place = PlaceSerializer()

    class Meta:
        model = Fact
        fields = ["id", "title", "text", "language", "source_url", "priority", "place"]


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ["number", "line", "brigade", "lat", "lon", "heading", "speed_mps", "reported_at"]


class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = ["zespol", "slupek", "name", "lat", "lon", "direction"]
