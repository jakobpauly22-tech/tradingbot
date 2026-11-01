# 04 Finanzielles Risikomanagement

Grundlagenwissen für den Risk-Manager. Quelle: *Financial Risk Management (FRM)*, Goethe-Uni WiSe 2026/27, Kapitel 1 bis 10 (Intro und Aktienmarktrisiko, Währungsrisiko, Rohstoffrisiko, Zinsrisiko, Optionsrisiken, VaR-Modelle, Kreditrisiko, CDS und ABS, EaR und CFaR, Liquiditätsrisiko). Ergänzend PFIN Teil III (VaR, Expected Shortfall, Versicherung, siehe 01).

## 1. Grundlagen (Kap. 1)

- **Risikoarten:** Marktrisiko (Aktien, Zinsen, Währungen, Rohstoffe), Kreditrisiko, Liquiditätsrisiko, operationelles Risiko; dazu Geschäfts-, Reputations-, Modell- und Rechtsrisiko.
- **Risikomanagement-Kreislauf:** identifizieren, messen, steuern (vermeiden, reduzieren, übertragen, tragen), überwachen und berichten.
- **Three Lines of Defense:** 1. Geschäftsbereich, 2. unabhängiges Risikocontrolling, 3. interne Revision. Verstöße (Allianz Global Investors Structured Alpha) führen zu Strafen; Fallbeispiele SVB (Fehlanreize, Zinsrisiko), Berliner Zahnärzte-Versorgungswerk.
- **Risiko vs. Unsicherheit (Knight 1921):** Risiko = bekannte Wahrscheinlichkeiten; Unsicherheit = unbekannte.
- **Risikomaße:** Portfoliovarianz; **VaR** = maximaler Verlust, der mit gegebener Konfidenz über einen Zeitraum nicht überschritten wird (Quantil); **Expected Shortfall / CVaR** = durchschnittlicher Verlust jenseits des VaR. Regulatorisch: risikogewichtete Aktiva (RWA, Basel III), EZB-Stresstest.
- **Erwarteter vs. unerwarteter Verlust:** Erwartete Verluste werden eingepreist (Risikoprämie, Rückstellungen); Eigenkapital puffert nur unerwartete Verluste.
- **Momente:** Mittelwert, Varianz, **Schiefe** (negative Schiefe = langer linker Rand → höherer VaR), **Kurtosis** (Normalverteilung = 3; > 3 fette Ränder, Tail Risk).

## 2. Aktienmarktrisiko (Kap. 1)

- Markowitz-Varianz in Matrixschreibweise: σ²_P = wᵀΣw.
- **Parametrischer Aktien-VaR:** VaR = z_α · σ_P · V (bei Mittelwert 0); z = 1,65 für 95 %, 2,33 für 99 %.
- **Absicherung mit Indexfutures:** Marktrisiko hängt vom Beta ab. Beispiel: Portfolio 30 Mio. $, β = 0,8; Markt −10 % → erwarteter Verlust 2,4 Mio. $. Short-Futures über 24 Mio. $ (= β · Wert) neutralisiert das Marktrisiko; spezifisches Risiko bleibt.
- **Geometrische Brownsche Bewegung:** dS = μS dt + σS dW; Kurse lognormal (nicht negativ, rechtsschief). Grundlage für **Monte-Carlo-Simulation** künftiger Vermögensverteilungen (Beispiel Scalable Capital, Mittnik).
- **Risikoadjustierte Performancemaße (RAPM):**
  - Sharpe Ratio = (R_P − R_f)/σ_P, Steigung relativ zur CML.
  - Treynor Ratio = (R_P − R_f)/β_P, Steigung relativ zur SML.
  - Jensens Alpha α = R_P − [R_f + β_P(R_M − R_f)].
  - RAROC = risikoadjustierter Ertrag / ökonomisches Kapital. Vergütung nach risikoadjustierter, nicht absoluter Performance.

## 3. VaR-Modelle (Kap. 4 und 6)

