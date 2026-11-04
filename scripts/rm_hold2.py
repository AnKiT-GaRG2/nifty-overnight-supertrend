"""HOLD2: pre-declared holdout check of H1 (Tier B events), H2 (15:15-bar short entries), H3 (two-timeframe long size). Rules in PROTOCOL_CHANGES.md ROUND "HOLD2". Run: <venv>/bin/python scripts/rm_hold2.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
from rm_engine import LOT, CAPITAL
em, ep = L.em, L.ep; HOLD = L.HOLD; TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; fl = L.fl
TIERB = ['2012-11-07', '2016-06-24', '2016-11-09', '2016-12-05', '2020-11-04', '2024-11-06']
def comps(env, lt, lz, mcl, sd, sz, mcs, cost='floor'):
    En = env['Ea']; fb = np.where(En.first_b)[0]; lb = np.where(En.last_b)[0]; out = []
    for d, s, m in ((lt, lz, mcl), (sd, sz, mcs)):
        R = En.run(np.asarray(d, np.int8), np.asarray(s, float), cost=cost, min_chg=m); net = pd.Series(R.net_d, index=En.days); gap = np.zeros(len(fb)); flag = np.zeros(len(fb))
        for i in range(1, len(fb)): gap[i] = R.posl[lb[i - 1]] * LOT * (En.fo[fb[i]] - En.prev[fb[i]]) / CAPITAL; flag[i] = R.posl[lb[i - 1]] != 0
        gap = pd.Series(gap, index=En.days); out += [gap, net - gap, pd.Series(flag, index=En.days)]
    return out
def sigs(env):
    lt, lz, st, sz = V.signals(env, 'v2'); return lt, lz, st, sz
def base_cp(env): return ST.comps(env, 'floor')
def h2_cp(env):
    lt, lz, st, sz = sigs(env); K = env['Ea'].bar_k; out = np.zeros(len(st), np.int8); pos = 0
    for t in range(len(st)):
        if st[t] == -1 and (pos == -1 or K[t] == 23): out[t] = -1
        pos = out[t]
    return comps(env, lt, lz, 1, out, np.ones(len(st)), 1)
def h3_cp(env):
    S = env['S']; lt, lz, st, sz = sigs(env); dst = np.asarray(S.dst_daily(10, 3.0), float); return comps(env, lt, np.where(S.d2b(dst) == 1, 1.0, 0.5), 2, st, sz, 1), dst
def h3_shift(env, dst, k):
    S = env['S']; lt, lz, st, sz = sigs(env); return comps(env, lt, np.where(S.d2b(np.roll(dst, k)) == 1, 1.0, 0.5), 2, st, sz, 1)
def boot_p5(d, rng, blk=20, n=1000):
    x = d.values; T = len(x); nb = int(np.ceil(T / blk)); m = []
    for _ in range(n):
        st = rng.integers(0, T - blk, nb); m.append(np.concatenate([x[s:s + blk] for s in st])[:T].mean())
    return np.percentile(np.array(m) - x.mean(), 5) + x.mean()           # 5th pct of the bootstrap mean (centred on the sample)
def run():
    rng = np.random.default_rng(1105); NT0 = len(__import__('json').load(open(f'{V.RES}/trials.json')))
    E = {w: (env, win) for w, env, win in (('HOLD', ep, HOLD), ('TEST', em, TEST))}
    ev = {w: ST.ev_mask(env, ST.ELECT + ST.BUDGET) for w, (env, _) in E.items()}
    B = {w: base_cp(env) for w, (env, _) in E.items()}
    bnet = {w: ST.stream(env, None, S0, B[w], ev[w]) for w, (env, _) in E.items()}; bm = {w: V.met(E[w][0], bnet[w], *E[w][1]) for w in E}
    print('base v2-FE (floor):', {w: fl(bm[w]) for w in E}, '\n')
    def delta(w, net): env, win = E[w]; return L.eqdd(env, net, bm[w]['MaxDD'], *win) - bm[w]['CAGR']
    res = {}
    # H1
    evB = {w: ST.ev_mask(env, ST.ELECT + ST.BUDGET + TIERB) for w, (env, _) in E.items()}
    nB = {w: ST.stream(E[w][0], None, S0, B[w], evB[w]) for w in E}; dH, dT = delta('HOLD', nB['HOLD']), delta('TEST', nB['TEST'])
    null = []
    for _ in range(200):
        k = int(rng.integers(60, 1000)); m = pd.Series(np.roll(ST.ev_mask(ep, TIERB).values, k), index=ep['days']) | ev['HOLD']; null.append(delta('HOLD', ST.stream(ep, None, S0, B['HOLD'], m)))
    p95 = np.percentile(null, 95); ok = dH > 0 and dH > p95 and dT >= 0; res['H1'] = ok; trial_log('HOLD2_H1', {}, 'holdout', V.met(ep, nB['HOLD'], *HOLD))
    print(f"H1 Tier B events: HOLD {fl(V.met(ep, nB['HOLD'], *HOLD))} delta {dH * 100:+.2f} pts (null p95 {p95 * 100:+.2f}, beats {(np.array(null) < dH).mean():.0%}); TEST delta {dT * 100:+.2f} -> {'PASS' if ok else 'FAIL'}")
    d = pd.DataFrame({'base': bnet['HOLD'], 'capB': nB['HOLD']})[ST.ev_mask(ep, TIERB) & ~ev['HOLD']]; print('   per-event HOLD (base vs capped day P&L):\n', d.round(4).to_string())
    # H2
    cp = {w: h2_cp(E[w][0]) for w in E}; n2 = {w: ST.stream(E[w][0], None, S0, cp[w], ev[w]) for w in E}; dH, dT = delta('HOLD', n2['HOLD']), delta('TEST', n2['TEST'])
    p5 = boot_p5((n2['HOLD'] - bnet['HOLD'])[HOLD[0]:HOLD[1]], rng); ok = dH > 0 and p5 > 0 and dT >= 0; res['H2'] = ok; trial_log('HOLD2_H2', {}, 'holdout', V.met(ep, n2['HOLD'], *HOLD))
    print(f"H2 15:15-bar short entries: HOLD {fl(V.met(ep, n2['HOLD'], *HOLD))} delta {dH * 100:+.2f} pts, boot 5th pct mean daily diff {p5 * 1e4:+.2f} bp; TEST delta {dT * 100:+.2f} -> {'PASS' if ok else 'FAIL'}")
    # H3
    cps, dsts = {}, {}
    for w in E: cps[w], dsts[w] = h3_cp(E[w][0])
    n3 = {w: ST.stream(E[w][0], None, S0, cps[w], ev[w]) for w in E}; dH, dT = delta('HOLD', n3['HOLD']), delta('TEST', n3['TEST']); null = []
    for _ in range(200):
        k = int(rng.integers(60, len(dsts['HOLD']) - 60)); null.append(delta('HOLD', ST.stream(ep, None, S0, h3_shift(ep, dsts['HOLD'], k), ev['HOLD'])))
    p95 = np.percentile(null, 95); ok = dH > 0 and dH > p95 and dT >= 0; res['H3'] = ok; trial_log('HOLD2_H3', {}, 'holdout', V.met(ep, n3['HOLD'], *HOLD))
    print(f"H3 two-timeframe long size: HOLD {fl(V.met(ep, n3['HOLD'], *HOLD))} delta {dH * 100:+.2f} pts (null median {np.median(null) * 100:+.2f}, p95 {p95 * 100:+.2f}, beats {(np.array(null) < dH).mean():.0%}); TEST delta {dT * 100:+.2f} -> {'PASS' if ok else 'FAIL'}")
    print('\nPASSED:', [k for k, v in res.items() if v], f'| trials {NT0} -> {len(__import__("json").load(open(f"{V.RES}/trials.json")))}')
if __name__ == '__main__': run()
