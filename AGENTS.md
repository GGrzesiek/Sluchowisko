# AGENTS.md

Shared context for AI assistants working on this repo (Claude Code, Codex, Cursor, a Claude project on claude.ai).
Claude Code loads it through `CLAUDE.md`. If you use claude.ai, add this file to your project's knowledge.

Keep it short and current. When a team decision changes, update this file in a PR like any other change.

## The project

**Słuchowisko**: a web app that tells short narrated stories about the places a Warsaw bus or tram passes.
Every sentence has a source the passenger can open ("Skąd to wiemy?").

- Warsaw Open Data Hackathon 2026, challenge **„Złap oddech”**.
- Audience: Warsaw residents on their everyday commute, not tourists.
- Problem: people lose touch with the place they live in, and learning its history takes too much effort.
- Core idea: how ordinary-looking places changed. What used to be here, how it looked, how it worked. Not dry dates
  and timelines.
- War and the Uprising are one layer among many, never the axis of the app.
- Demo: 5 lines, each in a different part of Warsaw (#1): tram 22 (Wola), tram 18 (Mokotów, Służewiec), bus 179
  (Ursynów), bus 169 (Praga-Północ), bus 117 (Saska Kępa, Gocław). Ten stop groups per line, 50 stories in total; the
  segments and stop group ids are in `data/demo_lines.json`. We submit a recorded demo, not a live one (#17); each
  recording is 2–3 minutes of a ride.

## Architecture

```
city API ──▶ stops and line routes ─────────────────────────────────────┐
         └─▶ recorded vehicle positions ─▶ ride simulation ─────────────┤
open sources ─▶ facts with sources ─▶ stories ─▶ verifier ─▶ voice-over ─┤
                                                                         ▼
                                                     static files ─▶ app (web/)
```

- **The app never calls an LLM.** Stories are written during development only and stored as static files. No model API
  key in the app, no generation at runtime (#3).
- Two modes:
  - **Demo** (the recorded demo, the hall): the app replays a recorded ride (#17). The hall has a connection, so the
    app does not have to work offline.
  - **Live**: the app asks our back end on Cloud Run where the vehicle is and which stops come next. The back end calls
    the city API itself, cached for 10 s. The city servers answer only Polish IP addresses, so the back end stays in
    `europe-central2` (Warsaw); no laptop is needed (#83, #84).
  - In both modes, photos and recordings load from the public media bucket `muzeum-w-autobusie-2026-media`. Anyone
    with a link can read a file there; only writers upload (#105).
- **One story per stop group** (zespół przystankowy: all poles with the same name at one junction). The same recording
  plays whatever the line or direction.
- Each stop gets:
  - a title: the stop group name;
  - one narrated audio clip, a popular-science hook, triggered on approach. Length comes from the travel time to the
    neighbouring stop, so the stop falls mid-story and the clip ends before the next one;
  - a longer read-after text, plain text, that goes deeper and does not repeat the narration;
  - the sources of every fact used in the narration and the text, listed at the end, Wikipedia-style;
  - up to 5 images for a carousel, each with caption, author and licence from the source.
- The UI gets no raw facts. A timeline, fact tiles, images inside the text and synced subtitles are optional, only if
  time allows (#65).
- Out of scope for now: video, AI-generated images, karaoke transcript, live LLM features.
- File shapes for the UI: `docs/data-contract.md`. If a shape is not there yet, agree on it in the team before writing
  code that depends on it.
- What the facts collector (#9) hands to the stories agent: the implementation plan in issue #9.

## Who does what

| Person   | GitHub       | Area                                                                                               |
| -------- | ------------ | -------------------------------------------------------------------------------------------------- |
| Grzesiek | @GGrzesiek   | DevOps, CI, keys (#5); recording rides (#7)                                                        |
| Hubert   | @hububiq     | City endpoints: stops, vehicle positions, prices (#32, #6, #10); ride simulation, serving (#14–15) |
| Kuba     | @Jzackiewicz | Pitch; stories agent: sources, stories, verifier, voice-over (#8, #11–13)                          |
| Masza    | @MaryTim     | UI (#16, #22); facts collector (#9)                                                                |
| Wojtek   | @xwojtuss    | UI (#16, #20)                                                                                      |

Stay inside the area of your issue. If you need to change someone else's area, mention them in the PR.

## Repo rules

Full version: `README.md` (moving to `docs/workflow.md` in #39). The parts an assistant gets wrong most often:

- `development` accepts **pull requests only**, merged with **Rebase and merge**. All CI checks must pass. Never push
  to `development` or `release` directly. Do not touch `gh-pages`.
- Branches: `feature/<issue>-<name>`, also `fix/`, `docs/`, `ci/`. Branch names in English.
- Code, identifiers, commit messages and PRs: **English**. **No comments in code.** UI content: **Polish**.
- Before pushing:
  `pipx run ruff==0.6.9 check --fix . && pipx run ruff==0.6.9 format . && npx prettier@3.3.3 --write .`
- Python ≥ 3.12. `.editorconfig` sets UTF-8, LF, 2 spaces (4 for Python). Prettier `printWidth` is 120.
- **Never commit keys.** Copy `.env.example` to `.env`. gitleaks scans the whole history; a leaked key must be
  rotated, deleting the commit is not enough. Keep keys out of tests, fixtures, logs and prompts.

## Hackathon rules that affect the code

- All code is written during Stage II (§4.3). Notes and research from before are knowledge, not code to paste in.
- Use of AI must be described in `docs/AI_USAGE.md` (§4.4). Update it in the same PR whenever a change involves AI:
  an agent, a prompt or skill, a model or voice, or substantial AI-written code or documentation.
- Everything we submit (README, `docs/`, content in the app) describes the finished app only. No notes to the team, no
  TODOs, no development history: those live in issues and PRs. Every required item is reviewed before submission
  in #66.
- The repo and the presentation are submitted before Stage II ends (§4.5).
- Use of Warsaw open data is 20% of the score; fit with the challenge is 15%. Make city data visible in the product,
  not only in the pipeline.

## Warsaw city data: known gotchas

- **dane.um.warszawa.pl**: `POST https://dane.um.warszawa.pl/api/action/<action>`, header `Authorization: <key>`,
  JSON body. The key is `ZTM_API_KEY` in `.env`.
- **There is no "stops of a line in order" endpoint.** We build our own route table:
  1. `get_ztm_przystanki_komunikacji_miejskiej`: all poles (`zespol`, `slupek`, `nazwa_zespolu`, `szer_geo`,
     `dlug_geo`). Dedupe by `zespol` + `slupek`.
  2. `get_ztm_lista_linii_na_przystanku` for each pole, inverted into line → poles.
  3. `get_ztm_odjazdy_linii_z_przystanku` for each pole of the line (`brygada`, `czas`, `kierunek`, `trasa`).
  4. Take one run (same `brygada` + `trasa` + `kierunek`, about a 60-minute window) and sort its poles by `czas`.
     Check against 2–3 runs.
- Pitfalls:
  - `trasa` is a variant code. `TP-*` is the main route. `TX-`, `TD-` and `TZ-` are variants and depot runs; keep
    them separate.
  - Each direction has its own pole in the same group (e.g. Sielce 01 and Sielce 02).
  - Loops have an extra layover pole after the terminus. It is not a passenger stop.
  - `brygada` has no fixed format (`1`, `08`, `010`). Compare as strings, do not normalise.
  - `czas` can go past `24:00`.
  - `get_ztm_lokalizacja_pojazdow` returns stale entries. Filter by `Time`.
- Requests were blocked from some cloud and VM networks, and CORS is unverified. Call the API from scripts or the
  back end, cache the responses, and never call it from the app at runtime.
- **api.um.warszawa.pl** (old API) is planned to shut down. Download what you need. `datastore_search` works only
  _without_ a key.
- Map services: WMS `https://wms.um.warszawa.pl/serwis`, WFS `https://wfs.um.warszawa.pl/serwis`. They include photo
  maps from 1935 and 1945 and streets as of 1939. Get layer names from `GetCapabilities`. WFS returns at most 1000
  features, so fetch in `bbox` tiles.
- Overpass and Wikidata: set a `User-Agent`, send one request at a time, and cache.

## Content rules

These apply to anything that collects, writes, checks or displays story content.

**Truth comes first:**

- Every sentence is backed by a fact with a source. Never add anything that is not in the provided sources.
- Do not drop a relevant fact because it complicates the story.
- When something is unknown, say so. "There is no connection" needs evidence, just like "there is one".
- Keep claims apart from facts ("the developer says…" is not a confirmed fact).
- Do not infer a cause from a coincidence.
- A single weak source (blog, marketing copy, anecdote) is not enough. Find a second one.
- If a name has no historical link to the place (e.g. a developer made it up), say it plainly.
- Explain unfamiliar references before using them (e.g. what Ostra Brama is).
- If a stop's patron has nothing to do with the place, still say who they were and why the name carries prestige.
- Every story answers "why am I hearing this here?" Without that link it is a quiz question, not a story.

**Licences:**

- Public domain, CC0, CC BY and CC BY-SA: fine with attribution.
- CC BY-NC: fine for the hackathon only.
- ND: show it, never modify it.
- Press and blogs: never copy. Give a link and one or two sentences in our own words.
- **Song lyrics: never, not even one line.** Title, artist and a link only.
- Public domain in Poland starts 70 years after the author's death. In 2026 we can quote authors who died before 1956. Check the translator too.
- Images: captions come from the source, never from the model. No licence means we don't use it.
- AI voices and AI music are always labelled as AI.

**Tone:**

- Tragic topics (ghetto, executions, the Holocaust): no music, no punchline, one calm voice.
- Do not extract victims' names automatically.
- Never put invented words into a real person's mouth.

## Working with an AI assistant here

- Talk to teammates in Polish. Code, commits and PRs stay in English.
- Start from the issue. Link it in the PR (`Closes #12`).
- Do not add LLM calls or analytics to the app. Its only network call is live mode asking our own back end; the app
  never calls the city API or any other service directly.
- Do not guess API fields. Look at a real (cached) response first.
- Keep PRs small and inside your area. Run the formatters before pushing.
- If a decision in this file looks outdated, say so and propose an update in a PR. Do not quietly work around it.

## Open questions for mentors

- Must the presentation be PPTX, or can it be HTML?
- Does a video make sense at all?
- Do the WMS/WFS map services and city council naming resolutions count as Warsaw open data?
