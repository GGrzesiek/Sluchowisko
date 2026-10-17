import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote, unquote

from collector import cache
from collector.html_text import to_text
from collector.schema import Fragment, NearbyObject, Source, Stop
from collector.sources import Book
from collector.wikipedia import chunks, sections

API = "https://warszawa.fandom.com/api.php"
SEARCH_LIMIT = 5
STREET_PREFIXES = ("Ulica", "Aleja", "Aleje", "Plac", "Rondo", "Skwer", "Most")
STOP_PREFIX = "Zespół przystankowy "


@dataclass(frozen=True)
class Article:
    title: str
    html: str
    retrieved_at: date

    @property
    def url(self) -> str:
        return article_url(self.title)


def plain_text(html: str) -> str:
    return to_text(html)[1]


def article_url(title: str) -> str:
    return f"https://warszawa.fandom.com/wiki/{quote(title.replace(' ', '_'))}"


def _parse_params(title: str) -> dict[str, str]:
    return {
        "action": "parse",
        "page": title,
        "prop": "text",
        "redirects": "1",
        "disablelimitreport": "1",
        "disableeditsection": "1",
        "format": "json",
        "formatversion": "2",
    }


def article(title: str) -> Article | None:
    response = cache.fetch("GET", API, params=_parse_params(title))
    parsed = response.json().get("parse")
    if not parsed or not parsed.get("text"):
        return None
    if parsed["title"] != title:
        return article(parsed["title"])
    return Article(title=parsed["title"], html=parsed["text"], retrieved_at=response.retrieved_at)


def cached_text(url: str) -> str | None:
    title = unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")
    stored = cache.lookup("GET", API, params=_parse_params(title))
    parsed = stored.json().get("parse") if stored else None
    return plain_text(parsed["text"]) if parsed and parsed.get("text") else None


def licence() -> tuple[str, str]:
    response = cache.fetch(
        "GET",
        API,
        params={"action": "query", "meta": "siteinfo", "siprop": "rightsinfo", "format": "json", "formatversion": "2"},
    )
    rights = response.json()["query"]["rightsinfo"]
    return rights["text"], rights["url"]


def search(query: str) -> list[str]:
    response = cache.fetch(
        "GET",
        API,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": "0",
            "srlimit": str(SEARCH_LIMIT),
            "format": "json",
            "formatversion": "2",
        },
    )
    return [item["title"] for item in response.json().get("query", {}).get("search", [])]


def wikitext(title: str) -> str:
    response = cache.fetch(
        "GET",
        API,
        params={
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": title,
            "format": "json",
            "formatversion": "2",
        },
    )
    pages = response.json().get("query", {}).get("pages", [])
    revisions = pages[0].get("revisions", []) if pages else []
    return revisions[0]["slots"]["main"]["content"] if revisions else ""


def stop_title(stop: Stop) -> str | None:
    marker = re.compile(r"\{\{\s*Zespół\s*\|[^{}]*\|\s*" + re.escape(stop.group_id) + r"\s*\}\}")
    for title in search(f"{STOP_PREFIX}{stop.name}"):
        if title.startswith(STOP_PREFIX) and marker.search(wikitext(title)):
            return title
    return None


def street_title(name: str) -> str | None:
    for title in search(name):
        prefix, _, street = title.partition(" ")
        if prefix in STREET_PREFIXES and street and (name == street or name.endswith(f" {street}")):
            return title
    return None


def add_article(found: Article, book: Book, object_id: str | None = None) -> list[str]:
    existing = book.source_id(found.url)
    if existing:
        return book.fragment_ids(existing)
    license, license_url = licence()
    source_id = book.add_source(
        type="varsaviana",
        title=found.title,
        publisher="Warszawikia",
        url=found.url,
        license=license,
        license_url=license_url,
        retrieved_at=found.retrieved_at,
    )
    return [
        book.add_fragment(source_id, text, section=heading, object_id=object_id)
        for heading, body in sections(plain_text(found.html))
        for text in chunks(body)
    ]


def collect_articles(stop: Stop, streets: list[NearbyObject], book: Book) -> None:
    wanted: list[tuple[str, str | None]] = []
    if title := stop_title(stop):
        wanted.append((title, None))
    for street in streets:
        if title := street_title(street.name):
            wanted.append((title, street.id))
    for title, object_id in wanted:
        if found := article(title):
            add_article(found, book, object_id)


def warszawikia_article(title: str) -> tuple[list[Source], list[Fragment]]:
    book = Book()
    if found := article(title):
        add_article(found, book)
    return book.sources, book.fragments
