"""Erzeugt testfaelle_uebungen.json aus den Musterlösungen der Übungsblätter und prüft sie gegen referenz.py."""
import json, math, sys
import referenz as R

Q_B1 = "Übungsblatt_Bonds_1_Vorlesung_mit_Lösung"
Q_B2 = "Übungsblatt_Bonds_2_Selbststudium_mit_Lösung"
Q_F1 = "Übungsblatt_FuturesForwards_1_Vorlesung_mit_Lösung"
Q_F2 = "Übungsblatt_FuturesForwards_2_Selbststudium_mit_Lösung"
Q_OP = "Übungsblatt_Optionen_mit_Lösung"
Q_BF = "BFIN Übungssammlung Hackethal_mit Lösungen"
Q_OF = "OFIN Uebung - SoSe26"

KONST = {
    "KURVE_OFIN": {1: 0.025, 2: 0.03, 3: 0.035, 4: 0.04, 5: 0.045, 6: 0.05},
    "KURVE_OFIN_NEG": {1: -0.0008, 2: -0.001, 3: -0.0005, 4: 0.0005, 5: 0.0019, 6: 0.0034, 7: 0.005, 8: 0.0067},
    "PF_BONDS_B1": {1: 26.0, 2: 26.0, 3: 226.0, 4: 110.0},
    "STEP_UP": {1: 40.0, 2: 40.0, 3: 50.0, 4: 1050.0},
    "STEP_UP_HALB": {0.5: 40.0, 1.5: 40.0, 2.5: 50.0, 3.5: 1050.0},
}

C = []  # (id, quelle, aufgabe, thema, wissen, ausdruck, erwartet, toleranz, hinweis)
def add(*a):
    a = list(a) + [""] * (9 - len(a))
    C.append(dict(zip(["id", "quelle", "aufgabe", "thema", "wissen", "ausdruck", "erwartet", "toleranz", "hinweis"], a)))

# ---------------- Bonds 1 (Maurer)
add("B1-2-preis", Q_B1, "2 (i)", "Anleihen", "02 §7", "price_flat(PF_BONDS_B1, 0.06)", 324.5525, 0.0005)
add("B1-2-duration", Q_B1, "2 (ii)", "Duration", "02 §7", "macaulay_duration(PF_BONDS_B1, 0.06)", 3.0463, 0.0005)
add("B1-2-preisaenderung", Q_B1, "2 (iv)", "Duration", "02 §7", "rel_change_duration(PF_BONDS_B1, 0.06, 0.01)", -0.0287, 0.00005)
add("B1-3-konvexitaet", Q_B1, "3 (ii)", "Konvexität", "02 §7", "convexity(bond_cashflows(1000, 0, 4), 0.05)", 18.1406, 0.0005)
add("B1-3-preisaenderung", Q_B1, "3 (iii)", "Konvexität", "02 §7", "rel_change_dur_conv(bond_cashflows(1000, 0, 4), 0.05, -0.015)", 0.0592, 0.00005)
add("B1-4-preis", Q_B1, "4", "Anleihen", "02 §7", "price_flat(STEP_UP, 0.05)", 981.4059, 0.0005)
add("B1-4-duration", Q_B1, "4", "Duration", "02 §7", "macaulay_duration(STEP_UP, 0.05)", 3.7656, 0.0005)
add("B1-4-modduration", Q_B1, "4", "Duration", "02 §7", "modified_duration(STEP_UP, 0.05)", 3.5863, 0.0005)
add("B1-4-abs-aenderung", Q_B1, "4", "Duration", "02 §7", "abs_change_duration(STEP_UP, 0.05, 0.005)", -17.5981, 0.001)
add("B1-5-preis", Q_B1, "5", "Anleihen", "02 §7", "price_flat(STEP_UP_HALB, 0.05)", 1005.6417, 0.0005)
add("B1-5-duration", Q_B1, "5", "Duration", "02 §7", "macaulay_duration(STEP_UP_HALB, 0.05)", 3.2656, 0.0005)
add("B1-6-barwert", Q_B1, "6 (i)", "Immunisierung", "02 §7", "pv(1_000_000, 0.05, 2)", 907029.4785, 0.001)
add("B1-6-nennwert-1j", Q_B1, "6 (ii)", "Immunisierung", "02 §7", "pv(1_000_000, 0.05, 2) * 0.5 * 1.05", 476190.4763, 0.001)
add("B1-6-nennwert-3j", Q_B1, "6 (ii)", "Immunisierung", "02 §7", "pv(1_000_000, 0.05, 2) * 0.5 * 1.05 ** 3", 525000.0001, 0.001)
add("B1-6-schock", Q_B1, "6 (iii)", "Immunisierung", "02 §7", "pv(1_000_000, 0.05, 2) * 0.5 * 1.05 * 1.06 + pv(1_000_000, 0.05, 2) * 0.5 * 1.05 ** 3 / 1.06", 1000044.9239, 0.001, "Wert nach 2 Jahren bei Zinsanstieg um 100 bp")
add("B1-7-gewicht", Q_B1, "7 (i)", "Duration Matching", "02 §7", "duration_match_weight(5, 2.8594, 7)", 0.4830, 0.00005)
add("B1-7-preis-b", Q_B1, "7 (iii)", "Anleihen", "02 §7", "pv(1000, 0.05, 7)", 710.6813, 0.0005)
add("B1-7-stueck-b", Q_B1, "7 (iii)", "Duration Matching", "02 §7", "45000 * round(1 - duration_match_weight(5, 2.8594, 7), 4) / pv(1000, 0.05, 7)", 32.7362, 0.0005, "Musterlösung rundet das Gewicht auf 4 Stellen")

# ---------------- Bonds 2: 20 Anleihen x 8 Kennzahlen
B2 = [  # Nr, Kupon, Laufzeit, Preis, D, Dmod, Dabs, C, rel D, rel D+C, abs exakt
 (1,0,1,95.2381,1.0000,0.9524,90.7029,1.8141,-0.0048,-0.0047,-0.4514),(2,0,2,90.7029,2.0000,1.9048,172.7675,5.4422,-0.0095,-0.0095,-0.8577),
 (3,0,3,86.3838,3.0000,2.8571,246.8107,10.8844,-0.0143,-0.0141,-1.2223),(4,0,4,82.2702,4.0000,3.8095,313.4105,18.1406,-0.0190,-0.0188,-1.5484),
 (5,0,5,78.3526,5.0000,4.7619,373.1077,27.2109,-0.0238,-0.0235,-1.8389),(6,.02,1,97.1429,1.0000,0.9524,92.5170,1.8141,-0.0048,-0.0047,-0.4604),
 (7,.02,2,94.4218,1.9798,1.8855,178.0369,5.3690,-0.0094,-0.0094,-0.8838),(8,.02,3,91.8303,2.9388,2.7988,257.0164,10.5887,-0.0140,-0.0139,-1.2729),
 (9,.02,4,89.3621,3.8761,3.6915,329.8843,17.3945,-0.0185,-0.0182,-1.6300),(10,.02,5,87.0116,4.7913,4.5631,397.0437,25.7054,-0.0228,-0.0225,-1.9573),
 (11,.04,1,99.0476,1.0000,0.9524,94.3311,1.8141,-0.0048,-0.0047,-0.4694),(12,.04,2,98.1406,1.9612,1.8678,183.3063,5.3013,-0.0093,-0.0093,-0.9100),
 (13,.04,3,97.2768,2.8844,2.7470,267.2220,10.3262,-0.0137,-0.0136,-1.3236),(14,.04,4,96.4540,3.7705,3.5909,346.3581,16.7582,-0.0180,-0.0177,-1.7116),
 (15,.04,5,95.6705,4.6203,4.4003,420.9797,24.4724,-0.0220,-0.0217,-2.0756),(16,.06,1,100.9524,1.0000,0.9524,96.1451,1.8141,-0.0048,-0.0047,-0.4784),
 (17,.06,2,101.8594,1.9439,1.8513,188.5757,5.2386,-0.0093,-0.0092,-0.9362),(18,.06,3,102.7232,2.8358,2.7007,277.4276,10.0915,-0.0135,-0.0134,-1.3742),
 (19,.06,4,103.5460,3.6793,3.5041,362.8320,16.2090,-0.0175,-0.0173,-1.7932),(20,.06,5,104.3295,4.4778,4.2645,444.9157,23.4441,-0.0213,-0.0210,-2.1940)]
for nr, k, t, p, d, dm, da, cv, rd, rdc, ab in B2:
    cf = f"bond_cashflows(100, {k}, {t})"
    base = f"B2-{nr:02d}"
    lbl = f"Bond {nr} (Kupon {k:.0%}, {t} J.)"
    add(f"{base}-preis", Q_B2, lbl, "Anleihen", "02 §6", f"price_flat({cf}, 0.05)", p, 0.0001)
    add(f"{base}-duration", Q_B2, lbl, "Duration", "02 §7", f"macaulay_duration({cf}, 0.05)", d, 0.0001)
    add(f"{base}-modduration", Q_B2, lbl, "Duration", "02 §7", f"modified_duration({cf}, 0.05)", dm, 0.0001)
    add(f"{base}-absduration", Q_B2, lbl, "Duration", "02 §7", f"modified_duration({cf}, 0.05) * price_flat({cf}, 0.05)", da, 0.0001)
    add(f"{base}-konvexitaet", Q_B2, lbl, "Konvexität", "02 §7", f"convexity({cf}, 0.05)", cv, 0.0001)
    add(f"{base}-rel-d", Q_B2, lbl, "Duration", "02 §7", f"rel_change_duration({cf}, 0.05, 0.005)", rd, 0.00005)
    add(f"{base}-rel-dc", Q_B2, lbl, "Konvexität", "02 §7", f"rel_change_dur_conv({cf}, 0.05, 0.005)", rdc, 0.00005)
    add(f"{base}-abs-dc", Q_B2, lbl, "Konvexität", "02 §7", f"abs_change_dur_conv({cf}, 0.05, 0.005)", ab, 0.0001,
        "Spalte 'absolute Preisänderung' der Musterlösung nutzt Duration und Konvexität")

