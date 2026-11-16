# Regime-Engine: Backtest des Schattenbuchs auf den Entwicklungsdaten (Korrektur der Simulation: Steuer aus der Kasse (Befund 3))

Stand 16.11.2026 10:04. Festlegungen eingefroren in Commit `d066bf6` (docs/REGIME.md), gerechnet mit Commit `d066bf6`. Gewerteter Zeitraum 01.11.2012 bis 31.12.2024, 10.000 € Schattenkapital, SPYI.DE, nach Kosten und Steuern (eigene Steuergruppe ohne Pauschbetrag). Tresor zu.

**Kein Gesamturteil in diesem Bericht.** Der US-Langtest 1995–2011 zählt mit (Kriterium b); das Urteil fällt erst danach (Jakob 15.11.2026). Nach diesem Lauf werden weder Schwellen noch Signale geändert.

## Kriterien für V1 je Hälfte

| Hälfte | Sharpe V1 | Sharpe Kaufen und Halten | Sharpe Mischung | Aktienanteil V1 = Mischung | max. Drawdown V1 | max. Drawdown KuH | Grenze c (75 %) | a) | b) | c) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 (01.11.2012–30.11.2018) | 0,45 | 0,65 | 0,65 | 90,27% | -33,29% | -24,12% | -18,09% | **nein** | **nein** | **nein** |
| 2 (01.12.2018–31.12.2024) | 0,63 | 0,69 | 0,63 | 69,86% | -17,15% | -34,71% | -26,03% | **nein** | **nein** | ja |

a) Sharpe ≥ Kaufen und Halten; b) Sharpe ≥ statische Mischung mit gleichem Durchschnitts-Aktienanteil; c) maximaler Drawdown mindestens 25 % kleiner als bei Kaufen und Halten.

## Bekannte Verzerrungen und Datenhinweise

- **Kasse zu 0 %** (XEON.DE hat die Datenprüfung nicht bestanden): In den Negativzins-Jahren 2015–2022 ist das in „Risiko aus“-Phasen günstiger als die Realität (Geldmarkt rund −0,4 % p. a.). Das begünstigt V1 gegenüber Kaufen und Halten leicht.
- SPYI.DE: [spanne] am 2012-06-13: Hoch unter Tief
- SPYI.DE: [spanne] am 2012-06-13: Schlusskurs außerhalb von Hoch/Tief
- SPYI.DE wurde bis 2016 dünn gehandelt: Tage mit Eröffnung = Hoch = Tief = Schluss je Jahr 2012: 176, 2013: 147, 2014: 120, 2015: 101, 2016: 86, 2017: 25, 2018: 1, 2019: 1, 2023: 3; 498 Tage ohne Umsatz. Ausführungen zur Eröffnung sind an solchen Tagen nur Näherungen.

## Alle Portfolios je Hälfte (nach Kosten und Steuern)

| Portfolio | Hälfte | Rendite p. a. | Sharpe | max. Drawdown | Trades | Aktienanteil |
| --- | --- | --- | --- | --- | --- | --- |
| V1 | 1 | 7,35% | 0,45 | -33,29% | 6 | 90,27% |
| V1 | 2 | 7,88% | 0,63 | -17,15% | 7 | 69,86% |
| D1 | 1 | 4,23% | 0,27 | -33,29% | 10 | 83,39% |
| D1 | 2 | 8,45% | 0,69 | -17,15% | 7 | 69,86% |
| D2 | 1 | 11,47% | 0,65 | -24,12% | 1 | 100,00% |
| D2 | 2 | 4,89% | 0,32 | -17,77% | 5 | 57,23% |
| D3 | 1 | 8,61% | 0,62 | -15,67% | 6 | 65,67% |
| D3 | 2 | 4,42% | 0,27 | -34,41% | 9 | 62,93% |
| D4 | 1 | 11,47% | 0,65 | -24,12% | 1 | 100,00% |
| D4 | 2 | 3,39% | 0,16 | -34,71% | 4 | 79,39% |
| Kaufen und Halten | 1 | 11,47% | 0,65 | -24,12% | 1 | – |
| Kaufen und Halten | 2 | 12,17% | 0,69 | -34,71% | 0 | – |
| Mischung | 1 | 10,33% | 0,65 | -22,03% | 11 | – |
| Mischung | 2 | 8,03% | 0,63 | -24,71% | 18 | – |

V1 ist die einzige gewertete Variante. D1 (nur Trend), D2 (nur Zinskurve), D3 (nur Kreditaufschlag) und D4 (nur Arbeitsmarkt) sind Diagnosen und zählen als Varianten, werden aber nie gewertet. Der Crossover-Schatten der Technik-Engine hat ein anderes Universum und Kapital (docs/TECHNIK.md) und ist hier nicht neu gerechnet.

## Gesamter Zeitraum (nur zur Einordnung)

| Portfolio | Endwert nach Steuern | Steuern gezahlt | Endwert nach fiktivem Verkauf und Steuern | Kosten | Trades | verworfene Orders |
| --- | --- | --- | --- | --- | --- | --- |
| V1 | 24.412 € | 2.254 € | 23.559 € | 310 € | 13 | 0 |
| D1 | 21.076 € | 1.632 € | 20.337 € | 360 € | 17 | 0 |
| D2 | 25.876 € | 3.595 € | 25.876 € | 177 € | 6 | 0 |
| D3 | 21.498 € | 2.366 € | 21.277 € | 343 € | 15 | 0 |
| D4 | 23.699 € | 3.213 € | 23.662 € | 151 € | 5 | 0 |
| Kaufen und Halten | 38.921 € | 228 € | 33.720 € | 15 € | 1 | 0 |
| Mischung | 29.095 € | 1.131 € | 26.467 € | 61 € | 29 | 2 |

## Zustände von V1

12 Wechsel nach der ersten Bewertung. Bewertungstag → Zustand (Order am nächsten Handelstag):

- 31.10.2012: Risiko an
- 31.08.2015: Risiko aus
- 30.11.2015: Risiko an
- 29.01.2016: Risiko aus
- 29.04.2016: Risiko an
- 31.10.2018: Risiko aus
- 28.02.2019: Risiko an
- 28.02.2020: Risiko aus
- 31.08.2020: Risiko an
- 28.02.2022: Risiko aus
- 31.01.2023: Risiko an
- 31.10.2023: Risiko aus
- 29.12.2023: Risiko an

Monatsenden mit Signal „aus“ (von 147): Trend 31, Zinskurve 31, Kreditaufschlag 50, Arbeitsmarkt 15, V1 roh 28, V1 mit Haltepflicht 29.

Ablage der Läufe: `daten/backtests/20261116T100449_regime_V1`, `daten/backtests/20261116T100450_regime_D1`, `daten/backtests/20261116T100451_regime_D2`, `daten/backtests/20261116T100451_regime_D3`, `daten/backtests/20261116T100452_regime_D4`, `daten/backtests/20261116T100453_regime_mischung`