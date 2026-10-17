from rest_framework import serializers

from transit.models import Stop

from . import media
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
        read_only_fields = ["audio_url", "audio_seconds", "updated_at"]

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
        status = attrs.get("status") or (self.instance and self.instance.status)
        photos = attrs.get("photos", self.instance.photos if self.instance else [])
        outside = [p["src"] for p in photos if not media.is_media_url(p["src"])]
        if status == Story.Status.VERIFIED and media.base_url() and outside:
            raise serializers.ValidationError(
                {"photos": [f"Run publish_photos before verifying; not in the media bucket: {', '.join(outside)}"]}
            )
        return attrs

    def update(self, instance, validated_data):
        if "narration" in validated_data and validated_data["narration"] != instance.narration:
            validated_data["audio_url"], validated_data["audio_seconds"] = "", None
        return super().update(instance, validated_data)


def photo_credit(photo):
    author = photo.get("author") or "NN"
    return f"Fot. {author} · {photo['license']}"


def audio_info(story):
    if story is None or not story.audio_url:
        return None
    return {"src": story.audio_url, "seconds": story.audio_seconds, "aiVoice": True}


def story_content(story):
    return {
        "groupId": story.group_id,
        "title": story.title,
        "status": story.status,
        "narration": story.narration,
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
        **_story_audio(story),
    }


def _story_audio(story):
    audio = audio_info(story)
    if audio is None:
        return {}
    return {"audio": audio["src"], "audioSeconds": audio["seconds"], "aiVoice": True}
