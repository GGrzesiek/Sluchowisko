# Data contract

Shapes the app (`web/`) reads from the back end and from static files.

## Ride WebSocket

`wss://<backend>/ws/ride/<vehicle>/`

Every message is JSON: `{"type": "<type>", "data": <payload>}`. The server pushes every `WS_PUSH_INTERVAL_SECONDS`
(10 s by default) and only sends what changed. The client sends `{"type": "ping"}` and gets `{"type": "pong", "data": {}}`.

| `type`     | When                                                        | `data`                                        |
| ---------- | ----------------------------------------------------------- | --------------------------------------------- |
| `route`    | On connect and whenever the route or the stop states change | `RideInfo` (`web/src/types.ts`)               |
| `audio`    | Once per stop group, when it becomes the next stop          | see below                                     |
| `location` | When the vehicle reaches a new stop group, once per group   | `{"groupId": "5002", "story": <story>\|null}` |
| `error`    | Once per new problem                                        | `{"code": "...", "line"?: "..."}`             |
| `pong`     | In answer to `ping`                                         | `{}`                                          |

Each stop in `RideInfo.stops` has `groupId`, the stop group id (`zespol`) used by stories and audio.

`route` data:

```json
{
  "vehicle": "3122",
  "line": "22",
  "destination": "Wiatraczna",
  "stops": [{ "name": "Okopowa", "groupId": "5004", "state": "next", "etaMinutes": 4, "hasStory": true }]
}
```

`state` is one of `passed`, `current`, `next` or `upcoming`. `etaMinutes` is missing for passed and current stops. `hasStory` is missing when the stop group has no verified story.

`location` is about the stop group that is `current` in the last `route`. `story` is `null` when that group has no
verified story. Drafts and rejected stories are never sent.

`story`:

```json
{
  "groupId": "5002",
  "title": "Cmentarz Powązkowski",
  "photos": [
    {
      "src": "https://...",
      "alt": "...",
      "year": "1936",
      "caption": "...",
      "credit": "Fot. Jan Kowalski · domena publiczna"
    }
  ],
  "body": { "format": "plain", "text": "..." },
  "blocks": [
    { "type": "paragraph", "text": "...", "sources": [1] },
    { "type": "image", "photo": 0 },
    { "type": "timeline", "items": [{ "year": "1790", "text": "...", "sources": [1] }] }
  ],
  "sources": [{ "label": "Wikipedia", "href": "https://..." }]
}
```

`body.text` is always the whole story as plain text. `blocks` is the same story split into typed blocks, `[]` when the
story has none. A client that does not know a block type skips it. `image.photo` is an index into `photos`, and
`sources` are 1-based numbers of entries in `sources`.

| Block       | Fields                                                      |
| ----------- | ----------------------------------------------------------- |
| `paragraph` | `text`, optional `sources`                                  |
| `image`     | `photo`                                                     |
| `timeline`  | `items`: at least one `{ year (4 digits), text, sources? }` |

`photos` has 1 to 5 items. `credit` is built from the author and licence of the photo.

`error` codes: `vehicle_not_found` (the server then closes with code 4404), `no_route`, `no_live_data`, `city_api`
and `internal`. All but `vehicle_not_found` are temporary: the connection stays open and the server keeps trying.

### Client to server

`{"type": "ping"}` is answered with `pong`. Any other message gets an `error` with `invalid_json` or
`unknown_message`; the connection stays open.

### `audio`

Recording for the next stop group on the route (the first stop with state `next`), so the clip starts on approach
and the stop falls mid-story:

```json
{
  "groupId": "5087",
  "name": "Niska",
  "available": true,
  "src": "https://storage.googleapis.com/muzeum-w-autobusie-2026-media/audio/5087.mp3",
  "seconds": 42,
  "aiVoice": true
}
```

No recording for that stop group (or its story is not verified yet):

```json
{ "groupId": "5087", "name": "Niska", "available": false }
```

- The message comes once per stop group per connection. Periodic refreshes do not repeat it. After a reconnect, the
  next stop group's message comes again.
- `available: false` does not close the connection; the ride goes on without narration for that stop.
- `src` is the full public URL of the recording in the media bucket. The app plays it directly; it needs no ElevenLabs
  key and no credentials.
- `seconds` is the length of the file, rounded to whole seconds.
- `aiVoice: true` means the narration is a synthetic voice and the player shows the AI voice label.
- If the file fails to load (an `error` event on the audio element), the app skips the narration for that stop and
  keeps the ride going.

## Ride replay (`ride.json`)

`web/public/rides/<line>.json`, one recorded ride per line, built from a positions recording by
`make simulate REC=data/raw/<line>/positions-....jsonl`. The app replays it in demo mode instead of live positions.

