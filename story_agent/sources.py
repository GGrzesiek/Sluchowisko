import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import quote, urlparse

from collector.schema import normalize_text
from story_agent.web import FetchError, fetch_json, fetch_text

WIKI_LICENSE = ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/")
FANDOM_LICENSE = ("CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0/")
DROP_SECTIONS = {
    "przypisy",
    "bibliografia",
    "linki zewnętrzne",
    "zobacz też",
    "uwagi",
    "źródła",
    "galeria",
    "references",
    "external links",
    "see also",
    "notes",
}
MAX_SECTION_CHARS = 4000
FILE_LINK = re.compile(r"\[\[(?:Plik|File|Grafika|Image|Kategoria|Category):[^\[\]]*(?:\[\[[^\]]*\]\][^\[\]]*)*\]\]")
HEADING = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$")

ALLOWED_DOMAINS = {
    "pl.wikipedia.org": ("encyclopedia", "Wikipedia", *WIKI_LICENSE),
    "warszawa.fandom.com": ("varsaviana", "Warszawikia", *FANDOM_LICENSE),
    "www.warszawa1939.pl": ("varsaviana", "Warszawa 1939", "CC BY-NC", None),
    "muzeumwarszawy.pl": ("institution", "Muzeum Warszawy", "© Muzeum Warszawy (parafraza i link)", None),
    "dzieje.pl": ("institution", "Dzieje.pl (Muzeum Historii Polski)", "© dzieje.pl (parafraza i link)", None),
    "zabytek.pl": ("official", "Narodowy Instytut Dziedzictwa", "© NID (parafraza i link)", None),
    "wolnelektury.pl": ("literature", "Wolne Lektury", "public domain", None),
}
LINK_ONLY_DOMAINS = {"www.warszawa1939.pl"}


@dataclass
class SourceDraft:
    type: str
    title: str
    publisher: str
    url: str
    license: str
    license_url: str | None
    retrieved_at: str
    author: str | None = None
    author_death_year: int | None = None
    sections: list[tuple[str | None, str]] = field(default_factory=list)
    derived: list[tuple[str, str, dict]] = field(default_factory=list)
    object_id: str | None = None


def wiki_api(lang: str = "pl") -> str:
    return f"https://{lang}.wikipedia.org/w/api.php"


def page_url(base: str, title: str) -> str:
    return f"{base}/wiki/{quote(title.replace(' ', '_'), safe='()_,:')}"


def split_sections(text: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    dropped_level: int | None = None
    for raw in text.splitlines():
        heading = HEADING.match(raw.strip())
        if heading:
            level = len(heading.group(1))
            name = heading.group(2).strip()
            if dropped_level is not None and level > dropped_level:
                continue
            dropped_level = level if name.lower() in DROP_SECTIONS else None
            if dropped_level is None:
                sections.append((name, []))
            continue
        if dropped_level is None:
            sections[-1][1].append(raw)
    result = []
    for name, lines in sections:
        paragraphs = [normalize_text(p) for p in lines if normalize_text(p)]
        chunk: list[str] = []
        for paragraph in paragraphs:
            if chunk and len(" ".join(chunk)) + len(paragraph) > MAX_SECTION_CHARS:
                result.append((name, " ".join(chunk)))
                chunk = []
            chunk.append(paragraph)
        if chunk:
            result.append((name, " ".join(chunk)))
    return result


def wikipedia_search(query: str, lang: str = "pl", limit: int = 5) -> list[str]:
    params = {"action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json"}
    data, _ = fetch_json(wiki_api(lang), params)
    return [hit["title"] for hit in data.get("query", {}).get("search", [])]


def wikipedia_geosearch(lat: float, lon: float, radius_m: int, limit: int = 50) -> list[tuple[str, int]]:
    params = {
        "action": "query",
        "list": "geosearch",
        "gscoord": f"{lat}|{lon}",
        "gsradius": radius_m,
        "gslimit": limit,
        "gsnamespace": 0,
        "format": "json",
    }
    data, _ = fetch_json(wiki_api(), params)
    hits = data.get("query", {}).get("geosearch", [])
    return sorted(((hit["title"], round(hit["dist"])) for hit in hits), key=lambda item: (item[1], item[0]))


def wikipedia_article(title: str, lang: str = "pl") -> SourceDraft | None:
    params = {
        "action": "query",
        "prop": "extracts|info",
        "explaintext": 1,
        "exsectionformat": "wiki",
        "inprop": "url",
        "redirects": 1,
        "titles": title,
        "format": "json",
    }
    data, retrieved_at = fetch_json(wiki_api(lang), params)
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), None)
    if not page or "missing" in page or not page.get("extract"):
        return None
    sections = split_sections(page["extract"])
    if not sections:
        return None
    return SourceDraft(
        type="encyclopedia",
        title=page["title"],
        publisher="Wikipedia",
        url=page_url(f"https://{lang}.wikipedia.org", page["title"]),
        license=WIKI_LICENSE[0],
        license_url=WIKI_LICENSE[1],
        retrieved_at=retrieved_at,
        sections=sections,
    )


