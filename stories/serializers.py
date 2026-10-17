from rest_framework import serializers

from transit.models import Stop

from .models import Story

MAX_PHOTOS = 5


class PhotoSerializer(serializers.Serializer):
    src = serializers.URLField(max_length=500)
    alt = serializers.CharField(max_length=300)
    year = serializers.RegexField(r"^\d{4}$", required=False, allow_blank=True, default="")
    caption = serializers.CharField(max_length=500)
    author = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    license = serializers.CharField(max_length=100)
    license_url = serializers.URLField(max_length=500, required=False, allow_blank=True, default="")
    source_url = serializers.URLField(max_length=500, required=False, allow_blank=True, default="")


class SourceSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=300)
    href = serializers.URLField(max_length=500)


class StorySerializer(serializers.ModelSerializer):
    group_id = serializers.RegexField(r"^\d+$", max_length=10)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    photos = PhotoSerializer(many=True, min_length=1, max_length=MAX_PHOTOS)
    sources = SourceSerializer(many=True, allow_empty=False)

    class Meta:
        model = Story
        fields = [
            "group_id",
            "title",
            "narration",
            "text",
            "audio_url",
            "audio_seconds",
            "photos",
            "sources",
            "status",
            "generated_by",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def validate_group_id(self, value):
        if not Stop.objects.filter(zespol=value).exists():
            raise serializers.ValidationError(f"Unknown stop group {value}. Run sync_city_data first.")
        if self.instance and self.instance.group_id != value:
            raise serializers.ValidationError("group_id cannot change.")
        return value

    def validate(self, attrs):
        group_id = attrs.get("group_id") or (self.instance and self.instance.group_id)
        if not attrs.get("title") and not (self.instance and self.instance.title):
            stop = Stop.objects.filter(zespol=group_id).order_by("slupek").first()
            attrs["title"] = stop.name if stop else group_id
        for key in ("photos", "sources"):
            if key in attrs:
                attrs[key] = [dict(item) for item in attrs[key]]
        return attrs


def photo_credit(photo):
    author = photo.get("author") or "NN"
    return f"Fot. {author} · {photo['license']}"


def story_content(story):
    return {
        "groupId": story.group_id,
        "title": story.title,
        "status": story.status,
        "narration": story.narration,
        "audio": {"src": story.audio_url, "seconds": story.audio_seconds} if story.audio_url else None,
        "photos": [
            {
                "src": p["src"],
                "alt": p["alt"],
                "year": p.get("year", ""),
                "caption": p["caption"],
                "credit": photo_credit(p),
            }
            for p in story.photos
        ],
        "body": {"format": "plain", "text": story.text},
        "sources": story.sources,
    }