- **Definition:** maximaler erwarteter Wertverlust unter normalen Bedingungen über eine Halte- oder Liquidationsperiode bei gegebener Konfidenz. **Stressed VaR:** dieselbe Rechnung mit Daten einer Krisenperiode.
- **Komponenten:** Positionen, Risikofaktoren, Bewertungsmodelle, Verteilungsannahmen.
- **Drei Ansätze:**

| Ansatz | Vorgehen | Stärken | Schwächen |
| --- | --- | --- | --- |
| Historische Simulation | historische Faktoränderungen auf das heutige Portfolio anwenden, Quantil ablesen | keine Verteilungsannahme, fette Ränder enthalten | Vergangenheit muss repräsentativ sein, wenige Extremwerte |
| Monte Carlo | Verteilung annehmen und schätzen (z.B. GARCH-Vola), viele Szenarien ziehen | flexibel, auch für nichtlineare Instrumente | Simulationsfehler, Normalverteilung ignoriert fette Ränder |
| Varianz-Kovarianz (parametrisch) | lineare Sensitivitäten φᵢ, multivariate Normalverteilung: σ²_ΔP = ΣΣ φᵢφⱼσᵢσⱼρᵢⱼ, VaR = z · σ_ΔP | schnell, einfach | Linearität und Normalverteilung oft verletzt |

- **Zerobond-Beispiel (Kap. 4):** vier VaR-Varianten aus derselben Datenbasis (parametrisch über Zinsänderung × Basispunktwert, über Duration, historische Simulation der Kursänderungen, parametrisch über Kursänderungen) liefern unterschiedliche Ergebnisse. Annahmen (Horizont, Konfidenz, Linearisierung, Verteilung) bestimmen das Resultat.
- **Zeithorizont:** √T-Regel nur bei i.i.d.-Renditen; bei Anleihen verringert der „Pull to Par“ das Risiko mit sinkender Restlaufzeit. Regulatorisch 10 Tage; nach der Finanzkrise längere, liquiditätsabhängige Horizonte und Expected Shortfall.
- **Modellrisiken:** Parameterunsicherheit (Volatilitäten, Korrelationen), Verteilungsannahme (Renditen haben fette Ränder und Schiefe), zeitvariable Volatilität (Volatility Clustering), Bewertungsmodelle.
- **Strategien mit kleinem VaR und hohem Tail Risk:** Carry Trades (Niederhoffer-Fonds, Thai-Baht 1997), Verkauf weit aus dem Geld liegender Puts, London Whale. VaR erfasst nicht, wie schlimm es jenseits des Quantils wird.
- **Fazit:** VaR ist unverzichtbar, aber Governance um das Modell ist wichtiger als Modelldetails; Regulierung schuf Anreize, Risiken zu unterschätzen.

## 4. Zinsrisiko (Kap. 4)

- Zwei Formen: Barwertrisiko (Kursänderung) und Ertragsrisiko (Zinsergebnis).
- Zerobondpreis ist konvex in der Rendite; Duration und Konvexität (siehe 02) beschreiben die Reaktion.
- **Basispunktwert (PV01):** Wertänderung bei 1 bp; ΔP ≈ −D_mod · P · Δy.
- **Zinsrisiko im Bankbuch (IRRBB):** 200-bp-Schock-Szenarien, Barwert- und Ertragsperspektive (Nettozinsertrag); stark gestiegene Duration der Bankaktiva; stille Lasten bei Zinsanstieg (SVB).

## 5. Währungsrisiko (Kap. 2)

