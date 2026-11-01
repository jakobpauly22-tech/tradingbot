# 03 Derivate

Grundlagenwissen zu Forwards, Futures und Optionen. Quellen: Christian Schlag, *Derivatives 1* (Goethe-Uni 2026/27), Teile I bis V; *Finanzen 2 (BFIN)*, Skript Maurer (Futures und Forwards, Hedging mit Futures, Optionen, Binomialmodell, Black-Scholes); *Finanzen I (OFIN)*, Teil V (Optionen); FRM Kapitel 5 (Optionsrisiken, siehe 04).

## 1. Grundbegriffe

- **Derivat:** Finanzinstrument, dessen Wert von einer Basisgröße abhängt (Aktie, Index, Anleihe, Zins, Wetter, Energiepreis, Kryptowährung). Definiert durch seine zustandsabhängige Auszahlung.
- **Bewertungsidee:** Auszahlung aus handelbaren Basisanlagen nachbilden (Replikation) und das Gesetz des einheitlichen Preises anwenden.
- **Kassamarkt vs. Terminmarkt;** börslich (Futures, standardisiert, Clearing) vs. außerbörslich (OTC, Forwards, Swaps). Einsatz: Absicherung, Spekulation, Arbitrage.

## 2. Forwards und Futures

- **Forward:** verbindliche Vereinbarung, ein Underlying zum Zeitpunkt T zum heute festgelegten Preis F₀(T) zu liefern. Kein Zahlungsfluss bei Abschluss. Long verdient bei S_T > F₀, Short bei S_T < F₀; physische Lieferung oder Cash Settlement.
- **Cost-of-Carry-Preis (ohne Erträge):** F₀ = S₀ · (1 + r)ᵀ, stetig F₀ = S₀ · e^{rT}. Herleitung über Arbitrage: Aktie auf Kredit kaufen (Cash-and-Carry) bzw. Leerverkauf plus Anlage (Reverse Cash-and-Carry).
- **Mit diskreten Dividenden:** F₀ = (S₀ − PV(D)) · e^{rT}. **Mit stetiger Rendite y:** F₀ = S₀ · e^{(r − y)T}.
- **Devisenforward (Zinsparität):** F₀ = S₀ · e^{(r_inland − r_ausland)T}. Beispiel: 1,10 USD/EUR, US-Zins 5 %, EUR-Zins 2 %, 6 Monate → 1,1166.
- **Wert eines laufenden Forwards (Long):** f_t = (F_t − K) · e^{−r(T−t)} bzw. S_t − K · e^{−r(T−t)} ohne Erträge.
- **Futures:** standardisiert, börsengehandelt, tägliche Abrechnung (Marking to Market) über das **Marginsystem** (Initial Margin, Maintenance Margin, Margin Call). Futures- und Forwardpreis sind bei deterministischen Zinsen gleich.
- **Basis** = Kassapreis − Futurespreis; konvergiert gegen null bei Fälligkeit. Aktienindexfutures: F₀ = S₀ · e^{(r − q)T} mit Dividendenrendite q.
- **Leerverkauf:** Wertpapier leihen und verkaufen, später zurückkaufen und zurückgeben; Leihgebühr und Dividendenausgleich.

## 3. Hedging mit Futures (BFIN Maurer)

- **1:1-Short-Hedge:** Kassaposition long, Futures short; verbleibendes **Basisrisiko**, wenn Absicherungsdatum, Underlying oder Fälligkeit nicht übereinstimmen.
- **Varianzminimale Hedge Ratio:** h* = ρ · σ_S / σ_F = Cov(ΔS, ΔF) / Var(ΔF). Anzahl Kontrakte N* = h* · Q_A / Q_F.
- Hedge-Effektivität = ρ² (Anteil der eliminierten Varianz).
- Aktienportfolio mit Indexfutures absichern: N* = β · Portfoliowert / Futureswert.

## 4. Optionen: Grundlagen

- **Call:** Recht, das Underlying bis T zum Basispreis K zu kaufen; **Put:** Recht zu verkaufen. Europäisch (Ausübung nur in T) vs. amerikanisch (jederzeit).
- **Auszahlungen bei Fälligkeit:** Call long max(S_T − K, 0); Put long max(K − S_T, 0); Short-Positionen spiegelbildlich. Gewinn = Auszahlung − Prämie (aufgezinst).
- **Optionswert = innerer Wert + Zeitwert.**
- **Strategien:** Protective Put (Downside-Absicherung), Covered Call, Straddle (Wette auf Volatilität), Spreads; „Veroptionieren“ einer Aktie.

## 5. Modellfreie Wertgrenzen

- Nichtnegativität: C ≥ 0, P ≥ 0. Dominanz: C ≤ S, P ≤ K.
- **Untergrenzen:** C_t ≥ max(S_t − K(1+r)^{−(T−t)}, 0); P_t ≥ max(K(1+r)^{−(T−t)} − S_t, 0).
- **Put-Call-Parität (europäisch):** P_t + S_t = C_t + K · (1 + r)^{−(T−t)}; mit Dividenden S_t durch S_t − PV(D) ersetzen.
- Konvexität im Basispreis: Für K₂ = λK₁ + (1 − λ)K₃ gilt C(K₂) ≤ λC(K₁) + (1 − λ)C(K₃).

