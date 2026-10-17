# Zasada prawdy — co wchodzi do faktów

Spis treści

1. Fakt atomowy i dowód
2. Rodzaje faktów
3. Wiarygodność źródeł
4. Pewność faktu
5. Czego nie wolno
6. Sprzeczności
7. Cytaty, literatura, licencje
8. Odległość od przystanku
9. Trudne tematy i teraźniejszość
10. Powody odrzucenia

## 1. Fakt atomowy i dowód

- Jeden fakt = jedno twierdzenie, które da się sprawdzić jednym cytatem. „Wał usypano w 1770 r. z obawy przed dżumą” to jeden fakt; „wał usypano w 1770 r., a ulica jest kręta, bo biegnie jego linią” to dwa.
- `tekst` piszesz własnymi słowami, po polsku, nawet jeśli źródło jest angielskie.
- Liczby, daty, nazwiska i nazwy przepisujesz dokładnie. Nie zaokrąglasz bardziej niż źródło. „Ok. 1770” zostaje „ok. 1770”.
- `dowody[]`: każdy dowód to `fragment` (id) i `cytat` — **dosłowny** wycinek tego fragmentu, zwykle jedno zdanie, najwyżej ok. 300 znaków. Bez poprawiania literówek i bez wielokropków w środku. Kod porównuje cytat z tekstem fragmentu i odrzuca fakt, jeśli się nie zgadza.
- Jeśli fakt potwierdza kilka źródeł, dodajesz po jednym dowodzie z każdego. To podnosi pewność.
- `obiekt`: id obiektu z wejścia, którego fakt dotyczy (jeśli dotyczy konkretnego obiektu).
- `era`: okres, którego fakt dotyczy (wartości w [mosty-i-haczyki.md](mosty-i-haczyki.md), rozdz. 7).

## 2. Rodzaje faktów (`rodzaj`)

| Rodzaj        | Kiedy                                                                                                        | Jak pisarz to podaje                      |
| ------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| `fakt`        | twierdzenie o świecie, podane przez źródło jako ustalone                                                     | wprost                                    |
| `deklaracja`  | ktoś mówi o sobie, swoim produkcie lub swoich zamiarach (deweloper, firma, inwestor, urząd o własnym planie) | „deweloper twierdzi, że…”                 |
| `wspomnienie` | relacja mieszkańca lub świadka przytoczona w źródle                                                          | „według mieszkańców…”, „wspomina…”        |
| `literatura`  | jak autor powieści, wiersza, reportażu opisał miejsce                                                        | „tak opisywał to Prus” — nigdy „tak było” |
| `legenda`     | opowieść przypięta do miejsca, podana przez źródło jako legenda                                              | „legenda mówi…”                           |
| `domysl`      | źródło wprost zgaduje lub przypuszcza                                                                        | „lokalni pasjonaci zgadują…”, „podobno”   |

Rozróżniaj autora i bohatera: poglądy postaci z powieści to nie poglądy pisarza.

## 3. Wiarygodność źródeł (po `zrodla[].typ`)

| Typ źródła                                                                                                                                                                                | Wiarygodność                                          |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `urzedowe` (uchwały, BIP, rejestr zabytków NID), `dane_miejskie` (API m.st. Warszawy), `instytucja` (muzeum, archiwum, IPN, dzieje.pl), `encyklopedia` (Wikipedia, Encyklopedia Warszawy) | wysoka                                                |
| `varsavianistyka` (warszawa1939.pl, Warszawikia, wsiewarszawy.pl, iwaw.pl), `prasa`, `portal_lokalny`                                                                                     | średnia                                               |
| `blog`, `komercyjne` (strona dewelopera, firmy, turystyczna, marketing)                                                                                                                   | niska                                                 |
| `literatura`                                                                                                                                                                              | nie ocenia się — to perspektywa, nie dowód (rozdz. 7) |

Wyjątki od tabeli:

- Strona komercyjna jest wiarygodna dla **deklaracji** swojego właściciela (co deweloper mówi o nazwie osiedla), ale nie dla faktów historycznych.
- Wikipedia jest wysoka dla faktów z przypisami; zdanie oznaczone „potrzebny przypis” lub wyglądające na anegdotę traktuj jak średnie.

**Niezależność:** dwa źródła, z których jedno powtarza drugie (ten sam tekst, jedno cytuje drugie jako jedyne źródło), liczą się jako jedno.

## 4. Pewność faktu (`pewnosc`)

| Pewność        | Warunek                                                      | Czy wchodzi                                       |
| -------------- | ------------------------------------------------------------ | ------------------------------------------------- |
| `potwierdzony` | ≥ 2 niezależne źródła albo 1 źródło o wysokiej wiarygodności | tak                                               |
| `srednia`      | 1 źródło o średniej wiarygodności                            | tak, ale nie jako rzecz sensacyjna (niżej)        |
| —              | 1 źródło o niskiej wiarygodności                             | **nie** → `odrzucone`, powód `jedno_slabe_zrodlo` |

- **Twierdzenia sensacyjne** („pierwszy”, „jedyny”, „największy”, rekordy, anegdoty o sławnych osobach, kuriozalne zbiegi okoliczności) wymagają pewności `potwierdzony`. Przykład odrzucenia: „Wyborową podano pasażerom Concorde” — tylko ze strony turystycznej, brzmi jak legenda marketingowa → `odrzucone`.
- **Wyjątek dla `domysl` i `wspomnienie`:** mogą wejść z jednego słabego źródła tylko wtedy, gdy odpowiadają na główne pytanie o miejsce (np. „dlaczego rondo nazwano imieniem kogoś, kto nie miał z nim związku”), nic lepszego nie ma, a rodzaj jest oznaczony. Wtedy pewność `srednia`.

