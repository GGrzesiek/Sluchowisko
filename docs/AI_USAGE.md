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

Historie przygotowuje agent oparty na modelu Claude (Anthropic), uruchamiany w Claude Code ze skillami
(`.claude/skills/`) i programem `story_agent`. Działa przed uruchomieniem aplikacji, w kilku krokach:

1. Skrypt bez AI zbiera dane o okolicy każdego przystanku: otwarte dane m.st. Warszawy, OpenStreetMap, Wikidata,
   Wikipedię, Warszawikię i zdjęcia z licencją.
2. Model czyta zebrany materiał, dociąga brakujące źródła z listy dozwolonych serwisów, wybiera fakty i układa plan
   historii. Każdy fakt ma dosłowny cytat ze źródła, który program porównuje z tekstem źródła; program sprawdza też
   wiarygodność źródeł i prawa do cytatów.
3. Model pisze scenariusz słuchowiska (jeden, dwa lub trzy głosy, dźwięki, pauzy) i dłuższy tekst do czytania
   wyłącznie z faktów z planu. Każde zdanie wskazuje swoje fakty. Głos epoki czyta tylko dosłowne cytaty z domeny
   publicznej. Każdy dźwięk ilustruje fakt ze źródła.
4. Model przygotowuje tekst dla syntezatora (liczby i skróty słownie, wskazówki intonacji) i opisy dźwięków. Program
   sprawdza, że treść się nie zmieniła.
5. Program nagrywa głosy, generuje dźwięki i muzykę w ElevenLabs, miksuje je i sprawdza długość nagrania.
6. Człowiek przegląda historię i nagranie, zanim trafią do aplikacji.

Research i tekst historii dla jednego przystanku przygotowuje też subagent `stop-story-writer`
(`.claude/agents/stop-story-writer.md`). Sam wyszukuje i sprawdza źródła w sieci, zapisuje fakty z oceną pewności
i pisze narrację (20–45 s) oraz tekst do czytania później. Każde zdanie musi mieć pokrycie w źródłach; rozbieżności
między źródłami i fakty z jednego słabego źródła oddaje osobno, do sprawdzenia przez człowieka.

## Przy tworzeniu oprogramowania

Zespół korzystał z asystentów AI (m.in. Claude Code) przy przeglądzie źródeł i API miasta, pisaniu kodu, konfiguracji
infrastruktury w Google Cloud (Terraform, GitHub Actions), dokumentacji i opisów zadań. Każda zmiana przechodzi przez pull request i automatyczne testy.
