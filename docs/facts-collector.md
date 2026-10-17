# Facts collector: what it produces for the stories agent

Status: **draft for agreement** between Grzesiek (collector, #9) and Kuba (stories agent, #8, #11–13).
Nothing here is final until we both agree. Change it in a PR like any other contract.

## 1. Role and boundary

The collector is a deterministic script. No LLM, no judgement. For every stop group on the demo lines it gathers
everything that can be queried **by coordinates or by ID** and writes one JSON file the agent reads.

The rule for "collector or agent?":

- If the query can be written without knowing the history of the place ("objects within 400 m of X", "the Wikipedia
  article linked from this OSM way"), the **collector** does it.
- If you first have to read something to know what to look for ("this text mentions St. Lazarus Hospital, let's find
  out what happened to it"), the **agent** does it, using the collector's fetch functions as tools (section 8).

Pipeline position:

```
route table (#32) ─▶ collector ─▶ out/collected/<group_id>.json + out/images/<group_id>/* ─▶ stories agent
```

## 2. Step 1: poles → stop groups

A **stop group** (zespół przystankowy) is all poles that share one `zespol` ID. The agent writes one story per group;
line and direction do not matter for the story.

1. Read all poles from `get_ztm_przystanki_komunikacji_miejskiej` (`zespol`, `slupek`, `nazwa_zespolu`, `szer_geo`,
   `dlug_geo`). Dedupe by `zespol` + `slupek`.
2. Group by `zespol`. **Do not group by name**: the same name can belong to different groups in different places.
3. Keep only groups served by the demo lines, according to the route table. Skip layover poles (the extra pole after
   a terminus is not a passenger stop).
4. Group position = mean of its poles' coordinates. Distances in the rest of this file are measured from this point.
5. From the route table, for every line, direction and main variant (`TP-*`) that serves the group, record the previous
   and next group and the travel time to each, in seconds.
6. `target_duration_s` = `min(45, max(15, shortest_travel_s - 10))`, where `shortest_travel_s` is the shortest travel
   time to any neighbouring group over all lines and directions. The 10 s margin covers the 10 s position refresh.
   Timetable times are in whole minutes, so this is approximate, which is fine for the POC.

Steps 5 and 6 depend on the route table (#32), which is route data, not facts. Until it exists, `routes` is an empty
list and `target_duration_s` is `null`; the collector still writes the file. When the route table is ready, the
collector fills both from it without changing anything else in the file. While `target_duration_s` is `null`, the
agent uses its own default length.

## 3. Step 2: the area

For each group:

- `district`: the Warsaw district containing the point (OSM `boundary=administrative`, `admin_level=9`).
- `neighbourhood`: the OSM `place=quarter` or `place=neighbourhood` that contains the point or is nearest within
  1 km. `null` if none.
- The Polish Wikipedia articles of the district and the neighbourhood (from their `wikipedia` / `wikidata` tags),
  added as sources and fragments (step 4). `area.fragment_ids` lists those fragments.
- `street_names`: unique names of named streets within 400 m, with `named_after` where known. The agent uses this
  to spot clusters of street names (e.g. Siarczana, Chemiczna, Hutnicza).
- `nearby_articles`: every Polish Wikipedia geosearch result within 400 m (up to 50), sorted by distance, as
  `{ "title", "distance_m", "fetched" }`. Only some of them are fetched in full (step 4); the agent fetches the rest
  through `wikipedia_article` when it decides they are worth it. Cutting the list to the nearest few would drop
  important articles in the city centre, so the list stays complete and only the full text is limited.

## 4. Step 3: objects nearby

Overpass, around the group point.

One radius for everything nearby: **400 m**.

- `highway` with `name`
- `historic=*`, `memorial=*`
- `building` / `amenity` / `tourism` / `leisure` with `wikidata`
- anything with `name:etymology:wikidata`, `heritage` or `ref:nid`

- Merge street segments with the same name into one object (shortest distance wins).
- For every `wikidata` and `name:etymology:wikidata` ID, fetch from Wikidata: Polish label and description, P138
  (named after), P571 (inception), P1435 (heritage status), sitelink count. For people: P569 / P570 (birth and
  death dates).
- If a street has `wikidata` but no `name:etymology:wikidata`, take the patron from the street's P138.

## 5. Step 4: sources and fragments

### What to fetch (minimum the agent needs)

The full decision on which sources to take automatically, by hand, or not at all is part of #9 and stays yours.
This table is only what the agent cannot work without.

| Source                                      | How                                                                                                                                                                               | `type`         |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| Polish Wikipedia                            | plain-text extracts (see below), full text for: the ~15 nearest geosearch results, articles linked from objects, patron articles, an article named after the stop (if one exists) | `encyclopedia` |
| Wikipedia of the district / neighbourhood   | from step 2                                                                                                                                                                       | `encyclopedia` |
| Warszawikia (`warszawa.fandom.com/api.php`) | search by stop name and by street names within 400 m (lower priority; CC BY-SA, from the wiki's `siteinfo`)                                                                       | `varsaviana`   |
| City data (dane.um, old API)                | see "City data as fragments" below                                                                                                                                                | `city_data`    |
| NID heritage register                       | objects with `ref:nid` / P1435 nearby                                                                                                                                             | `official`     |

Suggested to leave out of the automatic run: warszawa1939.pl, blogs, press, local portals (no API, NC licences, or
they need judgement). The agent can fetch them through tools when it decides they are worth it (section 8), within
the limits set there. Your call in #9.

### Fragment rules

The agent proves every fact with a **verbatim quote** from a fragment, and code checks that the quote really is in the
fragment. So fragments must be the source text itself:

- Plain text exactly as in the source. **No summarising, no rewording, no translation.**
- Prefer text that is already plain, so the cached raw response and the fragment match. For Wikipedia use
  `action=query&prop=extracts&explaintext=1&exsectionformat=wiki`: the response is plain text with `== Section ==`
  headings, which is also how it is split into sections. Full extracts (without `exintro`) return one page per
  request, so this is one request per article.
- Warszawikia (Fandom) has no `extracts` (checked 2026-10-17), so its wikitext is converted to plain text in code. The
  converter is one deterministic function, and the quote check (section 10) runs the same function on the cached raw
  response before searching it. Because the check runs the same converter, it cannot catch the converter's own
  mistakes (e.g. leftover template code), so review its output by hand for 2–3 articles.
- Normalise to Unicode NFC and collapse runs of whitespace into one space.
- One fragment per article section. If a section is longer than about 4000 characters, split it at paragraph
  boundaries.
- Drop sections that hold no content: "Przypisy", "Bibliografia", "Linki zewnętrzne", "Zobacz też".
- `id` = `<source_id>#<n>`, numbered in source order.

### City data as fragments

City data comes in as one-sentence fragments generated from a fixed template, with the numbers from the response.
The agent then quotes it like any other source.

These fragments are not verbatim source text, so they are marked and checked differently:

- `"derived": true`, plus `template` (the template ID) and `values` (the numbers and names inserted into it).
- The check renders `template` with `values` and compares it with `text`, then checks that every value comes from the
  cached response or a computation over it (for example a median).
- Each template is defined in code together with the computation behind each value (e.g. "median of `cena` over
  transactions within 400 m"). The check reruns that computation on the cached response and compares the result; it
  does not just look for the number somewhere in the response.
- All other fragments have `"derived": false` and no `template` or `values`.

Examples:

- RCN (`get_bgk_rcn`): "Mediana ceny 1 m² lokalu mieszkalnego w transakcjach z {year} r. w promieniu 400 m od
  przystanku {name} wyniosła {price} zł ({n} transakcji)." RCN coordinates are in PL-2000; convert them first.
- Participatory budget (`get_cks_budzet_obywatelski`): one fragment per project within 400 m or in the same
  neighbourhood: title, year, status, cost.
- Streets in 1939 (`HISTORIA_ULICE_1939`, a WMS layer; attributes come from its WFS counterpart): one fragment per
  1939 street within 400 m, with its 1939 name and distance: "W 1939 r. w promieniu 400 m od przystanku {name}
  istniała ulica {name_1939}." This is the most direct city dataset for "how this place changed". Two limits:
  - **Positive facts only.** No fragment says a street did not exist in 1939. A missing record in the layer is not
    evidence that the street was not there.
  - **No matching to today's streets.** Do not link a 1939 street to a current one by geometry; that is
    interpretation. The agent compares the 1939 list with `street_names` itself.
- Trees (old API): the 3 trees with the largest trunk girth within 400 m: species, girth, measurement year.
- Road investments (old API): investments on streets within 400 m that are ongoing or planned: name, dates.

### Source fields

| Field               | Meaning                                                                                                                                  |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                | `s1`, `s2`, … unique within the file                                                                                                     |
| `type`              | one of `official`, `city_data`, `institution`, `encyclopedia`, `varsaviana`, `press`, `local_portal`, `blog`, `commercial`, `literature` |
| `title`             | article or dataset title                                                                                                                 |
| `publisher`         | "Wikipedia", "m.st. Warszawa", "Narodowy Instytut Dziedzictwa", …                                                                        |
| `url`               | the page a passenger can open ("Skąd to wiemy?")                                                                                         |
| `license`           | e.g. "CC BY-SA 4.0", "CC0", "public domain"                                                                                              |
| `license_url`       |                                                                                                                                          |
| `author`            | for literature and signed texts, else `null`                                                                                             |
| `author_death_year` | for literature (from Wikidata P570); decides whether quotes are public domain                                                            |
| `retrieved_at`      | ISO date of the cached response, not of the run, so a rerun from cache gives the same file                                               |

**`type` matters**: the agent decides how much to trust a fact from it. Wikipedia is `encyclopedia`, dane.um and the
old API are `city_data`, NID and council resolutions are `official`, museums, archives, IPN and dzieje.pl are
`institution`, Warszawikia and warszawa1939.pl are `varsaviana`.

## 6. Step 5: images

Candidates only. The agent picks up to 5. About 15 candidates per group is enough.

1. **Wikimedia Commons**: images used in the fetched Wikipedia articles, plus Commons geosearch (namespace 6) within
   400 m. Read `extmetadata`: `ImageDescription`, `Artist`, `LicenseShortName`, `LicenseUrl`, `DateTimeOriginal`.
2. **City maps**: WMS `GetMap` from `https://wms.um.warszawa.pl/serwis`, same bounding box for all (about
   800 × 800 m, i.e. the 400 m radius around the group), 1024 px. Layers (from `GetCapabilities`, checked
   2026-10-17):

   | Layer                  | What                   | Image `kind`     |
   | ---------------------- | ---------------------- | ---------------- |
   | `RASTER_FOTOPLAN_1935` | 1935 photo map         | `photo_map_1935` |
   | `RASTER_PLAN_1939`     | 1939 city plan         | `plan_1939`      |
   | `RASTER_ORTOFOTO_1945` | 1945 aerial photo      | `photo_map_1945` |
   | `RASTER_FOTOPLAN_2021` | latest dated photo map | `orthophoto`     |

3. Muzeum Warszawy public-domain items: optional, by hand for the demo.

Rules:

- **No licence = not a candidate.** Accept public domain, CC0, CC BY and CC BY-SA. CC BY-NC is allowed for the
  hackathon; mark it. Skip ND.
- `caption` is the description from the source, with HTML stripped. If the source has none, use
  `"Źródło: {publisher}"`. Never generate a caption.
- Map captions come from a fixed template: "Fotoplan Warszawy {year}, okolice przystanku {name}" (for the 1939 plan:
  "Plan Warszawy 1939, okolice przystanku {name}").
- Download to `out/images/<group_id>/<image_id>.jpg`, at most 1600 px wide. Keep the original URL.

## 7. Output file

One file per group: `out/collected/<group_id>.json`.

```json
{
  "stop": {
    "group_id": "7010",
    "name": "Książęca",
    "lat": 52.2297,
    "lon": 21.0253,
    "poles": [{ "pole": "03", "lat": 52.2296, "lon": 21.0251 }],
    "lines": ["131"],
    "routes": [
      {
        "line": "131",
        "direction": "Dw. Centralny",
        "variant": "TP-…",
        "prev_group_id": "…",
        "prev_name": "Śniegockiej",
        "next_group_id": "…",
        "next_name": "Pl. Trzech Krzyży",
        "travel_prev_s": 60,
        "travel_next_s": 120
      }
    ],
    "target_duration_s": 45
  },
  "area": {
    "district": "Śródmieście",
    "neighbourhood": "Powiśle",
    "fragment_ids": ["s7#1", "s7#2"],
    "street_names": [{ "name": "Książęca", "object_id": "o1", "named_after": null, "distance_m": 0 }],
    "nearby_articles": [{ "title": "Ulica Książęca w Warszawie", "distance_m": 12, "fetched": true }]
  },
  "objects": [
    {
      "id": "o1",
      "name": "ulica Książęca",
      "kind": "street",
      "distance_m": 0,
      "osm_id": "way/…",
      "wikidata": "Q…",
      "wikipedia": "pl:Ulica Książęca w Warszawie",
      "named_after": null,
      "named_after_label": null,
      "old_names": [],
      "heritage_ref": null,
      "tags": {}
    }
  ],
  "sources": [
    {
      "id": "s1",
      "type": "encyclopedia",
      "title": "Ulica Książęca w Warszawie",
      "publisher": "Wikipedia",
      "url": "https://pl.wikipedia.org/wiki/…",
      "license": "CC BY-SA 4.0",
      "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
      "author": null,
      "author_death_year": null,
      "retrieved_at": "2026-10-17"
    }
  ],
  "fragments": [
    {
      "id": "s1#1",
      "source_id": "s1",
      "section": "Historia",
      "text": "…verbatim text…",
      "object_id": "o1",
      "derived": false
    }
  ],
  "images": [
    {
      "id": "i1",
      "kind": "photo",
      "file": "out/images/7010/i1.jpg",
      "url": "https://commons.wikimedia.org/wiki/File:…",
      "caption": "…from the source…",
      "author": "…",
      "year": "1912",
      "license": "public domain",
      "license_url": "…",
      "non_commercial": false,
      "source_id": "s4",
      "object_id": "o1"
    }
  ]
}
```

`kind` for objects: `street`, `square`, `building`, `monument`, `memorial`, `park`, `church`, `institution`, `other`.
`kind` for images: `photo`, `photo_map_1935`, `plan_1939`, `photo_map_1945`, `orthophoto`.

`derived` is `false` for every fragment except city data (see "City data as fragments").

Arrays are sorted (objects by distance, fragments by ID) so two runs on the same cache give the same file.

The shared pydantic models for this file live in one module that both the collector and the agent import, so the
contract is checked in code, not only on paper.

## 8. Fetch functions the agent reuses as tools

The agent can fetch more when something is worth following. To avoid writing the same fetchers twice, the collector
exposes them as plain functions. Each returns `(sources, fragments)` in the format above and uses the same cache:

| Function                                      | Returns                                                         |
| --------------------------------------------- | --------------------------------------------------------------- |
| `wikipedia_article(title, lang="pl")`         | one source + its section fragments                              |
| `wikipedia_search(query, lang="pl", limit=5)` | titles only (the agent then calls `wikipedia_article`)          |
| `wikidata_entity(qid)`                        | one source + one fragment with labels, descriptions, key claims |
| `warszawikia_article(title)`                  | one source + its section fragments                              |
| `fetch_allowed_url(url)`                      | one source + fragments, only for domains on an allowlist        |

Allowlist for `fetch_allowed_url`: `pl.wikipedia.org`, `warszawa.fandom.com`, `www.warszawa1939.pl`,
`muzeumwarszawy.pl`, `dzieje.pl`, `zabytek.pl`, `wolnelektury.pl`. Each domain has a fixed `type` and licence.

`www.warszawa1939.pl` is one of the most valuable sources for us (what stood at an address before the war), but it is
CC BY-NC and its `robots.txt` and terms are not checked yet. Until someone checks them, `fetch_allowed_url` does not
download from it: it returns a source with the URL only and no fragments, so the agent can link to it but not quote it.

## 9. Technical rules

- Cache every raw response under `cache/` (gitignored), keyed by request. A second run must work with the network off.
- Wikimedia, Wikidata, Overpass and MusicBrainz: send a `User-Agent` with a contact address, one request at a time.
- WFS returns at most 1000 features: fetch in `bbox` tiles. `circle=` does not work.
- Old API `datastore_search` works only **without** the API key.
- dane.um returns `HTTP 500 {"message":"Service unavailable"}` for **every client error**: missing or wrong key,
  missing body, missing or wrongly typed parameter. It is not an outage. Checked 2026-10-14, both endpoints work:
  - `get_bgk_rcn`:
    `{"dzielnica":"Bemowo","rodzajNieruchomosci":"nieruchomoscLokalowa","rodzajRynku":"rynekPierwotny","rok":2022}`.
    `rok` must be a number (a string, as in the official example, gives 500). It filters by district, not by radius:
    fetch the district, convert from PL-2000 and filter to 400 m. The response is GeoJSON `{type, features}`.
  - `get_cks_budzet_obywatelski`: `{"rok":2020,"status":"zrealizowane"}`. The body is required.
  - Both: `POST`, header `Authorization: <key>` (no "Bearer"), `Content-Type: application/json`.
- No API keys in output files, caches committed to git, logs or fixtures.

## 10. Done when

For Książęca, Rozbrat and Pl. Trzech Krzyży (line 131):

- [ ] `out/collected/<group_id>.json` exists and validates against the shared model.
- [ ] Each file has at least 5 sources and 10 fragments.
- [ ] Every fragment with `derived: false` can be found in the cached raw response it came from (after the same
      normalisation). Every fragment with `derived: true` renders from its `template` and `values`.
- [ ] Each has at least 3 licensed image candidates and the 1935 photo map crop.
- [ ] `routes` and `target_duration_s` are filled from the route table, once it exists (#32). Not a blocker before.
- [ ] At least one `city_data` fragment per group.
- [ ] A second run with the network off produces identical files.

## 11. Open questions

- `www.warszawa1939.pl`: check `robots.txt` and the terms before `fetch_allowed_url` downloads from it (section 8).
- WFS layer name for `HISTORIA_ULICE_1939` and whether it carries the 1939 street name as an attribute.
- Does the route table (#32) give travel times per pair of stops, or do we compute them from departures?
- Old API: download trees and road investments for the demo lines now, before the service is switched off.
