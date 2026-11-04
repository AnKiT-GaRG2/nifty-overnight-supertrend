"""FEAT round: futures-native features as long-leg cuts. Rules in PROTOCOL_CHANGES.md ROUND "FEAT". Run: <venv>/bin/python scripts/rm_feat.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
em = L.em; days = em['days']; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; fl = L.fl
f = pd.read_csv(os.path.join(V.ROOT, 'data/fut/nifty_fut.csv'), parse_dates=['date', 'expiry'])
rows = {}
for d, g in f.groupby('date'):
    g = g.sort_values('expiry'); g = g[g.expiry >= d]
    if len(g) < 2: continue
    n, x = g.iloc[0], g.iloc[1]; gap = max((x.expiry - n.expiry).days, 1)
    rows[d] = dict(F1=(x.close / n.close - 1) * 365 / gap, oi=g.oi.sum(), vol=g.volume.sum(), F4=n.oi / g.oi.sum())
D = pd.DataFrame(rows).T.sort_index().astype(float)
D['F2'] = D.oi / D.oi.shift(5) - 1; D['F3'] = D.vol / D.vol.rolling(20).mean()
D = D.reindex(days.union(D.index)).ffill().reindex(days).shift(1)                       # known at previous close
def pct(x): return x.rolling(365, min_periods=120).apply(lambda v: (v[:-1] < v[-1]).mean(), raw=True)
P = {k: pct(D[k]) for k in ('F1', 'F2', 'F3', 'F4')}
def state(k, tail): return ((P[k] > 0.8) if tail == 'hi' else (P[k] < 0.2)).fillna(False)
CP = ST.comps(em, 'floor'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET)
def stream(on):
    e2 = dict(em); e2['ens'] = em['ens'] * pd.Series(np.where(on, 0.5, 1.0), index=days); return ST.stream(e2, None, S0, CP, EV)
base = stream(pd.Series(False, index=days)); bT = V.met(em, base, *TRAIN); bX = V.met(em, base, *TEST)
GL, IL = CP[0], CP[1]; longpnl = (em['ens'].shift(1).fillna(1.0) * GL + em['ens'] * IL)[TRAIN[0]:TRAIN[1]]; worst = longpnl.nsmallest(20).index
print(f'base v2-FE: TRAIN {fl(bT)} | TEST {fl(bX)}\n'); rng = np.random.default_rng(1106); res = {}
for k in ('F1', 'F2', 'F3', 'F4'):
    for tail in ('hi', 'lo'):
        on = state(k, tail); w = int(on[worst].sum()); share = on[TRAIN[0]:TRAIN[1]].mean(); gate = w >= 10 and share <= 0.25
        print(f'{k} {tail}: on {share:.0%} of days, on for {w}/20 worst long days -> gate {"PASS" if gate else "no"}')
        if not gate: continue
        net = stream(on); dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; null = []
        for _ in range(200): kk = int(rng.integers(60, len(on) - 60)); null.append(L.eqdd(em, stream(pd.Series(np.roll(on.values, kk), index=days)), bT['MaxDD'], *TRAIN) - bT['CAGR'])
        p95 = np.percentile(null, 95); ok = dT > 0 and dT > p95 and dX >= 0; trial_log(f'FEAT_{k}{tail}', {}, 'train', V.met(em, net, *TRAIN))
        print(f'   TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} pts (null p95 {p95 * 100:+.1f}); TEST delta {dX * 100:+.1f} -> {"PASS" if ok else "FAIL"}')
