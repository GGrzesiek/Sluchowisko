import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

RADIUS_M = 400
MAX_NEARBY_ARTICLES = 50

SourceType = Literal[
    "official",
    "city_data",
    "institution",
    "encyclopedia",
    "varsaviana",
    "press",
    "local_portal",
    "blog",
    "commercial",
    "literature",
]
ObjectKind = Literal["street", "square", "building", "monument", "memorial", "park", "church", "institution", "other"]
ImageKind = Literal["photo", "photo_map_1935", "plan_1939", "photo_map_1945", "orthophoto"]

Text = Annotated[str, StringConstraints(min_length=1)]
Url = Annotated[str, StringConstraints(pattern=r"^https?://\S+$")]
Qid = Annotated[str, StringConstraints(pattern=r"^Q\d+$")]
GroupId = Annotated[str, StringConstraints(pattern=r"^\d+$")]
SourceId = Annotated[str, StringConstraints(pattern=r"^s\d+$")]
FragmentId = Annotated[str, StringConstraints(pattern=r"^s\d+#\d+$")]
ObjectId = Annotated[str, StringConstraints(pattern=r"^o\d+$")]
ImageId = Annotated[str, StringConstraints(pattern=r"^i\d+$")]
Distance = Annotated[int, Field(ge=0)]
Lat = Annotated[float, Field(ge=-90, le=90)]
Lon = Annotated[float, Field(ge=-180, le=180)]

_WHITESPACE = re.compile(r"\s+")
_NO_DERIVATIVES = re.compile(r"\bND\b")
_NON_COMMERCIAL = re.compile(r"\bNC\b")


