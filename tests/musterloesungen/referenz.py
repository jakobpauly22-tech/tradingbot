"""Referenzimplementierung der Formeln aus dem Grundlagenwissen.

Jede Funktion nennt die Wissensdatei, aus der die Formel stammt. Die Funktionen
werden von test_uebungen.py gegen die Musterlösungen der Übungsblätter geprüft.
Konventionen: Zinsen und Renditen als Dezimalzahl (0.05 = 5 %), Zeit in Jahren.
"""
from math import exp, log, sqrt, erf, comb

# ---------------------------------------------------------------- Barwerte (01, 02)

def fv(c0, r, t):
    """Endwert einer heutigen Zahlung. 02 Abschnitt 1."""
    return c0 * (1 + r) ** t


def pv(ct, r, t):
    """Barwert einer Zahlung in t. 02 Abschnitt 1."""
    return ct * (1 + r) ** (-t)


def pv_cashflows(cfs, r=None, curve=None):
    """Barwert eines Zahlungsstroms {t: CF}. Flacher Zins r oder Spot-Kurve {t: r_t}."""
    total = 0.0
    for t, c in cfs.items():
        rate = curve[t] if curve is not None and t != 0 else (r or 0.0)
        total += c * (1 + rate) ** (-t)
    return total


def npv(cfs, r=None, curve=None):
    """Kapitalwert inkl. C0. 01 Abschnitt 1, 02 Abschnitt 1."""
    return pv_cashflows(cfs, r=r, curve=curve)


def spot_from_pv(pv_value, ct, t):
    """Zins, der PV und Zahlung in t verbindet: (C/PV)^(1/t) - 1."""
    return (ct / pv_value) ** (1 / t) - 1


def breakeven_cashflow(cfs, t_unknown, curve):
    """Zahlung in t_unknown, bei der NPV = 0 wird."""
    return -npv(cfs, curve=curve) * (1 + curve[t_unknown]) ** t_unknown


def irr_two_period(c0, c1, c2):
    """Interne Zinsfüße eines Zwei-Perioden-Projekts (quadratische Gleichung in q = 1 + r)."""
    a, b, c = c0, c1, c2  # c0 q^2 + c1 q + c2 = 0
    disc = b * b - 4 * a * c
    roots = sorted(((-b + s * sqrt(disc)) / (2 * a)) for s in (1, -1))
    return [q - 1 for q in roots]


def annuity_pv(a, n, r=None, curve=None):
    """Barwert einer nachschüssigen Annuität. 01 Abschnitt 1, 02 Abschnitt 1."""
    if curve is not None:
        return sum(a * (1 + curve[t]) ** (-t) for t in range(1, n + 1))
    return a / r * (1 - (1 + r) ** (-n))


def perpetuity_pv(a, r, g=0.0):
    """Ewige (wachsende) Rente: A / (r - g), nur für g < r. 01 Abschnitt 1."""
    if g >= r:
        return float('inf')
    return a / (r - g)

# ---------------------------------------------------------------- Rendite und Portfolio (02, 09)

def simple_return(p0, p1, d1=0.0):
    return (p1 + d1 - p0) / p0


def expected_value(values, probs=None):
    probs = probs or [1 / len(values)] * len(values)
    return sum(v * p for v, p in zip(values, probs))


def variance(values, probs=None):
    probs = probs or [1 / len(values)] * len(values)
    m = expected_value(values, probs)
    return sum(p * (v - m) ** 2 for v, p in zip(values, probs))


def value_weights(quantities, prices):
    total = sum(q * p for q, p in zip(quantities, prices))
    return [q * p / total for q, p in zip(quantities, prices)]


def portfolio_return(weights, returns):
    return sum(w * r for w, r in zip(weights, returns))


def portfolio_variance_2(w1, s1, s2, rho):
    """σ²_P = w1²σ1² + w2²σ2² + 2w1w2ρσ1σ2. 02 Abschnitt 2."""
    w2 = 1 - w1
    return w1 ** 2 * s1 ** 2 + w2 ** 2 * s2 ** 2 + 2 * w1 * w2 * rho * s1 * s2


def mvp_weight_2(s1, s2, rho):
    """Gewicht von Anlage 1 im Minimum-Varianz-Portfolio. 02 Abschnitt 2."""
    cov = rho * s1 * s2
    return (s2 ** 2 - cov) / (s1 ** 2 + s2 ** 2 - 2 * cov)


