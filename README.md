# Słuchowisko

Aplikacja, która w trakcie jazdy autobusem lub tramwajem po Warszawie opowiada historie mijanych miejsc w formie
krótkich słuchowisk. Pasażer podaje numer boczny pojazdu albo skanuje kod QR z naklejki, a aplikacja pokazuje trasę,
najbliższe przystanki i historię miejsca, które właśnie mija: nagranie, tekst do przeczytania i zdjęcia. Każde zdanie
historii ma źródło, które można otworzyć z listy „Źródła”.

Projekt na Warsaw Open Data Hackathon 2026, wyzwanie „Złap oddech”: dla mieszkańców, którzy codziennie jeżdżą tą samą
trasą i nie mają czasu szukać historii swojej okolicy. Opowiadamy o tym, jak zwyczajne miejsca się zmieniały: co tu
było, jak wyglądało i jak działało.

## Wypróbuj

| Wersja      | Adres                                         |
| ----------- | --------------------------------------------- |
| Produkcyjna | http://ggrzesiek.dev/opendatahackathon42/     |
| Rozwojowa   | http://ggrzesiek.dev/opendatahackathon42/dev/ |

Link z naklejki w pojeździe ma postać `…/opendatahackathon42/?vehicle=<numer boczny>&line=<linia>`.

Numery pojazdów, które jadą teraz daną linią, razem z kierunkiem i następnym przystankiem, podaje backend, np. dla
linii 4: https://backend-6s5kkpohyq-lm.a.run.app/api/vehicles/?line=4&live=1. Numer z pola `number` wpisz w
aplikacji.

Historie mamy na razie dla kilku przystanków tramwaju 4 oraz dla testowych linii 161 i N50. Historie są przypisane do
zespołów przystankowych, a nie do linii, więc pokrycie zależy od przystanków. Które przystanki linii mają opublikowaną
historię, pokazuje pole `storyStatus` w `/api/lines/<linia>/stories/`, a listę wszystkich historii `/api/stories/`.

## Założenia

- **Każde zdanie ma źródło.** Historia powstaje tylko z faktów zebranych z otwartych źródeł, a pasażer może otworzyć
  źródło każdego z nich.
- **Zwyczajne miejsca, nie daty.** Opowiadamy, co było w mijanym miejscu, jak wyglądało i jak działało. Wojna i
  Powstanie są jedną z warstw, nie osią aplikacji.
- **Jedna historia na zespół przystankowy.** To samo nagranie gra niezależnie od linii i kierunku jazdy.
- **Bez AI w działającej aplikacji.** Historie, nagrania i zdjęcia są przygotowane wcześniej. Aplikacja nie wywołuje
  modeli językowych, a głos lektora jest syntetyczny.
- **Dane miasta tylko przez backend.** Aplikacja łączy się wyłącznie z naszym backendem; API m.st. Warszawy wywołuje
  backend.

## Jak to działa

```
API m.st. Warszawy ──▶ przystanki, linie, odjazdy ──▶ trasy linii ──────┐
                  └──▶ pozycje pojazdów co 10 s ────────────────────────┤
                                                                        ▼
otwarte źródła ──▶ fakty ze źródłem ──▶ historie ──▶ przegląd człowieka ──▶ backend ──▶ aplikacja ◀─────────┐
                                                          │                                          │
                                                          └──▶ nagrania, zdjęcia ──▶ Cloud Storage ──┘
```

1. **Trasy.** Z API m.st. Warszawy pobieramy przystanki, linie na przystankach i odjazdy. Kolejność przystanków
   każdej linii odtwarzamy z rozkładu jednego kursu.
2. **Pozycja pojazdu.** Backend co 10 s zna położenie pojazdów z API m.st. Warszawy. Wybiera trasę zgodną z kierunkiem
   jazdy, rzutuje na nią położenie pojazdu i wylicza minione, bieżący i następne przystanki z czasem dojazdu.
3. **Fakty.** Agent historii (`stop-story-writer`) wyszukuje fakty o zespole przystankowym w otwartych źródłach i
   w trakcie pracy prowadzi rejestr faktów ze źródłem i stopniem pewności. Fakt z jednego słabego źródła nie trafia
   do historii. Rejestr nie jest zapisywany w bazie, do backendu trafia gotowa historia ze źródłami.
4. **Historie.** Ten sam agent, oparty na modelu językowym, pisze historię wyłącznie z zebranych faktów i sam
   sprawdza każde zdanie przed oddaniem. Człowiek przegląda historię i dopiero wtedy zmienia jej status na
   `verified`; aplikacja dostaje tylko takie historie. Historie powstają przed uruchomieniem aplikacji; aplikacja
   nie wywołuje modeli językowych. Szczegóły: [docs/AI_USAGE.md](docs/AI_USAGE.md).
5. **Słuchowiska.** Historię czytają syntetyczne głosy ElevenLabs; muzyka i efekty dźwiękowe też są generowane przez
   AI. Nagrania i zdjęcia leżą w buckecie Google Cloud Storage.
6. **Aplikacja.** Strona statyczna. Z backendem łączy się przez WebSocket i dostaje aktualną trasę, historię
   przystanku, przy którym jest pojazd, i adres nagrania przystanku, który jest następny.

| Część          | Technologia                                         | Gdzie działa                                |
| -------------- | --------------------------------------------------- | ------------------------------------------- |
| Aplikacja      | React, Vite, Tailwind                               | GitHub Pages                                |
| Backend        | Django, Django REST Framework, Channels (WebSocket) | Google Cloud Run                            |
| Baza danych    | PostgreSQL 16                                       | Google Cloud SQL                            |
| Zdjęcia, audio | pliki statyczne                                     | Google Cloud Storage (publiczny bucket)     |
| Infrastruktura | Terraform, GitHub Actions                           | wdrożenie po każdej zmianie w `development` |

