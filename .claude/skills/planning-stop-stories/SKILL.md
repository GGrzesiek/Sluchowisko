---
name: planning-stop-stories
description: Krok 2 agenta historii („Słuchowisko”). Czyta materiał zebrany dla jednego zespołu przystankowego w Warszawie, dociąga brakujące źródła, wybiera i sprawdza fakty z dosłownymi cytatami i układa z nich plan historii (oś, most, haczyk, sposób zmiany, podział na słuchowisko i tekst do czytania, zdjęcia). Używaj po zbieraczu, przed pisaniem scenariusza.
---

# Plan historii przystanku

Agent ma cztery kroki: zbieracz → **plan historii (ten skill)** → pisarz scenariusza (`writing-stop-stories`) → realizator dźwięku (`voicing-stop-stories`). Całością steruje `making-stop-stories`.

Ten skill **nie pisze narracji**. Wyciąga fakty ze źródeł, dociąga to, czego brakuje, odrzuca to, co nie przechodzi zasady prawdy, i układa z reszty plan jednej historii dla przystanku.

**Język:** wartości tekstowe po polsku, naturalną polszczyzną. Klucze JSON i wartości wyliczeniowe po angielsku (jak w [schemas/plan.example.json](schemas/plan.example.json)). Wyjątek: `quote` przepisujesz dosłownie, w języku i pisowni źródła.

**Słuchacz:** mieszkaniec Warszawy w drodze do pracy lub szkoły, nie turysta. Słyszy nazwę przystanku z zapowiedzi i widzi okolicę przez okno. Nie zna historii miejsca i nie musi znać niczego spoza Warszawy.

## Najważniejsza reguła

**Jedyną wiedzą są fragmenty: z materiału zbieracza i te, które sam dociągniesz narzędziami.** Twoja pamięć podpowiada, czego szukać, ale nigdy nie jest źródłem. Rzecz, której nie znajdziesz we fragmentach, idzie do `gaps`, nie do `facts`.

## Wejście

- `python -m story_agent show <group_id>` — materiał w czytelnej formie: obiekty w promieniu 400 m (z patronami i dawnymi nazwami), hasła Wikipedii w okolicy (także niepobrane), źródła z typem i licencją, zdjęcia, wszystkie fragmenty z id.
- Ten sam materiał jako JSON: `out/collected/<group_id>.json` (model `CollectedStop` w `collector/schema.py`) i dociągnięte źródła w `out/collected/<group_id>.extra.json`.
- Docelowa długość nagrania: `python -m story_agent targets` (kolumna sekund).

Pola, których używasz najczęściej: `stop` (`group_id`, `name`), `area` (`district`, `neighbourhood`, `street_names`, `nearby_articles`), `objects[]` (`id`, `kind`, `distance_m`, `named_after_label`, `old_names`, `wikipedia`), `sources[]` (`id`, `type`, `title`, `publisher`, `license`, `author`, `author_death_year`), `fragments[]` (`id` = `s<n>#<k>`, `source_id`, `section`, `text`, `derived`), `images[]` (`id`, `kind`, `caption`, `year`, `license`, `object_id`).

Fragment z `derived: true` to zdanie zbudowane przez kod z danych (Wikidata, dane miasta). Cytujesz go jak każdy inny.

## Dociąganie źródeł

Zbieracz bierze tylko to, co da się znaleźć po współrzędnych i identyfikatorach. Ty dociągasz to, co wynika z lektury:

```
python -m story_agent fetch <group_id> <narzędzie> "<zapytanie>" --why "<po co>"
```

