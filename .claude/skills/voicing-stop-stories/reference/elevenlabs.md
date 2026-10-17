# ElevenLabs: głosy, znaczniki, dźwięki, muzyka

Stan na październik 2026, z dokumentacji ElevenLabs (linki na końcu). Kod wywołuje API sam; ten plik mówi, jak przygotować tekst, żeby wynik był dobry.

## Jak kod nagrywa

- **Głosy:** jedno zapytanie `POST /v1/text-to-dialogue/with-timestamps` z modelem z `story_agent/voices.json` (domyślnie `eleven_v3`, `language_code: "pl"`). Każda kwestia to osobny element `inputs` z głosem przypisanym do roli (`narrator`, `co_narrator`, `archive`). Model słyszy całą rozmowę naraz, więc intonacja jest spójna, a krótkie kwestie nie brzmią przypadkowo.
- Limit to ok. **2000 znaków** na zapytanie. Dłuższy scenariusz kod dzieli na części.
- Z odpowiedzi kod bierze czasy każdej kwestii, wstawia ciszę z `pause_after_s`, kładzie dźwięki i muzykę według kotwic, ścisza je pod głosem i normalizuje głośność (−16 LUFS, szczyt −1,5 dBTP).
- **Dźwięki:** `POST /v1/sound-generation` (model `eleven_text_to_sound_v2`, 0,5–30 s, opcja pętli).
- **Muzyka:** `POST /v1/music`, zawsze instrumentalna.
- Wszystko trafia do `cache/elevenlabs/`, więc ponowne uruchomienie z tym samym tekstem nie kosztuje kredytów.
- `eleven_v4` (nowszy) lepiej słucha znaczników i obsługuje wymowę w IPA. Można go wpisać w `voices.json` jako `model_id`, ale najpierw przetestuj jeden przystanek.

## Znaczniki (audio tags)

Znacznik to słowo po angielsku w nawiasie kwadratowym, przed fragmentem, którego dotyczy: `[curious] Skąd właściwie ta nazwa?`. Model go nie czyta, tylko gra.

Dozwolone (kod odrzuci inne):

| Znacznik           | Z `delivery`            | Uwagi                                        |
| ------------------ | ----------------------- | -------------------------------------------- |
| `[calm]`           | spokojnie               | bezpieczny domyślny                          |
| `[curious]`        | z ciekawością, pytająco | pytanie słuchacza, wejście w haczyk          |
| `[thoughtful]`     | z zadumą, refleksyjnie  | przed powrotem do dziś                       |
| `[warm]`           | ciepło                  | zakończenie                                  |
| `[softly]`         | ciszej, miękko          | nad dźwiękiem, który narasta                 |
| `[whispers]`       | szeptem                 | rzadko, tylko gdy treść tego chce            |
| `[serious]`        | poważnie                | fakty trudne                                 |
| `[sighs]`          | z westchnieniem         | rzadko                                       |
| `[excited]`        | żywo                    | tylko ton `light`, najwyżej raz              |
| `[amused]`         | z uśmiechem, z humorem  | tylko ton `light` lub `neutral`              |
| `[slowly]`         | wolno                   | ważne zdanie, cytat                          |
| `[matter-of-fact]` | rzeczowo                | dane, liczby                                 |
| `[reading]`        | —                       | jedyny znacznik głosu `archive` (albo żaden) |

- Najwyżej 2 znaczniki w kwestii, zwykle 0–1. Znacznik na początku kwestii albo w środku, gdy ton się zmienia.
- Ton `tragic`: tylko `[calm]`, `[serious]`, `[softly]`, `[slowly]`, `[reading]`.
- **Nie używaj znaczników dźwiękowych w tekście** (`[applause]`, `[explosion]` itp.). Dźwięki idą osobną ścieżką (`sounds`), bo tylko tam kod panuje nad głośnością i czasem.
- Znacznik musi pasować do głosu: spokojny lektor nie zagra krzyku. Nie zmuszaj głosu do skrajności.
- Nie pisz WIELKIMI LITERAMI dla akcentu — w v3 brzmi to jak krzyk. Akcent robi szyk zdania: ważne słowo na końcu.

## Rytm

- Interpunkcja to rytm: kropka = koniec myśli, przecinek = krótki oddech, „—” = zawieszenie, „…” = wahanie. Najwyżej jeden wielokropek w kwestii.
- Bardzo krótkie zdania obok siebie („Kercelak.”) brzmią mocno — używaj świadomie, raz na nagranie.

## Prompty dźwięków

Pisz **po angielsku** (model dźwięków słucha angielskiego najlepiej), konkretnie, w tej kolejności:

1. źródło i czynność — `blacksmith hammer striking an anvil`
2. miejsce i materiał — `in a small stone forge`
3. perspektywa i odległość — `close`, `distant`, `from across a courtyard`
4. rytm i natężenie — `steady rhythm`, `slow`, `occasional`
5. zawsze na końcu: `no voices, no music` (dla tłumu: `indistinct crowd murmur, no intelligible words`)

Przykłady:

- `Large open-air market in the 19th century, indistinct crowd murmur and distant calls, no intelligible words, wooden carts, no music`
- `Water wheel of an old watermill turning slowly, splashing water and creaking wood, close, steady, no voices, no music`
- `Single church bell ringing three times in the distance, open air, no voices, no music`
- `Horse-drawn tram passing on cobblestones, hooves and a small hand bell, medium distance, no voices, no music`

- `duration_s`: dla `spot` długość zdarzenia (1–5 s); dla `bed` i `swell` przybliżony czas, przez jaki dźwięk ma grać (kod i tak dopasuje go do kotwic, najwyżej 30 s, potem zapętla).
- `loop`: `true` dla `bed` i `swell`, `false` dla `spot`.
- Zakazane: broń, wybuchy, syreny, krzyki, płacz, wojna — kod odrzuci takie słowa.

## Prompt muzyki

Tylko gdy scenariusz ma `music`. Po angielsku: instrumenty, tempo, nastrój, przestrzeń dla głosu. Bez nazwisk kompozytorów i tytułów utworów.

`Instrumental, sparse and slow, solo piano with soft strings, pensive and warm, no drums, no vocals, leaves space for a narrator`

## Źródła

- Prompting Eleven v3: https://elevenlabs.io/docs/best-practices/prompting
- Best practices (pauzy, normalizacja, wymowa): https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices
- Text to Dialogue: https://elevenlabs.io/docs/capabilities/text-to-dialogue, API: https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert-with-timestamps
- Sound effects API: https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert
- Music API: https://elevenlabs.io/docs/api-reference/music/compose
- Eleven v4: https://elevenlabs.io/docs/overview/capabilities/text-to-speech/eleven-v4
