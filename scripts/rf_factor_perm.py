"""Factor-permutation search on REAL NSE Nifty futures (rf framework).
Factors come from the 'Nifty 50: What Moves It' document (FII flows, rupee, dollar, US10Y, S&P, crude, VIX, valuation, seasonality,
Asian FX) plus futures OI / premium. Every gate is an ALLOW flag known before the 15:00 decision (see gates.py / factors.py).
Position = base trend signal AND gate_1 AND ... AND gate_k (k = 0..3), x sizing. Mode 'both' (hold close->close) or 'night'.
Selection uses TRAIN+VALID only (score = min over the two periods of CAGR-|DD| in the total-return view);
TEST (2024+) is reported afterwards and never used to choose. Also: yearly walk-forward of the whole search, a
multiple-testing check (where does the chosen combo sit among all combos on test?), then full + regime-wise backtest.
Usage: python3 scripts/rf_factor_perm.py   (from repo root)"""
import sys, os, itertools, time, pickle
sys.path.insert(0, 'scripts')
import warnings; warnings.filterwarnings('ignore')
from rf import *
from gates import build_gates

t0 = time.time()
R = RF(); days = R.days; n = R.n; P = periods(days); X = R.X; Xv = X.values
G = build_gates(R)                                                   # ~80 allow-gates, all lagged (no lookahead)
oi_chg = pd.Series(R.oi).pct_change(5).shift(1).values
prem = pd.Series(R.basis * 365 / np.maximum(R.dte, 1)).shift(1).values
G['OI5 rising'] = np.nan_to_num(oi_chg, nan=1.0) > 0
G['prem<5%'] = np.nan_to_num(prem, nan=0.0) < 0.05

# curated pool: one or two thresholds per factor family named in the document
POOL = ['OI5 rising', 'prem<5%', 'vix<20', 'vix<25', 'vix1d<+8%', 'vix5d<+10%', 'rupee21<2%', 'rupee1d<0.3%', 'dxy21<1.5%', 'us10y21<0.25',
        'spx21>-2%', 'spx>sma200', 'brent21avg<100', 'brent5<+5%', 'fii_last_month>-10k', 'fii_12m>-2L', 'pe<25', 'not_Jan/Feb',
        'krw21<2%', 'banknifty>sma50']
POOL = [g for g in POOL if g in G]
GF = {g: G[g].astype(float) for g in POOL}

sma = lambda k: X.rolling(k).mean().values
mom = lambda k: X.pct_change(k).values
BASES = {
    'always long': np.ones(n),
    'trend50': (Xv > sma(50)) * 1.0, 'trend100': (Xv > sma(100)) * 1.0, 'trend200': (Xv > sma(200)) * 1.0,
    'supertrend15m': (R.st15 == 1) * 1.0, 'mom60>0': (mom(60) > 0) * 1.0,
}
rv20 = (X.pct_change().rolling(20).std() * np.sqrt(252)).values
SIZES = {'full': np.ones(n), 'volT15': np.nan_to_num(np.minimum(1, 0.15 / np.maximum(rv20, 0.05)), nan=1.0)}
MODES = ['both', 'night']

def score(r_tv):  # selection score on train+valid only: the weaker of the two periods' (CAGR-|DD|)
    return min(met(r_tv, *P['train'], days)['J'], met(r_tv, *P['valid'], days)['J'])

combos = []
for bn in BASES:
    for k in range(0, 4):
        for gs in itertools.combinations(POOL, k):
            combos.append((bn, gs))
print(f'{len(POOL)} gates, {len(BASES)} bases, {len(combos)} base x gate-sets; x {len(SIZES)} sizes x {len(MODES)} modes = {len(combos)*len(SIZES)*len(MODES)} variants')

rows = []
for bn, gs in combos:
    sig = BASES[bn].copy()
    for g in gs: sig = sig * GF[g]
    for zn, z in SIZES.items():
        pos = sig * z
        for mode in MODES:
            r_tv = R.run(pos, mode, True)
            m = {k: met(r_tv, *P[k], days) for k in P}
            rows.append(dict(base=bn, gates=gs, size=zn, mode=mode, tv=m, sel=score(r_tv), ng=len(gs), expo=float((sig[:-1] > 0).mean())))
print(f'evaluated in {time.time()-t0:.0f}s')

bh_r = R.run(np.ones(n), 'both', True); bh = {k: met(bh_r, *P[k], days) for k in P}
fm = lambda m: ' | '.join(f'{k} {m[k]["CAGR"]:5.1f}/{m[k]["DD"]:6.1f}/{m[k]["Sharpe"]:4.2f}' for k in ['train', 'valid', 'test', 'full'])
nm = lambda r: f"{r['base']}{(' & ' + ' & '.join(r['gates'])) if r['gates'] else ''} [{r['size']},{r['mode']}]"
print('\nBUY&HOLD futures (total return = futures P&L + 6% interest). CAGR/MaxDD/Sharpe:\n  ', fm(bh))

