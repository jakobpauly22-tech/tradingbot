# Split-Ereignisse der Kursreihen: Einordnung und Prüfliste

Erstellt 13.11.2026 12:54 mit `tools/split_ereignisse_einordnen.py`; Liste `config/kapitalmassnahmen_historie.yaml`. 265 Ereignisse ab 2012 in den Kursreihen des Universums.

| Art | Backtest bis 2024 | Betrieb ab 2025 |
| --- | --- | --- |
| abspaltung | 85 | 10 |
| kombiniert | 4 | 0 |
| nicht_zugehoerig | 2 | 1 |
| split | 143 | 12 |
| unklar | 3 | 5 |

## Prüfliste Backtest bis 2024 (0 Fälle: kombiniert oder unklar)

Bitte je Fall: Art (split, abspaltung, kombiniert) und Split-Faktor für die Aktienzahl bestätigen oder korrigieren.

| Ticker (CIK) | Datum | Faktor Kursreihe | SEC-Verhältnis | Einreichungen | Vorschlag | Bemerkung |
| --- | --- | --- | --- | --- | --- | --- |

## Betrieb ab 2025 noch offen (5)

Im SEC-Cache (companyfacts vom 02.11.2026) fehlt noch ein Periodenbericht, der dieselbe Periode vor und nach dem Ereignis zeigt, oder das Verhältnis ist nicht eindeutig. Ein Lauf nach dem nächsten SEC-Abruf ordnet die meisten selbst ein; was danach offen bleibt, kommt zur Prüfung. Gehaltene Titel der Bücher sind darunter nicht.

| Ticker (CIK) | Datum | Faktor Kursreihe | Bemerkung |
| --- | --- | --- | --- |
| CVNA (1690820) | 2026-05-08 | 5 | dieselbe Periode davor nicht gemeldet |
| DD (1666700) | 2026-06-24 | 0.333333 | SEC-Verhältnis 0.3334 passt weder zu 1 noch zum Produkt (zusammen mit 1 weiteren Ereignissen im Fenster, Produkt 0.7967) |
| HON (773840) | 2026-06-29 | 0.9535 | Faktor nahe 1, SEC-Verhältnis 0.5000 nicht eindeutig |
| MNST (865752) | 2026-08-11 | 2 | kein Periodenbericht danach |
| CTVA (1755672) | 2026-10-01 | 6.665 | kein Periodenbericht danach |

## Von Jakob geprüft, mit Beleg (23)

