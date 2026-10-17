import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from collector import city, warszawikia, wikidata, wikipedia
from collector.cache import REPO_ROOT, FetchError
from collector.check import CheckError, check
from collector.images import collect_images, write_images
from collector.osm import OverpassError, load_area
from collector.schema import Area, CollectedStop, Stop, StreetName, save
from collector.sources import Book
from collector.stops import UnknownStopGroup, load_stop, setup_backend

DEMO_LINES = REPO_ROOT / "data" / "demo_lines.json"
EXPECTED_ERRORS = (UnknownStopGroup, OverpassError, FetchError, CheckError)


def collect(group_id: str, root: Path = Path("out/collected"), images_root: Path = Path("out/images")) -> Path:
    return collect_stop(load_stop(group_id), root, images_root)


def collect_stop(stop: Stop, root: Path = Path("out/collected"), images_root: Path = Path("out/images")) -> Path:
    group_id = stop.group_id
    area = load_area(stop.lat, stop.lon)
    book = Book()
    objects = wikidata.enrich(area.objects, book)
    articles = wikipedia.collect_articles(stop, [area.district_tags, area.neighbourhood_tags], objects, book)
    warszawikia.collect_articles(stop, [o for o in objects if o.id in area.street_ids], book)
    for fact in city.facts(stop):
        source_id = book.add_source(
            type="city_data",
            title=fact.title,
            publisher="m.st. Warszawa",
            url=fact.url,
            license=fact.license,
            license_url=fact.license_url,
            retrieved_at=fact.retrieved_at,
        )
        book.add_derived(source_id, fact.template, fact.values)
    images = collect_images(stop, articles.lead_images)
    collected = CollectedStop(
        stop=stop,
        area=Area(
            district=area.district,
            neighbourhood=area.neighbourhood,
            fragment_ids=articles.area_fragment_ids,
            street_names=[
                StreetName(name=o.name, object_id=o.id, named_after=o.named_after, distance_m=o.distance_m)
                for o in objects
                if o.id in area.street_ids
            ],
            nearby_articles=articles.nearby,
        ),
        objects=objects,
        sources=book.sources,
        fragments=book.fragments,
        images=[image for image, _ in images],
    )
    if problems := check(collected):
        raise CheckError(f"Stop group {group_id} failed the checks:\n" + "\n".join(problems))
    write_images(group_id, images, images_root)
    return save(collected, root)


def collect_many(
    group_ids: list[str],
    jobs: int,
    root: Path = Path("out/collected"),
    images_root: Path = Path("out/images"),
) -> Iterator[tuple[str, Path | Exception]]:
    setup_backend()
    stops = {}
    for group_id in group_ids:
        try:
            stops[group_id] = load_stop(group_id)
        except UnknownStopGroup as error:
            yield group_id, error
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        running = {pool.submit(collect_stop, stop, root, images_root): group_id for group_id, stop in stops.items()}
        for done in as_completed(running):
            try:
                yield running[done], done.result()
            except EXPECTED_ERRORS as error:
                yield running[done], error


def demo_groups() -> list[str]:
    lines = json.loads(DEMO_LINES.read_text(encoding="utf-8"))["lines"]
    found: list[str] = []
    for line in lines:
        for direction in line["directions"]:
            for stop in direction["stops"]:
                if stop["group_id"] not in found:
                    found.append(stop["group_id"])
    return found
