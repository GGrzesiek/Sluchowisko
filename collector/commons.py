import html
import re
from dataclasses import dataclass
from urllib.parse import unquote

from collector import cache
from collector.schema import RADIUS_M, normalize_text

API = "https://commons.wikimedia.org/w/api.php"
THUMB_WIDTH = 1280
MAX_GEOSEARCH = 50
HIDDEN = re.compile(r"<(\w+)[^>]*display:\s*none[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
BREAK = re.compile(r"<(br|p|div|li)\b[^>]*>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
YEAR = re.compile(r"\b(1\d{3}|20\d{2})\b")
NO_DERIVATIVES = re.compile(r"\bND\b")
NON_COMMERCIAL = re.compile(r"\bNC\b")


@dataclass(frozen=True)
class Photo:
    title: str
    page_url: str
    file_url: str
    caption: str
    author: str | None
    year: str | None
    license: str
    license_url: str | None

    @property
    def non_commercial(self) -> bool:
        return bool(NON_COMMERCIAL.search(self.license.upper()))


def plain(value: str | None) -> str:
    return normalize_text(html.unescape(TAG.sub("", BREAK.sub(" ", HIDDEN.sub("", value or "")))))


def license_name(short_name: str) -> str | None:
    name = plain(short_name)
    upper = name.upper()
    if NO_DERIVATIVES.search(upper):
        return None
    if upper.startswith(("CC0", "CC BY")):
        return name
    if upper.startswith(("PUBLIC DOMAIN", "PD")):
        return "public domain"
    return None


def _info_params(title: str) -> dict[str, str]:
    return {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|mime|thumbmime|extmetadata",
        "iiurlwidth": str(THUMB_WIDTH),
        "iiextmetadatalanguage": "pl",
        "format": "json",
        "formatversion": "2",
    }


def _page(title: str) -> dict | None:
    pages = cache.fetch("GET", API, params=_info_params(title)).json().get("query", {}).get("pages", [])
    return pages[0] if pages and pages[0].get("imageinfo") else None


def photo(title: str) -> Photo | None:
    title = title.replace("_", " ")
    page = _page(title)
    if page and page["title"] != title:
        page = _page(page["title"])
    if not page:
        return None
    info = page["imageinfo"][0]
    meta = {key: value.get("value") for key, value in info.get("extmetadata", {}).items()}
    if (info.get("thumbmime") or info.get("mime")) != "image/jpeg" or str(meta.get("NonFree", "")).lower() == "true":
        return None
    license = license_name(meta.get("LicenseShortName") or "")
    if not license:
        return None
    year = YEAR.search(plain(meta.get("DateTimeOriginal")))
    return Photo(
        title=page["title"],
        page_url=info["descriptionurl"],
        file_url=info.get("thumburl") or info["url"],
        caption=plain(meta.get("ImageDescription")) or "Źródło: Wikimedia Commons",
        author=plain(meta.get("Artist")) or None,
        year=year.group(1) if year else None,
        license=license,
        license_url=meta.get("LicenseUrl") or None,
    )


def title_from_page_url(url: str) -> str:
    return unquote(url.rsplit("/wiki/", 1)[-1]).replace("_", " ")


def geosearch(lat: float, lon: float) -> list[str]:
    response = cache.fetch(
        "GET",
        API,
        params={
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{lat:.6f}|{lon:.6f}",
            "gsradius": str(RADIUS_M),
            "gsnamespace": "6",
            "gslimit": str(MAX_GEOSEARCH),
            "format": "json",
            "formatversion": "2",
        },
    )
    found = response.json().get("query", {}).get("geosearch", [])
    return [item["title"] for item in sorted(found, key=lambda item: (item["dist"], item["title"]))]
