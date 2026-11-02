# Technik-Engine: Entscheidungen und Entscheidungsbaum

Parameter: `config/technik.yaml`; Berichte: `docs/berichte/`; Code: `src/tradingbot/engines/technik/`.

## Erster gewerteter Lauf (02.11.2026)

Alle fünf Varianten verfehlt (Bericht `docs/berichte/2026-11-02_technik_satellite.md`). Die TradingView-Gegenprobe des
Crossovers auf SXR8 ist bestanden (`daten/technik/tradingview_crossover_SXR8.csv`). Dabei zeigte sich das
Stückpreis-Problem: SXR8 liegt ab Februar 2020 über der ganzen Positionsgröße (25 % von 1.250 € = 312,50 €) und ist
ohne Bruchstücke nicht kaufbar; die fünf Läufe sind davon betroffen.

## Entscheidungen (Jakob, 02.11.2026)

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

## Ersatz-ETF wegen Stückpreis (Jakob, 02.11.2026)

- **Regel:** Jeder ETF muss über den gesamten Zeitraum mit mindestens einem Stück kaufbar sein (Anteilspreis ≤
  Positionsgröße 312,50 €). Eine zusätzliche Drittel-Grenze für Aktien-ETFs entfällt, weil sie nichts ändert und nur
  einen weiteren Parameter einführt. Damit fällt nur SXR8 heraus (ab 19.02.2020 über 312,50 €).
- **Ersatz:** iShares Core S&P 500 (Dist), IUSA.DE – der nächste der Rangfolge der Auswahlregel.
- **Begründung der Rückschau:** Die Kaufbarkeit wird mit Kursen des ganzen Zeitraums geprüft. Das ist hier
  unbedenklich, weil der Ersatz denselben Index abbildet und nicht nach Rendite ausgewählt wird.
- **Ausschüttungen:** IUSA schüttet aus; Dividenden werden als Zahlung in die Kasse gebucht und versteuert
  (Aktienfonds, Teilfreistellung 30 %), nicht nur über den Kursverlauf.
- **Plausibilität:** IUSA inklusive Dividenden gegen SXR8, 03.01.2013–31.12.2019, Abweichung höchstens 0,3 Prozentpunkte
  p.a.; Ergebnis im Bericht.
- **Investitionsgrad je ETF:** Der Bericht weist je ETF aus, welcher Anteil des Zielwerts einer neuen Position nach der
  Rundung auf ganze Stücke tatsächlich gekauft wurde (vor allem IBCI, EUNH, EUN5).

Maßstab im Entscheidungsbaum: Buy & Hold aller ETFs der Liste, gleich gewichtet, quartalsweise, kostenfrei (Entscheidung
02.11.2026). „Ohne Kosten“ heißt für die Strategien: keine Gebühren, kein Spread, keine Slippage, kein Währungstausch;
ganze Stücke bleiben (strukturelle Eigenschaft des Handels über die API).

## Ergebnis der Neuberechnung (02.11.2026): Zweig a)

Bericht `docs/berichte/2026-11-02_2004_technik_satellite.md`, von Jakob geprüft und bestätigt. Ohne Kosten erreichen weder
Crossover noch Momentum den Sharpe von Buy & Hold in beiden Hälften. Die Technik-Engine ist kein Renditebaustein; echtes
Geld bleibt im Core, Crossover und Momentum laufen im Paper Trading als Schatten vorwärts mit. Ohne Kosten senken beide den
maximalen Drawdown deutlich (Crossover −12,4 %, Momentum −18,8 % gegen −17,1 % bei Buy & Hold über den ganzen Zeitraum);
sie bleiben als mögliche Risikosignale für den Gesamt-Score erhalten.

Für künftige Läufe (Jakob, 02.11.2026): Buy & Hold mit Bruchstücken und voll investiert (strengere Messlatte). Der Lauf
2026-11-02_2004 rechnete Buy & Hold kostenfrei, aber mit ganzen Stücken; kein Neulauf, weil der Sharpe-Vergleich davon kaum
abhängt. Kosten werden im Bericht nach Gebühr, Spread und Slippage sowie Währungstausch aufgeschlüsselt.