## 5. Czego nie wolno

- **Dopisywać wiedzy spoza fragmentów** — nawet oczywistej. Brakujące rzeczy idą do `braki`.
- **Wnioskować o przyczynie ze zbieżności.** Jeśli źródło A mówi „Niemcy nazwali tę ulicę Wilnaer Straße”, a źródło B „osiedle nazywa się Wilno”, nie piszesz, że jedno wynika z drugiego. To dwa osobne fakty.
- **Łączyć dwóch faktów w trzeci**, którego żadne źródło nie formułuje (np. „ulicę nazwano tak celowo, bo stoi przy niej wydział” — jeśli nikt tak nie pisze).
- **Twierdzić braku związku bez dowodu.** „Nic go z tym miejscem nie łączy” wymaga źródła, które to mówi. W przeciwnym razie: „nie wiadomo, czy coś go łączy” / „nie znaleźliśmy związku”.
- **Dopowiadać ironii ani oceny** („paradoksalnie”, „na szczęście”), której źródło nie zawiera.
- **Wkładać słów w usta prawdziwych osób.** Cytat osoby tylko wtedy, gdy jest dosłownie we fragmencie.
- **Pomijać faktu, który komplikuje historię.** Jeśli dotyczy głównego pytania o miejsce, musi być w `fakty`; jeśli podważa planowaną oś, zmieniasz oś.

## 6. Sprzeczności

- Gdy źródła różnią się w dacie, liczbie lub przebiegu zdarzeń, zapisz to w `sprzecznosci[]`: `opis`, `fakty` (id obu wersji), `rozstrzygniecie`.
- Rozstrzygasz na korzyść źródła o wyższej wiarygodności i piszesz dlaczego. Przy równej wiarygodności: `rozstrzygniecie: "nierozstrzygniete"` — wtedy w narracji tego faktu nie używasz, a w tekście do czytania można podać obie wersje.
- Różnica tylko w dokładności („1770” vs „ok. 1770”) to nie sprzeczność — bierzesz ostrożniejszą wersję.

## 7. Cytaty, literatura, licencje

- **Głos epoki** (cytat czytany w słuchowisku) tylko gdy: autor (i tłumacz, jeśli to przekład) ma `autor_rok_smierci` ≤ 1955, a cytat jest dosłownie we fragmencie. Inaczej `glos_epoki: null`, a treść najwyżej jako streszczenie w fakcie rodzaju `literatura`.
- **Obraz z literatury nie jest dowodem.** Jeśli budujesz na nim kontrast „wtedy i dziś”, potrzebujesz też faktu dokumentalnego (statystyka, prasa, reportaż, zdjęcie z opisem).
- **Piosenki:** tytuł, wykonawca, rok — tak. Ani jednego wersu, nawet krótkiego.
- **Prasa, blogi, strony z licencją NC:** fakty piszesz własnymi słowami (i tak to robisz). `cytat` jest tylko dowodem dla kodu, nie trafia do użytkownika.

## 8. Odległość od przystanku

- Fakty o obiektach w promieniu ok. 300 m mogą być kotwicą historii.
- Obiekty dalej (do ok. 500 m) — tylko jeśli są widoczne z trasy albo są częścią tej samej historii (np. ta sama ulica).
- Rzeczy dalekie (inne dzielnice, inne miasta) mogą być haczykiem, ale tylko z mostem z powrotem do przystanku.

## 9. Trudne tematy i teraźniejszość

- Wojna, Powstanie, Zagłada: nie są domyślną osią. Gdy przystanek ma równie mocną lżejszą historię, lżejsza idzie do `historia`, trudna do `warstwy_zapasowe`.
- Gdy trudny fakt **jest** odpowiedzią na główne pytanie o miejsce (np. nazwa upamiętnia egzekucję), nie omijasz go: `ton: tragiczny`.
- Nazwisk ofiar nie wypisujesz z list. Najwyżej liczba i to, co źródło mówi o miejscu.
- Teraźniejszość i plany miasta (budżet obywatelski, konsultacje, inwestycje): tylko jako fakty z danych (`dane_miejskie`). Nie budujesz historii wokół prognoz („za pięć lat będzie tu…”).

## 10. Powody odrzucenia (`odrzucone[].powod`)

| Powód                        | Znaczenie                                                              |
| ---------------------------- | ---------------------------------------------------------------------- |
| `jedno_slabe_zrodlo`         | tylko blog / strona komercyjna, bez potwierdzenia                      |
| `sensacja_bez_potwierdzenia` | twierdzenie sensacyjne z pewnością niższą niż `potwierdzony`           |
| `sprzecznosc`                | przegrało w rozstrzygnięciu sprzeczności                               |
| `wniosek_ze_zbieznosci`      | związek przyczynowy, którego źródło nie podaje                         |
| `deklaracja_jako_fakt`       | źródło podaje deklarację jak fakt, a nie ma niezależnego potwierdzenia |
| `poza_miejscem`              | dotyczy czegoś daleko i nie ma mostu                                   |
| `licencja`                   | cytat spoza domeny publicznej, tekst piosenki                          |
| `nieistotne`                 | prawdziwe, ale nie wnosi nic do tego miejsca                           |

Do `odrzucone` wpisuj rzeczy, które ktoś mógłby chcieć użyć (ciekawe, ale niepewne), a nie każde zdanie z fragmentów. Zwykle 2–10 pozycji.
