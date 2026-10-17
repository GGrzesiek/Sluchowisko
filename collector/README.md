# Facts collector

A deterministic script, without any AI, that gathers everything known about the surroundings of one stop group
(zespół przystankowy) and writes it as one JSON file. The stories agent reads that file and writes stories from it.

```
python -m collector 5086                 # one stop group
python -m collector 5086 5087 5159       # several stop groups
python -m collector --demo               # all 50 stop groups of the demo lines
python -m collector --demo --jobs 6      # more stop groups at once (default 4)
```

Each stop group gets `out/collected/<group_id>.json`, and the command prints its path. From Python: `collect("5086")`
returns the same path, and `collect_many(group_ids, jobs)` yields each group id with its path or error as soon as it is
done. A stop group that fails does not stop the others. Every file matches `CollectedStop` in `schema.py`: it is
written with `save` and read back with `load`.

Several stop groups are collected at once, but every server still gets one request at a time: while one stop group
waits for Overpass, another reads Wikipedia. When two stop groups need the same response (a district's flat prices,
a year of the participatory budget), it is downloaded once. The files are the same as when the stop groups are collected
one by one. Overpass sets the pace: one query per stop group, often 30 seconds.

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

- **Polish Wikipedia** (CC BY-SA 4.0), as plain text:

  - the articles of the district and the neighbourhood, listed in `area.fragment_ids`;
  - the article of every object and every patron (from the `wikipedia` tag, or from Wikidata);
  - every article within 400 m (`area.nearby_articles`, up to 50, sorted by distance), of which the 15 nearest are
    fetched in full and marked `"fetched": true`;
  - an article with the same title as the stop, only when its coordinates are within 1 km of the stop. A stop called
    Okopowa must not get the article about the Okopowa hill in the Sudetes.

  Each section is one fragment, split at paragraph boundaries when it is longer than 4000 characters. "Przypisy",
  "Bibliografia", "Linki zewnętrzne" and "Zobacz też" are left out. Redirects are followed, and the source is always
  the article's final title. Disambiguation pages are skipped.

