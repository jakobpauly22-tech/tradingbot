# Satellite-Strategien der Technik-Engine – gewertete Backtests (Modellkorrektur)

Stand 02.11.2026 20:04. Zeitraum 2013-01-03 bis 2024-12-31, Kapital 1,250 € (Schatten), 11 ETFs/ETCs laut `config/technik.yaml`. Getestete Varianten bisher: 5 (diese Neuberechnung zählt nicht als neue Variante).

Buy & Hold: alle ETFs gleich gewichtet, quartalsweise, Umsetzung `kostenfrei` (Entscheidung Jakob 03.11.2026).

## Daten

- Universum: IUSA.DE (Aktien USA), EUNK.DE (Aktien Europa), EUNN.DE (Aktien Japan), SXR1.DE (Aktien Pazifik ex Japan), EUNM.DE (Aktien Schwellenländer), EUNH.DE (Anleihen Euro-Staaten), EUN5.DE (Anleihen Euro-Unternehmen), IBCI.DE (Anleihen Euro inflationsindexiert), SXRM.DE (Anleihen US-Staaten), IUSP.DE (Anleihen Schwellenländer), 4GLD.DE (Gold)
- **SXRM.DE über Ersatzquelle CSBGU0.SW** (gleicher Fonds, gleiche Anteilsklasse, in EUR umgerechnet): an 1484 Tagen mit Xetra-Umsatz Median-Abweichung 0,06% (Grenze 0,5 %, bestanden), 95-%-Quantil 0,27%. Abrechnung über die USD-Kasse (Netto-Tausch), Gebühr nach dem Xetra-Plan.
- Korrektur: IUSA.DE 2013-02-20: Ausschüttung 0.0508 € ergänzt (Yahoo führt für IUSA 2013 keine Ausschüttungen (Jakob 03.11.2026))
- Korrektur: IUSA.DE 2013-05-29: Ausschüttung 0.0532 € ergänzt (Yahoo führt für IUSA 2013 keine Ausschüttungen (Jakob 03.11.2026))
- Korrektur: IUSA.DE 2013-08-28: Ausschüttung 0.0437 € ergänzt (Yahoo führt für IUSA 2013 keine Ausschüttungen (Jakob 03.11.2026))
- Korrektur: IUSA.DE 2013-11-27: Ausschüttung 0.0429 € ergänzt (Yahoo führt für IUSA 2013 keine Ausschüttungen (Jakob 03.11.2026))
- Korrektur: EUNH.DE 2012-06-11: O/H/T/S [104.39, 104.39, 104.98, 104.39] → 104.980 (Vortagesschluss; Hoch unter Tief, Schluss außerhalb der Spanne)
- Korrektur: EUN5.DE 2012-06-12: O/H/T/S [117.6, 117.63, 117.41, 117.23] → 117.720 (Vortagesschluss; Schluss außerhalb der Spanne)
- Korrektur: EUN5.DE 2012-06-13: O/H/T/S [117.05, 117.05, 117.05, 116.97] → 117.720 (Vortagesschluss; Schluss außerhalb der Spanne)
- **Plausibilität IUSA.DE** (inkl. Dividenden) gegen den ersetzten ETF: 16,32% gegen 16,53% p.a., Differenz -0.206 Pp. (Grenze ±0.3, bestanden); nur Kurs 14,56%. Die Prüfung rechnet vor Steuern (Total-Return-Index, Dividenden reinvestiert, ohne Steuern und Kosten). Im Backtest gehen die Dividenden als Zahlung in die Kasse und werden als Aktienfonds versteuert (Teilfreistellung 30 %).
- Xetra-Gold: Zwei Tage (26. und 29.06.2017) mit Schluss über dem Tageshoch (0,14 % und 0,45 %) unverändert (Entscheidung Jakob 03.11.2026). Steuer konservativ mit Abgeltungsteuer (§ 23 EStG offen im Steuermodul).

## Entscheidungsbaum (docs/TECHNIK.md)

| Variante | Sharpe ≥ B&H ohne Kosten in beiden Hälften | Kriterien nach Kosten bestanden |
| --- | --- | --- |
| crossover | **nein** | **nein** |
| momentum | **nein** | **nein** |
| price_channel | **nein** | **nein** |
| rsi2 | **nein** | **nein** |
| regime | **nein** | **nein** |

**Zweig a):** Weder Crossover noch Momentum erreichen ohne Kosten den Sharpe von Buy & Hold in beiden Hälften: Die Technik-Engine ist kein Renditebaustein. Echtes Geld bleibt im Core; Crossover und Momentum laufen im Paper Trading als Schatten vorwärts mit.

## Kennzahlen vor Steuern