# ---------------- Futures & Forwards 1
add("F1-1-forward-t0", Q_F1, "1 a)", "Forwards", "03 §2", "forward_price(40, 0.10, 3)", 53.24, 0.005)
add("F1-1-forward-t1", Q_F1, "1 b)", "Forwards", "03 §2", "forward_price(45, 0.10, 2)", 54.45, 0.005)
add("F1-1-wert-t1", Q_F1, "1 b)", "Forwards", "03 §2", "forward_value_long(45, forward_price(40, 0.10, 3), 0.10, 2)", 1.0, 0.005)
add("F1-2a", Q_F1, "2 a)", "Futures", "03 §2", "forward_price(100, 0.02, 1)", 102.0, 0.0005)
add("F1-2b", Q_F1, "2 b)", "Futures", "03 §2", "forward_price(100, 0.02, 1, div_fv=3 * 1.02 ** 0.75)", 98.9551, 0.0005)
add("F1-2c", Q_F1, "2 c)", "Futures", "03 §2", "forward_price(100, 0.02, 1, continuous=True, q=0.03)", 99.005, 0.0005)
add("F1-3a", Q_F1, "3 a)", "Futures", "03 §2", "forward_price(1000, 0.02, 0.5, continuous=True, q=0.01)", 1005.0125, 0.0005)
add("F1-3b", Q_F1, "3 b)", "Futures", "03 §2", "3 * (1300 - forward_price(1000, 0.02, 0.5, continuous=True, q=0.01)) * 250", 221240.625, 0.05)
add("F1-3c", Q_F1, "3 c)", "Futures", "03 §2", "futures_leverage(250, forward_price(1000, 0.02, 0.5, continuous=True, q=0.01), 20000)", 12.5627, 0.0005)
add("F1-4a", Q_F1, "4 a)", "Hedging", "03 §3", "hedge_contracts(0.95, 2_000_000, 25, 15200)", 5.0, 0.0005)
add("F1-4b", Q_F1, "4 b)", "Hedging", "03 §3", "5 * 25 * (15200 - 15140) + (1_990_000 - 2_000_000)", -2500.0, 0.005)
add("F1-5-beta", Q_F1, "5", "Hedging", "03 §3", "hedge_beta(0.8, 0.2, 0.3)", 0.5333, 0.00005)
add("F1-5-kontrakte", Q_F1, "5", "Hedging", "03 §3", "hedge_contracts(hedge_beta(0.8, 0.2, 0.3), 100e6, 250, 10500)", 20.3162, 0.002, "Musterlösung rechnet mit β = 0,5333 gerundet")

# ---------------- Futures & Forwards 2
add("F2-1a1", Q_F2, "1 a) 1)", "Forwards", "03 §2", "forward_price(50, 0.03, 1)", 51.50, 0.005)
add("F2-1a2", Q_F2, "1 a) 2)", "Forwards", "03 §2", "forward_price(50, 0.03, 2)", 53.0450, 0.00005)
add("F2-1a3", Q_F2, "1 a) 3)", "Forwards", "03 §2", "forward_price(50, 0.03, 3)", 54.6364, 0.00005)
add("F2-1b", Q_F2, "1 b)", "Forwards", "03 §2", "forward_price(50, 0.03, 3, div_fv=2 * 1.03 ** 2 + 2 * 1.03)", 50.4546, 0.00005)
add("F2-1c", Q_F2, "1 c)", "Forwards", "03 §2", "forward_price(50, 0.03, 2, continuous=True, q=0.02)", 51.0101, 0.00005)
for lbl, t, exp_ in (("a", 0.25, 0.9310), ("b", 0.5, 0.9535), ("c", 0.75, 0.9765), ("d", 1.0, 1.0)):
    add(f"F2-2{lbl}", Q_F2, f"2 {lbl})", "Hedging", "03 §3", f"1 / 1.1 ** (1 - {t})", exp_, 0.00005, "Hedge Ratio bei CoC: σ(K)/σ(F) = 1/(1+r)^(T−t)")
add("F2-3a", Q_F2, "3 a)", "Futures", "03 §2", "forward_price(14500, 0.02, 1, continuous=True)", 14792.9194, 0.00005)
add("F2-3b", Q_F2, "3 b)", "Futures", "03 §2", "forward_price(14500, 0.02, 1, continuous=True) * 25", 369822.985, 0.005)
add("F2-3c2", Q_F2, "3 c) 2)", "Futures", "03 §2", "forward_price(14500, 0.02, 1, continuous=True, q=0.01)", 14645.7274, 0.00005, "Kursindex: Dividendenrendite mindert den Futurespreis")
add("F2-3c3", Q_F2, "3 c) 3)", "Futures", "03 §2", "forward_price(14500, 0.02, 1, continuous=True, q=0.02)", 14500.0, 0.00005)
add("F2-4-beta", Q_F2, "4", "Hedging", "03 §3", "hedge_beta(0.5, 0.30, 0.25)", 0.6, 0.00005)
add("F2-4-kontrakte", Q_F2, "4", "Hedging", "03 §3", "hedge_contracts(0.6, 1_000_000, 25, forward_price(14500, 0.02, 0.5, continuous=True))", 1.6387, 0.00005)

# ---------------- Optionen
add("OP-2a-delta", Q_OP, "2 a)", "Binomialmodell", "03 §6", "binomial_replication(100, 1.2, 0.9, 0.05, 0, 10)[0]", -1/3, 0.00005)
add("OP-2a-anlage", Q_OP, "2 a)", "Binomialmodell", "03 §6", "binomial_replication(100, 1.2, 0.9, 0.05, 0, 10)[1]", 38.0952, 0.00005)
add("OP-2a-put", Q_OP, "2 a)", "Binomialmodell", "03 §6", "binomial_replication(100, 1.2, 0.9, 0.05, 0, 10)[2]", 4.7619, 0.00005)
add("OP-2b-put-2p", Q_OP, "2 b)", "Binomialmodell", "03 §7", "binomial_price(100, 1.2, 0.9, 0.05, 100, 2, 'put')", 4.3084, 0.00005)
add("OP-2c-call", Q_OP, "2 c)", "Binomialmodell", "03 §6", "binomial_replication(100, 1.2, 0.9, 0.05, 20, 0)[2]", 9.5238, 0.00005)
add("OP-2c-kredit", Q_OP, "2 c)", "Binomialmodell", "03 §6", "binomial_replication(100, 1.2, 0.9, 0.05, 20, 0)[1]", -57.1429, 0.00005)
add("OP-2d-call-2p", Q_OP, "2 d)", "Binomialmodell", "03 §7", "binomial_price(100, 1.2, 0.9, 0.05, 100, 2, 'call')", 13.6054, 0.00005)
add("OP-3-call", Q_OP, "3", "Binomialmodell", "03 §7", "binomial_price(400, 1.25, 0.8, 0.025, 420, 2, 'call')", 48.7805, 0.00005)
add("OP-4a-q", Q_OP, "4 a)", "Binomialmodell", "03 §6", "risk_neutral_q(1.3, 0.8, 0.10)", 0.6, 0.00005)
add("OP-4d-put-eu", Q_OP, "4 d)", "Binomialmodell", "03 §7", "binomial_price(40, 1.3, 0.8, 0.10, 45, 2, 'put')", 3.9140, 0.00005)
add("OP-4e-put-am", Q_OP, "4 e)", "Amerikanische Optionen", "03 §9", "binomial_price(40, 1.3, 0.8, 0.10, 45, 2, 'put', american=True)", 5.4017, 0.00005)
add("OP-5-bs", Q_OP, "5", "Black-Scholes", "03 §8", "black_scholes_call(50, 50, 0.02, 0.20, 0.36)", 2.57, 0.005, "Musterlösung liest N(d) aus der Tabelle; exakt 2,5675")

# ---------------- BFIN Hackethal
add("BF-1b-rendite", Q_BF, "Ü1 a)", "Portfolio", "02 §2", "portfolio_return([1/3, 2/3], [0.06, 0.09])", 0.08, 0.00005)
add("BF-1b-sigma", Q_BF, "Ü1 b)", "Portfolio", "02 §2", "portfolio_variance_2(1/3, 0.12, 0.18, 0.5) ** 0.5", 0.1442, 0.00005)
add("BF-1c-mvp", Q_BF, "Ü1 c)", "Portfolio", "02 §2", "mvp_weight_2(0.12, 0.18, 0.5)", 0.857, 0.0005)
add("BF-1d-mvp-rho1", Q_BF, "Ü1 d)", "Portfolio", "02 §2", "min(1.0, mvp_weight_2(0.12, 0.18, 0.9999999))", 1.0, 0.00005, "Ohne Leerverkauf 100 % in der risikoärmeren Aktie")
add("BF-1-cml-sigma", Q_BF, "Ü1 Mischportfolio", "Kapitalmarktlinie", "02 §2", "cml_sigma_for_target(0.05, 0.07, 0.06, 0.02)[0]", 0.036, 0.00005)
add("BF-1-cml-gewicht", Q_BF, "Ü1 Mischportfolio", "Kapitalmarktlinie", "02 §2", "cml_sigma_for_target(0.05, 0.07, 0.06, 0.02)[1]", 0.6, 0.00005)
add("BF-2a-markt-e", Q_BF, "Ü2 a)", "CAPM", "02 §3", "portfolio_return([2/3, 1/3], [0.09, 0.12])", 0.10, 0.00005)
add("BF-2a-markt-sigma", Q_BF, "Ü2 a)", "CAPM", "02 §3", "portfolio_variance_2(2/3, 0.10, 0.20, -0.2) ** 0.5", 0.0843, 0.00005)
add("BF-2b-beta", Q_BF, "Ü2 b)", "CAPM", "02 §3", "beta(0.01, portfolio_variance_2(2/3, 0.10, 0.20, -0.2))", 1.408, 0.003, "Musterlösung rundet σ²_M auf 0,0071")
add("BF-2b-ek-kosten", Q_BF, "Ü2 b)", "CAPM", "02 §3", "capm_return(0.03, beta(0.01, portfolio_variance_2(2/3, 0.10, 0.20, -0.2)), 0.07)", 0.1286, 0.0003, "Rundungsdifferenz wie oben")
add("BF-2c-ek-kosten-neu", Q_BF, "Ü2 c)", "CAPM", "02 §3", "capm_return(0.03, 0.5 * beta(0.01, portfolio_variance_2(2/3, 0.10, 0.20, -0.2)) + 0.5 * 0.6, 0.07)", 0.1003, 0.0003)
add("BF-2-beta", Q_BF, "Ü2 CAPM a)", "CAPM", "02 §3", "beta(0.05, 0.04)", 1.25, 0.00005)
add("BF-2-ek-kosten", Q_BF, "Ü2 CAPM b)", "CAPM", "02 §3", "capm_return(0.02, 1.25, 0.04)", 0.07, 0.00005)
add("BF-2-syst-anteil", Q_BF, "Ü2 CAPM c)", "CAPM", "02 §3", "systematic_share(1.25, 0.20, 0.30)", 0.6944, 0.00005)
for f, r, s, b, bm, bs, bh, sr, ac, aa in (("A", .0954, .3345, .91, .86, .96, .78, .18, .0306, -.0422),
                                            ("B", .0724, .1817, .60, .64, .10, -.34, .211, .0181, .0288),
                                            ("C", .0643, .2454, .98, 1.11, -.84, -.56, .123, -.0028, .0522)):
    add(f"BF-2-sharpe-{f}", Q_BF, "Ü2 APT a)", "Performancemessung", "04 §2, 09 §6", f"sharpe_ratio({r}, 0.0341, {s})", sr, 0.005)
    add(f"BF-2-alpha-capm-{f}", Q_BF, "Ü2 APT b)", "Performancemessung", "04 §2, 09 §6", f"capm_alpha({r}, 0.0341, {b}, 0.0678)", ac, 0.00006)
    add(f"BF-2-alpha-apt-{f}", Q_BF, "Ü2 APT c)", "Faktormodelle", "02 §4", f"apt_alpha({r}, 0.0341, [{bm}, {bs}, {bh}], [0.0337, 0.0394, 0.0470])", aa, 0.00006)
