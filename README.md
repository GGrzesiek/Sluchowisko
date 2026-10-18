# Słuchowisko

Aplikacja, która w trakcie jazdy autobusem lub tramwajem po Warszawie opowiada historie mijanych miejsc w formie
krótkich słuchowisk. Pasażer podaje numer boczny pojazdu albo skanuje kod QR z naklejki, a aplikacja pokazuje trasę,
najbliższe przystanki i historię miejsca, które właśnie mija: nagranie, tekst do przeczytania i zdjęcia. Każde zdanie
historii ma źródło, które można otworzyć („Skąd to wiemy?”).

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
linii 22: https://backend-6s5kkpohyq-lm.a.run.app/api/vehicles/?line=22&live=1. Numer z pola `number` wpisz w
aplikacji.

Linie z historiami:

| Linia  | Odcinek                               | Okolica            |
| ------ | ------------------------------------- | ------------------ |
| 🚋 22  | Powązkowska ↔ Pl. Starynkiewicza     | Wola               |
| 🚋 18  | Królikarnia ↔ Wynalazek              | Mokotów, Służewiec |
| 🚌 179 | Metro Natolin ↔ Miklaszewskiego      | Ursynów            |
| 🚌 169 | Dw. Wschodni (Kijowska) ↔ Rondo Żaba | Praga-Północ       |
| 🚌 117 | Rondo Waszyngtona ↔ Os. Jantar       | Saska Kępa, Gocław |

## Założenia

- **Każde zdanie ma źródło.** Historia powstaje tylko z faktów zebranych z otwartych źródeł, a pasażer może otworzyć
  źródło każdego z nich.
- **Zwyczajne miejsca, nie daty.** Opowiadamy, co było w mijanym miejscu, jak wyglądało i jak działało. Wojna i
  Powstanie są jedną z warstw, nie osią aplikacji.
- **Jedna historia na zespół przystankowy.** To samo nagranie gra niezależnie od linii i kierunku jazdy.
- **Bez AI w działającej aplikacji.** Historie, nagrania i zdjęcia są przygotowane wcześniej. Aplikacja nie wywołuje
  modeli językowych, a głos lektora jest oznaczony jako AI.
- **Dane miasta tylko przez backend.** Aplikacja łączy się wyłącznie z naszym backendem; API m.st. Warszawy wywołuje
  backend.

## Jak to działa

```
API m.st. Warszawy ──▶ przystanki, linie, odjazdy ──▶ trasy linii ──────┐
                  └──▶ pozycje pojazdów co 10 s ────────────────────────┤
                                                                        ▼
otwarte źródła ──▶ fakty ze źródłem ──▶ historie ──▶ weryfikacja ──▶ backend ──▶ aplikacja ◀─────────┐
                                                          │                                          │
                                                          └──▶ nagrania, zdjęcia ──▶ Cloud Storage ──┘
```

1. **Trasy.** Z API m.st. Warszawy pobieramy przystanki, linie na przystankach i odjazdy. Kolejność przystanków
   każdej linii odtwarzamy z rozkładu jednego kursu.
2. **Pozycja pojazdu.** Backend co 10 s zna położenie pojazdów z API m.st. Warszawy. Dopasowuje pojazd do kierunku
   jazdy, przesuwa go wzdłuż trasy o drogę przejechaną od ostatniego odczytu i wylicza minione, bieżący i następne
   przystanki z czasem dojazdu.
3. **Fakty.** Skrypt bez AI zbiera dla każdego zespołu przystankowego fakty z otwartych źródeł. Każdy fakt ma źródło,
   licencję i dosłowny fragment tekstu.
4. **Historie.** Agent oparty na modelu językowym pisze historie wyłącznie z zebranych faktów, a weryfikator sprawdza
   każde zdanie. Historie powstają przed uruchomieniem aplikacji; aplikacja nie wywołuje modeli językowych.
   Szczegóły: [docs/AI_USAGE.md](docs/AI_USAGE.md).
5. **Słuchowiska.** Historię czytają syntetyczne głosy ElevenLabs; muzyka i efekty dźwiękowe też są generowane przez
   AI. Nagrania i zdjęcia leżą w publicznym buckecie Google Cloud Storage.
6. **Aplikacja.** Strona statyczna. Z backendem łączy się przez WebSocket i dostaje aktualną trasę, historię
   następnego przystanku i adres jej nagrania.

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

Pasażer nie instaluje aplikacji: wystarczy naklejka z kodem QR w pojeździe, która otwiera stronę z numerem bocznym i
linią w adresie. Kolejną linię dodaje się, budując jej trasy z rozkładu (`build_routes`) i przygotowując historie dla
zespołów przystankowych, których jeszcze nie opisaliśmy; historie z przystanków wspólnych z innymi liniami działają od
razu. Aplikacja jest stroną statyczną, a backend na Cloud Run uruchamia się na żądanie, więc koszt utrzymania rośnie
dopiero z liczbą pasażerów.

