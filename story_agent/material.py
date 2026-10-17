import re

from collector.schema import CollectedStop, Fragment, Source, id_number, load, normalize_text
from story_agent.files import collected_path, extra_path, read_json, write_json
from story_agent.sources import (
    SourceDraft,
    fetch_allowed_url,
    warszawikia_article,
    warszawikia_search,
    wikidata_entity,
    wikipedia_article,
    wikipedia_search,
)

MAX_FETCHES = 10


def load_extra(group_id: str) -> dict:
    path = extra_path(group_id)
    if not path.exists():
        return {"sources": [], "fragments": [], "log": []}
    data = read_json(path)
    data["sources"] = [Source.model_validate(s) for s in data["sources"]]
    data["fragments"] = [Fragment.model_validate(f) for f in data["fragments"]]
    return data


def load_material(group_id: str) -> CollectedStop:
    base = load(collected_path(group_id))
    extra = load_extra(group_id)
    if not extra["sources"]:
        return base
    data = base.model_dump(mode="json")
    data["sources"] += [s.model_dump(mode="json") for s in extra["sources"]]
    data["fragments"] += [f.model_dump(mode="json") for f in extra["fragments"]]
    data["sources"].sort(key=lambda s: id_number(s["id"]))
    data["fragments"].sort(key=lambda f: id_number(f["id"]))
    return CollectedStop.model_validate(data)


def _next_source_id(material: CollectedStop) -> str:
    numbers = [id_number(s.id)[0] for s in material.sources]
    return f"s{max(numbers, default=0) + 1}"


def _draft_to_models(draft: SourceDraft, source_id: str) -> tuple[Source, list[Fragment]]:
    source = Source(
        id=source_id,
        type=draft.type,
        title=draft.title,
        publisher=draft.publisher,
        url=draft.url,
        license=draft.license,
        license_url=draft.license_url,
        author=draft.author,
        author_death_year=draft.author_death_year,
        retrieved_at=draft.retrieved_at or "1970-01-01",
    )
    fragments = [
        Fragment(
            id=f"{source_id}#{n}",
            source_id=source_id,
            section=section,
            text=normalize_text(text),
            object_id=None,
            derived=False,
        )
        for n, (section, text) in enumerate(draft.sections, start=1)
    ]
    offset = len(fragments)
    fragments += [
        Fragment(
            id=f"{source_id}#{n}",
            source_id=source_id,
            section=None,
            text=normalize_text(text),
            object_id=None,
            derived=True,
            template=template,
            values=values,
        )
        for n, (text, template, values) in enumerate(draft.derived, start=offset + 1)
    ]
    return source, fragments


def fetch_more(group_id: str, tool: str, query: str, why: str) -> str:
    material = load_material(group_id)
    extra = load_extra(group_id)
    if len(extra["log"]) >= MAX_FETCHES:
        return f"Limit {MAX_FETCHES} dociągnięć dla tego przystanku wyczerpany. Zapisz brak w `gaps`."
    known_urls = {s.url: s.id for s in material.sources}
    if tool in ("search", "warszawikia-search"):
        titles = wikipedia_search(query) if tool == "search" else warszawikia_search(query)
        result = "Tytuły: " + (" | ".join(titles) if titles else "brak wyników")
        extra["log"].append({"tool": "search", "query": query, "why": why, "result": result})
        _save_extra(group_id, extra)
        return result
    if tool == "wikipedia":
        draft = wikipedia_article(query)
    elif tool == "wikidata":
        draft = wikidata_entity(query)
    elif tool == "warszawikia":
        draft = warszawikia_article(query)
    elif tool == "url":
        draft = fetch_allowed_url(query)
    else:
        raise ValueError(f"unknown tool {tool}")
    log_tool = "url" if tool == "url" else tool
    if draft is None:
        result = "nie znaleziono"
        extra["log"].append({"tool": log_tool, "query": query, "why": why, "result": result})
        _save_extra(group_id, extra)
        return result
    if draft.url in known_urls:
        source_id = known_urls[draft.url]
        fragments = [f for f in material.fragments if f.source_id == source_id]
        return f"To źródło już jest w materiale jako {source_id}.\n\n" + render_fragments(material, fragments)
    source_id = _next_source_id(material)
    source, fragments = _draft_to_models(draft, source_id)
    extra["sources"].append(source)
    extra["fragments"] += fragments
    result = f"{source_id}: {source.title} ({len(fragments)} fragmentów)"
    extra["log"].append({"tool": log_tool, "query": query, "why": why, "result": result})
    _save_extra(group_id, extra)
    material = load_material(group_id)
    if not fragments:
        return result + "\nTylko link, bez fragmentów do cytowania."
    return result + "\n\n" + render_fragments(material, fragments)


