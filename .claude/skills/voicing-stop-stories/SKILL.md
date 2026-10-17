---
name: voicing-stop-stories
description: Krok 4 agenta historii („Słuchowisko”). Przygotowuje sprawdzony scenariusz słuchowiska do nagrania w ElevenLabs — liczby i skróty słownie, znaczniki emocji eleven_v3, wymowa nazw, prompty dźwięków i muzyki po angielsku — i zapisuje out/voiced/<id>.json. Używaj po writing-stop-stories, przed python -m story_agent render.
---

# Realizator dźwięku: tekst dla ElevenLabs

Agent: zbieracz → plan → scenariusz (`writing-stop-stories`) → **realizator (ten skill)** → nagranie i miks (kod) → rekord.

Pisarz napisał scenariusz dla człowieka. Ty robisz z niego **partyturę dla syntezatora**: te same słowa, ale tak zapisane, żeby głos przeczytał je poprawnie i z właściwą intonacją, oraz opisy dźwięków, z których model wygeneruje efekty. **Nie zmieniasz treści.** Nie dodajesz zdań, nie skracasz, nie poprawiasz stylu — jeśli coś jest nie tak w treści, wracasz do scenariusza.

Dlaczego osobny krok: weryfikator sprawdza fakty na czystym tekście scenariusza; znaczniki i zapis słowny liczb dokładamy dopiero potem, a kod pilnuje, żeby treść się nie rozjechała.

## Wejście

- `out/scripts/<group_id>.json` (model `StoryScript`) — kwestie (`voice`, `text`, `delivery`, `pause_after_s`), dźwięki (`description`, `shape`), `music`, `tone`.

## Wyjście

`out/voiced/<group_id>.json`, model `VoicedScript` w `story_agent/models.py`. Przykład: [schemas/voiced.example.json](schemas/voiced.example.json).

| Pole             | Co                                                                                                 |
| ---------------- | -------------------------------------------------------------------------------------------------- |
| `lines[]`        | ta sama liczba i kolejność co w scenariuszu: `id`, `voice`, `tts_text`                             |
| `sounds[]`       | jeden na każdy dźwięk scenariusza: `id`, `prompt` (po angielsku), `duration_s`, `loop`             |
| `music`          | `null` albo `{ "prompt": "…" }` — tylko gdy scenariusz ma muzykę                                   |
| `pronunciations` | lista zmian wymowy: `{ "word": "Lindley", "spoken_as": "Lindlej" }` (do przeglądu przez człowieka) |

## Przebieg

```
- [ ] 1. Dla każdej kwestii: przepisz text → tts_text
- [ ]    a. liczby, daty, lata, wieki słownie, w dobrym przypadku (reference/wymowa.md)
- [ ]    b. skróty i skrótowce rozwinięte; nazwy obce fonetycznie (+ pronunciations)
- [ ]    c. delivery → 0–1 znacznik z listy (reference/elevenlabs.md); archive: [reading] albo nic
- [ ]    d. rytm: przecinki, „—”, najwyżej jeden „…”; bez SSML, bez WIELKICH LITER
- [ ] 2. Dla każdego dźwięku: description → prompt po angielsku, duration_s, loop
- [ ] 3. Muzyka (jeśli jest): mood → prompt po angielsku, instrumentalny
- [ ] 4. python -m story_agent check-voiced <group_id>; popraw wszystko, co odrzuci
```

## Zasady (skrót)

1. **Te same słowa.** Zmieniasz tylko zapis (liczby, skróty, nazwy obce) i dodajesz znaczniki. Kod porównuje `tts_text` ze scenariuszem.
2. **Zero cyfr, skrótów z kropką i liczb rzymskich** w `tts_text`. Lata jako liczebniki porządkowe w przypadku, którego wymaga zdanie: „w 1770 roku” → „w tysiąc siedemset siedemdziesiątym roku”.
3. **Znaczniki po angielsku, z listy**, najwyżej 2 na kwestię, zwykle 0–1. Ton tragiczny: tylko `[calm]`, `[serious]`, `[softly]`, `[slowly]`.
4. **Bez znaczników dźwiękowych w tekście** — dźwięki idą przez `sounds`.
5. **Pauzy między kwestiami robi kod** (`pause_after_s`). W środku kwestii: przecinek, „—”, „…”. Żadnych `<break>`.
6. **Prompt dźwięku**: źródło i czynność → miejsce i materiał → odległość → rytm → `no voices, no music`. Tylko to, co jest w `description` scenariusza; bez dodawania nowych elementów.
7. **Prompt muzyki**: instrumentalna, oszczędna, z miejscem na głos; bez nazwisk kompozytorów i tytułów.

Szczegóły: [reference/wymowa.md](reference/wymowa.md) (liczby, skróty, nazwy) i [reference/elevenlabs.md](reference/elevenlabs.md) (jak kod nagrywa, znaczniki, prompty, limity).

## Po sprawdzeniu

`python -m story_agent render <group_id>` nagrywa głosy, generuje dźwięki i muzykę, miksuje i zapisuje `out/audio/<group_id>.mp3` oraz oś czasu `out/audio/<group_id>.timeline.json`. Jeśli nagranie jest dłuższe niż cel o więcej niż 2 s, kod kończy się błędem „ZA DŁUGO” — wtedy wracasz do scenariusza i skracasz, nie przyspieszasz głosu.

Bez kredytów ElevenLabs: `render <group_id> --dry-run` sprawdza oś czasu z dźwiękami zastępczymi.

## Autokontrola

- [ ] `check-voiced` kończy się „OK”.
- [ ] Każda liczba brzmi tak, jak powiedziałby ją lektor radiowy.
- [ ] Znaczniki pasują do tonu i nie ma ich więcej, niż trzeba.
- [ ] Każdy prompt dźwięku opisuje jedno źródło dźwięku i kończy się `no voices, no music`.
