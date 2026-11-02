# 05 Asset Management und Hedgefonds

Grundlagenwissen für Strategie-Bibliothek, Technik-Engine und Smart-Money-Engine. Quelle: Prof. Dr. Jan Viebig, *Hedge Funds: Dynamic Trading Strategies and Strategy-Specific Risks* (Goethe-Uni, WiSe 2026/27), Parts 0 bis 5.

## 1. Asset-Management-Industrie (Part 1)

- Globales verwaltetes Vermögen Ende 2025 rekordhoch bei rund 134 Billionen €.
- Ursprung: Prudent Man Rule und erste Investmentfonds. In den USA vier Fondstypen: offene Fonds (Mutual Funds), ETFs, geschlossene Fonds (Closed-end), Unit Investment Trusts.
- **ETF:** börsengehandelter Fonds; Creation/Redemption über autorisierte Teilnehmer hält den Kurs nahe am Nettoinventarwert (Beispiel iShares Core S&P 500 UCITS).
- **Passiv vs. aktiv:** Passiv bildet die Benchmark günstig nach, aktiv will sie schlagen. Starker Trend zu passiv: In den USA flossen seit 2016 rund 2,9 Billionen $ in Indexfonds und ETFs und 3,4 Billionen $ aus aktiven Aktienfonds ab.
- **Hedgefonds-Industrie:** stark gewachsen seit 1990, heute von institutionellen Investoren dominiert; Klassifizierung nach Strategien (HFR).
- **Liquid Alternatives** (UCITS-Fonds mit Hedgefonds-Strategien, tägliche Liquidität, Regulierung) vs. klassische Hedgefonds (Private Placement, Offshore, Lock-ups).

## 2. Hedgefonds: Definition und Strategien (Part 2)

- **Alfred Winslow Jones (1949):** Long/Short Equity, Vater des Hedgefonds.
- **Typische Merkmale:** Hebel, Leerverkäufe, hohe Erfolgsgebühren, Co-Investment des Managers, Prime Broker (Finanzierung, Wertpapierleihe, Verwahrung). Hebel vergrößert Gewinne und Verluste auf das Eigenkapital.
- Berühmte Manager: Soros, Paulson, Robertson, Druckenmiller, Tudor Jones, Shaw, Dalio und andere.

**HFR-Klassifikation (Auswahl):**

| Hauptgruppe | Teilstrategien |
| --- | --- |
| Equity Hedge | Equity Market Neutral, Fundamental Growth, Fundamental Value, Quantitative Directional, Short Bias, Sektoren |
| Macro | Active Trading, Commodity, Currency, Discretionary Thematic, Systematic Diversified (CTAs) |
| Event Driven | Activist, Credit Arbitrage, Distressed/Restructuring, Merger Arbitrage, Special Situations |
| Relative Value | Fixed Income (Asset Backed, Convertible Arbitrage, Corporate, Sovereign), Volatility, Yield Alternatives |

- **Quant Quake (August 2007):** viele quantitative marktneutrale Fonds verloren gleichzeitig, als überfüllte (crowded) Long/Short-Positionen aufgelöst wurden.
- **Systematic Diversified (Winton, David Harding):** Algorithmen folgen Trends in über 100 Futuresmärkten; 2008 Gewinne während des Aktiencrashs („Crisis Alpha“).
- **Datenprobleme:** kurze Historie (HFRI ab 1990), nur Monatsdaten, fette Ränder. MSCI World 1970–2025: arithmetisch 10,7 % p.a., ebenfalls fette Ränder.
- **Verzerrungen in Hedgefonds-Datenbanken:** Backfill/Instant-History-Bias ca. 1,2 bis 5 % p.a. (Fonds melden erst nach guter Phase und mit ganzer Historie), Survivorship Bias ca. 2 bis 4,4 % p.a. (aufgelöste Fonds fehlen), Selection Bias (nur meldewillige Fonds).

## 3. Faktormodelle, Beta und Marktneutralität (Part 3.1)

