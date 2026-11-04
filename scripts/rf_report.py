"""Builds results/FUTURES_FACTOR_REPORT.md. NSE Nifty FUTURES only (rf framework). Nothing here is tuned: the two strategies are frozen
(A = trend50 & OI5 rising, chosen before; B = best train+valid factor combo from rf_factor_perm.py). Test (2024+) is only reported.
Run from repo root: python3 scripts/rf_report.py"""
import sys, os; sys.path.insert(0, 'scripts')
import warnings; warnings.filterwarnings('ignore')
import rf as RFM
from rf import *
from factors import _asof
from gates import build_gates

R = RFM.RF(); days = R.days; n = R.n; P = periods(days); X = R.X; Xv = X.values
G = build_gates(R)
L = lambda k: pd.read_csv(os.path.join(DATA, f'{k}.csv'), parse_dates=['date']).set_index('date')['close'].astype(float)
oi_tot = pd.Series(R.oi)
oi5 = lambda s: np.nan_to_num(s.pct_change(5).shift(1).values, nan=1.0)       # shift(1): uses OI up to the PREVIOUS close only
oi_gate = oi5(oi_tot) > 0
G['OI5 rising'] = oi_gate; prem = pd.Series(R.basis * 365 / np.maximum(R.dte, 1)).shift(1).values; G['prem<5%'] = np.nan_to_num(prem, nan=0.0) < 0.05
sma = lambda k: X.rolling(k).mean().values
inr21 = _asof(L('usdinr').pct_change(21) * 100, days).values; us21 = _asof(L('us10y').diff(21), days).values
W_gate = (inr21 < 2.0) & (us21 < 0.25) & (~np.isin(np.array(days.month), [1, 2]))
sigA = ((Xv > sma(50)) & oi_gate) * 1.0; sigB = W_gate * 1.0; bh = np.ones(n)
def run(s, mode='both', interest=True, costx=1.0):
    c0, r0 = RFM.COST, RFM.ROLL; RFM.COST, RFM.ROLL = c0 * costx, r0 * costx
    try: return R.run(s, mode, interest)
    finally: RFM.COST, RFM.ROLL = c0, r0
PN = ['train', 'valid', 'test', 'full']
def M(r): return {p: met(r, *P[p], days) for p in PN}
def cell(m): return f"{m['CAGR']:.1f}% / {m['DD']:.1f}% / {m['Sharpe']:.2f}"
def table(rows, header='Strategy'):
    out = [f"| {header} | Train 2017-21 | Valid 2022-23 | Test 2024-26 | Full |", "|---|---|---|---|---|"]
    for name, r in rows: m = M(r); out.append(f"| {name} | " + " | ".join(cell(m[p]) for p in PN) + " |")
    return "\n".join(out)
md = []; add = md.append
add("# Nifty futures: factors that affect it, and their backtest (train / valid / test, full and regime-wise)\n")
add("Author: Ankit Garg. Research only, not investment advice. **All numbers use real NSE Nifty futures prices** (daily bhavcopy, front month, premium and roll included). No spot-index results are used; the earlier spot 18% result is dropped.\n")
add("Format of every cell: **CAGR / MaxDrawdown / Sharpe**. Periods: Train 2017-04 to 2021-12, Valid 2022-23, Test 2024-01 to 2026-10. Signal decided at 15:00 using only earlier data; fill at the last-30-minute VWAP; cost 0.025% per side plus 0.05% per roll (see section 3 for realistic costs).\n")
add("*Two views of return:* **pure futures P&L** (price change including the premium decay a long pays; no interest) and **total return** (pure P&L plus 6% p.a. on capital, since futures need only margin). The pure view is the honest answer to the carry question; the total view is how idle cash is normally treated.\n")

# ---------------- trials
add("## 1. How many strategies were tried (overfitting accounting)\n")
add("| Search | Futures variants |\n|---|---|\n| Real-futures search `rf_search.py` (signals x sizing x mode) | 378 |\n| Factor permutation search `rf_factor_perm.py` (6 bases x 0-3 of 20 gates x 2 sizings x 2 modes) | 32,424 |\n| Earlier spot-index searches (about 800 gates, not futures; excluded from all numbers) | not counted |\n| **Total futures variants looked at** | **about 32,800** |\n")
add("Picks were made on **train + valid only** (score = the weaker of the two periods' CAGR minus |MaxDD|). Test was never used to choose or change anything. After the picks, ablation and neighbour-threshold runs were done as diagnostics only; they did not change the strategy.\n")
add("Because ~32,800 variants were tried, the best train+valid score is optimistic. Check on test: of the 100 best train+valid variants, the median test CAGR was 3.8% (buy-and-hold futures 0.4%); 87% beat buy-and-hold on test CAGR and 95% had a smaller test drawdown. The single top variant ranks only at the 40th percentile of all variants on test (CAGR minus drawdown). Rank correlation between train+valid and test score is 0.28: real but weak.\n")

