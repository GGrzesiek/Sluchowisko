# Mosty, haczyki i kształt historii

Spis treści

1. Trzy elementy historii
2. Typy mostów
3. Jak wybrać oś
4. Haczyk
5. Sposoby pokazania zmiany w czasie
6. Kroki narracji
7. Ton i era
8. Narracja a tekst do czytania
9. Zdjęcia
10. Braki i warstwy zapasowe

## 1. Trzy elementy historii

| Element            | Czym jest                                                               | Przykład (Okopowa)                                                    |
| ------------------ | ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| **Fakt o miejscu** | coś twardego o tym konkretnym miejscu                                   | ulica powstała wzdłuż wału z 1770 r.                                  |
| **Haczyk**         | jeden skok do czegoś zaskakującego albo znanego z innej strony          | wał usypano przeciw dżumie, która nie przyszła; obok powstał Kercelak |
| **Most**           | zdanie, które odpowiada na pytanie _„dlaczego słyszę to akurat tutaj?”_ | „Okopowa jest taka kręta, bo wciąż biegnie linią tamtego nasypu”      |

Bez mostu fakt o patronie jest quizem, który mógłby lecieć na każdym przystanku.
**Test mostu:** czy to zdanie mogłoby zabrzmieć na innym przystanku? Jeśli tak, to nie jest most.

## 2. Typy mostów (`story.bridge.type`)

| Typ                      | Znaczenie                                                                               | Przykład                                                                 |
| ------------------------ | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **A. Tu się wydarzyło**  | osoba tu była, wydarzenie tu się stało, film tu kręcono                                 | blok „Alternatywy 4” przy Grzegorzewskiej                                |
| **B. Widać za oknem**    | obiekt, który mijasz, jest wejściem do historii                                         | mury fabryki Koneser przy Ząbkowskiej, ruina Młyna Michla                |
| **C. Dlaczego ta nazwa** | nazwa ulicy lub przystanku sama jest historią                                           | Okopowa = wał Lubomirskiego, Francuska = sojusz z 1921                   |
| **E. Słyszysz tę nazwę** | nazwa z zapowiedzi przystanku — nawet bez związku z miejscem pasażer pyta „kto to był?” | Rondo Żabczyńskiego                                                      |
| **D. Brak mostu**        | nic nie łączy treści z miejscem                                                         | patron ulicy, który nigdy tu nie był, a przystanek nie nosi jego imienia |

- D nigdy nie jest osią. Przy D szukasz innej osi albo przechodzisz na `status: area`.
- Przy E mówisz wprost, że związku z miejscem nie ma (jeśli źródło to mówi) albo że nie wiadomo, i odpowiadasz, dlaczego ta osoba jest ciekawa.
- Most może łączyć typy (np. C + A). W polu `type` podajesz główny.
- `bridge.draft` to robocze sformułowanie mostu dla pisarza, oparte na faktach z `bridge.fact_ids`.

## 3. Jak wybrać oś (`axis_candidates`, `story.axis`)

1. **Zacznij od miejsca, nie od patrona.** Najpierw: co tu stoi, co tu było, co tu kręcono, skąd nazwa przystanku.
2. **Mosty A, B i C mają pierwszeństwo przed E.** Między A, B i C wybierasz to, co pasażer słyszy lub widzi w momencie przystanku.
3. **Patron często nie jest najlepszą historią.** Na Ząbkowskiej wygrywa fabryka, przy Grzegorzewskiej serial.
4. **Osią jest najciekawsza prawdziwa historia, nie pośrednik.** Przy stacji Zacisze-Wilno osią jest kolej do Petersburga, a deweloper osiedla to jedno zdanie.
5. **Klaster nazw to osobna historia.** Kilka sąsiednich ulic (Siarczana, Chemiczna, Hutnicza) mówi, czym okolica była lub miała być. Pytania: kiedy, kto i dlaczego nadał te nazwy.
6. **Nazwy bywają marketingiem i historią naraz.** Rozdzielasz, co jest czym (deklaracja vs fakt).
7. Jeśli nazwa przystanku nie daje mostu i nie jest osobą (np. pochodzenie nazwy nieznane), przechodzisz na **historię okolicy**: `status: area`, kotwicą jest to, co widać.

W `axis_candidates` zapisz 1–3 rozważane osie z typem mostu i jednym zdaniem uzasadnienia, także te odrzucone. To idzie do śladu pracy agenta.

`story.listener_question` to pytanie, na które historia odpowiada, z perspektywy pasażera: „Dlaczego ta ulica jest taka kręta?”, „Kim był Żabczyński?”, „Skąd Wilno na Targówku?”.

## 4. Haczyk (`story.hook`)

- Jeden skok, nie lista ciekawostek.
- **Wybierasz go pod most i pod słuchacza**, nie pod „najfajniejszy fakt”. Przy Banacha wygrywa gęś z Księgi Szkockiej (bo wysiadają tu studenci matematyki), choć historia z instytutem Weigla jest mocniejsza emocjonalnie.
- Dobre haczyki: zaskoczenie, rzecz znana z innej strony (film, piosenka — tylko tytuł, książka, postać), związek z tym, kto tu wysiada.
- Haczyk musi dać się przypiąć z powrotem do miejsca (krok `return`).
- `why`: jedno zdanie, czemu ten, a nie inny kandydat.
- Jeśli żaden fakt nie nadaje się na haczyk, `hook: null`. Lepsza krótka, prawdziwa historia niż naciągany skok.

## 5. Sposoby pokazania zmiany w czasie (`story.change_mode`)