def _claim_ids(entity: dict, prop: str) -> list[str]:
    values = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and "id" in value:
            values.append(value["id"])
    return values


def _claim_year(entity: dict, prop: str) -> str | None:
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and "time" in value:
            match = re.match(r"^[+-]?(\d{1,4})-", value["time"])
            if match:
                return str(int(match.group(1)))
    return None


def label(entity: dict, lang: str = "pl") -> str | None:
    for code in (lang, "en"):
        if code in entity.get("labels", {}):
            return entity["labels"][code]["value"]
    return None


def description(entity: dict, lang: str = "pl") -> str | None:
    for code in (lang, "en"):
        if code in entity.get("descriptions", {}):
            return entity["descriptions"][code]["value"]
    return None


def wikidata_entities(qids: list[str]) -> tuple[dict[str, dict], str]:
    entities: dict[str, dict] = {}
    retrieved_at = ""
    unique = sorted(set(qids))
    for start in range(0, len(unique), 50):
        params = {
            "action": "wbgetentities",
            "ids": "|".join(unique[start : start + 50]),
            "props": "labels|descriptions|claims|sitelinks",
            "languages": "pl|en",
            "sitefilter": "plwiki",
            "format": "json",
        }
        data, retrieved_at = fetch_json("https://www.wikidata.org/w/api.php", params)
        entities.update({qid: entity for qid, entity in data.get("entities", {}).items() if "missing" not in entity})
    return entities, retrieved_at


def plwiki_title(entity: dict) -> str | None:
    return entity.get("sitelinks", {}).get("plwiki", {}).get("title")


def wikidata_entity(qid: str, entities: dict[str, dict] | None = None, retrieved_at: str = "") -> SourceDraft | None:
    if entities is None or qid not in entities:
        entities, retrieved_at = wikidata_entities([qid])
    entity = entities.get(qid)
    if not entity:
        return None
    name = label(entity)
    if not name:
        return None
    values: dict[str, str] = {"qid": qid, "label": name}
    parts = [name]
    if desc := description(entity):
        values["description"] = desc
        parts[0] = f"{name} ({desc})"
    for prop, key, words in (
        ("P569", "born", "urodzenie"),
        ("P570", "died", "śmierć"),
        ("P571", "inception", "powstanie"),
    ):
        if year := _claim_year(entity, prop):
            values[key] = year
            parts.append(f"{words}: {year}")
    named_after = _claim_ids(entity, "P138")
    if named_after:
        names, _ = wikidata_entities(named_after)
        labels = [label(names[q]) for q in named_after if q in names and label(names[q])]
        if labels:
            values["named_after"] = ", ".join(labels)
            parts.append(f"nazwany na cześć: {values['named_after']}")
    text = normalize_text("; ".join(parts) + ".")
    return SourceDraft(
        type="encyclopedia",
        title=f"{name} ({qid})",
        publisher="Wikidata",
        url=f"https://www.wikidata.org/wiki/{qid}",
        license="CC0",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        retrieved_at=retrieved_at,
        derived=[(text, "wikidata_entity", values)],
    )


def _strip_templates(text: str) -> str:
    out, depth, i = [], 0, 0
    while i < len(text):
        pair = text[i : i + 2]
        if pair == "{{":
            depth += 1
            i += 2
        elif pair == "}}" and depth:
            depth -= 1
            i += 2
        else:
            if depth == 0:
                out.append(text[i])
            i += 1
    return "".join(out)


