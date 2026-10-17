from django.contrib import admin

from .models import Line, PositionLog, Route, Stop, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["number", "line", "brigade", "lat", "lon", "heading", "speed_mps", "reported_at"]
    list_filter = ["line"]


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ["name", "zespol", "slupek", "lat", "lon"]
    search_fields = ["name", "zespol"]


admin.site.register(PositionLog)




class RouteInline(admin.TabularInline):
    model = Route
    extra = 0
    fields = ["code", "first_stop_name", "last_stop_name", "stop_count"]
    readonly_fields = fields


@admin.register(Line)
class LineAdmin(admin.ModelAdmin):
    list_display = ["number", "kind", "synced_at"]
    list_filter = ["kind"]
    search_fields = ["number"]
    inlines = [RouteInline]


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ["line", "code", "first_stop_name", "last_stop_name", "stop_count"]
    list_filter = ["line__kind"]
    search_fields = ["line__number", "code", "last_stop_name"]