| Narzędzie            | Zapytanie                 | Kiedy                                                                                                                                             |
| -------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wikipedia`          | tytuł hasła po polsku     | niepobrane hasło z `nearby_articles`, patron, obiekt, wydarzenie z fragmentu                                                                      |
| `search`             | słowa kluczowe            | nie znasz dokładnego tytułu; potem `wikipedia` z wybranym tytułem                                                                                 |
| `wikidata`           | `Q…`                      | daty życia patrona, „nazwany na cześć”, data powstania obiektu                                                                                    |
| `warszawikia`        | tytuł hasła               | ulica, przystanek, osiedle — varsavianistyka                                                                                                      |
| `warszawikia-search` | słowa kluczowe            | szukasz hasła w Warszawikii                                                                                                                       |
| `url`                | adres z dozwolonej domeny | konkretna strona z pl.wikipedia.org, warszawa.fandom.com, muzeumwarszawy.pl, dzieje.pl, zabytek.pl, wolnelektury.pl, warszawa1939.pl (tylko link) |

- **Kiedy dociągać:** fragment wspomina obiekt, osobę lub wydarzenie, o którym nic więcej nie ma; nie ma odpowiedzi na „skąd ta nazwa” albo „co tu było”; odniesienie spoza Warszawy trzeba wyjaśnić (`story.explain`); fakt ma tylko jedno słabe źródło i szukasz drugiego.
- **Limit:** 10 wywołań na przystanek. Najpierw przeczytaj cały materiał, potem dociągaj celowo.
- Wynik to nowe źródło (`s<n>`) z fragmentami, wypisane na ekran. Obowiązują je te same reguły wiarygodności i pewności.
- Na końcu przepisz listę z `python -m story_agent fetch-log <group_id>` do `fetch_log` w planie. To ślad pracy agenta do pitchu.

## Wyjście

`out/plans/<group_id>.json`, zgodny z modelem `StoryPlan` w `story_agent/models.py` (szablon: [schemas/plan.example.json](schemas/plan.example.json)). Wszystkie pola są wymagane; brak wartości to `null` albo pusta lista. Pola wypełniasz **w tej kolejności**, bo to kolejność myślenia:

1. `group_id`, `stop_name`, `target_duration_s` (z `targets`).
2. `facts[]` — fakty atomowe z dowodem (dosłowny `quote` z fragmentu).
3. `rejected[]` — co nie weszło i dlaczego.
4. `contradictions[]` — gdzie źródła mówią co innego.
5. `axis_candidates[]` — 1–3 rozważane historie z typem mostu.
6. `story` — wybrana oś: most, haczyk, sposób zmiany, głos epoki, kroki, ton, era.
7. `text_sections[]` — fakty do tekstu do czytania, w sekcjach.
8. `image_ids` — 0–5 id zdjęć w kolejności pokazywania (backend wymaga co najmniej jednego, jeśli jakieś są).
9. `gaps[]` — czego brakuje i gdzie tego szukać.
10. `spare_layers[]` — 0–2 inne historie z tego miejsca.
11. `fetch_log[]` — z `fetch-log`.

## Przebieg

```
- [ ] 1. Przeczytaj materiał (show). Co jest najbliżej, co widać z autobusu, skąd nazwa przystanku
- [ ] 2. Dociągnij brakujące źródła (najwyżej 10 wywołań)
- [ ] 3. Fakty atomowe z fragmentów, każdy z dosłownym cytatem
- [ ] 4. Pewność każdego faktu; odrzucenie tego, co nie przechodzi
- [ ] 5. Sprzeczności między źródłami
- [ ] 6. Kandydaci na oś (zaczynając od miejsca) i wybór mostu
- [ ] 7. Haczyk dobrany pod most i pod słuchacza
- [ ] 8. Sposób pokazania zmiany w czasie; głos epoki, jeśli jest cytat z domeny publicznej
- [ ] 9. Kroki: anchor → place_fact → (explanation) → jump → return
- [ ] 10. Podział: co do słuchowiska, co do tekstu do czytania
- [ ] 11. Zdjęcia, ton, era, braki, warstwy zapasowe, fetch_log
- [ ] 12. python -m story_agent check-plan <group_id> — popraw wszystkie błędy, przejrzyj ostrzeżenia
```

- Kroki 3–5 (co wchodzi, rodzaje faktów, pewność, sprzeczności, cytaty i licencje): [reference/zasada-prawdy.md](reference/zasada-prawdy.md).
- Kroki 6–10 (mosty, haczyki, sposoby zmiany, kształt narracji, ton): [reference/mosty-i-haczyki.md](reference/mosty-i-haczyki.md).
- Trzy przykłady całego rozumowania: [reference/przyklady.md](reference/przyklady.md). Fakty z przykładów możesz wykorzystać, gdy przystanek jest tym samym miejscem, ale jak każdy fakt muszą mieć dowód we fragmencie: z materiału albo dociągniętym. Przykład podpowiada, gdzie szukać.

## Myśl o słuchowisku

Plan jest materiałem dla pisarza słuchowiska. Gdy wybierasz między równie dobrymi faktami, wybierz ten, który **daje się usłyszeć**: kuźnia, młyn, tramwaj konny, targ, fabryka, dzwon kościoła, rzeka. Taki fakt pozwala pisarzowi dodać dźwięk, który mówi tyle samo co zdanie. Zapisz to w `note` przy kroku („w źródle: kuźnia przy młynie — można usłyszeć młot”). Dźwięk ilustruje tylko to, co fakt mówi wprost.

Cytat do głosu epoki (`story.period_voice`) to drugi głos w słuchowisku. Szukaj go w źródłach literackich i dawnej prasie, gdy autor zmarł najpóźniej w 1955 r. (`author_death_year`), albo w dokumentach urzędowych (`type: official`).

## Twarde reguły (skrót)

1. Każdy fakt ma co najmniej jeden dowód: `fragment_id` i dosłowny `quote`, który w nim występuje. Kod to sprawdzi.
2. Jeden fakt = jedno twierdzenie. Liczby, daty i nazwy dokładnie tak, jak w źródle.
3. Fakt z jednego słabego źródła (`blog`, `commercial`) nie wchodzi. Wyjątek: `guess` lub `memory`, które odpowiada na główne pytanie o miejsce — wtedy z atrybucją („lokalni pasjonaci zgadują…”).
4. Deklaracja (ktoś mówi o sobie: deweloper, firma, inwestor) to nie fakt. `kind: claim`, z podaniem, kto tak twierdzi.
5. Nie łączysz dwóch faktów we wniosek, którego żadne źródło nie formułuje. Zbieżność to nie przyczyna.
6. „Nic tu nie łączy” wymaga dowodu tak samo jak „łączy”. Bez dowodu: „nie wiadomo”.
7. Nie pomijasz faktu tylko dlatego, że komplikuje historię. Jeśli dotyczy pytania „skąd ta nazwa / co tu było”, musi być w `facts`, a oś trzeba do niego dopasować.
8. Literatura mówi, jak ktoś widział miejsce, nie jak było. `kind: literature`.
9. Cytat do głosu epoki tylko od autora zmarłego najpóźniej w 1955 r. albo z dokumentu urzędowego. Z piosenek zero wersów.
10. Zaczynasz od miejsca, nie od patrona. Haczyk wybierasz pod most, nie pod „najfajniejszy fakt”.
11. Wojna nie jest domyślną osią. Jeśli jednak jest odpowiedzią na główne pytanie o miejsce, nie omijasz jej — ustawiasz `tone: tragic`.
12. `confirmed` = źródło o wysokiej wiarygodności (`official`, `city_data`, `institution`, `encyclopedia`) albo dwa niezależne źródła. Inaczej `medium`.

## Budżet

- Słuchowisko ma ok. `target_duration_s × 2,3` słowa (mniej, gdy są pauzy na dźwięk). Na jeden fakt przypada ok. 8–10 s, więc w krokach używasz zwykle **3–6 faktów**.
- Tekst do czytania rozwija słuchowisko i go nie powtarza: zwykle **4–12 faktów** spoza narracji, w 2–4 sekcjach. Tekst jest obszerny — zbierz do niego wszystko, co prawdziwe i ciekawe.
- Fakt użyty w narracji może wrócić w tekście tylko jako kontekst do nowego faktu.

## Status

- `ok` — jest most A, B, C lub E dla samego przystanku.
- `area` — nazwa przystanku nie daje mostu; historia dotyczy okolicy i zaczyna się od tego, co widać (most B) albo co się tu wydarzyło (A).
- `not_enough_material` — nawet po dociąganiu historia okolicy nie ma pokrycia w faktach. Wtedy `story.steps` jest puste, a `gaps` mówią, czego szukać. Agent na tym kończy pracę z przystankiem.

## Autokontrola przed oddaniem

- [ ] `python -m story_agent check-plan <group_id>` kończy się „OK”.
- [ ] Żaden fakt nie pochodzi z mojej pamięci.
- [ ] Każdy fakt w `story.steps` i `text_sections` ma pewność `confirmed` lub `medium` albo jest oznaczonym `guess`, `memory` lub `claim`.
- [ ] Zdanie mostu odpowiada na pytanie „dlaczego słyszę to akurat tutaj?” i nie pasowałoby do innego przystanku.
- [ ] Kroki zaczynają się od `anchor` i kończą `return`.
- [ ] Odniesienia spoza Warszawy (inne miasto, postać, wydarzenie) są w `story.explain`.
- [ ] Narracja i tekst do czytania nie dzielą tych samych faktów, poza kontekstem.
- [ ] Najwyżej 5 zdjęć; nie opisuję, co na nich jest.
- [ ] Odrzucone fakty mają powód.