def cml_sigma_for_target(target, mu_t, sigma_t, rf):
    """Risiko auf der Kapitalmarktlinie für eine Zielrendite; Gewicht im riskanten Portfolio."""
    w = (target - rf) / (mu_t - rf)
    return w * sigma_t, w

# ---------------------------------------------------------------- CAPM, APT, Performance (01, 02, 04, 09)

def beta(cov_im, var_m):
    return cov_im / var_m


def capm_return(rf, beta_i, mrp):
    """E[r] = rf + β · Marktrisikoprämie. 01 Abschnitt 6, 02 Abschnitt 3."""
    return rf + beta_i * mrp


def systematic_share(beta_i, sigma_m, sigma_i):
    """Anteil des systematischen Risikos: β²σ²_M / σ²_i."""
    return beta_i ** 2 * sigma_m ** 2 / sigma_i ** 2


def sharpe_ratio(r, rf, sigma):
    return (r - rf) / sigma


def capm_alpha(r, rf, beta_i, rm):
    return r - (rf + beta_i * (rm - rf))


def apt_alpha(r, rf, betas, premia):
    """Alpha im Mehrfaktormodell; premia sind Faktorprämien (bereits über rf)."""
    return r - (rf + sum(b * p for b, p in zip(betas, premia)))

# ---------------------------------------------------------------- Aktienbewertung (01, 02)

def gordon_price(d1, k, g):
    return d1 / (k - g)


def ddm_from_earnings(eps0, roe, b, k):
    """Kurs aus Gewinn, ROE und Thesaurierungsquote b: g = ROE·b, D1 = EPS0(1+g)(1-b)."""
    g = roe * b
    d1 = eps0 * (1 + g) * (1 - b)
    return d1 / (k - g)


def pvgo(price, eps, k):
    return price - eps / k


def implied_growth(p0, d0, k):
    """g aus P0 = D0(1+g)/(k-g)."""
    return (p0 * k - d0) / (p0 + d0)


def two_stage_ddm(d0, g1, n1, g2, k):
    price, d = 0.0, d0
    for t in range(1, n1 + 1):
        d *= 1 + g1
        price += d / (1 + k) ** t
    terminal = d * (1 + g2) / (k - g2)
    return price + terminal / (1 + k) ** n1


def free_cash_flow(ebit, tax, depreciation, capex, delta_nwc):
    """FCF = EBIT(1 − t) + Abschreibungen − Capex − ΔNWC. 01 Abschnitt 9."""
    return ebit * (1 - tax) + depreciation - capex - delta_nwc

# ---------------------------------------------------------------- Kapitalstruktur (01)

def wacc(e, d, r_e, r_d, tax=0.0):
    v = e + d
    return e / v * r_e + d / v * r_d * (1 - tax)


def equity_beta_from_asset(beta_asset, e, d, beta_debt=0.0):
    """β_A = E/V·β_E + D/V·β_D, nach β_E aufgelöst."""
    v = e + d
    return (beta_asset - d / v * beta_debt) * v / e


def tax_shield_value(interest, tax, r):
    return interest * tax / (1 + r)

# ---------------------------------------------------------------- Anleihen und Duration (02)

def bond_cashflows(face, coupon_rate, maturity, first=1.0, freq=1):
    times = [first + i / freq for i in range(int(round((maturity - first) * freq)) + 1)]
    cfs = {t: face * coupon_rate / freq for t in times}
    cfs[times[-1]] += face
    return cfs


def price_flat(cfs, y):
    return sum(c * (1 + y) ** (-t) for t, c in cfs.items())


def macaulay_duration(cfs, y):
    p = price_flat(cfs, y)
    return sum(t * c * (1 + y) ** (-t) for t, c in cfs.items()) / p


def modified_duration(cfs, y):
    return macaulay_duration(cfs, y) / (1 + y)


def convexity(cfs, y):
    """Relative Konvexität Σ t(t+1)·CF/(1+y)^(t+2) / P (Konvention Maurer)."""
    p = price_flat(cfs, y)
    return sum(t * (t + 1) * c * (1 + y) ** (-(t + 2)) for t, c in cfs.items()) / p


def rel_change_duration(cfs, y, dy):
    return -modified_duration(cfs, y) * dy


