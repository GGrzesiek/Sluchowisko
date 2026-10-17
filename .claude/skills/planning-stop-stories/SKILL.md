---
name: planning-stop-stories
description: Wybiera, sprawdza i łączy fakty zebrane dla jednego zespołu przystankowego w Warszawie w plan historii (oś, most, haczyk, sposób zmiany, podział na narrację i tekst do czytania, zdjęcia) zgodnie z zasadą prawdy projektu „Muzeum w autobusie”. Używaj, gdy na wejściu jest JSON z fragmentami źródeł, obiektami w okolicy i zdjęciami dla przystanku, a zadaniem jest przygotować materiał dla pisarza — przed pisaniem narracji.
---

# Planowanie historii przystanku

Fabryka treści ma trzy kroki: **plan historii (ten skill)** → pisarz (narracja + tekst do czytania) → narrator (tekst do TTS).
Ten skill **nie pisze narracji**. Wyciąga fakty ze źródeł, odrzuca te, które nie przechodzą zasady prawdy, i układa z reszty plan jednej historii dla przystanku.

**Język:** wszystkie pola tekstowe wyjścia piszesz po polsku, naturalną polszczyzną. Wyjątek: pole `cytat` przepisujesz dosłownie, w języku i pisowni źródła.

**Słuchacz:** mieszkaniec Warszawy w drodze do pracy lub szkoły, nie turysta. Słyszy nazwę przystanku z zapowiedzi i widzi okolicę przez okno. Nie zna historii miejsca i nie musi znać niczego spoza Warszawy.

## Najważniejsza reguła

**Jedyną wiedzą są fragmenty z wejścia.** Nie dodajesz niczego z własnej pamięci, nawet jeśli jesteś pewny. Jeśli wiesz o czymś ważnym, czego brakuje we fragmentach, wpisujesz to do `braki` jako rzecz do sprawdzenia, nie do `fakty`.

## Wejście

Jeden JSON na zespół przystankowy (przykład: [schemas/wejscie.przyklad.json](schemas/wejscie.przyklad.json)):

- `przystanek` — `zespol`, `nazwa`, `lat`, `lon`, `dlugosc_docelowa_s` (docelowa długość narracji).
- `zrodla[]` — `id`, `typ`, `tytul`, `wydawca`, `url`, `licencja`, opcjonalnie `autor` i `autor_rok_smierci`.
- `fragmenty[]` — `id`, `zrodlo`, `tekst` (surowy tekst ze źródła), opcjonalnie `obiekt`. Dane miejskie (RCN, budżet obywatelski, rejestr drzew) też przychodzą jako fragmenty, ze źródłem typu `dane_miejskie`.
- `obiekty[]` — rzeczy w okolicy: ulice, budynki, pomniki, parki; `odleglosc_m`, `wikidata`, `patron`, `dawne_nazwy`.
- `zdjecia[]` — `id`, `typ`, `podpis`, `autor`, `rok`, `licencja`, `obiekt`. Licencja jest już sprawdzona.

## Wyjście

Jeden JSON zgodny z [schemas/wyjscie.przyklad.json](schemas/wyjscie.przyklad.json). Pola wypełniasz **w tej kolejności**, bo to kolejność myślenia: najpierw fakty i to, co odpada, potem wybór osi, na końcu plan.

1. `fakty[]` — fakty atomowe z dowodem (dosłowny `cytat` z fragmentu).
2. `odrzucone[]` — co nie weszło i dlaczego.
3. `sprzecznosci[]` — gdzie źródła mówią co innego.
4. `kandydaci_osi[]` — 1–3 rozważane historie z typem mostu.
5. `historia` — wybrana oś: most, haczyk, sposób zmiany, kroki narracji, ton, era.
6. `do_tekstu[]` — fakty do tekstu do czytania, pogrupowane w sekcje.
7. `zdjecia[]` — id zdjęć (0–5) w kolejności pokazywania.
8. `braki[]` — czego brakuje i gdzie tego szukać.
9. `warstwy_zapasowe[]` — 0–2 inne historie z tego miejsca (na przyszłą rotację).

## Przebieg

Skopiuj tę listę i odhaczaj kolejne kroki:

```
- [ ] 1. Miejsce: nazwa przystanku, co jest najbliżej, co widać z autobusu
- [ ] 2. Fakty atomowe z fragmentów, każdy z dosłownym cytatem
- [ ] 3. Pewność każdego faktu; odrzucenie tego, co nie przechodzi
- [ ] 4. Sprzeczności między źródłami
- [ ] 5. Kandydaci na oś historii (zaczynając od miejsca) i wybór mostu
- [ ] 6. Haczyk dobrany pod most i pod słuchacza
- [ ] 7. Sposób pokazania zmiany w czasie
- [ ] 8. Kroki narracji: kotwica → fakt o miejscu → skok → powrót
- [ ] 9. Podział: co do narracji, co do tekstu do czytania
- [ ] 10. Zdjęcia, ton, era, braki, warstwy zapasowe
- [ ] 11. Autokontrola (lista na końcu)
```

