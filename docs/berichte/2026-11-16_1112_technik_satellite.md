# Satellite-Strategien der Technik-Engine – gewertete Backtests (Korrektur der Simulation: Steuer aus der Kasse (Befund 3))

Steuer: `steuern.zahlung: jahresende_aus_kasse` (docs/berichte/2026-11-16_steuer_aus_kasse.md).

Stand 16.11.2026 11:12. Zeitraum 2013-01-02 bis 2024-12-31, Kapital 1,250 € (Schatten), 11 ETFs/ETCs laut `config/technik.yaml`. Getestete Varianten bisher: 5 (diese Neuberechnung zählt nicht als neue Variante).

Buy & Hold: alle ETFs gleich gewichtet, quartalsweise, Umsetzung `kostenfrei`, mit Bruchstücken und voll investiert (Entscheidungen Jakob 02.11.2026).

## Daten

- Universum: IUSA.DE (Aktien USA), EUNK.DE (Aktien Europa), EUNN.DE (Aktien Japan), SXR1.DE (Aktien Pazifik ex Japan), EUNM.DE (Aktien Schwellenländer), EUNH.DE (Anleihen Euro-Staaten), EUN5.DE (Anleihen Euro-Unternehmen), IBCI.DE (Anleihen Euro inflationsindexiert), IUSM.DE (Anleihen US-Staaten), IUSP.DE (Anleihen Schwellenländer), 4GLD.DE (Gold)
- Korrektur: IUSA.DE 2013-02-20: Ausschüttung 0.0508 € ergänzt (Yahoo führt für IUSA 2013 keine Ausschüttungen (Jakob 02.11.2026))
- Korrektur: IUSA.DE 2013-05-29: Ausschüttung 0.0532 € ergänzt (Yahoo führt für IUSA 2013 keine Ausschüttungen (Jakob 02.11.2026))
- Korrektur: IUSA.DE 2013-08-28: Ausschüttung 0.0437 € ergänzt (Yahoo führt für IUSA 2013 keine Ausschüttungen (Jakob 02.11.2026))
- Korrektur: IUSA.DE 2013-11-27: Ausschüttung 0.0429 € ergänzt (Yahoo führt für IUSA 2013 keine Ausschüttungen (Jakob 02.11.2026))
- Korrektur: EUNH.DE 2012-06-11: O/H/T/S [104.39, 104.39, 104.98, 104.39] → 104.980 (Vortagesschluss; Hoch unter Tief, Schluss außerhalb der Spanne)
- Korrektur: EUN5.DE 2012-06-12: O/H/T/S [117.6, 117.63, 117.41, 117.23] → 117.720 (Vortagesschluss; Schluss außerhalb der Spanne)
- Korrektur: EUN5.DE 2012-06-13: O/H/T/S [117.05, 117.05, 117.05, 116.97] → 117.720 (Vortagesschluss; Schluss außerhalb der Spanne)
- **Plausibilität IUSA.DE** (inkl. Dividenden) gegen den ersetzten ETF: 16,32% gegen 16,53% p.a., Differenz -0.206 Pp. (Grenze ±0.3, bestanden); nur Kurs 14,56%. Die Prüfung rechnet vor Steuern (Total-Return-Index, Dividenden reinvestiert, ohne Steuern und Kosten). Im Backtest gehen die Dividenden als Zahlung in die Kasse und werden als Aktienfonds versteuert (Teilfreistellung 30 %).
- Xetra-Gold: Zwei Tage (26. und 29.06.2017) mit Schluss über dem Tageshoch (0,14 % und 0,45 %) unverändert (Entscheidung Jakob 02.11.2026). Steuer konservativ mit Abgeltungsteuer (§ 23 EStG offen im Steuermodul).
- IUSM (Ersatz für SXRM seit 04.11.2026, erster gewerteter Lauf mit IUSM): 13.06.2012 (Eröffnung = Hoch = Tief = 160,23, Schluss 158,98) unverändert übernommen wie Xetra-Gold; Begründung: Tag liegt nur im nicht gewerteten Vorlauf (Wirkung höchstens über SMA200 bis Anfang 2013) (Entscheidung Jakob 2026-11-16).

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
| crossover | nach Kosten | gesamt | 2,57% | 0,28 | -21,56% | 5,14% | 0,59 | -18,41% | **nein** | **nein** |
| crossover | nach Kosten | Hälfte 1 | 0,68% | 0,11 | -21,56% | 3,86% | 0,50 | -15,27% | **nein** | **nein** |
| crossover | nach Kosten | Hälfte 2 | 4,46% | 0,45 | -16,53% | 6,32% | 0,67 | -18,41% | **nein** | ja |
| crossover | ohne Kosten | gesamt | 4,35% | 0,55 | -14,19% | 5,14% | 0,59 | -18,41% | **nein** | ja |
| crossover | ohne Kosten | Hälfte 1 | 1,78% | 0,29 | -14,19% | 3,86% | 0,50 | -15,27% | **nein** | ja |
| crossover | ohne Kosten | Hälfte 2 | 6,91% | 0,79 | -11,76% | 6,32% | 0,67 | -18,41% | ja | ja |
| momentum | nach Kosten | gesamt | 2,88% | 0,28 | -16,82% | 5,14% | 0,59 | -18,41% | **nein** | ja |
| momentum | nach Kosten | Hälfte 1 | 1,46% | 0,18 | -14,30% | 3,86% | 0,50 | -15,27% | **nein** | ja |
| momentum | nach Kosten | Hälfte 2 | 4,19% | 0,37 | -16,82% | 6,32% | 0,67 | -18,41% | **nein** | ja |
| momentum | ohne Kosten | gesamt | 4,65% | 0,47 | -13,98% | 5,14% | 0,59 | -18,41% | **nein** | ja |
| momentum | ohne Kosten | Hälfte 1 | 3,16% | 0,36 | -13,62% | 3,86% | 0,50 | -15,27% | **nein** | ja |
| momentum | ohne Kosten | Hälfte 2 | 6,05% | 0,57 | -13,98% | 6,32% | 0,67 | -18,41% | **nein** | ja |
| price_channel | nach Kosten | gesamt | -4,45% | -0,79 | -45,37% | 5,14% | 0,59 | -18,41% | **nein** | **nein** |
| price_channel | nach Kosten | Hälfte 1 | -4,22% | -0,70 | -27,96% | 3,86% | 0,50 | -15,27% | **nein** | **nein** |
| price_channel | nach Kosten | Hälfte 2 | -4,83% | -0,90 | -32,85% | 6,32% | 0,67 | -18,41% | **nein** | **nein** |
| price_channel | ohne Kosten | gesamt | 2,97% | 0,43 | -13,91% | 5,14% | 0,59 | -18,41% | **nein** | ja |
| price_channel | ohne Kosten | Hälfte 1 | 2,31% | 0,46 | -12,66% | 3,86% | 0,50 | -15,27% | **nein** | ja |
| price_channel | ohne Kosten | Hälfte 2 | 3,45% | 0,38 | -13,91% | 6,32% | 0,67 | -18,41% | **nein** | ja |
| rsi2 | nach Kosten | gesamt | -7,38% | -2,66 | -60,14% | 5,14% | 0,59 | -18,41% | **nein** | **nein** |
| rsi2 | nach Kosten | Hälfte 1 | -13,69% | -3,35 | -58,57% | 3,86% | 0,50 | -15,27% | **nein** | **nein** |
| rsi2 | nach Kosten | Hälfte 2 | -0,64% | -2,35 | -3,78% | 6,32% | 0,67 | -18,41% | **nein** | ja |
| rsi2 | ohne Kosten | gesamt | 1,34% | 0,25 | -11,13% | 5,14% | 0,59 | -18,41% | **nein** | ja |
| rsi2 | ohne Kosten | Hälfte 1 | 0,84% | 0,26 | -10,09% | 3,86% | 0,50 | -15,27% | **nein** | ja |
| rsi2 | ohne Kosten | Hälfte 2 | 1,84% | 0,23 | -8,87% | 6,32% | 0,67 | -18,41% | **nein** | ja |
| regime | nach Kosten | gesamt | 0,45% | 0,01 | -27,77% | 5,14% | 0,59 | -18,41% | **nein** | **nein** |
| regime | nach Kosten | Hälfte 1 | -0,56% | -0,03 | -23,40% | 3,86% | 0,50 | -15,27% | **nein** | **nein** |
| regime | nach Kosten | Hälfte 2 | 1,37% | 0,05 | -24,45% | 6,32% | 0,67 | -18,41% | **nein** | **nein** |
| regime | ohne Kosten | gesamt | 4,83% | 0,53 | -16,41% | 5,14% | 0,59 | -18,41% | **nein** | ja |
| regime | ohne Kosten | Hälfte 1 | 3,16% | 0,37 | -16,41% | 3,86% | 0,50 | -15,27% | **nein** | ja |
| regime | ohne Kosten | Hälfte 2 | 6,42% | 0,70 | -10,17% | 6,32% | 0,67 | -18,41% | ja | ja |