def rel_change_dur_conv(cfs, y, dy):
    return -modified_duration(cfs, y) * dy + 0.5 * convexity(cfs, y) * dy ** 2


def abs_change_duration(cfs, y, dy):
    return price_flat(cfs, y) * rel_change_duration(cfs, y, dy)


def abs_change_dur_conv(cfs, y, dy):
    """Absolute Preisänderung mit Duration und Konvexität: P · (−D_mod·Δy + ½·C·Δy²)."""
    return price_flat(cfs, y) * rel_change_dur_conv(cfs, y, dy)


def exact_change(cfs, y, dy):
    return price_flat(cfs, y + dy) - price_flat(cfs, y)


def ytm(cfs, price, lo=-0.5, hi=1.0):
    for _ in range(200):
        mid = (lo + hi) / 2
        if price_flat(cfs, mid) > price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def forward_rate(s_short, n_short, s_long, n_long):
    return ((1 + s_long) ** n_long / (1 + s_short) ** n_short) ** (1 / (n_long - n_short)) - 1


def accrued_interest(face, coupon_rate, freq, days_since, days_period):
    return face * coupon_rate / freq * days_since / days_period


def duration_match_weight(d_target, d_a, d_b):
    """Gewicht in A, sodass w·D_A + (1−w)·D_B = D_Ziel."""
    return (d_target - d_b) / (d_a - d_b)

# ---------------------------------------------------------------- Forwards, Futures, Hedging (03, 04)

def forward_price(s0, r, t, div_fv=0.0, continuous=False, q=0.0):
    """Cost-of-Carry-Preis. Diskret: S0(1+r)^T − FV(Dividenden); stetig: S0·e^{(r−q)T}."""
    if continuous:
        return s0 * exp((r - q) * t)
    return s0 * (1 + r) ** t - div_fv


def forward_value_long(s_t, f0, r, remaining):
    """Wert eines laufenden Long-Forwards ohne Erträge: S_t − F0/(1+r)^(T−t)."""
    return s_t - f0 * (1 + r) ** (-remaining)


def hedge_contracts(beta_pf, value, contract_size, futures_price):
    return beta_pf * value / (contract_size * futures_price)


def hedge_beta(rho, sigma_s, sigma_f):
    return rho * sigma_s / sigma_f


def futures_leverage(contract_size, futures_price, margin):
    return contract_size * futures_price / margin

# ---------------------------------------------------------------- Optionen (03)

def norm_cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def binomial_replication(s0, u, d, r, payoff_u, payoff_d):
    """Ein-Perioden-Replikation: Delta, Anlage B, Preis."""
    su, sd = s0 * u, s0 * d
    delta = (payoff_u - payoff_d) / (su - sd)
    b = (payoff_u - delta * su) / (1 + r)
    return delta, b, delta * s0 + b


def binomial_price(s0, u, d, r, k, n, kind='call', american=False):
    """n-Perioden-Binomialbaum (Cox-Ross-Rubinstein), europäisch oder amerikanisch."""
    q = ((1 + r) - d) / (u - d)
    pay = (lambda s: max(s - k, 0.0)) if kind == 'call' else (lambda s: max(k - s, 0.0))
    values = [pay(s0 * u ** j * d ** (n - j)) for j in range(n + 1)]
    for step in range(n - 1, -1, -1):
        new = []
        for j in range(step + 1):
            cont = (q * values[j + 1] + (1 - q) * values[j]) / (1 + r)
            new.append(max(cont, pay(s0 * u ** j * d ** (step - j))) if american else cont)
        values = new
    return values[0]


def risk_neutral_q(u, d, r):
    return ((1 + r) - d) / (u - d)


def black_scholes_call(s, k, r, sigma, t):
    d1 = (log(s / k) + (r + 0.5 * sigma ** 2) * t) / (sigma * sqrt(t))
    d2 = d1 - sigma * sqrt(t)
    return s * norm_cdf(d1) - k * exp(-r * t) * norm_cdf(d2)


def put_call_parity_put(call, s0, k, r, t=1.0):
    return call - s0 + k * (1 + r) ** (-t)


# ---------------------------------------------------------------- Kosten- und Erlösrechnung (08 Abschnitt 4)
# Quelle der Verfahren: BACC / Accounting 1, Kapitel 3 bis 9. Geldbeträge in €, Mengen in Stück.

