"""Long-history confidence test on NSE Nifty FUTURES (2007-2026), daily close-to-close engine.
Part 1: frozen strategies A (trend50 & OI5 rising) and B (rupee21<2% & US10Y21<0.25 & not Jan/Feb) on 2008-2016 = never seen before.
Part 2: independent factor search using 2008-2016 ONLY, then check the picks on 2017-2026 (not used to choose).
Part 3: yearly expanding-window walk-forward over all years (2011-2026), re-picking the best combo from all prior years.
Engine: position decided at close t earns close(t)->close(t+1) of the front month; cost 0.025%/side, 0.05% roll when carried over an expiry;
'total' adds 6% p.a. on capital, 'pure' is futures P&L only. FII/PE data do not exist before 2017 so those gates are not in this test.
Run from repo root: python3 scripts/rf_longhist.py  (needs data/fut/nifty_fut_pre2017.csv and data/pre/*.csv)"""
import sys, os, itertools, time
sys.path.insert(0, 'scripts')
import numpy as np, pandas as pd
import warnings; warnings.filterwarnings('ignore')
from factors import _asof
t0 = time.time(); D = 'data'
COST, ROLL, RF_RATE = 0.00025, 0.0005, 0.06
f = pd.concat([pd.read_csv(f'{D}/fut/nifty_fut_pre2017.csv', parse_dates=['date', 'expiry']), pd.read_csv(f'{D}/fut/nifty_fut.csv', parse_dates=['date', 'expiry'])])
f = f.drop_duplicates(['date', 'expiry']); f = f[(f.close > 0)].set_index(['date', 'expiry']).sort_index()
days = pd.DatetimeIndex(sorted(f.index.get_level_values(0).unique())); n = len(days)
ret = np.zeros(n); rollf = np.zeros(n); prevk = None; C = np.full(n, np.nan); oi = np.zeros(n); expday = np.zeros(n, bool)
grp = {d: g for d, g in f.reset_index().groupby('date')}
for i in range(n):
    g = grp[days[i]]; oi[i] = g.oi.sum(); expday[i] = (g.expiry == days[i]).any()
for i in range(1, n):
    e0 = set(grp[days[i - 1]].expiry[grp[days[i - 1]].expiry > days[i - 1]]); e1 = set(grp[days[i]].expiry)
    cand = sorted(e0 & e1)
    if not cand: continue
    k = cand[0]; ret[i] = f.loc[(days[i], k)].close / f.loc[(days[i - 1], k)].close - 1
    rollf[i] = float(prevk is not None and k != prevk); prevk = k
adj = 100 * np.cumprod(1 + ret); X = pd.Series(adj, index=days)
cal = np.r_[0, np.diff(days.values).astype('timedelta64[D]').astype(float)]      # calendar days since previous bar
print(f'{n} futures days {days[0].date()} .. {days[-1].date()}  ({time.time()-t0:.0f}s)')
def L(k):
    a = pd.read_csv(f'{D}/pre/{k}.csv', parse_dates=['date']); b = pd.read_csv(f'{D}/{k}.csv', parse_dates=['date'])
    return pd.concat([a, b]).drop_duplicates('date').set_index('date').sort_index()['close'].astype(float)
A_ = lambda s: _asof(s, days).values
usd, dxy, us, sp, br, vx = [L(k) for k in ['usdinr', 'dxy', 'us10y', 'spx', 'brent', 'vix']]
G = {}
G['OI5 rising'] = np.nan_to_num(pd.Series(oi).pct_change(5).shift(1).values, nan=1.0) > 0
G['rupee21<2%'] = A_(usd.pct_change(21) * 100) < 2; G['rupee1d<0.3%'] = A_(usd.pct_change() * 100) < 0.3
G['dxy21<1.5%'] = A_(dxy.pct_change(21) * 100) < 1.5; G['us10y21<0.25'] = A_(us.diff(21)) < 0.25
G['spx21>-2%'] = A_(sp.pct_change(21) * 100) > -2; G['spx>sma200'] = A_(sp) > A_(sp.rolling(200).mean())
G['brent21avg<100'] = A_(br.rolling(21).mean()) < 100; G['brent5<+5%'] = A_(br.pct_change(5) * 100) < 5
vs = pd.Series(vx.reindex(days).ffill().values, index=days).shift(1)
G['vix<20'] = (vs < 20).values; G['vix<25'] = (vs < 25).values; G['vix1d<+8%'] = (vs / vs.shift(1) - 1 < 0.08).values
G['not_Jan/Feb'] = ~np.isin(np.array(days.month), [1, 2]); G['bank-style: ret20>0'] = X.pct_change(20).shift(1).values > 0
G['rupee21<1%'] = A_(usd.pct_change(21) * 100) < 1; G['us10y21<0'] = A_(us.diff(21)) < 0
G = {k: np.nan_to_num(np.asarray(v, float), nan=1.0) > 0 for k, v in G.items()}                       # NaN (warm-up / missing) -> allow
POOL = list(G)
Xv = X.values; sma = lambda k: X.rolling(k).mean().values
BASES = {'always long': np.ones(n), 'trend50': (Xv > sma(50)) * 1.0, 'trend100': (Xv > sma(100)) * 1.0, 'trend200': (Xv > sma(200)) * 1.0, 'mom60>0': (X.pct_change(60).values > 0) * 1.0}
rv20 = (X.pct_change().rolling(20).std() * np.sqrt(252)).values; VOL = np.nan_to_num(np.minimum(1, 0.15 / np.maximum(rv20, 0.05)), nan=1.0)
def run(pos, interest=True):
    pos = np.nan_to_num(pos); r = np.zeros(n)
    prev = np.r_[0.0, pos[:-1]]                                              # position held over bar i = decided at close i-1
    held = prev * ret
    chg = np.abs(prev - np.r_[0.0, prev[:-1]])
    roll = ROLL * np.abs(prev) * rollf
    r = held - chg * COST - roll
    if interest: r = r + RF_RATE / 365 * cal
    return r
