from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from collector.schema import FragmentId, ImageId, ObjectId

FactId = Annotated[str, StringConstraints(pattern=r"^F\d+$")]
LineId = Annotated[str, StringConstraints(pattern=r"^L\d+$")]
SoundId = Annotated[str, StringConstraints(pattern=r"^S\d+$")]
Text = Annotated[str, StringConstraints(min_length=1)]

FactKind = Literal["fact", "claim", "memory", "literature", "legend", "guess"]
Confidence = Literal["confirmed", "medium"]
Era = Literal["before_1800", "1800_1918", "1918_1939", "1939_1945", "1945_1989", "after_1989"]
RejectReason = Literal[
    "single_weak_source",
    "unconfirmed_sensation",
    "contradiction",
    "coincidence_as_cause",
    "claim_as_fact",
    "off_site",
    "licence",
    "irrelevant",
]
BridgeType = Literal["A", "B", "C", "E", "D"]
ChangeMode = Literal["two_voices", "plan", "chain", "trace", "people", "none"]
StepRole = Literal["anchor", "place_fact", "explanation", "jump", "return"]
Tone = Literal["light", "neutral", "elevated", "tragic"]
PlanStatus = Literal["ok", "area", "not_enough_material"]
FetchTool = Literal["wikipedia", "search", "wikidata", "warszawikia", "url"]

Voice = Literal["narrator", "co_narrator", "archive"]
LineRole = Literal["anchor", "place_fact", "explanation", "jump", "return", "quote"]
SoundKind = Literal["ambience", "motif", "spot"]
SoundShape = Literal["bed", "swell", "spot"]
Edge = Literal["start", "end"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(Model):
    fragment_id: FragmentId
    quote: Text


class Fact(Model):
    id: FactId
    text: Text
    evidence: Annotated[list[Evidence], Field(min_length=1)]
    kind: FactKind
    confidence: Confidence
    object_id: ObjectId | None
    era: Era | None


class Rejected(Model):
    text: Text
    fragment_ids: list[FragmentId]
    reason: RejectReason
    note: str | None


class Contradiction(Model):
    description: Text
    fact_ids: list[FactId]
    resolution: Text


class AxisCandidate(Model):
    axis: Text
    bridge_type: BridgeType
    reason: Text


class Bridge(Model):
    type: Literal["A", "B", "C", "E"]
    draft: Text
    fact_ids: list[FactId]


class Hook(Model):
    fact_ids: Annotated[list[FactId], Field(min_length=1)]
    why: Text


class PeriodVoice(Model):
    fact_id: FactId
    fragment_id: FragmentId
    quote: Text
    author: Text


class Step(Model):
    role: StepRole
    fact_ids: list[FactId]
    note: str | None


class Explain(Model):
    what: Text
    fact_id: FactId | None


class Story(Model):
    status: PlanStatus
    axis: str
    listener_question: str
    bridge: Bridge | None
    hook: Hook | None
    change_mode: ChangeMode
    period_voice: PeriodVoice | None
    steps: list[Step]
    explain: list[Explain]
    tone: Tone
    era: Era | None


class TextSection(Model):
    draft_heading: Text
    fact_ids: Annotated[list[FactId], Field(min_length=1)]


class Gap(Model):
    what: Text
    why: Text
    where: Text


class SpareLayer(Model):
    axis: Text
    bridge_type: BridgeType
    fact_ids: list[FactId]
    tone: Tone


class FetchLogEntry(Model):
    tool: FetchTool
    query: Text
    why: Text
    result: Text


class StoryPlan(Model):
    group_id: Annotated[str, StringConstraints(pattern=r"^\d+$")]
    stop_name: Text
    target_duration_s: Annotated[int, Field(ge=10, le=120)]
    facts: list[Fact]
    rejected: list[Rejected]
    contradictions: list[Contradiction]
    axis_candidates: list[AxisCandidate]
    story: Story
    text_sections: list[TextSection]
    image_ids: Annotated[list[ImageId], Field(max_length=5)]
    gaps: list[Gap]
    spare_layers: Annotated[list[SpareLayer], Field(max_length=2)]
    fetch_log: list[FetchLogEntry]


class Line(Model):
    id: LineId
    voice: Voice
    role: LineRole
    text: Text
    fact_ids: list[FactId]
    delivery: str | None
    pause_after_s: Annotated[float, Field(ge=0, le=4)]


class Anchor(Model):
    line_id: LineId
    edge: Edge
    offset_s: Annotated[float, Field(ge=-3, le=4)]


class Sound(Model):
    id: SoundId
    kind: SoundKind
    shape: SoundShape
    description: Text
    fact_ids: Annotated[list[FactId], Field(min_length=1)]
    start: Anchor
    end: Anchor | None


class Music(Model):
    mood: Text


class Sentence(Model):
    text: Text
    fact_ids: list[FactId]


class Paragraph(Model):
    sentences: Annotated[list[Sentence], Field(min_length=1)]


class Section(Model):
    heading: str | None
    paragraphs: Annotated[list[Paragraph], Field(min_length=1)]


class StoryScript(Model):
    group_id: Annotated[str, StringConstraints(pattern=r"^\d+$")]
    title: Text
    cast: Literal["solo", "duet", "solo_with_archive", "duet_with_archive"]
    tone: Tone
    target_duration_s: Annotated[int, Field(ge=10, le=120)]
    lines: Annotated[list[Line], Field(min_length=1)]
    sounds: Annotated[list[Sound], Field(max_length=3)]
    music: Music | None
    text: Annotated[list[Section], Field(min_length=1)]
    image_ids: Annotated[list[ImageId], Field(max_length=5)]


class VoicedLine(Model):
    id: LineId
    voice: Voice
    tts_text: Text


class VoicedSound(Model):
    id: SoundId
    prompt: Text
    duration_s: Annotated[float, Field(ge=0.5, le=30)]
    loop: bool


class VoicedMusic(Model):
    prompt: Text


class Pronunciation(Model):
    word: Text
    spoken_as: Text


class VoicedScript(Model):
    group_id: Annotated[str, StringConstraints(pattern=r"^\d+$")]
    lines: Annotated[list[VoicedLine], Field(min_length=1)]
    sounds: list[VoicedSound]
    music: VoicedMusic | None
    pronunciations: list[Pronunciation]
