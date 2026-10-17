from urllib.parse import urlencode

from collector import cache, city, commons, images, warszawikia, web, wikidata, wikipedia
from collector.schema import CollectedStop, Fragment, Image, Source, Stop, normalize_text
from collector.sources import TEMPLATES, render

CACHED_TEXT = {
    "Wikipedia": wikipedia.cached_text,
    "Warszawikia": warszawikia.cached_text,
    **{publisher: web.cached_text for publisher in web.PUBLISHERS},
}


class CheckError(ValueError):
    pass


def check(collected: CollectedStop) -> list[str]:
    sources = {source.id: source for source in collected.sources}
    problems = []
    with cache.offline():
        try:
            city_facts = [(fact.template, fact.values) for fact in city.facts(collected.stop)]
        except cache.FetchError:
            city_facts = []
        for fragment in collected.fragments:
            try:
                problem = _check(fragment, sources[fragment.source_id], city_facts)
            except cache.FetchError as error:
                problem = f"the source is not in the cache ({error})"
            if problem:
                problems.append(f"{fragment.id}: {problem}")
        for image in collected.images:
            try:
                problem = _check_image(image, collected.stop)
            except cache.FetchError as error:
                problem = f"the image is not in the cache ({error})"
            if problem:
                problems.append(f"{image.id}: {problem}")
    return problems


def _check_image(image: Image, stop: Stop) -> str | None:
    if image.kind == "photo":
        found = commons.photo(commons.title_from_page_url(image.url))
        if not found:
            return "the cached Commons file is not an accepted photo"
        expected = {
            "url": found.page_url,
            "caption": found.caption,
            "author": found.author,
            "year": found.year,
            "license": found.license,
            "license_url": found.license_url,
        }
        cache.fetch_image(found.file_url)
    else:
        city_map = next(m for m in images.MAPS if m.kind == image.kind)
        params = images.map_params(city_map, stop)
        expected = {
            "url": f"{images.WMS}?{urlencode(params)}",
            "caption": images.map_caption(city_map, stop),
            "author": None,
            "year": city_map.year,
            "license": images.WMS_LICENSE,
            "license_url": images.WMS_CAPABILITIES,
        }
        cache.fetch_image(images.WMS, params=params)
    actual = {key: getattr(image, key) for key in expected}
    if actual != expected:
        changed = sorted(key for key in expected if actual[key] != expected[key])
        return f"{', '.join(changed)} do not match the cached source"
    return None


def _check(fragment: Fragment, source: Source, city_facts: list[tuple[str, dict]]) -> str | None:
    if fragment.derived:
        if fragment.template not in TEMPLATES:
            return f"unknown template {fragment.template}"
        if render(fragment.template, fragment.values) != fragment.text:
            return "the text is not what its template gives"
        if fragment.template.startswith("wikidata."):
            return wikidata.check_values(source.url, fragment.template, fragment.values)
        if fragment.template.startswith("city."):
            if (fragment.template, fragment.values) in city_facts:
                return None
            return "the values are not what the cached city data gives"
        return f"no value check for {fragment.template}"

    if source.publisher not in CACHED_TEXT:
        return f"no quote check for {source.publisher}"
    raw = CACHED_TEXT[source.publisher](source.url)
    if raw is None:
        return "the source is not in the cache"
    if fragment.text not in normalize_text(raw):
        return "the text is not in the cached source"
    return None
