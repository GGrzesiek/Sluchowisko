---
name: making-stop-stories
description: Agent historii „Słuchowiska” od początku do końca. Dla jednego lub wielu zespołów przystankowych z data/demo_lines.json zbiera źródła, planuje historię, pisze scenariusz słuchowiska i tekst do czytania, przygotowuje tekst dla ElevenLabs, nagrywa i miksuje audio i składa rekord dla backendu. Używaj, gdy ktoś prosi o historię, słuchowisko albo nagranie dla przystanku, linii lub wszystkich przystanków demo.
---

# Agent historii: od przystanku do nagrania

```
przystanek ─▶ [1] zbieracz ─▶ [2] plan ─▶ [3] scenariusz ─▶ [4] realizator ─▶ [5] nagranie ─▶ [6] rekord
              (kod)           (skill)     (skill)           (skill)           (kod)           (kod)
              collect         planning-   writing-          voicing-          render          record
                              stop-       stop-             stop-
                              stories     stories           stories
```

Kod (`python -m story_agent …`) robi wszystko, co da się zrobić bez oceny: pobiera źródła, sprawdza cytaty i reguły, nagrywa i miksuje. Ty robisz to, co wymaga oceny: wybierasz fakty, piszesz, reżyserujesz. Po każdym Twoim kroku kod sprawdza wynik; błędy poprawiasz, zanim pójdziesz dalej.

## Przygotowanie (raz)

1. Python ≥ 3.12 i zależności: `pip install -e .`
2. `ffmpeg` w PATH (Windows: `winget install Gyan.FFmpeg`).
3. `ELEVENLABS_API_KEY=…` (i ewentualnie `FFMPEG_PATH=…`) w `.env` w repo albo poza repo: `../.env` lub
   `../klucze_api.txt`. Kluczy nigdy nie commitujesz.
4. Głosy: `python -m story_agent voices` pokazuje głosy z konta. Wpisz `voice_id` dla `narrator`, `co_narrator`, `archive` w `story_agent/voices.json` — różne barwy (np. mężczyzna i kobieta), najlepiej natywne polskie głosy.

Bez klucza ElevenLabs agent dochodzi do kroku [4] i robi `render --dry-run`.

## Co zrobić dla jednego przystanku

Pracujesz w katalogu repo. `<g>` to `group_id` z `data/demo_lines.json` (`python -m story_agent targets` wypisuje wszystkie z docelową długością).

```
- [ ] 0. python -m story_agent next <g>  — pokazuje, od którego kroku zacząć
- [ ] 1. python -m story_agent collect <g>
- [ ] 2. skill planning-stop-stories → out/plans/<g>.json → python -m story_agent check-plan <g>
- [ ] 3. skill writing-stop-stories  → out/scripts/<g>.json → python -m story_agent check-script <g>
- [ ] 4. skill voicing-stop-stories  → out/voiced/<g>.json → python -m story_agent check-voiced <g>
- [ ] 5. python -m story_agent render <g>
- [ ] 6. python -m story_agent record <g>
```

- **Krok 1.** `collect` używa zbieracza zespołu (`collector.collect`), gdy jest gotowy; do tego czasu prostszego zbieracza z `story_agent/collect.py` (Wikipedia, Wikidata, OpenStreetMap, Warszawikia, Wikimedia Commons). Współrzędne bierze z backendu; jeśli backend nie odpowiada: `collect <g> --lat … --lon …`. Plików w `out/collected/` nie edytujesz ręcznie — dociągasz źródła przez `fetch` w kroku 2.
- **Krok 2.** Jeśli plan ma `story.status: not_enough_material`, kończysz pracę z przystankiem i zgłaszasz, czego brakuje (`gaps`).
- **Krok 5.** „ZA DŁUGO” → skróć scenariusz (krok 3), popraw tekst dla TTS (krok 4), nagraj ponownie. Nagrania są w cache, więc niezmienione kwestie nie kosztują drugi raz.
- **Krok 6.** Rekord `out/stories/<g>.json` ma kształt, który przyjmuje `POST /api/stories/` backendu, ze statusem `draft`. Zdjęcia i mp3 trzeba wgrać tam, skąd serwuje je aplikacja; adres podajesz przez `--media-base` (albo `MEDIA_BASE_URL`).

## Pętla poprawek

Po każdym `check-…`:

- „OK” → dalej.
- Błędy (✗) → popraw plik i sprawdź ponownie. Najwyżej 3 rundy na krok. Jeśli dalej są błędy, zatrzymaj ten przystanek, zapisz powód i przejdź do następnego.
- Ostrzeżenia (!) → przeczytaj; popraw, jeśli mają sens. Nie blokują.

Błąd z kroku dalszego może wymagać powrotu: brak faktu → plan (dociągnij źródło, dopisz fakt); za długie nagranie → scenariusz.

## Wiele przystanków

- „Zrób linię 22” → przystanki tej linii z `data/demo_lines.json`, po kolei. „Zrób wszystko” → `python -m story_agent status` pokazuje, co już jest; zaczynasz od brakujących.
- Jeden przystanek na raz, od początku do końca. Po każdym jedna linijka podsumowania.
- Każdy przystanek ma osobną historię. Nie opierasz się na sąsiednich przystankach — słuchacz może wsiąść w dowolnym miejscu i jechać w dowolnym kierunku.

## Czego agent nie robi

- Nie wymyśla faktów i nie pisze z pamięci. Wszystko ma cytat ze źródła.
- Nie wgrywa niczego na serwer, nie zmienia statusu na `verified` i nie robi commitów ani pushy — to decyzje człowieka.
- Nie zmienia kodu w `collector/` ani plików innych osób z zespołu.
- Nie zapisuje kluczy w plikach poza `.env`.

## Podsumowanie na koniec

Tabela: przystanek, status planu, obsada i dźwięki, długość nagrania vs cel, ostrzeżenia, co zostało do zrobienia (np. „przegląd człowieka”, „brak zdjęcia”). Do pitchu przydaje się: `fetch_log` z planu (co agent dociągnął i po co), `rejected` (co odrzucił i dlaczego), wyniki `out/checks/`.
