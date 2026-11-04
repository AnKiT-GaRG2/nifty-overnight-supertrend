"""DATA2 round: sector / foreign-index / heavyweight features as long-leg modifiers. Rules in PROTOCOL_CHANGES.md ROUND "DATA2". Run: <venv>/bin/python scripts/rm_data2.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
em = L.em; days = em['days']; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; fl = L.fl
X = pd.read_csv(os.path.join(V.ROOT, 'data/xmkt2/all_close.csv'), parse_dates=['date']).set_index('date').sort_index()
X = X.reindex(X.index.union(days)).ffill()
sec = X[['^CNXIT', '^CNXFMCG', '^CNXAUTO', '^CNXPHARMA', '^CNXMETAL', '^CNXREALTY', '^CNXENERGY', '^CNXPSUBANK', '^CNXINFRA']]
fgn = X[['^N225', '^HSI', '^KS11', '^AXJO', '^FTSE', '^GDAXI']]; hw = X[['HDFCBANK.NS', 'RELIANCE.NS', 'ICICIBANK.NS', 'INFY.NS', 'TCS.NS']]
nifty = pd.Series(em['S'].D['close'].values, index=em['S'].D.index).reindex(X.index.union(em['S'].D.index)).ffill().reindex(X.index)
lg = lambda s: np.log(s)
F = {}
F['D1'] = (lg(sec[['^CNXFMCG', '^CNXPHARMA']].mean(axis=1)) - lg(sec[['^CNXAUTO', '^CNXMETAL', '^CNXREALTY']].mean(axis=1))).diff(10)
F['D2'] = (sec > sec.rolling(50).mean()).mean(axis=1)
F['D3'] = (fgn / fgn.shift(5) - 1).mean(axis=1)
F['D4'] = (hw / hw.shift(10) - 1).mean(axis=1) - (nifty / nifty.shift(10) - 1)
F['D5'] = (sec['^CNXIT'] / sec['^CNXIT'].shift(10) - 1) - (nifty / nifty.shift(10) - 1)
F = {k: v.reindex(days).shift(1) for k, v in F.items()}
def pct(x): return x.rolling(365, min_periods=120).apply(lambda v: (v[:-1] < v[-1]).mean(), raw=True)
P = {k: pct(v) for k, v in F.items()}
def state(k, tail): return ((P[k] > 0.8) if tail == 'hi' else (P[k] < 0.2)).fillna(False)
CELLS = [('CUT', 'D1', 'hi'), ('CUT', 'D2', 'lo'), ('CUT', 'D3', 'lo'), ('CUT', 'D4', 'lo'), ('CUT', 'D4', 'hi'), ('CUT', 'D5', 'lo'), ('BOOST', 'D1', 'lo'), ('BOOST', 'D2', 'hi'), ('BOOST', 'D3', 'hi'), ('BOOST', 'D5', 'hi')]
CP = ST.comps(em, 'floor'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET)
def stream(on, fac):
    e2 = dict(em); e2['ens'] = em['ens'] * pd.Series(np.where(on, fac, 1.0), index=days); return ST.stream(e2, None, S0, CP, EV)
base = stream(pd.Series(False, index=days), 1.0); bT = V.met(em, base, *TRAIN); bX = V.met(em, base, *TEST)
GL, IL = CP[0], CP[1]; lp = (em['ens'].shift(1).fillna(1.0) * GL + em['ens'] * IL)[TRAIN[0]:TRAIN[1]]; worst, best = lp.nsmallest(20).index, lp.nlargest(20).index
print(f'base v2-FE: TRAIN {fl(bT)} | TEST {fl(bX)}\n'); rng = np.random.default_rng(1108)
for kind, k, tail in CELLS:
    on = state(k, tail); w = int(on[worst if kind == 'CUT' else best].sum()); share = on[TRAIN[0]:TRAIN[1]].mean(); gate = w >= 10 and share <= 0.25
    print(f'{kind} {k} {tail}: on {share:.0%} of days, on for {w}/20 {"worst" if kind == "CUT" else "best"} long days -> gate {"PASS" if gate else "no"}')
    if not gate: continue
    fac = 0.5 if kind == 'CUT' else 1.25; net = stream(on, fac); dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; null = []
    for _ in range(200): kk = int(rng.integers(60, len(on) - 60)); null.append(L.eqdd(em, stream(pd.Series(np.roll(on.values, kk), index=days), fac), bT['MaxDD'], *TRAIN) - bT['CAGR'])
    p95 = np.percentile(null, 95); ok = dT > 0 and dT > p95 and dX >= 0; trial_log(f'DATA2_{kind}{k}{tail}', {}, 'train', V.met(em, net, *TRAIN))
    print(f'   TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} pts (null p95 {p95 * 100:+.1f}); TEST delta {dX * 100:+.1f} -> {"PASS" if ok else "FAIL"}')
