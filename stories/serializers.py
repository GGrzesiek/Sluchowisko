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
    author = serializers.CharField(max_length=200)
    license = serializers.CharField(max_length=100)
    license_url = serializers.URLField(max_length=500, required=False, allow_blank=True, default="")
    source_url = serializers.URLField(max_length=500)


class SourceSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=300)
    href = serializers.URLField(max_length=500)


class SourceRefsField(serializers.ListField):
    child = serializers.IntegerField(min_value=1)


class ParagraphBlockSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["paragraph"])
    text = serializers.CharField()
    sources = SourceRefsField(required=False)


class ImageBlockSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["image"])
    photo = serializers.IntegerField(min_value=0)


class TimelineItemSerializer(serializers.Serializer):
    year = serializers.RegexField(r"^\d{4}$")
    text = serializers.CharField()
    sources = SourceRefsField(required=False)


class TimelineBlockSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["timeline"])
    items = TimelineItemSerializer(many=True, allow_empty=False)


BLOCK_SERIALIZERS = {
    "paragraph": ParagraphBlockSerializer,
    "image": ImageBlockSerializer,
    "timeline": TimelineBlockSerializer,
}


def _plain_text(blocks):
    parts = []
    for block in blocks:
        if block["type"] == "paragraph":
            parts.append(block["text"])
        elif block["type"] == "timeline":
            parts.append("\n".join(f"{item['year']}: {item['text']}" for item in block["items"]))
    return "\n\n".join(parts)


class StorySerializer(serializers.ModelSerializer):
    group_id = serializers.RegexField(r"^\d+$", max_length=10)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    photos = PhotoSerializer(many=True, min_length=1, max_length=MAX_PHOTOS)
    sources = SourceSerializer(many=True, allow_empty=False)
    text = serializers.CharField(required=False, allow_blank=True)
    blocks = serializers.JSONField(required=False)

    class Meta:
        model = Story
        fields = [
            "group_id",
            "title",
            "narration",
            "text",
            "blocks",
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

    def validate_blocks(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("blocks must be a list.")
        cleaned, errors = [], {}
        for index, block in enumerate(value):
            serializer_class = BLOCK_SERIALIZERS.get(block.get("type") if isinstance(block, dict) else None)
            if serializer_class is None:
                errors[index] = {"type": f"must be one of {', '.join(BLOCK_SERIALIZERS)}."}
                continue
            serializer = serializer_class(data=block)
            if serializer.is_valid():
                cleaned.append(serializer.data)
            else:
                errors[index] = serializer.errors
        if errors:
            raise serializers.ValidationError(errors)
        return cleaned

    def _check_block_references(self, blocks, photos, sources):
        for index, block in enumerate(blocks):
            if block["type"] == "image" and block["photo"] >= len(photos):
                raise serializers.ValidationError({"blocks": {index: f"photo {block['photo']} does not exist."}})
            refs = list(block.get("sources", []))
            for item in block.get("items", []):
                refs += item.get("sources", [])
            if any(ref > len(sources) for ref in refs):
                raise serializers.ValidationError(
                    {"blocks": {index: "sources refers to a source that does not exist."}}
                )

    def validate(self, attrs):
        group_id = attrs.get("group_id") or (self.instance and self.instance.group_id)
        if not attrs.get("title") and not (self.instance and self.instance.title):
            stop = Stop.objects.filter(zespol=group_id).order_by("slupek").first()
            attrs["title"] = stop.name if stop else group_id
        for key in ("photos", "sources"):
            if key in attrs:
                attrs[key] = [dict(item) for item in attrs[key]]
        blocks = attrs.get("blocks", self.instance.blocks if self.instance else [])
        photos = attrs.get("photos", self.instance.photos if self.instance else [])
        sources = attrs.get("sources", self.instance.sources if self.instance else [])
        self._check_block_references(blocks, photos, sources)
        if blocks and not attrs.get("text") and not (self.instance and self.instance.text and "blocks" not in attrs):
            attrs["text"] = _plain_text(blocks)
        if not blocks and not attrs.get("text") and not (self.instance and self.instance.text):
            raise serializers.ValidationError({"text": "Provide text or blocks."})
        status = attrs.get("status") or (self.instance and self.instance.status)
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


def story_photos(story):
    return [
        {
            "src": p["src"],
            "alt": p["alt"],
            "year": p.get("year", ""),
            "caption": p["caption"],
            "credit": photo_credit(p),
        }
        for p in story.photos
    ]


def story_content(story):
    return {
        "groupId": story.group_id,
        "title": story.title,
        "status": story.status,
        "narration": story.narration,
        "photos": story_photos(story),
        "body": {"format": "plain", "text": story.text},
        "blocks": story.blocks,
        "sources": story.sources,
        **_story_audio(story),
    }


def story_location(story):
    return {
        "groupId": story.group_id,
        "title": story.title,
        "photos": story_photos(story),
        "body": {"format": "plain", "text": story.text},
        "blocks": story.blocks,
        "sources": story.sources,
    }


def _story_audio(story):
    audio = audio_info(story)
    if audio is None:
        return {}
    return {"audio": audio["src"], "audioSeconds": audio["seconds"], "aiVoice": True}