add("BF-3-kurs", Q_BF, "Ü3 DDM a)", "Aktienbewertung", "02 §5", "ddm_from_earnings(5, 0.10, 0.75, capm_return(0.05, 0.9, 0.07))", 35.36, 0.005)
add("BF-3-pvgo", Q_BF, "Ü3 DDM b)", "Aktienbewertung", "02 §5", "pvgo(ddm_from_earnings(5, 0.10, 0.75, 0.113), 5, 0.113)", -8.89, 0.005, "PVGO negativ, weil ROE < k")
add("BF-3-kurs-b50", Q_BF, "Ü3 DDM c)", "Aktienbewertung", "02 §5", "ddm_from_earnings(5, 0.10, 0.50, 0.113)", 41.67, 0.01, "Folie zeigt 41,6 (abgeschnitten)")
add("BF-3-impl-g", Q_BF, "Ü3 HoF a)", "Aktienbewertung", "02 §5", "implied_growth(100, 4, 0.10)", 0.05769, 0.000005)
add("BF-3-impl-roe", Q_BF, "Ü3 HoF b)", "Aktienbewertung", "02 §5", "implied_growth(100, 4, 0.10) / 0.2", 0.2885, 0.00005)
add("BF-3-pvgo-hof", Q_BF, "Ü3 HoF c)", "Aktienbewertung", "02 §5", "100 - perpetuity_pv(4 * 5 / 4, 0.10)", 50.0, 0.005)
add("BF-3-zweistufig", Q_BF, "Ü3 Zweistufiges DDM", "Aktienbewertung", "02 §5", "two_stage_ddm(6, 0.04, 2, 0.02, 0.08)", 105.93, 0.005)
add("BF-3-wacc", Q_BF, "Ü3 Leverage a)", "Kapitalstruktur", "01 §14", "wacc(50, 50, capm_return(0.04, 0.1 / 0.06, 0.06), 0.04)", 0.09, 0.00005)
add("BF-3-beta-neu", Q_BF, "Ü3 Leverage b)", "Kapitalstruktur", "01 §14", "equity_beta_from_asset(0.5 * 0.1 / 0.06, 2, 1)", 1.25, 0.00005)
add("BF-3-ek-neu", Q_BF, "Ü3 Leverage b)", "Kapitalstruktur", "01 §14", "capm_return(0.04, equity_beta_from_asset(0.5 * 0.1 / 0.06, 2, 1), 0.06)", 0.115, 0.00005)
add("BF-3-fcf1", Q_BF, "Ü3 FCF 1", "Cashflows", "01 §9", "free_cash_flow(1_200_000, 0.30, 133_000, 76_000, 24_000)", 873000.0, 0.5)
add("BF-3-fcf2", Q_BF, "Ü3 FCF 2", "Cashflows", "01 §9", "free_cash_flow(500_000 - 100_000, 0.30, 100_000, 200_000, 0)", 180000.0, 0.5)
add("BF-3-wert", Q_BF, "Ü3 FCF 2", "Aktienbewertung", "01 §1", "gordon_price(free_cash_flow(400_000, 0.30, 100_000, 200_000, 0), 0.15, 0.06)", 2_000_000.0, 0.5)
add("BF-4-zerobond", Q_BF, "Ü4 Bondbewertung 1", "Anleihen", "02 §6", "pv(1000, 0.09, 8.5)", 480.70, 0.005)
add("BF-4-kuponbond", Q_BF, "Ü4 Bondbewertung 2", "Anleihen", "02 §6", "price_flat(bond_cashflows(1000, 0.07, 3), 0.10)", 925.39, 0.005)
add("BF-4-stueckzins-act", Q_BF, "Ü4 Stückzinsen 1", "Anleihen", "02 §6", "accrued_interest(100_000, 0.08, 2, 76, 183)", 1661.20, 0.005)
add("BF-4-stueckzins-30", Q_BF, "Ü4 Stückzinsen 1", "Anleihen", "02 §6", "accrued_interest(100_000, 0.08, 2, 75, 180)", 1666.67, 0.005)
add("BF-4-full-price", Q_BF, "Ü4 Stückzinsen 2", "Anleihen", "02 §6", "1.08 * 1000 + accrued_interest(1000, 0.09, 1, 30, 360)", 1087.50, 0.005)
add("BF-4-current-yield", Q_BF, "Ü4 Wahr/Falsch", "Anleihen", "02 §6", "0.08 * 100 / 95", 0.084, 0.0005)
add("BF-4-y2", Q_BF, "Ü4 Zinsstruktur B", "Zinsstruktur", "02 §6", "ytm(bond_cashflows(100, 0.03, 2), 101)", 0.0248, 0.00005)
add("BF-4-r2", Q_BF, "Ü4 Zinsstruktur C", "Zinsstruktur", "02 §6", "((1.02) * (1.0298)) ** 0.5 - 1", 0.0249, 0.00005)
add("BF-4-y3", Q_BF, "Ü4 Zinsstruktur", "Zinsstruktur", "02 §6", "ytm(bond_cashflows(100, 0.04, 3), 102)", 0.0329, 0.00005)
add("BF-4-f3", Q_BF, "Ü4 Zinsstruktur D", "Zinsstruktur", "02 §6", "forward_rate(0.0249, 2, 0.0333, 3)", 0.0503, 0.00005)
add("BF-4-r4", Q_BF, "Ü4 Zinsstruktur E/F", "Zinsstruktur", "02 §6", "spot_from_pv(85, 100, 4)", 0.0415, 0.00005)
add("BF-4-f4", Q_BF, "Ü4 Zinsstruktur G", "Zinsstruktur", "02 §6", "forward_rate(0.0333, 3, spot_from_pv(85, 100, 4), 4)", 0.0664, 0.001, "Musterlösung rechnet mit gerundeten Spot Rates")

