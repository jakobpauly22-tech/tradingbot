# Teil c1 b): gezielte Prüfung der wirksamen Fälle

Erstellt 15.11.2026 09:36 mit `tools/pruefe_abspaltungen_gezielt.py`. Methode vor der Rechnung festgehalten (docs/FUNDAMENTAL.md, „Teil c1: Methodenwechsel nach dem dritten Lauf“, Jakob 15.11.2026). Nichts wurde korrigiert.

Fälle: 128 Ereignisse (7 mit Bestand in Backtest A, 127 im Index-Nachbau ≤ −15 %). Mit Suchwort im Hauptdokument eines 8-K oder in einer Pressemitteilung (EX-99): 5; ohne: 123.

## Einschätzung je Fall (Claude, 15.11.2026) – zur Prüfung durch Jakob, nichts korrigiert

**Ergebnis: In keinem der 128 Fälle belegt ein Hauptdokument eines 8-K oder eine Pressemitteilung eine Abspaltung des
Titels selbst im Ereignisfenster.** Damit gibt es nach dieser Prüfung keinen Fall zu korrigieren.

Die fünf Fälle mit Suchwort:

| Fall | Fundstelle | Einschätzung |
| --- | --- | --- |
| NLSN 24.02.–12.03.2020 und 19.–23.03.2020 | EX-99.1/99.2 vom 27.02.2020, 8-K (Item 5.02) vom 20.03.2020 | Nur der **Plan**, Global Connect abzuspalten (Risikohinweise, Bedingung für Aktienzuteilungen). Abgespalten wurde nie, Global Connect wurde 2021 verkauft. Rückgang im Corona-Absturz (Markt −27,5 % im März). Keine Abspaltung. |
| RTN 05.–23.03.2020 und 27.03.–03.04.2020 (auch Buch A) | 8-K vom 13.03.2020, EX-99.1 vom 03.04.2020 | Die Abspaltungen (Carrier, Otis) waren Abspaltungen von **UTC**, nicht von Raytheon. Raytheon ging am 03.04.2020 in der Fusion mit UTC auf (Übernahme, letzter Kurs 116,96 USD am 02.04.); das regelt die Delisting-Logik. Keine Abspaltung. |
| WBD 05.–10.08.2022 | EX-99.3 vom 04.08.2022 | Erwähnt die Abspaltung von WarnerMedia durch **AT&T** (08.04.2022). Der Rückgang −16,5 % am 05.08.2022 folgt auf die Quartalszahlen. Der Wert −46,4 % ist ein **Datenfehler im Nachbau**, siehe Nebenbefund. Keine Abspaltung. |

Die übrigen 123 Fälle haben im Hauptdokument und in den Pressemitteilungen aller 8-K im Fenster kein Suchwort, 13 davon
haben gar kein 8-K im Fenster. Sie fallen in zwei Gruppen:

- **Marktbewegungen:** Corona-Absturz Februar bis April 2020 und die Ölpreis- und Bankenwellen (Juni 2020,
  März 2023), Ölpreisverfall Januar bis März 2016 und Dezember 2018. Hier bewegt sich der S&P 500 TR im selben Fenster
  deutlich mit (Spalte „S&P 500 TR im Fenster“). Dazu gehören alle Fälle in Buch A (MRO, XEC, RTN 2020).
- **Einzelereignisse** wie Quartalszahlen, Prognosesenkungen, Rechtsstreit oder Insolvenz (z. B. ENDP 2016, SIVB 2023,
  CTLT 2022/23). Bei einer echten, unbereinigten Abspaltung stünde im 8-K oder in der Pressemitteilung zum Ex-Tag
  „spin-off“ oder „distribution of all“. Das ist bei allen Teil-a-Fällen und bei CSC 2015 so.

**Grenze der Prüfung und Schlussprüfung (Jakob 15.11.2026):** 13 Fälle haben kein 8-K im Fenster; zehn fallen in Marktwellen (Ölpreis 2016 und 2018, Corona 2020). Die drei Einzelbewegungen PBCT, DISH und CTLT sind am Hauptdokument des nächsten 10-Q geprüft (Abschnitt „Schlussprüfung“): PBCT und CTLT erwähnen keine Abspaltung; bei DISH beziehen sich alle 19 Fundstellen auf die als „Spin-off“ definierte Abspaltung von EchoStar am 01.01.2008, nicht auf 2023.

**Ergebnis c1: Außer CSC 30.11.2015 keine Abspaltung mit fehlendem Wert gefunden.** CSC liegt vor beiden Messzeiträumen (Mitgliedschaft bis 01.12.2015; Nachbau ab 04.01.2016, Backtest A ab 03.10.2016) und erscheint deshalb in b) nicht; die Korrektur folgt gesondert.

## Nebenbefund: vermischte Kursreihe DISCK/WBD (CIK 1437107)

