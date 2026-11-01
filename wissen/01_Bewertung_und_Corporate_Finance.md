# 01 Bewertung und Corporate Finance

Grundlagenwissen für die Fundamental-Engine. Quellen: Ivo Welch, *Corporate Finance* (5. Aufl. 2022), Kapitel 2 bis 21 und Teil-Einführungen (Ordner `Corparate Finance`); Hartmut Paulus, *Unternehmensbewertung im Transaktionskontext* (Goethe-Uni, UBIT WS 2026/27).

## 1. Zeitwert des Geldes und Barwert (Welch Kap. 2–3)

- **Perfekter Markt:** keine Steuern, keine Transaktionskosten, keine Meinungsunterschiede, viele Käufer und Verkäufer. Referenzfall, an dem jede Abweichung gemessen wird.
- **Rendite:** r = (C₁ + Ausschüttung − C₀) / C₀. Renditen werden **nicht gemittelt, sondern verzinst**: (1 + r₀,ₜ) = (1 + r₁)(1 + r₂)…(1 + rₜ).
- 100 Basispunkte = 1 %. Zinsangaben (APR) sind nicht gleich Effektivzins (EAR): EAR = (1 + APR/m)^m − 1.
- **Barwert:** PV = Cₜ / (1 + r)ᵗ, Diskontfaktor 1/(1 + r)ᵗ.
- **Kapitalwert:** NPV = C₀ + C₁/(1+r) + C₂/(1+r)² + … Regel: Projekte mit NPV > 0 annehmen.
- Anleihekurse und Zinsen bewegen sich gegenläufig.
- Im perfekten Markt ist eine Firma den Barwert ihrer Assets wert; Wachstum allein macht sie nicht attraktiver, weil der Preis es bereits enthält. Überraschungsgewinne fallen den Alteigentümern zu.

**Sonderformeln (Kap. 3):**

| Zahlungsstrom | Barwert |
| --- | --- |
| Ewige Rente | PV = C₁ / r |
| Wachsende ewige Rente | PV = C₁ / (r − g), nur für g < r |
| Annuität über T Perioden | PV = C/r · [1 − 1/(1+r)ᵀ] |
| Wachsende Annuität | PV = C₁/(r − g) · [1 − ((1+g)/(1+r))ᵀ] |

- **Gordon-Wachstumsmodell:** P₀ = D₁ / (r − g); umgestellt r = D₁/P₀ + g (Dividendenrendite plus Wachstum). Grundlage für Endwert (Terminal Value) und implizite Kapitalkosten.

## 2. Investitionsrechnung (Kap. 4, 13)

- NPV ist im perfekten Markt die einzig richtige Methode. Investition und Konsum sind trennbar (Fisher-Separation).
- **IRR:** Zins, bei dem NPV = 0. Probleme: mehrere oder keine Lösungen, keine Skalenberücksichtigung, Vorzeichen kehren sich bei Finanzierungsprojekten um. Daumenregel: IRR > Kapitalkosten meist, aber nicht immer, NPV > 0.
- **Typische Fehler (Kap. 13):** versprochene mit erwarteten Cashflows verwechseln; Firmen- statt Projektkapitalkosten nutzen; Interaktionen zwischen Projekten ignorieren; versunkene Kosten berücksichtigen; Realoptionen (Aufschieben, Erweitern, Abbrechen) vergessen; eigene Verzerrungen wie Overconfidence. Diversifikation an sich schafft keinen Wert, wenn Anleger selbst diversifizieren können.
- Denken „an der Marge“: Projekte annehmen, solange Grenznutzen > Grenzkosten.

## 3. Zinsstruktur und Inflation (Kap. 5)

- Renditen können je Laufzeit unterschiedlich sein; die **Zinsstrukturkurve** zeigt annualisierte Renditen nach Laufzeit. Meist steigend; invers oft vor Rezessionen.
- Gründe für steigende Kurve: erwartete höhere künftige Zinsen und/oder **Laufzeitprämie**. Empirisch überwiegt die Prämie.
- **Fisher-Gleichung:** (1 + r_nominal) = (1 + r_real) · (1 + Inflation). Realzinsen können negativ sein.
- Nominale Cashflows mit nominalen Zinsen diskontieren, reale mit realen. Buchverluste sind echte Verluste.
- Inflationsgeschützte Anleihen (TIPS); kurzlaufende Anleihen sind weniger inflationsanfällig. Duration misst den durchschnittlichen Zahlungszeitpunkt.