def lagerbewertung(anfangsbestand, bewegungen, methode='fifo'):
    """Permanente FIFO- oder LIFO-Bewertung. 08 §4 Kostenartenrechnung.
    anfangsbestand: [[menge, preis], ...] (älteste Schicht zuerst);
    bewegungen: [menge, preis] = Zugang, [-menge] = Abgang, in zeitlicher Reihenfolge.
    Liefert {'abgaenge': [Wert je Abgang], 'endbestand': Wert}."""
    schichten = [list(s) for s in anfangsbestand]
    abgaenge = []
    for b in bewegungen:
        if b[0] > 0:
            schichten.append([b[0], b[1]])
            continue
        rest, wert = -b[0], 0.0
        while rest > 1e-9:
            s = schichten[0] if methode == 'fifo' else schichten[-1]
            nimm = min(rest, s[0])
            wert += nimm * s[1]
            s[0] -= nimm
            rest -= nimm
            if s[0] <= 1e-9:
                schichten.remove(s)
        abgaenge.append(wert)
    return {'abgaenge': abgaenge, 'endbestand': sum(m * p for m, p in schichten)}


def afa_linear(ak, rest, n):
    """Lineare Abschreibung je Periode: (AK − Restwert)/n. 08 §4."""
    return (ak - rest) / n


def afa_geo_satz(ak, rest, n):
    """Satz der geometrisch-degressiven Abschreibung: 1 − (Restwert/AK)^(1/n). 08 §4."""
    return 1 - (rest / ak) ** (1 / n)


def afa_geo(ak, rest, n, t, satz=None):
    """Geometrisch-degressive Abschreibung in Periode t (optional mit gerundetem Satz)."""
    s = afa_geo_satz(ak, rest, n) if satz is None else satz
    return ak * (1 - s) ** (t - 1) * s


def buchwert_geo(ak, rest, n, t, satz=None):
    """Restbuchwert nach Periode t bei geometrisch-degressiver Abschreibung."""
    s = afa_geo_satz(ak, rest, n) if satz is None else satz
    return ak * (1 - s) ** t


def afa_leistung(ak, rest, leistungen, t):
    """Leistungsabhängige Abschreibung in Periode t (t ab 1): (AK − Restwert)·x_t/Σx."""
    return (ak - rest) * leistungen[t - 1] / sum(leistungen)


def restwert_linear(p, l, n, t):
    """Restwert nach t Jahren (t auch gebrochen, z.B. 14/12) bei linearer Abschreibung von P auf L."""
    return p - (p - l) * t / n


def durchschnittswert_linear(p, l, n, t):
    """Durchschnittlich gebundenes Kapital im Jahr t: Mittel aus Restwert am Jahresanfang und -ende."""
    return (restwert_linear(p, l, n, t - 1) + restwert_linear(p, l, n, t)) / 2


def kalk_zinsen_restwert(p, l, n, t, i):
    """Kalkulatorische Zinsen im Jahr t nach dem Restwertverfahren: i · Durchschnittswert des Jahres t."""
    return i * durchschnittswert_linear(p, l, n, t)


def kalk_zinsen_durchschnitt(p, l, i):
    """Kalkulatorische Zinsen je Jahr nach dem Durchschnittsverfahren: i · (P + L)/2."""
    return i * (p + l) / 2


def bilanz_mittel(werte_vorjahr, werte_jahr):
    """Durchschnittswert einer Gruppe von Bilanzposten: (Σ Vorjahr + Σ Jahr)/2."""
    return (sum(werte_vorjahr) + sum(werte_jahr)) / 2


def kalk_zinsen_kapital(bnv, abzugskapital, i):
    """Kalkulatorische Zinsen = i · (betriebsnotwendiges Vermögen − Abzugskapital). 08 §4."""
    return i * (bnv - abzugskapital)


def schluesselung(betrag, schluessel):
    """Verteilt einen Gemeinkostenbetrag proportional zu den Schlüsselgrößen (BAB, Primärkosten)."""
    s = sum(schluessel)
    return [betrag * x / s for x in schluessel]


def bab_primaer(verteilungen, direkt=None):
    """Primäre Gemeinkosten je Kostenstelle: Σ der geschlüsselten Kostenarten + direkt zugeordnete Kosten.
    verteilungen: [[betrag, [schlüssel je Kostenstelle]], ...]."""
    n = len(verteilungen[0][1])
    summe = list(direkt) if direkt else [0.0] * n
    for betrag, schl in verteilungen:
        for j, v in enumerate(schluesselung(betrag, schl)):
            summe[j] += v
    return summe