`sp500_nachbau.lade_firmendaten` führt mehrere Reihen einer Firma mit `combine_first` zusammen, die zuerst geladene hat
Vorrang. Die Tiingo-Reihe DISCK läuft nach der Fusion (11.04.2022) mit eingefrorenem Kurs 24,42 USD und Lücken bis zum
16.09.2022 weiter. WBD füllt nur die Lücken, deshalb springt der Kurs der Firma zwischen beiden Reihen hin und her
(30 Tage mit Tagesrendite über ±20 % zwischen April und September 2022). Die Wirkung ist vernachlässigbar: Der Nachbau
mit getrennten Reihen (DISCK bis 08.04.2022, danach WBD) hat dieselbe CAGR bis zur vierten Nachkommastelle
(14,9823 %, 2022: −17,7229 % gegen −17,7228 %). Buch A hielt den Titel nie (beide Läufe). Andere Firmen mit mehreren
Reihen (GOOG/GOOGL, NWSA/NWS, FOX/FOXA, TFCF/TFCFA) sind Aktiengattungen mit vollständiger erster Reihe. Ihre
Abweichungen sind die Gattungsprämie, Lücken werden dort nicht gefüllt. Ohne Jakobs Entscheidung wird nichts korrigiert.
Im Neulauf von Teil c kann Buch A CIK 1437107 in diesem Zeitraum wählen; dann wirkt der Fehler.

## Schlussprüfung am nächsten 10-Q/10-K (Fälle ohne 8-K im Fenster)

Erstellt 15.11.2026 09:50 mit `tools/pruefe_abspaltungen_schluss.py`: Hauptdokument des ersten 10-Q/10-K nach dem Ereignis, Suchwörter wie im dritten Lauf.

- **PBCT 2020-03-19 bis 2020-04-03:** 10-Q für 2020-03-31, eingereicht 2020-05-11 (0001628280-20-007419, pbct-20200331.htm, 374,724 Zeichen): **keine Erwähnung** einer Abspaltung.
- **DISH 2023-06-08 bis 2023-06-15:** 10-Q für 2023-06-30, eingereicht 2023-08-08 (0001558370-23-013759, dish-20230630x10q.htm, 396,930 Zeichen): 19 Fundstelle(n):
  - „… on our noncontrolling investments in the Northstar Entities and the SNR Entities. Contingencies Separation Agreement On January 1, 2008, we completed the distribution of our technology and set-top box business and certain infrastructure assets (the Spin-off ) into a separate publicly-traded company, EchoStar. In connection with the Spin-off, we entered into a separation agreement with EchoStar that provides, among other things, for the division of certain liabilities, including liabilities resulting fr…“
  - „…ntingencies Separation Agreement On January 1, 2008, we completed the distribution of our technology and set-top box business and certain infrastructure assets (the Spin-off ) into a separate publicly-traded company, EchoStar. In connection with the Spin-off, we entered into a separation agreement with EchoStar that provides, among other things, for the division of certain liabilities, including liabilities resulting from litigation. Under the terms of the separation agreement, EchoStar has assumed cert…“
  - „…uding liabilities resulting from litigation. Under the terms of the separation agreement, EchoStar has assumed certain liabilities that relate to its business, including certain designated liabilities for acts or omissions that occurred prior to the Spin-off. Certain specific provisions govern intellectual property related claims under which, generally, EchoStar will only be liable for its acts or omissions following the Spin-off and we will indemnify EchoStar for any liabilities or damages resulting fr…“
  - „…in designated liabilities for acts or omissions that occurred prior to the Spin-off. Certain specific provisions govern intellectual property related claims under which, generally, EchoStar will only be liable for its acts or omissions following the Spin-off and we will indemnify EchoStar for any liabilities or damages resulting from intellectual property claims relating to the period prior to the Spin-off, as well as our acts or omissions following the Spin-off. On February 28, 2017, we and EchoStar an…“
  - „…laims under which, generally, EchoStar will only be liable for its acts or omissions following the Spin-off and we will indemnify EchoStar for any liabilities or damages resulting from intellectual property claims relating to the period prior to the Spin-off, as well as our acts or omissions following the Spin-off. On February 28, 2017, we and EchoStar and certain of our respective subsidiaries completed the transactions contemplated by the Share Exchange Agreement (the Share Exchange Agreement ) that w…“
- **CTLT 2023-10-31 bis 2023-11-02:** 10-Q für 2023-09-30, eingereicht 2023-12-08 (0001596783-23-000186, ctlt-20230930.htm, 151,648 Zeichen): **keine Erwähnung** einer Abspaltung.

## Übersicht