## Handel, Kosten, Investitionsgrad

| Variante | Trades | Kosten | Investitionsgrad (Mittel) | gescheitert am Stückpreis | gescheitert an der 125-€-Regel | Steuern gezahlt | Rendite nach Verkauf und Steuern |
| --- | --- | --- | --- | --- | --- | --- | --- |
| crossover | 238 | 358 € | 83,13% | 899 | 871 | 48 € | 2,05% |
| momentum | 216 | 334 € | 81,60% | 58 | 29 | 52 € | 2,31% |
| price_channel | 574 | 842 € | 56,14% | 205 | 178 | 0 € | -4,48% |
| rsi2 | 560 | 811 € | 6,64% | 416 | 660 | 0 € | -7,38% |
| regime | 370 | 553 € | 88,41% | 1232 | 401 | 0 € | 0,37% |
| buy_and_hold | 523 | 0 € | 99,82% | 0 | 0 | 125 € | 4,29% |

## Kosten aufgeschlüsselt (nach Kosten, vor Steuern)

| Variante | Trades | Gebühren | Spread und Slippage | Währungstausch | gesamt | je Trade |
| --- | --- | --- | --- | --- | --- | --- |
| crossover | 238 | 298 € | 61 € | 0 € | 358 € | 1.51 € |
| momentum | 216 | 270 € | 64 € | 0 € | 334 € | 1.54 € |
| price_channel | 574 | 718 € | 124 € | 0 € | 842 € | 1.47 € |
| rsi2 | 560 | 700 € | 111 € | 0 € | 811 € | 1.45 € |
| regime | 370 | 462 € | 91 € | 0 € | 553 € | 1.50 € |

