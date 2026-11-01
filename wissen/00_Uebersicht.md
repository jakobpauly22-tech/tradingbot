# Grundlagenwissen Trading-Bot: Übersicht

Verdichtetes Wissen aus allen Vorlesungsfolien, Skripten und Papern im Ordner `Wissen`, aufbereitet als Wissensbasis für den Trading-Bot. Stand: 31.10.2026.

## Zweck und Nutzung

- **Für Claude und Claude Code:** Die Dateien sind die fachliche Grundlage für alle Engines. Die CLAUDE.md des Repositorys verweist auf diesen Ordner; vor dem Bau eines Moduls wird die passende Datei gelesen.
- **Für dich:** Nachschlagewerk mit den wichtigsten Formeln, Modellen und Belegen, jeweils mit Bezug zum Bot.
- **Regel:** Formeln im Code nennen die Quelle (Datei und Abschnitt). Übungsaufgaben mit Musterlösung werden zu automatischen Tests.

## Dateien

| Datei | Inhalt | Wichtig für |
| --- | --- | --- |
| [01 Bewertung und Corporate Finance](01_Bewertung_und_Corporate_Finance.md) | Barwert, NPV, Zinsstruktur, CAPM, Markteffizienz, Multiples, Kapitalstruktur, WACC/APV/FTE, Realoptionen, M&A, VaR, Unternehmensbewertung (IDW S 1) | Fundamental-Engine, Risk-Manager |
| [02 Kapitalmarkttheorie, Portfolio und Anleihen](02_Kapitalmarkttheorie_Portfolio_Anleihen.md) | Markowitz, Tobin, CAPM, APT, Fama-French, DDM, Anleihen, Spot- und Forward-Rates, Duration, Konvexität, Credit Spreads, CDS | Portfolio-Konstruktion, Anleiheteil |
| [03 Derivate](03_Derivate.md) | Forwards, Futures, Hedging, Optionen, Wertgrenzen, Put-Call-Parität, Binomialmodell, Black-Scholes, amerikanische Optionen | Signale, spätere Absicherung |
| [04 Finanzielles Risikomanagement](04_Finanzielles_Risikomanagement.md) | VaR-Modelle, ES, Stressed VaR, RAPM, Zins-, Währungs-, Rohstoff-, Options-, Kredit- und Liquiditätsrisiko, EaR/CFaR | Risk-Manager |
| [05 Asset Management und Hedgefonds](05_Asset_Management_und_Hedgefonds.md) | Fondsindustrie, Hedgefonds-Strategien, Faktormodelle, Merger Arbitrage, CTA-Trendfolge (TFF), Red Flags, Pairs Trading | Technik-Engine, Strategie-Bibliothek, Smart Money |
| [06 Behavioral Finance](06_Behavioral_Finance.md) | Entscheidungstheorie, Heuristiken, Prospect Theory, Anlegerfehler, Grenzen der Arbitrage, Anomalien | Begründung der Signale, Journal |
| [07 Banken und Finanzintermediation](07_Banken_und_Finanzintermediation.md) | Bankbilanzen, Kreditvergabe, Kreditrationierung, Verbriefung, Bank Runs | Makro- und Stresssignale |
| [08 Rechnungslegung und Kostenrechnung](08_Rechnungslegung_und_Kostenrechnung.md) | Buchführung, HGB-Bewertung, Rückstellungen, Kosten- und Erlösrechnung, Deckungsbeitrag, Kennzahlen | Bilanzqualität in der Fundamental-Engine |
| [09 Ökonometrie](09_Oekonometrie.md) | OLS, Annahmen, Validität, funktionale Form, Interaktionen, Paneldaten, Performancemessung, CAPM-Test, Ereignisstudien | Backtests, Faktorregressionen, News-Engine |
| [10 Mikroökonomik](10_Mikrooekonomik.md) | Nachfrage, Elastizitäten, Nutzen, Kosten, Wettbewerb, Monopol, Oligopol, Spieltheorie, Externalitäten | Branchenanalyse, News-Einordnung |
| [11 Testkatalog aus den Übungen](11_Testkatalog_Uebungen.md) | 641 automatische Tests aus Musterlösungen (Anleihen, Barwert, Portfolio, CAPM, Bewertung, Kapitalstruktur, Futures, Optionen, Kosten- und Erlösrechnung); Referenzformeln im Ordner `Tests` | Qualitätssicherung aller Engines |

## Quellenzuordnung (alle Dateien im Ordner `Wissen`)

