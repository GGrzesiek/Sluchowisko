from django.db import models


class Stop(models.Model):
    """A stop post ("słupek"). zespol = stop group id, slupek = post number within it."""

    zespol = models.CharField(max_length=10)
    slupek = models.CharField(max_length=5)
    name = models.CharField(max_length=200)
    lat = models.FloatField()
    lon = models.FloatField()
    direction = models.CharField(max_length=200, blank=True)
    lines_checked_at = models.DateTimeField(null=True, blank=True)  # last "lines at stop" crawl

    class Meta:
        unique_together = ("zespol", "slupek")
        indexes = [models.Index(fields=["lat", "lon"])]

    def __str__(self):
        return f"{self.name} {self.slupek}"


class Vehicle(models.Model):
    """Latest known state of a vehicle. The QR code in the vehicle encodes `number`."""

    number = models.CharField(max_length=20, primary_key=True)  # side number, e.g. "3201"
    line = models.CharField(max_length=10, db_index=True)
    brigade = models.CharField(max_length=10, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()
    reported_at = models.DateTimeField()  # time from the API
    # previous point, used to compute heading/speed between two readings
    prev_lat = models.FloatField(null=True, blank=True)
    prev_lon = models.FloatField(null=True, blank=True)
    prev_reported_at = models.DateTimeField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)  # degrees, 0 = north
    speed_mps = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.number} (line {self.line})"


class PositionLog(models.Model):
    """Raw history, handy for replaying a ride in the demo and for congestion analysis."""

    vehicle_number = models.CharField(max_length=20, db_index=True)
    line = models.CharField(max_length=10)
    lat = models.FloatField()
    lon = models.FloatField()
    reported_at = models.DateTimeField(db_index=True)

    class Meta:
        unique_together = ("vehicle_number", "reported_at")


class Line(models.Model):
    TRAM, BUS, NIGHT, SUBURBAN, EXPRESS, REPLACEMENT, OTHER = (
        "tram", "bus", "night", "suburban", "express", "replacement", "other")
    KIND_CHOICES = [(k, k) for k in (TRAM, BUS, NIGHT, SUBURBAN, EXPRESS, REPLACEMENT, OTHER)]

    number = models.CharField(max_length=10, primary_key=True)  # "17", "180", "N37", "L-1"...
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, db_index=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "number"]

    def __str__(self):
        return self.number

    @property
    def vehicle_type(self) -> int:
        """Value for busestrams_get `type`: 2 = tram, 1 = everything else."""
        return 2 if self.kind == self.TRAM else 1


class Route(models.Model):
    """One variant of a line, e.g. "TP-TAR" (main route towards Tarchomin)."""

    line = models.ForeignKey(Line, on_delete=models.CASCADE, related_name="routes")
    code = models.CharField(max_length=20)
    first_stop_name = models.CharField(max_length=200, blank=True)
    last_stop_name = models.CharField(max_length=200, blank=True)  # = direction shown to riders
    stop_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("line", "code")
        ordering = ["line", "code"]

    def __str__(self):
        return f"{self.line_id} {self.code} → {self.last_stop_name}"

    @property
    def is_main(self) -> bool:
        # ZTM convention: route codes starting with "TP" are the main variants
        return self.code.upper().startswith("TP")


class RouteStop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="stops")
    order = models.PositiveIntegerField()
    zespol = models.CharField(max_length=10)
    slupek = models.CharField(max_length=5)
    stop = models.ForeignKey(Stop, null=True, blank=True, on_delete=models.SET_NULL)
    street_id = models.CharField(max_length=20, blank=True)
    stop_type = models.CharField(max_length=5, blank=True)  # "typ" from the API (e.g. on-request stop)
    distance_m = models.IntegerField(null=True, blank=True)  # "odleglosc" from the API

    class Meta:
        ordering = ["route", "order"]
        unique_together = ("route", "order")
        indexes = [models.Index(fields=["zespol", "slupek"])]

class StopLine(models.Model):
    """Which line stops at which stop post (from "Linie dostępne na przystanku")."""

    stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name="stop_lines")
    line = models.CharField(max_length=10, db_index=True)

    class Meta:
        unique_together = ("stop", "line")