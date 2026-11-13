# Datenkorrektur Piotroski „keine neuen Aktien“: Wirkung auf Signale, Filter und Auswahl

Erstellt mit `tools/auswertung_eq_offer.py` aus dem Cache `fundamental/scores_eq_offer` (Piotroski EQ_OFFER splitbereinigt (Jakob 13.11.2026)). Zeitraum 2016-10-01 bis 2024-12-31 (33 Stichtage), Tresor zu. Die Korrektur wurde vor dieser Auswertung als übernommen festgehalten (docs/FUNDAMENTAL.md); diese Zahlen dokumentieren nur die Wirkung.

Kontrolle: bisherige Rechnung im neuen Lauf gegen den Cache `fundamental/scores` vom ersten Lauf: 12962 von 13011 Firmen-Stichtagen gleich (Piotroski und Ausschluss); Zeilen nur in einem der beiden: 0. Piotroski-Werte verschieden: 0. Die übrigen Abweichungen betreffen nur die gespeicherte Spalte „ausgeschlossen“ (der alte Cache stammt von vor der Rundungsregel für hochgerechnete Piotroski-Werte; der Backtest wendet die Filter ohnehin neu an) oder Marktwerte nach späteren Kursdaten. Deshalb wird der Vergleichslauf aus demselben Cache gerechnet (Spalten der bisherigen Rechnung, Cache `fundamental/scores_eq_offer_bisher`), nicht aus dem alten.

## Quelle des Vorjahreswerts

Firmen-Stichtage mit Signal EQ_OFFER: 12595. Weg A (Vergleichswert aus derselben Einreichung): 12583; Rückfall B (Erstmeldung mit Split-Faktoren): 12; keine bekannte Aktienzahl im neuen Weg (Rückfall auf die bisherige Rechnung): 0.

Konsistenz mit der Tabelle der Abschlüsse: Wert t abweichend in 0, Erstmeldung t−1 abweichend in 0 Firmen-Stichtagen.

## Signal „keine neuen Aktien“: geänderte Fälle

Mit beiden Werten: 12595 Firmen-Stichtage; geändert 150 (1.19%), davon 0→1 (bisher fälschlich „neue Aktien“) 128, 1→0 22. Betroffene Firmen: 44.

| Jahr | Firmen-Stichtage | geändert | 0→1 | 1→0 | Firmen |
| --- | --- | --- | --- | --- | --- |
| 2016 | 372 | 11 | 11 | 0 | 11 |
| 2017 | 1488 | 29 | 23 | 6 | 15 |
| 2018 | 1482 | 32 | 27 | 5 | 13 |
| 2019 | 1502 | 13 | 12 | 1 | 9 |
| 2020 | 1521 | 11 | 11 | 0 | 5 |
| 2021 | 1549 | 13 | 13 | 0 | 6 |
| 2022 | 1556 | 13 | 8 | 5 | 6 |
| 2023 | 1562 | 16 | 12 | 4 | 7 |
| 2024 | 1563 | 12 | 11 | 1 | 6 |

Davon mit Split-Ereignis zwischen den Einreichungen: 101; ohne Split-Ereignis: 49.

Geänderte Firmen (Ticker, Split-Faktor, Anzahl Stichtage):

SBUX (2, 1), AWK (1, 2), MPC (2, 2), KR (2, 2), HBI (4, 2), PPG (2, 2), CF (5, 2), OI (1, 1), ROST (2, 2), GPN (2, 4), NKE (2, 4), COR (1, 4), CHD (2, 4), HWM (1, 4), LEN (1, 4), BF.B (2, 8), AOS (2, 2), J (1, 4), XRX (0.25, 4), CMCSK (2, 4), TMO (1, 4), SCG (1, 4), ISRG (3, 4), HSIC (2, 4), CPRT (2, 2), FISV (2, 4), TJX (2, 3), SKYD (1, 4), FAST (2, 4), PCAR (1, 4), AAPL (4, 4), EW (3, 4), ODFL (1.5, 4), CSX (3, 4), SHW (3, 4), GE (0.125, 4), ABMD (1, 2), TDG (1, 4), GRMN (1, 4), COP (1, 4), FTNT (5, 4), MNST (2, 3), SRE (2, 3), WMT (3, 3)

## Gegenprobe Weg A gegen Weg B

Beide Wege verfügbar: 12583 Firmen-Stichtage. Gleiches Signal: 12497; verschieden: 86. Abweichung der Vorjahreswerte: Median 0.000%, über 1 %: 205, über 10 %: 151.

Ursachen (Firmen-Stichtage): Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt) 37, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis) 30, Skalierungsfehler der Erstmeldung 19.

Verschiedene Signale je Firma (Ticker, Faktor der Kursreihe, Verhältnis A/B, Ursache, Stichtage):

