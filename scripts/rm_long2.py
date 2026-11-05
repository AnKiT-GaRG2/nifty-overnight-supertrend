"""LONG2 options 1 and 2: slower long signals and drawdown brake, long leg alone. Rules in PROTOCOL_CHANGES.md ROUND "LONG2". Run: <venv>/bin/python scripts/rm_long2.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_hold2 as H
from rm_ideas import trial_log
from rm_signals import supertrend
em = L.em; days = em['days']; R = V.ROOT; S = em['S']; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; fl = L.fl; ST.WS = 1e-9; N = len(S.st); one = np.ones(N)
def pct(x): return x.rolling(365, min_periods=120).apply(lambda v: (v[:-1] < v[-1]).mean(), raw=True)
m1 = pd.read_pickle(f'{R}/data/rm/dataset.pkl')['m1']; g = m1.groupby('date'); dop, dcl = g.open.first(), g.close.last()
BOOST = (pct(((dop / dcl.shift(1) - 1).abs()).reindex(days).shift(1)) > 0.8).fillna(False)
lt0, lz0, st0, sz0 = V.signals(em, 'v2'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET)
def cp(lt, cost='floor'): return H.comps(em, np.asarray(lt, np.int8), one, 1, st0, sz0, 1, cost)
def stream(c, brake=None, s=S0):
    f = pd.Series(np.where(BOOST, 1.25, 1.0), index=days)
    if brake is not None: f = f * pd.Series(np.where(brake, 0.5, 1.0), index=days)
    e2 = dict(em); e2['ens'] = em['ens'] * f; return ST.stream(e2, None, s, c, EV)
bc = cp(lt0); base = stream(bc); bT = V.met(em, base, *TRAIN); bX = V.met(em, base, *TEST); print(f'long-only base v2-FEG long: TRAIN {fl(bT)} | TEST {fl(bX)}\n')
# OPTION 1
sma = {L_: S.d2b(S.sma_daily(L_)) for L_ in (50, 100, 200)}; pc = S.d2b(S.dd.close.values)
cells = [(f'ST({n},{m})', (supertrend(S.h, S.l, S.c, n, m)[0] == 1).astype(np.int8)) for n in (14, 20, 30) for m in (3.0, 3.5, 4.0, 5.0) if (n, m) != (14, 3.0)]
cells += [(f'base AND daily close > SMA{L_}', (lt0 & (np.nan_to_num(pc) > np.nan_to_num(sma[L_]))).astype(np.int8)) for L_ in (50, 100, 200)]
res = {}
print('OPTION 1: slower long signals (equal-drawdown delta, long-only)')
for name, lt in cells:
    net = stream(cp(lt)); dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; res[name] = (dT, dX); trial_log('LONG2_' + name.replace(' ', ''), {}, 'train', V.met(em, net, *TRAIN))
    print(f'  {name:28s} TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} | TEST {fl(V.met(em, net, *TEST))} delta {dX * 100:+.1f}')
def plateau(name):
    if not name.startswith('ST('): return True
    n, m = [float(x) for x in name[3:-1].split(',')]; ms = (3.0, 3.5, 4.0, 5.0); i = ms.index(m); nb = [ms[j] for j in (i - 1, i + 1) if 0 <= j < 4]
    out = []
    for mm in nb:
        k = f'ST({int(n)},{mm})'
        if k in res: out.append(res[k][0] > 0)
        elif (int(n), mm) == (14, 3.0): out.append(True if False else 0 > 0)   # base itself has delta 0
    return all(out) if out else True
ok1 = [n for n, (a, b) in res.items() if a >= 0.02 and b >= 0 and plateau(n)]; print('OPTION 1 passes:', ok1 if ok1 else 'none')
# OPTION 2
eq = (1 + base).cumprod(); dd = eq / eq.cummax() - 1; rng = np.random.default_rng(1113); print('\nOPTION 2: drawdown brake on the long leg')
for X in (0.06, 0.09, 0.12):
    on = np.zeros(len(days), bool); cur = False
    for i in range(1, len(days)):
        d = dd.iloc[i - 1]
        if not cur and d < -X: cur = True
        elif cur and d > -X / 2: cur = False
        on[i] = cur
    on = pd.Series(on, index=days); net = stream(bc, on); dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; null = []
    for _ in range(200): kk = int(rng.integers(60, len(on) - 60)); null.append(L.eqdd(em, stream(bc, pd.Series(np.roll(on.values, kk), index=days)), bT['MaxDD'], *TRAIN) - bT['CAGR'])
    p95 = np.percentile(null, 95); ok = dT > 0 and dT > p95 and dX >= 0; trial_log(f'LONG2_BRAKE{int(X * 100)}', {}, 'train', V.met(em, net, *TRAIN))
    print(f'  brake X={X:.0%}: on {on[TRAIN[0]:TRAIN[1]].mean():.0%} of TRAIN days | TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} (p95 {p95 * 100:+.1f}) | TEST {fl(V.met(em, net, *TEST))} delta {dX * 100:+.1f} -> {"PASS" if ok else "fail"}')
print('\nlong-only size vs drawdown cap (FULL floor-cost MaxDD), base signal:')
cr = cp(lt0, 'real')
for cap in (-0.10, -0.125, -0.15, -0.177):
    lo, hi = 0.2, 4.0
    for _ in range(35):
        s = (lo + hi) / 2
        if V.met(em, stream(bc, None, s), *L.FULL)['MaxDD'] >= cap: lo = s
        else: hi = s
    nf, nr = stream(bc, None, lo), stream(cr, None, lo); print(f' cap {cap:.1%}: long {1.912 * lo:.2f}x | FULL floor {fl(V.met(em, nf, *L.FULL))} realistic {fl(V.met(em, nr, *L.FULL))} | TEST floor {fl(V.met(em, nf, *TEST))} realistic {fl(V.met(em, nr, *TEST))}')