# ---------------- OFIN Übung (Lam)
K = "KURVE_OFIN"
add("OF-04", Q_OF, "4", "Barwert", "02 §1", "fv(1000, 0.04, 4)", 1169.86, 0.005)
add("OF-05", Q_OF, "5", "Barwert", "02 §1", "pv(1000, 0.04, 4)", 854.80, 0.005)
add("OF-06", Q_OF, "6", "Barwert", "02 §1", f"pv_cashflows({{1: 100, 2: 100, 3: 100, 4: 100}}, curve={K})", 367.50, 0.005)
add("OF-07", Q_OF, "7", "Barwert", "02 §1", f"pv_cashflows({{1: 50, 2: 100, 4: 200}}, curve={K})", 314.0, 0.01)
add("OF-08", Q_OF, "8", "Barwert", "02 §1", "fv(1000, 0.035, 3)", 1108.72, 0.005)
add("OF-09", Q_OF, "9", "Barwert", "02 §1", "fv(1000 + pv(1000, 0.025, 1), 0.04, 4)", 2311.18, 0.005)
add("OF-10", Q_OF, "10", "Barwert", "02 §1", "spot_from_pv(826.45, 1000, 2)", 0.10, 0.00005)
add("OF-11", Q_OF, "11", "Barwert", "02 §1", "spot_from_pv(800, 1000, 4)", 0.0574, 0.00005)
add("OF-12", Q_OF, "12", "Kapitalwert", "01 §1", f"npv({{0: -350, 1: 100, 2: 100, 3: 100, 4: 100}}, curve={K})", 17.50, 0.005)
add("OF-13", Q_OF, "13", "Kapitalwert", "01 §1", f"npv({{0: -1000, 4: 1150}}, curve={K})", -16.98, 0.005)
add("OF-14", Q_OF, "14", "Kapitalwert", "01 §1", f"npv({{0: -100, 1: 50, 2: 50, 4: 10}}, curve={K})", 4.46, 0.005)
add("OF-15", Q_OF, "15", "Kapitalwert", "01 §1", f"breakeven_cashflow({{0: -50, 1: 30}}, 2, {K})", 21.99, 0.005)
add("OF-16", Q_OF, "16", "Kapitalwert", "01 §1", f"breakeven_cashflow({{0: -50, 1: 30}}, 3, {K})", 22.99, 0.005)
add("OF-17", Q_OF, "17", "Kapitalwert", "01 §1", f"breakeven_cashflow({{0: -50, 1: 30}}, 4, {K})", 24.25, 0.005)
add("OF-21", Q_OF, "21", "Interner Zins", "01 §2", "max(irr_two_period(-100, 10, 110))", 0.10, 0.00005, "zweite Lösung −200 % ökonomisch irrelevant")
add("OF-22-irr", Q_OF, "22", "Interner Zins", "01 §2", "max(irr_two_period(-20, 10, 20))", 0.28, 0.005)
add("OF-22-npv1", Q_OF, "22", "Interner Zins", "01 §2", "npv({0: -100, 1: 10, 2: 110}, 0.05)", 9.30, 0.005)
add("OF-22-npv2", Q_OF, "22", "Interner Zins", "01 §2", "npv({0: -20, 1: 10, 2: 20}, 0.05)", 7.66, 0.005, "IRR wählt P2, NPV wählt P1")
add("OF-23-irr-niedrig", Q_OF, "23", "Interner Zins", "01 §2", "min(irr_two_period(-15, 40, -26))", 0.12, 0.005, "zwei positive IRR: Mehrdeutigkeit")
add("OF-23-irr-hoch", Q_OF, "23", "Interner Zins", "01 §2", "max(irr_two_period(-15, 40, -26))", 0.54, 0.005)
add("OF-23-npv", Q_OF, "23", "Interner Zins", "01 §2", "npv({0: -15, 1: 40, 2: -26}, 0.15)", 0.12, 0.005)
add("OF-25-npv1", Q_OF, "Projekte r=5%", "Interner Zins", "01 §2", "npv({0: -1, 1: 2}, 0.05)", 0.904, 0.001, "Folie schneidet ab")
add("OF-25-npv2", Q_OF, "Projekte r=5%", "Interner Zins", "01 §2", "npv({0: -100, 1: 199}, 0.05)", 89.523, 0.001, "Skalenproblem des IRR; Folie schneidet ab")
N = "KURVE_OFIN_NEG"
add("OF-24", Q_OF, "24", "Anleihen", "02 §1", f"pv_cashflows(bond_cashflows(100, 0.05, 5), curve={N})", 124.02, 0.005, "negative Zinsen")
add("OF-25-annuitaet", Q_OF, "25", "Annuität", "02 §1", f"pv_cashflows(bond_cashflows(100, 0.05, 5), curve={N}) / annuity_pv(1, 5, curve={N})", 24.84, 0.005)
add("OF-26", Q_OF, "26", "Anleihen", "02 §1", f"pv(100, {N}[5], 5)", 99.06, 0.005)
add("OF-28", Q_OF, "28", "Annuität", "02 §1", f"annuity_pv(5, 5, curve={N})", 24.96, 0.005)
add("OF-29", Q_OF, "29", "Annuität", "02 §1", f"annuity_pv(10, 8, curve={N})", 78.86, 0.005)
add("OF-30", Q_OF, "30", "Annuität", "02 §1", "annuity_pv(10, 10, 0.0002)", 99.89, 0.005)
add("OF-31", Q_OF, "31", "Annuität", "02 §1", "annuity_pv(10, 10, 0.01)", 94.71, 0.005)
add("OF-32", Q_OF, "32", "Ewige Rente", "02 §1", "perpetuity_pv(10, 0.0002)", 50000.0, 0.005)
add("OF-33", Q_OF, "33", "Ewige Rente", "02 §1", "perpetuity_pv(10, 0.01)", 1000.0, 0.005)
add("OF-34", Q_OF, "34", "Ewige Rente", "02 §1", "perpetuity_pv(10, 0.0003) - perpetuity_pv(10, 0.0002)", -16666.67, 0.005, "extreme Zinssensitivität bei Niedrigzins")
add("OF-35", Q_OF, "35", "Aktienbewertung", "02 §1", "perpetuity_pv(3, 0.05)", 60.0, 0.005)
add("OF-36", Q_OF, "36", "Aktienbewertung", "02 §1", "perpetuity_pv(5, 0.03)", 166.67, 0.005)
add("OF-37", Q_OF, "37", "Aktienbewertung", "02 §1", "gordon_price(3 * 1.02, 0.05, 0.02)", 102.0, 0.005, "Folie: Dividende 3 wächst, D1 = 3·1,02")
add("OF-38", Q_OF, "38", "Aktienbewertung", "02 §1", "perpetuity_pv(3, 0.05, 0.06)", float('inf'), 0, "g > r: kein endlicher Wert")
add("OF-39", Q_OF, "39", "Aktienbewertung", "02 §1", "60 * 0.03", 1.8, 0.005)
add("OF-40", Q_OF, "40", "Aktienbewertung", "02 §1", "80 * (0.03 - 0.01) / 1.01", 1.58, 0.005)
add("OF-41", Q_OF, "41", "Aktienbewertung", "02 §1", "perpetuity_pv(3.5, 0.03) / perpetuity_pv(4, 0.03) - 1", -0.125, 0.00005)
add("OF-55", Q_OF, "55", "Rendite", "02 §2", "simple_return(55, 60)", 0.0909, 0.00005)
add("OF-56-auf", Q_OF, "56", "Rendite", "02 §2", "simple_return(35, 37)", 0.0571, 0.00005)
add("OF-56-ab", Q_OF, "56", "Rendite", "02 §2", "simple_return(35, 32)", -0.0857, 0.00005)
add("OF-58", Q_OF, "58", "Rendite", "02 §2", "simple_return(10, 0, 12)", 0.20, 0.00005)
add("OF-60-p3", Q_OF, "60", "Erwartungswert", "02 §2", "expected_value([0.10, 0.05, 0.0, -0.05])", 0.025, 0.00005)
add("OF-60-p4", Q_OF, "60", "Erwartungswert", "02 §2", "expected_value([0.20, 0.15, 0.10, 0.05, 0.0, -0.05, -0.10, -0.15])", 0.025, 0.00005)
add("OF-61-p5", Q_OF, "61", "Erwartungswert", "02 §2", "expected_value([0.12, 0.07, 0.0, -0.05, -0.10], [0.1, 0.2, 0.4, 0.2, 0.1])", 0.006, 0.00005)
add("OF-61-p6", Q_OF, "61", "Erwartungswert", "02 §2", "expected_value([0.20, 0.15, 0.10, 0.05, 0.0, -0.05, -0.10, -0.15], [0.1, 0.1, 0.1, 0.2, 0.1, 0.2, 0.1, 0.1])", 0.02, 0.00005)
add("OF-62-p2", Q_OF, "62", "Varianz", "02 §2", "variance([-0.1, 0.0, 0.1]) ** 0.5", 0.0816, 0.00005)
add("OF-62-p3", Q_OF, "62", "Varianz", "02 §2", "variance([0.10, 0.05, 0.0, -0.05]) ** 0.5", 0.056, 0.0005)
add("OF-62-p4", Q_OF, "62", "Varianz", "02 §2", "variance([0.20, 0.15, 0.10, 0.05, 0.0, -0.05, -0.10, -0.15]) ** 0.5", 0.115, 0.0005)
add("OF-62-p5", Q_OF, "62", "Varianz", "02 §2", "variance([0.12, 0.07, 0.0, -0.05, -0.10], [0.1, 0.2, 0.4, 0.2, 0.1]) ** 0.5", 0.0623, 0.00005)
add("OF-62-p6", Q_OF, "62", "Varianz", "02 §2", "variance([0.20, 0.15, 0.10, 0.05, 0.0, -0.05, -0.10, -0.15], [0.1, 0.1, 0.1, 0.2, 0.1, 0.2, 0.1, 0.1]) ** 0.5", 0.105, 0.0005)
add("OF-63-gewicht", Q_OF, "63", "Portfolio", "02 §2", "value_weights([15, 10], [15, 13])[0]", 0.6338, 0.00005)
add("OF-63-rendite", Q_OF, "63", "Portfolio", "02 §2", "portfolio_return(value_weights([15, 10], [15, 13]), [0.05, 0.03])", 0.0427, 0.00005)
add("OF-64-rendite", Q_OF, "64", "Portfolio", "02 §2", "portfolio_return(value_weights([3, 5, 7], [50, 30, 20]), [0.10, 0.08, 0.13])", 0.1027, 0.00005)
add("OF-65", Q_OF, "65", "Portfolio", "02 §2", "portfolio_variance_2(value_weights([15, 10], [15, 13])[0], 0.1 ** 0.5, 0.2 ** 0.5, 0.71)", 0.1136, 0.00005)
add("OF-66", Q_OF, "66", "Portfolio", "02 §2", "portfolio_variance_2(value_weights([15, 10], [15, 13])[0], 0.1 ** 0.5, 0.2 ** 0.5, -0.71)", 0.0203, 0.0001, "Folie schneidet ab")
add("OF-80", Q_OF, "80", "CAPM", "02 §3", "2 * 0.05", 0.10, 0.00005)
add("OF-81", Q_OF, "81", "CAPM", "02 §3", "0.08 / 0.05", 1.6, 0.00005)
add("OF-86", Q_OF, "86", "Kapitalstruktur", "01 §14", "(1 - 3 / 4) / (3 / 4)", 1/3, 0.00005, "FK/EK aus β_EK = 4, β_Asset = 3")
add("OF-94", Q_OF, "94", "Kapitalstruktur", "01 §10", "wacc(100, 60, capm_return(0.03, 1.2, 0.09), 0.03)", 0.0975, 0.00005)
add("OF-95", Q_OF, "95", "Kapitalstruktur", "01 §10", "wacc(200, 60, capm_return(0.03, 1.2, 0.09), 0.03)", 0.1131, 0.00005)
add("OF-96-beta", Q_OF, "96", "Kapitalstruktur", "01 §14", "equity_beta_from_asset(1.2, 100, 60)", 1.92, 0.00005)
add("OF-96-wacc", Q_OF, "96", "Kapitalstruktur", "01 §14", "wacc(100, 60, capm_return(0.03, equity_beta_from_asset(1.2, 100, 60), 0.09), 0.03)", 0.138, 0.00005)
add("OF-97-beta", Q_OF, "97", "Kapitalstruktur", "01 §14", "equity_beta_from_asset(1.2, 90, 70)", 2.1333, 0.00005)
add("OF-97-wacc", Q_OF, "97", "Kapitalstruktur", "01 §14", "wacc(90, 70, capm_return(0.03, equity_beta_from_asset(1.2, 90, 70), 0.09), 0.03)", 0.138, 0.00005, "MM: WACC unverändert")
add("OF-98-beta", Q_OF, "98", "Kapitalstruktur", "01 §14", "equity_beta_from_asset(1.2, 90, 70, beta_debt=0.1)", 2.0556, 0.00005)
add("OF-98-ek", Q_OF, "98", "Kapitalstruktur", "01 §14", "capm_return(0.03, equity_beta_from_asset(1.2, 90, 70, beta_debt=0.1), 0.09)", 0.215, 0.00005)
add("OF-98-wacc", Q_OF, "98", "Kapitalstruktur", "01 §14", "wacc(90, 70, capm_return(0.03, equity_beta_from_asset(1.2, 90, 70, beta_debt=0.1), 0.09), capm_return(0.03, 0.1, 0.09))", 0.138, 0.00005)
add("OF-99-ek-a", Q_OF, "99", "Modigliani-Miller", "01 §10", "simple_return(20, 24)", 0.20, 0.00005)
add("OF-99-ek-b", Q_OF, "99", "Modigliani-Miller", "01 §10", "((0.9 * 0.2 + 0.1 * 0.06) - 0.4 * 0.08) / 0.6", 0.2567, 0.00005, "gleicher WACC wegen Arbitragefreiheit")
add("OF-99-div-b", Q_OF, "99", "Modigliani-Miller", "01 §10", "30 * (1 + ((0.9 * 0.2 + 0.1 * 0.06) - 0.4 * 0.08) / 0.6)", 37.7, 0.005)
add("OF-100", Q_OF, "100", "Kapitalstruktur", "01 §14", "100 - 100 * 1.5 / 3", 50.0, 0.00005)
add("OF-101", Q_OF, "101", "Kapitalstruktur", "01 §14", "capm_return(0.02, equity_beta_from_asset((0.12 - 0.02) / (0.07 - 0.02), 60, 40), 0.05)", 0.1867, 0.00005)
add("OF-102-beta-fk", Q_OF, "102", "Kapitalstruktur", "01 §14", "(0.03 - 0.02) / (0.07 - 0.02)", 0.2, 0.00005)
add("OF-102-ek", Q_OF, "102", "Kapitalstruktur", "01 §14", "capm_return(0.02, equity_beta_from_asset(1.5, 50, 50, beta_debt=0.2), 0.05)", 0.16, 0.00005)
add("OF-103", Q_OF, "103", "Kapitalstruktur", "01 §6", "wacc(20, 40, expected_value([(120 - 46 - 20) / 20, (70 - 46 - 20) / 20, (0 - 20) / 20]), expected_value([6 / 40, 6 / 40, 4 / 40]))", 0.30, 0.00005, "Zahlungstabelle: FK erhält 46, im schlechten Zustand nur 44")
add("OF-134", Q_OF, "Steuern", "Tax Shield", "01 §14", "5 + (100 - 5) * (1 - 0.35)", 66.75, 0.005, "Auszahlung an EK+FK verschuldet vs. 65 unverschuldet")
add("OF-104-vu", Q_OF, "104 1)", "Tax Shield", "01 §14", "(200 + (280 - 200) * 0.65) / 1.12", 225.0, 0.005)
add("OF-104-vl", Q_OF, "104 2)", "Tax Shield", "01 §14", "(200 + (280 - 200) * 0.65) / 1.12 + tax_shield_value(11, 0.35, 0.12)", 228.44, 0.005)
add("OF-105-vu", Q_OF, "105 1)", "Tax Shield", "01 §14", "(50 + 25 * 0.65) / 1.12", 59.15, 0.005)
add("OF-105-vl", Q_OF, "105 2)", "Tax Shield", "01 §14", "(50 + 25 * 0.65) / 1.12 + tax_shield_value(25 * 0.11, 0.35, 0.12)", 60.01, 0.005)
add("OF-105-vu2", Q_OF, "105 3)", "Tax Shield", "01 §14", "(50 + 25 * 0.65) / 1.12 + (50 + 25 * 0.65) / 1.12 ** 2", 111.97, 0.005)
add("OF-105-vl2", Q_OF, "105 3)", "Tax Shield", "01 §14", "(50 + 25 * 0.65) / 1.12 + (50 + 25 * 0.65) / 1.12 ** 2 + 25 * 0.11 * 0.35 / 1.12 + 25 * 0.11 * 0.35 / 1.12 ** 2", 113.60, 0.01, "Musterlösung rundet Zwischenergebnisse")
for z, ik, p, e in ((10, 2, .10, 2.94), (15, 7, .14, 3.81), (32, 15, .20, 7.32), (50, 30, .35, 6.25), (70, 50, .50, -0.44)):
    add(f"OF-106-zins{z}", Q_OF, "106", "Trade-off-Theorie", "01 §14", f"({z} * 0.35 - {ik} * {p}) / 1.12", e, 0.01, "Optimum bei Zinsen 32; Folie schneidet ab")