- **Transaction Exposure:** vertraglich fixierte Fremdwährungszahlungen. Absicherung sehr unterschiedlich nach Quote und Horizont.
- **Translation Exposure:** Umrechnung ausländischer Bilanzen in die Konzernwährung; selten abgesichert.
- **Economic / Operating Exposure:** Wirkung von Wechselkursen auf künftige Cashflows und Wettbewerbsposition (Beispiel BMW Motorräder und Yen). Operatives Hedging: Produktion und Einkauf in der Fremdwährung.
- Weitere: Transferrisiko, politisches Risiko (Aufhebung des Franken-Mindestkurses).
- Theorie: Absicherung schafft im perfekten Markt keinen Wert; Nutzen durch geringere Distress-Kosten, Steuern, Planungssicherheit.
- **Fall Lufthansa 1985:** 500 Mio. $ für Flugzeuge in einem Jahr. Optionen: nicht absichern, 100 % Forward, Call-Option, 50 % Forward. Gewählt 50 % Forward; der Dollar fiel danach stark, der Vorstand geriet unter Druck. Lehre: Absicherungsentscheidungen werden ex post am Ergebnis gemessen, nicht an der Entscheidungsqualität.

## 6. Rohstoffrisiko (Kap. 3)

- Forwards sind lineare Instrumente. Rohstoff-Forward: F₀ = (S₀ + Lagerkosten − Convenience Yield) · e^{rT}. **Contango** (F > S) vs. **Backwardation** (F < S). Covid veränderte die Ölforwardkurve drastisch.
- **Minimum-Varianz-Hedge Ratio:** N* = ρ · σ_S/σ_F, entspricht der Steigung einer Regression von ΔS auf ΔF. **Hedge-Effizienz** = ρ² (eliminierte Varianz).
- **Metallgesellschaft 1993:** langfristige Lieferzusagen mit kurzfristigen Futures (Stack and Roll) abgesichert; Ölpreisverfall und Wechsel in Contango führten zu hohen Nachschusszahlungen (Liquiditätsrisiko). Hedging schafft Risiken, wenn das Grundgeschäft nicht verstanden wird.

## 7. Optionsrisiken (Kap. 5)

- Auszahlungsrisiko bei Fälligkeit vs. Marktpreisrisiko während der Laufzeit.
- Strategien: Bull Spread (mit Calls oder Puts), Long Straddle (Wette auf hohe Volatilität), Short Straddle (auf niedrige), Butterfly (begrenzt das Risiko des Short Straddle).
- **Taylor-Entwicklung:** ΔC ≈ Δ · ΔS + ½ Γ · (ΔS)² + ν · Δσ + Θ · Δt. Die **Griechen** aggregieren Risiken im Risikobericht.
- **Delta-Hedging:** nur lokal wirksam; Gamma-Risiko bei großen Kursbewegungen erfordert Nachjustieren.
- **Fall Lufthansa Treibstoff-Hedge:** Optionsabsicherung mit Wirkung auf die GuV (Bilanzierung nicht abgelaufener Optionen).

## 8. Kreditrisiko (Kap. 7) und CDS/ABS (Kap. 8)

- **Kennzahlen:** PD (Ausfallwahrscheinlichkeit), LGD (Verlustquote), EAD (Forderungshöhe bei Ausfall). **Erwarteter Verlust EL = PD · LGD · EAD.** Unerwarteter Verlust über Portfoliomodelle.
- Basel II/III: Standardansatz oder interne Ratings (IRBA) mit RWA-Formel.
- **Informationsquellen für PD:** Ratings, Bilanzdaten, Marktpreise. Risikoneutrale PD aus Spreads: PD ≈ Spread / (1 − Recovery). Spreads sind stark zyklisch.
- **Externe Ratings (S&P):** Geschäftsrisikoprofil + Finanzrisikoprofil → Ankerrating, dann Modifikatoren und externe Unterstützung. Historische marginale und kumulierte Ausfallraten je Ratingklasse.
- **Interne Ratings:** quantitatives Scoring plus qualitative Faktoren. **Altman Z-Score (1968):** Z = 1,2·X₁ + 1,4·X₂ + 3,3·X₃ + 0,6·X₄ + 1,0·X₅ (X₁ Working Capital/Aktiva, X₂ Gewinnrücklagen/Aktiva, X₃ EBIT/Aktiva, X₄ Marktwert EK/Buchwert FK, X₅ Umsatz/Aktiva); Z < 1,81 Gefahrenzone, > 2,99 sicher. Logistische Regression als Marktstandard; Schufa-Modell 2025.
- **Validierung:** Trennschärfe über CAP-Kurve und **Gini-Koeffizient** (Accuracy Ratio).
- **Portfoliomodelle:** Verlustverteilung über ein Jahr; CreditMetrics nutzt Aktienkorrelationen und Ratingmigration.
- **CDS:** Versicherung gegen Ausfall einer Referenzadresse; Kontrahentenrisiko des Verkäufers, Absicherung durch Sicherheiten und zentrale Gegenparteien.
- **ABS und Verbriefung:** True Sale an Zweckgesellschaft, Pass-Through-Strukturen, **Tranchierung** mit Wasserfall (Equity, Junior/Mezzanine, Senior AAA). Junior-Tranchen landeten oft in CDOs; Lehre der Finanzkrise.

