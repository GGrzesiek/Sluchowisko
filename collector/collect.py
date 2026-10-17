from pathlib import Path

from collector import wikidata
from collector.osm import load_area
from collector.schema import Area, CollectedStop, StreetName, save
from collector.sources import Book
from collector.stops import load_stop


def collect(group_id: str, root: Path = Path("out/collected")) -> Path:
    stop = load_stop(group_id)
    area = load_area(stop.lat, stop.lon)
    book = Book()
    objects = wikidata.enrich(area.objects, book)
    collected = CollectedStop(
        stop=stop,
        area=Area(
            district=area.district,
            neighbourhood=area.neighbourhood,
            fragment_ids=[],
            street_names=[
                StreetName(name=o.name, object_id=o.id, named_after=o.named_after, distance_m=o.distance_m)
                for o in objects
                if o.id in area.street_ids
            ],
            nearby_articles=[],
        ),
        objects=objects,
        sources=book.sources,
        fragments=book.fragments,
        images=[],
    )
    return save(collected, root)
