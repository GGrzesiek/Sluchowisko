# Przykłady rozumowania

**Uwaga:** przykłady pokazują przede wszystkim sposób pracy. Gdy przystanek z wejścia jest tym samym miejscem (Okopowa i Francuska są przystankami demo), możesz wykorzystać fakty z przykładu, ale każdy z nich musi mieć dowód we fragmencie: z wejścia albo dociągniętym ze źródła wskazanego w przykładzie. Bez dowodu fakt idzie do `gaps`.

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

- Nazwa i kształt ulicy są historią → most **C**. Pasażer jedzie po linii wału → sposób **`trace`**, bo związek przyczynowy („ulica biegnie linią wału”) podaje źródło, a nie my.
- Getto i egzekucje to prawda o tym miejscu, ale nie odpowiedź na pytanie „skąd ta nazwa i ten kształt”. Ta sama ulica ma równie mocną, lżejszą historię → trudna warstwa idzie do `spare_layers` z `tone: tragic`, nie znika.
- Haczyk: Kercelak — da się wrócić do miejsca (nazwa ronda, które mijasz).

**Wyjście (skrót)**

```json
{
  "facts": [
    {
      "id": "F1",
      "text": "W 1770 r. marszałek Stanisław Lubomirski kazał usypać wokół Warszawy wał z fosą z obawy przed dżumą.",
      "evidence": [{ "fragment_id": "s1#1", "quote": "…" }],
      "kind": "fact",
      "confidence": "confirmed",
      "era": "before_1800"
    },
    {
      "id": "F2",
      "text": "Zaraza nie dotarła do Warszawy; według Muzeum Warszawy miasto uratowała zima.",
      "evidence": [{ "fragment_id": "s1#2", "quote": "…" }],
      "kind": "fact",
      "confidence": "confirmed",
      "era": "before_1800"
    },
    {
      "id": "F4",
      "text": "Dzisiejszy przebieg Okopowej i Towarowej to niemal dokładnie linia dawnego wału.",
      "evidence": [{ "fragment_id": "s2#1", "quote": "…" }],
      "kind": "fact",
      "confidence": "medium",
      "era": "before_1800"
    }
  ],
  "axis_candidates": [
    {
      "axis": "Ulica biegnie linią wału przeciw dżumie",
      "bridge_type": "C",
      "reason": "Nazwa i kształt ulicy, po której jedziesz, wynikają z wału."
    },
    {
      "axis": "Okopowa jako granica getta",
      "bridge_type": "A",
      "reason": "Prawdziwe i ważne, ale ton tragiczny; lżejsza warstwa ma równie mocny most."
    }
  ],
  "story": {
    "status": "ok",
    "axis": "Okopowa jest kręta, bo wciąż biegnie linią wału usypanego w 1770 r. przeciw dżumie.",
    "listener_question": "Dlaczego ta ulica nazywa się Okopowa i biegnie właśnie tak?",
    "bridge": {
      "type": "C",
      "draft": "Jedziesz po linii dawnego wału — stąd nazwa i kształt ulicy.",
      "fact_ids": ["F1", "F4"]
    },
    "hook": { "fact_ids": ["F6"], "why": "Kercelak pozwala wrócić do miejsca: została po nim nazwa ronda." },
    "change_mode": "trace",
    "steps": [
      { "role": "anchor", "fact_ids": [], "note": "Jedziesz po dawnej granicy miasta." },
      { "role": "place_fact", "fact_ids": ["F1", "F2"] },
      { "role": "place_fact", "fact_ids": ["F4"] },
      { "role": "jump", "fact_ids": ["F6"] },
      { "role": "return", "fact_ids": ["F7"], "note": "Po bazarze została nazwa ronda, które mijasz." }
    ],
    "tone": "light",
    "era": "before_1800"
  },
  "spare_layers": [
    { "axis": "Okopowa jako granica getta", "bridge_type": "A", "fact_ids": ["F9", "F10"], "tone": "tragic" }
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
- Przypuszczenie o prestiżu to `guess`. Wchodzi z jednego źródła tylko dlatego, że odpowiada na główne pytanie („dlaczego on?”), i z atrybucją.
- Mordor to historia **okolicy**, nie tej nazwy → `spare_layers`.

**Wyjście (skrót)**

```json
{
  "facts": [
    {
      "id": "F1",
      "text": "Nie wiadomo, by Aleksandra Żabczyńskiego coś łączyło z tym miejscem.",
      "evidence": [{ "fragment_id": "s2#1", "quote": "…" }],
      "kind": "fact",
      "confidence": "medium",
      "era": "after_1989"
    },
    {
      "id": "F2",
      "text": "Lokalny autor przypuszcza, że nazwisko aktora miało dodać biurowej okolicy prestiżu.",
      "evidence": [{ "fragment_id": "s2#1", "quote": "…" }],
      "kind": "guess",
      "confidence": "medium",
      "era": "after_1989"
    },
    {
      "id": "F5",
      "text": "Po powrocie do Polski w 1946 r. Żabczyński był inwigilowany i nie zagrał już w żadnym filmie.",
      "evidence": [{ "fragment_id": "s1#3", "quote": "…" }],
      "kind": "fact",
      "confidence": "confirmed",
      "era": "1945_1989"
    }
  ],
  "story": {
    "status": "ok",
    "axis": "Największy amant przedwojennego kina, wymazany z ekranu po wojnie, ma rondo w środku biurowego Służewca.",
    "listener_question": "Kim był Żabczyński i dlaczego rondo nosi jego imię?",
    "bridge": {
      "type": "E",
      "draft": "Słyszysz jego nazwisko w zapowiedzi, choć nie wiadomo, by coś go tu łączyło.",
      "fact_ids": ["F1", "F2"]
    },
    "hook": {
      "fact_ids": ["F4", "F5"],
      "why": "Kontrast amant–wojna–zakaz grania jest ciekawszy niż lista filmów."
    },
    "change_mode": "none",
    "explain": [{ "what": "kim był Aleksander Żabczyński", "fact_id": "F3" }],
    "tone": "neutral",
    "era": "1918_1939"
  },
  "spare_layers": [
    { "axis": "Od dzielnicy przemysłowej do Mordoru", "bridge_type": "B", "fact_ids": ["F8", "F9"], "tone": "light" }
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

- Słowa dewelopera to `claim` — wchodzą z atrybucją („deweloper wskazywał…”), nie jako fakt o pochodzeniu nazwy.
- Kolej z 1862 r. jest faktem potwierdzonym niezależnie → to ona jest osią, deweloper to jedno zdanie (pośrednik).
- Wilnaer Straße to prawdziwy fakt, ale żadne źródło nie mówi, że nazwa osiedla od niej pochodzi. Fakt zostaje, a wniosek „stąd nazwa” idzie do `rejected` z powodem `coincidence_as_cause`.
- Słuchacz może nie wiedzieć, czym jest Wilno → `explain`.

**Wyjście (skrót)**

```json
{
  "facts": [
    {
      "id": "F1",
      "text": "Prezes dewelopera wskazywał, że osiedle Wilno nawiązuje do historycznej kolei z Warszawy do Wilna.",
      "evidence": [{ "fragment_id": "s1#1", "quote": "…" }],
      "kind": "claim",
      "confidence": "medium",
      "era": "after_1989"
    },
    {
      "id": "F2",
      "text": "Kolej z Petersburga do Warszawy, otwarta w 1862 r., biegła przez Wilno i kończyła się na dzisiejszym Dworcu Wileńskim.",
      "evidence": [{ "fragment_id": "s2#1", "quote": "…" }],
      "kind": "fact",
      "confidence": "confirmed",
      "era": "1800_1918"
    },
    {
      "id": "F4",
      "text": "W czasie okupacji Niemcy nazwali Radzymińską Wilnaer Straße.",
      "evidence": [{ "fragment_id": "s4#1", "quote": "…" }],
      "kind": "fact",
      "confidence": "medium",
      "era": "1939_1945"
    }
  ],
  "rejected": [
    {
      "text": "Osiedle nazwano Wilno od niemieckiej nazwy Radzymińskiej.",
      "fragment_ids": ["s4#1"],
      "reason": "coincidence_as_cause",
      "note": "Żadne źródło nie łączy tych nazw."
    }
  ],
  "story": {
    "status": "ok",
    "axis": "Wilno na Targówku wzięło się z kolei do Petersburga, przy której zawraca autobus.",
    "listener_question": "Skąd Wilno na Targówku?",
    "bridge": {
      "type": "C",
      "draft": "Tory, przy których jesteś, to fragment kolei, która biegła przez Wilno.",
      "fact_ids": ["F2"]
    },
    "change_mode": "chain",
    "explain": [{ "what": "czym jest Wilno", "fact_id": null }],
    "tone": "light",
    "era": "1800_1918"
  },
  "gaps": [
    {
      "what": "1–2 zdania, czym jest Wilno (dziś stolica Litwy)",
      "why": "krok wyjaśnienia dla słuchacza",
      "where": "Wikipedia — Wilno"
    },
    {
      "what": "numer i przebieg linii kolejowej przy stacji",
      "why": "potwierdzenie, że stacja leży przy torach dawnej kolei",
      "where": "Wikipedia / OSM"
    }
  ]
}
```