# ---------------- the two frozen strategies vs buy and hold
add("## 2. Frozen strategies vs simply holding Nifty futures\n")
add("- **Hold** = buy Nifty futures and keep them (rolling each month).\n- **A: Trend(50) + rising OI**: long when the 15:00 price is above its 50-day average AND total futures open interest rose over the last 5 days (OI known to the previous close). Otherwise flat.\n- **B: Factor-gated**: long unless USD/INR rose >2% in 21 days, OR US 10Y yield rose >=25bp in 21 days, OR it is January/February. Chosen as best of the 32,424 on train+valid.\n")
add("**Total return (futures P&L + 6% interest on capital):**\n"); add(table([('Hold futures', run(bh)), ('A: Trend50 & OI', run(sigA)), ('B: Factor-gated', run(sigB))])); add("")
add("**Pure futures P&L (no interest; includes the premium a long pays):**\n"); add(table([('Hold futures', run(bh, interest=False)), ('A: Trend50 & OI', run(sigA, interest=False)), ('B: Factor-gated', run(sigB, interest=False))])); add("")
add("Reading: in total-return terms both beat holding futures on Sharpe and drawdown in every period (A's CAGR is lower than holding in train, 11.3% vs 16.7%, and higher in valid and test). In pure-price terms holding futures lost money in test (-5.4%), A is slightly negative (-1.8%) and B slightly positive (+1.8%). A cuts drawdown by roughly 60-80% but does not make high returns; B earns more but with a bigger drawdown than A. Neither makes real money from price alone in the test years.\n")

# ---------------- costs
add("## 3. Costs: brokerage, STT, exchange charges, slippage\n")
add("Assumed per futures lot of about Rs 15 lakh notional: brokerage ~Rs 20/order (~0.0013%), STT 0.02% on the sell side (a 0.05% STT is covered by the x1.6 scenario below), exchange charges 0.00183%, SEBI 0.0001%, stamp duty 0.002% on buy, GST 18% on brokerage and exchange charges, slippage 1bp per side (Nifty futures are very liquid). Round trip comes to about **0.048%**, i.e. 0.024% per side, almost exactly the 0.025% per side the model already used. Scenarios: x1 (0.025%/side), x1.6 (0.04%/side: higher STT plus 2bp slippage), x3 (stress).\n")
rows = []
for cx in [1, 1.6, 3]:
    rows.append((f'A costs x{cx}', run(sigA, costx=cx))); rows.append((f'B costs x{cx}', run(sigB, costx=cx)))
rows.append(('Hold futures (1 entry, ~1 roll/month)', run(bh)))
add(table(rows)); add("")
add(f"Trading frequency: A holds {sigA.mean()*100:.0f}% of days, about {np.abs(np.diff(sigA)).sum()/2/((days[-1]-days[0]).days/365.25):.0f} round trips a year; B holds {sigB.mean()*100:.0f}% of days, about {np.abs(np.diff(sigB)).sum()/2/((days[-1]-days[0]).days/365.25):.0f} round trips a year. Low turnover is why costs barely matter; at 3x costs both still beat holding futures on Sharpe and drawdown (A's test CAGR falls to 1.8%).\n")

# ---------------- parameter sweep
add("## 4. Parameter check: is 50 a fluke?\n")
add("Trend(N) AND OI(5-day) rising, total-return view:\n")
rows = [(f'Trend({k}) & OI5', run(((Xv > sma(k)) & oi_gate) * 1.0)) for k in [30, 40, 50, 60, 80, 100, 150]]
add(table(rows)); add("")
add("Same, pure futures P&L:\n"); add(table([(f'Trend({k}) & OI5', run(((Xv > sma(k)) & oi_gate) * 1.0, interest=False)) for k in [30, 40, 50, 60, 80]])); add("")
add("Reading: N = 30 to 150 all give a similar shape (full CAGR 7.4-9.4%, drawdown 7-10% in total-return view), so 50 is not a lucky spike. Honest caveats: in pure futures P&L the test period is negative for every N (-0.5% to -4.5%), and the shorter averages (30, 40) are clearly worse in test than the longer ones, so 50 to 150 are the safer range.\n")

