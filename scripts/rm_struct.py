"""STRUCT round (rules in PROTOCOL_CHANGES.md ROUND "STRUCT"). Run: <venv>/bin/python scripts/rm_struct.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
from rm_engine import LOT, CAPITAL
from rm_signals import supertrend
em = L.em; fl = L.fl; S = em['S']; En = em['Ea']; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; ELIST = ST.ELECT + ST.BUDGET; EV = ST.ev_mask(em, ELIST)
CFG = [(n, m) for n in (10, 14, 20) for m in (2.5, 3.0, 3.5)]; STS = np.array([supertrend(S.h, S.l, S.c, n, m)[0] for n, m in CFG])
DST = np.asarray(S.dst_daily(10, 3.0), float); SMA = np.asarray(S.sma_daily(100), float); DCL = S.dd.close.values
def comps(lt, lz, cost, mc):
    st_, sz_ = V.signals(em, 'v2')[2], V.signals(em, 'v2')[3]; fb = np.where(En.first_b)[0]; lb = np.where(En.last_b)[0]; out = []
    for d, s, m in ((lt, lz, mc), (st_, sz_, 1)):
        R = En.run(d, s, cost=cost, min_chg=m); net = pd.Series(R.net_d, index=En.days); gap = np.zeros(len(fb)); flag = np.zeros(len(fb))
        for i in range(1, len(fb)): gap[i] = R.posl[lb[i - 1]] * LOT * (En.fo[fb[i]] - En.prev[fb[i]]) / CAPITAL; flag[i] = R.posl[lb[i - 1]] != 0
        gap = pd.Series(gap, index=En.days); out += [gap, net - gap, pd.Series(flag, index=En.days)]
    return out
def sig(idea, share=None, dst=None, drift=None):
    st = (S.st == 1)
    if idea == 'S1': return (share > 0).astype(np.int8), share, 2
    if idea == 'S2': dd = S.d2b(dst); return st.astype(np.int8), np.where(dd == 1, 1.0, 0.5), 2
    if idea == 'S3':
        dr = S.d2b(drift.astype(float)) == 1; return (st | dr).astype(np.int8), np.where(st, 1.0, np.where(dr, 0.25, 0.0)), 2
def run(idea, **kw):
    lt, lz, mc = sig(idea, **kw); lt = np.asarray(lt); return comps(lt, np.asarray(lz, float), 'floor', mc)
def eqd(cp, ref_dd, win, ws=ST.WS):
    old = ST.WS; ST.WS = ws
    try: n = ST.stream(em, None, S0, cp, EV); return L.eqdd(em, n, ref_dd, *win)
    finally: ST.WS = old
def solve(cp, ws=ST.WS):
    old = ST.WS; ST.WS = ws; lo, hi = 0.3, 3.0
    try:
        for _ in range(35):
            s = (lo + hi) / 2
            if V.met(em, ST.stream(em, None, s, cp, EV), *TRAIN)['MaxDD'] >= -0.177: lo = s
            else: hi = s
        return lo, ST.stream(em, None, lo, cp, EV)
    finally: ST.WS = old
if __name__ == '__main__':
    base_cp = ST.comps(em, 'floor'); bnet = ST.stream(em, None, S0, base_cp, EV); bT = V.met(em, bnet, *TRAIN); bX = V.met(em, bnet, *TEST); rng = np.random.default_rng(3611)
    print(f'v2-FE (scale {S0}): TRAIN {fl(bT)} | TEST {fl(bX)}\n'); res = {}
    cases = [('S1 ensemble (long-only share)', 'S1', dict(share=STS.__eq__(1).mean(0))), ('S2 two-timeframe', 'S2', dict(dst=DST)), ('S3 drift floor 0.25', 'S3', dict(drift=pd.Series(DCL > SMA).values if False else (S.d2b(DCL) > S.d2b(SMA))))]
    # S3 uses prior-day values already inside d2b: build daily array drift_d = close > sma (day d) then d2b shifts by one day
    drift_d = pd.Series(DCL > SMA).values; cases[2] = ('S3 drift floor 0.25', 'S3', dict(drift=drift_d))
    for name, idea, kw in cases:
        cp = run(idea, **kw); d_ = eqd(cp, bT['MaxDD'], TRAIN) - bT['CAGR']; s, net = solve(cp); null = []
        for _ in range(200):
            if idea == 'S1': k = int(rng.integers(60, S.N - 60)); kw2 = dict(share=np.roll(kw['share'], k))
            elif idea == 'S2': k = int(rng.integers(60, len(DST) - 60)); kw2 = dict(dst=np.roll(DST, k))
            else: k = int(rng.integers(60, len(drift_d) - 60)); kw2 = dict(drift=np.roll(drift_d, k))
            null.append(eqd(run(idea, **kw2), bT['MaxDD'], TRAIN) - bT['CAGR'])
        p95 = np.percentile(null, 95); keep = d_ > 0 and d_ > p95; trial_log('STRUCT_' + idea, {}, 'train', V.met(em, net, *TRAIN))
        print(f'{name}: at scale {s:.3f} TRAIN {fl(V.met(em, net, *TRAIN))} | TEST {fl(V.met(em, net, *TEST))} || equal-DD delta TRAIN {d_ * 100:+.1f} pts (null median {np.median(null) * 100:+.1f}, p95 {p95 * 100:+.1f}, beats {(np.array(null) < d_).mean():.0%}) -> {"KEEP" if keep else "no"}')
    s, net = solve(base_cp, ws=1e-9); d4 = V.met(em, net, *TRAIN)['CAGR'] - bT['CAGR']; trial_log('STRUCT_S4', {}, 'train', V.met(em, net, *TRAIN))
    print(f'S4 long-only: scale {s:.3f} (long {1.912 * s:.2f}x) TRAIN {fl(V.met(em, net, *TRAIN))} | TEST {fl(V.met(em, net, *TEST))} || delta vs v2-FE TRAIN {d4 * 100:+.1f} pts -> {"KEEP" if d4 > 0 else "no (shorts earn their place)"}')
