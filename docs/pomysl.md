# Muzeum w autobusie — pomysł i zakres

Streszczenie tablicy Miro „Hackathon brainstorming” (stan na 15.10). Nazwa robocza.

## Pomysł

Jedziesz autobusem albo tramwajem, a aplikacja opowiada ci krótkie, sprawdzone historie miejsc, które właśnie mijasz.

- **Dla kogo:** warszawiacy w codziennych dojazdach, nie turyści. Zamiast scrollowania — 1–2 minuty o tym, co jest za oknem.
- **Problem:** ludzie mieszkają w miejscach, nie wiedząc, co się tam działo, i nie czują się z nimi związani. Historia istnieje, ale leży w muzeach, archiwach i aplikacjach do spacerów — tarcie jest za duże.
- **Skala:** ok. 930 mln przejazdów ZTM rocznie; wg różnych szacunków 40%+ mieszkańców urodziło się poza Warszawą.
- **Ton:** codzienna historia — patroni ulic, dawne nazwy, bazary, kina, co się zmieniło. Wojna to jedna z wielu warstw, nie oś.

## Nasza luka: trzy rzeczy naraz

1. Cała sieć komunikacji, nie jedna trasa.
2. Automatycznie z danych miasta.
3. Zwykłe miejsca, nie tylko zabytki.

Jeśli w pitchu wypadnie którakolwiek z trzech, jesteśmy kolejną apką-przewodnikiem.

## Zaufanie (pytanie urzędnika)

Historie powstają z góry, nie na żywo, więc każdy słyszy to samo i da się to sprawdzić. LLM pisze tylko z
dostarczonych źródeł, drugi przebieg sprawdza każde zdanie. We wdrożeniu treści zatwierdza redakcja (np. DSH albo muzeum).
W kodzie: `pipeline/stories.py` (tylko źródła) + `pipeline/verify.py` (drugi przebieg + źródło z linkiem przy każdym zdaniu).

## Zakres na 24 godziny

**Robimy**

- Jedna linia, jeden kierunek, 10–15 przystanków
- Dane: przystanki, trasa i pozycje pojazdów ZTM, budżet obywatelski
- Kontekst: Wikipedia, OSM i Wikidata (patroni ulic, dawne nazwy)
- Historie 30–60 s, z góry, tylko ze źródeł, z weryfikatorem
- Lektor ElevenLabs, pliki nagrane z góry
- UI: pasek trasy, karta historii z napisami, „Skąd to wiemy?”
- Symulacja przejazdu z nagranych pozycji ZTM
- Nagrane demo, deck, dokumentacja

**Jeśli zostanie czas:** suwak 1945 ↔ dziś z map miasta, automatyczne rozpoznanie pojazdu, widok na monitor w pojeździe, tło dźwiękowe.

**Nie robimy:** obrazów AI „jak to wyglądało”, muzyki epoki, synchronizacji „spójrz w lewo”, całej sieci w demo (tylko
liczby w pitchu), innych języków / rotacji / „dziś w historii” (tylko w pitchu), drzew-świadków i starego API, wpisów
mieszkańców, kont i logowania.

## Przykładowa trasa (tablica „jedna trasa”)

Tramwaj 4 · Rondo Żaba → Żerań Wschodni · Targówek i Białołęka · 13 przystanków. Sześć historii (Rondo Żaba,
Julianowska, Rembielińska, Poborzańska, Metro Bródno, Inowłodzka) — szkice faktów są w `data/sources/tram-4/manual/`,
jeszcze bez linków do źródeł.

## Do ustalenia

- Linia demo (tramwaj 4 rozpisany; kandydaci z tablicy: Okopowa, pl. Zawiszy)
- Wyzwanie: „Złap oddech” — jak opowiadamy pomysł w tej kategorii
- Model: Gemini Flash za darmo, Bielik jeśli dadzą API
- Podział ról w zespole