- **Markowitz:** Optimierung per Lagrange-Ansatz, Lösung in Matrixform; Python-Beispiel mit vier Anlageklassen. Es gibt kein einzelnes optimales Portfolio, nur eine Effizienzlinie und Präferenzen.
- **Warnungen bei der Optimierung:** Ergebnisse sind In-Sample, keine Prognose; der Optimierer belohnt vergangene Gewinner (Gold +203 %, MSCI World +239 % in zehn Jahren, Anleihen +12 %); kleine Änderungen der erwarteten Renditen verschieben die Gewichte stark; Korrelationen ändern sich (Aktien und Anleihen fielen 2022 gemeinsam: MSCI World −18,0 %, US-Anleihen −13,0 %).
- **CAPM:** CML mit Sharpe Ratio als Steigung, Herleitung, SML. Beta-Schätzung in der Praxis (Bloomberg BETA).
- **Portfolio-Beta:** holdings-based (aktuelle Gewichte, für Manager) vs. returns-based (Regression der Fondsrenditen, für externe Anleger; Beispiel Templeton Growth vs. MSCI World).
- **„Marktneutral“:** HFR: Nettoexposure höchstens 10 % long oder short. Statistisch: alle Faktor-Betas des gewählten Modells null; ein Fonds kann Markt-Beta null haben und trotzdem Faktorrisiken tragen.
- **Empirie:** Beta erklärt Durchschnittsrenditen schlecht, Book-to-Market gut → Fama-French. Long/Short-Equity-Fonds laden auf Fama-French-Faktoren.
- **BARRA Global Equity Model (GEM):** Mehrfaktor-Risikomodell mit Länder-, Branchen- und Stilfaktoren (Risikoindizes wie Size, Value, Momentum, Volatility); r = Xf + u, Kovarianz V = XFXᵀ + Δ.
- **Lineare Faktormodelle:** einfach und interpretierbar, erfassen aber keine nichtlinearen Hedgefonds-Risiken.

## 4. Asset-Based-Style-Faktoren (Part 3.2)

- **Idee (Fung/Hsieh 2001, 2004; Agarwal/Naik 2004):** Strategie-spezifische Faktoren aus handelbaren Anlagen, z.B. Optionsstrategien, bilden nichtlineare Auszahlungen ab und bleiben dennoch in einem linearen Regressionsmodell.
- Grundannahme: Fonds mit demselben Stil haben ähnliche Risiko- und Renditeprofile.

## 5. Merger Arbitrage (Part 3.3)

- **Mechanik:** Nach Ankündigung Zielaktie kaufen (bei Aktientausch zusätzlich Käuferaktie leerverkaufen); Gewinn ist der **Arbitrage-Spread** zwischen Angebots- und Marktpreis.
- **Mitchell/Pulvino (2001), 4.750 Fusionen 1963–1998:**
  - Etwa 50 bp pro Monat (6,2 % p.a.) über dem risikolosen Zins bei Beta nahe null in normalen und steigenden Märkten.
  - In Märkten mit Verlusten von 4 % oder mehr pro Monat: Beta ≈ 0,5. Die Korrelation steigt genau dann, wenn Diversifikation am meisten gebraucht wird.
  - Auszahlungsprofil ähnelt einem verkauften Index-Put: nichtlineares Risiko. Die Überrendite ist eher Risikoprämie als echtes Alpha.
  - Scheitert ein Deal, weitet sich der Median-Spread von etwa 15 % auf über 30 % am Tag der Absage. Deals werden in Crashs häufiger abgesagt.
  - Transaktionskosten senken die früher sehr hohen Überrenditen deutlich.
- **Fall Riverbed Technology (2014):** Angebote von Elliott (19 $, dann 21 $), Ablehnung, Kursbewegungen über und unter dem Angebotspreis, Positionsausbau durch Eton Park, späteres Interesse zu 25 $.

## 6. CTAs und Trendfolge (Part 3.4 und Part 5)

- **Fung/Hsieh (1997, 2001):** Trendfolger haben **straddle-ähnliche Renditen**: Gewinne in extremen Aktienmarktphasen nach oben und unten. Standard-Anlageklassenfaktoren erklären sie nicht; **Lookback-Straddles** (Option auf die Spanne zwischen Höchst- und Tiefstkurs) erklären einen großen Teil.
- **Futures-Grundlagen (Part 5.1–5.2):** Forward-Kurven (EUR/USD), Contango und Backwardation, Börsen und Kontrakte (DAX-Future, E-mini S&P 500, Euro-Bund, WTI), Margin, Lieferung, Konvergenz, Rollen. Forwardpreis F = S·e^{(r − y)T}, Umrechnung periodisch ↔ stetig, Zinsparität für Währungen.
- **Konstruktion eines Trendfolge-Faktors (TFF):**
  1. **Signal:** Kauf, wenn der aktuelle Kurs Pₜ über dem einfachen gleitenden Durchschnitt (SMA) der letzten m Handelstage liegt, sonst Verkauf; m = 30, 60, 120 oder 240.
  2. **SMA** ist ein Filter, der glättet, aber nicht prognostiziert.
  3. **Risk Parity:** Jede Position wird mit ihrer Volatilität skaliert, geschätzt per EWMA mit λ = 0,994 (Halbwertszeit ≈ 115 Handelstage), Zielvolatilität 10 %. Volatile Kontrakte erhalten kleinere Positionen, jeder Kontrakt trägt gleich viel Risiko bei.
  4. **Kosten:** Rohstoffe 4 bp, Aktienindizes 2 bp, Anleihen 1 bp, Währungen 3 bp je Transaktion.
  5. **16 Faktoren:** 4 Anlageklassen × 4 Lookbacks; 207 Futureskontrakte, Daten ab 1959.
