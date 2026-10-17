from django.contrib import admin

from .models import Story


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ["group_id", "title", "status", "generated_by", "updated_at"]
    list_filter = ["status", "generated_by"]
    list_editable = ["status"]
    search_fields = ["group_id", "title", "narration", "text"]