Gescheiterte Orders zählen je Tag und ETF; bei stehendem Signal wird ein Kauf täglich erneut versucht.

## Investitionsgrad je ETF (gekaufter Wert / Zielwert neuer Positionen, Rundung auf ganze Stücke)

| ETF | crossover | momentum | price_channel | rsi2 | regime |
| --- | --- | --- | --- | --- | --- |
| IUSA.DE | 95,30% (13) | 95,68% (17) | 93,49% (37) | 96,15% (49) | 95,34% (19) |
| EUNK.DE | 91,19% (11) | 96,32% (13) | 88,54% (34) | 91,86% (37) | 92,18% (13) |
| EUNN.DE | 92,85% (13) | 96,46% (12) | 90,97% (34) | 93,94% (33) | 93,51% (23) |
| SXR1.DE | 80,51% (19) | 82,78% (22) | 77,65% (27) | 87,10% (17) | 84,96% (24) |
| EUNM.DE | 94,95% (11) | 96,49% (5) | 92,77% (34) | 95,94% (34) | 94,43% (23) |
| EUNH.DE | 78,74% (13) | 70,93% (8) | 78,62% (19) | 79,59% (16) | 76,07% (15) |
| EUN5.DE | 77,57% (6) | 78,68% (4) | 78,25% (15) | 81,87% (28) | 82,88% (14) |
| IBCI.DE | 67,72% (10) | 64,82% (6) | 83,03% (16) | 75,32% (19) | 77,08% (15) |
| IUSM.DE | 68,47% (9) | 70,47% (9) | 73,08% (25) | 80,44% (13) | 66,25% (13) |
| IUSP.DE | 96,52% (5) | – | 88,05% (20) | 89,30% (15) | 91,86% (13) |
| 4GLD.DE | 92,53% (11) | 91,91% (14) | 91,52% (27) | 92,29% (19) | 91,10% (15) |