| Ticker (CIK) | Ereignis | Liste | A | Index | Titel im Fenster | S&P 500 TR im Fenster | 8-K im Fenster | Suchwort in Hauptdokument/Pressemitteilung |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MRO (101778) | 2016-01-06 bis 2016-01-20 | unklar |  | ja | -38.4% | -7.7% | 0 | keins |
| JNPR (1043604) | 2016-01-28 bis 2016-01-29 | unklar |  | ja | -11.1% | +3.1% | 1 | keins |
| HBI (1359841) | 2016-02-02 bis 2016-02-09 | unklar |  | ja | -22.9% | -4.4% | 1 | keins |
| VIAB (1339947) | 2016-02-05 bis 2016-02-10 | unklar |  | ja | -30.8% | -3.3% | 3 | keins |
| SWN (7332) | 2016-02-09 bis 2016-03-01 | unklar |  | ja | -39.8% | +7.0% | 4 | keins |
| ENDP (1593034) | 2016-02-29 bis 2016-03-01 | unklar |  | ja | -20.3% | +1.6% | 2 | keins |
| SWN (7332) | 2016-03-08 bis 2016-03-09 | unklar |  | ja | -17.0% | -0.6% | 2 | keins |
| ENDP (1593034) | 2016-03-15 bis 2016-03-21 | unklar |  | ja | -31.5% | +1.6% | 5 | keins |
| SRCL (861878) | 2016-04-29 bis 2016-05-02 | unklar |  | ja | -21.4% | +0.3% | 2 | keins |
| ENDP (1593034) | 2016-05-05 bis 2016-05-12 | unklar |  | ja | -50.9% | +0.7% | 1 | keins |
| CMA (28412) | 2016-06-24 bis 2016-06-27 | unklar |  | ja | -16.9% | -5.3% | 3 | keins |
| ETFC (1015780) | 2016-06-24 bis 2016-06-28 | unklar |  | ja | -15.1% | -3.6% | 3 | keins |
| SRCL (861878) | 2016-07-29 bis 2016-08-01 | unklar |  | ja | -15.6% | +0.0% | 2 | keins |
| NLSN (1492633) | 2016-10-25 bis 2016-10-26 | unklar |  | ja | -16.7% | -0.5% | 4 | keins |
| ENDP (1593034) | 2016-10-26 bis 2016-11-08 | unklar |  | ja | -32.4% | -0.1% | 5 | keins |
| PDCO (891024) | 2016-11-18 bis 2016-11-23 | unklar |  | ja | -18.6% | +0.8% | 2 | keins |
| ALXN (899866) | 2016-12-12 bis 2016-12-13 | unklar |  | ja | -16.7% | +0.6% | 2 | keins |
| HBI (1359841) | 2017-02-02 bis 2017-02-06 | unklar |  | ja | -16.8% | +0.6% | 3 | keins |
| JWN (72333) | 2017-05-11 bis 2017-05-15 | unklar |  | ja | -17.2% | +0.2% | 2 | keins |
| FL (850209) | 2017-05-12 bis 2017-05-22 | unklar |  | ja | -20.5% | +0.1% | 2 | keins |
| IPG (51644) | 2017-07-25 bis 2017-07-27 | unklar |  | ja | -16.5% | +0.2% | 3 | keins |
| PXD (1038357) | 2017-08-02 bis 2017-08-07 | unklar |  | ja | -20.6% | +0.2% | 2 | keins |
| FL (850209) | 2017-08-18 bis 2017-08-22 | unklar |  | ja | -30.4% | +0.9% | 1 | keins |
| CELG (816284) | 2017-10-26 bis 2017-10-27 | unklar |  | ja | -17.9% | +0.9% | 4 | keins |
| EVHC (1678531) | 2017-10-30 bis 2017-11-10 | unklar |  | ja | -42.5% | +0.2% | 3 | keins |
| SRCL (861878) | 2018-02-22 bis 2018-02-23 | unklar |  | ja | -19.8% | +1.7% | 1 | keins |
| PDCO (891024) | 2018-03-01 bis 2018-03-02 | unklar |  | ja | -20.8% | -0.8% | 1 | keins |
| RHT (1087423) | 2018-06-19 bis 2018-06-27 | unklar |  | ja | -24.7% | -2.7% | 2 | keins |
| NLSN (1492633) | 2018-07-26 bis 2018-07-27 | unklar |  | ja | -24.4% | -1.0% | 2 | keins |
| TWTR (1418091) | 2018-07-27 bis 2018-07-31 | unklar |  | ja | -25.8% | -0.7% | 2 | keins |
| HBI (1359841) | 2018-08-01 bis 2018-08-02 | unklar |  | ja | -17.9% | +0.4% | 2 | keins |
| SIVB (719739) | 2018-10-19 bis 2018-10-29 | unklar |  | ja | -22.5% | -4.6% | 2 | keins |
| FLIR (354908) | 2018-10-29 bis 2018-10-31 | unklar |  | ja | -15.2% | +2.0% | 1 | keins |
| ATVI (718877) | 2018-11-05 bis 2018-11-20 | unklar |  | ja | -28.6% | -2.8% | 2 | keins |
| ABMD (815094) | 2018-11-12 bis 2018-11-14 | unklar |  | ja | -22.9% | -2.8% | 3 | keins |
| JWN (72333) | 2018-11-12 bis 2018-11-19 | unklar |  | ja | -21.7% | -3.2% | 2 | keins |
| HES (4447) | 2018-12-17 bis 2018-12-24 | unklar |  | ja | -28.4% | -9.5% | 0 | keins |
| TWTR (1418091) | 2018-12-17 bis 2018-12-24 | unklar |  | ja | -26.3% | -9.5% | 0 | keins |
| XLNX (743988) | 2019-04-25 bis 2019-04-26 | unklar |  | ja | -14.9% | +0.4% | 1 | keins |
| FL (850209) | 2019-05-22 bis 2019-05-31 | unklar |  | ja | -29.9% | -3.9% | 2 | keins |
| ABMD (815094) | 2019-08-01 bis 2019-08-02 | unklar |  | ja | -28.0% | -1.6% | 2 | keins |
| CXO (1358071) | 2019-08-01 bis 2019-08-07 | unklar |  | ja | -30.4% | -3.2% | 2 | keins |
| ALXN (899866) | 2019-08-30 bis 2019-09-04 | unklar |  | ja | -13.1% | +0.5% | 1 | keins |
| ETFC (1015780) | 2019-10-01 bis 2019-10-02 | unklar |  | ja | -19.4% | -3.0% | 2 | keins |
| TWTR (1418091) | 2019-10-22 bis 2019-10-25 | unklar |  | ja | -24.4% | +0.5% | 1 | keins |
| ABMD (815094) | 2019-11-18 bis 2019-11-19 | unklar |  | ja | -17.4% | -0.0% | 1 | keins |
| SIVB (719739) | 2020-02-21 bis 2020-03-17 | unklar |  | ja | -44.8% | -24.9% | 3 | keins |
| CMA (28412) | 2020-02-24 bis 2020-03-23 | unklar |  | ja | -55.4% | -32.8% | 2 | keins |
| DFS (1393612) | 2020-02-24 bis 2020-03-23 | unklar |  | ja | -64.6% | -32.8% | 4 | keins |
| DISH (1001082) | 2020-02-24 bis 2020-03-23 | unklar |  | ja | -55.4% | -32.8% | 0 | keins |
| ETFC (1015780) | 2020-02-24 bis 2020-03-23 | unklar |  | ja | -48.7% | -32.8% | 3 | keins |
| JWN (72333) | 2020-02-24 bis 2020-03-17 | unklar |  | ja | -53.2% | -24.1% | 3 | keins |
| NLSN (1492633) | 2020-02-24 bis 2020-03-12 | treffer |  | ja | -37.4% | -25.6% | 3 | 6 |
| XEC (1168054) | 2020-02-24 bis 2020-02-27 | unklar | ja | ja | -27.9% | -10.7% | 2 | keins |
| FLIR (354908) | 2020-02-25 bis 2020-03-04 | unklar |  | ja | -28.1% | -2.9% | 1 | keins |
| XRX (108772) | 2020-02-27 bis 2020-03-23 | unklar |  | ja | -54.9% | -28.1% | 3 | keins |
| MXIM (743316) | 2020-02-28 bis 2020-03-20 | unklar |  | ja | -21.2% | -22.5% | 0 | keins |
| HBI (1359841) | 2020-03-03 bis 2020-03-19 | unklar |  | ja | -31.2% | -21.9% | 2 | keins |
| HOLX (859737) | 2020-03-03 bis 2020-03-18 | unklar |  | ja | -39.3% | -22.3% | 3 | keins |
| MRO (101778) | 2020-03-03 bis 2020-03-23 | unklar | ja | ja | -59.8% | -27.5% | 1 | keins |
| NBL (72207) | 2020-03-03 bis 2020-03-19 | unklar |  | ja | -75.1% | -21.9% | 2 | keins |
| PXD (1038357) | 2020-03-03 bis 2020-03-18 | unklar |  | ja | -54.3% | -22.3% | 3 | keins |
| XEC (1168054) | 2020-03-03 bis 2020-03-23 | unklar | ja | ja | -58.6% | -27.5% | 3 | keins |
| CXO (1358071) | 2020-03-05 bis 2020-03-18 | unklar |  | ja | -47.6% | -23.3% | 2 | keins |
| DRE (783280) | 2020-03-05 bis 2020-03-23 | unklar |  | ja | -26.6% | -28.4% | 3 | keins |
| HES (4447) | 2020-03-05 bis 2020-03-17 | unklar |  | ja | -45.9% | -19.1% | 2 | keins |
| IPG (51644) | 2020-03-05 bis 2020-03-23 | unklar |  | ja | -40.3% | -28.4% | 3 | keins |
| LEG (58492) | 2020-03-05 bis 2020-03-23 | unklar |  | ja | -43.8% | -28.4% | 1 | keins |
| PBCT (1378946) | 2020-03-05 bis 2020-03-16 | unklar |  | ja | -20.3% | -23.7% | 1 | keins |
| QRVO (1604778) | 2020-03-05 bis 2020-03-23 | unklar |  | ja | -32.3% | -28.4% | 3 | keins |
| RTN (1047122) | 2020-03-05 bis 2020-03-23 | treffer | ja | ja | -42.6% | -28.4% | 1 | 1 |
| SEE (1012100) | 2020-03-05 bis 2020-03-18 | unklar |  | ja | -43.6% | -23.3% | 2 | keins |
| AVB (915912) | 2020-03-06 bis 2020-03-24 | unklar |  | ja | -40.2% | -19.0% | 2 | keins |
| KSU (54480) | 2020-03-06 bis 2020-03-23 | unklar |  | ja | -34.5% | -25.9% | 3 | keins |
| TWTR (1418091) | 2020-03-06 bis 2020-03-18 | treffer |  | ja | -37.1% | -20.6% | 4 | keins |
| FLIR (354908) | 2020-03-09 bis 2020-03-13 | unklar |  | ja | -18.8% | -8.7% | 1 | keins |
| WBA (1618921) | 2020-03-09 bis 2020-03-12 | unklar |  | ja | -18.8% | -16.5% | 0 | keins |
| ABMD (815094) | 2020-03-11 bis 2020-03-13 | unklar |  | ja | -13.3% | -5.9% | 0 | keins |
| CTRA (858470) | 2020-03-11 bis 2020-03-23 | unklar |  | ja | -16.5% | -22.3% | 1 | keins |
| FLIR (354908) | 2020-03-18 bis 2020-03-23 | unklar |  | ja | -16.8% | -11.5% | 1 | keins |
| K (55067) | 2020-03-19 bis 2020-03-23 | unklar |  | ja | -22.3% | -6.7% | 2 | keins |
| NLSN (1492633) | 2020-03-19 bis 2020-03-23 | treffer |  | ja | -25.7% | -6.7% | 3 | 7 |
| PBCT (1378946) | 2020-03-19 bis 2020-04-03 | unklar |  | ja | -31.3% | +3.9% | 0 | keins |
| VAR (203527) | 2020-03-19 bis 2020-03-23 | unklar |  | ja | -18.6% | -6.7% | 4 | keins |
| JWN (72333) | 2020-03-20 bis 2020-03-23 | unklar |  | ja | -26.5% | -7.1% | 4 | keins |
| JWN (72333) | 2020-03-26 bis 2020-04-02 | unklar |  | ja | -27.8% | +2.1% | 6 | keins |
| DFS (1393612) | 2020-03-27 bis 2020-04-03 | unklar |  | ja | -31.6% | -5.3% | 1 | keins |
| MRO (101778) | 2020-03-27 bis 2020-04-01 | unklar | ja | ja | -19.6% | -6.0% | 0 | keins |
| RTN (1047122) | 2020-03-27 bis 2020-04-03 | treffer | ja |  | -24.6% | -5.3% | 2 | 3 |
| CMA (28412) | 2020-04-13 bis 2020-04-16 | unklar |  | ja | -25.0% | +0.4% | 2 | keins |
| HES (4447) | 2020-04-14 bis 2020-04-20 | unklar |  | ja | -10.0% | +2.3% | 1 | keins |
| LEG (58492) | 2020-05-01 bis 2020-05-13 | unklar |  | ja | -29.9% | -3.1% | 7 | keins |
| JWN (72333) | 2020-05-28 bis 2020-06-01 | unklar |  | ja | -15.5% | +0.7% | 3 | keins |
| CXO (1358071) | 2020-06-09 bis 2020-06-12 | unklar |  | ja | -19.8% | -5.9% | 0 | keins |
| DFS (1393612) | 2020-06-09 bis 2020-06-12 | unklar |  | ja | -13.5% | -5.9% | 3 | keins |
| HES (4447) | 2020-06-09 bis 2020-06-12 | unklar |  | ja | -16.9% | -5.9% | 1 | keins |
| JWN (72333) | 2020-06-09 bis 2020-06-12 | unklar |  | ja | -25.2% | -5.9% | 2 | keins |
| MRO (101778) | 2020-06-09 bis 2020-06-12 | unklar | ja | ja | -21.9% | -5.9% | 1 | keins |
| NBL (72207) | 2020-06-09 bis 2020-06-12 | unklar |  | ja | -19.4% | -5.9% | 0 | keins |
| XRX (108772) | 2020-06-09 bis 2020-06-12 | unklar |  | ja | -14.1% | -5.9% | 1 | keins |
| CMA (28412) | 2020-06-10 bis 2020-06-12 | unklar |  | ja | -12.9% | -5.1% | 3 | keins |
| TWTR (1418091) | 2020-10-28 bis 2020-11-02 | unklar |  | ja | -23.0% | -2.4% | 2 | keins |
| HBI (1359841) | 2020-11-05 bis 2020-11-06 | unklar |  | ja | -21.5% | +1.9% | 2 | keins |
| DISCK (1437107) | 2021-03-23 bis 2021-03-29 | unklar |  | ja | -45.8% | +0.8% | 2 | keins |
| TWTR (1418091) | 2021-04-30 bis 2021-05-03 | unklar |  | ja | -16.1% | -0.4% | 2 | keins |
| ATVI (718877) | 2021-11-03 bis 2021-11-04 | unklar |  | ja | -12.2% | +1.1% | 1 | keins |
| SIVB (719739) | 2022-03-04 bis 2022-03-08 | unklar |  | ja | -11.5% | -4.4% | 1 | keins |
| DISH (1001082) | 2022-05-05 bis 2022-05-12 | unklar |  | ja | -31.9% | -8.5% | 1 | keins |
| TWTR (1418091) | 2022-05-09 bis 2022-05-18 | unklar |  | ja | -26.0% | -4.8% | 5 | keins |
| TWTR (1418091) | 2022-07-08 bis 2022-07-12 | unklar |  | ja | -12.2% | -2.1% | 2 | keins |
| SIVB (719739) | 2022-07-22 bis 2022-07-26 | unklar |  | ja | -16.3% | -1.9% | 1 | keins |
| WBD (1437107) | 2022-08-05 bis 2022-08-10 | treffer |  | ja | -46.4% | +1.4% | 3 | 3 |
| SIVB (719739) | 2022-10-14 bis 2022-10-24 | unklar |  | ja | -32.8% | +3.5% | 2 | keins |
| CTLT (1596783) | 2022-10-27 bis 2022-11-04 | unklar |  | ja | -41.0% | -1.5% | 1 | keins |
| WBD (1437107) | 2022-11-02 bis 2022-11-09 | unklar |  | ja | -26.3% | -2.7% | 3 | keins |
| CMA (28412) | 2023-03-07 bis 2023-03-14 | unklar |  | ja | -36.1% | -3.1% | 2 | keins |
| SIVB (719739) | 2023-03-07 bis 2023-03-10 | unklar |  | ja | -62.5% | -4.6% | 5 | keins |
| CMA (28412) | 2023-03-17 bis 2023-03-24 | unklar |  | ja | -15.1% | +0.3% | 2 | keins |
| CTLT (1596783) | 2023-04-12 bis 2023-04-19 | unklar |  | ja | -34.2% | +1.1% | 1 | keins |
| CMA (28412) | 2023-05-02 bis 2023-05-04 | unklar |  | ja | -26.6% | -2.5% | 2 | keins |
| CTLT (1596783) | 2023-05-05 bis 2023-05-17 | unklar |  | ja | -34.8% | +2.5% | 4 | keins |
| DISH (1001082) | 2023-06-08 bis 2023-06-15 | unklar |  | ja | -19.8% | +3.8% | 0 | keins |
| DFS (1393612) | 2023-07-20 bis 2023-07-21 | unklar |  | ja | -13.7% | -0.6% | 1 | keins |
| CTLT (1596783) | 2023-10-31 bis 2023-11-02 | unklar |  | ja | -17.6% | +3.6% | 0 | keins |
| WBD (1437107) | 2023-11-08 bis 2023-11-09 | unklar |  | ja | -17.0% | -0.7% | 1 | keins |
| QRVO (1604778) | 2024-05-01 bis 2024-05-03 | unklar |  | ja | -17.9% | +1.8% | 2 | keins |
| WBA (1618921) | 2024-06-27 bis 2024-07-09 | unklar |  | ja | -31.1% | +1.9% | 3 | keins |
| QRVO (1604778) | 2024-10-30 bis 2024-10-31 | unklar |  | ja | -29.1% | -2.2% | 1 | keins |

