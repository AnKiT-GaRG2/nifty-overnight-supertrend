"""SHORT3 round (rules in PROTOCOL_CHANGES.md ROUND "SHORT3"). Run: <venv>/bin/python scripts/rm_short3.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_batch2 as B, rm_struct as R, rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_short2 as S2, rm_events as E
from rm_ideas import trial_log
em, S, En = B.em, B.S, B.En; TRAIN, TEST = B.TRAIN, B.TEST; S17 = 1.115; EV = E.E2; fl = L.fl; K = En.bar_k; N = B.N; one = B.one
def stream(cp, s=S17): return ST.stream(em, None, s, cp, EV)
def run(sd, sz=one): return B.comps2(S2.long_base(), one, 1, sd, sz, 1)[0]
def sS1():
    raw = B.SH_BASE; out = np.zeros(N, np.int8); pos = 0
    for t in range(N):
        if raw[t] == -1 and (pos == -1 or K[t] == 23): out[t] = -1
        pos = out[t]
    return run(out)
C5 = pd.Series(S.D['close'].values, index=S.D.index).pipe(lambda c: c / c.shift(5) - 1).values          # day-d 5-day return; d2b uses the previous completed day
def sS2(x, arr=C5):
    ok = np.nan_to_num(S.d2b(arr), nan=0.0) < -x / 100.0; return run(np.where((B.SH_BASE == -1) & ok, -1, 0).astype(np.int8))
if __name__ == '__main__':
    base_cp = ST.comps(em, 'floor'); bnet = stream(base_cp); bT = V.met(em, bnet, *TRAIN); bX = V.met(em, bnet, *TEST); rng = np.random.default_rng(7611); res = {}
    print(f'base v2-FE (-17%, scale {S17}): TRAIN {fl(bT)} | TEST {fl(bX)}\n')
    def solve(cp):
        lo, hi = 0.3, 3.5
        for _ in range(35):
            s = (lo + hi) / 2
            if V.met(em, stream(cp, s), *TRAIN)['MaxDD'] >= -0.17: lo = s
            else: hi = s
        return lo, stream(cp, lo)
    def ev(name, fn, nullfn=None):
        cp = fn(); n0 = stream(cp); delta = L.eqdd(em, n0, bT['MaxDD'], *TRAIN) - bT['CAGR']; s, net = solve(cp); trial_log('SHORT3_' + name.split()[0], {}, 'train', V.met(em, net, *TRAIN))
        if nullfn: null = [L.eqdd(em, stream(nullfn()), bT['MaxDD'], *TRAIN) - bT['CAGR'] for _ in range(200)]; p95 = np.percentile(null, 95); keep = delta > 0 and delta > p95; bm = f'null median {np.median(null) * 100:+.1f}, p95 {p95 * 100:+.1f}, beats {(np.array(null) < delta).mean():.0%}'
        else: p5 = B.boot_p5((n0 - bnet)[TRAIN[0]:TRAIN[1]], rng); keep = delta > 0 and p5 > 0; bm = f'bootstrap 5th pct of mean daily diff {p5 * 1e4:+.2f} bp'
        res[name] = (delta, keep); print(f'{name}: scale {s:.3f} TRAIN {fl(V.met(em, net, *TRAIN))} | TEST {fl(V.met(em, net, *TEST))} || delta TRAIN {delta * 100:+.1f} pts; {bm} -> {"KEEP" if keep else "no"}')
    ev('S1 15:15-bar entries only', sS1)
    for x in (3, 4, 5): ev(f'S2 crash-only x={x}%', (lambda x=x: sS2(x)), (lambda x=x: sS2(x, np.roll(C5, int(rng.integers(60, len(C5) - 60))))))
    if all(v[0] <= 0 for v in res.values()): print('\nS1 and S2 all fail outright -> STOP; S3 not run.')
    else: print('\nnot all failing outright -> S3 would run next (declared); not run in this pass')
    print('kept:', [k for k, v in res.items() if v[1]])
