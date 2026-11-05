"""v2-FEG at scale 1.142 (section 9) and 1.20 (section 10): per-period CAGR / MaxDD / Sharpe, floor and realistic costs. Run: <venv>/bin/python scripts/rm_v2feg_scale.py"""
import sys, io, contextlib
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import rm_fact3 as Z
import numpy as np, pandas as pd, rm_v2next as V, rm_v2lev as L, rm_stress as ST
em, days, fl = Z.em, Z.days, Z.fl; ON = (Z.pct(Z.F['G22']) > 0.8).fillna(False)
W = {'train': ('2017-04-03', '2021-12-31'), 'valid': ('2022-01-01', '2023-12-31'), 'test': Z.TEST, 'full': L.FULL}
e2 = dict(em); e2['ens'] = em['ens'] * pd.Series(np.where(ON, 1.25, 1.0), index=days)
for s in (1.142, 1.20):
    for nm in ('real', 'floor'):
        n = ST.stream(e2, None, s, ST.comps(em, nm), Z.EV)
        print(s, nm, ' | '.join(f'{k} {fl(V.met(em, n, *w))}' for k, w in W.items()), f'worst {n[L.FULL[0]:L.FULL[1]].min():+.1%}')