Cel: słuchacz ma poczuć, jak daleko zaszło to samo miejsce, a nie dostać datę i fakt. Wybierasz jeden sposób, tylko jeśli jego warunek jest spełniony.

| Wartość      | Na czym polega                                                                                                          | Warunek konieczny                                                                                                 |
| ------------ | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `two_voices` | głos epoki (cytat lub streszczenie), potem narrator mówi, jak jest dziś — najlepiej jedną twardą liczbą z danych miasta | fakt rodzaju `literature` / dawna prasa **i** fakt o teraźniejszości; cytat tylko z domeny publicznej             |
| `plan`       | co planowano → co się wydarzyło → co widzisz dziś                                                                       | dokument planu (kto, kiedy, co) **i** fakt o tym, co stało się potem; tylko plany z przeszłości                   |
| `chain`      | kolejne wcielenia tej samej ziemi w 3–4 krokach, zakończone dniem dzisiejszym                                           | każde ogniwo ma fakt; brakujące ogniwo nazywasz luką, nie zgadujesz                                               |
| `trace`      | coś, co widać dziś, wygląda tak _z powodu_ czegoś, czego już nie ma                                                     | związek przyczynowy podany **przez źródło** (nie twój wniosek)                                                    |
| `people`     | kto tu mieszkał, a kto mieszka                                                                                          | fakty o mieszkańcach w różnych okresach; przerwy (wojna, wysiedlenia, wyburzenia) pokazujesz, jeśli są w źródłach |
| `none`       | historia nie pokazuje zmiany w czasie                                                                                   | —                                                                                                                 |

Przy `people` bez oceniania („dobrze, że…”, „szkoda, że…”). Przy wojnie lub Zagładzie: ton tragiczny.

## 6. Kroki narracji (`story.steps`)

Każdy krok to `role`, `fact_ids` (id) i opcjonalna `note` dla pisarza.

| Rola          | Co robi                                                                         | Uwagi                                                                                   |
| ------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `anchor`      | gdzie jesteś / co słyszysz lub widzisz                                          | zwykle nazwa przystanku albo obiekt za oknem; może nie mieć faktu, jeśli to tylko nazwa |
| `place_fact`  | twardy fakt o tym miejscu                                                       | 1–2 fakty                                                                               |
| `explanation` | 1–2 zdania o czymś spoza Warszawy, zanim powiesz, co to ma wspólnego z miejscem | tylko gdy potrzebne (Ostra Brama, Wilno, Francja)                                       |
| `jump`        | haczyk                                                                          | fakty z `hook.fact_ids`                                                                 |
| `return`      | zamknięcie pętli: z powrotem do miejsca, które pasażer mija                     | „po bazarze została tylko nazwa ronda, które mijasz”                                    |

Kolejność: `anchor` → `place_fact` → (`explanation`) → `jump` → `return`. Przy sposobie `chain` kroki `place_fact` mogą się powtarzać jako kolejne ogniwa.

`story.explain[]`: lista odniesień, których słuchacz może nie znać (osoby, miejsca spoza Warszawy, wydarzenia), razem z id faktu, który je wyjaśnia. Jeśli takiego faktu nie ma, dopisz to do `gaps`.

## 7. Ton i era

`tone`: `light` | `neutral` | `elevated` | `tragic`.

- `tragic` = w audio cisza zamiast muzyki, bez puenty i bez inscenizacji. Ustawiasz go, gdy oś dotyczy śmierci, egzekucji, Zagłady, wysiedleń.

`era` (dla historii i dla każdego faktu): `before_1800` | `1800_1918` | `1918_1939` | `1939_1945` | `1945_1989` | `after_1989`. Dla historii podajesz erę, w której dzieje się jej główna część.

## 8. Narracja a tekst do czytania

- **Narracja** (kroki) to opowieść z hakiem, popularnonaukowa, 3–6 faktów.
- **Tekst do czytania** (`text_sections`) jest bardziej wnikliwy: rozwija to, co padło w narracji, ale tego nie powtarza. Użytkownik czyta go, gdy słuchowisko się skończy.
- `text_sections` to 2–4 sekcje: `draft_heading` + `fact_ids` (id). Dobre sekcje: szerszy kontekst osi, kolejne ogniwa lub szczegóły, „czego nie wiemy” (sprzeczności, domysły — uczciwie opisane), co jest tu dziś (dane miejskie).
- Fakty z narracji mogą wrócić w tekście tylko jako tło dla nowego faktu.

## 9. Zdjęcia (`image_ids`)

- 0–5 id zdjęć z wejścia, w kolejności pokazywania. Pierwsze powinno pasować do kotwicy (to, co pasażer widzi, albo jak to wyglądało).
- Wybierasz po metadanych: `object_id`, `year`, `caption`. Preferuj zdjęcia obiektów z osi historii i zestawienia „wtedy i dziś” (np. fotoplan 1935 + dzisiejsze zdjęcie).
- **Nie opisujesz zdjęć** i nie wymyślasz podpisów. Podpis idzie ze źródła.

## 10. Braki i warstwy zapasowe

`gaps[]`: `what` (co brakuje), `why` (które pytanie domyka), `where` (typ źródła: uchwała nazewnicza, warszawa1939.pl, Wikidata, prasa…). Wpisuj tu też rzeczy, które „wiesz”, ale których nie ma we fragmentach. Ta lista zasila późniejszą pętlę dociągania źródeł.

`spare_layers[]` (0–2): inne historie z tego miejsca, które miały most, ale przegrały wybór — np. trudniejsza warstwa wojenna albo patron bez związku. Każda: `axis`, `bridge_type`, `fact_ids`, `tone`. Będą użyte przy rotacji (później).
