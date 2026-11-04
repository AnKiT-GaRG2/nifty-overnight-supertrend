"""Descriptive robustness of the FACT3 pass (BOOST G22 hi). No trials, no tuning. Run: <venv>/bin/python scripts/rm_fact3_check.py"""
import sys, os, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import rm_fact3 as Z
import numpy as np, pandas as pd, rm_v2next as V, rm_v2lev as L, rm_stress as ST
em, days, fl = Z.em, Z.days, Z.fl; F = Z.F; p = Z.pct(F['G22'])
def mk(lo, fac, cost='floor'):
    on = (p > lo).fillna(False); CP = ST.comps(em, cost); e2 = dict(em); e2['ens'] = em['ens'] * pd.Series(np.where(on, fac, 1.0), index=days); return ST.stream(e2, None, Z.S0, CP, Z.EV), on
W = {'train 2017-04..2021': ('2017-04-03', '2021-12-31'), 'valid 2022-23': ('2022-01-01', '2023-12-31'), 'TEST 2024-26': Z.TEST, 'FULL': L.FULL}
for cost in ('floor', 'real'):
    CP = ST.comps(em, cost); b = ST.stream(em, None, Z.S0, CP, Z.EV); print(f'\n== {cost} costs: base vs BOOST G22 hi (p>0.8, x1.25), CAGR/MaxDD/Sharpe + equal-DD delta')
    n, on = mk(0.8, 1.25, cost)
    for k, w in W.items(): bm = V.met(em, b, *w); print(f' {k:22s} base {fl(bm)} | boost {fl(V.met(em, n, *w))} | equal-DD delta {(L.eqdd(em, n, bm["MaxDD"], *w) - bm["CAGR"]) * 100:+.1f} pts')
print('\nneighbours (floor, descriptive; NOT a tuning step): percentile cut-off x boost size -> TRAIN delta / TEST delta / FULL delta')
b = ST.stream(em, None, Z.S0, ST.comps(em, 'floor'), Z.EV)
for lo in (0.7, 0.75, 0.8, 0.85):
    for fac in (1.15, 1.25, 1.5):
        n, _ = mk(lo, fac); d = [(L.eqdd(em, n, V.met(em, b, *w)['MaxDD'], *w) - V.met(em, b, *w)['CAGR']) * 100 for w in (Z.TRAIN, Z.TEST, L.FULL)]; print(f' p>{lo} x{fac}: {d[0]:+.1f} / {d[1]:+.1f} / {d[2]:+.1f}')
print('\nby year equal-DD-free comparison (annual return base -> boost, %):')
n, on = mk(0.8, 1.25); 
for y in range(2017, 2027):
    a, z = f'{y}-01-01', f'{y}-12-31'; print(f' {y}: {((1 + b[a:z]).prod() - 1) * 100:6.1f} -> {((1 + n[a:z]).prod() - 1) * 100:6.1f}  (on {on[a:z].mean():.0%} of days)')