for k_, e in ((90, 20.45), (100, 13.64), (110, 6.82), (120, 0.0)):
    add(f"OF-112-call-{k_}", Q_OF, "112", "Binomialmodell", "03 §6", f"binomial_price(100, 1.2, 0.8, 0.10, {k_}, 1, 'call')", e, 0.005)
for k_, e in ((80, 0.0), (90, 2.27), (100, 4.55), (110, 6.81), (120, 9.09)):
    add(f"OF-113-put-{k_}", Q_OF, "113", "Binomialmodell", "03 §6", f"binomial_price(100, 1.2, 0.8, 0.10, {k_}, 1, 'put')", e, 0.01, "Folie schneidet teils ab (6,818 → 6,81)")
add("OF-114", Q_OF, "114", "Put-Call-Parität", "03 §5", "binomial_price(100, 1.2, 0.8, 0.10, 110, 1, 'call') - binomial_price(100, 1.2, 0.8, 0.10, 110, 1, 'put')", 0.0, 0.00005)
add("OF-118-npv1", Q_OF, "118", "Agency", "02 §9", "npv({0: -100, 1: expected_value([120, 110])}, 0.10)", 4.55, 0.005)
add("OF-118-npv2", Q_OF, "118", "Agency", "02 §9", "npv({0: -100, 1: expected_value([150, 50])}, 0.10)", -9.09, 0.005)
for fk, r, e1, e2 in ((100, .10, 4.54, 18.18), (100, .20, 0.0, 12.5), (60, .10, 44.54, 38.18), (60, .40, 22.14, 23.57)):
    add(f"OF-118-ek1-fk{fk}-r{int(r*100)}", Q_OF, "118", "Agency", "02 §9", f"expected_value([max(120 - {fk} * (1 + {r}), 0), max(110 - {fk} * (1 + {r}), 0)]) / (1 + {r})", e1, 0.01)
    add(f"OF-118-ek2-fk{fk}-r{int(r*100)}", Q_OF, "118", "Agency", "02 §9", f"expected_value([max(150 - {fk} * (1 + {r}), 0), max(50 - {fk} * (1 + {r}), 0)]) / (1 + {r})", e2, 0.01, "Asset Substitution: Eigentümer wählt das riskante Projekt")
add("OF-118-schwelle", Q_OF, "118", "Agency", "02 §9", "120 / 100 - 1", 0.20, 0.00005)


# ---------------- Accounting 1 (Kosten- und Erlösrechnung)
# Lösung WiSe 2026/27 (Bormann) zu den Aufgaben SoSe 2026 (Rohlfing-Bastian). Nur Aufgaben, deren Angaben
# übereinstimmen; abweichende Nummern: SoSe 4.4 = Lösung 4.3, SoSe 9.2 = Lösung 9.3.
Q_AC = "Accounting_1_WiSe_2026_27_Lösung (Aufgaben: Accounting 1 SoSe 2026)"
def ac(id_, aufg, thema, ausdruck, erw, tol, hinweis=""):
    add("AC-" + id_, Q_AC, aufg, thema, "08 §4", ausdruck, erw, tol, hinweis)

# 3.1 FIFO / LIFO (permanente Bewertung)
LAG = "[[1500, 5.10]], [[300, 5.30], [-1300], [-300], [1400, 5.45], [800, 6.55], [-600], [-1000]]"
for m, werte, eb in (("fifo", (6630, 1550, 3240, 5450), 5240), ("lifo", (6690, 1530, 3930, 5670), 4290)):
    for k, (dat, w) in enumerate(zip(("16.02", "13.07", "21.10", "28.11"), werte)):
        ac(f"3.1-{m}-abgang-{dat}", "3.1 (a)", "Lagerbewertung", f"lagerbewertung({LAG}, '{m}')['abgaenge'][{k}]", w, 0.005)
    ac(f"3.1-{m}-endbestand", "3.1 (a)", "Lagerbewertung", f"lagerbewertung({LAG}, '{m}')['endbestand']", eb, 0.005)
ac("3.1-summe", "3.1 (a)", "Lagerbewertung", f"sum(lagerbewertung({LAG}, 'fifo')['abgaenge']) + lagerbewertung({LAG}, 'fifo')['endbestand']", 22110, 0.005, "AB + Zugänge = Abgänge + EB")

# 3.2 Abschreibungspläne
for t, rw in zip(range(1, 5), (140000, 100000, 60000, 20000)):
    ac(f"3.2-linear-rw{t}", "3.2 (1)", "Abschreibung", f"restwert_linear(180000, 20000, 4, {t})", rw, 0.005)
ac("3.2-linear-afa", "3.2 (1)", "Abschreibung", "afa_linear(180000, 20000, 4)", 40000, 0.005)
ac("3.2-geo-satz", "3.2 (2)", "Abschreibung", "afa_geo_satz(180000, 20000, 4)", 0.4226, 0.00005)
for t, a in zip(range(1, 5), (76068, 43922, 25360, 14643)):
    ac(f"3.2-geo-afa{t}", "3.2 (2)", "Abschreibung", f"afa_geo(180000, 20000, 4, {t}, satz=0.4226)", a, 1.0, "Musterlösung rechnet mit gerundetem Satz 42,26 % und rundet je Periode auf ganze €")
ac("3.2-geo-rw4-gerundet", "3.2 (2)", "Abschreibung", "buchwert_geo(180000, 20000, 4, 4, satz=0.4226)", 20007, 1.0, "Rundungsdifferenz laut Musterlösung")
ac("3.2-geo-rw4-exakt", "3.2 (2)", "Abschreibung", "buchwert_geo(180000, 20000, 4, 4)", 20000, 0.005, "exakter Satz führt genau auf den Resterlös")
for t, a in zip(range(1, 5), (50000, 30000, 45000, 35000)):
    ac(f"3.2-leistung-afa{t}", "3.2 (3)", "Abschreibung", f"afa_leistung(180000, 20000, [100000, 60000, 90000, 70000], {t})", a, 0.005)

# 3.3 Dienstwagen, kalkulatorische Zinsen
ac("3.3a-nutzungsdauer", "3.3 (a)", "Kalkulatorische Abschreibung", "192000 / (4000 * 12)", 4, 0.00005)
ac("3.3a-restwert-01.03.X3", "3.3 (a)", "Kalkulatorische Abschreibung", "restwert_linear(30000, 0, 4, 14 / 12)", 21250, 0.005)
ac("3.3a-zinsen-gesamt", "3.3 (a)", "Kalkulatorische Zinsen", "kalk_zinsen_durchschnitt(30000, 0, 0.10) * 4", 6000, 0.005)
for t in range(1, 6):
    ac(f"3.3b-restwert{t}", "3.3 (b)", "Kalkulatorische Abschreibung", f"restwert_linear(90000, 0, 5, {t})", 90000 - 18000 * t, 0.005)
    ac(f"3.3b-durchschnitt{t}", "3.3 (b)", "Kalkulatorische Abschreibung", f"durchschnittswert_linear(90000, 0, 5, {t})", 99000 - 18000 * t, 0.005)
    ac(f"3.3c-zins-restwert{t}", "3.3 (c)", "Kalkulatorische Zinsen", f"kalk_zinsen_restwert(90000, 0, 5, {t}, 0.10)", 9900 - 1800 * t, 0.005, "Restwertverfahren: Zins auf den Durchschnittswert des Jahres")
ac("3.3c-zins-durchschnitt", "3.3 (c)", "Kalkulatorische Zinsen", "kalk_zinsen_durchschnitt(90000, 0, 0.10)", 4500, 0.005)
N_BNV = "[3100000, 2400000, 150000, 1200000, 420000, 1000000, 1200000], [2900000, 2000000, 170000, 1600000, 380000, 200000, 1200000]"
N_NBV = "[585000, 465000, 240000], [575000, 455000, 320000]"
N_ABZ = "[1460000, 230000, 300000], [860000, 570000, 300000]"
H_ABZ = "Musterlösung zählt Rückstellungen, erhaltene Anzahlungen und Lieferantenverbindlichkeiten zum Abzugskapital"
ac("3.3d-bnv", "3.3 (d)", "Kalkulatorische Zinsen", f"bilanz_mittel({N_BNV})", 8960000, 0.005, "Wohnhäuser und Spekulationspapiere sind nicht betriebsnotwendig")
ac("3.3d-nbv", "3.3 (d)", "Kalkulatorische Zinsen", f"bilanz_mittel({N_NBV})", 1320000, 0.005)
ac("3.3d-abzugskapital", "3.3 (d)", "Kalkulatorische Zinsen", f"bilanz_mittel({N_ABZ})", 1860000, 0.005, H_ABZ)
ac("3.3d-zinsgebunden", "3.3 (d)", "Kalkulatorische Zinsen", f"bilanz_mittel({N_BNV}) + bilanz_mittel({N_NBV}) - bilanz_mittel({N_ABZ})", 8420000, 0.005)
ac("3.3d-zinsberechtigt", "3.3 (d)", "Kalkulatorische Zinsen", f"bilanz_mittel({N_BNV}) - bilanz_mittel({N_ABZ})", 7100000, 0.005)
ac("3.3d-zinsen", "3.3 (d)", "Kalkulatorische Zinsen", f"kalk_zinsen_kapital(bilanz_mittel({N_BNV}), bilanz_mittel({N_ABZ}), 0.10)", 710000, 0.005)