# ---------------- expiry
add("## 5. Expiry effect on OI\n")
fut = pd.read_csv(os.path.join(DATA, 'fut', 'nifty_fut.csv'), parse_dates=['date', 'expiry']).drop_duplicates(['date', 'expiry'])
fm_oi = fut[fut.expiry >= fut.date].sort_values(['date', 'expiry']).groupby('date').oi.first().reindex(days)   # front-month only OI
oi_front_gate = oi5(fm_oi.reset_index(drop=True)) > 0
nxt = np.array([ (R.days[i:][R.expday[i:]][0] - R.days[i]).days if R.expday[i:].any() else 99 for i in range(n)])
expwin = nxt <= 3
agree = (oi_gate == oi_front_gate).mean() * 100; agree_exp = (oi_gate[expwin] == oi_front_gate[expwin]).mean() * 100
frozen = oi_gate.copy()
for i in range(1, n):
    if expwin[i]: frozen[i] = frozen[i - 1]
sigAfront = ((Xv > sma(50)) & oi_front_gate) * 1.0; sigAfreeze = ((Xv > sma(50)) & frozen) * 1.0
add("How handled: the OI used is the **sum of open interest across all live Nifty contracts**, not the front month. When positions roll from the expiring contract to the next one, OI moves between contracts but the sum barely changes, so the roll does not create a fake rise or fall. Checks:\n")
add(f"- Front-month-only OI would be wrong around expiry: it agrees with total-OI on {agree:.0f}% of all days but only {agree_exp:.0f}% on days within 3 days before expiry.\n")
add(table([('A with total OI (used)', run(sigA)), ('A with front-month OI only', run(sigAfront)), ('A with OI gate frozen in last 3 days before expiry', run(sigAfreeze))])); add("")
add("Reading: using total OI (or freezing the gate near expiry) gives the same results; the front-month-only version is the one that is distorted (test CAGR -4.2% instead of +4.2%). Rolls also pay 0.05% in the cost model whenever a position is carried across expiry.\n")

# ---------------- lookahead
add("## 6. Timing: no future data in the signal\n")
add("- Decision is made at 15:00 on day t. The price used is the 15:00 bar close; the position is filled at the last-30-minute VWAP after that.\n- OI for day t is published after close, so the signal uses `OI[t-1]` (OI is shifted one day and the 5-day change is taken on the shifted series). The 5-day change at day t is OI(t-1)/OI(t-6)-1.\n- All macro series (USD/INR, US10Y, DXY, S&P, Brent, VIX) are the latest close **strictly before** day t; FII monthly flows are used only from the next month.\nProof by experiment:\n")
sigCheat = ((Xv > sma(50)) & (np.nan_to_num(oi_tot.pct_change(5).values, nan=1.0) > 0)) * 1.0    # same-day OI = cheating
sigLag2 = ((Xv > sma(50)) & (np.nan_to_num(oi_tot.pct_change(5).shift(2).values, nan=1.0) > 0)) * 1.0
add(table([('A as used (OI lagged 1 day)', run(sigA)), ('A cheating: same-day OI (not allowed)', run(sigCheat)), ('A with OI lagged 2 days', run(sigLag2))])); add("")
add("A leak would make the used version look better than the safer lagged versions. It does not: lag-1 (9.4% full) is about the same as lag-2 (9.3%), and the same-day OI row is not better (6.8%). So the one-day lag is not hiding any advantage, and no future OI is used. The OI series and gates are built from the previous close only.\n")