In Klammern: Zahl der Käufe.

## Vergleich mit dem früheren Lauf (`daten/technik/kriterien_alter_steuerweg.csv`), nach Kosten

| Variante | Abschnitt | Rendite p.a. vorher | jetzt | Sharpe vorher | jetzt | max. DD vorher | jetzt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| crossover | gesamt | 3,16% | 2,57% | 0,34 | 0,28 | -20,41% | -21,56% |
| crossover | Hälfte 1 | 0,92% | 0,68% | 0,14 | 0,11 | -20,41% | -21,56% |
| crossover | Hälfte 2 | 5,36% | 4,46% | 0,55 | 0,45 | -16,30% | -16,53% |
| momentum | gesamt | 2,90% | 2,88% | 0,28 | 0,28 | -17,59% | -16,82% |
| momentum | Hälfte 1 | 1,46% | 1,46% | 0,18 | 0,18 | -14,30% | -14,30% |
| momentum | Hälfte 2 | 4,24% | 4,19% | 0,37 | 0,37 | -17,59% | -16,82% |
| price_channel | gesamt | -4,45% | -4,45% | -0,79 | -0,79 | -45,37% | -45,37% |
| price_channel | Hälfte 1 | -4,22% | -4,22% | -0,70 | -0,70 | -27,96% | -27,96% |
| price_channel | Hälfte 2 | -4,83% | -4,83% | -0,90 | -0,90 | -32,85% | -32,85% |
| rsi2 | gesamt | -7,38% | -7,38% | -2,66 | -2,66 | -60,14% | -60,14% |
| rsi2 | Hälfte 1 | -13,69% | -13,69% | -3,35 | -3,35 | -58,57% | -58,57% |
| rsi2 | Hälfte 2 | -0,64% | -0,64% | -2,35 | -2,35 | -3,78% | -3,78% |
| regime | gesamt | 0,45% | 0,45% | 0,01 | 0,01 | -27,77% | -27,77% |
| regime | Hälfte 1 | -0,56% | -0,56% | -0,03 | -0,03 | -23,40% | -23,40% |
| regime | Hälfte 2 | 1,37% | 1,37% | 0,05 | 0,05 | -24,45% | -24,45% |

Korrigiert am 16.11.2026: Die erste Fassung dieser Tabelle stellte die Zeilen „ohne Kosten“ des früheren Laufs neben „nach Kosten“ (fehlender Filter im Werkzeug, behoben); die Rechnung war nicht betroffen.

Ablage der Läufe: `daten\backtests\20261116T111112_technik_crossover`, `daten\backtests\20261116T111139_technik_momentum`, `daten\backtests\20261116T111201_technik_price_channel`, `daten\backtests\20261116T111220_technik_rsi2`, `daten\backtests\20261116T111241_technik_regime`, `daten\backtests\20261116T111254_technik_buy_and_hold`