import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from collector import cache, commons
from collector.schema import RADIUS_M, Image, ImageKind, Stop

WMS = "https://wms.um.warszawa.pl/serwis"
WMS_CAPABILITIES = f"{WMS}?SERVICE=WMS&REQUEST=GetCapabilities"
WMS_LICENSE = "Usługa WMS m.st. Warszawy: AccessConstraints „None whatsoever”, Fees „None”"
MAP_SIZE_PX = 1024
MAX_PHOTOS = 15
MAX_LEAD_PHOTOS = 10


@dataclass(frozen=True)
class CityMap:
    layer: str
    kind: ImageKind
    year: str
    title: str


MAPS = (
    CityMap("RASTER_FOTOPLAN_1935", "photo_map_1935", "1935", "Fotoplan Warszawy 1935"),
    CityMap("RASTER_PLAN_1939", "plan_1939", "1939", "Plan Warszawy 1939"),
    CityMap("RASTER_ORTOFOTO_1945", "photo_map_1945", "1945", "Fotoplan Warszawy 1945"),
    CityMap("RASTER_FOTOPLAN_2021", "orthophoto", "2021", "Fotoplan Warszawy 2021"),
)


@dataclass(frozen=True)
class LeadImage:
    file_name: str
    source_id: str
    object_id: str | None


def map_caption(city_map: CityMap, stop: Stop) -> str:
    return f"{city_map.title}, okolice przystanku {stop.name}"


def map_params(city_map: CityMap, stop: Stop) -> dict[str, str]:
    half_lat = RADIUS_M / 111_320
    half_lon = half_lat / math.cos(math.radians(stop.lat))
    corners = (stop.lon - half_lon, stop.lat - half_lat, stop.lon + half_lon, stop.lat + half_lat)
    return {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetMap",
        "LAYERS": city_map.layer,
        "STYLES": "",
        "CRS": "CRS:84",
        "BBOX": ",".join(f"{value:.6f}" for value in corners),
        "WIDTH": str(MAP_SIZE_PX),
        "HEIGHT": str(MAP_SIZE_PX),
        "FORMAT": "image/jpeg",
    }


def write_images(group_id: str, images: list[tuple[Image, bytes]], root: Path) -> None:
    folder = root / group_id
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for image, data in images:
        (folder / f"{image.id}.jpg").write_bytes(data)


def collect_images(stop: Stop, lead_images: list[LeadImage]) -> list[tuple[Image, bytes]]:
    images: list[tuple[Image, bytes]] = []

    def save(data: bytes, **fields) -> None:
        image_id = f"i{len(images) + 1}"
        images.append((Image(id=image_id, file=f"out/images/{stop.group_id}/{image_id}.jpg", **fields), data))

    for city_map in MAPS:
        params = map_params(city_map, stop)
        save(
            cache.fetch_image(WMS, params=params),
            kind=city_map.kind,
            url=f"{WMS}?{urlencode(params)}",
            caption=map_caption(city_map, stop),
            author=None,
            year=city_map.year,
            license=WMS_LICENSE,
            license_url=WMS_CAPABILITIES,
            non_commercial=False,
            source_id=None,
            object_id=None,
        )

    seen: set[str] = set()
    lead = [(f"File:{image.file_name}", image.source_id, image.object_id) for image in lead_images]
    nearby = [(title, None, None) for title in commons.geosearch(stop.lat, stop.lon)]
    for candidates, limit in ((lead, MAX_LEAD_PHOTOS), (nearby, MAX_PHOTOS)):
        for title, source_id, object_id in candidates:
            if len(seen) >= limit:
                break
            found = commons.photo(title)
            if not found or found.title in seen:
                continue
            seen.add(found.title)
            save(
                cache.fetch_image(found.file_url),
                kind="photo",
                url=found.page_url,
                caption=found.caption,
                author=found.author,
                year=found.year,
                license=found.license,
                license_url=found.license_url,
                non_commercial=found.non_commercial,
                source_id=source_id,
                object_id=object_id,
            )
    return images
