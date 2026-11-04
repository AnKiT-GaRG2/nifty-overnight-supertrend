"""LONG1: stand-alone long-leg improvement from signal-internal features. Rules in PROTOCOL_CHANGES.md ROUND "LONG1". Run: <venv>/bin/python scripts/rm_long1.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
em = L.em; days = em['days']; R = V.ROOT; S = em['S']; En = em['Ea']; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; fl = L.fl; ST.WS = 1e-9
def pct(x): return x.rolling(365, min_periods=120).apply(lambda v: (v[:-1] < v[-1]).mean(), raw=True)
m1 = pd.read_pickle(f'{R}/data/rm/dataset.pkl')['m1']; g = m1.groupby('date'); dop, dcl = g.open.first(), g.close.last()
G22 = ((dop / dcl.shift(1) - 1).abs()).reindex(days).shift(1); BOOST = (pct(G22) > 0.8).fillna(False)
st = np.asarray(S.st); N = len(st); close = np.asarray(S.c, float); lastb = np.where(En.last_b)[0]; dc = S.dc
run_start = np.zeros(N, int); cur = 0
for t in range(N):
    if st[t] == 1 and (t == 0 or st[t - 1] != 1): cur = t
    run_start[t] = cur
age_b = np.where(st == 1, np.arange(N) - run_start, 0); gain_b = np.where(st == 1, close / close[run_start] - 1, 0.0)
dD = S.D; dclose = pd.Series(dD['close'].values, index=dD.index).reindex(days); dh = pd.Series(dD['high'].values, index=dD.index).reindex(days); dl = pd.Series(dD['low'].values, index=dD.index).reindex(days)
atr = (dh - dl).rolling(14).mean(); atrp = atr / dclose
F = {}
F['T1'] = pd.Series(age_b[lastb] / 25.0, index=days); F['T2'] = pd.Series(gain_b[lastb], index=days) / atrp; F['T3'] = atrp
F['T4'] = (dclose - dl.rolling(20).min()) / atr; F['T5'] = (dh.rolling(20).max() - dclose) / atr
# T1/T2 at the previous day's last bar (zero when the Supertrend was red); others from the previous completed day
F = {k: v.shift(1) for k, v in F.items()}
CP = ST.comps(em, 'floor'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET)
def stream(on, fac, cp=CP, s=S0):
    f = pd.Series(np.where(BOOST, 1.25, 1.0), index=days) * pd.Series(np.where(on, fac, 1.0), index=days); e2 = dict(em); e2['ens'] = em['ens'] * f; return ST.stream(e2, None, s, cp, EV)
off = pd.Series(False, index=days); base = stream(off, 1.0); bT = V.met(em, base, *TRAIN); bX = V.met(em, base, *TEST)
W = {'train 2017-04..2021': ('2017-04-03', '2021-12-31'), 'valid 2022-23': ('2022-01-01', '2023-12-31'), 'TEST 2024-26': TEST, 'FULL': L.FULL}
for cost in ('floor', 'real'):
    cp = ST.comps(em, cost); n = stream(off, 1.0, cp); print(f'LONG-ONLY base ({cost}, long 2.22x + boost): ' + ' | '.join(f'{k} {fl(V.met(em, n, *w))}' for k, w in W.items()))
GL, IL = CP[0], CP[1]; ens0 = em['ens'] * pd.Series(np.where(BOOST, 1.25, 1.0), index=days); lp = (ens0.shift(1).fillna(1.0) * GL + ens0 * IL)[TRAIN[0]:TRAIN[1]]; worst, best = lp.nsmallest(20).index, lp.nlargest(20).index
rng = np.random.default_rng(1112); passed = []; near = []
for k, v in F.items():
    p = pct(v)
    for tail, state in (('hi', p > 0.8), ('lo', p < 0.2)):
        state = state.fillna(False)
        for kind in ('CUT', 'BOOST'):
            w = int(state[worst if kind == 'CUT' else best].sum()); sh = state[TRAIN[0]:TRAIN[1]].mean(); gate = w >= 10 and sh <= 0.25
            if w >= 8: near.append(f'{kind} {k} {tail}: {w}/20 on {sh:.0%}')
            if not gate: continue
            fac = 0.5 if kind == 'CUT' else 1.25; net = stream(state, fac); dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; null = []
            for _ in range(200): kk = int(rng.integers(60, len(state) - 60)); null.append(L.eqdd(em, stream(pd.Series(np.roll(state.values, kk), index=days), fac), bT['MaxDD'], *TRAIN) - bT['CAGR'])
            p95 = np.percentile(null, 95); ok = dT > 0 and dT > p95 and dX >= 0; trial_log(f'LONG1_{kind}{k}{tail}', {}, 'train', V.met(em, net, *TRAIN)); passed += [(kind, k, tail)] if ok else []
            print(f'GATE PASS {kind} {k} {tail}: on {sh:.0%}, {w}/20 | TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} (p95 {p95 * 100:+.1f}) | TEST delta {dX * 100:+.1f} -> {"PASS" if ok else "fail"}')
print('near (8+/20):', near if near else 'none'); print('full passes:', passed)