def wikitext_to_text(wikitext: str) -> str:
    text = re.sub(r"<!--.*?-->", "", wikitext, flags=re.S)
    text = re.sub(r"<ref[^>/]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = _strip_templates(text)
    text = re.sub(r"\{\|.*?\|\}", "", text, flags=re.S)
    text = re.sub(FILE_LINK, "", text)
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", text)
    text = re.sub(r"\[https?://\S+\]", "", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^[*#:;]+\s*", "", text, flags=re.M)
    return html.unescape(text)


FANDOM_API = "https://warszawa.fandom.com/pl/api.php"


def warszawikia_search(query: str, limit: int = 3) -> list[str]:
    params = {"action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json"}
    data, _ = fetch_json(FANDOM_API, params)
    return [hit["title"] for hit in data.get("query", {}).get("search", [])]


def warszawikia_article(title: str) -> SourceDraft | None:
    params = {"action": "parse", "page": title, "prop": "wikitext", "redirects": 1, "format": "json"}
    data, retrieved_at = fetch_json(FANDOM_API, params)
    parsed = data.get("parse")
    if not parsed:
        return None
    sections = split_sections(wikitext_to_text(parsed["wikitext"]["*"]))
    if not sections:
        return None
    return SourceDraft(
        type="varsaviana",
        title=parsed["title"],
        publisher="Warszawikia",
        url=page_url("https://warszawa.fandom.com/pl", parsed["title"]),
        license=FANDOM_LICENSE[0],
        license_url=FANDOM_LICENSE[1],
        retrieved_at=retrieved_at,
        sections=sections,
    )


class _Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.paragraphs: list[str] = []
        self._in = None
        self._buffer: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip += 1
        elif tag in ("p", "h1", "h2", "h3", "title", "li") and not self._skip:
            self._in = tag
            self._buffer = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header") and self._skip:
            self._skip -= 1
        elif tag == self._in:
            text = normalize_text("".join(self._buffer))
            if tag == "title":
                self.title = text
            elif len(text) > 40:
                self.paragraphs.append(text)
            self._in = None

    def handle_data(self, data):
        if self._in and not self._skip:
            self._buffer.append(data)


def fetch_allowed_url(url: str) -> SourceDraft | None:
    host = urlparse(url).netloc.lower()
    if host not in ALLOWED_DOMAINS:
        raise FetchError(f"{host} is not on the allowlist: {', '.join(sorted(ALLOWED_DOMAINS))}")
    kind, publisher, licence, licence_url = ALLOWED_DOMAINS[host]
    path_title = urlparse(url).path.rsplit("/", 1)[-1].replace("_", " ")
    if host == "pl.wikipedia.org":
        return wikipedia_article(path_title)
    if host == "warszawa.fandom.com":
        return warszawikia_article(path_title)
    if host in LINK_ONLY_DOMAINS:
        return SourceDraft(kind, path_title or url, publisher, url, licence, licence_url, "", sections=[])
    body, retrieved_at = fetch_text(url)
    parser = _Paragraphs()
    parser.feed(body)
    text = "\n".join(parser.paragraphs)
    sections = split_sections(text)
    return SourceDraft(
        kind, parser.title or path_title or url, publisher, url, licence, licence_url, retrieved_at, sections=sections
    )


ACCEPTED_LICENCE = re.compile(r"^(cc0|cc[ -]by|public domain|pd\b|pd-)", re.I)


def commons_images(lat: float, lon: float, radius_m: int, limit: int = 30) -> list[dict]:
    params = {
        "action": "query",
        "generator": "geosearch",
        "ggscoord": f"{lat}|{lon}",
        "ggsradius": radius_m,
        "ggslimit": limit,
        "ggsnamespace": 6,
        "prop": "imageinfo|coordinates",
        "codistancefrompoint": f"{lat}|{lon}",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1600,
        "format": "json",
    }
    data, _ = fetch_json("https://commons.wikimedia.org/w/api.php", params)
    images = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})

        def value(key, meta=meta):
            raw = meta.get(key, {}).get("value") or ""
            return normalize_text(html.unescape(re.sub(r"<[^>]+>", " ", str(raw)))) or None

        licence = value("LicenseShortName")
        if not licence or not ACCEPTED_LICENCE.match(licence) or re.search(r"\bND\b", licence.upper()):
            continue
        coords = (page.get("coordinates") or [{}])[0]
        year = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", value("DateTimeOriginal") or "")
        images.append(
            {
                "title": page["title"],
                "url": (info.get("descriptionurl") or "").replace(" ", "%20") or None,
                "thumb": info.get("thumburl") or info.get("url"),
                "caption": value("ImageDescription") or "Źródło: Wikimedia Commons",
                "author": value("Artist"),
                "year": year.group(1) if year else None,
                "license": licence,
                "license_url": value("LicenseUrl"),
                "dist": coords.get("dist", 0),
            }
        )
    return sorted(images, key=lambda image: (image["dist"], image["title"]))
