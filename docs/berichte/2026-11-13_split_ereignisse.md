# Split-Ereignisse der Kursreihen: Einordnung und Prüfliste

Erstellt 13.11.2026 10:55 mit `tools/split_ereignisse_einordnen.py`; Liste `config/kapitalmassnahmen_historie.yaml`. 265 Ereignisse ab 2012 in den Kursreihen des Universums.

| Art | Backtest bis 2024 | Betrieb ab 2025 |
| --- | --- | --- |
| abspaltung | 83 | 10 |
| kombiniert | 4 | 0 |
| split | 133 | 12 |
| unklar | 17 | 6 |

## Prüfliste Backtest bis 2024 (21 Fälle: kombiniert oder unklar)

Bitte je Fall: Art (split, abspaltung, kombiniert) und Split-Faktor für die Aktienzahl bestätigen oder korrigieren.

| Ticker (CIK) | Datum | Faktor Kursreihe | SEC-Verhältnis | Einreichungen | Vorschlag | Bemerkung |
| --- | --- | --- | --- | --- | --- | --- |
| DLTR (935703) | 2012-06-27 | 2 | 2000816.9935 | 2011-08-18 → 2012-08-16 | unklar | SEC-Verhältnis 2.001e+06: Skalierungsfehler (Tausend statt Stück), bereinigt 2.0008; Vorschlag: split, Split-Faktor 2 |
| DUK (1326160) | 2012-07-03 | 0.333333 | – | nan | unklar | dieselbe Periode davor nicht gemeldet |
| TMUS (1283699) | 2013-05-01 | 0.5 | 1.4747 | 2012-07-26 → 2013-08-08 | kombiniert, Split-Faktor 1.47465 | SEC-Verhältnis 1.4747: Split-Anteil, Rest Abspaltung (Vorschlag, zu prüfen) |
| LDOS (1336920) | 2013-09-30 | 0.405 | 0.2492 | 2012-12-06 → 2013-12-10 | kombiniert, Split-Faktor 0.249249 | SEC-Verhältnis 0.2492: Split-Anteil, Rest Abspaltung (Vorschlag, zu prüfen) |
| ROL (84839) | 2015-03-11 | 1.5 | 1499.9966 | 2014-04-25 → 2015-04-30 | unklar | SEC-Verhältnis 1500: Skalierungsfehler (Tausend statt Stück), bereinigt 1.5000; Vorschlag: split, Split-Faktor 1.5 |
| V (1403161) | 2015-03-19 | 4 | – | nan | unklar | keine SEC-Aktienzahlen |
| DXC (1688568) | 2015-11-30 | 1.7412 | – | nan | unklar | kein Periodenbericht davor |
| OXY (797468) | 2016-02-25 | 1.0017 | 1.0000 | 2015-02-23 → 2016-02-26 | unklar | Faktor nahe 1, SEC-Verhältnis 1.0000 nicht eindeutig |
| LNT (352541) | 2016-05-20 | 2 | – | nan | unklar | erster Periodenbericht danach erst 2019-05-03 |
| JCI (833444) | 2016-09-06 | 0.955 | – | nan | unklar | dieselbe Periode davor nicht gemeldet |
| EVHC (1678531) | 2016-12-02 | 0.334 | – | nan | unklar | kein Periodenbericht davor |
| HLT (1585689) | 2017-01-04 | 0.487329 | 0.3337 | 2016-02-26 → 2017-02-15 | kombiniert, Split-Faktor 0.333671 | SEC-Verhältnis 0.3337: Split-Anteil, Rest Abspaltung (Vorschlag, zu prüfen) |
| LEN (920760) | 2017-11-09 | 1.017 | 1.0213 | 2017-01-20 → 2018-01-25 | unklar | Faktor nahe 1, SEC-Verhältnis 1.0213 nicht eindeutig |
| FERG (2011641) | 2018-06-11 | 0.947 | – | nan | unklar | kein Periodenbericht davor |
| DELL (1571996) | 2018-12-28 | 1.806 | – | nan | unklar | dieselbe Periode davor nicht gemeldet |
| DD (30554) | 2019-04-02 | 1.487 | – | nan | unklar | kein Periodenbericht danach |
| DD (1666700) | 2019-06-03 | 0.4725 | 0.3333 | 2018-08-03 → 2019-08-06 | unklar | SEC-Verhältnis 0.3333 passt weder zu 1 noch zum Produkt (zusammen mit 1 weiteren Ereignissen im Fenster, Produkt 0.7026) |
| DD (30554) | 2019-06-03 | 0.333333 | – | nan | unklar | kein Periodenbericht danach |
| MTCH (891103) | 2020-07-01 | 3.502 | 2.1584 | 2019-08-09 → 2020-08-10 | kombiniert, Split-Faktor 2.15838 | SEC-Verhältnis 2.1584: Split-Anteil, Rest Abspaltung (Vorschlag, zu prüfen) |
| GOOG (1652044) | 2022-07-18 | 20 | – | nan | unklar | erster Periodenbericht danach erst 2024-07-24 |
| PANW (1327567) | 2022-09-14 | 3 | – | nan | unklar | dieselbe Periode davor nicht gemeldet |

