from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from collector import cache, warszawikia, wikipedia
from collector.html_text import to_text
from collector.schema import Fragment, Source, SourceType
from collector.sources import Book


@dataclass(frozen=True)
class Site:
    type: SourceType
    publisher: str
    license: str
    license_url: str | None


SITES = {
    "www.warszawa1939.pl": Site(
        "varsaviana", "warszawa1939.pl", "CC BY-NC", "https://creativecommons.org/licenses/by-nc/4.0/"
    ),
    "muzeumwarszawy.pl": Site("institution", "Muzeum Warszawy", "wszelkie prawa zastrzeżone", None),
    "dzieje.pl": Site("institution", "dzieje.pl", "© PAP, wszelkie prawa zastrzeżone", "https://dzieje.pl/copyright"),
    "zabytek.pl": Site(
        "official",
        "Narodowy Instytut Dziedzictwa",
        "CC BY-NC-ND 3.0",
        "https://creativecommons.org/licenses/by-nc-nd/3.0/pl/",
    ),
    "wolnelektury.pl": Site(
        "literature", "Wolne Lektury", "domena publiczna lub CC BY-SA 3.0", "https://wolnelektury.pl/info/regulamin/"
    ),
}
PUBLISHERS = {site.publisher for site in SITES.values()}


class NotAllowed(ValueError):
    pass


def fetch_allowed_url(url: str) -> tuple[list[Source], list[Fragment]]:
    parts = urlsplit(url)
    title = unquote(parts.path.removeprefix("/wiki/")).replace("_", " ")
    if parts.hostname == "pl.wikipedia.org":
        return wikipedia.wikipedia_article(title)
    if parts.hostname == "warszawa.fandom.com":
        return warszawikia.warszawikia_article(title)
    site = SITES.get(parts.hostname or "")
    if not site:
        raise NotAllowed(f"{parts.hostname} is not on the allowlist: {', '.join(sorted(SITES))}")

    response = cache.fetch("GET", url)
    page_title, text = to_text(response.body)
    book = Book()
    source_id = book.add_source(
        type=site.type,
        title=page_title or url,
        publisher=site.publisher,
        url=url,
        license=site.license,
        license_url=site.license_url,
        retrieved_at=response.retrieved_at,
    )
    for heading, body in wikipedia.sections(text):
        for chunk in wikipedia.chunks(body):
            book.add_fragment(source_id, chunk, section=heading)
    return book.sources, book.fragments


def cached_text(url: str) -> str | None:
    stored = cache.lookup("GET", url)
    return to_text(stored.body)[1] if stored else None