| Variante | Art | Abschnitt | Rendite p.a. | Sharpe | max. Drawdown | B&H Rendite | B&H Sharpe | B&H Drawdown | Sharpe ≥ B&H | DD ≥ −20 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| crossover | nach Kosten | gesamt | 0,85% | 0,06 | -26,08% | 4,89% | 0,60 | -17,09% | **nein** | **nein** |
| crossover | nach Kosten | Hälfte 1 | -1,92% | -0,21 | -26,08% | 3,64% | 0,53 | -14,31% | **nein** | **nein** |
| crossover | nach Kosten | Hälfte 2 | 3,69% | 0,34 | -22,40% | 6,16% | 0,68 | -17,09% | **nein** | **nein** |
| crossover | ohne Kosten | gesamt | 3,97% | 0,51 | -12,36% | 4,89% | 0,60 | -17,09% | **nein** | ja |
| crossover | ohne Kosten | Hälfte 1 | 1,62% | 0,28 | -11,71% | 3,64% | 0,53 | -14,31% | **nein** | ja |
| crossover | ohne Kosten | Hälfte 2 | 6,37% | 0,72 | -12,36% | 6,16% | 0,68 | -17,09% | ja | ja |
| momentum | nach Kosten | gesamt | 1,98% | 0,17 | -20,64% | 4,89% | 0,60 | -17,09% | **nein** | **nein** |
| momentum | nach Kosten | Hälfte 1 | 1,02% | 0,12 | -20,64% | 3,64% | 0,53 | -14,31% | **nein** | **nein** |
| momentum | nach Kosten | Hälfte 2 | 2,94% | 0,23 | -20,16% | 6,16% | 0,68 | -17,09% | **nein** | **nein** |
| momentum | ohne Kosten | gesamt | 4,46% | 0,44 | -18,84% | 4,89% | 0,60 | -17,09% | **nein** | ja |
| momentum | ohne Kosten | Hälfte 1 | 3,18% | 0,34 | -18,84% | 3,64% | 0,53 | -14,31% | **nein** | ja |
| momentum | ohne Kosten | Hälfte 2 | 5,76% | 0,56 | -13,22% | 6,16% | 0,68 | -17,09% | **nein** | ja |
| price_channel | nach Kosten | gesamt | -5,27% | -0,93 | -50,71% | 4,89% | 0,60 | -17,09% | **nein** | **nein** |
| price_channel | nach Kosten | Hälfte 1 | -4,66% | -0,79 | -30,39% | 3,64% | 0,53 | -14,31% | **nein** | **nein** |
| price_channel | nach Kosten | Hälfte 2 | -5,88% | -1,06 | -34,43% | 6,16% | 0,68 | -17,09% | **nein** | **nein** |
| price_channel | ohne Kosten | gesamt | 2,95% | 0,43 | -12,70% | 4,89% | 0,60 | -17,09% | **nein** | ja |
| price_channel | ohne Kosten | Hälfte 1 | 2,81% | 0,55 | -12,70% | 3,64% | 0,53 | -14,31% | ja | ja |
| price_channel | ohne Kosten | Hälfte 2 | 3,08% | 0,33 | -12,40% | 6,16% | 0,68 | -17,09% | **nein** | ja |
| rsi2 | nach Kosten | gesamt | -7,36% | -2,28 | -60,87% | 4,89% | 0,60 | -17,09% | **nein** | **nein** |
| rsi2 | nach Kosten | Hälfte 1 | -13,97% | -3,15 | -59,71% | 3,64% | 0,53 | -14,31% | **nein** | **nein** |
| rsi2 | nach Kosten | Hälfte 2 | -0,24% | -0,64 | -5,37% | 6,16% | 0,68 | -17,09% | **nein** | ja |
| rsi2 | ohne Kosten | gesamt | 2,00% | 0,39 | -10,13% | 4,89% | 0,60 | -17,09% | **nein** | ja |
| rsi2 | ohne Kosten | Hälfte 1 | 1,78% | 0,47 | -10,13% | 3,64% | 0,53 | -14,31% | **nein** | ja |
| rsi2 | ohne Kosten | Hälfte 2 | 2,23% | 0,31 | -9,25% | 6,16% | 0,68 | -17,09% | **nein** | ja |
| regime | nach Kosten | gesamt | -1,55% | -0,22 | -38,80% | 4,89% | 0,60 | -17,09% | **nein** | **nein** |
| regime | nach Kosten | Hälfte 1 | -2,44% | -0,23 | -27,48% | 3,64% | 0,53 | -14,31% | **nein** | **nein** |
| regime | nach Kosten | Hälfte 2 | -0,65% | -0,21 | -27,49% | 6,16% | 0,68 | -17,09% | **nein** | **nein** |
| regime | ohne Kosten | gesamt | 4,31% | 0,47 | -16,23% | 4,89% | 0,60 | -17,09% | **nein** | ja |
| regime | ohne Kosten | Hälfte 1 | 3,29% | 0,39 | -16,23% | 3,64% | 0,53 | -14,31% | **nein** | ja |
| regime | ohne Kosten | Hälfte 2 | 5,34% | 0,57 | -13,09% | 6,16% | 0,68 | -17,09% | **nein** | ja |

## Handel, Kosten, Investitionsgrad

