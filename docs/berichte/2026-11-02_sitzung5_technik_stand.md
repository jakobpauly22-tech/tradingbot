# Sitzung 5 – Technik-Engine: Stand vor den gewerteten Läufen

Die gewerteten Läufe sind **noch nicht gerechnet**. Zwei Punkte sperren sie laut Datenregel und Kriterienregel, bis Jakob
entschieden hat (`tools/backtest_technik.py --nur-pruefen` meldet sie, Exit 2). Gewerteter Zeitraum nach der Regel
„alle ETFs 12 Monate Historie ab 01.01.2012“: **03.01.2013 bis 31.12.2024**, Hälften 03.01.2013–02.01.2019 und
02.01.2019–31.12.2024.

## Umgesetzt

| Teil | Ort |
| --- | --- |
| Entscheidungen, Universum, Parameter, Kriterien | `config/technik.yaml`, Roadmap, CLAUDE.md |
| Fundamental-Veto (Piotroski ≤ 3, Z'' mit zweitem Signal, Altman Z Industrie; Beneish Warnhinweis; ruht bei ETFs) | `config/risiko.yaml` |
| Positionsgrenze ETFs 25 %, Einzelaktien 10 % | `config/technik.yaml`, `config/risiko.yaml`, CLAUDE.md |
| Indikatoren (SMA, Wilder-ATR/RSI/ADX, Momentum 12−1, Donchian) | `src/tradingbot/engines/technik/indikatoren.py`, `wissen/05` Abschnitt 8 |
| Strategien mit 1-%-Risiko-Sizing, Stop 2 × ATR, Zeit-Stops, Regime, `score()` | `src/tradingbot/engines/technik/strategien.py` |
| Datenprüfung, Zeitraum, Hälften | `src/tradingbot/engines/technik/daten.py` |
| Lauf mit Sperren, Kriterien je Hälfte, Variantenzähler, Bericht hier | `tools/backtest_technik.py` |
| Gegenprobe Crossover (Pine Script und Bot-Seite) | `tools/tradingview/`, `tools/gegenprobe_crossover.py` |

Unterwegs gefunden und behoben: ADX setzte in der Anlaufphase DX = 0 statt NaN (verfälschte die Glättung); Test
„dauerhafter Aufwärtstrend ergibt ADX 100“ deckt das jetzt ab.

## ETF-Universum nach der Auswahlregel (Fondsvolumen laut justETF, 03.11.2026)

| Klasse | ETF | Ticker | Volumen Mio. € |
| --- | --- | --- | --- |
| Aktien USA | iShares Core S&P 500 (Acc) | SXR8 | größter |
| Aktien Europa | iShares Core MSCI Europe (Acc) | EUNK | 16.100 |
| Aktien Japan | iShares Core MSCI Japan IMI | EUNN | 7.271 |
| Aktien Pazifik ex Japan | iShares Core MSCI Pacific ex Japan | SXR1 | 3.829 |
| Aktien Schwellenländer | iShares MSCI EM (Acc) | EUNM | 8.909 |
| Anleihen Euro-Staaten | iShares Core € Govt Bond | EUNH | 5.383 |
| Anleihen Euro-Unternehmen | iShares Core € Corp Bond | EUN5 | 9.519 |
| Anleihen Euro inflationsindexiert | iShares € Inflation Linked Govt Bond | IBCI | 1.817 |
| Anleihen US-Staaten | iShares $ Treasury Bond 7-10yr (Acc) | SXRM | 4.625 |
| Anleihen Schwellenländer | iShares J.P. Morgan EM Local Govt Bond | IUSP | 4.612 |
| Gold | Invesco Physical Gold ETC | 8PSG | 25.438 |

Ausgeschieden wegen der Regel: Amundi Core Stoxx Europe 600 (erst 2013), iShares Core MSCI EM IMI (2014), Xtrackers
MSCI EM 1C (2017), iShares Physical Gold (Xetra-Kurse erst ab 2021). Gold ist ein ETC, kein UCITS-ETF (ein Gold-ETF
ist nach UCITS nicht zulässig).

## Offene Entscheidungen (Jakob)

1. **Datenfehler (Sperre).**
   - EUNH, EUN5: je 1–2 Tage im Juni 2012 mit Schluss außerhalb der Tagesspanne, nur im Vorlauf. Vorschlag: freigeben.
   - SXRM (US-Treasury): Yahoo liefert die Xetra-Reihe in USD (Kursniveau gleich der USD-Linie an der SIX),
     54 % der Tage ohne Umsatz, 22 gleiche Schlusskurse in Folge 2017. Optionen: (a) Ersatzquelle desselben Fonds
     an der SIX (CSBGU0.SW, USD, in EUR umgerechnet; 9 kleine Spannen-Befunde); (b) nächster der Klasse, iShares $
     Treasury 1-3yr (IUSU, Xetra, EUR, sauber; aber kurze Laufzeit, verhält sich fast wie Kasse). Vorschlag: (a).
   - 8PSG (Gold): 2013–2014 75 Tagessprünge von ±25–40 %, 06/2022–12/2023 430 Tage eingefroren. Optionen:
     (a) Xetra-Gold (4GLD, 20.485 Mio. €, Xetra seit 2007, sauber) als nächster der Rangfolge; (b) Ersatzquelle
     desselben ETC in London (SGLD.L, USD, 240 Spannen-Befunde). Vorschlag: (a). Hinweis: Xetra-Gold ist ein
     Lieferanspruch; Gewinne sind nach einem Jahr steuerfrei, davor privates Veräußerungsgeschäft (§ 23 EStG,
     persönlicher Steuersatz). Das Steuermodul bildet das noch nicht ab (Satellite-Haltedauer meist unter einem Jahr).
2. **Buy & Hold mit 1.250 € (Sperre).** Bei 11 ETFs ist jede Position 114 € < 125 €; die 1-%-Gebührenregel verwirft
   jeden Kauf, das Buy & Hold bliebe Kasse. Optionen: `kostenfrei` (strengere Messlatte, wie das Kontrollportfolio der
   Fundamental-Engine) oder `ohne_gebuehrenregel` (gleiche Kosten, Käufe unter 125 € erlaubt; dann kostet jede
   Order mindestens 1,25 €, bei quartalsweisem Rebalancing von 11 Positionen grob 4 % p.a.). Vorschlag: `kostenfrei`.
3. **Umsetzungsdetails zur Prüfung** (in `config/technik.yaml` vermerkt):
   - Stop und Zeit-Stop auf den Tagesschluss geprüft, Ausführung zur nächsten Eröffnung (keine liegende Stop-Order).
   - Vergabe nach Stärke außer Momentum: Crossover SMA50/SMA200 − 1, Price Channel Ausbruch in ATR, RSI(2) niedrigster
     zuerst. Im Regime bei mehreren Regeln: Trend vor Ausbruch vor Umkehr.
   - Nach einem Stop: Crossover erst nach neuem Kreuzen von unten, Momentum erst zur nächsten Monatsprüfung.
   - Anlageklassen (5 Aktienregionen, 5 Anleiheklassen, Gold) und „größter“ nach heutigem Volumen (leichter
     Rückschaufehler).
