# Phase 2 – Abschluss-Backtest Gesamtdepot (Realbuch mit Risk-Manager)

Stand 03.11.2026 11:05. Zeitraum 04.10.2016 bis 30.12.2024. Start 500 €, danach 98 Einzahlungen à 100 € am ersten Handelstag des Monats (eingezahlt gesamt 10.300 €). Festgeschrieben vor dem Lauf: `docs/PHASE2.md`.

Anteilspreise: SPYI-Split 25:1 am 23.02.2026 rückgängig gemacht (echte Preise 92,70–235,35 €), damit ganze Stücke und Mindestorder real geprüft werden.

## Kriterien

| Nr. | Prüfung | Ergebnis | Wert |
| --- | --- | --- | --- |
| 1 | Regeln eingehalten (Risk-Manager vor jeder Order, keine negative Kasse, kein Short, Bestand = Trades) | **bestanden** | 56 Prüfungen, 56 Käufe, 0 Vetos |
| 2 | TWR vor Steuern höchstens 0,5 Pp. vom kostenfreien ACWI IMI | **verfehlt** | -0,51 Pp. p.a. |
| 3 | TWR nach Steuern und nach Verkauf höchstens 0,2 Pp. vom Zwilling | **bestanden** | 0,01 / 0,01 Pp. p.a. |
| 4 | Core-Notbremse nie ausgelöst (12 Monate > 10 Pp. hinter ACWI IMI) | **bestanden** | 0 Tage im Review |
| 5 | Bericht | **bestanden** | diese Datei |

Gesamt: mindestens ein Kriterium verfehlt – mit Jakob besprechen.

## Kennzahlen (zeitgewichtet; XIRR = geldgewichtet)

| Reihe | Ebene | TWR p.a. | XIRR | Volatilität | Sharpe | max. Drawdown | Endwert |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Realbuch | vor Steuern | 10,64% | 11,54% | 16,77% | 0,59 | -34,16% | 17.112,35 € |
| Realbuch | nach Steuern | 10,64% | 11,54% | 16,77% | 0,59 | -34,16% | 17.112,35 € |
| Realbuch | nach Verkauf und Steuern | 9,83% | 10,17% | 16,93% | 0,54 | -34,16% | 16.101,71 € |
| Zwilling | vor Steuern | 10,63% | 11,54% | 16,77% | 0,59 | -34,17% | 17.111,47 € |
| Zwilling | nach Steuern | 10,63% | 11,54% | 16,77% | 0,59 | -34,17% | 17.111,47 € |
| Zwilling | nach Verkauf und Steuern | 9,82% | 10,17% | 16,93% | 0,54 | -34,17% | 16.100,99 € |
| MSCI ACWI IMI (SPYI, kostenfrei, TR) | Index | 11,15% | – | 17,47% | 0,60 | -34,60% | – |

## Ablauf

- Käufe: 56 (Zwilling 54), im Mittel 1,3 Stück zu 179,25 €.
- Verfallene Limits: 0; Kasse im Mittel zum Zeitpunkt des Verfalls – €, ungenutzt im Mittel – Kalendertage bis zum nächsten Kauf.
- Vetos des Risk-Managers: 0.
- Verworfene Orders gesamt: 0 (Gründe: {}).
- Kassenquote: im Mittel 2,81%, höchstens 100,00% (am 04.10.2016); Investitionsgrad im Mittel 97,19%.
- Kosten: 80,03 € (Zwilling 77,53 €); Steuern gezahlt 0,00 € (Zwilling 0,00 €), Steuer bei fiktivem Verkauf 985,27 €.

Ablage: `daten\backtests\20261103T110557_phase2_gesamtdepot`.

## Entscheidung (Jakob, 03.11.2026)

Phase 2 gilt als abgeschlossen, mit dokumentierter Ausnahme: Kriterium 2 bleibt **verfehlt (−0,51 Pp., Grenze 0,5)**, die
Grenze wird nicht geändert. Begründung und Lehre („Technik am Zwilling, Strategie am Index“) in `docs/PHASE2.md`.

