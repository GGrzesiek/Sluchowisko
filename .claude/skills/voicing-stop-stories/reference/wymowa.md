# Tekst do wymówienia: liczby, skróty, nazwy

Syntezator sam zgaduje, jak przeczytać „1867 r.”, i często myli przypadek. Dlatego w `tts_text` **nie ma cyfr, skrótów ani liczb rzymskich** — wszystko zapisujesz słowami, w poprawnej formie gramatycznej. Kod odrzuci kwestię z cyfrą, skrótem z kropką albo liczbą rzymską.

## Lata i daty

Rok czytamy jako liczebnik porządkowy w przypadku, którego wymaga zdanie.

| W scenariuszu           | W `tts_text`                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------ |
| w 1770 roku / w 1770 r. | w tysiąc siedemset siedemdziesiątym roku                                                         |
| od 1867 roku            | od tysiąc osiemset sześćdziesiątego siódmego roku                                                |
| do 1905 r.              | do tysiąc dziewięćset piątego roku                                                               |
| rok 1944                | rok tysiąc dziewięćset czterdziesty czwarty                                                      |
| 11 listopada 1918       | jedenastego listopada tysiąc dziewięćset osiemnastego roku                                       |
| w latach 30. XX wieku   | w latach trzydziestych dwudziestego wieku                                                        |
| 1867–1944               | od tysiąc osiemset sześćdziesiątego siódmego do tysiąc dziewięćset czterdziestego czwartego roku |
| w 2013 roku             | w dwa tysiące trzynastym roku                                                                    |
| XIX w. / w XIX wieku    | dziewiętnasty wiek / w dziewiętnastym wieku                                                      |

## Liczby z rzeczownikami

Liczebnik główny zgadza się z rzeczownikiem: „400 metrów” → „czterysta metrów”, „2 kilometry” → „dwa kilometry”, „22 tysiące” → „dwadzieścia dwa tysiące”, „ok. 1,5 km” → „około półtora kilometra”, „40%” → „czterdzieści procent”, „12 000 zł” → „dwanaście tysięcy złotych”, „5 m²” → „pięć metrów kwadratowych”.

Liczby porządkowe: „1. Pułk” → „Pierwszy Pułk”, „3 Maja” → „Trzeciego Maja”, „al. Jana Pawła II” → „aleja Jana Pawła Drugiego”.

## Skróty

| Skrót      | Rozwinięcie (odmień!)            |
| ---------- | -------------------------------- |
| ul.        | ulica, ulicy, ulicą…             |
| al.        | aleja, alei…                     |
| pl.        | plac, placu…                     |
| os.        | osiedle, osiedla…                |
| św.        | święty, świętego, świętej…       |
| gen. / płk | generał / pułkownik (odmiana)    |
| ks. / bp   | ksiądz / biskup (odmiana)        |
| prof. / dr | profesor / doktor (odmiana)      |
| im.        | imienia                          |
| r. / w.    | roku / wieku                     |
| ok.        | około                            |
| m.in.      | między innymi                    |
| tzw.       | tak zwany, tak zwana…            |
| nr         | numer                            |
| km, m, ha  | kilometr, metr, hektar (odmiana) |
| zł         | złotych, złote…                  |

Skrótowce czytane literami zapisz tak, jak brzmią: PKP → „pe-ka-pe”, ZTM → „zet-te-em”, PRL → „pe-er-el”, NID → „en-i-de”, MPK → „em-pe-ka”. Skrótowce czytane jak słowo zostają: PAST → „Past”, ZUS → „Zus”.

## Nazwy

- Polskie nazwy zostawiasz bez zmian. Syntezator zwykle akcentuje je dobrze.
- Nazwy obce, które polski lektor przeczytałby po swojemu, zapisz fonetycznie po polsku i wpisz do `pronunciations`: „Lindley” → „Lindlej”, „Wilnaer Straße” → „Wilnaer Sztrase”, „Concorde” → „Konkord”.
- Imiona i nazwiska prawdziwych osób zapisz tak, by brzmiały poprawnie, ale nie zmieniaj ich: „Żabczyński” zostaje.
- Nie dodajesz ani nie usuwasz słów poza rozwinięciami. Kod porównuje `tts_text` ze scenariuszem i odrzuci kwestię, która za bardzo się różni.

## Znaki

- Bez nawiasów, ukośników, znaków `&`, `%`, `§`, `+`, `=`, cudzysłowów w środku zdania (cudzysłów zamień na rytm zdania albo pauzę).
- Myślnik „—” daje krótki oddech; wielokropek „…” daje zawieszenie. Najwyżej jeden wielokropek w kwestii.
- Nie wstawiaj `<break time=…/>` ani innych znaczników SSML — `eleven_v3` ich nie obsługuje. Dłuższe pauzy robi kod z `pause_after_s`.
