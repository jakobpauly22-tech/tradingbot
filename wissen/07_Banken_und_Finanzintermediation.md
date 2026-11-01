# 07 Banken und Finanzintermediation

Grundlagenwissen zu Banken, Kreditvergabe und Finanzstabilität. Quelle: *Money and Banking*, Goethe-Uni, Kapitel 1 bis 6 (Introduction, Balance Sheets and Profit and Loss, Bank Lending 1 und 2, Investment Banking, Bank Funding).

## 1. Finanzsystem und Wachstum (Kap. 1)

- Hocheinkommensländer haben große Finanzsektoren; ein besserer Finanzsektor fördert Wachstum. Ab einer gewissen Größe kann „zu viel Finanzsektor“ schaden.
- Die Schattenseite: Fehlallokation von Kapital und Finanzkrisen schaden Volkswirtschaften stark; Zusammenhang von Finanzsektor und Ungleichheit (Löhne im Finanzsektor).
- **Finanzmärkte vs. Finanzintermediäre:** Intermediäre lösen Informations- und Transaktionsprobleme (Screening, Monitoring, Losgrößen-, Fristen- und Risikotransformation, Liquiditätsversicherung).

## 2. Bankbilanzen und GuV (Kap. 2)

- **Aktiva:** Liquidität (Bargeld, Zentralbankguthaben, Wertpapiere) und Kredite. **Passiva:** Einlagen, Interbanken- und Kapitalmarktfinanzierung, Eigenkapital.
- **Geschäftsmodelle:** Sparkasse (Frankfurter Sparkasse, zinsgetrieben), Neobroker/Bank (Trade Republic, provisionsgetrieben), Universalbank und Vermögensverwalter (UBS).
- **Kennzahlen:** Nettozinsmarge, Provisionsüberschuss, Cost-Income-Ratio, Eigenkapitalrendite (RoE), Eigenkapitalquote, Kredit-Einlagen-Verhältnis.
- Deutscher Bankensektor: niedrige Zinsmargen und Eigenkapitalrenditen über lange Zeit; Profitabilität stieg mit der Zinswende. EZB-Stabilitätsrisiken: Kreditqualität, Gewerbeimmobilien, Zinsrisiko, Cyber.

## 3. Kreditvergabe (Kap. 3–4)

- **Kredit vs. Wertpapier:** bilateral, private Information, Covenants und Nachverhandlung möglich.
- **Kreditverträge:** Laufzeit, Zins (fest/variabel), Sicherheiten, **Covenants** (restriktiv: Ausschüttungs-, Investitions-, Verschuldungsgrenzen; finanziell: Zinsdeckung, Verschuldungsgrad, Mindest-Eigenkapital).
- **Kreditanalyse, die 5 C:** Capacity (Rückzahlungsfähigkeit aus Cashflow), Character (Zahlungsmoral, z.B. Schufa), Capital (Eigenmittel), Collateral (Sicherheiten), Conditions (Konjunktur, Branche).
- Sicherheiten mildern Moral Hazard und dienen als Screening-Instrument (gute Schuldner signalisieren durch Sicherheiten).
- **Kreditpreis:** Zins = Refinanzierungskosten + Betriebskosten + erwarteter Verlust (PD · LGD) + Eigenkapitalkosten für unerwartete Verluste.
- **Kreditrationierung (Stiglitz/Weiss 1981):** Höhere Zinsen ziehen riskantere Schuldner an (Adverse Selection) und verleiten zu riskanteren Projekten. Der Erwartungsertrag der Bank steigt deshalb nur bis zu einem Zins (im Beispiel 29,99 %); darüber wird nicht weiter erhöht, Nachfrage bleibt unbefriedigt. Empirisch: Rationierung trifft intransparente Firmen stärker (Kirschenmann 2016).
- **Relationship Banking:** langfristige, breite Beziehungen erzeugen private Information, glätten Kreditkonditionen über den Zyklus, schaffen aber Lock-in.

## 4. Investment Banking (Kap. 5)

- **Syndizierte Kredite:** Lead Arranger strukturiert, Teilnehmer übernehmen Anteile (Beispiel eBay-Revolver 2011). Vorteile: Risikoteilung, Größe, Reputation; hoher Anteil nicht-bankfinanzierter Institutionen bei Leveraged Loans.
- **Verbriefung (ABS):** Forderungspool an Zweckgesellschaft, Ausgabe von Tranchen. **Attachment- und Detachment-Punkte** bestimmen, ab welchem Poolverlust eine Tranche Verluste trägt; Tranchendicke = Detachment − Attachment. Senior-Tranchen sind sicher, solange Ausfälle nicht stark korrelieren.
- Motive des Originators: Refinanzierung, Eigenkapitalentlastung, Risikotransfer. Grenzen: Informationsasymmetrie, Fehlanreize (Originate to Distribute), Fehlverkauf von Hypotheken (Vergleich Deutsche Bank mit dem US-Justizministerium).

## 5. Bankfinanzierung und Bank Runs (Kap. 6)

- **Einlagenvertrag:** jederzeit fällig, nominal fix, **Sequential Service Constraint** (wer zuerst kommt, wird zuerst bedient).
- **Diamond/Dybvig (1983):** Banken versichern Haushalte gegen Liquiditätsschocks, indem sie illiquide, ertragreiche Projekte mit liquiden Einlagen finanzieren (Beispiel: c₁ = 100/c₂ = 225 vs. c₁ = 110/c₂ = 210 erhöht den Erwartungsnutzen risikoaverser Haushalte).
- **Zwei Gleichgewichte:** ohne Panik (nur Liquiditätsbedürftige heben ab) und Panik (alle heben ab, Bank muss liquidieren). Lösungen: **Einlagensicherung** oder Aussetzen der Auszahlung.
- **Northern Rock 2007:** klassischer Bank Run; heute beschleunigen soziale Medien Runs (SVB 2023).
- **Marktdisziplin:** Gläubiger überwachen und bestrafen riskante Banken; im Krisenfall ziehen vor allem nicht versicherte, gut informierte Einleger ab.
- **Kapitalstruktur von Banken:** MM, Trade-off, Liquiditätsproduktion (Einlagen als nützliches Produkt), Marktdisziplin, staatliches Sicherheitsnetz (verleitet zu hoher Verschuldung).

## Bezug zum Trading-Bot

| Konzept | Einsatz im Bot |
| --- | --- |
| Bankkennzahlen (Zinsmarge, CIR, RoE) | Fundamental-Engine: eigene Bewertungslogik für Banken (Standard-DCF passt nicht) |
| Kreditrationierung, Kreditzyklus | Makro-Kontext: Kreditvergabe und Spreads als Konjunktursignal |
| Bank Runs, Einlagensicherung | Stresssignal (Abflüsse, Spreads, Bankaktien) für die Regime-Erkennung |
| Verbriefung und Tranchen | Verständnis von Anleihe-ETFs und Kreditrisiken im Multi-Asset-Teil |
| Covenants, 5 C | Qualitative Prüfung der Verschuldung in der Fundamental-Engine |