| Ticker (CIK) | Datum | Faktor Kursreihe | Art | Split-Faktor | Beleg |
| --- | --- | --- | --- | --- | --- |
| DLTR (935703) | 2012-06-27 | 2 | split | 2 | SEC 8-K 29.05.2012 (0000935703-12-000033), EX-99.1: „2-for-1 stock split“ |
| DUK (1326160) | 2012-07-03 | 0.333333 | split | 0.333333 | SEC 8-K 02.08.2012 (0001193125-12-330265), EX-99.1: „one-for-three reverse stock split … completed immediately prior to closing the merger with Progress Energy on July 2, 2012“ |
| TMUS (1283699) | 2013-05-01 | 0.5 | split | 0.5 | SEC 8-K 02.05.2013 (0001193125-13-193449): Reverse-Split, jede MetroPCS-Aktie „now represents one-half of a share“; SEC-Verhältnis 1,4747 durch Reverse-Acquisition-Bilanzierung verzerrt, nicht verwendet |
| LDOS (1336920) | 2013-09-30 | 0.405 | kombiniert | 0.25 | SEC 8-K 01.10.2013 (0001193125-13-387297) und 03.10.2013 (0001193125-13-389646): Abspaltung New SAIC und „reverse stock split at a stock split ratio of 1-for-4“ |
| ROL (84839) | 2015-03-11 | 1.5 | split | 1.5 | SEC 8-K 28.01.2015 (0001552781-15-000114), EX-99.1: „three-for-two stock split“ |
| V (1403161) | 2015-03-19 | 4 | split | 4 | SEC 8-K 29.01.2015 (0001193125-15-025534), Item 8.01: „4-for-1 stock split of the Company’s class A common stock“ |
| DXC (1688568) | 2015-11-30 | 1.7412 | abspaltung | 1 | SEC 8-K von CSC (CIK 23082) 04.11.2015 (0000023082-15-000060), EX-99.2: Abspaltung CSRA und Sonderdividende 10,50 USD |
| OXY (797468) | 2016-02-25 | 1.0017 | abspaltung | 1 | SEC 8-K 02.03.2016 (0000797468-16-000020): Sonderdividende aller CRC-Aktien, letzter Schritt der Abspaltung California Resources |
| LNT (352541) | 2016-05-20 | 2 | split | 2 | SEC 8-K 05.05.2016 (0000352541-16-000114), EX-99.1: „two-for-one common stock split“ |
| JCI (833444) | 2016-09-06 | 0.955 | split | 0.955 | SEC 8-K von Tyco 08.08.2016 (0000833444-16-000202), EX-99.1: „0.955-for-one share consolidation“ bei der Fusion mit Johnson Controls |
| EVHC (1678531) | 2016-12-02 | 0.334 | unklar | – | kein Beleg mit Verhältnis in den 8-K um das Datum (Fusion AmSurg/Envision); auf Jakobs Anweisung unklar, kein Faktor |
| HLT (1585689) | 2017-01-04 | 0.487329 | kombiniert | 0.333333 | SEC 8-K 04.01.2017 (0001193125-17-001901): „1-for-3 reverse stock split“; Abspaltung Park Hotels und Hilton Grand Vacations (8-K 24.10.2016, 0001193125-16-744536) |
| LEN (920760) | 2017-11-09 | 1.017 | split | 1.02 | SEC 8-K 30.10.2017 (0001193125-17-325037), EX-99.1: Aktiendividende „one share of Class B common stock for each 50 shares“ |
| FERG (2011641) | 2018-06-11 | 0.947 | unklar | – | keine SEC-Einreichungen im Zeitraum (damals nicht SEC-registriert); auf Jakobs Anweisung unklar, kein Faktor |
| DELL (1571996) | 2018-12-28 | 1.806 | unklar | – | 8-K 15.11.2018 (0001193125-18-327222) betrifft den Umtausch der Class-V-Aktien, kein Split-Verhältnis; auf Jakobs Anweisung unklar, kein Faktor |
| DD (1666700) | 2019-04-02 | 1.487 | abspaltung | 1 | SEC 8-K 02.04.2019 (0001193125-19-095042): Abspaltung Dow Inc. per Sachdividende abgeschlossen |
| DD (30554) | 2019-04-02 | 1.487 | nicht_zugehoerig | – | SEC 8-K12B DowDuPont 01.09.2017 (0001193125-17-274834): E. I. du Pont seit 31.08.2017 nicht mehr gehandelt, Umtausch 1,2820 DowDuPont je Aktie |
| DD (1666700) | 2019-06-03 | 0.4725 | kombiniert | 0.333333 | SEC 8-K 03.06.2019 (0001193125-19-163322): Abspaltung Corteva, danach „one-for-three reverse stock split“ |
| DD (30554) | 2019-06-03 | 0.333333 | nicht_zugehoerig | – | SEC 8-K12B DowDuPont 01.09.2017 (0001193125-17-274834): E. I. du Pont seit 31.08.2017 nicht mehr gehandelt, Umtausch 1,2820 DowDuPont je Aktie |
| MTCH (891103) | 2020-07-01 | 3.502 | kombiniert | 2.1584 | SEC 8-K 02.07.2020 (0001104659-20-080606): je Old-IAC-Aktie 1 New-IAC-Aktie und 2,1584 Aktien Class M („Reclassification Exchange Ratio“) |
| GOOG (1652044) | 2022-07-18 | 20 | split | 20 | SEC 8-K 03.06.2022 (0001193125-22-167375): „20-for-one stock split“ |
| PANW (1327567) | 2022-09-14 | 3 | split | 3 | SEC 8-K 22.08.2022 (0001327567-22-000020), Item 8.01: „three-for-one stock split“ |
| DD (30554) | 2026-06-24 | 0.333333 | nicht_zugehoerig | – | SEC 8-K12B DowDuPont 01.09.2017 (0001193125-17-274834): E. I. du Pont seit 31.08.2017 nicht mehr gehandelt, Umtausch 1,2820 DowDuPont je Aktie |

