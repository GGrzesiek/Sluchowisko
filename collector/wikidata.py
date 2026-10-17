import re
from dataclasses import dataclass
from datetime import date

from collector import cache
from collector.schema import Fragment, NearbyObject, Source
from collector.sources import Book

API = "https://www.wikidata.org/w/api.php"
LICENSE = "CC0 1.0"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
LABEL_BATCH = 50
NOT_WIKIPEDIAS = {
    "commonswiki",
    "specieswiki",
    "metawiki",
    "wikidatawiki",
    "mediawikiwiki",
    "sourceswiki",
    "incubatorwiki",
    "outreachwiki",
    "wikimaniawiki",
    "foundationwiki",
    "wikifunctionswiki",
}
WIKIDATA_TIME = re.compile(r"^\+(\d{4,})-(\d\d)-(\d\d)T")


@dataclass(frozen=True)
class Entity:
    qid: str
    label: str | None
    description: str | None
    claims: dict[str, list[dict]]
    wikipedias: int
    retrieved_at: date

    def items(self, prop: str) -> list[str]:
        return [value["id"] for value in self.values(prop) if isinstance(value, dict) and "id" in value]

    def values(self, prop: str) -> list:
        return [
            claim["mainsnak"]["datavalue"]["value"]
            for claim in self.claims.get(prop, [])
            if claim.get("rank") != "deprecated" and claim["mainsnak"].get("snaktype") == "value"
        ]


def entity(qid: str) -> Entity | None:
    response = cache.fetch(
        "GET",
        API,
        params={
            "action": "wbgetentities",
            "ids": qid,
            "props": "labels|descriptions|claims|sitelinks",
            "languages": "pl",
            "format": "json",
        },
    )
    found = next(iter(response.json().get("entities", {}).values()), None)
    if not found or "missing" in found:
        return None
    return Entity(
        qid=found["id"],
        label=found.get("labels", {}).get("pl", {}).get("value"),
        description=found.get("descriptions", {}).get("pl", {}).get("value"),
        claims=found.get("claims", {}),
        wikipedias=sum(key.endswith("wiki") and key not in NOT_WIKIPEDIAS for key in found.get("sitelinks", {})),
        retrieved_at=response.retrieved_at,
    )


def labels(qids: set[str]) -> dict[str, str]:
    ordered = sorted(qids, key=lambda qid: int(qid[1:]))
    found: dict[str, str] = {}
    for start in range(0, len(ordered), LABEL_BATCH):
        batch = ordered[start : start + LABEL_BATCH]
        response = cache.fetch(
            "GET",
            API,
            params={
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "labels",
                "languages": "pl",
                "format": "json",
            },
        )
        for qid, item in response.json().get("entities", {}).items():
            if label := item.get("labels", {}).get("pl", {}).get("value"):
                found[qid] = label
    return found


def format_time(value: dict) -> str | None:
    match = WIKIDATA_TIME.match(value.get("time", ""))
    if not match:
        return None
    year, month, day = match.groups()
    year = str(int(year))
    if value["precision"] >= 11:
        return f"{int(day)}.{month}.{year}"
    if value["precision"] == 10:
        return f"{month}.{year}"
    if value["precision"] == 9:
        return year
    return None


def enrich(objects: list[NearbyObject], book: Book) -> list[NearbyObject]:
    entities = {qid: entity(qid) for qid in _ids(o.wikidata for o in objects)}
    objects = [_with_patron(o, entities.get(o.wikidata)) for o in objects]
    entities |= {qid: entity(qid) for qid in _ids(o.named_after for o in objects) if qid not in entities}
    known = {qid: found for qid, found in entities.items() if found}

    referenced = {qid for found in known.values() for prop in ("P138", "P1435") for qid in found.items(prop)}
    names = labels(referenced - {qid for qid, found in known.items() if found.label}) | {
        qid: found.label for qid, found in known.items() if found.label
    }

    described: set[str] = set()
    for nearby in objects:
        for qid in (nearby.wikidata, nearby.named_after):
            if qid in known and qid not in described:
                described.add(qid)
                add_entity(known[qid], names, book, object_id=nearby.id)
    return [
        o.model_copy(update={"named_after_label": names.get(o.named_after)}) if o.named_after else o for o in objects
    ]


def add_entity(found: Entity, names: dict[str, str], book: Book, object_id: str | None = None) -> str | None:
    facts = _facts(found, names)
    if not found.label or not facts:
        return None
    source_id = book.add_source(
        type="encyclopedia",
        title=found.label,
        publisher="Wikidata",
        url=f"https://www.wikidata.org/wiki/{found.qid}",
        license=LICENSE,
        license_url=LICENSE_URL,
        retrieved_at=found.retrieved_at,
    )
    for template, values in facts:
        book.add_derived(source_id, template, {"label": found.label, **values}, object_id=object_id)
    return source_id


def wikidata_entity(qid: str) -> tuple[list[Source], list[Fragment]]:
    book = Book()
    found = entity(qid)
    if found:
        referenced = {item for prop in ("P138", "P1435") for item in found.items(prop)}
        add_entity(found, labels(referenced), book)
    return book.sources, book.fragments


def _facts(found: Entity, names: dict[str, str]) -> list[tuple[str, dict[str, str | int]]]:
    facts: list[tuple[str, dict[str, str | int]]] = []
    if found.description:
        facts.append(("wikidata.description", {"description": found.description}))
    if named_after := _joined(found.items("P138"), names):
        facts.append(("wikidata.named_after", {"named_after": named_after}))
    if heritage := _joined(found.items("P1435"), names):
        facts.append(("wikidata.heritage", {"heritage": heritage}))
    for prop, template, key in (
        ("P571", "wikidata.inception", "inception"),
        ("P569", "wikidata.born", "born"),
        ("P570", "wikidata.died", "died"),
    ):
        dates = [formatted for value in found.values(prop) if (formatted := format_time(value))]
        if dates:
            facts.append((template, {key: dates[0]}))
    if found.wikipedias:
        facts.append(("wikidata.sitelinks", {"sitelinks": found.wikipedias}))
    return facts


def _with_patron(nearby: NearbyObject, found: Entity | None) -> NearbyObject:
    if nearby.named_after or not found:
        return nearby
    patrons = found.items("P138")
    return nearby.model_copy(update={"named_after": patrons[0]}) if len(patrons) == 1 else nearby


def _joined(qids: list[str], names: dict[str, str]) -> str | None:
    return ", ".join(names[qid] for qid in qids if qid in names) or None


def _ids(values) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen
