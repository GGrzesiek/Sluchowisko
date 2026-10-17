# Facts collector

A deterministic script, without any AI, that gathers everything known about the surroundings of one stop group
(zespół przystankowy) and writes it as one JSON file. The stories agent reads that file and writes stories from it.

```
python -m collector 5086
```

This writes `out/collected/5086.json` and prints its path. From Python: `collect("5086")` returns the same path. The
file always matches `CollectedStop` in `schema.py`: it is written with `save` and read back with `load`.

## Setup

The collector reads stops from the backend's stop table, so the table has to be filled first:

```
cp .env.example .env      # set ZTM_API_KEY
python manage.py migrate
python manage.py import_stops
```

## What it collects

- **Stop group**: every pole with the given `zespol` in the backend's stop table (imported from
  `get_ztm_przystanki_komunikacji_miejskiej`). The group's position is the mean of its poles' coordinates, and every
  distance in the file is measured from it. The collector reads the table directly through Django instead of calling
  the backend over HTTP, so no server has to be running.
- **Area** (OpenStreetMap, through Overpass):
  - district: the administrative boundary of level 9 that contains the stop (level 8 or 7 outside Warsaw);
  - neighbourhood: the boundary of level 10 that contains the stop (the city's own MSI areas, e.g. Powązki). Where
    there is none, the `place=neighbourhood` or `place=quarter` area that contains the stop, or the nearest such place
    within 1 km;
  - streets: every named street within 400 m, with segments of the same name merged into one object at the shortest
    distance. Each keeps its Wikidata and Wikipedia links, its patron (`name:etymology:wikidata`) and old names.
- **Objects within 400 m** (OpenStreetMap): everything with `historic`, `memorial`, `heritage`, `ref:nid` or
  `name:etymology:wikidata`, and buildings, amenities, tourist sites, parks and land use (e.g. cemeteries) that have a
  Wikidata link. Objects without a name are left out. The distance is to the nearest point of the object's outline,
  0 when the stop is inside it. All objects, streets included, are sorted by distance and numbered `o1`, `o2`, ….
- **Wikidata** for every object with a Wikidata link and for every patron: the Polish label and description, what the
  name comes from (P138), heritage status (P1435), inception (P571), dates of birth and death (P569, P570) and the
  number of Wikipedias with an article about it. When a street has no `name:etymology:wikidata` tag, its patron comes
  from the street's own P138. Each item is one source; each fact is one fragment.

## Fragments from data

Most fragments are text copied from the source. Facts that come from data, such as Wikidata claims, are written as one
sentence from a fixed template in `sources.py`, e.g. `{label} – data powstania: {inception}.` Such a fragment has
`"derived": true`, the template's id and the values put into it, so its text can be rebuilt from the cached response.
Dates keep only the precision Wikidata gives: `1806`, `03.1806` or `7.03.1806`.

## Functions for the stories agent

- `wikidata_entity(qid)` in `wikidata.py` returns one source and its fragments for any Wikidata item.

## Cache

Every response is stored under `cache/<host>/` and reused, so a second run gives the same file and works without a
network. A cached entry keeps the request, the response body and the date it was downloaded. Request headers, and
with them API keys, are never stored. Delete a file from `cache/` to download it again.

Requests send a `User-Agent` with the project's address, go one at a time with at least a second between requests to
the same server, and retry a busy server (HTTP 429, 502, 503, 504) after 10, 30 and 90 seconds. Overpass has two
servers; whichever answers first is cached.
