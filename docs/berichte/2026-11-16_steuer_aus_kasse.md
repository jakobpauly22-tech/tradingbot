# Korrektur der Simulation: Steuer aus der Kasse (Befund 3 der unabhängigen Prüfung)

Festgehalten am 16.11.2026 um 09:27, **vor jeder Änderung am Code und vor jeder Nachrechnung**. Grundlage:
`docs/berichte/2026-11-16_unabhaengige_pruefung.md`, Befund 3. Entscheidungen von Jakob am 16.11.2026.

## Befund

Die Jahressteuer wird bisher erst nach dem Lauf berechnet und nur von der Reihe `wert_nach_steuern` abgezogen
(`src/tradingbot/backtest/simulation.py:503-540`, Stand 662f9f4). Die Kasse im Lauf bleibt unberührt. Ein Buch, das
Gewinne realisiert und voll reinvestiert, ist dadurch zu mehr als 100 % seines Nachsteuerwerts investiert (V1 Anfang
2024 rund 111 %); Schwankung und Drawdown der gewerteten Reihe sind verstärkt.

## Korrekturregel

Die Regel vom 01.11.2026 bleibt: Die Steuer fließt am letzten Handelstag des Jahres als eigener Abfluss ab, **ohne
Zwangsverkauf**. Neu ist nur, dass der Abfluss die Kasse im Lauf trifft:

1. **Abfluss aus der Kasse:** Am letzten Handelstag des Jahres wird die Jahressteuer der Steuergruppe berechnet, den
   Teilportfolios wie bisher nach ihrem positiven steuerpflichtigen Beitrag zugeordnet und aus der EUR-Kasse gezahlt.
2. **Fremdwährungskasse:** Reicht die EUR-Kasse nicht und liegt Fremdwährungskasse vor, wird für die Steuer
   zurückgetauscht, mit Tauschkosten (Auszahlung im Sinn der Regel vom 02.11.2026).
3. **Kasse reicht nicht:** Der Rest ist eine zinslose Steuerschuld. Sie löst nie einen Verkauf aus. Spätere Zuflüsse
   (Verkaufserlöse, Dividenden, Einzahlungen) tilgen sie zuerst.
4. **Käufe bei offener Schuld werden anteilig kleiner:** Verkäufe rechnen gegen den Depotwert ohne Abzug der Schuld,
   Käufe gegen den Depotwert minus Schuld.
5. **Wertreihen:** „Nach Steuern“ = Kasse + Positionen − offene Steuerschuld (die gewertete Reihe). „Vor Steuern“ =
   Wert nach Steuern + festgesetzte Steuern; in der zeitgewichteten Rendite vor Steuern zählen Steuerzahlungen als
   Auszahlung.

Bekannte Vereinfachungen: Die Steuerschuld ist zinslos. Der Abfluss liegt am Jahresende statt beim Steuerbescheid. Der
Pfad „vor Steuern“ ist kein eigener steuerfreier Lauf mehr; er hält wegen der gezahlten Steuer etwas weniger Positionen
als ein Lauf ganz ohne Steuern.

## Zusage

**Die Korrektur wird unabhängig vom Ergebnis übernommen.** Das umfasst ausdrücklich ihre Wirkung auf Zwillinge,
Benchmarks und Vergleichsportfolios (Kaufen und Halten, statische Mischung), auf alle bisherigen Backtests und auf den
Neulauf c3.

- Kriterien, Grenzen, Signale, Parameter und Gewichte bleiben unverändert. Nach der Nachrechnung wird nichts
  nachjustiert.
- Urteile werden nicht geändert, falls sie bestehen bleiben. Kippt ein Kriterium in die eine oder andere Richtung,
  steht das im Bericht und wird mit Jakob besprochen.
- Der bisherige Rechenweg bleibt nur als Vergleichsmodus erhalten (`steuern.zahlung: jahresende_nur_wertreihe`) und
  wird in jedem Bericht markiert; gewertet wird nur noch mit `jahresende_aus_kasse`.

## Nachrechnung (Umfang, festgelegt vor dem Lauf)

Jeweils alter und neuer Steuermodus auf demselben Code- und Datenstand, Entwicklungsdaten bis 31.12.2024, Tresor zu.

| Lauf | Verglichen wird |
| --- | --- |
| Regime (V1, D1–D4, Kaufen und Halten, Mischung) | Kriterien a–c je Hälfte, Sharpe, maximaler Drawdown, Endwerte |
| Phase 2 Gesamtdepot | Kriterien 2 bis 4 und Prüfung 1 |
| Technik (fünf Varianten und Buy & Hold) | Sharpe und maximaler Drawdown je Hälfte |

- **Regime:** Die Nachrechnung wird als Lauf mit dem Anlass „Korrektur der Simulation: Steuer aus der Kasse
  (Befund 3)“ in `daten/regime/varianten.csv` eingetragen, nicht als neue Variante. Der neue Festlegungs-Commit betrifft
  nur die Simulation; Kriterien und Signale bleiben unverändert (`engines/regime/signale.py` wird nicht angefasst).
- **Fundamental A:** keine Nachrechnung vor c3. In c3 (ab 01.12.2026) laufen beide Steuermodi nebeneinander.
- Der Betrieb (Paper Trading) ist nicht betroffen; die Simulation läuft dort nicht.

## Ergebnis

Folgt nach Umsetzung und Nachrechnung.