def met(r, lo, hi):
    x = r[lo:hi]; eq = np.cumprod(1 + x); yrs = max((days[hi - 1] - days[lo]).days / 365.25, 1e-9)
    c = (eq[-1] ** (1 / yrs) - 1) * 100; dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
    return c, dd, (x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0)
ix = lambda s: int(np.searchsorted(days, pd.Timestamp(s)))
SEG = {'PRE 2008-16 (unseen)': ('2008-01-01', '2016-12-31'), '  GFC era 2008-09': ('2008-01-01', '2009-12-31'), '  2010-12': ('2010-01-01', '2012-12-31'), '  2013-16': ('2013-01-01', '2016-12-31'),
       'Train 2017-21': ('2017-04-01', '2021-12-31'), 'Valid 2022-23': ('2022-01-01', '2023-12-31'), 'Test 2024-26': ('2024-01-01', '2026-12-31'), 'FULL 2008-26': ('2008-01-01', '2026-12-31')}
SEGI = {k: (ix(a), ix(b) + 1 if ix(b) < n else n) for k, (a, b) in SEG.items()}
fmt = lambda r: ' | '.join(f"{k.strip()[:11]:11s} {met(r, *SEGI[k])[0]:5.1f}/{met(r, *SEGI[k])[1]:6.1f}/{met(r, *SEGI[k])[2]:4.2f}" for k in SEG)
posA = (Xv > sma(50)) * G['OI5 rising'] * 1.0; posB = (G['rupee21<2%'] & G['us10y21<0.25'] & G['not_Jan/Feb']) * 1.0; posH = np.ones(n)
print('\n=== PART 1: FROZEN A, B vs HOLD on all eras (CAGR/MaxDD/Sharpe). PRE-2017 rows were never seen when A and B were chosen ===')
for view, inter in [('TOTAL (futures P&L + 6% interest)', True), ('PURE futures P&L (no interest)', False)]:
    print('\n' + view)
    for nm, p in [('HOLD futures', posH), ('A trend50&OI5', posA), ('B rupee&us10y&Jan/Feb', posB)]:
        r = run(p, inter); print(f'{nm:22s}', ' | '.join(f"{k.strip()[:6]:6s} {met(r, *SEGI[k])[0]:5.1f}/{met(r, *SEGI[k])[1]:6.1f}/{met(r, *SEGI[k])[2]:4.2f}" for k in SEG))
print('\nYear by year, total return % (HOLD / A / B):')
for y in range(2008, 2027):
    a, b = ix(f'{y}-01-01'), min(ix(f'{y}-12-31') + 1, n); sl = slice(a, b)
    print(f'  {y}: ' + ' / '.join(f'{(np.prod(1 + run(p)[sl]) - 1) * 100:6.1f}' for p in [posH, posA, posB]))
tot = {nm: run(p) for nm, p in [('H', posH), ('A', posA), ('B', posB)]}

# ---------------- PART 2: independent discovery on 2008-2016 only
combos = [(bn, gs) for bn in BASES for k in range(0, 4) for gs in itertools.combinations(POOL, k)]
print(f'\n=== PART 2: independent search on 2008-2016 ONLY: {len(POOL)} gates, {len(combos)} base x gate-sets x 2 sizings = {2*len(combos)} variants ===')
GF = {g: G[g].astype(float) for g in POOL}
rets = []; meta = []
for bn, gs in combos:
    s = BASES[bn].copy()
    for g in gs: s = s * GF[g]
    for zn, z in [('full', 1.0), ('volT15', VOL)]:
        rets.append(run(s * z).astype(np.float32)); meta.append((bn, gs, zn))
