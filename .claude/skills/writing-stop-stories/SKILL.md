---
name: writing-stop-stories
description: Krok 3 agenta historii („Słuchowisko”). Z gotowego planu historii pisze scenariusz krótkiego słuchowiska dla przystanku (kwestie dla jednego, dwóch lub trzech głosów, dźwięki, które wchodzą na pierwszy plan, pauzy) oraz obszerny tekst do czytania. Każde zdanie wskazuje fakty z planu. Używaj po planning-stop-stories, przed voicing-stop-stories.
---

# Scenariusz słuchowiska i tekst do czytania

Agent: zbieracz → plan (`planning-stop-stories`) → **scenariusz (ten skill)** → realizator dźwięku (`voicing-stop-stories`) → nagranie i rekord (kod).

Piszesz dwie rzeczy z tego samego planu:

1. **Słuchowisko** — 20–45 s, odtwarzane, gdy pojazd zbliża się do przystanku. Popularnonaukowy haczyk, nie wykład. Głosy, dźwięk, cisza.
2. **Tekst do czytania** — obszerny, czytany po wysiadce albo w drodze. Rozwija słuchowisko, nie powtarza go.

Piszesz **czystą polszczyzną dla człowieka**: liczby cyframi, normalna interpunkcja, bez znaczników dla syntezatora. Znaczniki, wymowę i prompty dźwięków dodaje następny krok. Dzięki temu weryfikacja faktów działa na czystym tekście.

## Wejście

- `out/plans/<group_id>.json` — plan (model `StoryPlan`). Najważniejsze: `facts`, `story` (oś, most, haczyk, `change_mode`, `period_voice`, `steps`, `explain`, `tone`), `text_sections`, `image_ids`, `target_duration_s`.
- `python -m story_agent show <group_id>` — materiał źródłowy, gdy chcesz zobaczyć kontekst faktu. **Nie dodajesz niczego, czego nie ma w `facts` planu.** Jeśli czegoś brakuje, wróć do planu (dociągnij źródło, dopisz fakt, `check-plan`), zamiast pisać z pamięci.

## Wyjście

`out/scripts/<group_id>.json`, model `StoryScript` w `story_agent/models.py`. Przykład: [schemas/script.example.json](schemas/script.example.json).

| Pole                | Co                                                                                                                                        |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `cast`              | `solo` · `solo_with_archive` · `duet` · `duet_with_archive` (kiedy który: [reference/sluchowisko.md](reference/sluchowisko.md), rozdz. 3) |
| `tone`              | taki jak `story.tone` w planie                                                                                                            |
| `target_duration_s` | z planu                                                                                                                                   |
| `lines[]`           | kwestie po kolei: `id` (`L1`…), `voice`, `role`, `text`, `fact_ids`, `delivery`, `pause_after_s`                                          |
| `sounds[]`          | 0–3 dźwięki: `id` (`S1`…), `kind`, `shape`, `description`, `fact_ids`, `start`, `end`                                                     |
| `music`             | `null` albo `{ "mood": "…" }`                                                                                                             |
| `text[]`            | sekcje tekstu do czytania: `heading`, `paragraphs[].sentences[]` (`text`, `fact_ids`)                                                     |
| `image_ids`         | z planu (0–5)                                                                                                                             |

**Kwestie (`lines`)**

- `voice`: `narrator` (prowadzi, zawsze jest), `co_narrator` (drugi przewodnik), `archive` (tylko dosłowny cytat).
- `role`: `anchor`, `place_fact`, `explanation`, `jump`, `return` — jak kroki planu; `quote` dla cytatu.
- `fact_ids`: fakty, na których stoi kwestia. Puste tylko w `anchor` (sama nazwa przystanku, pytanie słuchacza).
- `delivery`: krótka wskazówka po polsku, jak to powiedzieć („z ciekawością”, „ciszej”), albo `null`. Realizator zamieni ją na znacznik.
- `pause_after_s`: cisza po kwestii, 0–4 s. Długa pauza (1,5–2,5 s) to miejsce, w którym dźwięk wychodzi na pierwszy plan.
- Kwestia ma 1–3 zdań. Zmiana głosu = nowa kwestia.

**Dźwięki (`sounds`)**

- `kind` + `shape`: `ambience` + `bed` (tło), `motif` + `swell` (narasta i wychodzi na pierwszy plan), `spot` + `spot` (pojedyncze zdarzenie).
- `description`: po polsku, konkretnie: co wydaje dźwięk, z czego, gdzie, jak daleko, w jakim rytmie. Bez ludzkich słów.
- `fact_ids`: fakt, który ten dźwięk ilustruje. Bez faktu nie ma dźwięku.
- `start` / `end`: `{ "line_id", "edge": "start" | "end", "offset_s" }`, czyli „na początku / na końcu kwestii Lx, przesunięte o tyle sekund” (od −3 do 4). `spot` ma `end: null` — długość ustala realizator.

**Tekst do czytania (`text`)**

