"""Diagnostic (no trials): split v2-FE's deepest drawdown stretches into long-leg and short-leg P&L. Run: <venv>/bin/python scripts/rm_ddsplit.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
em = L.em; ELIST = ST.ELECT + ST.BUDGET; S = 1.163; WL, WS = ST.WL, ST.WS
def legs_pnl(env, cp, ev, s=S):
    GL, IL, FL, GS, IS, FS = cp; e = env['ens']; mp = e.shift(1).fillna(1.0); one = pd.Series(1.0, index=env['days'])
    wG, wI = WL * s * mp, WL * s * e; sG = WS * s
    fG = np.where(ev, 1.0 / wG.clip(lower=1e-9), 1.0).clip(max=1.0) if False else pd.Series(np.where(ev, np.minimum(1.0, 1.0 / wG.clip(lower=1e-9)), 1.0), index=env['days'])
    fI = pd.Series(np.where(ev, np.minimum(1.0, 1.0 / (WL * s * e).clip(lower=1e-9)), 1.0), index=env['days'])
    fSG = pd.Series(np.where(ev, np.minimum(1.0, 1.0 / sG), 1.0), index=env['days']); fSI = fSG
    long = WL * s * (mp * GL * fG + e * IL * fI); short = WS * s * (GS * fSG + IS * fSI); cost = ST.CR * 2 * (wG * (1 - fG) * FL + sG * (1 - fSG) * FS)
    return long, short, cost
if __name__ == '__main__':
    cp = ST.comps(em, 'floor'); ev = ST.ev_mask(em, ELIST); long, short, cost = legs_pnl(em, cp, ev); net = long + short - cost
    assert np.allclose(net, ST.stream(em, None, S, cp, ev)), 'leg split does not reproduce v2-FE'
    a = '2017-04-03'; r = (net + em['INT'])[a:]; eq = (1 + r).cumprod(); peak = eq.cummax(); dd = eq / peak - 1
    under = dd < 0; grp = (~under).cumsum()[under]; rows = []
    for g, idx in dd[under].groupby(grp):
        tr = idx.idxmin(); pk = eq[:tr].idxmax(); rows.append((idx.min(), pk, tr, idx.index[-1]))
    rows = sorted(rows)[:5]
    print('FULL-period v2-FE (floor costs, scale 1.163): five deepest drawdowns, P&L from equity peak to trough, % of capital (simple sum of daily returns)\n')
    print('| # | depth | peak -> trough | long leg | short leg | event/other costs | interest | driver |'); print('|---|---|---|---|---|---|---|---|')
    for i, (d, pk, tr, end) in enumerate(rows, 1):
        w = slice(pk + pd.Timedelta(days=1), tr); l, s_, c, it = long[w].sum(), short[w].sum(), cost[w].sum(), em['INT'][w].sum()
        drv = 'long leg' if abs(l) > abs(s_) and l < 0 else ('short leg' if s_ < 0 and abs(s_) >= abs(l) else 'mixed')
        print(f'| {i} | {d:.1%} | {pk.date()} -> {tr.date()} | {l:+.1%} | {s_:+.1%} | {-c:+.1%} | {it:+.1%} | {drv} |')
    print(f'\nWhole-period leg totals (sum of daily % of capital): long {100 * long[a:].sum():+.0f}%, short {100 * short[a:].sum():+.0f}%')
    tr_s = (short[a:] != 0); print(f'short leg: days with P&L != 0: {100 * tr_s.mean():.0f}%; of those days, share losing: {100 * (short[a:] < 0).sum() / max(tr_s.sum(), 1):.0f}%')