def _save_extra(group_id: str, extra: dict) -> None:
    write_json(
        extra_path(group_id),
        {
            "sources": [s.model_dump(mode="json") for s in extra["sources"]],
            "fragments": [f.model_dump(mode="json") for f in extra["fragments"]],
            "log": extra["log"],
        },
    )


def fetch_log(group_id: str) -> list[dict]:
    return load_extra(group_id)["log"]


def render_fragments(material: CollectedStop, fragments: list[Fragment]) -> str:
    sources = {s.id: s for s in material.sources}
    lines = []
    for fragment in fragments:
        source = sources[fragment.source_id]
        section = f" / {fragment.section}" if fragment.section else ""
        flag = " [derived]" if fragment.derived else ""
        lines.append(f"[{fragment.id}] {source.title}{section}{flag}\n{fragment.text}\n")
    return "\n".join(lines)


def render_material(material: CollectedStop) -> str:
    stop = material.stop
    out = [
        f"# {stop.name} (zespół {stop.group_id}) {stop.lat}, {stop.lon}",
        f"Dzielnica: {material.area.district}; okolica: {material.area.neighbourhood or '—'}",
        "",
        "## Obiekty (do 400 m)",
    ]
    for o in material.objects:
        extra = []
        if o.named_after_label:
            extra.append(f"patron: {o.named_after_label} ({o.named_after})")
        if o.old_names:
            extra.append("dawne nazwy: " + ", ".join(o.old_names))
        if o.wikipedia:
            extra.append(f"wiki: {o.wikipedia}")
        if o.heritage_ref:
            extra.append(f"zabytek: {o.heritage_ref}")
        out.append(f"- {o.id} {o.kind} „{o.name}” {o.distance_m} m" + (f" — {'; '.join(extra)}" if extra else ""))
    out += ["", "## Hasła Wikipedii w promieniu 400 m"]
    for article in material.area.nearby_articles:
        missing = "" if article.fetched else " — niepobrane"
        out.append(f"- {article.title} ({article.distance_m} m){missing}")
    out += ["", "## Źródła"]
    for s in material.sources:
        author = f", autor: {s.author} (zm. {s.author_death_year})" if s.author else ""
        out.append(f"- {s.id} [{s.type}] {s.title} — {s.publisher}, {s.license}{author} — {s.url}")
    out += ["", "## Zdjęcia"]
    for i in material.images:
        out.append(f"- {i.id} {i.kind} {i.year or ''} „{i.caption[:160]}” — {i.author or 'NN'}, {i.license}")
    out += ["", "## Fragmenty", ""]
    out.append(render_fragments(material, list(material.fragments)))
    return "\n".join(out)


def quote_in_fragment(quote: str, fragment_text: str) -> bool:
    def squash(value: str) -> str:
        value = normalize_text(value)
        value = re.sub(r"[„”“\"«»]", '"', value)
        value = re.sub(r"[‘’']", "'", value)
        return value.replace("–", "-").replace("—", "-")

    return squash(quote) in squash(fragment_text)