# 3.5 monatliche kalkulatorische Zinsen
for t, z in zip(range(1, 7), (1833.33, 1500, 1166.67, 833.33, 500, 166.67)):
    ac(f"3.5-zins-restwert{t}", "3.5", "Kalkulatorische Zinsen", f"kalk_zinsen_restwert(300000, 0, 6, {t}, 0.08) / 12", z, 0.005)
ac("3.5-zins-durchschnitt", "3.5", "Kalkulatorische Zinsen", "kalk_zinsen_durchschnitt(300000, 0, 0.08) / 12", 1000, 0.005)
ac("3.5-afa", "3.5", "Kalkulatorische Abschreibung", "afa_linear(300000, 0, 6)", 50000, 0.005)

# 3.6 Iglu AG (T€)
I_BNV = "[12000, 2200, 310, 1200, 2400], [11400, 1800, 170, 1600, 2800]"
I_NBV = "[645, 465, 40], [575, 455, 320]"
I_ABZ = "[2080], [1280]"
ac("3.6-bnv", "3.6", "Kalkulatorische Zinsen", f"bilanz_mittel({I_BNV})", 17940, 0.0005)
ac("3.6-nbv", "3.6", "Kalkulatorische Zinsen", f"bilanz_mittel({I_NBV})", 1250, 0.0005)
ac("3.6-abzugskapital", "3.6", "Kalkulatorische Zinsen", f"bilanz_mittel({I_ABZ})", 1680, 0.0005, "Rückstellungen als Abzugskapital")
ac("3.6-zinsgebunden", "3.6", "Kalkulatorische Zinsen", f"bilanz_mittel({I_BNV}) + bilanz_mittel({I_NBV}) - bilanz_mittel({I_ABZ})", 17510, 0.0005)
ac("3.6-zinsberechtigt", "3.6", "Kalkulatorische Zinsen", f"bilanz_mittel({I_BNV}) - bilanz_mittel({I_ABZ})", 16260, 0.0005)
ac("3.6-zinsen", "3.6", "Kalkulatorische Zinsen", f"kalk_zinsen_kapital(bilanz_mittel({I_BNV}), bilanz_mittel({I_ABZ}), 0.08)", 1300.80, 0.0005)

# 4.1 Primärkostenverteilung (BAB)
V41 = ("[[90000, [1, 3, 2, 0, 0, 0, 0, 5, 4]], [100000, [2, 1, 0, 1, 2, 2, 2, 0, 0]], [50000, [10, 20, 0, 25, 10, 15, 10, 5, 5]], "
       "[28000, [0, 0, 0, 10000, 6000, 12000, 0, 0, 0]], [150000, [35000, 40000, 55000, 65000, 80000, 375000, 25000, 75000, 50000]]], "
       "[0, 0, 0, 0, 0, 0, 0, 125000, 110000]")
for k, (ks, w) in enumerate(zip(("hausmeister", "werkstatt", "werksarzt", "angelruten", "angelschnuere", "kunstkoeder", "lager", "verwaltung", "vertrieb"),
                                (37562.5, 45500, 22312.5, 44687.5, 46000, 109812.5, 29687.5, 171562.5, 145875))):
    ac(f"4.1-primaer-{ks}", "4.1", "Kostenstellenrechnung", f"bab_primaer({V41})[{k}]", w, 0.005, "Fertigungslöhne und -material sind Einzelkosten und gehen nicht in den BAB")

# 4.2 Block- und Treppenumlage, Zuschlagssätze
P42 = "[14600, 3800, 6300, 5900, 6250, 5500, 8100, 8400, 7600, 24050, 19600]"
L42 = ("[[0, 60, 40, 140, 100, 120, 130, 60, 160, 90, 40], [0, 0, 0, 34, 16, 26, 0, 10, 0, 8, 0], [0, 0, 0, 18, 24, 0, 12, 0, 4, 16, 2]]"
       " + [[0] * 11] * 8")
END42 = ("dreherei", "lackiererei", "vormontage", "endmontage", "einkauf", "lager", "verwaltung", "vertrieb")
SOLL42 = {"block": (11199.91, 10624.38, 8636.78, 11354.26, 9847.11, 10712.53, 27264.01, 20461.03),
          "treppe": (11425.26, 10794.29, 8672.66, 11211.98, 9835.31, 10449.38, 27307.70, 20403.42)}
ZS42 = {"block": (130374.97, (0.7000, 0.7589, 1.2338, 1.4193, 0.8939, 0.2091, 0.1569)),
        "treppe": (130388.89, (0.7141, 0.7710, 1.2390, 1.4015, 0.8819, 0.2094, 0.1565))}
for verf in ("block", "treppe"):
    E = f"ibl_endkosten({P42}, {L42}, None, '{verf}', [0, 1, 2])"
    for k, (ks, w) in enumerate(zip(END42, SOLL42[verf])):
        ac(f"4.2a-{verf}-{ks}", "4.2 (a)", "Innerbetriebliche Leistungsverrechnung", f"{E}[{k + 3}]", w, 0.006, "Eigenverbrauch der Hausverwaltung (30 m²) bleibt unberücksichtigt")
    HK = f"(45000 + 23000 + sum({E}[3:9]))"
    hk, saetze = ZS42[verf]
    ac(f"4.2b-{verf}-herstellkosten", "4.2 (b)", "Zuschlagssätze", HK, hk, 0.006)
    for (ks, ausdr), s in zip((("dreherei", f"{E}[3] / 16000"), ("lackiererei", f"{E}[4] / 14000"), ("vormontage", f"{E}[5] / 7000"),
                               ("endmontage", f"{E}[6] / 8000"), ("material", f"({E}[7] + {E}[8]) / 23000"),
                               ("verwaltung", f"{E}[9] / {HK}"), ("vertrieb", f"{E}[10] / {HK}")), saetze):
        ac(f"4.2b-{verf}-zuschlag-{ks}", "4.2 (b)", "Zuschlagssätze", ausdr, s, 0.00005)

# SoSe 4.4 (= Lösung 4.3): Block, Treppe, Gleichungsverfahren
P44 = "[60000, 80000, 75000, 40000, 35000, 70000, 20000]"
L44a = "[[0, 0, 0, 0, 400, 400, 0], [0, 0, 0, 0, 0, 200, 0], [0, 0, 0, 0, 0, 300, 300], [0, 0, 0, 0, 0, 0, 100], [0] * 7, [0] * 7, [0] * 7]"
E44a = f"ibl_endkosten({P44}, {L44a}, None, 'block', [0, 1, 2, 3])"
H44 = "SoSe-Aufgabe 4.4 entspricht Lösung 4.3"
for k, ks, w, x in ((4, "ks5", 65000, 100), (5, "ks6", 217500, 200), (6, "ks7", 97500, 150)):
    ac(f"4.4a-block-end-{ks}", "4.4 (a)", "Innerbetriebliche Leistungsverrechnung", f"{E44a}[{k}]", w, 0.005, H44)
    ac(f"4.4a-block-stueck-{ks}", "4.4 (a)", "Innerbetriebliche Leistungsverrechnung", f"{E44a}[{k}] / {x}", w / x, 0.005, H44)
P44b = "[60000, 80000, 75000, 40000, 35000, 70000, 20000, 30000]"
L44b = ("[[0, 0, 0, 0, 400, 400, 0, 0], [0, 0, 0, 0, 0, 200, 0, 0], [0, 0, 0, 0, 0, 200, 300, 100], [0, 0, 0, 0, 0, 0, 100, 0], "
        "[0] * 8, [0, 0, 0, 0, 0, 0, 0, 100], [0] * 8, [0] * 8]")
E44b = f"ibl_endkosten({P44b}, {L44b}, [None, None, None, None, None, 200, None, None], 'treppe', [0, 1, 2, 3, 5])"
for k, ks, w, x in ((4, "ks5", 65000, 100), (5, "ks6", 102500, 100), (6, "ks7", 97500, 150), (7, "ks8", 145000, 100)):
    ac(f"4.4b-treppe-end-{ks}", "4.4 (b)", "Innerbetriebliche Leistungsverrechnung", f"{E44b}[{k}]", w, 0.005, H44)
    ac(f"4.4b-treppe-stueck-{ks}", "4.4 (b)", "Innerbetriebliche Leistungsverrechnung", f"{E44b}[{k}] / {x}", w / x, 0.005, H44)
L44c = L44b.replace("[0] * 8, [0, 0, 0, 0, 0, 0, 0, 100]", "[10, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 100]", 1)
E44c = f"ibl_endkosten({P44b}, {L44c}, [None, None, None, None, 100, 200, None, None], 'gleichung')"
for k, ks, w, x, s in ((4, "ks5", 61578.95, 90, 684.21), (5, "ks6", 104210.53, 100, 1042.11), (6, "ks7", 97500, 150, 650), (7, "ks8", 146710.53, 100, 1467.11)):
    ac(f"4.4c-gleichung-end-{ks}", "4.4 (c)", "Innerbetriebliche Leistungsverrechnung", f"{E44c}[{k}]", w, 0.005, H44 + "; KS5 liefert 10 von 100 Einheiten an KS1")
    ac(f"4.4c-gleichung-stueck-{ks}", "4.4 (c)", "Innerbetriebliche Leistungsverrechnung", f"{E44c}[{k}] / {x}", s, 0.005, H44)

# 4.5 Backstüberl, Gleichungsverfahren
P45 = "[10000, 4000, 13000, 15000, 17000, 11000, 13000, 10000]"
L45 = ("[[0, 112, 80, 48, 48, 320, 960, 32], [0, 0, 400, 300, 100, 100, 100, 0], [0, 0, 0, 600, 0, 0, 0, 0], [0, 0, 10500, 0, 199500, 0, 0, 0], "
       "[0, 0, 0, 0, 0, 20000, 180000, 0], [0, 0, 0, 0, 0, 0, 2000, 0], [0] * 8, [0] * 8]")
X45 = "[None, None, None, None, None, 20000, None, None]"
for k, w in enumerate((10000, 4700, 17068.95, 33778.95, 49860, 18456, 66189.60, 10200)):
    ac(f"4.5b-gk-ks{k + 1}", "4.5 (b)", "Innerbetriebliche Leistungsverrechnung", f"ibl_gleichung({P45}, {L45}, {X45})[{k}]", w, 0.005)
