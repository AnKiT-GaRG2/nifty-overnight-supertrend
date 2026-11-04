"""Non-textbook Nifty-futures signals built from information the price chart does not show: futures term structure, expiry cycle,
open-interest flushes, volume capitulation, volatility risk premium, volatility-managed exposure.  Same engine, costs, next-open execution.
PROTOCOL (fixed before running): params tuned on TRAIN 2013-2021 only (best train Sharpe per hypothesis); shortlist = train Sharpe>0.5 AND valid(2022-23) Sharpe>0.5 AND >=10% exposure;
test 2024-26 shown once; no change after seeing test. Bar for 'candidate': test CAGR>0, test Sharpe>=0.4, positive in >=10 of 14 calendar years, bootstrap 90% lower bound of Sharpe (2013-26) > 0."""
import itertools, math, json
import numpy as np, pandas as pd
src = open('scripts/report_futures_ext.py').read().split("FAM = [")[0]
exec(src)
full_src = open('scripts/report_futures_ext.py').read()
exec(full_src.split('# ------------------------------------------------------------------ engine')[1].split('RES = {}')[0])
IDX_ALL = IDX
# ------------------------------------------------------------------ extra, causal features (each day uses only that day's listing)
near = np.full(n, np.nan); nxt = np.full(n, np.nan); dte0 = np.full(n, np.nan); dd01 = np.full(n, np.nan); vol = np.zeros(n)
dayidx = {d: i for i, d in enumerate(days)}
for i, t in enumerate(days):
    g = G[t].sort_index(); ex = list(g.index); vol[i] = g.volume.sum()
    near[i] = g.close.iloc[0]; nxt[i] = g.close.iloc[1]; dte0[i] = (ex[0] - t).days; dd01[i] = (ex[1] - ex[0]).days
def tdays_to(e, i):                                           # trading days from day i to expiry date e (calendar known in advance)
    return int(np.searchsorted(days.values, np.datetime64(e))) - i
tdte = np.array([tdays_to(sorted(G[t].index)[0], i) for i, t in enumerate(days)], float)
# trading days since the previous expiry
exp_all = sorted({e for g in G.values() for e in g.index}); exp_pos = np.array([np.searchsorted(days.values, np.datetime64(e)) for e in exp_all])
since = np.array([i - exp_pos[exp_pos <= i].max() if (exp_pos <= i).any() else np.nan for i in range(n)], float)
spread = S((nxt / near - 1) * 365 / dd01)                      # annualised calendar spread (near->next): implied financing/fear gauge
c = D['c']; r1 = c.pct_change(); rv20 = r1.rolling(20).std() * np.sqrt(252) * 100; vixs = D['vix']
vsr = S(vol); oi = D['oia']
FEATS = dict(spread=spread, vol=vsr, tdte=S(tdte), since=S(since), rv20=rv20, oi=oi)
z = lambda x, w: (x - x.rolling(w).mean()) / x.rolling(w).std()
RES2 = {}; NEWTRIALS = [0]
def ev(name, sig, params):
    NEWTRIALS[0] += 1
    r = evaluate(name, lambda D, ls=False, _s=sig, **kw: _s, params)
    RES2.setdefault(name, []).append(r); return r
hold = lambda s, h: s.astype(float).rolling(h, min_periods=1).max()
sma200 = sma(c, 200)
# H1 term-structure fear: calendar spread unusually LOW (z) -> long
for w, th, h, f in itertools.product([60, 120, 250], [1.0, 1.5, 2.0], [1, 3, 5], ['none', 'c>200']):
    s_ = (z(spread, w) < -th); s_ = s_ & (c > sma200) if f == 'c>200' else s_
    ev('H1 spread-collapse long', hold(s_, h), dict(w=w, th=th, h=h, f=f))
# H2 expiry-cycle windows (trading days to expiry) and post-expiry windows
td = FEATS['tdte']; sn = FEATS['since']
for a, L in itertools.product([0, 2, 4, 6, 8, 10, 12, 15, 18], [3, 5, 8]):
    ev('H2a long in window [a,a+L) trading days before expiry', ((td >= a) & (td < a + L)).astype(float), dict(a=a, L=L))
for a, L in itertools.product([0, 1, 2, 3, 5, 8, 12], [2, 3, 5]):
    ev('H2b long in window after expiry', ((sn >= a) & (sn < a + L)).astype(float), dict(a=a, L=L))
