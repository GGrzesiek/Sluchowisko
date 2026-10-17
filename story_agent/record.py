import os

from collector.schema import CollectedStop
from story_agent.models import StoryPlan, StoryScript

GENERATED_BY = "story_agent: Claude (Anthropic) + ElevenLabs"
ALT_LIMIT = 300


def narration_text(script: StoryScript) -> str:
    return "\n".join(line.text for line in script.lines)


def body_text(script: StoryScript) -> str:
    blocks = []
    for section in script.text:
        if section.heading:
            blocks.append(section.heading)
        for paragraph in section.paragraphs:
            blocks.append(" ".join(sentence.text for sentence in paragraph.sentences))
    return "\n\n".join(blocks)


def used_fact_ids(script: StoryScript) -> list[str]:
    ordered = []
    for line in script.lines:
        ordered += line.fact_ids
    for sound in script.sounds:
        ordered += sound.fact_ids
    for section in script.text:
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                ordered += sentence.fact_ids
    return list(dict.fromkeys(ordered))


def source_list(script: StoryScript, plan: StoryPlan, material: CollectedStop) -> list[dict]:
    facts = {f.id: f for f in plan.facts}
    fragments = {f.id: f for f in material.fragments}
    sources = {s.id: s for s in material.sources}
    ordered = []
    for fact_id in used_fact_ids(script):
        for evidence in facts[fact_id].evidence:
            ordered.append(fragments[evidence.fragment_id].source_id)
    result = []
    for source_id in dict.fromkeys(ordered):
        source = sources[source_id]
        label = f"{source.title} — {source.publisher}, {source.license}"
        if source.author:
            label = f"{source.author}, {label}"
        result.append({"label": label[:300], "href": source.url})
    return result


def photos(script: StoryScript, material: CollectedStop, media_base: str) -> list[dict]:
    images = {i.id: i for i in material.images}
    result = []
    for image_id in script.image_ids:
        image = images[image_id]
        src = f"{media_base}/images/{material.stop.group_id}/{image.id}.jpg" if media_base else image.url
        result.append(
            {
                "src": src,
                "alt": image.caption[:ALT_LIMIT],
                "year": image.year or "",
                "caption": image.caption[:500],
                "author": (image.author or "")[:200],
                "license": image.license[:100],
                "license_url": image.license_url or "",
                "source_url": image.url,
            }
        )
    return result


def build_record(
    script: StoryScript,
    plan: StoryPlan,
    material: CollectedStop,
    audio_seconds: float | None,
    media_base: str | None = None,
) -> dict:
    media_base = (media_base if media_base is not None else os.getenv("MEDIA_BASE_URL", "")).rstrip("/")
    audio_url = f"{media_base}/audio/{material.stop.group_id}.mp3" if media_base and audio_seconds else ""
    return {
        "group_id": material.stop.group_id,
        "title": material.stop.name,
        "narration": narration_text(script),
        "text": body_text(script),
        "audio_url": audio_url,
        "audio_seconds": round(audio_seconds) if audio_seconds else None,
        "photos": photos(script, material, media_base),
        "sources": source_list(script, plan, material),
        "status": "draft",
        "generated_by": GENERATED_BY,
    }