for k, w in enumerate((6.25, 4.70, 28.45, 0.16, 0.25, 0.92)):
    ac(f"4.5b-preis-ks{k + 1}", "4.5 (b)", "Innerbetriebliche Leistungsverrechnung", f"ibl_verrechnungspreise({P45}, {L45}, {X45})[{k}]", w, 0.005, "Musterlösung rundet auf zwei Stellen")
for k, w in ((5, 16610.40), (6, 66189.60), (7, 10200)):
    ac(f"4.5c-end-ks{k + 1}", "4.5 (c)", "Innerbetriebliche Leistungsverrechnung", f"ibl_endkosten({P45}, {L45}, {X45}, 'gleichung')[{k}]", w, 0.005)
ac("4.5a-koeff-formen-lauge", "4.5 (a)", "Innerbetriebliche Leistungsverrechnung", "199500 / (10500 + 199500)", 0.95, 0.00005)

# 5.1 Plan-Gesamtzuschlag
ac("5.1a-zuschlag", "5.1 (a)", "Zuschlagskalkulation", "zuschlagssatz(154630, 160000)", 0.9664, 0.00005)
ac("5.1b-selbstkosten", "5.1 (b)", "Zuschlagskalkulation", "7400 * (1 + round(zuschlagssatz(154630, 160000), 4)) + 2600", 17151.36, 0.005, "Musterlösung rechnet mit gerundetem Satz 96,64 %")

# 5.2 Divisionskalkulation
for hj, x, p, sk, k, e, g, tol, hw in (("a", 50000, 8, 7.275, 363750, 400000, 36250, 0.0005, ""),
                                         ("b", 45000, 8, 7.545, 339375, 360000, 20625, 0.004, "Musterlösung rundet Gemeinkosten je Stück auf 2,67 €")):
    ac(f"5.2{hj}-stueckkosten", f"5.2 ({hj})", "Divisionskalkulation", f"stueckkosten_division(2.25 + 3.50 * 45 / 60, 120000, {x})", sk, tol, hw)
    ac(f"5.2{hj}-kosten-gefertigt", f"5.2 ({hj})", "Divisionskalkulation", f"stueckkosten_division(2.25 + 3.50 * 45 / 60, 120000, {x}) * {x}", k, 0.005)
    ac(f"5.2{hj}-erloese", f"5.2 ({hj})", "Divisionskalkulation", f"{p} * {x}", e, 0.005)
    ac(f"5.2{hj}-erfolg", f"5.2 ({hj})", "Divisionskalkulation", f"{p} * {x} - stueckkosten_division(2.25 + 3.50 * 45 / 60, 120000, {x}) * {x}", g, 0.005)

# 5.3 BikeSport, normalisierte Zuschlagssätze
for ks, a, w in (("ks1", "30000, 60000", 0.5), ("ks2", "50000, 75000", 2 / 3), ("ks3", "20000, 10000", 2.0),
                 ("material", "5000, 50000", 0.1), ("verwaltung", "63000, 300000", 0.21), ("vertrieb", "30000, 300000", 0.1)):
    ac(f"5.3a-zuschlag-{ks}", "5.3 (a)", "Zuschlagskalkulation", f"zuschlagssatz({a})", w, 0.00005)
ac("5.3b-selbstkosten", "5.3 (b)", "Zuschlagskalkulation",
   "selbstkosten(materialkosten(20, 0.1) + 40 * (1 + 0.5) + 30 * (1 + 2 / 3) + 50 * (1 + 2), 0.21, 0.1)", 369.42, 0.005)

# 5.4 Venus GmbH
for n, a, w in (("fm-gesamt", "15 * 6000 + 30 * 3000", 180000), ("fl-gesamt", "10 * 6000 + 35 * 3000", 165000), ("zeit-gesamt", "0.30 * 6000 + 0.50 * 3000", 3300),
                ("zuschlag-material", "zuschlagssatz(18000, 180000)", 0.10), ("zuschlag-fertigung", "zuschlagssatz(330000, 3300)", 100),
                ("zuschlag-vwvt", "zuschlagssatz(60825, 405500)", 0.15)):
    ac(f"5.4-{n}", "5.4 (a)" if "gesamt" in n else "5.4 (b)", "Zuschlagskalkulation", a, w, 0.00005)
HK_R = "(materialkosten(15, 0.10) + 10 + 0.30 * 100)"
HK_H = "(materialkosten(30, 0.10) + 35 + 0.50 * 100)"
ac("5.4c-ring", "5.4 (c)", "Zuschlagskalkulation", f"selbstkosten({HK_R}, 0.15)", 64.975, 0.0005)
ac("5.4c-halskette", "5.4 (c)", "Zuschlagskalkulation", f"selbstkosten({HK_H}, 0.15)", 135.70, 0.0005)
ac("5.4-hk-abgesetzt", "5.4 (b)", "Zuschlagskalkulation", f"{HK_R} * 3000 + {HK_H} * 2000", 405500, 0.005, "Konsistenz mit der vorgegebenen Basis 405.500 €")

# 5.6 FUNBLADE, Kalkulationssätze AI und AII
for n, a, w, tol in (("ai-einkauf", "zuschlagssatz(199800, 270000)", 0.74, 0.00005), ("ai-montage", "zuschlagssatz(54000, 24000)", 2.25, 0.00005),
                     ("ai-hk-umsatz", "588375 + 199800 + 54000", 842175, 0.005), ("ai-vwvt", "zuschlagssatz(92625, 588375 + 199800 + 54000)", 0.10998, 0.000005),
                     ("aii-einkauf", "zuschlagssatz(199800, 7500)", 26.64, 0.005), ("aii-montage", "zuschlagssatz(54000, 7500)", 7.20, 0.005),
                     ("aii-vwvt", "zuschlagssatz(92625, 7500)", 12.35, 0.005)):
    ac(f"5.6a-{n}", "5.6 (a)", "Zuschlagskalkulation", a, w, tol)
ac("5.6b-allround-ai", "5.6 (b)", "Zuschlagskalkulation", "selbstkosten(materialkosten(32, 0.74) + 2.5 * 13 + 2.5 * 2.25, zuschlagssatz(92625, 842175))", 104.122, 0.001)
ac("5.6b-allround-aii", "5.6 (b)", "Zuschlagskalkulation", "32 + 26.64 + 2.5 * 13 + 7.20 + 12.35", 110.69, 0.005, "Stückschlüsselung verteilt Gemeinkosten unabhängig vom Ressourcenverbrauch")

# 5.7 Schlosshotel, normalisierter Zuschlag
GK57 = "[48000, 72000, 57000, 66000, 61500, 59000], [17800, 21500, 19500, 23800, 21700, 24500]"
ac("5.7a-zuschlag", "5.7 (a)", "Zuschlagskalkulation", f"normalisierter_zuschlag({GK57})", 2.82, 0.005)
ac("5.7b-selbstkosten", "5.7 (b)", "Zuschlagskalkulation", f"5 * 200 * (1 + round(normalisierter_zuschlag({GK57}), 2)) + 2350 + 1680", 7850, 0.005, "Musterlösung rechnet mit gerundetem Zuschlag 2,82")

# 6.2 Tüftel AG: Zuschlagskalkulation vs. Activity-based Costing
for n, a, w in (("mgk", "zuschlagssatz(2250000, 2250000)", 1.0), ("fgk", "zuschlagssatz(1700000, 3400000)", 0.5), ("vwvt", "zuschlagssatz(4800000, 9600000)", 0.5)):
    ac(f"6.2a-zuschlag-{n}", "6.2 (a)", "Zuschlagskalkulation", a, w, 0.00005)
ac("6.2b-angebot-zuschlag-a", "6.2 (b)", "Zuschlagskalkulation", "selbstkosten(materialkosten(400 * 500, 1.0) + 3400000 / 1700 * 16 / 60 * 500 * (1 + 0.5), 0.5)", 1200000, 0.005)
ac("6.2c-angebot-zuschlag-c", "6.2 (c)", "Zuschlagskalkulation", "selbstkosten(materialkosten(450 * 20, 1.0) + 3400000 / 1700 * 30 / 60 * 20 * (1 + 0.5), 0.5)", 72000, 0.005)
for n, a, w in (("c1", "prozesskostensatz(2400000, 100 + 80 + 60)", 10000), ("c2", "prozesskostensatz(2640000, 25 + 5 + 50)", 33000), ("c3", "prozesskostensatz(5100000, 1700)", 3000)):
    ac(f"6.2d-rate-{n}", "6.2 (d)", "Activity-based Costing", a, w, 0.005)
ac("6.2d-fixanteil", "6.2 (d)", "Activity-based Costing", "14400000 - 400 * 2500 - 310 * 2000 - 450 * 1400 - 2400000 - 2640000 - 5100000", 2010000, 0.005, "nicht über Einzelkosten oder Cost Driver verrechnet")
ac("6.2e-angebot-abc-a", "6.2 (e)", "Activity-based Costing", "prozesskosten_angebot(400 * 500, [1, 1, 500 * 16 / 60], [10000, 33000, 3000])", 643000, 0.005, "ein Auftrag, eine Variante")
ac("6.2f-angebot-abc-c", "6.2 (f)", "Activity-based Costing", "prozesskosten_angebot(450 * 20, [1, 2, 20 * 30 / 60], [10000, 33000, 3000])", 115000, 0.005, "Kleinserie: Zuschlagskalkulation (72.000 €) unterschätzt die Kosten")

# 7.1 einstufige Deckungsbeitragsrechnung
ac("7.1-fixkosten", "7.1", "Deckungsbeitragsrechnung", "60 * 2000 + 120 * 3000", 480000, 0.005)
for t, pr, x, e, dba, dbb in (("a", "[4400, 6700]", "[60, 120]", -2580, 149940, 327480), ("b", "[4100, 6900]", "[180, 70]", 120850, 395820, 205030)):
    ac(f"7.1{t}-erfolg", f"7.1 ({t})", "Deckungsbeitragsrechnung", f"periodenerfolg_db({pr}, {x}, [1901, 3971], 480000)", e, 0.005)
    ac(f"7.1{t}-db-a", f"7.1 ({t})", "Deckungsbeitragsrechnung", f"periodenerfolg_db({pr}[:1], {x}[:1], [1901], 0)", dba, 0.005)
    ac(f"7.1{t}-db-b", f"7.1 ({t})", "Deckungsbeitragsrechnung", f"periodenerfolg_db({pr}[1:], {x}[1:], [3971], 0)", dbb, 0.005)

# 7.3 Umsatzkostenverfahren, Voll- und Teilkosten
X73 = (2600, 3350, 6350, 4700, 3050, 2550)
for m, x, v, t in zip(range(1, 7), X73, (46500, 61500, 121500, 88500, 55500, 45500), (36600, 56100, 134100, 91200, 48300, 35300)):
    ac(f"7.3-vollkosten-m{m}", "7.3", "Erfolgsrechnung", f"erfolg_ukv_vollkosten(50, {x}, 24, 14250 + 11250, 4250, 5500)", v, 0.005)
    ac(f"7.3-teilkosten-m{m}", "7.3", "Erfolgsrechnung", f"erfolg_teilkosten(50, {x}, 24, 14250 + 11250 + 5500)", t, 0.005)