- **Beispiel S&P 500, m = 120, 1982–2026 (179 Quartale):** quadratischer Fit U-förmig („Smile“). In den 14 Quartalen mit S&P < −10 % verdiente der Faktor im Schnitt +8,3 %, in 27 Quartalen mit S&P > +10 % +3,4 %. Konvexes, optionsähnliches Profil.
- **Ergebnis TFF-16:** Trendfolge war in allen vier Anlageklassen historisch sehr profitabel. Ein großer Teil des Risikos der größten CTAs (Winton, BlueTrend, AQR Managed Futures, Transtrend, Campbell) ist systematisch und mit regelbasierten Faktoren nachbildbar. Schrittweise Regression (Aufnahme bei p < 5 %, Entfernung bei p > 10 %, Multikollinearität vermeiden) zeigt je Fonds wenige dominierende Faktoren, meist lange Lookbacks (120, 240 Tage) bei Aktien und Anleihen.

## 7. Equity Hedge: diskretionär und systematisch (Part 4)

- **Stile:** Equity Market Neutral (Faktor- oder Stat-Arb-basiert), Fundamental Growth, Fundamental Value, Quantitative Directional, Short Bias.
- **Fundamentale Bewertung:** MM-Propositionen I und II, Irrelevanz der Dividendenpolitik, analytische Bilanz; DCF in fünf Schritten: FCFF, WACC, Unternehmenswert, Abzug Nettoschulden, Wert je Aktie. Asset-, Equity- und Debt-Beta. FCFE- und FCFF-Methode liefern denselben Eigenkapitalwert. Fallbeispiel Microsoft. Management schafft Wert nur über Rendite auf investiertes Kapital über den Kapitalkosten.
- **Fall Stirling Homex (1971): drei Warnsignale (Red Flags):**
  1. **Operativer Cashflow / Jahresüberschuss:** dauerhaft unter 1 oder negativ heißt, Gewinne beruhen auf Accruals statt Cash (Sloan 1996). Stirling Homex: −3,82 → −5,24.
  2. **Forderungslaufzeit (RCP)** = durchschnittliche Forderungen / Umsatz · 365: von 151 auf 265 Tage; Forderungen +144 % bei Umsatz +63 %; nicht fakturierte Forderungen von 30 % auf 65 %.
  3. **Lagerdauer (DOH)** = durchschnittliche Vorräte / Herstellkosten · 365; operativer Zyklus DOH + RCP von 227 auf 327 Tage. Umsatzrealisierung versteckte Vorräte als Forderungen.
  - Gute Gründe für Leerverkäufe: aggressiv gebuchte Forderungen, überbewertete Vermögenswerte, zu niedrige Risikovorsorge, versteckte Schulden.
- **Fall Enron (2001):** Mark-to-Market-Umsätze, schwache Qualität des operativen Cashflows, überbewertete Assets, versteckte Schulden in Zweckgesellschaften, Geschäfte mit nahestehenden Personen. James Chanos shortete ab November 2000; Analysten lobten Enron noch im Oktober 2001.
- **Pairs Trading (statistische Arbitrage):**
  - **Kointegration:** Zwei Kurse Yₜ, Xₜ sind jeweils I(1), der Spread uₜ = Yₜ − a·Xₜ ist stationär I(0). Hedge Ratio a per OLS (BMW/Mercedes-Benz: a ≈ 1,23). Bild: „die Betrunkene und ihr Hund an der Leine“.
  - **Fehlerkorrekturmodell:** ΔYₜ = θ₁ · uₜ₋₁ + …; θ₁ < 0 und signifikant heißt, die Lücke schließt sich. **Halbwertszeit** aus Δuₜ = γ·uₜ₋₁ + eₜ: HL = −ln 2 / ln(1 + γ).
  - Ökonomische Kräfte hinter Kointegration: Kaufkraftparität, Zinsparität, Cash-and-Carry, Kurs und Dividenden/Gewinne, Unternehmen derselben Branche.
  - **BMW/Mercedes-Benz (Jan. 2015 bis Okt. 2026):** 1 BMW-Aktie ≈ 1,23 Mercedes-Aktien; etwa 0,8 % der Lücke schließen sich pro Tag, Halbwertszeit ≈ 88 Handelstage (rund 4 Monate).
  - **Strategie:** Engle-Granger-Test, Spread berechnen, z-Score bilden; bei z > +2 teures Papier verkaufen und billiges kaufen, bei z < −2 umgekehrt; schließen, wenn der Spread zum Mittelwert zurückkehrt.
  - **BMW/Mercedes-Benz 2021–2025:** vier Trades mit je +5,3 % bis +8,0 % (z. B. Einstieg 29.10.2021 bei z = −2,07: 100 BMW kaufen, 123 Mercedes verkaufen, +924 € bzw. +7,5 %). Haltedauer teils über ein Jahr.

