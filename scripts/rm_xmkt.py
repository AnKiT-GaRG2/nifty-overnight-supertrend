"""XMKT: cross-market long-leg factors (DXY, EEM, HYG/IEF). Run: <venv>/bin/python scripts/rm_xmkt.py diag|test"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_lossf as LF, rm_noise as NZ, rm_ddsplit as DS
from rm_ideas import trial_log, DATA
em = L.em; days = em['days']; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; fl = L.fl; EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET)
def rd(n, col): return pd.read_csv(f'{DATA}/xmkt/{n}.csv', parse_dates=['date']).set_index('date')[col].astype(float)
DXY, EEM, HYG, IEF = rd('DX_Y_NYB', 'close'), rd('EEM', 'adjclose'), rd('HYG', 'adjclose'), rd('IEF', 'adjclose'); RATIO = (HYG / IEF).dropna()
def state(fam, L_):
    if fam == 'X1': s = (DXY > DXY.rolling(L_).mean()) & (DXY / DXY.shift(20) - 1 > 0)
    elif fam == 'X2': s = EEM < EEM.rolling(L_).mean()
    else: s = RATIO < RATIO.rolling(L_).mean()
    return s.astype(float)
def on(fam, L_): v = NZ.prior_val(days, state(fam, L_)); return (v == 1).reindex(days).fillna(False)        # value dated strictly before the Indian day
SPEC = {'X1': 50, 'X2': 100, 'X3': 50}
def diag():
    cp = ST.comps(em, 'floor'); net = ST.stream(em, None, S0, cp, EV); long, short, cost = DS.legs_pnl(em, cp, EV)
    a, z = TRAIN; r = (net + em['INT'])[a:z]; eq = (1 + r).cumprod(); dd = eq / eq.cummax() - 1; under = dd < 0; grp = (~under).cumsum()[under]; rows = []
    for g, idx in dd[under].groupby(grp): tr = idx.idxmin(); rows.append((idx.min(), eq[:tr].idxmax(), tr))
    rows = sorted(rows)[:5]; print('TRAIN-only five deepest v2-FE drawdowns (floor): ' + '; '.join(f'{d:.1%} {p.date()}..{t.date()}' for d, p, t in rows))
    lm = long[a:z].groupby([long[a:z].index.year, long[a:z].index.month]).sum(); nb = max(int(round(0.1 * len(lm))), 1); best = lm.nlargest(nb); bm = set(best.index)
    mask = pd.Series([(d.year, d.month) in bm for d in days], index=days)[a:z]; print(f'best long-leg months (top 10% = {nb} of {len(lm)}): ' + ', '.join(f'{y}-{m:02d} ({v:+.0%})' for (y, m), v in best.items()) + '\n')
    print('| factor (spec) | on-share of all TRAIN days | on in drawdowns (>=50% of days peak->trough) | share of best-month days on | gate |'); print('|---|---|---|---|---|'); gate = {}
    for fam, L_ in SPEC.items():
        o = on(fam, L_); share = o[a:z].mean(); per = [(o[p:t].mean()) for _, p, t in rows]; k = sum(x >= 0.5 for x in per); bshare = o[a:z][mask].mean()
        gate[fam] = k >= 3 and bshare <= 0.25
        print(f"| {fam} (L={L_}) | {share:.0%} | {k} of 5 ({', '.join(f'{x:.0%}' for x in per)}) | {bshare:.0%} | {'TEST' if gate[fam] else 'SKIP'} |")
    return gate
if __name__ == '__main__':
    g = diag() if (len(sys.argv) < 2 or sys.argv[1] == 'diag') else None