Serwery API m.st. Warszawy odpowiadają tylko na zapytania z polskich adresów IP, dlatego backend działa w regionie
Google Cloud `europe-central2` (Warszawa) i sam pobiera pozycje pojazdów.

## Wdrożenie

Pasażer nie instaluje aplikacji: wystarczy kod QR, który otwiera stronę z numerem taborowym i linią w adresie, albo
wpisanie numeru pojazdu. Kolejną linię dodaje się, budując jej trasy z rozkładu (`build_routes`) i przygotowując historie dla
zespołów przystankowych, których jeszcze nie opisaliśmy, bo nie wszystkie przystanki linii mają już historię; historie z przystanków wspólnych z innymi liniami działają od
razu. Aplikacja jest stroną statyczną, a backend działa na Cloud Run.

## Uruchomienie u siebie

Wymagane: Node.js 22. Do własnego backendu także Python 3.12 i klucz do API m.st. Warszawy.

```bash
git clone https://github.com/GGrzesiek/opendatahackathon42.git
cd opendatahackathon42
```

**Sama aplikacja, z naszym backendem.** Bez klucza i bez Pythona:

```bash
make web
```

Otwórz adres, który poda Vite, i wpisz numer pojazdu z listy z sekcji „Wypróbuj”.

**Aplikacja z własnym backendem.** W `.env` (powstaje z `.env.example`) wpisz klucz w `ZTM_API_KEY`, a `DATABASE_URL`
zostaw pusty, żeby backend użył lokalnej bazy SQLite. API m.st. Warszawy odpowiada tylko z polskiego adresu IP.

```bash
make setup
make backend
```

`make setup` instaluje zależności, pobiera z API m.st. Warszawy przystanki i linie (kilka minut) i buduje trasy linii wymienionych
w `DEMO_LINES` w `Makefile`. Lokalna baza nie ma historii, więc aplikacja pokaże trasę i przystanki bez nagrań. W drugim
terminalu:

```bash
make web API_URL=http://localhost:8000
.venv/bin/python manage.py live_vehicles --line 4
```

Drugie polecenie wypisuje numery pojazdów, które jadą teraz linią 4.

## Dane m.st. Warszawy

API: `https://dane.um.warszawa.pl/api/action/<akcja>` oraz usługi mapowe Biura Geodezji i Katastru.

| Zbiór                            | Akcja lub warstwa                                                                          | Do czego służy                                            |
| -------------------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| Lokalizacja pojazdów             | `get_ztm_lokalizacja_pojazdow`                                                             | pozycja pojazdu na żywo                                   |
| Przystanki komunikacji miejskiej | `get_ztm_przystanki_komunikacji_miejskiej`                                                 | nazwy i współrzędne przystanków                           |
| Linie na przystanku              | `get_ztm_lista_linii_na_przystanku`                                                        | które linie zatrzymują się na przystanku                  |
| Odjazdy linii z przystanku       | `get_ztm_odjazdy_linii_z_przystanku`                                                       | kolejność przystanków na trasie                           |
| Plany i fotoplany (WMS)          | `RASTER_FOTOPLAN_1935`, `RASTER_PLAN_1939`, `RASTER_ORTOFOTO_1945`, `RASTER_FOTOPLAN_2021` | zdjęcia w historii: okolica przystanku w czterech epokach |

## Pozostałe źródła i licencje

| Źródło            | Co z niego bierzemy                                 | Licencja               |
| ----------------- | --------------------------------------------------- | ---------------------- |
| Wikipedia (pl)    | hasła o dzielnicach, ulicach, obiektach i patronach | CC BY-SA 4.0           |
| Wikidata          | patroni, daty, status zabytku                       | CC0                    |
| Warszawikia       | hasła o przystankach i ulicach                      | CC BY-SA               |
| Wikimedia Commons | zdjęcia z podpisem i autorem                        | licencja każdego pliku |

Przy każdej historii aplikacja pokazuje listę źródeł, z których pochodzą jej fakty.

Zasady, których się trzymamy:

- Treści z domeny publicznej, CC0, CC BY i CC BY-SA pokazujemy z podpisem autora i licencji.
- Artykułów prasowych i blogów nie kopiujemy; pokazujemy link.
- Tekstów piosenek nie cytujemy; podajemy tylko tytuł, wykonawcę i link.
- Nazwisk ofiar nie wyciągamy automatycznie.
- Głos lektora jest syntetyczny (ElevenLabs); opisujemy to w [docs/AI_USAGE.md](docs/AI_USAGE.md).

## Zespół

| Osoba    | Rola                                  | GitHub                                         |
| -------- | ------------------------------------- | ---------------------------------------------- |
| Grzesiek | DevOps, infrastruktura, nagrania tras | [@GGrzesiek](https://github.com/GGrzesiek)     |
| Hubert   | Backend, dane o komunikacji           | [@hububiq](https://github.com/hububiq)         |
| Kuba     | Pitch, AI                             | [@Jzackiewicz](https://github.com/Jzackiewicz) |
| Masza    | Frontend, Design, AI                  | [@MaryTim](https://github.com/MaryTim)         |
| Wojtek   | Frontend, Design, Backend             | [@xwojtuss](https://github.com/xwojtuss)       |

Zasady pracy w repozytorium, CI i wdrażanie: [docs/workflow.md](docs/workflow.md).
