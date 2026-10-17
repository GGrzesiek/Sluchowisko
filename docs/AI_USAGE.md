# Wykorzystanie sztucznej inteligencji

Opis zgodny z § 4 ust. 4 regulaminu Warsaw Open Data Hackathon 2026.

## W aplikacji

- Aplikacja nie korzysta z modeli językowych w trakcie działania. Wszystkie historie są przygotowane wcześniej
  i zapisane jako pliki statyczne.
- Słuchowiska czytają syntetyczne głosy (ElevenLabs). Efekty dźwiękowe i muzyka w słuchowiskach też są generowane
  przez AI (ElevenLabs). W aplikacji są oznaczone jako AI.
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
3. Wybiera historię, która łączy się z miejscem (co tu się wydarzyło, co widać z okna, skąd nazwa), i pisze narrację
   na 20–45 sekund oraz dłuższy tekst do czytania później. Każde zdanie ma pokrycie w źródłach.
4. Przed oddaniem sprawdza oba teksty zdanie po zdaniu: czy każde ma źródło, czy nie wyciąga wniosków z samej
   zbieżności faktów i czy nie cytuje tekstów spoza domeny publicznej.
5. Człowiek przegląda historię i jej źródła, zanim trafi do aplikacji.

## Przy tworzeniu oprogramowania

Zespół korzystał z asystentów AI (m.in. Claude Code) przy przeglądzie źródeł i API miasta, pisaniu kodu, konfiguracji
infrastruktury w Google Cloud (Terraform, GitHub Actions), dokumentacji i opisów zadań. Każda zmiana przechodzi przez pull request i automatyczne testy.
