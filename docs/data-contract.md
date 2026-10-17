# Data contract for the UI

The pipeline writes everything to `data/processed/<line>/`. The UI reads only these files and does not need to know the
ZTM API. A change to a file's shape means a change to this document in the same PR.

## `route.json`: route (`mwa route`)

```json
{
  "line": "4",
  "slug": "tram-4",
  "variant": "TP-ZER",
  "origin": "Rondo Żaba",
  "destination": "Żerań Wschodni",
  "stops": [
    {
      "order": 1,
      "slug": "rondo-zaba",
      "name": "Rondo Żaba",
      "zespol": "1234",
      "slupek": "01",
      "lat": 52.2731,
      "lon": 21.0312,
      "direction": "Żerań Wschodni",
      "story": true
    }
  ]
}
```

The route bar (drawn like a metro map) uses `stops` in `order`. `story: true` marks a stop with a story.

## `stories.json`: stories

The stories agent writes the stories. The pipeline then adds verification (`mwa verify`) and the voice-over with
subtitles (`mwa tts`).

```json
{
  "line": "4",
  "generated_at": "2026-10-17T14:02:11",
  "stories": [
    {
      "stop_slug": "inowlodzka",
      "stop_name": "Inowłodzka",
      "stop_order": 10,
      "title": "Pierwszy kurs z Annopola",
      "year": "2024",
      "sentences": [{ "text": "…", "source_ids": ["m1", "w2"] }],
      "verification": { "status": "ok", "problems": [], "checked_at": "…" },
      "audio": "audio/inowlodzka.mp3",
      "duration_s": 41.2,
      "subtitles": [{ "text": "…", "start": 0.0, "end": 4.8, "source_ids": ["m1"] }]
    },
    { "stop_slug": "poborzanska", "stop_name": "Poborzańska", "stop_order": 7, "skip": true, "reason": "Brak źródeł" }
  ]
}
```

- **Story card:** `year`, `title`, and subtitles from `subtitles`. Highlight the sentence where `start <= time < end`.
- **"Skąd to wiemy?":** the `source_ids` of the current sentence point to source documents (below).
- The UI shows only stories with `verification.status == "ok"` and an `audio` field. Stories with `skip: true` are
  skipped.
- `mwa verify` marks a story `needs_review` when a sentence has no source, cites an unknown source, cites a source
  without a link, or the story is outside 60–130 words (about 30–60 s of speech).
- `mwa tts` voices only verified stories unless run with `--include-unverified`.

## Sources: `data/sources/<line>/manual/*.yaml` and `auto/*.json`

Each document is `{id, kind, title, text, url}`. `kind` is `manual`, `wikipedia`, `osm` or `wikidata`. Id prefixes are
`m` (manual), `w` (Wikipedia), `o` (OSM) and `d` (Wikidata). Ids are unique within a stop.

Manual facts are collected by the team, one file per stop:

```yaml
stop: Rondo Żaba
facts:
  - id: m1
    year: "1924"
    text: "Pierwszy tramwaj dojeżdża na Nowe Bródno."
    url: https://…
    status: confirmed
```

- `url` is required for a fact to be usable; the verifier rejects sentences citing a fact without one.
- `status` is `draft` (from the Miro board, source not confirmed yet) or `confirmed` (checked against the source).
  Missing `status` means `confirmed`.

`mwa context` writes `auto/*.json` from Wikipedia geosearch, OpenStreetMap streets and Wikidata.

## `ride.json`: ride simulation (`mwa simulate <recording>`)

```json
{
  "line": "4",
  "vehicle": "1234",
  "started_at": "2026-10-16 07:41:20",
  "duration_s": 1260,
  "points": [{ "t": 0.0, "lat": 52.2731, "lon": 21.0312 }],
  "events": [
    {
      "t": 0.0,
      "type": "arrive",
      "stop_order": 1,
      "stop_slug": "rondo-zaba",
      "stop_name": "Rondo Żaba",
      "story": true
    }
  ]
}
```

- The dot on the route bar interpolates between `points` by `t` (seconds from start). The demo may speed time up.
- An `arrive` event with `story: true` plays the story with the same `stop_slug`.

## Line config: `config/*.yaml`

```yaml
slug: tram-4
line: "4"
vehicle_type: 2
origin: Rondo Żaba
destination: Żerań Wschodni
trigger_radius_m: 150
stops:
  - { name: Rondo Żaba, story: true }
  - { name: Staniewicka }
```

- `vehicle_type`: `1` bus, `2` tram (ZTM API values).
- `trigger_radius_m`: distance from a stop at which the vehicle counts as passing it.
- `stops`: in route order. Names must match ZTM stop group names; `mwa route` warns about mismatches.
- To add a line, copy the file, change the fields and run `mwa --line config/<file>.yaml route`.
