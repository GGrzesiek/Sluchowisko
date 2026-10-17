import re
from dataclasses import dataclass
from datetime import date

from collector import cache
from collector.schema import Fragment, NearbyObject, Source
from collector.sources import Book

API = "https://www.wikidata.org/w/api.php"
LICENSE = "CC0 1.0"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
ENTITY_PROPS = "labels|descriptions|claims|sitelinks"
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
    wikipedia_title: str | None = None

    def items(self, prop: str) -> list[str]:
        return [value["id"] for value in self.values(prop) if isinstance(value, dict) and "id" in value]

    def values(self, prop: str) -> list:
        return [
            claim["mainsnak"]["datavalue"]["value"]
            for claim in self.claims.get(prop, [])
            if claim.get("rank") != "deprecated" and claim["mainsnak"].get("snaktype") == "value"
        ]


def _params(qid: str, props: str) -> dict[str, str]:
    return {"action": "wbgetentities", "ids": qid, "props": props, "languages": "pl", "format": "json"}


def entity(qid: str) -> Entity | None:
    response = cache.fetch("GET", API, params=_params(qid, ENTITY_PROPS))
    found = next(iter(response.json().get("entities", {}).values()), None)
    if not found or "missing" in found:
        return None
    if found["id"] != qid:
        return entity(found["id"])
    sitelinks = found.get("sitelinks", {})
    return Entity(
        qid=found["id"],
        label=_label(found),
        description=found.get("descriptions", {}).get("pl", {}).get("value"),
        claims=found.get("claims", {}),
        wikipedias=sum(key.endswith("wiki") and key not in NOT_WIKIPEDIAS for key in sitelinks),
        retrieved_at=response.retrieved_at,
        wikipedia_title=sitelinks.get("plwiki", {}).get("title"),
    )


def labels(qids: set[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for qid in sorted(qids, key=lambda qid: int(qid[1:])):
        response = cache.fetch("GET", API, params=_params(qid, "labels"))
        if label := _label(next(iter(response.json().get("entities", {}).values()), {})):
            found[qid] = label
    return found


def _label(item: dict) -> str | None:
    return item.get("labels", {}).get("pl", {}).get("value")


class CachedLabels:
    def __contains__(self, qid: str) -> bool:
        return self[qid] is not None

    def __getitem__(self, qid: str) -> str | None:
        for props in (ENTITY_PROPS, "labels"):
            stored = cache.lookup("GET", API, params=_params(qid, props))
            if stored and (label := _label(next(iter(stored.json().get("entities", {}).values()), {}))):
                return label
        return None


def check_values(url: str, template: str, values: dict) -> str | None:
    found = entity(url.rsplit("/", 1)[-1])
    if not found or not found.label:
        return "the cached Wikidata item has no Polish label"
    expected = {name: {"label": found.label, **facts} for name, facts in _facts(found, CachedLabels())}
    if expected.get(template) != values:
        return f"values {values} do not match the cached Wikidata item ({expected.get(template)})"
    return None


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


def _facts(found: Entity, names: "dict[str, str] | CachedLabels") -> list[tuple[str, dict[str, str | int]]]:
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


def _joined(qids: list[str], names: "dict[str, str] | CachedLabels") -> str | None:
    return ", ".join(names[qid] for qid in qids if qid in names) or None


def _ids(values) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen
