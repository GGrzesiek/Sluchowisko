# Przykłady rozumowania

**Uwaga:** przykłady pokazują przede wszystkim sposób pracy. Gdy przystanek z wejścia jest tym samym miejscem (Okopowa i Francuska są przystankami demo), możesz wykorzystać fakty z przykładu, ale każdy z nich musi mieć dowód we fragmencie: z wejścia albo dociągniętym ze źródła wskazanego w przykładzie. Bez dowodu fakt idzie do `braki`.

Wejście i wyjście są skrócone: pokazane są tylko pola, które ilustrują daną decyzję.

Spis treści

1. Okopowa — most C, sposób „ślad”, trudna warstwa odłożona
2. Rondo Żabczyńskiego — most E, domysł z atrybucją
3. PKP Zacisze-Wilno — deklaracja vs fakt, zbieżność to nie przyczyna

---

## 1. Okopowa (tramwaj, Wola)

**Wejście (skrót)**

- `s1` instytucja — Muzeum Warszawy, „Jak powstała ulica Okopowa”. Fragmenty: w 1770 r. z obawy przed dżumą marszałek Lubomirski kazał usypać wał z fosą; zarazy nie było, miasto uratowała zima; wał był granicą celną i hamował rozwój miasta; ulica biegła po wewnętrznej stronie wału.
- `s2` varsavianistyka — Warszawikia, „Ulica Okopowa”: przebieg Towarowej i Okopowej to niemal dokładnie linia dawnego wału; Kercelak założony w 1867 r. przy rogatce; dziś nazwa ronda.
- `s3` portal_lokalny — PTTK, kamienie pamięci: w czasie okupacji Okopowa była granicą getta; egzekucja przy rogu z Wolską.

**Kluczowe decyzje**

- Nazwa i kształt ulicy są historią → most **C**. Pasażer jedzie po linii wału → sposób **`slad`**, bo związek przyczynowy („ulica biegnie linią wału”) podaje źródło, a nie my.
- Getto i egzekucje to prawda o tym miejscu, ale nie odpowiedź na pytanie „skąd ta nazwa i ten kształt”. Ta sama ulica ma równie mocną, lżejszą historię → trudna warstwa idzie do `warstwy_zapasowe` z `ton: tragiczny`, nie znika.
- Haczyk: Kercelak — da się wrócić do miejsca (nazwa ronda, które mijasz).

**Wyjście (skrót)**

```json
{
  "fakty": [
    {
      "id": "F1",
      "tekst": "W 1770 r. marszałek Stanisław Lubomirski kazał usypać wokół Warszawy wał z fosą z obawy przed dżumą.",
      "dowody": [{ "fragment": "s1#1", "cytat": "…" }],
      "rodzaj": "fakt",
      "pewnosc": "potwierdzony",
      "era": "przed1800"
    },
    {
      "id": "F2",
      "tekst": "Zaraza nie dotarła do Warszawy; według Muzeum Warszawy miasto uratowała zima.",
      "dowody": [{ "fragment": "s1#2", "cytat": "…" }],
      "rodzaj": "fakt",
      "pewnosc": "potwierdzony",
      "era": "przed1800"
    },
    {
      "id": "F4",
      "tekst": "Dzisiejszy przebieg Okopowej i Towarowej to niemal dokładnie linia dawnego wału.",
      "dowody": [{ "fragment": "s2#1", "cytat": "…" }],
      "rodzaj": "fakt",
      "pewnosc": "srednia",
      "era": "przed1800"
    }
  ],
  "kandydaci_osi": [
    {
      "os": "Ulica biegnie linią wału przeciw dżumie",
      "most_typ": "C",
      "uzasadnienie": "Nazwa i kształt ulicy, po której jedziesz, wynikają z wału."
    },
    {
      "os": "Okopowa jako granica getta",
      "most_typ": "A",
      "uzasadnienie": "Prawdziwe i ważne, ale ton tragiczny; lżejsza warstwa ma równie mocny most."
    }
  ],
  "historia": {
    "status": "ok",
    "os": "Okopowa jest kręta, bo wciąż biegnie linią wału usypanego w 1770 r. przeciw dżumie.",
    "pytanie_sluchacza": "Dlaczego ta ulica nazywa się Okopowa i biegnie właśnie tak?",
    "most": {
      "typ": "C",
      "zdanie_robocze": "Jedziesz po linii dawnego wału — stąd nazwa i kształt ulicy.",
      "fakty": ["F1", "F4"]
    },
    "haczyk": { "fakty": ["F6"], "dlaczego_ten": "Kercelak pozwala wrócić do miejsca: została po nim nazwa ronda." },
    "sposob_zmiany": "slad",
    "kroki": [
      { "rola": "kotwica", "fakty": [], "notatka": "Jedziesz po dawnej granicy miasta." },
      { "rola": "fakt_o_miejscu", "fakty": ["F1", "F2"] },
      { "rola": "fakt_o_miejscu", "fakty": ["F4"] },
      { "rola": "skok", "fakty": ["F6"] },
      { "rola": "powrot", "fakty": ["F7"], "notatka": "Po bazarze została nazwa ronda, które mijasz." }
    ],
    "ton": "lekki",
    "era": "przed1800"
  },
  "warstwy_zapasowe": [
    { "os": "Okopowa jako granica getta", "most_typ": "A", "fakty": ["F9", "F10"], "ton": "tragiczny" }
  ]
}
```

---

## 2. Rondo Żabczyńskiego (Służewiec)

**Wejście (skrót)**

- `s1` instytucja — dzieje.pl: Aleksander Żabczyński (1900–1958), amant kina przedwojennego; walczył we wrześniu 1939, przez Węgry do Francji, ranny pod Monte Cassino; wrócił w 1946, inwigilowany, po wojnie nie zagrał w filmie.
- `s2` portal_lokalny — moko.waw.pl: autor pisze, że nie zna żadnego związku aktora z tym miejscem, i zgaduje, że nazwisko miało dodać okolicy prestiżu.
- `s3` portal_lokalny — ulicetwojegomiasta.pl: historia biurowego Służewca („Mordor”).

**Kluczowe decyzje**

- Pasażer słyszy „Rondo Żabczyńskiego” → most **E**.
- Źródło `s2` mówi „nie znam związku” — to **nie** jest dowód, że związku nie ma. Fakt brzmi więc „nie wiadomo, by…”, a nie „nic go z tym miejscem nie łączy”.
- Przypuszczenie o prestiżu to `domysl`. Wchodzi z jednego źródła tylko dlatego, że odpowiada na główne pytanie („dlaczego on?”), i z atrybucją.
- Mordor to historia **okolicy**, nie tej nazwy → `warstwy_zapasowe`.

**Wyjście (skrót)**

```json
{
  "fakty": [
    {
      "id": "F1",
      "tekst": "Nie wiadomo, by Aleksandra Żabczyńskiego coś łączyło z tym miejscem.",
      "dowody": [{ "fragment": "s2#1", "cytat": "…" }],
      "rodzaj": "fakt",
      "pewnosc": "srednia",
      "era": "po1989"
    },
    {
      "id": "F2",
      "tekst": "Lokalny autor przypuszcza, że nazwisko aktora miało dodać biurowej okolicy prestiżu.",
      "dowody": [{ "fragment": "s2#1", "cytat": "…" }],
      "rodzaj": "domysl",
      "pewnosc": "srednia",
      "era": "po1989"
    },
    {
      "id": "F5",
      "tekst": "Po powrocie do Polski w 1946 r. Żabczyński był inwigilowany i nie zagrał już w żadnym filmie.",
      "dowody": [{ "fragment": "s1#3", "cytat": "…" }],
      "rodzaj": "fakt",
      "pewnosc": "potwierdzony",
      "era": "1945-1989"
    }
  ],
  "historia": {
    "status": "ok",
    "os": "Największy amant przedwojennego kina, wymazany z ekranu po wojnie, ma rondo w środku biurowego Służewca.",
    "pytanie_sluchacza": "Kim był Żabczyński i dlaczego rondo nosi jego imię?",
    "most": {
      "typ": "E",
      "zdanie_robocze": "Słyszysz jego nazwisko w zapowiedzi, choć nie wiadomo, by coś go tu łączyło.",
      "fakty": ["F1", "F2"]
    },
    "haczyk": {
      "fakty": ["F4", "F5"],
      "dlaczego_ten": "Kontrast amant–wojna–zakaz grania jest ciekawszy niż lista filmów."
    },
    "sposob_zmiany": "brak",
    "wyjasnic": [{ "co": "kim był Aleksander Żabczyński", "fakt": "F3" }],
    "ton": "neutralny",
    "era": "1918-1939"
  },
  "warstwy_zapasowe": [
    { "os": "Od dzielnicy przemysłowej do Mordoru", "most_typ": "B", "fakty": ["F8", "F9"], "ton": "lekki" }
  ]
}
```

---

## 3. PKP Zacisze-Wilno (Targówek)

**Wejście (skrót)**

- `s1` komercyjne/prasa — budnet.pl: prezes dewelopera mówi, że nazwa osiedla Wilno to hołd dla Kresów i nawiązanie do historycznej kolei z Warszawy do Wilna.
- `s2` encyklopedia — Wikipedia: kolej Petersburg–Warszawa otwarta do Warszawy w 1862 r., przez Wilno, kończyła się na dzisiejszym Dworcu Wileńskim.
- `s3` encyklopedia — Wikipedia: stacja Zacisze-Wilno otwarta w 2013 r.
- `s4` varsavianistyka: w czasie okupacji Niemcy nazwali Radzymińską Wilnaer Straße.

**Kluczowe decyzje**

- Słowa dewelopera to `deklaracja` — wchodzą z atrybucją („deweloper wskazywał…”), nie jako fakt o pochodzeniu nazwy.
- Kolej z 1862 r. jest faktem potwierdzonym niezależnie → to ona jest osią, deweloper to jedno zdanie (pośrednik).
- Wilnaer Straße to prawdziwy fakt, ale żadne źródło nie mówi, że nazwa osiedla od niej pochodzi. Fakt zostaje, a wniosek „stąd nazwa” idzie do `odrzucone` z powodem `wniosek_ze_zbieznosci`.
- Słuchacz może nie wiedzieć, czym jest Wilno → `wyjasnic`.

**Wyjście (skrót)**

```json
{
  "fakty": [
    {
      "id": "F1",
      "tekst": "Prezes dewelopera wskazywał, że osiedle Wilno nawiązuje do historycznej kolei z Warszawy do Wilna.",
      "dowody": [{ "fragment": "s1#1", "cytat": "…" }],
      "rodzaj": "deklaracja",
      "pewnosc": "srednia",
      "era": "po1989"
    },
    {
      "id": "F2",
      "tekst": "Kolej z Petersburga do Warszawy, otwarta w 1862 r., biegła przez Wilno i kończyła się na dzisiejszym Dworcu Wileńskim.",
      "dowody": [{ "fragment": "s2#1", "cytat": "…" }],
      "rodzaj": "fakt",
      "pewnosc": "potwierdzony",
      "era": "1800-1918"
    },
    {
      "id": "F4",
      "tekst": "W czasie okupacji Niemcy nazwali Radzymińską Wilnaer Straße.",
      "dowody": [{ "fragment": "s4#1", "cytat": "…" }],
      "rodzaj": "fakt",
      "pewnosc": "srednia",
      "era": "1939-1945"
    }
  ],
  "odrzucone": [
    {
      "tekst": "Osiedle nazwano Wilno od niemieckiej nazwy Radzymińskiej.",
      "fragmenty": ["s4#1"],
      "powod": "wniosek_ze_zbieznosci",
      "uwaga": "Żadne źródło nie łączy tych nazw."
    }
  ],
  "historia": {
    "status": "ok",
    "os": "Wilno na Targówku wzięło się z kolei do Petersburga, przy której zawraca autobus.",
    "pytanie_sluchacza": "Skąd Wilno na Targówku?",
    "most": {
      "typ": "C",
      "zdanie_robocze": "Tory, przy których jesteś, to fragment kolei, która biegła przez Wilno.",
      "fakty": ["F2"]
    },
    "sposob_zmiany": "lancuch",
    "wyjasnic": [{ "co": "czym jest Wilno", "fakt": null }],
    "ton": "lekki",
    "era": "1800-1918"
  },
  "braki": [
    {
      "czego": "1–2 zdania, czym jest Wilno (dziś stolica Litwy)",
      "po_co": "krok wyjaśnienia dla słuchacza",
      "gdzie_szukac": "Wikipedia — Wilno"
    },
    {
      "czego": "numer i przebieg linii kolejowej przy stacji",
      "po_co": "potwierdzenie, że stacja leży przy torach dawnej kolei",
      "gdzie_szukac": "Wikipedia / OSM"
    }
  ]
}
```
