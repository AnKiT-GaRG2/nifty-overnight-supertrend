"""v2-FEG = v2-FE + long boost x1.25 when |prior-day opening gap| is in its top 20% of the prior 365 days (FACT3, adopted by the user 2026-11-05).
Solves the scale so FULL floor-cost MaxDD = -17.7% and prints the table. Run: <venv>/bin/python scripts/rm_v2feg.py"""
import sys, os, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import rm_fact3 as Z
import numpy as np, pandas as pd, rm_v2next as V, rm_v2lev as L, rm_stress as ST
em, days, fl = Z.em, Z.days, Z.fl; ON = (Z.pct(Z.F['G22']) > 0.8).fillna(False)
W = {'train 2017-04..2021': ('2017-04-03', '2021-12-31'), 'valid 2022-23': ('2022-01-01', '2023-12-31'), 'TEST 2024-26': Z.TEST, 'FULL 2017-04..2026-10': L.FULL}
def stream(s, cp, boost=True):
    e2 = dict(em); e2['ens'] = em['ens'] * pd.Series(np.where(ON & boost, 1.25, 1.0), index=days); return ST.stream(e2, None, s, cp, Z.EV)
cf, cr = ST.comps(em, 'floor'), ST.comps(em, 'real')
lo, hi = 0.3, 3.0
for _ in range(35):
    s = (lo + hi) / 2
    if V.met(em, stream(s, cf), *L.FULL)['MaxDD'] >= -0.177: lo = s
    else: hi = s
s = lo; print(f'v2-FEG scale {s:.3f}: long {1.912 * s:.2f}x (boosted days {1.912 * s * 1.25:.2f}x) / short {0.956 * s:.2f}x; boost on {ON[L.FULL[0]:L.FULL[1]].mean():.0%} of days')
for cost, cp in (('floor', cf), ('real', cr)):
    n = stream(s, cp); print(f'\n{cost} costs (CAGR / MaxDD / Sharpe):'); [print(f' {k:24s} {fl(V.met(em, n, *w))}') for k, w in W.items()]
    d = n[L.FULL[0]:L.FULL[1]]; print(f' worst day {d.min():+.1%}')
print('\nfor reference v2-FE (scale 1.163, no boost):'); b = ST.stream(em, None, 1.163, cf, Z.EV); print(' floor FULL', fl(V.met(em, b, *L.FULL)), '| realistic FULL', fl(V.met(em, ST.stream(em, None, 1.163, cr, Z.EV), *L.FULL)))