- Kroki 2–4 (co wchodzi, rodzaje faktów, pewność, sprzeczności, cytaty i licencje): [reference/zasada-prawdy.md](reference/zasada-prawdy.md).
- Kroki 5–9 (mosty, haczyki, sposoby zmiany, kształt narracji, ton): [reference/mosty-i-haczyki.md](reference/mosty-i-haczyki.md).
- Trzy przykłady całego rozumowania: [reference/przyklady.md](reference/przyklady.md). Fakty z przykładów możesz wykorzystać, gdy przystanek jest tym samym miejscem, ale jak każdy fakt muszą mieć dowód we fragmencie: z wejścia albo dociągniętym. Przykład podpowiada, gdzie szukać.

## Twarde reguły (skrót)

1. Każdy fakt ma co najmniej jeden dowód: id fragmentu i dosłowny `cytat`, który w nim występuje. Kod to sprawdzi.
2. Jeden fakt = jedno twierdzenie. Liczby, daty i nazwy dokładnie tak, jak w źródle.
3. Fakt z jednego słabego źródła (blog, strona komercyjna, turystyczna) nie wchodzi. Wyjątek: domysł lub wspomnienie, które odpowiada na główne pytanie o miejsce — wtedy wchodzi z rodzajem `domysl` lub `wspomnienie` i z atrybucją („lokalni pasjonaci zgadują…”).
4. Deklaracja (ktoś mówi o sobie: deweloper, firma, inwestor) to nie fakt. Rodzaj `deklaracja`, z podaniem, kto tak twierdzi.
5. Nie łączysz dwóch faktów we wniosek, którego żadne źródło nie formułuje. Zbieżność to nie przyczyna.
6. „Nic tu nie łączy” wymaga dowodu tak samo jak „łączy”. Bez dowodu: „nie wiadomo”.
7. Nie pomijasz faktu tylko dlatego, że komplikuje historię. Jeśli dotyczy pytania „skąd ta nazwa / co tu było”, musi być w `fakty`, a oś trzeba do niego dopasować.
8. Literatura mówi, jak ktoś widział miejsce, nie jak było. Rodzaj `literatura`.
9. Cytat do głosu epoki tylko od autora zmarłego przed 1956 r. (`autor_rok_smierci` ≤ 1955). Z piosenek zero wersów.
10. Zaczynasz od miejsca, nie od patrona. Haczyk wybierasz pod most, nie pod „najfajniejszy fakt”.
11. Wojna nie jest domyślną osią. Jeśli jednak jest odpowiedzią na główne pytanie o miejsce, nie omijasz jej — ustawiasz `ton: tragiczny`.

## Budżet

- Narracja ma ok. `dlugosc_docelowa_s × 2,5` słowa. Na jeden fakt przypada ok. 8–10 s, więc w krokach narracji używasz zwykle **3–6 faktów**.
- Tekst do czytania rozwija narrację i jej nie powtarza: zwykle **4–12 faktów** spoza narracji, w 2–4 sekcjach.
- Fakt użyty w narracji może wrócić w tekście tylko jako kontekst do nowego faktu, nie jako powtórzenie.

## Status

- `ok` — jest most A, B, C lub E dla samego przystanku.
- `obszar` — nazwa przystanku nie daje mostu; historia dotyczy okolicy i zaczyna się od tego, co widać (most B) albo co się tu wydarzyło (A).
- `za_malo_materialu` — nawet historia okolicy nie ma pokrycia w faktach. Wtedy `historia.kroki` jest puste, a `braki` mówią, czego szukać.

## Autokontrola przed oddaniem

- [ ] Każdy `cytat` jest dosłownym wycinkiem wskazanego fragmentu.
- [ ] Żaden fakt nie pochodzi z mojej pamięci.
- [ ] Każdy fakt w `historia.kroki` i `do_tekstu` ma pewność `potwierdzony` lub `srednia` albo jest oznaczonym domysłem, wspomnieniem lub deklaracją.
- [ ] Zdanie mostu odpowiada na pytanie „dlaczego słyszę to akurat tutaj?” i nie pasowałoby do innego przystanku.
- [ ] Kroki zaczynają się od kotwicy i kończą powrotem do miejsca.
- [ ] Odniesienia spoza Warszawy (inne miasto, postać, wydarzenie) są na liście `historia.wyjasnic`.
- [ ] Narracja i tekst do czytania nie dzielą tych samych faktów, poza kontekstem.
- [ ] Najwyżej 5 zdjęć; nie opisuję, co na nich jest.
- [ ] Odrzucone fakty mają powód.