## 8. Technische Indikatoren (eigene Zusammenfassung, Quellen außerhalb der Vorlesung)

Formeln wie in `src/tradingbot/engines/technik/indikatoren.py`; jeder Wert am Tag t nutzt nur Daten bis t.

| Indikator | Formel | Quelle |
| --- | --- | --- |
| SMA(n) | Mittel der letzten n Schlusskurse | – |
| Wilder-Glättung RMA(n) | Start = Mittel der ersten n Werte, dann S_t = S_{t−1} + (x_t − S_{t−1}) / n (EMA mit α = 1/n) | Wilder (1978) |
| True Range | TR = max(H − L, \|H − C_{t−1}\|, \|L − C_{t−1}\|) | Wilder (1978) |
| ATR(n) | RMA(TR, n); steuert Stop (2 × ATR) und Positionsgröße | Wilder (1978) |
| RSI(n) | 100 − 100 / (1 + RS), RS = RMA(Gewinne) / RMA(Verluste) | Wilder (1978) |
| ADX(n) | +DM/−DM aus Hoch/Tief-Differenzen, ±DI = 100 · RMA(±DM)/RMA(TR), DX = 100 · \|+DI − −DI\| / (+DI + −DI), ADX = RMA(DX) | Wilder (1978) |
| Momentum 12−1 | im Monat M: C(Ende M−2) / C(Ende M−13) − 1, der jüngste Monat wird ausgelassen (kurzfristige Umkehr) | Jegadeesh/Titman (1993); Zeitreihen-Variante: Moskowitz/Ooi/Pedersen (2012) |
| Donchian-Kanal | höchstes Hoch / tiefstes Tief der letzten n Tage ohne den heutigen | Donchian; Turtle-Regeln (Faith 2007) |

Positionsgröße nach Risiko (fester Bruchteil): Stück = Risiko · Kapital / (2 · ATR); als Gewicht 0,01 · Kurs / (2 · ATR),
gedeckelt (Satellite: 25 % je ETF, 10 % je Einzelaktie). Bezug zu Abschnitt 6: Trendfolge der CTAs nutzt dieselben
Bausteine (Zeitreihen-Momentum, Ausbrüche, volatilitätsgesteuerte Positionsgröße).

## Bezug zum Trading-Bot

| Konzept | Einsatz im Bot |
| --- | --- |
| TFF-Konstruktion (SMA, m = 30–240) | Technik-Engine: Trendfolge über Anlageklassen hinweg, passt zur Startauswahl (MA-Crossover, Momentum) |
| Risk Parity mit EWMA (λ = 0,994, Ziel-Vola 10 %) | Positionsgrößen im Satellite und Gewichtung der Anlageklassen |
| Straddle-Profil der Trendfolge | Trendfolge als Krisenschutz neben dem Core einplanen |
| Kostensätze je Anlageklasse | Startwerte für Backtest-Kosten (plus Brokergebühren) |
| Optimierungswarnungen | Keine reine Markowitz-Optimierung auf Basis historischer Renditen |
| Faktorregression, returns-based Beta | Prüfen, welche Faktoren die Bot-Rendite erklären |
| Datenbank-Verzerrungen | Backtests nur mit Daten inklusive aufgelöster Titel |
| Red Flags (CFO/NI, RCP, DOH) | Fundamental-Engine: Ausschlussfilter für Bilanzqualität |
| Pairs Trading mit Kointegration | Ideen-Backlog: marktneutrales Modul (braucht Leerverkauf, später) |
| Merger Arbitrage, Crowding | News-Engine und Smart Money: Übernahmen und überfüllte Positionen als Risiko |
| Hedgefonds-Strategien und Manager | Smart-Money-Engine: Einordnung von 13F-Positionen nach Stil |
| Technische Indikatoren (Abschnitt 8) | Technik-Engine: Satellite-Strategien, Stops, Positionsgröße |