def normalize_text(text: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


def id_number(item_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", item_id))


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Pole(Model):
    pole: Text
    lat: Lat
    lon: Lon


class Stop(Model):
    group_id: GroupId
    name: Text
    lat: Lat
    lon: Lon
    poles: Annotated[list[Pole], Field(min_length=1)]


class StreetName(Model):
    name: Text
    object_id: ObjectId | None
    named_after: Qid | None
    distance_m: Distance


class NearbyArticle(Model):
    title: Text
    distance_m: Distance
    fetched: bool


class Area(Model):
    district: Text
    neighbourhood: Text | None
    fragment_ids: list[FragmentId]
    street_names: list[StreetName]
    nearby_articles: Annotated[list[NearbyArticle], Field(max_length=MAX_NEARBY_ARTICLES)]

    @model_validator(mode="after")
    def _articles_sorted_by_distance(self) -> Self:
        distances = [article.distance_m for article in self.nearby_articles]
        if distances != sorted(distances):
            raise ValueError("area.nearby_articles must be sorted by distance_m")
        if any(article.distance_m > RADIUS_M for article in self.nearby_articles):
            raise ValueError(f"area.nearby_articles must be within {RADIUS_M} m")
        return self


class NearbyObject(Model):
    id: ObjectId
    name: Text
    kind: ObjectKind
    distance_m: Distance
    osm_id: Annotated[str, StringConstraints(pattern=r"^(node|way|relation)/\d+$")] | None
    wikidata: Qid | None
    wikipedia: Annotated[str, StringConstraints(pattern=r"^[a-z]{2,3}:.+$")] | None
    named_after: Qid | None
    named_after_label: Text | None
    old_names: list[Text]
    heritage_ref: Text | None
    tags: dict[str, str]


class Source(Model):
    id: SourceId
    type: SourceType
    title: Text
    publisher: Text
    url: Url
    license: Text
    license_url: Url | None
    author: Text | None
    author_death_year: int | None
    retrieved_at: date


class Fragment(Model):
    id: FragmentId
    source_id: SourceId
    section: Text | None
    text: Text
    object_id: ObjectId | None
    derived: bool
    template: Text | None = None
    values: dict[str, str | int | float] | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.id.split("#")[0] != self.source_id:
            raise ValueError(f"fragment {self.id}: id must start with its source_id {self.source_id}")
        if self.text != normalize_text(self.text):
            raise ValueError(f"fragment {self.id}: text must be NFC with whitespace collapsed (use normalize_text)")
        if self.derived and (self.template is None or self.values is None):
            raise ValueError(f"fragment {self.id}: a derived fragment needs template and values")
        if not self.derived and (self.template is not None or self.values is not None):
            raise ValueError(f"fragment {self.id}: only a derived fragment has template and values")
        return self


class Image(Model):
    id: ImageId
    kind: ImageKind
    file: Text
    url: Url
    caption: Text
    author: Text | None
    year: Annotated[str, StringConstraints(pattern=r"^\d{4}$")] | None
    license: Text
    license_url: Url | None
    non_commercial: bool
    source_id: SourceId | None
    object_id: ObjectId | None

    @model_validator(mode="after")
    def _check_license(self) -> Self:
        if _NO_DERIVATIVES.search(self.license.upper()):
            raise ValueError(f"image {self.id}: ND licences are not candidates ({self.license})")
        if self.non_commercial != bool(_NON_COMMERCIAL.search(self.license.upper())):
            raise ValueError(f"image {self.id}: non_commercial must match the licence ({self.license})")
        return self


def _unique(kind: str, ids: list[str]) -> set[str]:
    seen = set()
    for item_id in ids:
        if item_id in seen:
            raise ValueError(f"duplicate {kind} id {item_id}")
        seen.add(item_id)
    return seen


def _known(kind: str, item_id: str | None, known: set[str], where: str) -> None:
    if item_id is not None and item_id not in known:
        raise ValueError(f"{where} points to unknown {kind} {item_id}")


def _sorted(kind: str, ids: list[str]) -> None:
    if ids != sorted(ids, key=id_number):
        raise ValueError(f"{kind} must be sorted by id")


class CollectedStop(Model):
    stop: Stop
    area: Area
    objects: list[NearbyObject]
    sources: list[Source]
    fragments: list[Fragment]
    images: list[Image]

    @model_validator(mode="after")
    def _check_file(self) -> Self:
        object_ids = _unique("object", [o.id for o in self.objects])
        source_ids = _unique("source", [s.id for s in self.sources])
        fragment_ids = _unique("fragment", [f.id for f in self.fragments])
        _unique("image", [i.id for i in self.images])

        distances = [o.distance_m for o in self.objects]
        if distances != sorted(distances):
            raise ValueError("objects must be sorted by distance_m")
        _sorted("sources", [s.id for s in self.sources])
        _sorted("fragments", [f.id for f in self.fragments])
        _sorted("images", [i.id for i in self.images])

        for fragment_id in self.area.fragment_ids:
            _known("fragment", fragment_id, fragment_ids, "area.fragment_ids")
        for street in self.area.street_names:
            _known("object", street.object_id, object_ids, f"area.street_names {street.name}")
        for fragment in self.fragments:
            _known("source", fragment.source_id, source_ids, f"fragment {fragment.id}")
            _known("object", fragment.object_id, object_ids, f"fragment {fragment.id}")
        for image in self.images:
            _known("source", image.source_id, source_ids, f"image {image.id}")
            _known("object", image.object_id, object_ids, f"image {image.id}")
            expected = f"out/images/{self.stop.group_id}/{image.id}.jpg"
            if image.file != expected:
                raise ValueError(f"image {image.id}: file must be {expected}")
        return self


def output_path(group_id: str, root: Path = Path("out/collected")) -> Path:
    return root / f"{group_id}.json"


def dumps(collected: CollectedStop) -> str:
    data = collected.model_dump(mode="json", exclude_defaults=True)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def save(collected: CollectedStop, root: Path = Path("out/collected")) -> Path:
    path = output_path(collected.stop.group_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(collected), encoding="utf-8")
    return path


def load(path: Path) -> CollectedStop:
    return CollectedStop.model_validate_json(path.read_text(encoding="utf-8"))
