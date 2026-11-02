# Satellite-Strategien der Technik-Engine – gewertete Backtests

Stand 02.11.2026 18:56. Zeitraum 2013-01-03 bis 2024-12-31, Kapital 1,250 € (Schatten), 11 ETFs/ETCs laut `config/technik.yaml`. Getestete Varianten bisher: 5.

Buy & Hold: alle ETFs gleich gewichtet, quartalsweise (Umsetzung: kostenfrei; Entscheidung Jakob 02.11.2026: kostenfrei als strengere Messlatte, weil 114 € je Position unter der 125-€-Grenze lägen).

## Daten

- **SXRM.DE über Ersatzquelle CSBGU0.SW** (gleicher Fonds, gleiche Anteilsklasse, in EUR umgerechnet): an 1484 Tagen mit Xetra-Umsatz Median-Abweichung 0,06% (Grenze 0,5 %, bestanden), 95-%-Quantil 0,27%. SXRM wird auf Xetra in USD gehandelt; der Backtest rechnet den ETF wie einen EUR-Wert ohne Währungstausch (Vereinfachung, die Tauschkosten wären mit Netto-Tausch gering).
- Korrektur: EUNH.DE 2012-06-11: O/H/T/S [104.39, 104.39, 104.98, 104.39] → 104.980 (Vortagesschluss; Hoch unter Tief, Schluss außerhalb der Spanne)
- Korrektur: EUN5.DE 2012-06-12: O/H/T/S [117.6, 117.63, 117.41, 117.23] → 117.720 (Vortagesschluss; Schluss außerhalb der Spanne)
- Korrektur: EUN5.DE 2012-06-13: O/H/T/S [117.05, 117.05, 117.05, 116.97] → 117.720 (Vortagesschluss; Schluss außerhalb der Spanne)
- Xetra-Gold (4GLD) statt Invesco Physical Gold (fehlerhafte Yahoo-Kurse). Zwei Tage (26. und 29.06.2017) mit Schluss über dem Tageshoch (0,14 % und 0,45 %) unverändert übernommen – offen, bitte bestätigen. Steuer konservativ mit Abgeltungsteuer, ohne Steuerfreiheit nach einem Jahr (§ 23 EStG als offener Punkt im Steuermodul).

## Ergebnis je Variante (Kriterien in beiden Hälften)

| Variante | bestanden |
| --- | --- |
| crossover | nein |
| momentum | nein |
| price_channel | nein |
| rsi2 | nein |
| regime | nein |

## Kennzahlen nach Kosten, vor Steuern

| Variante | Abschnitt | Rendite p.a. | Sharpe | max. Drawdown | B&H Rendite | B&H Sharpe | B&H Drawdown | Sharpe ≥ B&H | DD ≥ −20 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| crossover | gesamt | 1,19% | 0,11 | -22,29% | 5,71% | 0,65 | -19,04% | **nein** | **nein** |
| crossover | Hälfte 1 | -0,77% | -0,07 | -22,29% | 3,89% | 0,53 | -14,90% | **nein** | **nein** |
| crossover | Hälfte 2 | 3,19% | 0,31 | -18,29% | 7,56% | 0,76 | -19,04% | **nein** | ja |
| momentum | gesamt | 1,65% | 0,14 | -21,09% | 5,71% | 0,65 | -19,04% | **nein** | **nein** |
| momentum | Hälfte 1 | 1,02% | 0,12 | -21,09% | 3,89% | 0,53 | -14,90% | **nein** | **nein** |
| momentum | Hälfte 2 | 2,28% | 0,16 | -15,23% | 7,56% | 0,76 | -19,04% | **nein** | ja |
| price_channel | gesamt | -4,56% | -0,88 | -44,54% | 5,71% | 0,65 | -19,04% | **nein** | **nein** |
| price_channel | Hälfte 1 | -4,09% | -0,71 | -25,95% | 3,89% | 0,53 | -14,90% | **nein** | **nein** |
| price_channel | Hälfte 2 | -5,02% | -1,04 | -30,70% | 7,56% | 0,76 | -19,04% | **nein** | **nein** |
| rsi2 | gesamt | -7,37% | -2,74 | -60,04% | 5,71% | 0,65 | -19,04% | **nein** | **nein** |
| rsi2 | Hälfte 1 | -12,93% | -3,31 | -56,40% | 3,89% | 0,53 | -14,90% | **nein** | **nein** |
| rsi2 | Hälfte 2 | -1,44% | -2,50 | -8,35% | 7,56% | 0,76 | -19,04% | **nein** | ja |
| regime | gesamt | 0,03% | -0,04 | -21,75% | 5,71% | 0,65 | -19,04% | **nein** | **nein** |
| regime | Hälfte 1 | -0,28% | -0,00 | -20,18% | 3,89% | 0,53 | -14,90% | **nein** | **nein** |
| regime | Hälfte 2 | 0,35% | -0,09 | -21,25% | 7,56% | 0,76 | -19,04% | **nein** | **nein** |