rows.sort(key=lambda r: -r['sel'])
print('\n=== TOP 15 by train+valid score (test shown only for information) ===')
for r in rows[:15]: print(f"{nm(r):95s}", fm(r['tv']))

# ---- the same search restricted by number of gates: does adding factors help OUT of sample?
print('\n=== Does adding factors help? best-by-train+valid for each gate count (test is out-of-sample) ===')
for k in range(0, 4):
    sub = [r for r in rows if r['ng'] == k]; b = sub[0]
    ts = np.array([r['tv']['test']['J'] for r in sub]); print(f"k={k}: n={len(sub):6d}  best: {nm(b)[:80]:80s} test {b['tv']['test']['CAGR']:5.1f}/{b['tv']['test']['DD']:6.1f}/{b['tv']['test']['Sharpe']:4.2f} | median test J of all k={k}: {np.median(ts):5.1f}")

# ---- how often does a gate appear in the top 100 (train+valid), and what is the test performance of those top 100?
from collections import Counter
cnt = Counter(g for r in rows[:100] for g in r['gates']); print('\nGate frequency in top-100 by train+valid:', cnt.most_common(10))
top100 = rows[:100]
print(f"Top-100 (picked on train+valid): median test CAGR {np.median([r['tv']['test']['CAGR'] for r in top100]):.1f}, median test DD {np.median([r['tv']['test']['DD'] for r in top100]):.1f}, "
      f"share beating B&H test CAGR {np.mean([r['tv']['test']['CAGR']>bh['test']['CAGR'] for r in top100])*100:.0f}%, share with better test DD {np.mean([r['tv']['test']['DD']>bh['test']['DD'] for r in top100])*100:.0f}%")
tsel = np.array([r['sel'] for r in rows]); tte = np.array([r['tv']['test']['J'] for r in rows])
print('Spearman(train+valid score, test J) over all variants:', round(pd.Series(tsel).rank().corr(pd.Series(tte).rank()), 3))

# ---- choose: best train+valid score, but require >=1 gate to count as "factor-introduced"; also report best 0-gate
best_any = rows[0]; best_f = [r for r in rows if r['ng'] >= 1][0]
chosen = best_any
print('\nCHOSEN (best train+valid, any gate count):', nm(chosen)); print('   ', fm(chosen['tv']))
print('BEST WITH >=1 FACTOR GATE:', nm(best_f)); print('   ', fm(best_f['tv']))
pct = (tte < chosen['tv']['test']['J']).mean() * 100
print(f"chosen combo's test J ranks at the {pct:.0f}th percentile of all {len(rows)} variants")

# ---- walk-forward: each year re-pick the best (train-to-date) variant among a prefiltered 3000, apply next year
print('\n=== YEARLY WALK-FORWARD (re-pick on all prior years) ===')
sig_cache = {}
def posof(r):
    sig = BASES[r['base']].copy()
    for g in r['gates']: sig = sig * GF[g]
    return sig * SIZES[r['size']]