| Ordner / Datei | Eingepflegt in |
| --- | --- |
| Accounting/BACC_SoSe_2026 | 08 |
| Accounting/OACC Teil I, II, III | 08 |
| Corparate Finance/001-part bis 006-part (Teil-Einführungen Welch) | 01 |
| Corparate Finance/02-npv bis 13-npvadvice | 01 (Kap. 7–8 und 10 auch 02) |
| Corparate Finance/14-financials, 15-comps | 01, 08 |
| Corparate Finance/16-corpclaims bis 21-proforma | 01 |
| Folien/1. bis 10. FRM | 04 |
| Folien/1_ bis 6_MoneyBanking | 07 |
| Folien/BF1 | 06 |
| Folien/Barberis&Thaler, Bloomfield 2006, Sewell 2008 | 06 |
| Folien/BFIN Vorlesungsskript Hackethal | 02 (Einführung auch 06) |
| Folien/BFIN_Vorlesungsskript_Maurer | 02 (Zinsrisiko, Kreditrisiko), 03 (Futures, Hedging, Optionen) |
| Folien/BFIN_Exkurs_CDS | 02 |
| Folien/Finanzen_III_(PFIN) | 01 (Abschnitte 14–18) |
| Folien/Goethe Uni UBIT (Unternehmensbewertung) | 01 (Abschnitt 13) |
| Folien/Part_0 bis Part_5 (Viebig, Hedge Funds) | 05 |
| Folien/slides_derivatives_1 Teile 01–05 | 03 |
| Folien/Vorlesungsfolien OFIN | 02 (Optionen auch 03, Agency und Effizienz 02 und 06) |
| Mikro1_Slides_2026 | 10 |
| Ökonometrie/01, 02, 03 boef slides | 09 |
| Ökonometrie/BOEF Teil 2 (Updates 1–124, Vorab-Version für 125–145) | 09 |
| Übungen/ (13 Dateien; 8 Aufgabenblätter mit Lösung, davon Accounting 1 über die separate Datei Accounting_1_WiSe_2026_27_Lösung) | 11, Rechenkonventionen in 08 |

## Vorgehen bei der Erstellung

- Text aus allen 75 PDFs extrahiert, Wasserzeichen und doppelte Folienaufbauten entfernt.
- Vorlesungsfolien: Gliederung und Folieninhalte gelesen, folienspezifische Zahlen und Beispiele übernommen (z.B. TFF-Konstruktion, Red Flags, Merger-Arbitrage-Befunde, VaR-Beispiele).
- Lehrbuchkapitel (Welch): Zusammenfassungen am Kapitelende und Kapitelstruktur ausgewertet.
- Fachartikel (Barberis/Thaler, Sewell, Bloomfield): Kernaussagen und Struktur.
- Die PDFs bleiben die Originalquelle. Für Detailfragen liest Claude gezielt im Original nach.

## Wichtigste Formeln auf einen Blick

| Thema | Formel | Datei |
| --- | --- | --- |
| Kapitalwert | NPV = Σ Cₜ/(1 + r)ᵗ | 01 |
| Gordon-Modell | P₀ = D₁/(r − g) | 01, 02 |
| CAPM | E[rᵢ] = r_f + βᵢ(E[r_M] − r_f) | 01, 02 |
| Beta | βᵢ = Cov(rᵢ, r_M)/Var(r_M) | 01, 02 |
| Portfoliovarianz | σ²_P = w′Σw | 02, 09 |
| Minimum-Varianz-Portfolio | w = Σ⁻¹1/(1′Σ⁻¹1) | 09 |
| WACC | E/V·r_E + D/V·r_D·(1 − τ) | 01 |
| Modifizierte Duration | ΔP/P ≈ −D_mod·Δy + ½·C·(Δy)² | 02 |
| Forwardpreis | F₀ = S₀·e^{(r − y)T} | 03 |
| Black-Scholes | C = S·N(d₁) − K·e^{−rT}·N(d₂) | 03 |
| Parametrischer VaR | VaR = z_α·σ·V, T-Tage: ·√T | 01, 04 |
| Expected Shortfall (normal) | ES = μ + σ·φ(z_α)/(1 − α) | 01 |
| Sharpe / Treynor / Jensen | (r_p − r_f)/σ_p; (r_p − r_f)/β_p; α aus Regression | 04, 09 |
| Hedge Ratio | h* = ρ·σ_S/σ_F | 03, 04 |
| Erwarteter Kreditverlust | EL = PD·LGD·EAD | 04 |
| Trendsignal (TFF) | long, wenn Pₜ ≥ SMA_m(P) | 05 |
| Risk-Parity-Skalierung | Gewicht ∝ Zielvola / σ̂_EWMA (λ = 0,994) | 05 |
| Halbwertszeit Spread | HL = −ln 2/ln(1 + γ) | 05 |
| Dispositionseffekt | DE = PGR − PLR | 06 |
| OLS | β̂ = (X′X)⁻¹X′y | 09 |
| Abnormale Rendite | AR = r − (α̂ + β̂·r_M); CAR = Σ AR | 09 |
| Break-even-Menge | x* = K_f/(p − k_v) | 08 |
| Lerner-Index | (P − MC)/P = −1/E_P | 10 |

## Erweiterung

Neue Folien in den passenden Unterordner von `Wissen` legen und Claude bitten, sie einzupflegen. Neue Inhalte werden in die passende Datei ergänzt oder als neue Datei mit fortlaufender Nummer angelegt; diese Übersicht wird dann aktualisiert.