## 9. Earnings at Risk und Cashflow at Risk (Kap. 9)

- Drei Risikoparadigmen: Wertrisiko (VaR), Cashflowrisiko (CFaR), Ertragsrisiko (EaR). CEOs und Analysten mögen stabile Gewinne; Gewinnüberraschungen werden bestraft.
- Bilanzierung bestimmt das Ertragsrisiko (Fair Value vs. fortgeführte Kosten, Hedge Accounting).
- **Beispiel „Mr. Rich“:** null CFaR, aber großer VaR. Festzinsanleihe (hohes Wertrisiko, sichere Cashflows) vs. variabel verzinste Anleihe (geringes Wertrisiko, unsichere Cashflows).
- Zentralbanken: Bewertung von Goldbeständen (Bundesbank vs. SNB). Fehlgeschlagene Zinsabsicherung (Bauer) mit Zinsswaps.

## 10. Liquiditätsrisiko (Kap. 10)

- **Funding Liquidity** (Refinanzierung) vs. **Market Liquidity** (Positionen ohne großen Preisabschlag verkaufen).
- Fälle: Northern Rock (Bank Run), Lehman (Repo-Finanzierung), IKB, AIG (Sicherheitenanforderungen), britische Pensionsfonds 2022 (LDI-Margin-Calls), Metallgesellschaft, Dollar-Refinanzierung europäischer Banken.
- **Basel III:** Liquidity Coverage Ratio (kurzfristig, 30-Tage-Stress) und Net Stable Funding Ratio (verfügbare / erforderliche stabile Refinanzierung ≥ 100 %).

## Bezug zum Trading-Bot

| Konzept | Einsatz im Bot |
| --- | --- |
| VaR und ES (historisch, parametrisch, Monte Carlo) | Risk-Manager: tägliche Kennzahlen, ES als Hauptmaß wegen fetter Ränder |
| Stressed VaR, Stresstests | Szenarien 2008, 2020, 2022 auf das aktuelle Portfolio anwenden |
| Schiefe und Kurtosis | Strategien mit negativer Schiefe (Carry, Short Vol, Mean Reversion) besonders begrenzen |
| Zeitvariable Volatilität, GARCH | Positionsgröße an aktuelle statt historische Volatilität koppeln |
| Sharpe, Treynor, Jensens Alpha | Standardbericht im Journal und Wochenreport |
| β-Hedge mit Indexfutures | Späteres Modul zur Absicherung des Core |
| Hedge Ratio und Effizienz (ρ²) | Prüfen, ob ein ETF eine Anlageklasse gut abbildet |
| Altman Z-Score, PD, Spreads | Fundamental-Engine: Insolvenzfilter; Spreads als Stresssignal |
| Liquiditätsrisiko | Nur liquide Wertpapiere, Ordergröße nach Handelsvolumen |
| Ex-post-Bewertung (Lufthansa) | Journal bewertet Entscheidungsqualität, nicht nur Ergebnis |
