from pathlib import Path

from collector import city, warszawikia, wikidata, wikipedia
from collector.check import CheckError, check
from collector.images import collect_images, write_images
from collector.osm import load_area
from collector.schema import Area, CollectedStop, StreetName, save
from collector.sources import Book
from collector.stops import load_stop


def collect(group_id: str, root: Path = Path("out/collected"), images_root: Path = Path("out/images")) -> Path:
    stop = load_stop(group_id)
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
