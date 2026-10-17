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
  "stops": [
    { "name": "Okopowa", "groupId": "5004", "state": "passed" | "current" | "next" | "upcoming",
      "etaMinutes": 4, "hasStory": true }
  ]
}
```

`etaMinutes` is missing for passed and current stops. `hasStory` is missing when the stop group has no verified story.

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

## Writing a story

`PUT /api/stories/<group_id>/` with the write token (`Authorization: Bearer <token>`). A photo needs `src`, `alt`,
`caption`, `author`, `license` and `source_url`; `year`, `license_url` are optional. A story needs 1 to 5 photos, at
least one source, and `text` or `blocks`. When only `blocks` is given, `text` is generated from them. Block types and
references to photos and sources are validated, and a bad block rejects the whole story. Only stories with status `verified` reach the app.
