from datetime import date

from collector.schema import Fragment, Source, SourceType, id_number, normalize_text

TEMPLATES = {
    "wikidata.description": "{label}: {description}.",
    "wikidata.named_after": "{label} – pochodzenie nazwy: {named_after}.",
    "wikidata.inception": "{label} – data powstania: {inception}.",
    "wikidata.heritage": "{label} – status ochrony: {heritage}.",
    "wikidata.born": "{label} – data urodzenia: {born}.",
    "wikidata.died": "{label} – data śmierci: {died}.",
    "wikidata.sitelinks": "{label} – liczba artykułów w Wikipedii w różnych językach: {sitelinks}.",
    "city.flat_prices": (
        "Mediana ceny 1 m² lokalu mieszkalnego w transakcjach rynkowych z {year} r. w promieniu 400 m od przystanku "
        "{name} wyniosła {price} zł (liczba lokali: {count})."
    ),
    "city.budget": (
        "W budżecie obywatelskim na rok {year} zrealizowano projekt „{title}”, {distance} m od przystanku {name}; "
        "koszt: {cost} zł."
    ),
    "city.budget_no_cost": (
        "W budżecie obywatelskim na rok {year} zrealizowano projekt „{title}”, {distance} m od przystanku {name}."
    ),
    "city.tree": (
        "W rejestrze drzew m.st. Warszawy, {distance} m od przystanku {name}: {species} ({latin}), obwód pnia "
        "{girth} cm, wysokość {height} m, dane z {year} r."
    ),
}


def render(template: str, values: dict[str, str | int | float]) -> str:
    return normalize_text(TEMPLATES[template].format(**values))


class Book:
    def __init__(self) -> None:
        self._sources: list[Source] = []
        self._fragments: list[Fragment] = []
        self._by_url: dict[str, str] = {}
        self._fragment_count: dict[str, int] = {}

    def source_id(self, url: str) -> str | None:
        return self._by_url.get(url)

    def fragment_ids(self, source_id: str) -> list[str]:
        return [f"{source_id}#{number}" for number in range(1, self._fragment_count.get(source_id, 0) + 1)]

    def add_source(
        self,
        *,
        type: SourceType,
        title: str,
        publisher: str,
        url: str,
        license: str,
        license_url: str | None,
        retrieved_at: date,
        author: str | None = None,
        author_death_year: int | None = None,
    ) -> str:
        if url in self._by_url:
            return self._by_url[url]
        source_id = f"s{len(self._sources) + 1}"
        self._sources.append(
            Source(
                id=source_id,
                type=type,
                title=title,
                publisher=publisher,
                url=url,
                license=license,
                license_url=license_url,
                author=author,
                author_death_year=author_death_year,
                retrieved_at=retrieved_at,
            )
        )
        self._by_url[url] = source_id
        return source_id

    def add_fragment(
        self, source_id: str, text: str, *, section: str | None = None, object_id: str | None = None
    ) -> str:
        return self._add(source_id, normalize_text(text), section, object_id, None, None)

    def add_derived(
        self,
        source_id: str,
        template: str,
        values: dict[str, str | int | float],
        *,
        section: str | None = None,
        object_id: str | None = None,
    ) -> str:
        return self._add(source_id, render(template, values), section, object_id, template, values)

    def _add(
        self,
        source_id: str,
        text: str,
        section: str | None,
        object_id: str | None,
        template: str | None,
        values: dict | None,
    ) -> str:
        number = self._fragment_count.get(source_id, 0) + 1
        self._fragment_count[source_id] = number
        fragment_id = f"{source_id}#{number}"
        self._fragments.append(
            Fragment(
                id=fragment_id,
                source_id=source_id,
                section=section,
                text=text,
                object_id=object_id,
                derived=template is not None,
                template=template,
                values=values,
            )
        )
        return fragment_id

    @property
    def sources(self) -> list[Source]:
        return list(self._sources)

    @property
    def fragments(self) -> list[Fragment]:
        return sorted(self._fragments, key=lambda fragment: id_number(fragment.id))
