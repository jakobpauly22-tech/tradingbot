# Phase 2: Abschluss-Backtest Gesamtdepot (Realbuch)

Festgeschrieben vor dem Lauf am 03.11.2026 (Entscheidungen Jakob 03.11.2026). Parameter in `config/backtest.yaml`
(`phase2_gesamtdepot`). Werkzeug: `tools/backtest_phase2.py`. Bericht: `docs/berichte/`.

## Was gerechnet wird

- **Zeitraum:** 01.10.2016 bis 31.12.2024 (gewerteter Zeitraum); Tresor bleibt zu.
- **Realbuch nach den Paper-Regeln:** Start mit 500 €, danach 100 € Einzahlung am ersten Handelstag jedes Monats.
  Alles im Core-ETF SPYI (Satellite-Anteil fließt laut Schattenbetrieb in den Core). Kauf nach den Realbuch-Regeln:
  Limit-Order zum Vortagesschluss + 2 % (auf Cent abgerundet), ganze Stücke, Restkasse bleibt und wird mit dem nächsten
  Betrag angelegt, 1-%-Gebührenregel (Order ab 125 €).
- **Limit-Modell:** Ausführung zur Eröffnung, aber nur, wenn die Eröffnung höchstens das Limit ist; sonst verfällt die
  Order und wird am nächsten Tag neu vorgeschlagen. Ausführungspreis inkl. Spread und Slippage höchstens das Limit.
- **Risk-Manager eingehängt:** Jede Order läuft vor der Ausführung durch `RiskManager.pruefe` mit den Regeln des
  Realbuchs (Kasse je Währung, nur long, 1-%-Regel, Orderwert ≤ Bot-Budget, Orders je Tag ≤ 5, Limit ≤ 2 % über dem
  letzten Kurs). Das Bot-Budget wächst mit den Einzahlungen (Startkapital plus Einzahlungen bis zum Tag; Umsetzung
  Claude, zur Prüfung). Ein Veto wird mit Grund protokolliert, die Order nicht ausgeführt.
- **Kosten und Steuern** wie im Backtest-Framework (IBKR-Gebühr, Spread, Slippage; Abgeltungsteuer mit vollem
  Pauschbetrag, Vorabpauschale).
- **Anteilspreise:** SPYI hatte am 23.02.2026 einen Split 25:1 (SSGA). Yahoo führt die Historie rückwirkend
  bereinigt und den Split nicht als Ereignis. Für ganze Stücke und Mindestorder zählen die echten Anteilspreise:
  Kurse vor dem Split × 25 (`config/daten.yaml`, `kapitalmassnahmen`). Renditen ändern sich dadurch nicht.
- **Vergleich:**
  - MSCI ACWI IMI als kostenfreier Total-Return-Index (SPYI ohne Kosten);
  - Zwilling: Buy & Hold SPYI mit denselben Einzahlungen, denselben Kosten und Steuern, ganzen Stücken und 1-%-Regel,
    aber Market-Order zur Eröffnung und ohne Risk-Manager (zeigt den Effekt von Limit und Risk-Manager).
- **Renditen zeitgewichtet (TWR),** damit Einzahlungszeitpunkte den Vergleich nicht verzerren:
  r_t = (V_t − E_t) / V_{t−1} − 1 mit Einzahlung E_t am Tag t; zusätzlich interner Zinsfuß (XIRR) der Zahlungen.

## Woran „sauber gelaufen“ gemessen wird (Kriterien 1–5)

1. **Regeln eingehalten:** Jede ausgeführte Order hat den Risk-Manager passiert; an keinem Tag negative Kasse in
   einer Währung, Short-Bestand oder Hebel; Bestand = Summe der Trades an jedem Tag. Verletzung → Abbruch.
2. **Nähe zum ACWI IMI vor Steuern:** TWR p.a. höchstens 0,5 Prozentpunkte vom kostenfreien Index entfernt.
3. **Gleichlauf mit dem Zwilling** nach Steuern und nach fiktivem Verkauf am Ende: TWR p.a. höchstens 0,2 Prozentpunkte
   Abweichung.
4. **Core-Notbremse** (12 Monate mehr als 10 Prozentpunkte hinter MSCI ACWI IMI, TWR) wird nie ausgelöst; Tage im
   Review werden ausgewiesen.
5. **Bericht** unter `docs/berichte/`: Kennzahlen, Orders, verfallene Limits (Anzahl und im Mittel ungenutzte Kasse),
   Vetos mit Grund, höchste Kassenquote, Prüfungen 1–4 als bestanden oder verfehlt.

Eine Phase gilt als fertig, wenn ihr Backtest sauber gegen die Benchmark läuft (CLAUDE.md). Dieser Backtest prüft vor
allem die Technik des Realbuchs (Risk-Manager, Limit-Logik, ganze Stücke, Kosten, Steuern); eine Renditeaussage zum Core
ist er nicht, weil der Core der Benchmark ist.