- 2–4 sekcje według `text_sections` planu; `heading` krótki, rzeczowy (albo `null` w pierwszej sekcji).
- Obszerny: zwykle 250–600 słów. Każde zdanie ma `fact_ids`. Zbierz wszystko, co plan daje — to miejsce na szczegóły, które nie zmieściły się w słuchowisku.
- Plain text: bez markdownu, wypunktowań, linków i przypisów (źródła dopisze kod na końcu, w stylu Wikipedii).
- Język popularnonaukowy, pełne zdania, akapity po 2–5 zdań. Wolno dłuższe zdania niż w słuchowisku, ale bez urzędowego stylu.
- Uczciwie: sprzeczności i domysły z planu opisz jako takie („Źródła podają różne daty…”, „Lokalni pasjonaci zgadują…”). Dobra ostatnia sekcja to „Czego nie wiemy”, jeśli plan ją ma.
- Nie powtarzaj zdań ze słuchowiska. Fakt z narracji może wrócić tylko jako tło dla nowego faktu.

## Przebieg

```
- [ ] 1. Przeczytaj plan: oś, most, haczyk, kroki, ton, period_voice, explain
- [ ] 2. Wybierz obsadę (cast) i jeden pomysł dźwiękowy (albo świadomie żaden)
- [ ] 3. Policz budżet: ok. 2,3 słowa na sekundę mowy; pauzy i wejście dźwięku zabierają czas
- [ ] 4. Napisz kwestie: kotwica → fakt o miejscu → (wyjaśnienie) → skok → powrót
- [ ] 5. Ustaw dźwięki i pauzy wokół skoku; sprawdź, czy dźwięk ma fakt
- [ ] 6. Przeczytaj słuchowisko na głos (w myślach) z zegarkiem; skróć, co się nie mieści
- [ ] 7. Napisz tekst do czytania z text_sections
- [ ] 8. python -m story_agent check-script <group_id>; popraw błędy, przejrzyj ostrzeżenia
```

## Zasady słuchowiska (skrót)

Pełne zasady z researchu: [reference/sluchowisko.md](reference/sluchowisko.md). Najważniejsze:

1. **Pierwsze zdanie to miejsce** — nazwa przystanku albo rzecz za oknem. Bez wstępów.
2. **Teraźniejszość gra za oknem.** Dźwięki w słuchowisku należą do przeszłości; nie dodajesz odgłosów dzisiejszej ulicy.
3. **Pisz do ucha:** zdania 6–15 słów, jedna myśl, szyk prosty, najwyżej dwie liczby, powtórz kluczowe słowo zamiast zaimka.
4. **Jeden motyw dźwiękowy.** Najmocniejszy moment: zdanie o miejscu z przeszłości → dźwięk narasta pod nim → pauza 1,5–2,5 s, w której dźwięk jest sam → dźwięk gaśnie pod powrotem do dziś.
5. **Dźwięk ilustruje tylko to, co fakt mówi wprost**, bez anachronizmów. Nazwij źródło dźwięku raz, nie opisuj, co słychać.
6. **Głosy mają stałe funkcje.** Drugi przewodnik zadaje pytanie pasażera albo niesie kontrast „a dziś”. Głos archiwalny czyta tylko dosłowny cytat z domeny publicznej i jest zapowiedziany („Tak pisał o tym Prus:”).
7. **Nikt prawdziwy nie mówi słów, których nie napisał.** Żadnych scen z postaciami.
8. **Ostatnie zdanie wraca do miejsca**, które pasażer mija. Konkret, nie morał.
9. **Ton tragiczny:** `solo`, bez dźwięków, bez muzyki, bez puenty; jedna pauza po najważniejszym zdaniu.
10. **Muzyka domyślnie `null`.** Jeśli jest: instrumentalna, subtelna, nigdy przy tonie tragicznym.

## Zasady prawdy przy pisaniu

- Każde zdanie wynika z faktów w `fact_ids`. Nie dopisujesz przyczyn, ocen ani ironii, których fakt nie zawiera.
- Fakt `claim` podajesz z atrybucją („deweloper twierdzi…”), `guess` jako domysł („podobno”, „lokalni pasjonaci zgadują”), `literature` jako obraz autora („tak widział to Prus”), `memory` jako wspomnienie.
- Fakty z `story.explain` muszą paść, zanim użyjesz odniesienia.
- Liczby i nazwy dokładnie jak w fakcie. Prosty rachunek z daty („ponad dwieście lat temu”) jest dozwolony.
- Bez słów-wytrychów: „niezwykły”, „fascynujący”, „magiczny”, „warto wiedzieć”, „jak się okazuje”.

## Autokontrola

- [ ] `check-script` kończy się „OK”.
- [ ] Pierwsze zdanie mówi, gdzie jestem; ostatnie wraca do tego miejsca.
- [ ] Słuchowisko odpowiada na `story.listener_question`.
- [ ] Każdy dźwięk ma fakt i jest rozpoznawalny bez obrazu; najwyżej jeden motyw.
- [ ] Każdy głos ma jasną funkcję; nowy głos jest zapowiedziany albo wchodzi pytaniem.
- [ ] Tekst do czytania jest obszerny, ma sekcje i nie powtarza słuchowiska.
