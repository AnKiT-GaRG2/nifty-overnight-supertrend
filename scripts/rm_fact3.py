"""FACT3: broad screen of new factors as long-leg cut/boost. Rules in PROTOCOL_CHANGES.md ROUND "FACT3". Run: <venv>/bin/python scripts/rm_fact3.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_data
from rm_ideas import trial_log
em = L.em; days = em['days']; R = V.ROOT; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; fl = L.fl
X = pd.read_csv(f'{R}/data/xmkt3/all_close.csv', parse_dates=['date']).set_index('date').sort_index(); X = X.reindex(X.index.union(days)).ffill()
vix_us = pd.read_csv(f'{R}/data/xmkt/VIX.csv', parse_dates=['date']).set_index('date').sort_index(); vix_us = vix_us.iloc[:, -1] if vix_us.shape[1] > 1 else vix_us.iloc[:, 0]
vix_us = vix_us.reindex(X.index.union(vix_us.index)).ffill().reindex(X.index)
usdinr = pd.read_csv(f'{R}/data/usdinr.csv', parse_dates=['date']).set_index('date')['close']; usdinr = usdinr.reindex(X.index.union(usdinr.index)).ffill().reindex(X.index)
rt = lambda s, n: s / s.shift(n) - 1
G = {}
G['G1'] = X['^VIX9D'] / vix_us; G['G2'] = vix_us / X['^VIX3M']; G['G3'] = X['^VVIX']; G['G4'] = X['^SKEW']; G['G5'] = X['^MOVE']; G['G6'] = X['^OVX']
G['G7'] = rt(X['BTC-USD'], 10); G['G8'] = rt(X['^SOX'], 10) - rt(X['SPY'], 10); G['G9'] = X['^TNX'] - X['^IRX']; G['G10'] = rt(X['TLT'], 10)
G['G11'] = ((X['XLU'] + X['XLP']) / X['SPY']).pipe(lambda s: s / s.shift(10) - 1); G['G12'] = rt(X['FXI'], 10); G['G13'] = rt(X['COPX'], 10) - rt(X['SPY'], 10); G['G14'] = np.log(usdinr).diff().rolling(20).std()
G = {k: v.reindex(days) for k, v in G.items()}
m1 = rm_data.pd.read_pickle(f'{R}/data/rm/dataset.pkl')['m1']; m1 = m1[m1.index.hour * 60 + m1.index.minute >= 555]
c5 = m1['close'].resample('5min', origin='start_day', offset='9h15min').last().dropna(); r5 = np.log(c5).diff(); r5 = r5[r5.index.normalize() == r5.index.normalize().to_series().shift(0).values] if False else r5
dd = pd.Series(r5.index.normalize(), index=r5.index); first5 = r5.groupby(dd).transform(lambda x: np.r_[np.nan, np.ones(len(x) - 1)])      # drop the overnight return at each day's first bar
r5 = r5.where(first5.notna()); rv = (r5 ** 2).groupby(dd).sum(); jr = r5.abs().groupby(dd).max() / np.sqrt(rv)
g = m1.groupby('date'); dop, dcl, dhi, dlo = g.open.first(), g.close.last(), g.high.max(), g.low.min()
t = m1.index.hour * 60 + m1.index.minute; l30 = m1[t >= 14 * 60 + 59].groupby('date').close.agg(['first', 'last']); f30 = m1[t <= 9 * 60 + 45].groupby('date').close.agg(['first', 'last'])
l30c = (l30['last'] / m1[t == 14 * 60 + 58].groupby('date').close.last() - 1); f30c = (m1[t == 9 * 60 + 45].groupby('date').close.last() / dop - 1)
H = {'G15': np.log(rv), 'G16': rv / rv.rolling(20).mean(), 'G17': jr, 'G18': l30c, 'G19': f30c, 'G20': (dcl - dlo) / (dhi - dlo), 'G21': dop / dcl.shift(1) - 1, 'G22': (dop / dcl.shift(1) - 1).abs()}
G.update({k: v.reindex(days) for k, v in H.items()}); F = {k: v.shift(1) for k, v in G.items()}
def pct(x): return x.rolling(365, min_periods=120).apply(lambda v: (v[:-1] < v[-1]).mean(), raw=True)
cells = []
for k, v in F.items():
    p = pct(v)
    for tail, st in (('hi', p > 0.8), ('lo', p < 0.2)):
        for kind in ('CUT', 'BOOST'): cells.append((kind, f'{k} {tail}', st.fillna(False)))
dow = pd.Series(days.dayofweek, index=days)
for i, nm in enumerate(('Mon', 'Tue', 'Wed', 'Thu', 'Fri')):
    for kind in ('CUT', 'BOOST'): cells.append((kind, f'DOW {nm}', dow == i))
f = pd.read_csv(f'{R}/data/fut/nifty_fut.csv', parse_dates=['date', 'expiry']); exps = np.sort(f.expiry.unique()); pos = pd.Series(range(len(days)), index=days)
ne = pd.Series([pd.Timestamp(exps[np.searchsorted(exps, np.datetime64(d))]) for d in days], index=days); dte = pd.Series([max(0, days.searchsorted(ne[d]) - pos[d]) if ne[d] <= days[-1] else 99 for d in days], index=days)
mo = pd.Series(days.to_period('M'), index=days); eom = (mo.groupby(mo).cumcount(ascending=False) < 3)
for kind in ('CUT', 'BOOST'): cells.append((kind, 'EXPIRY-WEEK (<=2d)', dte <= 2)); cells.append((kind, 'MONTH-END (last 3d)', eom))
CP = ST.comps(em, 'floor'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET)
def stream(on, fac):
    e2 = dict(em); e2['ens'] = em['ens'] * pd.Series(np.where(on, fac, 1.0), index=days); return ST.stream(e2, None, S0, CP, EV)
base = stream(pd.Series(False, index=days), 1.0); bT = V.met(em, base, *TRAIN); bX = V.met(em, base, *TEST)
lp = (em['ens'].shift(1).fillna(1.0) * CP[0] + em['ens'] * CP[1])[TRAIN[0]:TRAIN[1]]; worst, best = lp.nsmallest(20).index, lp.nlargest(20).index
print(f'base v2-FE: TRAIN {fl(bT)} | TEST {fl(bX)} | cells {len(cells)}\n'); rng = np.random.default_rng(1111); near = []; passed = []
for kind, name, on in cells:
    on = on.astype(bool); w = int(on[worst if kind == 'CUT' else best].sum()); sh = on[TRAIN[0]:TRAIN[1]].mean(); gate = w >= 10 and sh <= 0.25
    if w >= 8: near.append(f'{kind} {name}: {w}/20, on {sh:.0%}')
    if not gate: continue
    fac = 0.5 if kind == 'CUT' else 1.25; net = stream(on, fac); dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; null = []
    for _ in range(200): kk = int(rng.integers(60, len(on) - 60)); null.append(L.eqdd(em, stream(pd.Series(np.roll(on.values, kk), index=days), fac), bT['MaxDD'], *TRAIN) - bT['CAGR'])
    p95 = np.percentile(null, 95); ok = dT > 0 and dT > p95 and dX >= 0; trial_log('FACT3_' + kind + name.replace(' ', ''), {}, 'train', V.met(em, net, *TRAIN)); passed += [(kind, name, on, fac)] if ok else []
    print(f'GATE PASS {kind} {name}: on {sh:.0%}, {w}/20 | TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} (null p95 {p95 * 100:+.1f}) | TEST delta {dX * 100:+.1f} -> {"PASS" if ok else "fail"}')
print('\nnear-misses (8-9 of 20):', near if near else 'none'); print('cells gated:', len(cells), '| full passes:', [(k, n) for k, n, _, _ in passed])
if len(passed) >= 2:
    on_all = pd.Series(1.0, index=days)
    for _, _, on, fac in passed: on_all = on_all * pd.Series(np.where(on, fac, 1.0), index=days)
    e2 = dict(em); e2['ens'] = em['ens'] * on_all; net = ST.stream(e2, None, S0, CP, EV); print('COMBINED: TRAIN', fl(V.met(em, net, *TRAIN)), 'delta', round((L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']) * 100, 1), '| TEST', fl(V.met(em, net, *TEST)), 'delta', round((L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']) * 100, 1))
