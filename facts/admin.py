from django.contrib import admin

from .models import Fact, Place, SeenFact


class FactInline(admin.TabularInline):
    model = Fact
    extra = 0
    fields = ["title", "approved", "priority", "source_url"]


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "lat", "lon"]
    search_fields = ["name"]
    inlines = [FactInline]


@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ["title", "place", "approved", "priority", "generated_by"]
    list_filter = ["approved", "language", "generated_by"]
    list_editable = ["approved", "priority"]  # quick human review of AI-generated facts
    search_fields = ["title", "text"]


admin.site.register(SeenFact)