# ---------------- factors
add("## 7. Factors from the Nifty document: what each one does (standalone, on futures)\n")
add("Each factor is a gate on 'always long futures': allow holding only when the factor is calm. 'Blocked-day return' is the annualised pure-futures return on the days the gate said stay out. **A good factor has a blocked-day return below the allowed-day return.** Train / Valid / Test shown separately.\n")
FAC = [('Rupee weak: USD/INR +2% in 21d', 'rupee21<2%'), ('Rupee weak: +0.3% yesterday', 'rupee1d<0.3%'), ('Dollar index +1.5% in 21d', 'dxy21<1.5%'), ('US 10Y +25bp in 21d', 'us10y21<0.25'),
       ('S&P 500 down >2% in 21d', 'spx21>-2%'), ('S&P 500 below 200DMA', 'spx>sma200'), ('Brent 21d avg >$100', 'brent21avg<100'), ('Brent +5% in 5d', 'brent5<+5%'),
       ('India VIX >=20', 'vix<20'), ('India VIX >=25', 'vix<25'), ('India VIX +8% yesterday', 'vix1d<+8%'), ('FII sold >10k cr last month', 'fii_last_month>-10k'),
       ('FII sold >2 lakh cr in 12m', 'fii_12m>-2L'), ('Nifty P/E >=25', 'pe<25'), ('Jan/Feb seasonality', 'not_Jan/Feb'), ('Korean won weak 2% in 21d', 'krw21<2%'),
       ('Bank Nifty below 50DMA', 'banknifty>sma50'), ('Futures OI falling over 5d', 'OI5 rising'), ('Futures premium >=5% annualised', 'prem<5%')]
rp = run(bh, interest=False)
hdr = "| Factor (caution when…) | Days blocked | Blocked-day ann. return Train / Valid / Test | Allowed-day ann. return Train / Valid / Test | Gated-long (total return) Train / Valid / Test CAGR | Verdict |"
add(hdr); add("|---|---|---|---|---|---|")
ann = lambda x: ((1 + x).prod() ** (252 / max(len(x), 1)) - 1) * 100 if len(x) >= 20 else float('nan')
for lbl, g in FAC:
    gate = np.asarray(G[g], bool); rg = run(gate * 1.0); mg = M(rg)
    bl, al = [], []
    for p in ['train', 'valid', 'test']:
        lo, hi = P[p]; idx = np.arange(lo, hi - 1); x = rp[idx + 1]; gi = gate[idx]
        bl.append(ann(x[~gi])); al.append(ann(x[gi]))
    good = sum(b < a for b, a in zip(bl, al) if not np.isnan(b)); tot = sum(1 for b in bl if not np.isnan(b))
    verdict = 'works in all 3' if good == 3 else ('works in 2 of 3' if good == 2 else ('mixed' if good == 1 else 'does not work'))
    if tot < 3: verdict = 'too few blocked days in some period'
    add(f"| {lbl} | {(~gate).mean()*100:.0f}% | " + " / ".join((f"{b:.0f}%" if not np.isnan(b) else "n/a") for b in bl) + " | " + " / ".join((f"{a:.0f}%" if not np.isnan(a) else "n/a") for a in al) + " | " + " / ".join(f"{mg[p]['CAGR']:.1f}%" for p in ['train', 'valid', 'test']) + f" | {verdict} |")
add("\nBlocked-day returns are noisy where blocked days are few (Brent >$100, VIX >=25, P/E, FII 12m are 'n/a' where a period has under 20 blocked days; the rupee 2% figure in valid is a handful of crisis days). Gated-long CAGR is in the total-return view. 'Works' means blocked-day return < allowed-day return in that period.\n\nHold futures (total return) CAGR for reference: " + " / ".join(f"{M(run(bh))[p]['CAGR']:.1f}%" for p in ['train', 'valid', 'test']) + ". Factors the document called 'no effect' (gold, India 10Y yield, yen, US inflation, expiry week) were not tested as drivers.\n")
add("FII monthly flows: data file ends 27 Jan 2026, so FII gates carry the last value forward after that (stale). P/E file ends 1 Jul 2026. Treat both as less reliable for 2026.\n")

# ---------------- regimes by period
rv = {}
ret = X.pct_change(); dd252 = (X / X.rolling(252, min_periods=60).max() - 1).values; m20 = X.pct_change(20).values; s200 = sma(200)
vix = L('vix').reindex(days).ffill().shift(1).values
def lab(d):
    out = np.full(n, '', dtype=object)
    for k, c in d.items(): out[c] = k
    return out