def _gauss(a, b):
    n = len(b)
    m = [list(map(float, a[i])) + [float(b[i])] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c and m[r][c] != 0:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def _marktanteil(lief, output, i):
    if not output or output[i] in (None, 0):
        return 0.0
    return output[i] - sum(lief[i][j] for j in range(len(lief)) if j != i)


def ibl_gleichung(primaer, lief, output=None):
    """Gleichungsverfahren der innerbetrieblichen Leistungsverrechnung. 08 §4 Kostenstellenrechnung.
    lief[i][j]: Leistungseinheiten von Stelle i an Stelle j; output[i]: Gesamtleistung von i
    (nötig, wenn i auch an den Markt liefert; sonst Zeilensumme). Liefert die Gesamtkosten GK_i
    nach Empfang aller Leistungen: GK_i = primär_i + Σ_j GK_j · lief[j][i]/X_j."""
    n = len(primaer)
    x = [(output[i] if output and output[i] else sum(lief[i][j] for j in range(n) if j != i)) for i in range(n)]
    a = [[(1.0 if i == j else 0.0) - (lief[j][i] / x[j] if x[j] and j != i else 0.0) for j in range(n)] for i in range(n)]
    return _gauss(a, primaer)


def ibl_verrechnungspreise(primaer, lief, output=None):
    """Verrechnungspreis je Leistungseinheit: k_i = GK_i / X_i (Gleichungsverfahren)."""
    n = len(primaer)
    gk = ibl_gleichung(primaer, lief, output)
    x = [(output[i] if output and output[i] else sum(lief[i][j] for j in range(n) if j != i)) for i in range(n)]
    return [gk[i] / x[i] if x[i] else None for i in range(n)]


def ibl_endkosten(primaer, lief, output=None, verfahren='gleichung', vorstellen=None):
    """Endkosten je Kostenstelle nach innerbetrieblicher Leistungsverrechnung.
    verfahren: 'gleichung', 'block' (nur Leistungen an Endkostenstellen zählen) oder
    'treppe' (Vorkostenstellen in der Reihenfolge vorstellen; Leistungen an bereits
    abgerechnete Stellen werden ignoriert). Liefert die verbleibenden Kosten je Stelle;
    Stellen, die ganz an andere liefern, haben Endkosten 0."""
    n = len(primaer)
    if verfahren == 'gleichung':
        gk = ibl_gleichung(primaer, lief, output)
        res = []
        for i in range(n):
            x = output[i] if output and output[i] else sum(lief[i][j] for j in range(n) if j != i)
            abgabe = sum(lief[i][j] for j in range(n) if j != i)
            res.append(gk[i] * (1 - abgabe / x) if x else gk[i])
        return res
    kosten = list(map(float, primaer))
    vor = list(vorstellen)
    erledigt = set()
    for i in vor:
        if verfahren == 'block':
            empf = [j for j in range(n) if j not in vor]
        else:
            empf = [j for j in range(n) if j != i and j not in erledigt]
        markt = _marktanteil(lief, output, i)
        basis = sum(lief[i][j] for j in empf) + markt
        betrag = kosten[i]
        for j in empf:
            kosten[j] += betrag * lief[i][j] / basis
        kosten[i] = betrag * markt / basis
        erledigt.add(i)
    return kosten


def zuschlagssatz(gemeinkosten, basis):
    """Gemeinkostenzuschlagssatz = Gemeinkosten / Zuschlagsbasis (als Dezimalzahl oder €/Einheit)."""
    return gemeinkosten / basis


def normalisierter_zuschlag(gemeinkosten, basen):
    """Normalisierter Zuschlagssatz über mehrere Perioden: Σ Gemeinkosten / Σ Zuschlagsbasen."""
    return sum(gemeinkosten) / sum(basen)


def materialkosten(mek, mgk_satz):
    """Materialkosten = MEK · (1 + MGK-Zuschlag)."""
    return mek * (1 + mgk_satz)


def selbstkosten(herstellkosten, vw_satz=0.0, vt_satz=0.0, sondereinzelkosten=0.0):
    """Selbstkosten = HK · (1 + Verwaltungs- + Vertriebszuschlag) + Sondereinzelkosten des Vertriebs."""
    return herstellkosten * (1 + vw_satz + vt_satz) + sondereinzelkosten


def stueckkosten_division(einzelkosten_stueck, gemeinkosten, menge):
    """Einstufige Divisionskalkulation mit Einzelkosten je Stück und periodischen Gemeinkosten."""
    return einzelkosten_stueck + gemeinkosten / menge


def prozesskostensatz(prozesskosten, driver_menge):
    """Activity-based Costing: Kosten je Einheit des Kostentreibers."""
    return prozesskosten / driver_menge


def prozesskosten_angebot(einzelkosten, driver_mengen, saetze):
    """ABC-Kalkulation eines Auftrags: Einzelkosten + Σ Treibermenge · Prozesskostensatz."""
    return einzelkosten + sum(m * s for m, s in zip(driver_mengen, saetze))


def periodenerfolg_db(preise, mengen, kv, fixkosten):
    """Einstufige Deckungsbeitragsrechnung: Σ (p − k_v) · x − K_f. 08 §4."""
    return sum((p - k) * x for p, x, k in zip(preise, mengen, kv)) - fixkosten


def erfolg_ukv_vollkosten(p, x_abs, kv_herst, kf_herst, x_prod, kf_vwvt, kv_vwvt=0.0):
    """Umsatzkostenverfahren auf Vollkostenbasis: abgesetzte Menge zu vollen Stück-Herstellkosten
    (fixe Herstellkosten auf die Produktionsmenge verteilt), Verwaltung/Vertrieb als Periodenkosten."""
    return x_abs * (p - kv_herst - kv_vwvt - kf_herst / x_prod) - kf_vwvt


def erfolg_teilkosten(p, x_abs, kv, kf):
    """Teilkostenrechnung (UKV oder GKV): DB der abgesetzten Menge − alle Fixkosten der Periode."""
    return x_abs * (p - kv) - kf


def erfolg_gkv(p, x_abs, x_prod, kv, kf_herst, kf_vwvt, vollkosten=True):
    """Gesamtkostenverfahren: Erlöse + Bestandsveränderung − alle Kosten der Periode.
    Bestandsveränderung zu Herstellkosten je Stück der Periode (voll oder variabel)."""
    hk = kv + (kf_herst / x_prod if vollkosten else 0.0)
    return p * x_abs + (x_prod - x_abs) * hk - (kv * x_prod + kf_herst + kf_vwvt)


def db1_produkt(preis, x_abs, x_herst, var_herstkosten_periode, var_vertrieb):
    """Deckungsbeitrag I eines Produkts (mehrstufige DB-Rechnung): Erlöse − variable Herstellkosten
    der abgesetzten Menge − variable Vertriebskosten."""
    return preis * x_abs - var_herstkosten_periode * x_abs / x_herst - var_vertrieb


def break_even_menge(kf, p, kv, zielgewinn=0.0):
    """Break-even- bzw. Zielgewinn-Menge: (K_f + G)/(p − k_v). 08 §4."""
    return (kf + zielgewinn) / (p - kv)


def db_rate(p, kv):
    """Deckungsbeitragsrate (p − k_v)/p."""
    return (p - kv) / p


def break_even_umsatz(kf, p, kv, zielgewinn=0.0):
    """Break-even- bzw. Zielumsatz: (K_f + G)/DB-Rate."""
    return (kf + zielgewinn) / db_rate(p, kv)


def engpass_programm(db, zeit, max_menge, kapazitaet):
    """Optimales Produktionsprogramm bei einem Engpass: Rangfolge nach relativem Deckungsbeitrag
    db/zeit, nur Produkte mit positivem DB. Liefert die Mengen je Produkt. 08 §4."""
    reihen = sorted([i for i in range(len(db)) if db[i] > 0], key=lambda i: -db[i] / zeit[i])
    menge, frei = [0.0] * len(db), float(kapazitaet)
    for i in reihen:
        menge[i] = min(max_menge[i], frei / zeit[i])
        frei -= menge[i] * zeit[i]
    return menge


def engpass_erfolg(db, zeit, max_menge, kapazitaet, fixkosten=0.0):
    """Periodenerfolg des optimalen Engpassprogramms."""
    return sum(d * x for d, x in zip(db, engpass_programm(db, zeit, max_menge, kapazitaet))) - fixkosten