## Betrieb ab 2025 noch offen (6)

Im SEC-Cache (companyfacts vom 02.11.2026) fehlt noch ein Periodenbericht, der dieselbe Periode vor und nach dem Ereignis zeigt, oder das Verhältnis ist nicht eindeutig. Ein Lauf nach dem nächsten SEC-Abruf ordnet die meisten selbst ein; was danach offen bleibt, kommt zur Prüfung. Gehaltene Titel der Bücher sind darunter nicht.

| Ticker (CIK) | Datum | Faktor Kursreihe | Bemerkung |
| --- | --- | --- | --- |
| CVNA (1690820) | 2026-05-08 | 5 | dieselbe Periode davor nicht gemeldet |
| DD (1666700) | 2026-06-24 | 0.333333 | SEC-Verhältnis 0.3334 passt weder zu 1 noch zum Produkt (zusammen mit 1 weiteren Ereignissen im Fenster, Produkt 0.7967) |
| DD (30554) | 2026-06-24 | 0.333333 | kein Periodenbericht danach |
| HON (773840) | 2026-06-29 | 0.9535 | Faktor nahe 1, SEC-Verhältnis 0.5000 nicht eindeutig |
| MNST (865752) | 2026-08-11 | 2 | kein Periodenbericht danach |
| CTVA (1755672) | 2026-10-01 | 6.665 | kein Periodenbericht danach |

## Automatisch als Abspaltung eingeordnet (93)

WMB 2012-01-03 (1.22669), COP 2012-05-01 (1.31179), JCI 2012-10-01 (2.01167), ABT 2013-01-02 (2.0842), JEF 2013-02-26 (1.027), VLO 2013-05-02 (1.094), MUR 2013-09-03 (1.158), PENN 2013-11-04 (4.423), TT 2013-12-02 (1.252), OKE 2014-02-03 (1.1422), DOV 2014-03-03 (1.205), SPG 2014-05-29 (1.063), NOV 2014-06-02 (1.109), IP 2014-07-02 (1.014), IRM 2014-09-26 (1.082), ADP 2014-10-01 (1.139), A 2014-11-03 (1.398), KMB 2014-11-03 (1.043), OXY 2014-12-01 (1.042), VNO 2015-01-16 (1.10497), GOOG 2015-04-27 (1.00275), PPL 2015-06-02 (1.07365), BAX 2015-07-01 (1.841), MAS 2015-07-01 (1.138), NI 2015-07-02 (2.545), EBAY 2015-07-20 (2.376), VTR 2015-08-18 (0.8757), HPQ 2015-11-02 (2.202), DRI 2015-11-10 (1.11869), DHR 2016-07-05 (1.319), APD 2016-10-03 (1.081), HON 2016-10-03 (1.00533), DOC 2016-11-01 (1.098), YUM 2016-11-01 (1.391), CAG 2016-11-10 (1.285), HPE 2017-04-03 (1.3348), VNO 2017-07-18 (1.237), MET 2017-08-07 (1.122), HPE 2017-09-01 (1.289), APTV 2017-12-05 (1.193), PNR 2018-05-01 (1.489), DOV 2018-05-09 (1.238), DXC 2018-06-01 (1.156), WYN 2018-06-01 (2.215), HON 2018-10-01 (1.011), HON 2018-10-29 (1.032), EQT 2018-11-13 (1.837), HSIC 2019-02-08 (1.275), GE 2019-02-26 (1.04), FMC 2019-03-04 (1.153), DD 2019-04-02 (1.487), VFC 2019-05-23 (1.062), ECHO 2019-09-11 (1.234), JEF 2019-09-27 (1.068), TT 2020-03-02 (1.289), RTX 2020-04-03 (1.589), FTV 2020-10-09 (1.195), PFE 2020-11-17 (1.054), FTI 2021-02-16 (1.344), MRK 2021-06-03 (1.048), DTE 2021-07-01 (1.175), BBWI 2021-08-03 (1.237), IP 2021-10-01 (1.056), DELL 2021-11-02 (1.973), IBM 2021-11-04 (1.046), ADS 2021-11-08 (1.253), O 2021-11-15 (1.032), EXC 2022-02-02 (1.402), ZBH 2022-03-01 (1.03), BDX 2022-04-01 (1.025), T 2022-04-11 (1.324), FBHS 2022-12-15 (1.17), GE 2023-01-04 (1.281), JEF 2023-01-17 (1.046), LH 2023-07-03 (1.164), BWA 2023-07-05 (1.136), DHR 2023-10-02 (1.128), K 2023-10-02 (1.065), FLEX 2024-01-03 (1.327), MMM 2024-04-01 (1.196), GE 2024-04-02 (1.253), ILMN 2024-06-25 (1.028), J 2024-09-30 (1.197), LEN 2025-01-21 (1.033), WDC 2025-02-24 (1.323), J 2025-05-16 (1.01), FTV 2025-06-30 (1.327), HON 2025-10-30 (1.061), DD 2025-11-03 (2.39), CMCSA 2026-01-05 (1.067), BDX 2026-02-10 (1.272), FDX 2026-06-01 (1.241), SPGI 2026-07-01 (1.057)