# H3 OI flush: OI falls hard while price falls (forced liquidation) -> long
for k, x, h in itertools.product([2, 3, 5], [0.02, 0.04, 0.06], [1, 3, 5]):
    ev('H3 OI-flush long', hold((oi / oi.shift(k) - 1 < -x) & (c / c.shift(k) - 1 < 0), h), dict(k=k, x=x, h=h))
# H4 volatility risk premium: VIX minus realised vol, state long while premium rich
vrp = vixs - rv20
for q, f in itertools.product([2, 4, 6, 8, 10], ['none', 'c>200']):
    s_ = vrp > q; s_ = s_ & (c > sma200) if f == 'c>200' else s_; ev('H4 VRP>q long', s_.astype(float), dict(q=q, f=f))
# H5 volume capitulation: volume spike on a down day with weak close
for zz, rr, h in itertools.product([1.5, 2.0, 2.5], [0.005, 0.01, 0.015], [1, 3]):
    ev('H5 volume-capitulation long', hold((z(vsr, 60) > zz) & (r1 < -rr), h), dict(z=zz, r=rr, h=h))
# H6 volatility-managed beta (always long, scaled by recent realised vol; no leverage)
for tv, lb in itertools.product([6, 8, 10, 12], [10, 20, 60]):
    rv = r1.rolling(lb).std().shift(0) * np.sqrt(252) * 100; ev('H6 vol-managed long', (tv / rv).clip(upper=1.0).fillna(0), dict(target=tv, lb=lb))
# H7 crowding gate on beta: long unless OI is extreme AND price weak
oipct = oi.rolling(252).apply(lambda a: (a[-1] > a).mean(), raw=True)
for p, ma in itertools.product([0.8, 0.9, 0.95], [50, 100]):
    ev('H7 beta unless crowded OI & weak trend', (~((oipct > p) & (c < sma(c, ma)))).astype(float), dict(p=p, ma=ma))
print('new trials this run:', NEWTRIALS[0])
# ------------------------------------------------------------------ select on train only, shortlist on train+valid, then test
BH = evaluate('Buy & Hold futures', b_bh, {}, log=False)
sel = {}
for name, lst in RES2.items():
    b = max(lst, key=lambda r: r['m']['train']['Sharpe']); sel[name] = b
fmt = lambda m, k: f"{m[k]['CAGR']:.1f} / {m[k]['Sharpe']:.2f} / {m[k]['MaxDD']:.1f}"
cols = ['train', 'valid', 'test', 'full']
tab = ["| Hypothesis (params tuned on train 2013-21) | Train | Valid | Test | Full | Exposure |", "|---|---|---|---|---|---|"]
for nm, r in sorted(sel.items(), key=lambda x: -x[1]['m']['train']['Sharpe']):
    m = r['m']; tab.append(f"| {nm} {r['params']} | " + " | ".join(fmt(m, k) for k in cols) + f" | {m['full']['Exposure']:.0f}% |")
tab.append("| Buy & Hold futures | " + " | ".join(fmt(BH['m'], k) for k in cols) + " | 100% |")
print('\n'.join(tab))
short = [(nm, r) for nm, r in sel.items() if r['m']['train']['Sharpe'] > 0.5 and r['m']['valid']['Sharpe'] > 0.5 and r['m']['train']['Exposure'] >= 10]
print('\nSHORTLIST (train&valid Sharpe>0.5, exposure>=10%):', [(nm, r['params']) for nm, r in short])
# how often does the tuned best on train survive? robustness: share of ALL param combos per hypothesis with test CAGR>0 and train CAGR>0
for nm, lst in RES2.items():
    ok = [r for r in lst if r['m']['train']['CAGR'] > 0 and r['m']['valid']['CAGR'] > 0]
    print(f"{nm[:58]:58s} combos={len(lst):3d}  pos train&valid={len(ok):3d}  of which test>0: {sum(r['m']['test']['CAGR']>0 for r in ok):3d}")
pd.to_pickle({k: [{kk: vv for kk, vv in r.items() if kk != 'sig'} for r in v] for k, v in RES2.items()}, 'results/novel_res.pkl')
open('results/novel_table.md', 'w').write('\n'.join(tab))
