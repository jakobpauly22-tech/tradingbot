# Gegenprobe mit TradingView (Crossover 50/200)

Entscheidung 02.11.2026: Der Crossover wird an einem ETF im TradingView Strategy Tester nachgerechnet; die Regeln müssen in
beiden Rechnungen ähnliche Ergebnisse liefern (ROADMAP, „Regeln für die Übernahme“, Punkt 5).

1. In TradingView den Pine Editor öffnen, `crossover_gegenprobe.pine` einfügen, „Zum Chart hinzufügen“.
2. Chart: `XETR:SXR8`, Intervall 1 Tag. Eingaben: Start und Ende wie in `config/technik.yaml` (gewerteter Zeitraum).
3. Im Strategy Tester die „Liste der Trades“ exportieren (CSV) und unter `daten/technik/tradingview_crossover_SXR8.csv`
   ablegen.
4. Bot-Seite rechnen: `.venv\Scripts\python tools\gegenprobe_crossover.py SXR8.DE`.
5. Vergleich: gleiche Ein- und Ausstiegstage (±1 Tag wegen unterschiedlicher Kursdaten), gleiche Stückzahlen,
   Endwert innerhalb weniger Prozent. Abweichungen kommen meist von den Kursdaten (Yahoo gegen TradingView,
   Dividenden, Handelstage); sie werden notiert, nicht wegjustiert.

Bewusste Vereinfachung beider Seiten: Gebühr fest 1,25 € je Order (bei Orders unter 2.500 € exakt das IBKR-Minimum),
kein Spread, keine Slippage, keine Steuern. Die Gegenprobe prüft die Regeln, nicht das Kostenmodell.