## Uruchomienie u siebie

Wymagane: Python 3.12, Node.js 22, klucz do API m.st. Warszawy.

```bash
git clone https://github.com/GGrzesiek/opendatahackathon42.git
cd opendatahackathon42
cp .env.example .env
```

W `.env` wpisz klucz w `ZTM_API_KEY`. Pozostaw `DATABASE_URL` pusty, żeby backend użył lokalnej bazy SQLite.

Backend:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py sync_city_data
.venv/bin/python manage.py build_routes --line 22
.venv/bin/python manage.py runserver
```

`build_routes` powtórz dla linii 18, 179, 169 i 117. Numery pojazdów jadących teraz linią 22 wypisze, w osobnym
terminalu, `.venv/bin/python manage.py live_vehicles --line 22`. API m.st. Warszawy odpowiada tylko z polskiego adresu
IP.

Aplikacja, w drugim terminalu:

```bash
cd web
npm ci
VITE_API_URL=http://localhost:8000 npm run dev
```

Otwórz adres, który poda Vite, i wpisz jeden z tych numerów.

## Dane m.st. Warszawy

API: `https://dane.um.warszawa.pl/api/action/<akcja>` oraz usługi mapowe Biura Geodezji i Katastru.

| Zbiór                                 | Akcja lub warstwa                                                                          | Do czego służy                                      |
| ------------------------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| Lokalizacja pojazdów                  | `get_ztm_lokalizacja_pojazdow`                                                             | pozycja pojazdu na żywo                             |
| Przystanki komunikacji miejskiej      | `get_ztm_przystanki_komunikacji_miejskiej`                                                 | nazwy i współrzędne przystanków                     |
| Linie na przystanku                   | `get_ztm_lista_linii_na_przystanku`                                                        | które linie zatrzymują się na przystanku            |
| Odjazdy linii z przystanku            | `get_ztm_odjazdy_linii_z_przystanku`                                                       | kolejność przystanków na trasie                     |
| Rejestr Cen Nieruchomości             | `get_bgk_rcn`                                                                              | mediana ceny m² w okolicy przystanku                |
| Budżet obywatelski                    | `get_cks_budzet_obywatelski`                                                               | zrealizowane projekty w okolicy przystanku          |
| Granice dzielnic, rejestr drzew (WFS) | `GRANICE_DZIELNIC`, `ZIELEN_DRZEWA`                                                        | dzielnica przystanku, największe drzewa w okolicy   |
| Plany i fotoplany (WMS)               | `RASTER_FOTOPLAN_1935`, `RASTER_PLAN_1939`, `RASTER_ORTOFOTO_1945`, `RASTER_FOTOPLAN_2021` | jak wyglądała okolica przystanku w czterech epokach |

## Pozostałe źródła i licencje

| Źródło                   | Co z niego bierzemy                                      | Licencja               |
| ------------------------ | -------------------------------------------------------- | ---------------------- |
| OpenStreetMap (Overpass) | ulice, patroni, dawne nazwy, pomniki i tablice w okolicy | ODbL                   |
| Wikipedia (pl)           | hasła o dzielnicach, ulicach, obiektach i patronach      | CC BY-SA 4.0           |
| Wikidata                 | patroni, daty, status zabytku                            | CC0                    |
| Warszawikia              | hasła o przystankach i ulicach                           | CC BY-SA               |
| Wikimedia Commons        | zdjęcia z podpisem i autorem                             | licencja każdego pliku |

Pełna lista sprawdzonych źródeł, z decyzją, które bierzemy automatycznie, a które tylko jako link:
[collector/README.md](collector/README.md#sources).

Zasady, których się trzymamy:

- Treści z domeny publicznej, CC0, CC BY i CC BY-SA pokazujemy z podpisem autora i licencji.
- Artykułów prasowych i blogów nie kopiujemy; pokazujemy link.
- Tekstów piosenek nie cytujemy; podajemy tylko tytuł, wykonawcę i link.
- Nazwisk ofiar nie wyciągamy automatycznie.
- Głos lektora jest syntetyczny i w aplikacji oznaczony jako głos AI.

## Zespół

| Osoba    | Rola                                  | GitHub                                         |
| -------- | ------------------------------------- | ---------------------------------------------- |
| Grzesiek | DevOps, infrastruktura, nagrania tras | [@GGrzesiek](https://github.com/GGrzesiek)     |
| Hubert   | Backend, dane o komunikacji           | [@hububiq](https://github.com/hububiq)         |
| Kuba     | Pitch, agent historii                 | [@Jzackiewicz](https://github.com/Jzackiewicz) |
| Masza    | Frontend, zbieranie faktów            | [@MaryTim](https://github.com/MaryTim)         |
| Wojtek   | Frontend                              | [@xwojtuss](https://github.com/xwojtuss)       |

Zasady pracy w repozytorium, CI i wdrażanie: [docs/workflow.md](docs/workflow.md).
