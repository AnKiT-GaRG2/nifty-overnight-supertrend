"""BATCH2 round: ideas 5, 6, 10 (batch A) and 7, 8 (batch B); rules in PROTOCOL_CHANGES.md ROUND "BATCH2". Run: <venv>/bin/python scripts/rm_batch2.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_struct as R, rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
from rm_engine import LOT, CAPITAL
from rm_signals import supertrend
em, En, S = R.em, R.En, R.S; TRAIN, TEST, S0, EV = R.TRAIN, R.TEST, R.S0, R.EV; fl = L.fl
K = En.bar_k; DC = S.dc; N = S.N; ST3 = S.st.astype(int); DCL = S.dd.close.values; one = np.ones(N)
SH_BASE = V.signals(em, 'v2')[2]
def comps2(lt, lz, mcl, sd, sz, mcs, cost='floor'):
    fb = np.where(En.first_b)[0]; lb = np.where(En.last_b)[0]; out = []
    for d, s, m in ((lt, lz, mcl), (sd, sz, mcs)):
        Rr = En.run(np.asarray(d, np.int8), np.asarray(s, float), cost=cost, min_chg=m); net = pd.Series(Rr.net_d, index=En.days); gap = np.zeros(len(fb)); flag = np.zeros(len(fb))
        for i in range(1, len(fb)): gap[i] = Rr.posl[lb[i - 1]] * LOT * (En.fo[fb[i]] - En.prev[fb[i]]) / CAPITAL; flag[i] = Rr.posl[lb[i - 1]] != 0
        gap = pd.Series(gap, index=En.days); out += [gap, net - gap, pd.Series(flag, index=En.days)]
    return out, Rr
def donch_arr():
    c = S.D['close']; hh = c.rolling(20).max().shift(1).values; ll = c.rolling(20).min().shift(1).values; s = 0; out = np.zeros(len(c))
    for i, v in enumerate(c.values):
        if v > hh[i]: s = 1
        elif v < ll[i]: s = 0
        out[i] = s
    return out
MA_ARR = (S.D['close'].rolling(20).mean() > S.D['close'].rolling(50).mean()).astype(float).values; DON_ARR = donch_arr()
SMA200 = np.asarray(S.sma_daily(200), float); P200 = (DCL < SMA200).astype(float)
def sig_I5(don=DON_ARR, ma=MA_ARR):
    size = ((ST3 == 1).astype(float) + np.nan_to_num(S.d2b(don)) + np.nan_to_num(S.d2b(ma))) / 3.0; return comps2((size > 0), size, 2, SH_BASE, one, 1)
def sig_I6():
    st4 = supertrend(S.h, S.l, S.c, 14, 4.0)[0]; lng = np.zeros(N, np.int8); cur = 0; armed = True
    for t in range(N):
        if cur == 0:
            if ST3[t] == 1 and armed: cur = 1
            elif ST3[t] == -1: armed = True
        elif st4[t] == -1: cur = 0; armed = False
        lng[t] = cur
    sh = np.where(lng == 0, SH_BASE, 0).astype(np.int8); return comps2(lng, one, 1, sh, one, 1)
def sig_I10(p200=P200):
    allow = np.nan_to_num(S.d2b(p200)) == 1; sh = np.where((ST3 == -1) & allow, -1, 0).astype(np.int8); return comps2((ST3 == 1), one, 1, sh, one, 1)
def sig_I7():
    lt = (ST3 == 1).astype(np.int8); Rr = En.run(lt, one, cost='floor', min_chg=1); size = np.ones(N); half = False; cl = 0
    for tr in sorted(Rr.trades.tolist(), key=lambda r: r[0]):
        if tr[2] != 1: continue
        eb, xb = int(tr[0]), int(tr[1])
        if half: size[max(eb - 1, 0):xb] = 0.5
        if tr[6] - tr[7] > 0: cl = 0; half = False
        else:
            cl += 1
            if cl >= 2: half = True
    return comps2(lt, size, 1, SH_BASE, one, 1)
def sig_I8():
    lt = (ST3 == 1).astype(np.int8); prev = np.r_[0, ST3[:-1]]; lt[(K == 0) & (ST3 == 1) & (prev != 1)] = 0; return comps2(lt, one, 1, SH_BASE, one, 1)
def eqd(cp, ref, win): return L.eqdd(em, ST.stream(em, None, S0, cp, EV), ref, *win)
def solve(cp):
    lo, hi = 0.3, 3.5
    for _ in range(35):
        s = (lo + hi) / 2
        if V.met(em, ST.stream(em, None, s, cp, EV), *TRAIN)['MaxDD'] >= -0.177: lo = s
        else: hi = s
    return lo, ST.stream(em, None, lo, cp, EV)
def boot_p5(d, rng, B=1000, blk=20):
    d = d.values; n = len(d); m = []
    for _ in range(B):
        idx = []; 
        while len(idx) < n: s = int(rng.integers(0, n)); idx += [(s + j) % n for j in range(blk)]
        m.append(d[idx[:n]].mean())
    return np.percentile(m, 5)
if __name__ == '__main__':
    base_cp = ST.comps(em, 'floor'); bnet = ST.stream(em, None, S0, base_cp, EV); bT = V.met(em, bnet, *TRAIN); bX = V.met(em, bnet, *TEST); rng = np.random.default_rng(4611)
    print(f'v2-FE floor (scale {S0}): TRAIN {fl(bT)} | TEST {fl(bX)}\n'); out = {}
    def evaluate(name, fn, nullfn=None):
        (cp, Rr) = fn(); delta = eqd(cp, bT['MaxDD'], TRAIN) - bT['CAGR']; s, net = solve(cp); n0 = ST.stream(em, None, S0, cp, EV); trial_log('BATCH2_' + name, {}, 'train', V.met(em, net, *TRAIN))
        if nullfn is not None:
            null = [eqd(nullfn(), bT['MaxDD'], TRAIN) - bT['CAGR'] for _ in range(200)]; p95 = np.percentile(null, 95); keep = delta > 0 and delta > p95; bm = f'shift null median {np.median(null) * 100:+.1f}, p95 {p95 * 100:+.1f}, beats {(np.array(null) < delta).mean():.0%}'
        else:
            p5 = boot_p5((n0 - bnet)[TRAIN[0]:TRAIN[1]], rng); keep = delta > 0 and p5 > 0; bm = f'bootstrap 5th pct of mean daily difference {p5 * 1e4:+.2f} bp'
        out[name] = (delta, keep); print(f'{name}: at scale {s:.3f} TRAIN {fl(V.met(em, net, *TRAIN))} | TEST {fl(V.met(em, net, *TEST))} || equal-DD delta TRAIN {delta * 100:+.1f} pts; {bm} -> {"KEEP" if keep else "no"}')
    def null5(): k = int(rng.integers(60, len(DON_ARR) - 60)); return sig_I5(np.roll(DON_ARR, k), np.roll(MA_ARR, k))[0]
    def null10(): k = int(rng.integers(60, len(P200) - 60)); return sig_I10(np.roll(P200, k))[0]
    evaluate('I5 signal-type ensemble', lambda: sig_I5(), null5); evaluate('I6 enter 3 / exit 4', sig_I6); evaluate('I10 shorts below SMA200', lambda: sig_I10(), null10)
    if all(v[0] <= 0 for v in out.values()): print('\nBATCH A: all three fail outright -> STOP, batch B not run.')
    else:
        print('\nBATCH A not all failing outright -> running batch B'); evaluate('I7 loss-streak half size', sig_I7); evaluate('I8 no new long on first bar', sig_I8)
    print('\nkept:', [k for k, v in out.items() if v[1]])