## 4. Unsicherheit, Ausfall und Risiko (Kap. 6)

- Erwartungswert = wahrscheinlichkeitsgewichtete Summe der Ergebnisse. Risikoneutralität: Indifferenz bei gleicher erwarteter Rendite.
- **Versprochene ≠ erwartete Rendite:** Die Differenz ist vor allem die Ausfallprämie (Default Premium). Ratings (Moody's, S&P): Investment Grade bis BBB-/Baa3, darunter Junk.
- **Zahlungstabelle (Payoff Table):** Zustände mit Wahrscheinlichkeiten und Aufteilung des Projektwerts auf Ansprüche (Fremd- und Eigenkapital).
- Fremdkapital „hebelt“ Eigenkapital; beschränkte Haftung.
- NPV: **erwartete** Cashflows mit **erwarteten** Renditen diskontieren, nie versprochene mit versprochenen. NPV ist robust gegen kleine Zinsfehler bei nahen Cashflows, nicht bei fernen.

## 5. Rendite, Risiko und Diversifikation (Kap. 7–8)

- **Historische Muster:** Risiko (Standardabweichung, Beta) ist recht stabil und prognostizierbar; erwartete Renditen nicht. „Trust your risk estimates more than your expected return estimates.“
- Bargeld < Anleihen < Aktien bei Risiko und durchschnittlicher Rendite. Große Portfolios haben geringeres Risiko als Einzelaktien.
- Arithmetisches Mittel ≥ geometrisches Mittel. Näherung: geometrisch ≈ arithmetisch − σ²/2. Man kann trotz positivem arithmetischem Mittel alles verlieren.
- **Varianz:** Var(r) = Σ pᵢ (rᵢ − E[r])², bei Stichproben durch N − 1 teilen. **Standardabweichung** = √Varianz.
- **Portfolio:** E[r_P] = Σ wᵢ E[rᵢ]; Var(r_P) = Σ Σ wᵢ wⱼ Cov(rᵢ, rⱼ).
- **Marktbeta:** βᵢ = Cov(rᵢ, r_M) / Var(r_M); typisch 0 bis 2,5. Betas lassen sich gewichtet mitteln, Varianzen und Standardabweichungen nicht.
- Nur das Beta misst den Risikobeitrag zu einem gut diversifizierten Portfolio. Effizienzlinie, Tangentialportfolio und Zwei-Fonds-Theorem: Jeder rationale Anleger hält risikolose Anlage plus Tangentialportfolio.

## 6. Kapitalkosten, Benchmarks und CAPM (Kap. 9–10)

- **Opportunitätskosten des Kapitals:** erwartete Rendite einer gleichwertigen Alternative (gleiche Laufzeit, gleiches Risiko).
- Risikofreier Zins passend zur Laufzeit der Cashflows (Duration-Matching).
- **Equity Premium:** schwer zu schätzen; plausible Bandbreite etwa 1 % (geometrisch, langfristig) bis 8 % (arithmetisch, kurzfristig), für langfristige Cashflows oft 2–3 %.
- **CAPM:** E[rᵢ] = r_F + βᵢ · (E[r_M] − r_F). Wertpapiermarktlinie (SML).
- CAPM liefert Laufzeit- und Risikoprämie, keine Ausfallprämie: Ausfallrisiko gehört in den erwarteten Cashflow im Zähler.
- Beta-Schätzung per Regression, mit Shrinkage Richtung 1. Welchs Fazit: „Kompass, nicht GPS“, Schätzungen sind ungenau.
- Weitere Faktoren aus Benchmarks: Size (Small Cap), Value, Momentum, Profitabilität, Investment.

## 7. Unvollkommene Märkte (Kap. 11)

- Transaktionskosten (direkt: Gebühren; indirekt: Spread, Suche, Warten). **Round-Trip-Kosten** beachten.
- Geld-Brief-Spanne (Bid-Ask), Mid-Preis, Payment for Order Flow, Hochfrequenzhändler.
- Illiquide Anlagen verlangen eine **Liquiditätsprämie**. Flight to Quality und Liquiditätsengpässe in Krisen.
- Steuern: Durchschnitts- vs. Grenzsteuersatz; Kursgewinne begünstigt. Rechnungen immer nach Kosten und nach Steuern. Steuern fallen auf nominale, nicht reale Renditen an.
- Kotierte Renditen = Laufzeitprämie + Ausfallprämie + Risikoprämie + Liquiditäts- und Steuerprämien. Imperfektionsprämien sind oft größer als die CAPM-Prämie.

## 8. Markteffizienz und Behavioral Finance (Kap. 12)

- **Effizienz:** Preise verarbeiten alle verfügbaren Informationen. Kurzfristig folgen Aktien näherungsweise einem Random Walk (Martingal).
- **Formen:** schwach (Kursmuster reichen nicht, um den Markt zu schlagen), halbstreng (öffentliche Informationen reichen nicht), streng (auch Insiderwissen reicht nicht).
- Haltungen: True Believer, Firm Believer, Mild Believer, Non-Believer. Die meisten Professoren meinen: Es ist schwer, durch Ineffizienzen reich zu werden.
- **Arbitrage:** echte Arbitrage ist risikolos und ohne negative Zahlungen; Risk(y) Arbitrage ist eine gute Wette mit Verlustrisiko.
- Bei Millionen Anlegern schlagen viele den Markt zufällig, einige sogar viele Jahre in Folge. Survivorship Bias.
- **Event Study:** abnormale Rendite um ein Ereignis (Gewinnmeldung, Dividendenerhöhung, Gerichtsurteil) misst dessen Wertwirkung. Signal-Rausch-Verhältnis beachten.
- Begriffe: Noise Trader, Blase, Short Squeeze, technische Analyse, Momentum-Investing.

## 9. Jahresabschluss, Cashflows und Multiples (Kap. 14–15)

- Vier Pflichtrechnungen: Bilanz, GuV, Eigenkapitalveränderungsrechnung, Kapitalflussrechnung.
- **Gewinn ist kein Cashflow:** Abschreibungen addieren, Investitionen (Capex) abziehen, Veränderung des Working Capitals abziehen; latente Steuern beachten.
- **Free Cash Flow (vereinfacht):** FCF = EBIT·(1 − t) + Abschreibungen − Capex − ΔWorking Capital.
- **Multiples (Comparables):** Annahmen: wertrelevante Kennzahl, gute Vergleichsunternehmen, Proportionalität. KGV (P/E) am verbreitetsten; Forward- besser als Trailing-Gewinne. Höheres Wachstum → höheres KGV.
- KGV-Zerlegung: P = E/r + PVGO (Barwert der Wachstumschancen). PEG = KGV / Wachstum.
- **1/X-Problem:** KGVs nicht einfach mitteln; Median nutzen, negative Gewinne ausschließen, E/P mitteln oder Summen bilden.
- Kennzahlen: Current Ratio, Quick Ratio, Zinsdeckung (Interest Coverage, TIE), Verschuldung (D/E), Umschlagsdauern (DSO, DIO, DPO, Cash Conversion Cycle), ROA, ROE, ROS, Asset Turnover, **DuPont:** ROE = Umsatzrendite × Kapitalumschlag × Leverage; Dividendenrendite, Ausschüttungs- und Thesaurierungsquote, Kurs-Buchwert-Verhältnis.
- NPV und Multiples haben unterschiedliche Fehlerquellen; beide rechnen und abwägen, nicht einfach mitteln. Pairs Trading als Anwendung des Gesetzes des einheitlichen Preises.

## 10. Kapitalstruktur (Kap. 16–19)

- Ansprüche: vorrangiges und nachrangiges Fremdkapital, Wandelanleihen, Vorzugsaktien, Stammaktien, Optionsscheine. Fremdkapital hat Vorrang bei Cashflows; Eigenkapital hat Kontrolle außerhalb von Notlagen.
- **Modigliani-Miller (perfekter Markt):** Finanzierungsmix ändert den Firmenwert nicht; WACC ist konstant. Mehr Fremdkapital macht Eigenkapital riskanter, ohne die Gesamtkapitalkosten zu ändern.
- **WACC (ohne Steuern):** WACC = w_E · E[r_E] + w_D · E[r_D].
- **Mit Steuern (Kap. 18):** WACC = w_E · E[r_E] + w_D · E[r_D] · (1 − τ). **APV** = Wert bei reiner Eigenfinanzierung + Barwert der Steuervorteile. Faustregel: ein dauerhafter zusätzlicher Euro Schulden steigert den Wert um den Grenzsteuersatz τ.
- **Unvollkommenheiten (Kap. 19):** Insolvenzkosten (direkt und indirekt: Unterinvestition, übermäßiges Risiko), Disziplinierung durch Schulden, Gläubigerenteignung, Signalwirkung (Eigenkapitalemission signalisiert Überbewertung), Agency-Konflikte. Diese Effekte gehören in Cashflows und Kapitalkosten, nicht in neue Formeln.
- Klienteleffekte: Hochbesteuerte Anleger halten wachstumsstarke Aktien mit niedriger Dividende.

## 11. Ausschüttungen (Kap. 20)

- Dividenden und Aktienrückkäufe; im perfekten Markt irrelevant (MM).
- Dividenden werden geglättet; Erhöhungen lösen positive Kursreaktionen aus, Sonderdividenden und große Rückkäufe im Schnitt etwa 15 %.
- Dividenden-Gewinn-Verhältnis langfristig um 50 %; Dividendenrendite des Marktes seit 2000 etwa 1,5 bis 2,5 %. Rückkäufe sind heute etwa gleich wichtig wie Dividenden.
- Rückkäufe erhöhen nicht automatisch den Gewinn je Aktie (EPS) im ökonomischen Sinn.

## 12. Pro-forma-Planung (Kap. 21)

- Detaillierter Prognosezeitraum plus Endwert (Terminal Value, meist über Gordon-Formel).
- Positionen umsatzabhängig oder fix prognostizieren; Szenarioanalyse; **Kalibrierung** an beobachtete Marktwerte (implizite Annahmen sichtbar machen).
- Pro formas sind unzuverlässig, aber alternativlos.

## 13. Unternehmensbewertung in der Praxis (UBIT, Paulus)

- **M&A-Prozess:** Vorbereitung, Long List, Teaser, Non-binding Offer, Due Diligence (Financial, Tax, Legal, Commercial), Binding Offer, Signing, Closing. Erfolgsquote von Übernahmen oft gering: viele Transaktionen vernichten Shareholder Value.
- **Kaufpreismechanismen:** Locked Box (Preis auf Basis eines Stichtags vor Signing, Verzinsung bis Closing), Closing Accounts mit Equity Bridge (Cash, Schulden und schuldenähnliche Posten, Working-Capital-Abweichung), Earn-out (Zusatzpreis bei Erreichen von Zielen, z.B. EBITDA).
- **Grundprinzipien:** Zukunftsbezogenheit („für das Gewesene gibt der Kaufmann nichts“, Schmalenbach), **Äquivalenzprinzip** (Risiko-, Laufzeit-, Kaufkraft-, Steuer- und Verfügbarkeitsäquivalenz zwischen Zähler und Nenner), Stichtagsprinzip, Bewertung der wirtschaftlichen Einheit.
- Es gibt keinen einen objektiven Wert: Er hängt von Zweck, Perspektive und Informationsstand ab. **Grenzpreise** von Käufer und Verkäufer bilden den Einigungsbereich. „Price is what you pay, value is what you get.“
- **IDW S 1:** objektivierter Wert (typisierter, atomistischer Anteilseigner, Unternehmen „wie es steht und liegt“) vs. Entscheidungswert (subjektiver Grenzpreis mit Synergien). Weitere Standards: IVS, IPEV, DVFA.
- **Verfahren:** Gesamtbewertung (Ertragswert und DCF; marktorientiert mit Multiples) vs. Einzelbewertung (Substanz- und Liquidationswert). DCF dominiert in Deutschland und international.
- **Enterprise Value vs. Equity Value:** Equity Value = Enterprise Value − Nettofinanzverbindlichkeiten (± schuldenähnliche Posten, Minderheiten, nicht betriebsnotwendiges Vermögen).
- Methodenwahl hängt vom Informationsstand ab: früh Multiples und Brancheninfos, später Businessplan und DCF.
- Marktpreise schwanken um den fundamentalen Wert; Multiples variieren stark über die Zeit (z.B. Software-EV/EBITDA 2000 bis 2025). Gute Kapitalmarktkommunikation verringert die Schwankungsbreite.
- Kürzel: FCF, NOPLAT, MRP (Marktrisikoprämie), WACC, β (verschuldet/unverschuldet), NTM, YTD.

## 14. Kapitalstruktur vertieft (PFIN, Berk/DeMarzo)

Quelle: *Finanzen III (PFIN)*, WiSe 2026/27, Teil I bis III.

- **MM I (ohne Steuern):** V_L = V_U. Begründung über Arbitrage und „homemade leverage“: Anleger können Verschuldung privat nachbilden.
- **MM II:** r_E = r_U + (D/E) · (r_U − r_D). Mehr Fremdkapital erhöht die Eigenkapitalkosten, der WACC bleibt gleich.
- **Betas:** β_U = E/(D+E) · β_E + D/(D+E) · β_D; bei risikolosem Fremdkapital β_E = β_U · (1 + D/E).
- **Trugschlüsse:** Leverage erhöht den erwarteten EPS, aber auch dessen Risiko, nicht den Wert. Eigenkapitalemissionen zum fairen Preis verwässern keinen Wert.
- **Steuern:** Zinsen sind abzugsfähig. Tax Shield je Periode = τ_c · Zinsen. Bei dauerhafter Schuld D: PV(Tax Shield) = τ_c · D, also V_L = V_U + τ_c · D. Bei Ziel-Verschuldungsgrad: WACC = E/V · r_E + D/V · r_D · (1 − τ_c), bzw. r_wacc = r_U − D/V · τ_c · r_D.
- **Persönliche Steuern:** effektiver Steuervorteil τ* = 1 − (1 − τ_c)(1 − τ_e)/(1 − τ_i). Grenzen: Zinsschranke in Deutschland, Wachstum, andere Tax Shields (Abschreibungen, Investitionsprämien, „Wachstumsbooster“ 2025).
- **Trade-off-Theorie:** V_L = V_U + PV(Tax Shield) − PV(Financial-Distress-Kosten) − PV(Agency-Kosten) + PV(Agency-Nutzen). Optimum dort, wo der Grenznutzen zusätzlicher Schulden den Grenzkosten entspricht.
- **Insolvenzkosten:** direkt (Rechts- und Beratungskosten) und indirekt (Kundenverlust, Lieferanten, Mitarbeiter, Notverkäufe). Getragen werden sie ex ante von den Eigentümern über niedrigere Emissionserlöse.
- **Agency-Kosten der Verschuldung:** übermäßiges Risiko und Asset Substitution, Debt Overhang und Unterinvestition, Cashing Out, Leverage-Ratchet-Effekt. Gegenmittel: kurze Laufzeiten, Covenants.
- **Agency-Nutzen:** konzentriertes Eigentum, weniger Verschwendung (Free-Cash-Flow-Problem), Commitment.
- **Asymmetrische Information:** Signalwirkung von Schulden; Eigenkapitalemission als negatives Signal (Lemons-Problem), Kurse fallen bei Ankündigung. **Pecking Order:** Innenfinanzierung vor Fremdkapital vor Eigenkapital.

## 15. Bewertungsmethoden mit Fremdkapital (PFIN Teil II)

| Methode | Cashflows | Diskontsatz | Geeignet bei |
| --- | --- | --- | --- |
| WACC | Free Cash Flow (unverschuldet) | WACC nach Steuern | konstantem Verschuldungsgrad |
| APV | FCF plus separat Tax Shields | r_U für FCF, passender Satz für Tax Shields | wechselnder Verschuldung, festen Tilgungsplänen |
| Flow to Equity (FTE) | FCFE = FCF − (1 − τ_c)·Zinsen + Nettoneuverschuldung | r_E | Sicht der Eigentümer, wechselnder Verschuldung |

- **Projektbezogene Kapitalkosten:** Unlevered Beta aus Vergleichsunternehmen, mit dem Zielverschuldungsgrad des Projekts neu verschulden.
- Weitere Verschuldungspolitiken: konstante Zinsdeckung, vorab festgelegte Schuldenniveaus (Tax Shields mit r_D diskontieren).
- Weitere Finanzierungseffekte: Emissionskosten, Fehlbewertung von Wertpapieren, Financial Distress.

## 16. Realoptionen (PFIN Teil II)

- Entscheidungsbäume: Unsicherheit als Knoten, rückwärts lösen.
- Bewertung über Replikation und risikoneutrale Wahrscheinlichkeiten (Binomialmodell).
- **Option zu warten** wirkt wie ein Call: Warten lohnt bei hoher Unsicherheit, geringen entgangenen Cashflows und niedrigem Zins.
- **Wachstums- und Abbruchoptionen** (Beispiele Tesla, Startup, Filialschließung).
- Faustregeln: Investitionsausgaben möglichst spät, Wachstumsoptionen erhöhen den Wert junger Unternehmen, Ausstiegsoptionen erhöhen die Attraktivität riskanter Projekte.

## 17. M&A, LBO und Squeeze-out (PFIN Teil III)

- Motive: Skalen- und Verbundeffekte, vertikale Integration, Know-how, Marktmacht, Effizienz, Steuern, Diversifikation (meist kein Wertbeitrag), Wachstum der Gewinne je Aktie (Scheinargument).
- Übernahmeangebot: Barangebot oder Aktientausch; Umtauschverhältnis so, dass der Wert für die Zielaktionäre der Prämie entspricht. Beispiel UniCredit und Commerzbank.
- **Merger Arbitrage:** Kauf der Zielaktie nach Ankündigung; Spread spiegelt das Scheiterrisiko.
- Übernahmeabwehr: Poison Pill, Staggered Board, White Knight, Golden Parachute, Rekapitalisierung.
- **Free-Rider-Problem:** Aktionäre profitieren vom Wertzuwachs ohne Verkauf. Lösungen: Toehold, LBO, Squeeze-out.
- **LBO:** Kauf überwiegend mit Fremdkapital, das auf das Zielunternehmen übertragen wird; Steuervorteile.

## 18. Risikomanagement und Versicherung (PFIN Teil III)

- **Value at Risk (VaR):** Verlust, der mit Wahrscheinlichkeit α nicht überschritten wird. **Expected Shortfall (ES):** erwarteter Verlust, falls der VaR überschritten wird. ES ist kohärent und erfasst Extremverluste besser.
- Bei Normalverteilung der Verluste: VaR = μ + σ · z_α; ES = μ + σ · φ(z_α)/(1 − α). Beispiel: σ = 20 Mio., 10 Tage, 99 %: VaR = 20 · 2,326 = 46,5 Mio.
- **Zeitskalierung:** T-Tages-VaR = 1-Tages-VaR · √T (unabhängige, identisch normalverteilte Verluste mit Mittelwert 0).
- **Versicherung:** im perfekten Markt NPV-neutral. Versicherungen gegen nicht diversifizierbare Risiken haben negatives Beta, der faire Preis enthält eine Risikoprämie. Nutzen entsteht nur durch Marktunvollkommenheiten: geringere Distress- und Emissionskosten, Steuerglättung, höhere Verschuldungskapazität, bessere Managementanreize, Risikoeinschätzung durch den Versicherer. Kosten: Verwaltung, Adverse Selection, Moral Hazard.

## Bezug zum Trading-Bot

| Konzept | Einsatz im Bot |
| --- | --- |
| DCF, Gordon, Endwert | Fundamental-Engine: innerer Wert und Margin of Safety |
| Implizite Kapitalkosten (r = D/P + g) | Erwartete Rendite aus Marktpreisen ableiten, statt sie historisch zu schätzen |
| Multiples mit Median und E/P | Peer-Vergleich ohne 1/X-Verzerrung |
| Gewinn vs. Cashflow, Accruals | Qualitätsfilter (Gewinne ohne Cashflow abwerten) |
| CAPM, Beta mit Shrinkage | Kapitalkosten und Marktabhängigkeit im Risk-Manager |
| Arithmetisch vs. geometrisch | Backtest-Kennzahlen immer geometrisch ausweisen |
| Transaktionskosten, Steuern | Paper Trading und Backtest nach Kosten und Steuern |
| Markteffizienz, Survivorship Bias | Skepsis gegenüber Backtest-Gewinnern |
| Event Study | Messung von Earnings- und Dividendeneffekten in der News-Engine |
| Zinsstruktur, Inversion | Regime-Erkennung (Rezessionssignal) |
| Ausfallprämie, Ratings | Anleihe-ETFs und Kreditrisiko im Multi-Asset-Teil |
| VaR und Expected Shortfall, √T-Regel | Risk-Manager: Tages- und Monatsrisiko des Portfolios |
| Signalwirkung von Kapitalmaßnahmen | News-Engine: Kapitalerhöhung eher negativ, Rückkauf und Dividendenerhöhung eher positiv |
| Merger Arbitrage, Übernahmeprämie | News-Engine: Einordnung von Übernahmemeldungen |
| Verschuldung, Trade-off, Distress-Kosten | Fundamental-Engine: Verschuldungsgrad und Zinsdeckung als Risikofilter |