REG = {'Trend (price vs 200DMA)': lab({'Bull (above)': Xv > s200, 'Bear (below)': Xv <= s200}),
       'Volatility (India VIX)': lab({'Low <15': vix < 15, 'Mid 15-22': (vix >= 15) & (vix < 22), 'High >=22': vix >= 22}),
       'Momentum (20d return)': lab({'Down <-3%': m20 < -0.03, 'Flat': (m20 >= -0.03) & (m20 <= 0.03), 'Up >3%': m20 > 0.03}),
       'Drawdown (from 252d high)': lab({'Near high <5%': dd252 > -0.05, 'Pullback 5-10%': (dd252 <= -0.05) & (dd252 > -0.10), 'Deep >10%': dd252 <= -0.10})}
S = {'Hold': run(bh), 'A': run(sigA), 'B': run(sigB)}
add("## 8. Regime-wise results in Train / Valid / Test / Full\n")
add("Annualised total return % / Sharpe in each market regime (regime known at the decision day; return is the next holding period). Hold = buy-and-hold futures, A = Trend50 & OI, B = factor-gated. `n` = days. '-' = fewer than 20 days. Where a strategy is mostly in cash, its volatility is tiny and the Sharpe is inflated (values like 25 are artefacts; read the return column).\n")
for rn_, la in REG.items():
    add(f"### {rn_}\n"); add("| Regime | Period | n | Hold | A | B |"); add("|---|---|---|---|---|---|")
    for lv in [v for v in REG[rn_] .tolist() if v != ''][:0] or sorted(set(la) - {''}):
        for p in PN:
            lo, hi = P[p]; idx = np.arange(lo, hi - 1); idx = idx[la[idx] == lv]
            if len(idx) < 20: add(f"| {lv} | {p} | {len(idx)} | - | - | - |"); continue
            cells = []
            for sn in ['Hold', 'A', 'B']:
                x = S[sn][idx + 1]; sh = x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
                cells.append(f"{((1+x).prod()**(252/len(x))-1)*100:.1f}% / {sh:.2f}")
            add(f"| {lv} | {p} | {len(idx)} | " + " | ".join(cells) + " |")
    add("")
add("### Calendar year (full-period strategy returns, total return view)\n"); add("| Year | Hold | A | B |"); add("|---|---|---|---|")
for y in range(2017, 2027):
    ix = np.where(np.array(days.year) == y)[0]; ix = ix[ix > 0]
    add(f"| {y} | " + " | ".join(f"{((1+S[s][ix]).prod()-1)*100:.1f}%" for s in ['Hold', 'A', 'B']) + " |")
add("")

add("## 9. Verdict against the checklist\n")
add("1. Futures only: yes, every number above. Spot results are dropped.\n2. Carry: a long pays the premium; it is inside every pure-futures figure. Hold futures made 4.2% a year over the full period in pure terms and lost money in test.\n3. Costs: realistic all-in costs are about the 0.025% per side already modelled; at 3x costs both strategies still beat holding futures.\n4. Versus holding futures: A and B both beat it on Sharpe and drawdown in train, valid and test (total-return view). In pure futures P&L, B beats holding in every period; A does so only on drawdown and Sharpe, and its price-only return in train (4.8%) is below holding (9.9%).\n5. Train / valid / test: shown separately everywhere. Both strategies earn less in test than in train/valid.\n6. Expiry: total OI across contracts is used; front-month-only OI is distorted near expiry.\n7. Timing: OI lagged one day; lagging two days gives the same result and same-day OI is not better, so there is no hidden look-ahead advantage.\n8. Parameters: Trend 30 to 150 behave similarly, not a lucky 50.\n9. Overfitting: about 32,800 futures variants tried; picks on train+valid only; test untouched; top-100 median test CAGR 3.8% vs 0.4% for holding.\n")
add("**Honest limits.** (a) Test (2024 to Oct 2026) is only 2.8 years, with a flat-to-falling Nifty, so it favours any strategy that sits out. (b) Pure-futures test returns for A and B are about -2% to +2% a year; the headline test numbers rely on interest earned on idle capital. (c) B's thresholds come from a document written with the full 2016-26 history in view, so B is less blind than A. (d) Daily data only; execution at VWAP is assumed.\n")
add("**Suggested next step:** paper-trade A (simplest, 2 parameters, smallest drawdown) and B side by side for 2-3 months, with the rules frozen as written here; compare each with simply holding Nifty futures after real costs.\n")
open('results/FUTURES_FACTOR_REPORT.md', 'w').write("\n".join(md)); print('written', len("\n".join(md)))
