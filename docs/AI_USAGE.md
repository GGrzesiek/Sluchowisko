# Wykorzystanie sztucznej inteligencji

Opis zgodny z § 4 ust. 4 regulaminu Warsaw Open Data Hackathon 2026.

## W aplikacji

- Aplikacja nie korzysta z modeli językowych w trakcie działania. Wszystkie historie są przygotowane wcześniej
  i zapisane jako pliki statyczne.
- Słuchowiska czyta syntetyczny głos (ElevenLabs). Ambient i głosy w tle w słuchowiskach też są generowane przez AI
  (ElevenLabs). W aplikacji są oznaczone jako AI.
- Jedyny obraz wygenerowany przez AI to ilustracja autobusu „ogórek” w animacji na ekranie startowym i na ekranie
  wyszukiwania pojazdu. Historie nie pokazują obrazów wygenerowanych przez AI: zdjęcia i mapy pochodzą ze źródeł
  z licencją, a ich podpisy podaje źródło.

## Przygotowanie historii

Historie przygotowuje agent oparty na modelu Claude (Anthropic), uruchamiany w Claude Code jako subagent
`stop-story-writer` (`.claude/agents/stop-story-writer.md`). Działa przed uruchomieniem aplikacji, osobno dla każdego
przystanku:

1. Dostaje nazwę przystanku i sam wyszukuje źródła w sieci: encyklopedie, serwisy o historii Warszawy, opracowania
   naukowe i źródła z epoki.
2. Zapisuje fakty z oceną pewności. Fakt z jednego słabego źródła nie trafia do historii, a rozbieżności między
   źródłami (np. różne daty) oddaje osobno.
3. Wybiera wątek, który łączy się z miejscem (co tu się wydarzyło, co widać z okna, skąd nazwa), i układa z dwóch–
   czterech faktów scenariusz słuchowiska na ok. 40 sekund (20–45 s) dla jednego narratora oraz dłuższy tekst do
   czytania później. Każde zdanie ma pokrycie w źródłach. Scenariusz opisuje też ambient zgodny z treścią i najwyżej
   jeden–dwa krótkie głosy w tle, które budują klimat, ale nie przekazują faktów.
4. Pisze tekst narracji pod mowę, nie pod czytanie: zdania różnej długości, bez wyliczanek, liczby słownie, najwyżej
   trzy znaczniki audio (np. ton ciepły, zamyślony, pauza przed puentą) i zapisy wymowy dla skrótowców i obcych
   nazw.
5. Dobiera od jednego do pięciu zdjęć z Wikimedia Commons z okolicy przystanku, z podpisem, autorem i licencją
   przepisanymi z Commons, bez generowania obrazów. Gdy żadne zdjęcie nie pasuje, historia dostaje starą mapę
   Warszawy z serwisu map m.st. Warszawy (1945, 1935, 1939, 2021).
6. Przed oddaniem sprawdza oba teksty zdanie po zdaniu: czy każde ma źródło, czy nie wyciąga wniosków z samej
   zbieżności faktów i czy nie cytuje tekstów spoza domeny publicznej.
7. Człowiek przegląda historię i jej źródła, zanim trafi do aplikacji.

Nagranie powstaje skryptem `tools/render_drama.py`. Narrację czyta syntetyczny głos ElevenLabs (model Eleven v4,
z ustalonymi ustawieniami stabilności i podobieństwa głosu oraz stałym seedem, żeby kolejne nagrania brzmiały tak
samo). Ambient i głosy w tle też generuje ElevenLabs, a skrypt składa je w jeden plik MP3 i ścisza tło pod głosem
narratora. Człowiek odsłuchuje nagranie, zanim trafi do aplikacji.

## Przy tworzeniu oprogramowania

Zespół korzystał z asystentów AI (m.in. Claude Code) przy przeglądzie źródeł i API miasta, pisaniu kodu, konfiguracji
infrastruktury w Google Cloud (Terraform, GitHub Actions), dokumentacji i opisów zadań. Prezentację przygotowaliśmy z pomocą AI. Każda zmiana przechodzi przez pull request i automatyczne testy.
