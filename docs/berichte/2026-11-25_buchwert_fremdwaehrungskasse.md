# Datenkorrektur Buchwert: Fremdwährungskasse zum Laufkurs (25.11.2026)

Stand: **ausgeführt** 25.11.2026 13:14; Sicherung vorher: `journal_2026-11-25_131458.sqlite`

Grundlage: Befund 1, Entscheidungen Jakob 25.11.2026 (D3 korrigieren, D4 Spalte `kasse` neu plus `fx`). Werkzeug `tools/buchwert_korrektur_20261125.py`, Regeln im Kopf des Werkzeugs.

Δ = EUR-Kasse + USD-Kasse / Laufkurs − gespeicherte Kasse; Wert und Wert mit Modellgebühr verschieben sich um Δ, der Positionsteil bleibt.

## fundamental_a

| Tag | NYSE | Laufkurs (Quelle) | EUR-Kasse | USD-Kasse $ | Kasse alt | Kasse neu | Δ | Wert alt | Wert neu | Modell alt | Modell neu | Status |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2026-11-02 | 2026-11-02 | – | 10.000,00 | – | 10.000,00 | 10.000,00 | 0,00 | 10.000,00 | 10.000,00 | – | – | unverändert |
| 2026-11-03 | 2026-11-03 | – | 10.000,00 | – | 10.000,00 | 10.000,00 | 0,00 | 10.000,00 | 10.000,00 | – | – | unverändert |
| 2026-11-09 | 2026-11-06 | – | 10.000,00 | – | 10.000,00 | 10.000,00 | 0,00 | 10.000,00 | 10.000,00 | 10.000,00 | 10.000,00 | unverändert |
| 2026-11-10 | 2026-11-09 | 1,11657 (Ausführung) | 931,21 | 4.855,83 | 5.236,00 | 5.280,09 | 44,09 | 10.007,48 | 10.051,58 | 10.007,50 | 10.051,59 | korrigieren |
| 2026-11-11 | 2026-11-11 | 1,10902 (Rückrechnung) | 931,21 | 4.855,83 | 5.236,00 | 5.309,70 | 73,70 | 10.067,40 | 10.141,11 | 10.067,42 | 10.141,12 | korrigieren |
| 2026-11-12 | 2026-11-12 | 1,10583 (Ausführung) | 931,21 | 824,38 | 1.590,35 | 1.676,70 | 86,34 | 9.934,40 | 10.020,74 | 9.934,42 | 10.020,76 | korrigieren |
| 2026-11-13 | 2026-11-13 | 1,10278 (Rückrechnung) | 931,21 | 824,38 | 1.590,35 | 1.678,76 | 88,40 | 10.015,11 | 10.103,51 | 10.015,12 | 10.103,52 | korrigieren |
| 2026-11-16 | 2026-11-16 | 1,09987 (Ausführung) | 931,21 | 298,42 | 1.112,15 | 1.202,53 | 90,38 | 10.005,60 | 10.095,98 | 10.005,61 | 10.095,99 | korrigieren |
| 2026-11-17 | 2026-11-17 | 1,10084 (Rückrechnung) | 931,21 | 298,42 | 1.112,15 | 1.202,29 | 90,14 | 9.850,80 | 9.940,94 | 9.850,81 | 9.940,95 | korrigieren |
| 2026-11-18 | 2026-11-18 | 1,09769 (Rückrechnung) | 931,21 | 298,42 | 1.112,15 | 1.203,07 | 90,92 | 9.826,48 | 9.917,39 | 9.826,49 | 9.917,41 | korrigieren |
| 2026-11-19 | 2026-11-19 | 1,09709 (Rückrechnung) | 931,21 | 298,42 | 1.112,15 | 1.203,22 | 91,07 | 9.701,43 | 9.792,49 | 9.701,44 | 9.792,51 | korrigieren |
| 2026-11-23 | 2026-11-23 | 1,09039 (Rückrechnung) | 931,21 | 304,27 | 1.117,51 | 1.210,25 | 92,74 | 9.765,50 | 9.858,24 | 9.765,51 | 9.858,25 | korrigieren |
| 2026-11-24 | 2026-11-24 | 1,09673 (Rückrechnung) | 931,21 | 304,27 | 1.117,51 | 1.208,64 | 91,13 | 9.900,07 | 9.991,20 | 9.900,08 | 9.991,21 | korrigieren |

Wert am 2026-11-24: alt 9.900,07 €, neu 9.991,20 € (gegen 10.000 €: -1,00 % → -0,09 %)


## fundamental_b

