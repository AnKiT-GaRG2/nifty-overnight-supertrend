"""SHORT2 round (rules in PROTOCOL_CHANGES.md ROUND "SHORT2"). Run: <venv>/bin/python scripts/rm_short2.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_batch2 as B, rm_struct as R, rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
from rm_signals import supertrend
em, S, En = B.em, B.S, B.En; TRAIN, TEST, S0, EV = B.TRAIN, B.TEST, B.S0, B.EV; fl = L.fl; N = B.N; one = B.one; ST3 = B.ST3
SMA100 = np.asarray(S.sma_daily(100), float); PC = S.d2b(B.DCL); SM = S.d2b(SMA100); BELOW = (PC < SM)
LOWD = S.D['low'].values
def long_base(): return (ST3 == 1).astype(np.int8)
def run(sd, sz): return B.comps2(long_base(), one, 1, sd, sz, 1)[0]
def sA(m): stm = supertrend(S.h, S.l, S.c, 14, m)[0]; return run(np.where((stm == -1) & BELOW, -1, 0).astype(np.int8), one)
def sD(p200=B.P200):
    b200 = np.nan_to_num(S.d2b(p200)) == 1; sd = B.SH_BASE; sz = np.ones(N); cur = 1.0; prev = 0
    for t in range(N):
        if sd[t] == -1:
            if prev != -1: cur = 1.5 if b200[t] else 1.0
            sz[t] = cur
        prev = sd[t]
    return run(sd, sz)
def sC(lowd=LOWD):
    plow = S.d2b(lowd); out = np.zeros(N, np.int8); prev = 0
    for t in range(N):
        if B.SH_BASE[t] == -1:
            if prev == -1: out[t] = -1
            elif S.c[t] < plow[t]: out[t] = -1
        prev = out[t]
    return run(out, one)
def sE():
    sd = B.SH_BASE; sz = np.ones(N); prev = 0; ec = atr = 0.0; added = False; stopped = False
    for t in range(N):
        if sd[t] == -1:
            if prev != -1: ec, atr, added, stopped = S.c[t], S.atr15[t], False, False
            elif not stopped:
                if added and S.c[t] >= ec: added, stopped = False, True
                elif not added and S.c[t] <= ec - 2 * atr: added = True
            sz[t] = 1.5 if added else 1.0
        prev = sd[t]
    return run(sd, sz)
if __name__ == '__main__':
    base_cp = ST.comps(em, 'floor'); bnet = ST.stream(em, None, S0, base_cp, EV); bT = V.met(em, bnet, *TRAIN); rng = np.random.default_rng(5611); res = {}
    print(f'v2-FE floor (scale {S0}): TRAIN {fl(bT)} | TEST {fl(V.met(em, bnet, *TEST))}\n')
    def ev(name, fn, nullfn=None):
        cp = fn(); delta = B.eqd(cp, bT['MaxDD'], TRAIN) - bT['CAGR']; s, net = B.solve(cp); n0 = ST.stream(em, None, S0, cp, EV); trial_log('SHORT2_' + name.split()[0], {}, 'train', V.met(em, net, *TRAIN))
        if nullfn: null = [B.eqd(nullfn(), bT['MaxDD'], TRAIN) - bT['CAGR'] for _ in range(200)]; p95 = np.percentile(null, 95); keep = delta > 0 and delta > p95; bm = f'shift null median {np.median(null) * 100:+.1f}, p95 {p95 * 100:+.1f}, beats {(np.array(null) < delta).mean():.0%}'
        else: p5 = B.boot_p5((n0 - bnet)[TRAIN[0]:TRAIN[1]], rng); keep = delta > 0 and p5 > 0; bm = f'bootstrap 5th pct of mean daily diff {p5 * 1e4:+.2f} bp'
        res[name] = (delta, keep); print(f'{name}: scale {s:.3f} TRAIN {fl(V.met(em, net, *TRAIN))} | TEST {fl(V.met(em, net, *TEST))} || delta TRAIN {delta * 100:+.1f} pts; {bm} -> {"KEEP" if keep else "no"}')
    ev('A m=2.0', lambda: sA(2.0)); ev('A m=2.5', lambda: sA(2.5))
    ev('D 1.5x below SMA100&200', lambda: sD(), lambda: sD(np.roll(B.P200, int(rng.integers(60, len(B.P200) - 60)))))
    if all(v[0] <= 0 for v in res.values()): print('\nBATCH A (A, D) all fail outright -> STOP, C and E not run.')
    else:
        print('\nnot all failing outright -> running C and E')
        ev('C breakdown confirmation', lambda: sC(), lambda: sC(np.roll(LOWD, int(rng.integers(60, len(LOWD) - 60))))); ev('E pyramiding', sE)
    print('\nkept:', [k for k, v in res.items() if v[1]])