Rm = np.vstack(rets); print(f'matrix {Rm.shape} built in {time.time()-t0:.0f}s')
def scores(lo, hi, rows=None):
    x = Rm[:, lo:hi].astype(np.float64); eq = np.cumprod(1 + x, axis=1); yrs = (days[hi - 1] - days[lo]).days / 365.25
    c = (eq[:, -1] ** (1 / yrs) - 1) * 100; dd = (eq / np.maximum.accumulate(eq, axis=1) - 1).min(axis=1) * 100
    return c, dd
a, m_, b = ix('2008-01-01'), ix('2012-07-01'), ix('2017-01-01')
c1, d1 = scores(a, m_); c2, d2 = scores(m_, b); sel = np.minimum(c1 - np.abs(d1), c2 - np.abs(d2))
order = np.argsort(-sel); nmv = lambda j: f"{meta[j][0]}{(' & ' + ' & '.join(meta[j][1])) if meta[j][1] else ''} [{meta[j][2]}]"
cT, dT = scores(ix('2017-04-01'), n)
print('\nTOP 12 by 2008-16 score (min over two halves of CAGR-|DD|); columns: 2008-16 CAGR/DD | AFTERWARDS 2017-26 CAGR/DD (never used to select)')
cpre, dpre = scores(a, b)
for j in order[:12]: print(f'{nmv(j)[:100]:100s} {cpre[j]:5.1f}/{dpre[j]:6.1f} | {cT[j]:5.1f}/{dT[j]:6.1f}')
from collections import Counter
cnt = Counter(g for j in order[:100] for g in meta[j][1]); print('\nGate frequency in top-100 found on 2008-16:', cnt.most_common(8))
hc, hd = scores(ix('2017-04-01'), n); hj = [j for j, m in enumerate(meta) if m[0] == 'always long' and not m[1] and m[2] == 'full'][0]
top = order[:100]
print(f'HOLD 2017-26: {cT[hj]:.1f}/{dT[hj]:.1f}.  Top-100 from 2008-16 on 2017-26: median CAGR {np.median(cT[top]):.1f}, median DD {np.median(dT[top]):.1f}; share beating HOLD CAGR {np.mean(cT[top] > cT[hj])*100:.0f}%, better DD {np.mean(dT[top] > dT[hj])*100:.0f}%')
rank = pd.Series(sel).rank(ascending=False)
for nm_, bn, gs in [('A trend50&OI5', 'trend50', ('OI5 rising',)), ('B rupee&us10y&Jan/Feb', 'always long', ('rupee21<2%', 'us10y21<0.25', 'not_Jan/Feb'))]:
    j = [k for k, m in enumerate(meta) if m[0] == bn and m[1] == gs and m[2] == 'full'][0]
    print(f'{nm_}: rank {int(rank[j])} of {len(meta)} on 2008-16 selection score; 2008-16 {cpre[j]:.1f}/{dpre[j]:.1f}')
print('Spearman(2008-16 score, 2017-26 CAGR-|DD|) over all variants:', round(pd.Series(sel).rank().corr(pd.Series(cT - np.abs(dT)).rank()), 3))

# ---------------- PART 3: expanding-window walk-forward over all years
print('\n=== PART 3: yearly walk-forward 2011-2026 over the same variants (re-pick on all prior years; score = weaker half of CAGR-|DD|) ===')
oos = []; idxs = []
for Y in range(2011, 2027):
    lo, hi = ix('2008-01-01'), ix(f'{Y}-01-01'); mid = (lo + hi) // 2
    c1, d1 = scores(lo, mid); c2, d2 = scores(mid, hi); j = int(np.argmax(np.minimum(c1 - np.abs(d1), c2 - np.abs(d2))))
    y0, y1 = hi, min(ix(f'{Y}-12-31') + 1, n); oos.append(Rm[j, y0:y1].astype(float)); idxs.append((y0, y1))
    print(f"  {Y}: {nmv(j)[:90]:90s} OOS {((np.prod(1 + Rm[j, y0:y1].astype(float)) - 1) * 100):6.1f}%  HOLD {((np.prod(1 + tot['H'][y0:y1]) - 1) * 100):6.1f}%")
x = np.concatenate(oos); xh = np.concatenate([tot['H'][a_:b_] for a_, b_ in idxs]); xa = np.concatenate([tot['A'][a_:b_] for a_, b_ in idxs]); xb = np.concatenate([tot['B'][a_:b_] for a_, b_ in idxs])
def S(x): eq = np.cumprod(1 + x); yrs = len(x) / 252; return f'{(eq[-1]**(1/yrs)-1)*100:5.1f}% / {(eq/np.maximum.accumulate(eq)-1).min()*100:6.1f}% / {x.mean()/x.std()*np.sqrt(252):4.2f}'
print('WALK-FORWARD 2011-26 (total return) CAGR/MaxDD/Sharpe:', S(x)); print('HOLD futures same years                         :', S(xh)); print('frozen A same years                             :', S(xa)); print('frozen B same years                             :', S(xb))
print(f'\ndone {time.time()-t0:.0f}s')