## 6. Ein-Perioden-Modelle und risikoneutrale Bewertung (Schlag Teil III)

- Zustände s = 1…S, Basisanlagen mit Auszahlungsmatrix X und Preisvektor p. **Replikation:** X · θ = x_neu lösen, Preis = pᵀθ.
- **Zwei Zustände (Aktie, Bankkonto):** Delta N₁ = (Cᵘ − Cᵈ)/(S₀(u − d)); Preis C₀ = [q · Cᵘ + (1 − q) · Cᵈ] / (1 + r) mit **risikoneutraler Wahrscheinlichkeit** q = ((1 + r) − d)/(u − d).
- Arbitragefreiheit ⇔ d < 1 + r < u ⇔ positive künstliche Wahrscheinlichkeiten existieren (erstes Fundamentaltheorem). Eindeutigkeit ⇔ Markt vollständig.
- Numeraire-Wechsel: Mit der Aktie als Numeraire entsteht ein anderes Wahrscheinlichkeitsmaß (q̃ = q·u/(1 + r)).
- Allgemeines Modell: p* = (X*)ᵀ Q*; Existenz und Eindeutigkeit von Q* prüfen. Beispiel: q₁* = 0,818, q₂* = 0,182.

## 7. Binomialmodell (Schlag Teil IV, BFIN Maurer, OFIN Teil V)

- **Mehrperiodig, rückwärts rechnen:** In jedem Knoten C = [q · C_oben + (1 − q) · C_unten] / (1 + r).
- **T Perioden:** C₀ = (1 + r)^{−T} · Σᵢ (T über i) qⁱ(1 − q)^{T−i} · max(S₀uⁱd^{T−i} − K, 0).
- **Binomiale Call-Formel:** C₀ = S₀ · B(T, q̃; a) − K(1 + r)^{−T} · B(T, q; a); allgemein C₀ = S₀ · Prob_Q̃(S_T ≥ K) − PV(K) · Prob_Q(S_T ≥ K).
- **Replikation über Delta:** Δ = (Cᵘ − Cᵈ)/(Sᵘ − Sᵈ); Call = Δ Aktien + Kredit, Put = −Δ Aktien + Anlage.
- Verfeinerung der Perioden: u = e^{σ√Δt}, d = 1/u (Cox-Ross-Rubinstein) → Grenzfall Black-Scholes.

## 8. Black-Scholes

- **Call:** C = S₀ · N(d₁) − K · e^{−rT} · N(d₂); **Put:** P = K · e^{−rT} · N(−d₂) − S₀ · N(−d₁).
- d₁ = [ln(S₀/K) + (r + σ²/2)T] / (σ√T); d₂ = d₁ − σ√T.
- Annahmen: lognormale Kurse (geometrische Brownsche Bewegung), konstante Volatilität und Zins, kein Arbitrage, kontinuierlicher Handel. Volatilität ist der einzige nicht beobachtbare Input (historisch oder **implizit** aus Marktpreisen).
- **Sensitivitäten (Griechen):** Delta (∂C/∂S = N(d₁) beim Call), Gamma (Krümmung), Vega (Volatilität), Theta (Zeitverfall), Rho (Zins). Optionswert steigt mit S (Call), σ, T (meist) und r (Call).

## 9. Amerikanische Optionen (Schlag Teil V)

- Ausübung lohnt, wenn der Ausübungswert den Fortführungswert übersteigt; im Binomialbaum in jedem Knoten max(Ausübung, Fortführung).
- Beispiel amerikanischer Put (S₀ = 100, K = 110, u = 1,2, d = 0,8, r = 10 %, q = 0,75): vorzeitige Ausübung in den unteren Knoten optimal.
- **Amerikanische Calls ohne Dividende werden nie vorzeitig ausgeübt** (C^A = C^E ≥ S − PV(K) > S − K). Mit Dividende kann Ausübung kurz vor dem Dividendentermin lohnen, wenn D > K[1 − (1 + r)^{−(T−τ)}].
- Puts können auch ohne Dividende vorzeitig ausgeübt werden (Zinsertrag auf K).

## Bezug zum Trading-Bot

| Konzept | Einsatz im Bot |
| --- | --- |
| Cost of Carry, Zinsparität | Plausibilität von Futures- und Devisenkursen, Erwartungen über Währungen |
| Varianzminimaler Hedge, β-Hedge | Spätere Absicherung des Core mit Indexfutures (nach Margin-Konto) |
| Implizite Volatilität, VIX | Regime-Erkennung und Positionsgröße (hohe implizite Vola → kleinere Positionen) |
| Put-Call-Parität, Wertgrenzen | Datenqualitätsprüfung bei Optionsdaten |
| Protective Put, Straddle | Ideen-Backlog für spätere Absicherungsmodule |
| Risikoneutrale Bewertung | Marktimplizite Wahrscheinlichkeiten (z.B. aus Optionspreisen) als Signal |

Hinweis: Optionen und Futures sind nach dem Risikoprofil vorerst nicht handelbar (kein Margin-Konto, Kontraktgrößen zu groß für 500 €). Das Wissen dient Signalen und späteren Modulen.
