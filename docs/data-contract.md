# Data contract

Shapes the app (`web/`) reads from the back end and from static files.

## Ride WebSocket

`wss://<backend>/ws/ride/<vehicle>/?device_id=<uuid>`

Every message from the server is `{"type": "<type>", "data": {...}}`. The client sends `{"type": "ping"}` and gets
`{"type": "pong", "data": {}}`.

| `type`     | When                                               | `data`                                   |
| ---------- | -------------------------------------------------- | ---------------------------------------- |
| `route`    | On connect and whenever the stop states change     | `RideInfo` (`web/src/types.ts`)          |
| `audio`    | Once per stop group, when it becomes the next stop | see below                                |
| `location` | When new facts are ahead of the vehicle            | `LocationInfo` (`web/src/rideSocket.ts`) |
| `error`    | Once per new problem                               | `{"code": "...", "line"?: "..."}`        |

Each stop in `RideInfo.stops` has `groupId`, the stop group id (`zespol`) used by stories and audio.

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
