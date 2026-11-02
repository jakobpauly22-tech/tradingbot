# Technik-Engine: Entscheidungen und Entscheidungsbaum

Parameter: `config/technik.yaml`; Berichte: `docs/berichte/`; Code: `src/tradingbot/engines/technik/`.

## Erster gewerteter Lauf (02.11.2026)

Alle fünf Varianten verfehlt (Bericht `docs/berichte/2026-11-02_technik_satellite.md`). Die TradingView-Gegenprobe des
Crossovers auf SXR8 ist bestanden (`daten/technik/tradingview_crossover_SXR8.csv`). Dabei zeigte sich das
Stückpreis-Problem: SXR8 liegt ab Februar 2020 über der ganzen Positionsgröße (25 % von 1.250 € = 312,50 €) und ist
ohne Bruchstücke nicht kaufbar; die fünf Läufe sind davon betroffen.

## Entscheidungen (Jakob, 03.11.2026)

1. **RSI(2) und Price Channel sind für den Satellite raus.** Begründung strukturell (Handelsfrequenz bei
   Mindestgebühr), nicht ergebnisgetrieben; vorher als Risiko benannt. Im Satellite bleiben Crossover und Momentum.
2. **Neuberechnung der fünf Varianten als Modellkorrektur** (keine neue Variante; alte und neue Ergebnisse werden
   dokumentiert):
   - Stückpreis-Problem lösen. IBKR bietet Bruchstücke für europäische ETFs nur in den Handelsoberflächen und über
     FIX/CTCI, nicht über die API (IBKR-FAQ „Fractional Share Trading“). Daher Ersatz-ETFs; Liste vor dem Lauf zeigen.
   - SXRM (Xetra-Handel in USD) über die USD-Kasse abbilden.
   - Zusätzlich je Variante: Ergebnis ohne Kosten, Investitionsgrad, Zahl der am Stückpreis oder an der 125-€-Regel
     gescheiterten Orders.
3. **Entscheidungsbaum** (vor dem Neulauf festgeschrieben):
   - **a)** Erreicht **ohne Kosten** weder Crossover noch Momentum den Sharpe von Buy & Hold in beiden Hälften:
     Die Technik-Engine ist kein Renditebaustein. Echtes Geld bleibt im Core; Crossover und Momentum laufen im Paper
     Trading als Schatten vorwärts mit.
   - **b)** Erreicht eine von beiden das ohne Kosten: Mindestkapital des Satellite aus dem Kostenbudget ableiten
     (Kosten höchstens 0,5 % p.a. bei der beobachteten Handelsfrequenz), mit diesem Kapital einmal neu rechnen, als neue
     Variante zählen, gleiche Kriterien (Sharpe ≥ Buy & Hold und max. Drawdown nicht schlechter als −20 %, nach Kosten,
     in beiden Hälften).
4. **Xetra-Gold:** Die zwei Tage im Juni 2017 (Schluss über dem Tageshoch) bleiben unverändert; im Bericht vermerkt.

Maßstab im Entscheidungsbaum: Buy & Hold aller ETFs der Liste, gleich gewichtet, quartalsweise, kostenfrei (Entscheidung
03.11.2026). „Ohne Kosten“ heißt für die Strategien: keine Gebühren, kein Spread, keine Slippage, kein Währungstausch;
ganze Stücke bleiben (strukturelle Eigenschaft des Handels über die API).
