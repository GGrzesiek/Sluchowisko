import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote, unquote, urlsplit

from collector import cache, wikidata
from collector.geo import distance_m
from collector.images import LeadImage
from collector.schema import MAX_NEARBY_ARTICLES, RADIUS_M, Fragment, NearbyArticle, NearbyObject, Source, Stop
from collector.sources import Book

LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
DROPPED_SECTIONS = {"Przypisy", "Bibliografia", "Linki zewnętrzne", "Zobacz też"}
MAX_FRAGMENT_CHARS = 4000
FULL_TEXT_NEAREST = 15
STOP_ARTICLE_RADIUS_M = 1000
HEADING = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Articles:
    area_fragment_ids: list[str]
    nearby: list[NearbyArticle]
    lead_images: list[LeadImage]


@dataclass(frozen=True)
class Article:
    lang: str
    title: str
    text: str
    coordinates: tuple[float, float] | None
    retrieved_at: date
    image: str | None = None

    @property
    def url(self) -> str:
        return article_url(self.lang, self.title)


def api(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/w/api.php"


def article_url(lang: str, title: str) -> str:
    return f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


def _extract_params(title: str) -> dict[str, str]:
    return {
        "action": "query",
        "prop": "extracts|pageprops|coordinates|pageimages",
        "ppprop": "disambiguation",
        "piprop": "name",
        "explaintext": "1",
        "exsectionformat": "wiki",
        "titles": title,
        "redirects": "1",
        "format": "json",
        "formatversion": "2",
    }


def article(title: str, lang: str = "pl") -> Article | None:
    page, retrieved_at = _page(title, lang)
    if page and page["title"] != title:
        page, retrieved_at = _page(page["title"], lang)
    if not page or "disambiguation" in page.get("pageprops", {}) or not page.get("extract"):
        return None
    primary = next((c for c in page.get("coordinates", []) if c.get("primary")), None)
    return Article(
        lang=lang,
        title=page["title"],
        text=page["extract"],
        coordinates=(primary["lat"], primary["lon"]) if primary else None,
        retrieved_at=retrieved_at,
        image=page.get("pageimage"),
    )


def _page(title: str, lang: str) -> tuple[dict | None, date]:
    response = cache.fetch("GET", api(lang), params=_extract_params(title))
    pages = response.json().get("query", {}).get("pages", [])
    page = pages[0] if pages else None
    if not page or page.get("missing") or page.get("invalid"):
        return None, response.retrieved_at
    return page, response.retrieved_at


def cached_text(url: str) -> str | None:
    parts = urlsplit(url)
    lang = parts.hostname.split(".")[0]
    title = unquote(parts.path.removeprefix("/wiki/")).replace("_", " ")
    stored = cache.lookup("GET", api(lang), params=_extract_params(title))
    if not stored:
        return None
    pages = stored.json().get("query", {}).get("pages", [])
    return pages[0].get("extract") if pages else None


def sections(text: str) -> list[tuple[str | None, str]]:
    parts: list[tuple[int, str | None, str]] = []
    start, level, heading = 0, 1, None
    for match in HEADING.finditer(text):
        parts.append((level, heading, text[start : match.start()]))
        start, level, heading = match.end(), len(match.group(1)), match.group(2)
    parts.append((level, heading, text[start:]))

    kept: list[tuple[str | None, str]] = []
    dropped_level: int | None = None
    for level, heading, body in parts:
        if dropped_level is not None and level > dropped_level:
            continue
        dropped_level = level if heading in DROPPED_SECTIONS else None
        if dropped_level is None and body.strip():
            kept.append((heading, body))
    return kept


def chunks(body: str) -> list[str]:
    paragraphs = [" ".join(line.split()) for line in body.split("\n") if line.strip()]
    result: list[str] = []
    for paragraph in paragraphs:
        if result and len(result[-1]) + 1 + len(paragraph) <= MAX_FRAGMENT_CHARS:
            result[-1] = f"{result[-1]} {paragraph}"
        else:
            result.append(paragraph)
    return result


def add_article(found: Article, book: Book, object_id: str | None = None) -> list[str]:
    existing = book.source_id(found.url)
    if existing:
        return book.fragment_ids(existing)
    source_id = book.add_source(
        type="encyclopedia",
        title=found.title,
        publisher="Wikipedia",
        url=found.url,
        license=LICENSE,
        license_url=LICENSE_URL,
        retrieved_at=found.retrieved_at,
    )
    return [
        book.add_fragment(source_id, text, section=heading, object_id=object_id)
        for heading, body in sections(found.text)
        for text in chunks(body)
    ]


def geosearch(lat: float, lon: float, lang: str = "pl") -> list[tuple[str, int]]:
    response = cache.fetch(
        "GET",
        api(lang),
        params={
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{lat:.6f}|{lon:.6f}",
            "gsradius": str(RADIUS_M),
            "gslimit": str(MAX_NEARBY_ARTICLES),
            "format": "json",
            "formatversion": "2",
        },
    )
    found = [(item["title"], round(item["dist"])) for item in response.json().get("query", {}).get("geosearch", [])]
    return sorted((item for item in found if item[1] <= RADIUS_M), key=lambda item: (item[1], item[0]))


def collect_articles(stop: Stop, area_tags: list[dict[str, str]], objects: list[NearbyObject], book: Book) -> Articles:
    lead_images: list[LeadImage] = []

    def use(found: Article, object_id: str | None = None) -> list[str]:
        fragment_ids = add_article(found, book, object_id)
        source_id = book.source_id(found.url)
        if found.image and source_id and all(image.source_id != source_id for image in lead_images):
            lead_images.append(LeadImage(found.image, source_id, object_id))
        return fragment_ids

    area_fragment_ids = []
    for tags in area_tags:
        title = _title_from_tags(tags)
        if title and (found := article(title)):
            area_fragment_ids += use(found)

    wanted: list[tuple[str, str | None]] = []
    for nearby in objects:
        if title := _title_from_tags({"wikipedia": nearby.wikipedia or "", "wikidata": nearby.wikidata or ""}):
            wanted.append((title, nearby.id))
        if nearby.named_after and (title := _entity_title(nearby.named_after)):
            wanted.append((title, nearby.id))
    nearby_titles = geosearch(stop.lat, stop.lon)
    object_by_title = {title: object_id for title, object_id in wanted}
    wanted += [(title, object_by_title.get(title)) for title, _ in nearby_titles[:FULL_TEXT_NEAREST]]

    fetched: set[str] = set()
    for title, object_id in wanted:
        if found := article(title):
            use(found, object_id)
            fetched.add(found.title)

    named_like_stop = article(stop.name)
    if (
        named_like_stop
        and named_like_stop.coordinates
        and distance_m(stop.lat, stop.lon, *named_like_stop.coordinates) <= STOP_ARTICLE_RADIUS_M
    ):
        use(named_like_stop)
        fetched.add(named_like_stop.title)

    return Articles(
        area_fragment_ids=area_fragment_ids,
        nearby=[NearbyArticle(title=title, distance_m=d, fetched=title in fetched) for title, d in nearby_titles],
        lead_images=lead_images,
    )


def _title_from_tags(tags: dict[str, str]) -> str | None:
    lang, _, title = tags.get("wikipedia", "").partition(":")
    if lang == "pl" and title:
        return title
    return _entity_title(tags["wikidata"]) if tags.get("wikidata") else None


def _entity_title(qid: str) -> str | None:
    found = wikidata.entity(qid)
    return found.wikipedia_title if found else None


def wikipedia_article(title: str, lang: str = "pl") -> tuple[list[Source], list[Fragment]]:
    book = Book()
    if found := article(title, lang):
        add_article(found, book)
    return book.sources, book.fragments


def wikipedia_search(query: str, lang: str = "pl", limit: int = 5) -> list[str]:
    response = cache.fetch(
        "GET",
        api(lang),
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": "0",
            "srlimit": str(limit),
            "format": "json",
            "formatversion": "2",
        },
    )
    return [item["title"] for item in response.json().get("query", {}).get("search", [])]