```json
{
  "line": "22",
  "vehicle": "3122",
  "brigade": "1",
  "direction": { "from": "Powązkowska", "to": "Pl. Starynkiewicza" },
  "recordedAt": "2026-10-17T19:31:05+02:00",
  "durationS": 524.0,
  "speedup": 10,
  "triggerRadiusM": 60,
  "points": [{ "t": 0, "lat": 52.2533, "lon": 20.9822 }],
  "events": [{ "t": 20.0, "type": "arrive", "groupId": "5159", "pole": "04", "name": "Powązkowska", "distanceM": 8 }]
}
```

- `t` is seconds from the start of the clip, in recorded (real) time. The clip covers the demo segment from
  `data/demo_lines.json` plus `padding_s` (20 s) before the first stop and after the last one.
- `points`: vehicle positions in time order. Between two points the app interpolates linearly.
- `events`: one `arrive` event per stop group of the segment, in route order, at the moment the vehicle is closest to
  the stop. Every stop group of the segment has a story, so `groupId` is also the story and audio id. When a stop group
  has two poles on the route, it still gets one event; `pole` is the pole the vehicle passed.
- `speedup`: how many times faster than real time the app plays the clip (`t / speedup` seconds of wall-clock time).
- `recordedAt`: when the clip starts, Warsaw time.
- `triggerRadiusM` and `distanceM`: how close the vehicle had to come to count as arriving, and how close it came.

## Audio files

Public bucket `muzeum-w-autobusie-2026-media`, object `audio/<groupId>.<ext>`, one per stop group with a verified story.
Formats: `mp3` (preferred), `m4a`, `ogg`, `opus`, `wav`.

The private recordings bucket names each file after its stop group id (`<groupId>.mp3`, in any folder).
`python manage.py sync_audio --download`, run with `DATABASE_URL` pointing to Cloud SQL (through `cloud-sql-proxy`):

1. reads the verified stories,
2. downloads the recordings bucket into a fresh temporary folder,
3. uploads each story's recording to the media bucket, and only then sets `audio_url` (the public URL) and
   `audio_seconds`,
4. clears both fields for verified stories without a readable recording.

`--dry-run` lists what would be uploaded without changing anything. A story moved back to draft, or given a new
narration, loses its recording until the next `sync_audio`.

## Stories

`GET /api/stories/<groupId>/` and the static files from `python manage.py export_stories` return `StoryContent`
(`web/src/types.ts`) plus `groupId` and `narration`. When the story has a recording, it also has `audio` (the public
URL, as in `StoryContent.audio?: string`), `audioSeconds` and `aiVoice: true`; without one these keys are absent.

## Importing the agent's output

`python manage.py import_story <group_id>... | --all [--out out] [--force] [--dry-run]` reads two files per stop group
and saves them as a story with status `draft`:

- `out/drafts/<group_id>.json`: `narration`, `blocks`, `sources` (`label`, `href`), optional `title`, `lead`, `card`, `source_note` and `text`;
- `out/photos/<group_id>.json`: the `photos` array (1 to 5 items, shape as in "Writing a story").

The data goes through the same validation as `PUT /api/stories/<group_id>/`, so an unknown stop group, a missing
photo or source, or a bad block fails that group and names it. A story that is already `verified` or `rejected` is
skipped unless `--force` is given, which replaces it with the new draft; a changed narration clears its recording.
`--all` imports every file in `out/drafts`.

The agent also writes presentation fields: `lead` (one sentence under the title), `card` (`icon` is one of `patron`,
`oldname`, `bazaar`, `cinema`, `building`, `river`, `event`; optional four-digit `year`) and `source_note` (one sentence
under the source list). They are sent as `lead`, `card` and `sourceNote` and are absent when empty.

Block types: `paragraph` (`text`, `sources`), `image` (`photo`), `timeline` (`items` with `year` as four digits or
`dziś`, `text`, optional `tone` of `past`, `loss` or `now`, `sources`), `facts` (exactly 3 `items` with `value` up to 12
and `label` up to 24 characters, `sources`) and `callout` (`title`, `text`, `sources`). Source numbers start at 1 and
photo numbers at 0. The agent writes no `text`; the backend builds it from the blocks.

## Writing a story

`PUT /api/stories/<group_id>/` with the write token (`Authorization: Bearer <token>`). A photo needs `src`, `alt`,
`caption`, `author`, `license` and `source_url`; `year`, `license_url` are optional. A story needs 1 to 5 photos, at
least one source, and `text` or `blocks`. When only `blocks` is given, `text` is generated from them. Block types and
references to photos and sources are validated, and a bad block rejects the whole story. Only stories with status `verified` reach the app.