BAX (1.841, 0.543, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 2), OI (1, 1000.000, Skalierungsfehler der Erstmeldung, 1), PPL (1.07365, 0.931, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 2), AWK (1, 1.001, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 2), APD (1.081, 0.925, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 4), COR (1, 1000.000, Skalierungsfehler der Erstmeldung, 4), HWM (1, 0.334, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), LEN (1, 0.889, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), J (1, 1.011, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), TMO (1, 1.001, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), SCG (1, 1.001, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), GE (1.04, 0.962, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 4), PCAR (1, 1000000.000, Skalierungsfehler der Erstmeldung, 4), SKYD (1, 1.637, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), RTX (1.589, 0.629, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 4), FTV (1.195, 0.837, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 4), MTCH (3.502, 0.616, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 2), IBM (1.046, 0.956, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 4), EXC (1.402, 0.713, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 4), ABMD (1, 0.001, Skalierungsfehler der Erstmeldung, 2), TDG (1, 1.066, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), GRMN (1, 0.001, Skalierungsfehler der Erstmeldung, 4), ZBH (1.03, 0.971, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 4), COP (1, 1000.000, Skalierungsfehler der Erstmeldung, 4), DHR (1.128, 0.887, Faktor der Kursreihe passt nicht (z. B. Abspaltung als Split geführt), 3)

## Weg A weicht von der Erstmeldung ab, ohne Split-Ereignis (getrennt ausgewiesen)

317 von 12248 Firmen-Stichtagen (83 Firmen); Median der Abweichung 0.038%; mit geändertem Signal: 49 (14 Firmen); Abweichung über 40 % (Hinweis auf einen Split ohne Yahoo-/Tiingo-Ereignis oder eine Aktiendividende): 11 Firmen.

Mit geändertem Signal (Ticker, Verhältnis A/Erstmeldung, Ursache, Stichtage):

HWM (0.334, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), J (1.011, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), PCAR (1000000.000, Skalierungsfehler der Erstmeldung, 4), TMO (1.001, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), SCG (1.001, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), OI (1000.000, Skalierungsfehler der Erstmeldung, 1), ABMD (0.001, Skalierungsfehler der Erstmeldung, 2), LEN (0.889, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), GRMN (0.001, Skalierungsfehler der Erstmeldung, 4), COR (1000.000, Skalierungsfehler der Erstmeldung, 4), COP (1000.000, Skalierungsfehler der Erstmeldung, 4), TDG (1.066, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4), AWK (1.001, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 2), SKYD (1.637, ohne Split-Ereignis (fehlendes Ereignis, Aktiendividende oder Neuausweis), 4)

## Rückfall B ohne Split-Ereignis: Verdachtsfälle

Rückfall B ohne Faktor: 12 Firmen-Stichtage; Verhältnis t/t−1 außerhalb (0.7, 1.4): 4 (1 Firmen). Diese bleiben unbereinigt (nichts wird geraten).

FTI 2017-04-03 (0.00), FTI 2017-07-03 (0.00), FTI 2017-10-02 (0.00), FTI 2018-01-01 (0.00)

## Piotroski und Filter

Piotroski-Wert (für den Filter) geändert: 150 Firmen-Stichtage. Grenze Piotroski ≤ 3: nicht mehr ausgeschlossen 2 (1 Firmen), neu ausgeschlossen 8 (2 Firmen). Ausschluss gesamt (alle Filter): bisher 1344, korrigiert 1348; gewechselt 4.

Grenzwechsel (Ticker Stichtag alt→neu): CF 2016-10-03 3→4, CF 2017-01-02 3→4, HWM 2017-04-03 5→3, HWM 2017-07-03 5→3, HWM 2017-10-02 5→3, HWM 2018-01-01 5→3, GE 2022-04-01 5→3, GE 2022-07-01 5→3, GE 2022-10-03 5→3, GE 2023-01-02 5→3

## Auswahl Fundamental A und B (ohne Kurse nachgestellt)

| Buch | Stichtage mit anderer Auswahl | Titelwechsel gesamt | Titel nur bisher | Titel nur korrigiert |
| --- | --- | --- | --- | --- |
| A | 5 von 33 | 5 | 4 | 3 |
| B | 8 von 33 | 9 | 7 | 6 |

- **A:** nur bisher BKNG, CF, KR, URBN; nur korrigiert CF, SRE, WU.
- **B:** nur bisher CDNS, CTXS, FCX, GWW, HRB, JBHT, TSN; nur korrigiert AAPL, AMZN, COO, GRMN, J, PHM.

Titelwechsel = Plätze je Stichtag, die mit einem anderen Titel besetzt sind (Summe über die Stichtage).