cand = rows[:1500] + [r for r in rows if r['ng'] <= 1]; seen = set(); cand = [r for r in cand if not ((nm(r)) in seen or seen.add(nm(r)))]
Rcache = {nm(r): R.run(posof(r), r['mode'], True) for r in cand}
oos, od = [], []
for Y in range(2021, 2027):
    lo_tr = np.searchsorted(days, pd.Timestamp('2017-04-01')); hi_tr = np.searchsorted(days, pd.Timestamp(f'{Y}-01-01'))
    mid = np.searchsorted(days, pd.Timestamp(f'{Y-2}-01-01')) if Y - 2 >= 2018 else lo_tr
    def wscore(r):
        x = Rcache[nm(r)]; a = met(x, lo_tr, mid if mid > lo_tr + 200 else (lo_tr + hi_tr) // 2, days)['J']; b = met(x, mid if mid > lo_tr + 200 else (lo_tr + hi_tr) // 2, hi_tr, days)['J']
        return min(a, b)
    pk = max(cand, key=wscore); lo = hi_tr; hi = np.searchsorted(days, pd.Timestamp(f'{Y}-12-31'), side='right')
    x = Rcache[nm(pk)][lo:hi]; oos.append(x); od.append(days[lo:hi])
    print(f"  WF {Y}: {nm(pk)[:90]:90s} OOS {((np.prod(1+x)-1)*100):6.1f}%  (B&H {((np.prod(1+bh_r[lo:hi])-1)*100):6.1f}%)")
x = np.concatenate(oos); eq = np.cumprod(1 + x); yrs = (np.concatenate([np.array(a) for a in od])[-1] - od[0][0]).days / 365.25
xb = np.concatenate([bh_r[np.searchsorted(days, pd.Timestamp(f'{Y}-01-01')):np.searchsorted(days, pd.Timestamp(f'{Y}-12-31'), side='right')] for Y in range(2021, 2027)]); eb = np.cumprod(1 + xb)
print(f"WALK-FORWARD OOS 2021-26: CAGR {(eq[-1]**(1/yrs)-1)*100:5.1f}%  MaxDD {((eq/np.maximum.accumulate(eq)-1).min()*100):6.1f}%  Sharpe {x.mean()/x.std()*np.sqrt(252):4.2f}  | B&H {(eb[-1]**(1/yrs)-1)*100:5.1f}%  {((eb/np.maximum.accumulate(eb)-1).min()*100):6.1f}%  {xb.mean()/xb.std()*np.sqrt(252):4.2f}")

# ---- regime-wise backtest of chosen vs best-with-factor vs previous champion vs B&H
reg_defs = {}
ret = X.pct_change(); dd252 = (X / X.rolling(252, min_periods=60).max() - 1).values; vixs = G['vix<20']  # placeholder to ensure data
vix = pd.read_csv(os.path.join(DATA, 'vix.csv'), parse_dates=['date']).set_index('date')['close'].astype(float).reindex(days).ffill().shift(1).values
m20 = mom(20); s200 = sma(200)
def lab(cond_dict):
    out = np.full(n, '', dtype=object)
    for k, c in cond_dict.items(): out[c] = k
    return out
reg_defs['Trend (vs 200DMA)'] = lab({'Bull': Xv > s200, 'Bear': Xv <= s200})
reg_defs['Volatility (India VIX)'] = lab({'Low<15': vix < 15, 'Mid15-22': (vix >= 15) & (vix < 22), 'High>=22': vix >= 22})
reg_defs['Momentum (20d)'] = lab({'Down<-3%': m20 < -0.03, 'Flat': (m20 >= -0.03) & (m20 <= 0.03), 'Up>3%': m20 > 0.03})
reg_defs['Drawdown (vs 252d high)'] = lab({'Near-high<5%': dd252 > -0.05, 'Pullback5-10%': (dd252 <= -0.05) & (dd252 > -0.10), 'Deep>10%': dd252 <= -0.10})
reg_defs['Year'] = np.array([str(d.year) for d in days], dtype=object)
prev = [r for r in rows if r['base'] == 'trend50' and r['gates'] == ('OI5 rising',) and r['size'] == 'full' and r['mode'] == 'both'][0]
strats = {'BUY&HOLD': bh_r, 'CHOSEN': R.run(posof(chosen), chosen['mode'], True), 'BEST>=1 FACTOR': R.run(posof(best_f), best_f['mode'], True), 'PRIOR (trend50&OI5)': R.run(posof(prev), prev['mode'], True)}
print('\n=== FULL-PERIOD BACKTEST (total-return view; CAGR/MaxDD/Sharpe) ===')
for k, r in strats.items(): print(f"{k:22s}", ' | '.join(f"{p} {met(r,*P[p],days)['CAGR']:5.1f}/{met(r,*P[p],days)['DD']:6.1f}/{met(r,*P[p],days)['Sharpe']:4.2f}" for p in ['train', 'valid', 'test', 'full']))
print('\n=== REGIME-WISE (annualised return % / Sharpe / days). Regime known at the decision day; return = next holding period ===')
reg_rows = []
for rn_, lab_arr in reg_defs.items():
    print(f'-- {rn_}')
    for lv in sorted(set(lab_arr) - {''}):
        line = f'   {lv:15s}'
        for sn, r in strats.items():
            idx = np.where(lab_arr[:-1] == lv)[0]; x = r[idx + 1]
            if len(x) < 20: line += f' | {sn[:8]:8s} n/a'; continue
            ar = ((1 + x).prod() ** (252 / len(x)) - 1) * 100; sh = x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
            line += f' | {sn[:8]:8s} {ar:6.1f}%/{sh:5.2f}'
            reg_rows.append(dict(regime_set=rn_, regime=lv, strategy=sn, days=len(x), ann_ret=ar, sharpe=sh))
        print(line, f'  (n={int((lab_arr[:-1]==lv).sum())})')
pd.DataFrame(reg_rows).to_csv('results/rf_factor_perm_regimes.csv', index=False)
pd.DataFrame([dict(name=nm(r), base=r['base'], gates='+'.join(r['gates']), size=r['size'], mode=r['mode'], sel=r['sel'], **{f'{p}_{q}': r['tv'][p][q] for p in P for q in ['CAGR', 'DD', 'Sharpe']}) for r in rows[:300]]).to_csv('results/rf_factor_perm_top300.csv', index=False)
print(f'\ndone in {time.time()-t0:.0f}s')
