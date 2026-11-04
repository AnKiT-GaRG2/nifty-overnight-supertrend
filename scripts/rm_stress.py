"""STRESS round: single-day stress cap (G) and scheduled-event cap (E) on v2; rules in PROTOCOL_CHANGES.md ROUND "STRESS".
Run: <venv>/bin/python scripts/rm_stress.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L
from rm_engine import LOT, CAPITAL
from rm_ideas import trial_log
em, ep = L.em, L.ep; FULL, HOLD = L.FULL, L.HOLD; WL, WS = 1.912, 0.956; CR = 0.00025
TEST = ('2024-01-01', '2026-12-31')
ELECT = ['2014-05-16', '2019-05-23', '2024-06-04']
BUDGET = ['2012-03-16', '2013-02-28', '2014-07-10', '2015-02-28', '2016-02-29', '2017-02-01', '2018-02-01', '2019-02-01', '2019-07-05', '2020-02-01', '2021-02-01', '2022-02-01', '2023-02-01', '2024-02-01', '2024-07-23', '2025-02-01', '2026-02-01']

def comps(env, cost):
    En = env['Ea']; lt, lz, st, sz = V.signals(env, 'v2'); fb = np.where(En.first_b)[0]; lb = np.where(En.last_b)[0]; out = []
    for d, s in ((lt, lz), (st, sz)):
        R = En.run(d, s, cost=cost, min_chg=1); net = pd.Series(R.net_d, index=En.days); gap = np.zeros(len(fb)); flag = np.zeros(len(fb))
        for i in range(1, len(fb)):
            gap[i] = R.posl[lb[i - 1]] * LOT * (En.fo[fb[i]] - En.prev[fb[i]]) / CAPITAL; flag[i] = R.posl[lb[i - 1]] != 0
        gap = pd.Series(gap, index=En.days); out += [gap, net - gap, pd.Series(flag, index=En.days)]
    return out                                   # GL, IL, FL, GS, IS, FS

def ev_mask(env, dates):
    days = env['days']; m = pd.Series(False, index=days)
    for d in dates:
        i = days.searchsorted(pd.Timestamp(d))
        if 0 <= i < len(days) and pd.Timestamp(d) >= days[0] and pd.Timestamp(d) <= days[-1]: m.iloc[i] = True
    return m

def stream(env, C, s, cp, ev=None):
    GL, IL, FL, GS, IS, FS = cp; e = env['ens']; mp = e.shift(1).fillna(1.0)
    wG, wI, sG, sI = WL * s * mp, WL * s * e, WS * s, WS * s; one = pd.Series(1.0, index=env['days'])
    fG, fI, fSG, fSI = one.copy(), one.copy(), one.copy(), one.copy()
    if C: fG = np.minimum(1.0, C / wG.clip(lower=1e-9)); fSG = np.minimum(1.0, C / sG)
    if ev is not None:
        fG = np.where(ev, np.minimum(fG, 1.0 / wG.clip(lower=1e-9)), fG); fI = np.where(ev, np.minimum(1.0, 1.0 / wI.clip(lower=1e-9)), fI)
        fSG = np.where(ev, np.minimum(fSG, 1.0 / sG), fSG); fSI = np.where(ev, np.minimum(1.0, 1.0 / sI), fSI)
    fG, fI, fSG, fSI = (pd.Series(x, index=env['days']) for x in (fG, fI, fSG, fSI))
    pnl = WL * s * (mp * GL * fG + e * IL * fI) + WS * s * (GS * fSG + IS * fSI)
    cost = CR * 2 * (wG * (1 - fG) * FL + sG * (1 - fSG) * FS)
    return pnl - cost

CELLS = [('none', None, None), ('G C=2.0', 2.0, None), ('G C=1.5', 1.5, None), ('G C=1.2', 1.2, None), ('E1 elections', None, ELECT), ('E2 elections+budgets', None, ELECT + BUDGET), ('G1.5 + E2', 1.5, ELECT + BUDGET)]
fl = L.fl
if __name__ == '__main__':
    CP = {(w, c): comps(env, c) for w, env in (('FULL', em), ('HOLD', ep)) for c in ('floor', 'real')}
    res = {}
    for name, C, evd in CELLS:
        evm = {w: (ev_mask(env, evd) if evd else None) for w, env in (('FULL', em), ('HOLD', ep))}
        f = lambda s: stream(em, C, s, CP[('FULL', 'floor')], evm['FULL'])
        lo, hi = 0.3, 2.5
        for _ in range(35):
            s = (lo + hi) / 2
            if V.met(em, f(s), *FULL)['MaxDD'] >= -0.177: lo = s
            else: hi = s
        s = lo; row = {}
        for cost in ('floor', 'real'):
            nf = stream(em, C, s, CP[('FULL', cost)], evm['FULL']); nh = stream(ep, C, s, CP[('HOLD', cost)], evm['HOLD'])
            row[cost] = (V.met(em, nf, *FULL), V.met(em, nf, *TEST), V.met(ep, nh, *HOLD), nf)
        nf = row['floor'][3]['2017-04-03':]; res[name] = (s, row)
        trial_log('STRESS', {'cell': name}, 'train', row['floor'][0])
        print(f"\n### {name}: scale {s:.3f} (long {WL * s:.2f}x, short {WS * s:.2f}x); worst day {nf.min():.1%}, days losing >5%: {(nf < -0.05).sum()}, >2%: {(nf < -0.02).sum()}")
        for cost in ('floor', 'real'): print(f'  {cost:5s} FULL {fl(row[cost][0])} | test {fl(row[cost][1])} | HOLD {fl(row[cost][2])}')
    print('\n## Per-event effect (floor costs, scale of E2 cell; total-day P&L as % of capital: no cap vs E2 cap). Positive = cap cost money.')
    s2 = res['E2 elections+budgets'][0]; ev = ev_mask(em, ELECT + BUDGET); a = stream(em, None, s2, CP[('FULL', 'floor')], None); b = stream(em, None, s2, CP[('FULL', 'floor')], ev)
    d = pd.DataFrame({'uncapped': a, 'capped': b})[ev]; d['cost_of_cap'] = d.uncapped - d.capped
    print(d.round(4).to_string()); print('net P&L given up over all FULL events: %.2f%% of capital (sum of daily differences); events where the cap cost money: %d of %d' % (100 * d.cost_of_cap.sum(), (d.cost_of_cap > 0).sum(), len(d)))
    evp = ev_mask(ep, ELECT + BUDGET); ap = stream(ep, None, s2, CP[('HOLD', 'floor')], None); bp = stream(ep, None, s2, CP[('HOLD', 'floor')], evp)
    dp = pd.DataFrame({'uncapped': ap, 'capped': bp})[evp]; dp['cost_of_cap'] = dp.uncapped - dp.capped; print('\nHOLDOUT events (floor):'); print(dp.round(4).to_string()); print('net given up on holdout events: %.2f%% of capital' % (100 * dp.cost_of_cap.sum()))