## Automatisch als Abspaltung eingeordnet, ungeprüft (92)

WMB 2012-01-03 (1.22669), COP 2012-05-01 (1.31179), JCI 2012-10-01 (2.01167), ABT 2013-01-02 (2.0842), JEF 2013-02-26 (1.027), VLO 2013-05-02 (1.094), MUR 2013-09-03 (1.158), PENN 2013-11-04 (4.423), TT 2013-12-02 (1.252), OKE 2014-02-03 (1.1422), DOV 2014-03-03 (1.205), SPG 2014-05-29 (1.063), NOV 2014-06-02 (1.109), IP 2014-07-02 (1.014), IRM 2014-09-26 (1.082), ADP 2014-10-01 (1.139), A 2014-11-03 (1.398), KMB 2014-11-03 (1.043), OXY 2014-12-01 (1.042), VNO 2015-01-16 (1.10497), GOOG 2015-04-27 (1.00275), PPL 2015-06-02 (1.07365), BAX 2015-07-01 (1.841), MAS 2015-07-01 (1.138), NI 2015-07-02 (2.545), EBAY 2015-07-20 (2.376), VTR 2015-08-18 (0.8757), HPQ 2015-11-02 (2.202), DRI 2015-11-10 (1.11869), DHR 2016-07-05 (1.319), APD 2016-10-03 (1.081), HON 2016-10-03 (1.00533), DOC 2016-11-01 (1.098), YUM 2016-11-01 (1.391), CAG 2016-11-10 (1.285), HPE 2017-04-03 (1.3348), VNO 2017-07-18 (1.237), MET 2017-08-07 (1.122), HPE 2017-09-01 (1.289), APTV 2017-12-05 (1.193), PNR 2018-05-01 (1.489), DOV 2018-05-09 (1.238), DXC 2018-06-01 (1.156), WYN 2018-06-01 (2.215), HON 2018-10-01 (1.011), HON 2018-10-29 (1.032), EQT 2018-11-13 (1.837), HSIC 2019-02-08 (1.275), GE 2019-02-26 (1.04), FMC 2019-03-04 (1.153), VFC 2019-05-23 (1.062), ECHO 2019-09-11 (1.234), JEF 2019-09-27 (1.068), TT 2020-03-02 (1.289), RTX 2020-04-03 (1.589), FTV 2020-10-09 (1.195), PFE 2020-11-17 (1.054), FTI 2021-02-16 (1.344), MRK 2021-06-03 (1.048), DTE 2021-07-01 (1.175), BBWI 2021-08-03 (1.237), IP 2021-10-01 (1.056), DELL 2021-11-02 (1.973), IBM 2021-11-04 (1.046), ADS 2021-11-08 (1.253), O 2021-11-15 (1.032), EXC 2022-02-02 (1.402), ZBH 2022-03-01 (1.03), BDX 2022-04-01 (1.025), T 2022-04-11 (1.324), FBHS 2022-12-15 (1.17), GE 2023-01-04 (1.281), JEF 2023-01-17 (1.046), LH 2023-07-03 (1.164), BWA 2023-07-05 (1.136), DHR 2023-10-02 (1.128), K 2023-10-02 (1.065), FLEX 2024-01-03 (1.327), MMM 2024-04-01 (1.196), GE 2024-04-02 (1.253), ILMN 2024-06-25 (1.028), J 2024-09-30 (1.197), LEN 2025-01-21 (1.033), WDC 2025-02-24 (1.323), J 2025-05-16 (1.01), FTV 2025-06-30 (1.327), HON 2025-10-30 (1.061), DD 2025-11-03 (2.39), CMCSA 2026-01-05 (1.067), BDX 2026-02-10 (1.272), FDX 2026-06-01 (1.241), SPGI 2026-07-01 (1.057)

