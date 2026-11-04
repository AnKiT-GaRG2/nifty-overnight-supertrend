"""SHORTF cells re-run with TRAIN 2017-04..2023-12 / TEST 2024-01..2026-10 and no use of the 2012-16 holdout. Run: <venv>/bin/python scripts/rm_shortf_split.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_shortf as SF
em = L.em; fl = L.fl; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); ELIST = ST.ELECT + ST.BUDGET
CP = ST.comps(em, 'floor'); CPR = ST.comps(em, 'real'); EV = ST.ev_mask(em, ELIST)
lo, hi = 0.3, 2.5
for _ in range(35):
    s = (lo + hi) / 2
    if V.met(em, ST.stream(em, None, s, CP, EV), *TRAIN)['MaxDD'] >= -0.177: lo = s
    else: hi = s
S0 = lo; print(f'scale solved on TRAIN (floor MaxDD -17.7%): {S0:.3f} (long {1.912 * S0:.2f}x, short {0.956 * S0:.2f}x); previously 1.163 from FULL\n')
for c, cp in (('floor', CP), ('real', CPR)):
    n = ST.stream(em, None, S0, cp, EV); print(f'v2-FE {c}: TRAIN {fl(V.met(em, n, *TRAIN))} | TEST {fl(V.met(em, n, *TEST))}')
bT = V.met(em, ST.stream(em, None, S0, CP, EV), *TRAIN); bX = V.met(em, ST.stream(em, None, S0, CP, EV), *TEST)
def combined(perm, cp=CP):
    g, i, f = SF.short_comps(em, perm, 'floor'); return ST.stream(em, None, S0, (cp[0], cp[1], cp[2], g, i, f), EV)
rng = np.random.default_rng(2611); ok_all = True; print()
for fam, j, name in SF.CELLS:
    p = SF.perm_daily(em, fam, j); n = combined(p); eT = L.eqdd(em, n, bT['MaxDD'], *TRAIN) - bT['CAGR']; eX = L.eqdd(em, n, bX['MaxDD'], *TEST) - bX['CAGR']; null = []
    for _ in range(200):
        k = int(rng.integers(60, len(p) - 60)); ps = pd.Series(np.roll(p.values, k), index=p.index); null.append(L.eqdd(em, combined(ps), bT['MaxDD'], *TRAIN) - bT['CAGR'])
    p95 = np.percentile(null, 95); ok = eT > p95 and eT > 0 and eX > 0; ok_all &= ok
    print(f'{name}: TRAIN {fl(V.met(em, n, *TRAIN))} | TEST {fl(V.met(em, n, *TEST))} | equal-DD delta TRAIN {eT * 100:+.1f} pts, TEST {eX * 100:+.1f} pts | null TRAIN median {np.median(null) * 100:+.1f}, p95 {p95 * 100:+.1f}, beats {(np.array(null) < eT).mean():.0%} | {"ok" if ok else "no"}')
print('\nverdict:', 'PASS' if ok_all else 'FAIL')
