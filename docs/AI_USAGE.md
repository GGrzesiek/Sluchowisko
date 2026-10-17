# Wykorzystanie sztucznej inteligencji

Opis zgodny z § 4 ust. 4 regulaminu Warsaw Open Data Hackathon 2026.

## W aplikacji

- Aplikacja nie korzysta z modeli językowych w trakcie działania. Wszystkie historie są przygotowane wcześniej
  i zapisane jako pliki statyczne.
- Narrację czyta syntetyczny głos (ElevenLabs). W aplikacji jest oznaczony jako głos AI.
- Aplikacja nie pokazuje obrazów wygenerowanych przez AI. Zdjęcia i mapy pochodzą ze źródeł z licencją, a ich podpisy
  podaje źródło.

## Przygotowanie historii

Historie przygotowuje agent oparty na modelu Claude (Anthropic). Działa przed uruchomieniem aplikacji, w kilku krokach:

1. Skrypt bez AI zbiera dane o okolicy każdego przystanku: otwarte dane m.st. Warszawy, OpenStreetMap, Wikidata,
   Wikipedię i zdjęcia z licencją.
2. Model wybiera fakty i układa plan historii. Każdy fakt ma dosłowny cytat ze źródła, który program porównuje
   z tekstem źródła.
3. Model pisze narrację i dłuższy tekst wyłącznie z faktów zatwierdzonych w planie.
4. Program i drugi przebieg modelu sprawdzają każde zdanie: czy ma źródło, czy źródło mówi to samo i czy tekst jest
   poprawną, naturalną polszczyzną.
5. Człowiek przegląda historię przed nagraniem.
6. Zatwierdzony tekst czyta syntetyczny głos.

## Przy tworzeniu oprogramowania

Zespół korzystał z asystentów AI (m.in. Claude Code) przy przeglądzie źródeł i API miasta, pisaniu kodu, dokumentacji
i opisów zadań. Każda zmiana przechodzi przez pull request i automatyczne testy.