ac("7.3-vollkosten-summe", "7.3", "Erfolgsrechnung", " + ".join(f"erfolg_ukv_vollkosten(50, {x}, 24, 25500, 4250, 5500)" for x in X73), 419000, 0.005)
ac("7.3-teilkosten-summe", "7.3", "Erfolgsrechnung", " + ".join(f"erfolg_teilkosten(50, {x}, 24, 31000)" for x in X73), 401600, 0.005,
   "Differenz 17.400 € = Lageraufbau 2.900 Stück × 6 € fixe Herstellkosten")

# 7.4 Seaside AG
ac("7.4a-gkv-vollkosten", "7.4 a)", "Erfolgsrechnung", "erfolg_gkv(30, 4000, 3200, 4, 12000, 10000, True)", 79000, 0.005, "Lagerabbau zu vollen Herstellkosten 7,75 €/Stück")
ac("7.4a-gkv-teilkosten", "7.4 a)", "Erfolgsrechnung", "erfolg_gkv(30, 4000, 3200, 4, 12000, 10000, False)", 82000, 0.005)
ac("7.4b-ukv-vollkosten", "7.4 b)", "Erfolgsrechnung", "erfolg_ukv_vollkosten(30, 4000, 4, 12000, 3200, 10000)", 79000, 0.005, "GKV und UKV liefern bei gleicher Bewertung denselben Erfolg")

# 7.5 mehrstufige Deckungsbeitragsrechnung
DB75 = {"p1": "db1_produkt(5, 8000, 10000, 4000 + 8000, 1200)", "p2": "db1_produkt(2, 10000, 10000, 3000 + 4000, 400)",
        "p3": "db1_produkt(1, 15000, 20000, 3000 + 4000, 300)", "p4": "db1_produkt(3, 5000, 5000, 2000 + 12000, 2000)"}
for (p, a), w in zip(DB75.items(), (29200, 12600, 9450, -1000)):
    ac(f"7.5a-db1-{p}", "7.5 a)", "Deckungsbeitragsrechnung", a, w, 0.005)
ac("7.5a-varhk-abgesetzt-p1", "7.5 a)", "Deckungsbeitragsrechnung", "(4000 + 8000) * 8000 / 10000", 9600, 0.005)
ac("7.5a-varhk-abgesetzt-p3", "7.5 a)", "Deckungsbeitragsrechnung", "(3000 + 4000) * 15000 / 20000", 5250, 0.005)
ac("7.5a-db2-werk-d", "7.5 a)", "Deckungsbeitragsrechnung", f"{DB75['p1']} - 3000", 26200, 0.005)
ac("7.5a-db2-werk-u", "7.5 a)", "Deckungsbeitragsrechnung", f"{DB75['p2']} + {DB75['p3']} + {DB75['p4']} - 5000", 16050, 0.005)
ac("7.5a-nettoerfolg", "7.5 a)", "Deckungsbeitragsrechnung", " + ".join(DB75.values()) + " - 3000 - 5000 - 30000", 12250, 0.005, "P4 hat negativen DB I")

# 8.1 Sadida, Break-even
ac("8.1a-stueck-db", "8.1 (a)", "Break-even", "60 - 20 * 1.2", 36, 0.00005)
ac("8.1a-db-rate", "8.1 (a)", "Break-even", "db_rate(60, 20 * 1.2)", 0.6, 0.00005)
ac("8.1b-be-menge", "8.1 (b)", "Break-even", "break_even_menge(30000000, 60, 24)", 833334, 1.0, "Musterlösung rundet auf ganze Trikots auf")
ac("8.1b-be-tage", "8.1 (b)", "Break-even", "break_even_menge(30000000, 60, 24) / (2800000 / 360)", 107.14, 0.005, "nach 108 Tagen erreicht")
ac("8.1b-zielumsatz", "8.1 (b)", "Break-even", "break_even_umsatz(30000000, 60, 24, 6000000)", 60000000, 0.01)
ac("8.1c-zielmenge", "8.1 (c)", "Break-even", "break_even_menge(30000000, 60, 24, 6000000)", 1000000, 0.005)
ac("8.1c-preis-usd", "8.1 (c)", "Break-even", "60 / 0.8", 75, 0.00005)
ac("8.1d-ohne-sicherung", "8.1 (d)", "Break-even", "1000000 * (60 * 0.8 - 24) - 30000000", -6000000, 0.01, "Währungsrisiko auf der Erlösseite")
ac("8.1d-mit-sicherung", "8.1 (d)", "Break-even", "1000000 * (60 * 0.95 - 24) - 30000000 - 2500000", 500000, 0.01, "Angebot annehmen")
ac("8.1e-zielmenge", "8.1 (e)", "Break-even", "break_even_menge(30000000, 60 * 0.8, 24 * 0.8, 6000000)", 1250000, 0.01, "natürlicher Hedge nur teilweise: Fixkosten bleiben in €")
ac("8.1e-zielumsatz-eur", "8.1 (e)", "Break-even", "break_even_menge(30000000, 60 * 0.8, 24 * 0.8, 6000000) * 60 * 0.8", 60000000, 0.01)
ac("8.1f-zielmenge", "8.1 (f)", "Break-even", "break_even_menge(30000000 + 8000000 * 0.8, 75 * 0.8, 24 * 0.8, 6000000)", 1039216, 1.0, "aufgerundet")

# 8.2 Iglu, Break-even auf Monatsbasis
KF82 = "(130000 + 85000 + 250000 + 360000 + 435000 + 90480 + 180000 + 294000)"
ac("8.2a-db", "8.2 (a)", "Break-even", "24 - (2 + 2 + 2.70 + 0.50)", 16.80, 0.00005)
ac("8.2a-fixkosten", "8.2 (a)", "Break-even", KF82, 1824480, 0.005)
ac("8.2a-be-besucher", "8.2 (a)", "Break-even", f"break_even_menge({KF82}, 24, 7.20)", 108600, 0.005)
ac("8.2a-be-umsatz", "8.2 (a)", "Break-even", f"break_even_umsatz({KF82}, 24, 7.20)", 2606400, 0.01)
ac("8.2c-gewinn-160000", "8.2 (c)", "Break-even", f"160000 * (24 - 7.20) - {KF82}", 863520, 0.01)

# SoSe 9.2 (= Lösung 9.3): Engpassplanung Moha GmbH
DB92, Z92, M92 = "[6, -2, 6, 48, 5]", "[20, 10, 10, 60, 5]", "[300, 600, 800, 400, 4000]"
H92 = "SoSe-Aufgabe 9.2 entspricht Lösung 9.3"
ac("9.2a-kapazitaet", "9.2 (a)", "Engpassplanung", "800 * 60", 48000, 0.00005, H92)
ac("9.2a-bedarf", "9.2 (a)", "Engpassplanung", "300 * 20 + 800 * 10 + 400 * 60 + 4000 * 5", 58000, 0.00005, "Bedarf der Produkte mit positivem DB > Kapazität: wirksamer Engpass")
for p, k, w in (("a", 0, 0.3), ("c", 2, 0.6), ("d", 3, 0.8), ("e", 4, 1.0)):
    ac(f"9.2b-rel-db-{p}", "9.2 (b)", "Engpassplanung", f"{DB92}[{k}] / {Z92}[{k}]", w, 0.00005, H92)
for p, k, w in (("a", 0, 0), ("c", 2, 400), ("d", 3, 400), ("e", 4, 4000)):
    ac(f"9.2b-menge-{p}", "9.2 (b)", "Engpassplanung", f"engpass_programm({DB92}, {Z92}, {M92}, 48000)[{k}]", w, 0.0005, H92)
ac("9.2b-erfolg", "9.2 (b)", "Engpassplanung", f"engpass_erfolg({DB92}, {Z92}, {M92}, 48000, 40000)", 1600, 0.005, H92)
ac("9.2c-rel-db-b", "9.2 (c)", "Engpassplanung", "(32 - 24 - 1) / 10", 0.7, 0.00005, H92)
ac("9.2c-max-auftrag-b", "9.2 (c)", "Engpassplanung", f"engpass_programm([6, 32 - 24 - 1, 6, 48, 5], {Z92}, [300, 1000000000, 800, 400, 4000], 48000)[1]", 400, 0.0005,
   "Auftrag verdrängt nur C (0,6 €/min), nicht D (0,8 €/min)")
ac("9.2d-rel-db-e-eigen", "9.2 (d)", "Engpassplanung", "(11 - 10) / 5", 0.2, 0.00005, "Eigenfertigung spart nur 1 € gegenüber Fremdbezug")
for p, k, w in (("a", 0, 300), ("c", 2, 800), ("d", 3, 400), ("e", 4, 2000)):
    ac(f"9.2d-menge-{p}", "9.2 (d)", "Engpassplanung", f"engpass_programm([6, -2, 6, 48, 11 - 10], {Z92}, {M92}, 48000)[{k}]", w, 0.0005, H92)
ac("9.2d-fremdbezug-e", "9.2 (d)", "Engpassplanung", f"4000 - engpass_programm([6, -2, 6, 48, 11 - 10], {Z92}, {M92}, 48000)[4]", 2000, 0.0005, H92)


def run(cases, konst):
    ns = {k: getattr(R, k) for k in dir(R) if not k.startswith('_')}
    ns.update({"max": max, "min": min, "round": round, "sum": sum})
    ns.update({k: {float(t): v for t, v in d.items()} for k, d in konst.items()})
    fails = []
    for c in cases:
        got = eval(c["ausdruck"], {"__builtins__": {}}, ns)
        exp_ = c["erwartet"]
        ok = (math.isinf(got) and math.isinf(exp_)) or abs(got - exp_) <= c["toleranz"] + 1e-12
        c["berechnet"] = None if math.isinf(got) else round(got, 6)
        if not ok:
            fails.append((c["id"], exp_, got))
    return fails


if __name__ == "__main__":
    fails = run(C, KONST)
    print(f"{len(C)} Testfälle, {len(C) - len(fails)} bestanden, {len(fails)} abweichend")
    for f in fails:
        print("ABWEICHUNG", f)
    out = {"stand": "2026-10-31", "beschreibung": "Testfälle aus Übungsblättern mit Musterlösung; 'ausdruck' wird mit den Funktionen aus referenz.py ausgewertet.",
           "konstanten": {k: {str(t): v for t, v in d.items()} for k, d in KONST.items()},
           "faelle": [{k: (None if (isinstance(v, float) and math.isinf(v)) else v) for k, v in c.items()} | ({"erwartet": "unendlich"} if isinstance(c["erwartet"], float) and math.isinf(c["erwartet"]) else {}) for c in C]}
    json.dump(out, open("testfaelle_uebungen.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