## Handel und Kosten

| Variante | Trades | verworfene Orders | Kosten | Steuern gezahlt | Rendite nach Verkauf und Steuern |
| --- | --- | --- | --- | --- | --- |
| crossover | 232 | 491 | 347 € | 22 € | 0,89% |
| momentum | 213 | 31 | 324 € | 30 € | 1,30% |
| price_channel | 543 | 96 | 794 € | 0 € | -4,57% |
| rsi2 | 570 | 595 | 822 € | 0 € | -7,37% |
| regime | 373 | 234 | 556 € | 9 € | -0,06% |
| buy_and_hold | 21 | 0 | 0 € | 49 € | 4,81% |

Ablage der Läufe: `daten\backtests\20261102T185454_technik_crossover`, `daten\backtests\20261102T185507_technik_momentum`, `daten\backtests\20261102T185519_technik_price_channel`, `daten\backtests\20261102T185528_technik_rsi2`, `daten\backtests\20261102T185558_technik_regime`, `daten\backtests\20261102T185603_technik_buy_and_hold`
## Diagnose (Claude): kein Rechenfehler, die Kosten bei 1.250 € entscheiden

Ein erster Lauf brach erst beim Schreiben dieses Berichts ab (Programmfehler im Bericht, Simulationen unverändert).
Seine Ordner sind als `…_ABGEBROCHEN_berichtfehler` markiert, seine Zeilen aus `daten/technik/varianten.csv` entfernt
(dieselben fünf Varianten, deterministisch neu gerechnet). Gezählte Varianten der Technik-Engine: 5.

- **Logik geprüft:** RSI(2) auf SXR8 allein, ohne Kosten: 107 Trades, 74 % Gewinner (90 Ausstiege über SMA5, 17 Stops) –
  so, wie man es für RSI(2) über SMA200 erwartet. Crossover auf SXR8 ohne Kosten: 14 Trades, Endwert 1.753 € aus
  1.250 €; 9 von 14 Ausstiegen über den 2-ATR-Stop.
- **Vor Kosten im Plus, nach Kosten nicht:** Realisierte Gewinne nach Kosten plus Kosten ergeben vor Kosten etwa
  Crossover +290 €, Momentum +360 €, Price Channel +210 €, RSI(2) +70 €. Die Kosten (324–822 €) sind bei
  Ordergrößen um 200–270 € je Hin- und Rückweg rund 1,3–1,5 % (2 × 1,25 € Mindestgebühr plus Spread und Slippage).
  Kurzfristige Strategien mit vielen Trades (RSI(2) 570, Price Channel 543 Trades) verlieren dadurch am stärksten.
- **Verworfene Orders** sind fast alle Restkäufe unter 125 € (1-%-Regel), die mangels freier Kasse zu klein ausfallen und
  bei stehendem Signal täglich erneut verworfen werden; kein Fehler, aber Kasse bleibt ungenutzt (Crossover im Mittel
  20 % Kasse, RSI(2) 93 %).
- **Buy & Hold** ist kostenfrei gerechnet (strengere Messlatte); mit Kosten wäre es bei 114 € je Position nicht handelbar.

Gegenprobe Crossover, Bot-Seite (SXR8, 1,25 € je Order, ohne Spread, Slippage und Steuern, ab 03.01.2013):
26 Trades, Endwert 1.547,67 €; Trades in `daten/technik/gegenprobe_crossover_SXR8_DE.csv`. Die TradingView-Seite rechnet
Jakob mit `tools/tradingview/crossover_gegenprobe.pine`.

Nach der Regel: Ergebnis dokumentieren und mit Jakob besprechen; keine Änderung an Parametern ohne Fehler oder
theoretische Begründung. Der Tresor bleibt zu.