- **Warszawikia** (warszawa.fandom.com, licence from the wiki's own `rightsinfo`: CC-BY-SA):

  - the article about the stop group, used only when its wikitext names the same group id, e.g.
    `{{Zespół|Cmentarz Żydowski|5086}}`;
  - the article about every street within 400 m, used only when its title is "Ulica", "Aleja", "Plac", "Rondo",
    "Skwer" or "Most" followed by the OpenStreetMap name or its ending ("Ulica Anielewicza" for "Mordechaja
    Anielewicza").

  The text comes from the rendered page, because the wikitext is full of templates that produce words, e.g.
  `{{ulicy|Okopow|a}}ej` gives "ulicy Okopowej". `html_text.py` turns the page into plain text with its section
  headings and leaves out the infobox, images, gallery, table of contents, references and the disambiguation note.

- **Images**, saved as `out/images/<group_id>/<image_id>.jpg`:

  - four city maps from the WMS service of m.st. Warszawa, all of the same 800 × 800 m square around the stop at
    1024 px: the 1935 photo map (`RASTER_FOTOPLAN_1935`), the 1939 plan (`RASTER_PLAN_1939`), the 1945 aerial photo
    (`RASTER_ORTOFOTO_1945`) and the 2021 photo map (`RASTER_FOTOPLAN_2021`). Their captions come from a fixed
    template: "Fotoplan Warszawy 1935, okolice przystanku Cm. Żydowski". The service states no licence; its
    capabilities say `AccessConstraints: None whatsoever` and `Fees: None`, and the image keeps exactly that
    statement;
  - up to 15 photos from Wikimedia Commons: first the lead images of the fetched Wikipedia articles (at most 10,
    linked to the article's source and object), then photos taken within 400 m, nearest first. Only JPEG files with a
    licence are used: public domain, CC0, CC BY, CC BY-SA, and CC BY-NC marked as non-commercial. Files with ND
    licences are left out. Caption, author and year come from the file's description on Commons, with HTML removed;
    a file without a description gets "Źródło: Wikimedia Commons". Photos are downloaded 1280 px wide.

- **City data** (m.st. Warszawa), each fact as one sentence from a template:

  - flat prices from the property price register (`get_bgk_rcn` on dane.um.warszawa.pl): the median price per m² of
    flats sold on the open market in 2025 within 400 m of the stop, with the number of flats. The register is queried
    for every district that the 400 m square touches (district boundaries from the city WFS layer
    `GRANICE_DZIELNIC`), because the API filters by district, not by distance. The API accepts district names
    only without Polish letters, spaces or hyphens (`PragaPolnoc`) and answers HTTP 500 to any other spelling. With fewer than 5 flats there is no
    fact: a median of one or two sales says nothing and could point to a single buyer;
  - completed participatory budget projects 2015–2026 (`get_cks_budzet_obywatelski`) whose location or any of its
    pins is within 400 m: year, title, distance and cost. Each project is its own source, linked to its page on
    bo.um.warszawa.pl. The names of the people who submitted projects are in the data and are never copied;
  - the 3 trees with the largest trunk girth within 400 m, from the city's tree register (WFS layer
    `ZIELEN_DRZEWA`, one request for the whole square, split only when the server's limit of 1000 trees is reached): species, girth, height, distance and the year of the record. A tree with several trunks is
    ranked by its largest one, and its girth is kept as the register gives it, e.g. `55, 100`.

  Data from dane.um.warszawa.pl is not protected by copyright and may be reused without restrictions (portal terms,
  §8). The WMS and WFS services state no licence, only `AccessConstraints`; each source keeps that statement.
  Coordinates in the city's PL-2000 grid (zone 7) are converted in `pl2000.py`.

## Checks

Before a file is saved, every fragment is checked against the cache, with the network switched off:

- a fragment copied from a source must appear word for word in the cached response, after the same normalisation
  (Unicode NFC, runs of whitespace collapsed to one space);
- a fragment built from a template must be exactly what its template gives with its values, and the values must be
  what the same computation gives on the cached response;
- every image must be in the cache, and its address, caption, author, year and licence must be what the cached
  Commons description or the map template gives.

A file that fails a check is not saved, and neither are its images: the command prints what failed and why.

## Fragments from data

Most fragments are text copied from the source. Facts that come from data, such as Wikidata claims, are written as one
sentence from a fixed template in `sources.py`, e.g. `{label} – data powstania: {inception}.` Such a fragment has
`"derived": true`, the template's id and the values put into it, so its text can be rebuilt from the cached response.
Dates keep only the precision Wikidata gives: `1806`, `03.1806` or `7.03.1806`. Numbers are written with a space
between thousands: `16 216 zł`.

## Functions for the stories agent

They use the same cache and return sources and fragments in the same format, numbered from `s1`:

- `wikipedia_article(title, lang="pl")` in `wikipedia.py`: one article, one fragment per section;
- `wikipedia_search(query, lang="pl", limit=5)` in `wikipedia.py`: article titles only;
- `wikidata_entity(qid)` in `wikidata.py`: one Wikidata item and its facts;
- `warszawikia_article(title)` in `warszawikia.py`: one Warszawikia article, one fragment per section;
- `fetch_allowed_url(url)` in `web.py`: one page from a site on the allowlist. Wikipedia and Warszawikia links go to
  the functions above. Every other site has a fixed source type and licence; any other address is refused.

| Site                | Type        | Licence                                            |
| ------------------- | ----------- | -------------------------------------------------- |
| www.warszawa1939.pl | varsaviana  | CC BY-NC (stated on every page)                    |
| zabytek.pl          | official    | CC BY-NC-ND 3.0 (portal terms, NID descriptions)   |
| dzieje.pl           | institution | © PAP, all rights reserved                        |
| muzeumwarszawy.pl   | institution | all rights reserved (no licence stated)            |
| wolnelektury.pl     | literature  | public domain or CC BY-SA 3.0, depending on a work |

Pages with a non-commercial or all-rights-reserved licence are context for the agent: a story retells their facts in
its own words and links to them, and never copies their text.

## Random stops

```
python -m collector.sample 10 --seed 20261017
```

Takes the live positions of all buses and trams from the city API (only readings from the last 5 minutes, because the
API also returns stale ones), shuffles the vehicles with the given seed, and collects the stop group nearest to each
vehicle, within 300 m, until 10 groups are done. A vehicle without a stop group that close is skipped. Every file
passes the same checks as a single run; a stop with little around it gives a file with fewer items.

The backend's `ride/<vehicle>/stops/` endpoint would give the current stop by route, but it needs the routes of every
line, built from the timetable of every pole; the nearest stop group to the vehicle's position needs only the stop
table.

## Cache

Every response is stored under `cache/<host>/` and reused, so a second run gives the same file and works without a
network. A cached entry keeps the request, the response body and the date it was downloaded. Request headers, and
with them API keys, are never stored. Delete a file from `cache/` to download it again.

Requests send a `User-Agent` with the project's address and go one at a time. Wikipedia, Wikidata, Wikimedia Commons and Warszawikia get the next request as soon as the previous one is answered, as their API guidelines allow; other servers get at least a second between requests, and www.warszawa1939.pl 10 seconds, as its `robots.txt` asks. A busy server (HTTP 429, 502, 503, 504) is retried after 10, 30 and 90 seconds. Overpass has two servers; whichever answers first is cached.

## Sources

✅ collected automatically · 🖐️ by hand or through `fetch_allowed_url`, only for chosen places · ❌ not worth it ·
⛔ not possible

| Source                                                             | Decision | Why                                                                                                                                                                            |
| ------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| OpenStreetMap (Overpass)                                           | ✅       | Area, streets with patrons and old names, monuments, memorials and buildings within 400 m.                                                                                     |
| Wikipedia (pl)                                                     | ✅       | District, neighbourhood, objects, patrons and every article within 400 m.                                                                                                      |
| Wikidata                                                           | ✅       | Patrons, inception, heritage status, life dates.                                                                                                                               |
| Warszawikia                                                        | ✅       | The stop group's own article, matched by group id, and street articles.                                                                                                        |
| Wikimedia Commons                                                  | ✅       | Lead images of the articles and photos taken within 400 m, with licence and caption from Commons.                                                                              |
| City maps (WMS): photo maps 1935, 1945, 2021, plan 1939            | ✅       | One image per era for the same 800 × 800 m square.                                                                                                                             |
| Flat prices, register of property prices (dane.um)                 | ✅       | Median price per m² within 400 m.                                                                                                                                              |
| Participatory budget (dane.um)                                     | ✅       | Completed projects within 400 m, 2015–2026, without the names of the people who submitted them.                                                                                |
| Tree register (city WFS `ZIELEN_DRZEWA`)                           | ✅       | The 3 largest trees within 400 m. Replaces the trees from the old API.                                                                                                         |
| Streets existing in 1939 (WMS `HISTORIA_ULICE_1939`)               | ⛔       | Only a picture: there is no WFS layer and point queries return nothing, so the names cannot be read as data. The 1939 plan image shows them.                                   |
| Historic city boundaries 1916–1992 (WMS `HISTORIA_GRANICA_*`)      | ⛔       | Same as the 1939 streets: WMS only.                                                                                                                                            |
| Lindley plans, plan 1956, other photo maps                         | ❌       | One map per era is enough for a story.                                                                                                                                         |
| WFS cemeteries, squares, green areas                               | ❌       | OpenStreetMap and Wikidata already have them.                                                                                                                                  |
| Road investments (old API)                                         | ⛔       | The old API answers "Nieautoryzowany dostęp do danych", also without a key.                                                                                                    |
| Street naming resolutions (BIP, Zespół Nazewnictwa Miejskiego)     | 🖐️       | No search to query by street; by hand for chosen streets.                                                                                                                      |
| NID heritage register                                              | ❌       | No data with locations: the INSPIRE service returns 404, the zabytek.pl API fails, and dane.gov.pl has statistics only. Heritage status comes from Wikidata and OpenStreetMap. |
| zabytek.pl pages                                                   | 🖐️       | Through `fetch_allowed_url`; descriptions are CC BY-NC-ND 3.0.                                                                                                                 |
| Muzeum Warszawy                                                    | 🖐️       | Through `fetch_allowed_url`; no licence stated, so context only. Public-domain photos by hand.                                                                                 |
| warszawa1939.pl                                                    | 🖐️       | Through `fetch_allowed_url`, 10 s between requests as its `robots.txt` asks; CC BY-NC. The right address needs judgement, so the agent fetches it.                             |
| dzieje.pl                                                          | 🖐️       | Through `fetch_allowed_url`; © PAP, context only.                                                                                                                             |
| Wolne Lektury                                                      | 🖐️       | Through `fetch_allowed_url`, for a text that describes a place.                                                                                                                |
| MusicBrainz                                                        | 🖐️       | Songs about a place by hand: title, artist and link only, never lyrics.                                                                                                        |
| Biblioteka Narodowa                                                | ❌       | No working endpoint found, low value for single stops.                                                                                                                         |
| Legendy and Piosenki warszawskie anthologies                       | 🖐️       | Link only.                                                                                                                                                                     |
| warszawskie-mozaiki.pl, iwaw.pl, wsiewarszawy.pl and similar       | 🖐️       | No API; link and our own words only.                                                                                                                                           |
| Local portals and press                                            | 🖐️       | Link and one or two sentences in our own words.                                                                                                                                |
| Local societies, blogs                                             | 🖐️       | A blog is a weak source: used only with a second source.                                                                                                                       |
| Polona, Europeana, Mazowiecka Biblioteka Cyfrowa, Kronika Warszawy | ❌       | Scans need reading and judgement; by hand only if a story needs them.                                                                                                          |
| NAC, szukajwarchiwach.gov.pl                                       | 🖐️       | Pre-war photos only, by hand.                                                                                                                                                  |
| fotopolska.eu                                                      | ⛔       | No API, licence per photo, often ND.                                                                                                                                           |
| Zapisy Terroru, Tablice Pamięci, 1944.pl, getto.pl, IPN            | 🖐️       | Link only. Victims' names are never extracted automatically.                                                                                                                   |
| Wikidata filming locations (P915)                                  | 🖐️       | Through `wikidata_entity` when a story needs it.                                                                                                                               |
| IMDb filming locations                                             | ⛔       | Its terms forbid scraping.                                                                                                                                                     |
| Filmoteka Narodowa, kronika.gov.pl                                 | 🖐️       | Link only.                                                                                                                                                                     |
| Freesound, Musopen                                                 | 🖐️       | Sound is chosen with the voice-over, licence checked per file.                                                                                                                 |
