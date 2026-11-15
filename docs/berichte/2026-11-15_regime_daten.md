# Regime-Engine: Datenprüfung (15.11.2026)

Kriterien aus docs/REGIME.md (vor dem Laden festgelegt). Tresor zu: Daten bis 31.12.2024.

## Abdeckung der Makroreihen

| Reihe | erster Datenstand | gebraucht ab | erste Beobachtung | ok |
| --- | --- | --- | --- | --- |
| UNRATE | 15.03.1960 | 01.10.1993 | 01.01.1948 | ja |
| T10Y3M | 05.01.1982 | 01.01.1994 | 04.01.1982 | ja |
| BAA10Y | 03.01.1986 | 01.01.1994 | 02.01.1986 | ja |
| DGS3MO | 02.09.1981 | 01.01.1994 | 01.09.1981 | ja |

^SP500TR (Langtest): erster Kurs 04.01.1988, 6052 Tage bis 31.12.2011 – ok (gebraucht: 10 Monatsschlüsse vor dem 01.01.1995).

**Langtest 1995–2011: möglich**

## XEON.DE

Erster Kurs 02.01.2012, größte Lücke 0 Handelstage (Kalender SPYI.DE).

| Kriterium | bestanden |
| --- | --- |
| 1 Lücken | ja |
| 2 Tagesänderung | NEIN |
| 3 Jahresrendite | ja |

Tagesänderungen über ±0.25%: 3 – 16.03.2020 +0.53%, 17.03.2020 -0.47%, 21.04.2020 -0.31%

| Jahr | XEON.DE | EZB-Einlagesatz (Mittel) | Abstand |
| --- | --- | --- | --- |
| 2012 | +0.10 % | +0.13 % | -0.03 Pp. |
| 2013 | -0.01 % | +0.00 % | -0.01 Pp. |
| 2014 | +0.00 % | -0.09 % | +0.09 Pp. |
| 2015 | -0.23 % | -0.21 % | -0.02 Pp. |
| 2016 | -0.48 % | -0.38 % | -0.10 Pp. |
| 2017 | -0.52 % | -0.40 % | -0.12 Pp. |
| 2018 | -0.47 % | -0.40 % | -0.07 Pp. |
| 2019 | -0.49 % | -0.43 % | -0.06 Pp. |
| 2020 | -0.57 % | -0.50 % | -0.07 Pp. |
| 2021 | -0.58 % | -0.50 % | -0.08 Pp. |
| 2022 | -0.04 % | +0.08 % | -0.12 Pp. |
| 2023 | +3.30 % | +3.31 % | -0.01 Pp. |
| 2024 | +3.78 % | +3.73 % | +0.05 Pp. |

**XEON.DE: NICHT bestanden – defensive Anlage ist Kasse zu 0 % (Kriterien werden nicht angepasst)**