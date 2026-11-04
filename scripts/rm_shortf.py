"""SHORTF round: short-leg-only permission filters with a per-leg noise benchmark (rules in PROTOCOL_CHANGES.md ROUND "SHORTF"). Run: <venv>/bin/python scripts/rm_shortf.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_lossf as LF
from rm_ideas import trial_log
from rm_engine import LOT, CAPITAL
em, ep = L.em, L.ep; FULL, HOLD = L.FULL, L.HOLD; fl = L.fl; ELIST = ST.ELECT + ST.BUDGET; S0 = 1.163
def perm_daily(env, fam, j):
    D = env['S'].D; c = D['close']; days = env['days']; r = c.pct_change()
    if fam == 'F1': p = (r.rolling(5).std() > r.rolling(20).std()).shift(1)
    elif fam == 'F2': p = (LF.prior(days, LF.FX, 5) > [0.005, 0.01, 0.015][j])
    else: swing = D['high'].shift(2).rolling(20).max(); p = ((c < swing) & (c < c.rolling(50).mean())).shift(1)
    return p.reindex(days).fillna(False).astype(bool)
def short_comps(env, perm, cost):
    En, S = env['Ea'], env['S']; raw = V.signals(env, 'v2')[2]; pb = perm.values[S.dc]; size = np.ones(En.N); cur = 1.0; prev = 0
    for t in range(En.N):
        if raw[t] == -1:
            if prev != -1: cur = 1.0 if pb[t] else 0.5
            size[t] = cur
        prev = raw[t]
    R = En.run(raw, size, cost=cost, min_chg=1); fb = np.where(En.first_b)[0]; lb = np.where(En.last_b)[0]; net = pd.Series(R.net_d, index=En.days); gap = np.zeros(len(fb)); flag = np.zeros(len(fb))
    for i in range(1, len(fb)): gap[i] = R.posl[lb[i - 1]] * LOT * (En.fo[fb[i]] - En.prev[fb[i]]) / CAPITAL; flag[i] = R.posl[lb[i - 1]] != 0
    gap = pd.Series(gap, index=En.days); return gap, net - gap, pd.Series(flag, index=En.days)
CELLS = [('F1', 0, 'F1 vol5>vol20')] + [('F2', j, f'F2 USDINR 5d > {x}%') for j, x in enumerate((0.5, 1.0, 1.5))] + [('F3', 0, 'F3 below swing high & 50d mean')]
if __name__ == '__main__':
    rng = np.random.default_rng(1104); CP = {w: ST.comps(env, 'floor') for w, env in (('FULL', em), ('HOLD', ep))}; EV = {'FULL': ST.ev_mask(em, ELIST), 'HOLD': ST.ev_mask(ep, ELIST)}
    bF = V.met(em, ST.stream(em, None, S0, CP['FULL'], EV['FULL']), *FULL); bH = V.met(ep, ST.stream(ep, None, S0, CP['HOLD'], EV['HOLD']), *HOLD)
    print(f'v2-FE floor: FULL {fl(bF)} | HOLD {fl(bH)}\n'); ok_all = True
    def combined(env, w, perm): g, i, f = short_comps(env, perm, 'floor'); c = CP[w]; return ST.stream(env, None, S0, (c[0], c[1], c[2], g, i, f), EV[w])
    for fam, j, name in CELLS:
        pF, pH = perm_daily(em, fam, j), perm_daily(ep, fam, j); nF, nH = combined(em, 'FULL', pF), combined(ep, 'HOLD', pH)
        eF = L.eqdd(em, nF, bF['MaxDD'], *FULL) - bF['CAGR']; eH = L.eqdd(ep, nH, bH['MaxDD'], *HOLD) - bH['CAGR']; null = []
        for _ in range(200):
            k = int(rng.integers(60, len(pF) - 60)); ps = pd.Series(np.roll(pF.values, k), index=pF.index)
            null.append(L.eqdd(em, combined(em, 'FULL', ps), bF['MaxDD'], *FULL) - bF['CAGR'])
        p95 = np.percentile(null, 95); beat = (np.array(null) < eF).mean(); trial_log('SHORTF_' + fam, {'j': j}, 'train', V.met(em, nF, *FULL)); ok = eF > p95 and eF > 0 and eH > 0; ok_all &= ok
        print(f'{name}: permission on {pF["2017-04-03":].mean():.0%} of days | FULL {fl(V.met(em, nF, *FULL))} | equal-DD delta FULL {eF * 100:+.1f} pts, HOLD {eH * 100:+.1f} pts | null median {np.median(null) * 100:+.1f}, p95 {p95 * 100:+.1f}, beats {beat:.0%} | {"ok" if ok else "no"}')
    print('\nSHORTF verdict:', 'PASS' if ok_all else 'FAIL (at least one cell missed the rule)')
