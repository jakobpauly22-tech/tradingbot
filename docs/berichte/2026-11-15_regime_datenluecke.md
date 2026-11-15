# Regime-Engine: Identitätsprüfung der Betriebsregel für Datenlücken

Stand 15.11.2026, Git 65060e3. Vergleich von `src/tradingbot/engines/regime/signale.py` heute mit dem Festlegungs-Commit b628678.

- Zeitraum: Monatsenden von SPYI.DE 02.01.2012 bis 30.12.2024 (156 Monatsenden), Makrodaten point-in-time (ALFRED), Tresor geschlossen.
- Verläufe (vier Signale, Rohzustand, Zustand mit Haltepflicht) je Variante: V1 identisch, D1 identisch, D2 identisch, D3 identisch, D4 identisch.
- Sahm-Wert: alte Formel und Lückenregel stimmen an 156 Monatsenden überein (Toleranz 1e-12).
- **Ergebnis: identisch.**

Kein Backtest: keine Wertreihen, keine Kennzahlen, kein Eintrag in `daten/regime/varianten.csv`. Das Urteil „V1 nicht bestanden“ bleibt unberührt.