| Variante | Trades | Kosten | Investitionsgrad (Mittel) | gescheitert am Stückpreis | gescheitert an der 125-€-Regel | Steuern gezahlt | Rendite nach Verkauf und Steuern |
| --- | --- | --- | --- | --- | --- | --- | --- |
| crossover | 250 | 459 € | 82,25% | 1009 | 967 | 11 € | 0,51% |
| momentum | 218 | 370 € | 81,87% | 60 | 32 | 34 € | 1,50% |
| price_channel | 540 | 919 € | 55,68% | 264 | 172 | 0 € | -5,33% |
| rsi2 | 538 | 855 € | 6,41% | 376 | 708 | 0 € | -7,39% |
| regime | 384 | 690 € | 88,92% | 1119 | 583 | 0 € | -1,61% |
| buy_and_hold | 24 | 0 € | 82,37% | 57 | 0 | 63 € | 4,08% |

Gescheiterte Orders zählen je Tag und ETF; bei stehendem Signal wird ein Kauf täglich erneut versucht.

## Investitionsgrad je ETF (gekaufter Wert / Zielwert neuer Positionen, Rundung auf ganze Stücke)

| ETF | crossover | momentum | price_channel | rsi2 | regime |
| --- | --- | --- | --- | --- | --- |
| IUSA.DE | 94,48% (13) | 95,31% (19) | 92,85% (33) | 96,15% (48) | 94,08% (19) |
| EUNK.DE | 91,97% (14) | 89,72% (13) | 89,04% (34) | 92,23% (35) | 91,70% (10) |
| EUNN.DE | 93,74% (11) | 95,65% (14) | 91,53% (34) | 95,98% (28) | 93,32% (28) |
| SXR1.DE | 81,45% (21) | 83,47% (20) | 81,31% (25) | 87,58% (18) | 77,65% (26) |
| EUNM.DE | 96,44% (12) | 96,46% (4) | 94,90% (30) | 94,42% (30) | 95,49% (21) |
| EUNH.DE | 79,08% (11) | 72,15% (8) | 71,45% (16) | 79,88% (16) | 85,96% (14) |
| EUN5.DE | 77,98% (8) | 77,27% (4) | 74,25% (14) | 79,63% (25) | 87,90% (11) |
| IBCI.DE | 66,93% (11) | 74,70% (5) | 82,57% (11) | 76,58% (21) | 77,72% (17) |
| SXRM.DE | 84,98% (12) | 78,16% (9) | 73,81% (28) | 81,51% (16) | 79,08% (16) |
| IUSP.DE | 90,52% (3) | 96,64% (1) | 90,53% (20) | 87,83% (15) | 90,14% (14) |
| 4GLD.DE | 90,88% (11) | 92,01% (14) | 92,69% (26) | 93,05% (17) | 91,93% (18) |

In Klammern: Zahl der Käufe.

## Vergleich mit dem früheren Lauf (`daten/technik/kriterien_lauf1.csv`), nach Kosten

| Variante | Abschnitt | Rendite p.a. vorher | jetzt | Sharpe vorher | jetzt | max. DD vorher | jetzt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| crossover | gesamt | 1,19% | 0,85% | 0,11 | 0,06 | -22,29% | -26,08% |
| crossover | Hälfte 1 | -0,77% | -1,92% | -0,07 | -0,21 | -22,29% | -26,08% |
| crossover | Hälfte 2 | 3,19% | 3,69% | 0,31 | 0,34 | -18,29% | -22,40% |
| momentum | gesamt | 1,65% | 1,98% | 0,14 | 0,17 | -21,09% | -20,64% |
| momentum | Hälfte 1 | 1,02% | 1,02% | 0,12 | 0,12 | -21,09% | -20,64% |
| momentum | Hälfte 2 | 2,28% | 2,94% | 0,16 | 0,23 | -15,23% | -20,16% |
| price_channel | gesamt | -4,56% | -5,27% | -0,88 | -0,93 | -44,54% | -50,71% |
| price_channel | Hälfte 1 | -4,09% | -4,66% | -0,71 | -0,79 | -25,95% | -30,39% |
| price_channel | Hälfte 2 | -5,02% | -5,88% | -1,04 | -1,06 | -30,70% | -34,43% |
| rsi2 | gesamt | -7,37% | -7,36% | -2,74 | -2,28 | -60,04% | -60,87% |
| rsi2 | Hälfte 1 | -12,93% | -13,97% | -3,31 | -3,15 | -56,40% | -59,71% |
| rsi2 | Hälfte 2 | -1,44% | -0,24% | -2,50 | -0,64 | -8,35% | -5,37% |
| regime | gesamt | 0,03% | -1,55% | -0,04 | -0,22 | -21,75% | -38,80% |
| regime | Hälfte 1 | -0,28% | -2,44% | -0,00 | -0,23 | -20,18% | -27,48% |
| regime | Hälfte 2 | 0,35% | -0,65% | -0,09 | -0,21 | -21,25% | -27,49% |

Ablage der Läufe: `daten\backtests\20261102T195940_technik_crossover`, `daten\backtests\20261102T200044_technik_momentum`, `daten\backtests\20261102T200140_technik_price_channel`, `daten\backtests\20261102T200233_technik_rsi2`, `daten\backtests\20261102T200345_technik_regime`, `daten\backtests\20261102T200434_technik_buy_and_hold`