## Fundstellen im Hauptdokument oder in Pressemitteilungen

### NLSN (1492633) 2020-02-24 bis 2020-03-12

- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.1, „spin-off“: „…ments This news release includes information that could constitute forward-looking statements made pursuant to the safe harbor provision of the Private Securities Litigation Reform Act of 1995. These statements include those set forth above under 2020 Full Year Guidance, those regarding our plan to spin-off Nielsen Global Connect as well as those that may be identified by words such as will, intend, expect, anticipate, should, could and similar expressions. These statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Fa…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.1, „spin-off“: „… expect, anticipate, should, could and similar expressions. These statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Factors leading thereto may include, without limitation, the expected benefits and costs of the spin-off transaction, the expected timing of completion of the spin-off transaction, the ability of Nielsen to complete the spin-off transaction considering the various conditions to the completion of the spin-off transaction (some of which are outside Nielsen s control, including those conditions related t…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.1, „spin-off“: „…se statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Factors leading thereto may include, without limitation, the expected benefits and costs of the spin-off transaction, the expected timing of completion of the spin-off transaction, the ability of Nielsen to complete the spin-off transaction considering the various conditions to the completion of the spin-off transaction (some of which are outside Nielsen s control, including those conditions related to regulatory approvals), business disruption during the pendenc…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.2, „spin-off“: „…t 99.2 The following discussion includes information that could constitute forward-looking statements, made pursuant to the safe harbor provisions of the Private Securities Litigation Reform Act of 1995. These statements include those set forth below under 2020 Guidance, those regarding our plan to spin-off the Company s Global Connect business as well as those that may be identified by words such as will, intend, expect, anticipate, should, could, and similar expressions. These statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.2, „spin-off“: „…expect, anticipate, should, could, and similar expressions. These statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Factors leading thereto may include, without limitation, the expected benefits and costs of the spin-off transaction, the expected timing of completion of the spin-off transaction, the ability of Nielsen to complete the spin-off transaction considering the various conditions to the completion of the spin-off transaction (some of which are outside Nielsen s control, including those conditions related t…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.2, „spin-off“: „…se statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Factors leading thereto may include, without limitation, the expected benefits and costs of the spin-off transaction, the expected timing of completion of the spin-off transaction, the ability of Nielsen to complete the spin-off transaction considering the various conditions to the completion of the spin-off transaction (some of which are outside Nielsen s control, including those conditions related to regulatory approvals), business disruption during the pendenc…“

### RTN (1047122) 2020-03-05 bis 2020-03-23

- 8-K 2020-03-13 (0001193125-20-072473, Items 1.01,9.01), 8-K, „spin-off“: „… results of operations, uses of cash, share repurchases, tax rates, R D spend, other measures of financial performance, potential future plans, strategies or transactions, credit ratings and net indebtedness, other anticipated benefits of the Rockwell Collins acquisition, the proposed merger or the spin-offs by UTC of Otis and Carrier into separate independent companies (the separation transactions ), including estimated synergies and customer cost savings resulting from the proposed merger, the expected timing of completion of the proposed merger and the separation transactions, estimated costs assoc…“

### NLSN (1492633) 2020-03-19 bis 2020-03-23

- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.1, „spin-off“: „…ments This news release includes information that could constitute forward-looking statements made pursuant to the safe harbor provision of the Private Securities Litigation Reform Act of 1995. These statements include those set forth above under 2020 Full Year Guidance, those regarding our plan to spin-off Nielsen Global Connect as well as those that may be identified by words such as will, intend, expect, anticipate, should, could and similar expressions. These statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Fa…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.1, „spin-off“: „… expect, anticipate, should, could and similar expressions. These statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Factors leading thereto may include, without limitation, the expected benefits and costs of the spin-off transaction, the expected timing of completion of the spin-off transaction, the ability of Nielsen to complete the spin-off transaction considering the various conditions to the completion of the spin-off transaction (some of which are outside Nielsen s control, including those conditions related t…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.1, „spin-off“: „…se statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Factors leading thereto may include, without limitation, the expected benefits and costs of the spin-off transaction, the expected timing of completion of the spin-off transaction, the ability of Nielsen to complete the spin-off transaction considering the various conditions to the completion of the spin-off transaction (some of which are outside Nielsen s control, including those conditions related to regulatory approvals), business disruption during the pendenc…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.2, „spin-off“: „…t 99.2 The following discussion includes information that could constitute forward-looking statements, made pursuant to the safe harbor provisions of the Private Securities Litigation Reform Act of 1995. These statements include those set forth below under 2020 Guidance, those regarding our plan to spin-off the Company s Global Connect business as well as those that may be identified by words such as will, intend, expect, anticipate, should, could, and similar expressions. These statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.2, „spin-off“: „…expect, anticipate, should, could, and similar expressions. These statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Factors leading thereto may include, without limitation, the expected benefits and costs of the spin-off transaction, the expected timing of completion of the spin-off transaction, the ability of Nielsen to complete the spin-off transaction considering the various conditions to the completion of the spin-off transaction (some of which are outside Nielsen s control, including those conditions related t…“
- 8-K 2020-02-27 (0001564590-20-006995, Items 2.02,9.01), EX-99.2, „spin-off“: „…se statements are subject to risks and uncertainties, and actual results and events could differ materially from what presently is expected. Factors leading thereto may include, without limitation, the expected benefits and costs of the spin-off transaction, the expected timing of completion of the spin-off transaction, the ability of Nielsen to complete the spin-off transaction considering the various conditions to the completion of the spin-off transaction (some of which are outside Nielsen s control, including those conditions related to regulatory approvals), business disruption during the pendenc…“
- 8-K 2020-03-20 (0001193125-20-080675, Items 5.02), 8-K, „spinoff“: „…less than the target number of PRSUs granted) will be measured based on the level of achievement of Company revenue and adjusted earnings per share goals (each weighted at 50%) measured over a performance period commencing on January 1, 2020 and ending on the date on which the Company completes the spinoff of its Global Connect business and the earned PRSUs will cliff vest on December 31, 2022, subject to the named executive officer s active employment through such date. The RSUs will vest in four equal annual installments commencing on the first anniversary of the grant date, subject, in each case, …“

### RTN (1047122) 2020-03-27 bis 2020-04-03

- 8-K 2020-03-13 (0001193125-20-072473, Items 1.01,9.01), 8-K, „spin-off“: „… results of operations, uses of cash, share repurchases, tax rates, R D spend, other measures of financial performance, potential future plans, strategies or transactions, credit ratings and net indebtedness, other anticipated benefits of the Rockwell Collins acquisition, the proposed merger or the spin-offs by UTC of Otis and Carrier into separate independent companies (the separation transactions ), including estimated synergies and customer cost savings resulting from the proposed merger, the expected timing of completion of the proposed merger and the separation transactions, estimated costs assoc…“
- 8-K 2020-04-03 (0001193125-20-097237, Items 1.02,2.01,3.01,3.03,5.01,5.02,5.03,8.01,9.01), EX-99.1, „spin-off“: „…., April 3, 2020 Raytheon Technologies Corporation (NYSE: RTX) announced the successful completion of the all-stock merger of equals transaction between Raytheon Company and United Technologies Corporation on April 3, 2020, following the completion by United Technologies of its previously announced spin-offs of its Carrier and Otis businesses. Headquartered in Waltham, Mass., Raytheon Technologies is one of the largest aerospace and defense companies in the world with approximately $74 billion in pro forma 2019 net sales and a global team of 195,000 employees, including 60,000 engineers and scientists…“
- 8-K 2020-04-03 (0001193125-20-097237, Items 1.02,2.01,3.01,3.03,5.01,5.02,5.03,8.01,9.01), EX-99.1, „spin-off“: „…er measures of financial performance, potential future plans, strategies or transactions, credit ratings and net indebtedness, other anticipated benefits to RTC of UTC s Rockwell Collins acquisition, the merger between United Technologies Corporation ( UTC ) and Raytheon Company ( Raytheon ) or the spin-offs by UTC of Otis and Carrier into separate independent companies (the separation transactions ), including estimated synergies and customer cost savings resulting from the merger and the separation transactions and other statements that are not historical facts. All forward-looking statements involv…“

### WBD (1437107) 2022-08-05 bis 2022-08-10

- 8-K 2022-08-04 (0001437107-22-000205, Items 2.02,8.01,9.01), EX-99.3, „separation and distribution“: „…g-term debt 124 10 Total long-term debt $ 31,405 $ 1,713 In March 2022, SpinCo issued $30,000 of senior unsecured notes ( Senior notes ) at par. The interest rates, maturities, and principal amounts of each class of notes are reflected in the table below. On April 8, 2022, in connection with AT T s separation and distribution of WarnerMedia, and merger of Spinco with WBD, we paid a special cash dividend of $20,000 to Parent from the proceeds of the Senior notes issuance in March. Prior to the transaction close date, $10,000 of the proceeds from the issuance was received by Parent. With the exception of the Floating rate…“
- 8-K 2022-08-04 (0001437107-22-000205, Items 2.02,8.01,9.01), EX-99.3, „separation and distribution“: „…ivables sold exceeding net cash flow impacts (e.g., collect and reinvest). The transferred receivables are fully guaranteed by our bankruptcy-remote subsidiaries, which hold additional receivables in the amount of $3,359 that are pledged as collateral under this agreement. Upon completion of AT T s separation and distribution of WarnerMedia, and merger of SpinCo on April 8, 2022, AT T Mobility LLC receivables no longer serve as collateral under this agreement. AT T intercompany receivables and related party, DirecTV, receivables were pledged as additional collateral. Any reduction of collateral in the future may impact …“
- 8-K 2022-08-04 (0001437107-22-000205, Items 2.02,8.01,9.01), EX-99.3, „separation and distribution“: „…ady accrued on the balance sheet. In our opinion, although the outcomes of these proceedings are uncertain, they should not have a material adverse effect on our financial position, results of operations or cash flows. NOTE 16. SUBSEQUENT EVENTS Discovery Merger On April 8, 2022, AT T completed the separation and distribution of WarnerMedia, and merger of SpinCo, an AT T subsidiary formed to hold the WarnerMedia business, with a subsidiary of Discovery, Inc., which was renamed Warner Bros. Discovery Inc. (WBD). Each AT T shareholder received 0.241917 shares of WBD common stock for each share of AT T common stock held as…“

## Abruffehler (0)