| Tag | NYSE | Laufkurs (Quelle) | EUR-Kasse | USD-Kasse $ | Kasse alt | Kasse neu | Δ | Wert alt | Wert neu | Modell alt | Modell neu | Status |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2026-11-02 | 2026-11-02 | – | 10.000,00 | – | 10.000,00 | 10.000,00 | 0,00 | 10.000,00 | 10.000,00 | – | – | unverändert |
| 2026-11-03 | 2026-11-03 | – | 10.000,00 | – | 10.000,00 | 10.000,00 | 0,00 | 10.000,00 | 10.000,00 | – | – | unverändert |
| 2026-11-09 | 2026-11-06 | – | 10.000,00 | – | 10.000,00 | 10.000,00 | 0,00 | 10.000,00 | 10.000,00 | 10.000,00 | 10.000,00 | unverändert |
| 2026-11-10 | 2026-11-09 | 1,11657 (Ausführung) | 2.167,21 | 3.101,22 | 4.906,58 | 4.944,66 | 38,08 | 9.984,43 | 10.022,51 | 9.984,44 | 10.022,53 | korrigieren |
| 2026-11-11 | 2026-11-11 | 1,10902 (Rückrechnung) | 2.167,21 | 3.101,22 | 4.906,58 | 4.963,57 | 56,99 | 9.998,81 | 10.055,80 | 9.998,82 | 10.055,82 | korrigieren |
| 2026-11-12 | 2026-11-12 | 1,10583 (Ausführung) | 2.167,21 | 730,06 | 2.762,34 | 2.827,40 | 65,06 | 9.954,35 | 10.019,42 | 9.954,36 | 10.019,43 | korrigieren |
| 2026-11-13 | 2026-11-13 | 1,10278 (Rückrechnung) | 2.167,21 | 730,06 | 2.762,34 | 2.829,23 | 66,89 | 10.050,93 | 10.117,82 | 10.050,94 | 10.117,83 | korrigieren |
| 2026-11-16 | 2026-11-16 | 1,09987 (Ausführung) | 2.167,21 | 730,06 | 2.762,34 | 2.830,98 | 68,64 | 10.018,69 | 10.087,33 | 10.018,70 | 10.087,34 | korrigieren |
| 2026-11-17 | 2026-11-17 | 1,10084 (Rückrechnung) | 2.167,21 | 730,06 | 2.762,34 | 2.830,39 | 68,06 | 9.899,92 | 9.967,97 | 9.899,93 | 9.967,99 | korrigieren |
| 2026-11-18 | 2026-11-18 | 1,09769 (Rückrechnung) | 2.167,21 | 730,06 | 2.762,34 | 2.832,29 | 69,96 | 9.870,03 | 9.939,99 | 9.870,04 | 9.940,00 | korrigieren |
| 2026-11-19 | 2026-11-19 | 1,09709 (Rückrechnung) | 2.167,21 | 730,06 | 2.762,34 | 2.832,66 | 70,32 | 9.757,61 | 9.827,94 | 9.757,63 | 9.827,95 | korrigieren |
| 2026-11-23 | 2026-11-23 | 1,09039 (Rückrechnung) | 2.167,21 | 735,93 | 2.767,72 | 2.842,13 | 74,41 | 9.860,67 | 9.935,08 | 9.860,68 | 9.935,09 | korrigieren |
| 2026-11-24 | 2026-11-24 | 1,09673 (Rückrechnung) | 2.167,21 | 735,93 | 2.767,72 | 2.838,23 | 70,51 | 9.869,66 | 9.940,17 | 9.869,68 | 9.940,19 | korrigieren |

Wert am 2026-11-24: alt 9.869,66 €, neu 9.940,17 € (gegen 10.000 €: -1,30 % → -0,60 %)


## Abnahme (Plan Punkt 5.4)

- Rekonstruierte Kasse (alte Konvention) je Tag auf den Cent gleich der gespeicherten: ja (26 von 26 Zeilen).
- Laufkurs je Tag in beiden Büchern gleich (≤ 1e-4) und mit Belegkursen verträglich: ja.
- Brüche: 0.
- Zu korrigieren: 20, bereits korrigiert: 0, unverändert: 6.
- Andere Bücher (real, crossover, momentum, regime): nicht angefasst.
- Querprüfung mit dem Code des Tageslaufs: fundamental_a 2026-11-24: Kasse neu 1.208,6417 €, Journal.kasse_bewertet 1.208,6417 € – gleich
- Querprüfung mit dem Code des Tageslaufs: fundamental_b 2026-11-24: Kasse neu 2.838,2277 €, Journal.kasse_bewertet 2.838,2277 € – gleich

## Nach der Ausführung

- Zweiter Durchgang am echten Journal: zu korrigieren 0, bereits korrigiert 20, unverändert 6, Brüche 0.
