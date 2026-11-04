"""LONGENTRY: alternative long entries in the full system + cap table. Rules in PROTOCOL_CHANGES.md ROUND "LONGENTRY". Run: <venv>/bin/python scripts/rm_longentry.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_hold2 as H
from rm_ideas import trial_log
from rm_signals import supertrend
em = L.em; S = em['S']; N = len(S.st); TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); FULL = L.FULL; S0 = 1.163; fl = L.fl
EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET); lt0, lz0, st0, sz0 = V.signals(em, 'v2'); one = np.ones(N)
dst = np.asarray(S.dst_daily(10, 3.0), float); DL = (np.nan_to_num(S.d2b(dst)) == 1).astype(np.int8)
def cp(lt, cost='floor'): return H.comps(em, np.asarray(lt, np.int8), one, 1, st0, sz0, 1, cost)
def sig(name):
    if name == 'base': return lt0
    if name == 'L9 daily ST(10,3)': return DL
    if name == 'L10 AND': return (lt0 & DL).astype(np.int8)
    if name == 'L11 OR': return (lt0 | DL).astype(np.int8)
    n, m = [float(x) for x in name.split('(')[1].rstrip(')').split(',')]; return (supertrend(S.h, S.l, S.c, int(n), m)[0] == 1).astype(np.int8)
CELLS = ['base'] + [f'L{i+1} ST({n},{m})' for i, (n, m) in enumerate([(n, m) for n in (10, 14, 20) for m in (2.5, 3.0, 3.5) if (n, m) != (14, 3.0)])] + ['L9 daily ST(10,3)', 'L10 AND', 'L11 OR']
stream = lambda c: ST.stream(em, None, S0, c, EV)
bc = cp(lt0); bnet = stream(bc); bT = V.met(em, bnet, *TRAIN); bX = V.met(em, bnet, *TEST); print(f'base v2-FE floor: TRAIN {fl(bT)} | TEST {fl(bX)} | FULL {fl(V.met(em, bnet, *FULL))}\n'); rng = np.random.default_rng(1110); passed = []
for name in CELLS[1:]:
    lt = sig(name); c = cp(lt); net = stream(c); dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; null = []
    for _ in range(100): null.append(L.eqdd(em, stream(cp(np.roll(lt, int(rng.integers(500, N - 500))))), bT['MaxDD'], *TRAIN) - bT['CAGR'])
    p95 = np.percentile(null, 95); ok = dT >= 0.02 and dT > p95 and dX >= 0; trial_log('LONGENTRY_' + name.split()[0], {}, 'train', V.met(em, net, *TRAIN)); passed += [name] if ok else []
    print(f'{name}: TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} (null p95 {p95 * 100:+.1f}) | TEST {fl(V.met(em, net, *TEST))} delta {dX * 100:+.1f} -> {"PASS" if ok else "fail"}')
print('\nPASSED:', passed)
# PART 2: cap table for v2-FE (full period)
print('\nPART 2: v2-FE, scale needed per FULL-period drawdown cap (floor-cost DD), CAGR floor / realistic, TEST window')
cf, cr = bc, cp(lt0, 'real')
for cap in (-0.177, -0.20, -0.22, -0.25, -0.28, -0.30):
    lo, hi = 0.3, 3.5
    for _ in range(35):
        s = (lo + hi) / 2
        if V.met(em, ST.stream(em, None, s, cf, EV), *FULL)['MaxDD'] >= cap: lo = s
        else: hi = s
    nf, nr = ST.stream(em, None, lo, cf, EV), ST.stream(em, None, lo, cr, EV)
    print(f'cap {cap:.1%}: scale {lo:.3f} (long {1.912 * lo:.2f}x / short {0.956 * lo:.2f}x) | FULL floor {fl(V.met(em, nf, *FULL))} | FULL realistic {fl(V.met(em, nr, *FULL))} | TEST floor {fl(V.met(em, nf, *TEST))} | TEST realistic {fl(V.met(em, nr, *TEST))}')
