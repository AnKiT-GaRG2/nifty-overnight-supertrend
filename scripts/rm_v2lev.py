"""V2LEV: levers C (vol-targeted size), D (short trailing exit), E (fast long re-entry) vs frozen v2; rules in PROTOCOL_CHANGES.md ROUND "V2LEV".
Run: <venv>/bin/python scripts/rm_v2lev.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V
from rm_engine import metrics_from, LOT, CAPITAL
from rm_ideas import trial_log
from rm_signals import supertrend
em, ep = V.env_main(), V.env_pre()
FULL = ('2017-04-03', '2026-12-31'); HOLD = ('2012-07-02', '2016-08-31'); DEV = ('2017-04-03', '2023-12-31'); WL, WS = 1.912, 0.956
ENV = {'FULL': (em, FULL), 'HOLD': (ep, HOLD)}

def legs2(env, sig, cost):
    En = env['Ea']; lt, lz, st, sz = sig; fb = np.where(En.first_b)[0]; lb = np.where(En.last_b)[0]; out = []
    for d, s in ((lt, lz), (st, sz)):
        R = En.run(d, s, cost=cost, min_chg=1); net = pd.Series(R.net_d, index=En.days); gap = np.zeros(len(fb))
        for i in range(1, len(fb)): gap[i] = R.posl[lb[i - 1]] * LOT * (En.fo[fb[i]] - En.prev[fb[i]]) / CAPITAL
        gap = pd.Series(gap, index=En.days); out += [gap, net - gap]
    return out                                              # GL, IL, GS, IS

def build(env, GL, IL, GS, IS, mv=None):
    e = env['ens'] * (mv if mv is not None else 1.0); s = mv if mv is not None else pd.Series(1.0, index=env['days'])
    return WL * (e.shift(1).fillna(1.0) * GL + e * IL) + WS * (s.shift(1).fillna(1.0) * GS + s * IS)

def vol20(env): c = pd.Series(env['S'].D['close'].values, index=env['S'].D.index); return (c.pct_change().rolling(20).std() * np.sqrt(252)).shift(1)
vm = vol20(em); VREF = float(vm[DEV[0]:DEV[1]].median())
def raw_term(env, k): return ((VREF / vol20(env)) ** k).clip(0.5, 1.5)
NORM = {k: float(raw_term(em, k)[DEV[0]:DEV[1]].mean()) for k in (0.5, 0.75, 1.0)}
def mv_series(env, k): return (raw_term(env, k) / NORM[k]).fillna(1.0)

def daily_atr(env, n=14):
    D = env['S'].D; pc = D['close'].shift(1); tr = pd.concat([D['high'] - D['low'], (D['high'] - pc).abs(), (D['low'] - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().shift(1).values[env['S'].dc]
def short_trail(env, k):
    S = env['S']; raw = V.signals(env, 'v2')[2]; atr = daily_atr(env); c = S.c; out = np.zeros_like(raw); inn = False; blocked = False; low = np.inf
    for t in range(len(raw)):
        if raw[t] == 0: inn = False; blocked = False; continue
        if not inn and not blocked: inn = True; low = c[t]
        if inn:
            low = min(low, c[t])
            if not np.isnan(atr[t]) and c[t] > low + k * atr[t]: inn = False; blocked = True
        out[t] = -1 if inn else 0
    return out
def fast_reentry(env, mf):
    S = env['S']; fast = supertrend(S.h, S.l, S.c, 7, mf)[0]; lt, lz, st, sz = V.signals(env, 'v2')
    on = (fast == 1) & (S.st == -1)
    return np.where(on | (lt == 1), 1, 0).astype(np.int8), lz, np.where(on, 0, st).astype(np.int8), sz

LEVERS = {'C': [('k=0.5', 0.5), ('k=0.75', 0.75), ('k=1.0', 1.0)], 'D': [('trail k=2', 2), ('trail k=3', 3), ('trail k=4', 4)], 'E': [('fast mf=2.0', 2.0), ('fast mf=2.5', 2.5), ('fast mf=3.0', 3.0)]}
fl = lambda m: f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
def met(env, net, a, z): ex = net[a:z]; return metrics_from(ex + env['INT'][a:z], None, None, None, ex)
def eqdd(env, net, ref, a, z):
    lo, hi = 0.05, 4.0
    for _ in range(40):
        s = (lo + hi) / 2
        if met(env, net * s, a, z)['MaxDD'] < ref: hi = s
        else: lo = s
    return met(env, net * lo, a, z)['CAGR']
if __name__ == '__main__':
    RES = {}; YEARS = {}
    for wn, (env, (a, z)) in ENV.items():
        for cost in ('real', 'floor'):
            base_sig = V.signals(env, 'v2'); GL, IL, GS, IS = legs2(env, base_sig, cost); base = build(env, GL, IL, GS, IS); mb = met(env, base, a, z); eb = mb['CAGR']
            RES[(wn, cost, 'base')] = mb; print(f'\n### {wn} {a}..{z}, {cost} costs. v2: {fl(mb)}'); print('| cell | CAGR / MaxDD / Sharpe | equal-DD CAGR | delta vs v2 | note |'); print('|---|---|---|---|---|')
            for lev, cells in LEVERS.items():
                for name, p in cells:
                    note = ''
                    if lev == 'C': net = build(env, GL, IL, GS, IS, mv_series(env, p)); note = f'avg size {mv_series(env, p)[a:z].mean():.3f}'
                    elif lev == 'D': sg = list(base_sig); sg[2] = short_trail(env, p); g = legs2(env, tuple(sg), cost); net = build(env, *g)
                    else: g = legs2(env, fast_reentry(env, p), cost); net = build(env, *g)
                    m = met(env, net, a, z); ed = eqdd(env, net, mb['MaxDD'], a, z); RES[(wn, cost, lev, name)] = (m, ed - eb)
                    if wn == 'FULL' and cost == 'real':
                        trial_log('V2LEV_' + lev, {'cell': name}, 'train', m)
                        yr = net['2017-04-03':].groupby(net['2017-04-03':].index.year).apply(lambda x: (1 + x).prod() - 1); YEARS[(lev, name)] = yr
                    print(f"| {lev} {name} | {fl(m)} | {ed:.1%} | {(ed - eb) * 100:+.1f} pts | {note} |")
            if wn == 'FULL' and cost == 'real': yb = base['2017-04-03':].groupby(base['2017-04-03':].index.year).apply(lambda x: (1 + x).prod() - 1)
    print('\n## Year-by-year futures P&L return, realistic costs, FULL (excl. interest): v2 vs middle cells (2018, 2020, 2022)')
    for y in (2018, 2020, 2022): print(y, f'v2 {yb[y]:.1%}', {f'{l} {n}': f'{YEARS[(l, n)][y]:.1%}' for l, n in (('C', 'k=0.75'), ('D', 'trail k=3'), ('E', 'fast mf=2.5'))})
    print('\n## PASS test: all 3 cells beat v2 equal-drawdown CAGR in FULL/HOLD x real/floor, and the middle cell by >= +1.0 pt on FULL')
    for lev, cells in LEVERS.items():
        allpos = all(RES[(w, c, lev, n)][1] > 0 for w in ('FULL', 'HOLD') for c in ('real', 'floor') for n, _ in cells)
        mid = all(RES[('FULL', c, lev, cells[1][0])][1] >= 0.01 for c in ('real', 'floor'))
        worst = min(RES[(w, c, lev, n)][1] for w in ('FULL', 'HOLD') for c in ('real', 'floor') for n, _ in cells); best = max(RES[(w, c, lev, n)][1] for w in ('FULL', 'HOLD') for c in ('real', 'floor') for n, _ in cells)
        print(f"- {lev}: {'PASS' if allpos and mid else 'FAIL'} (all cells positive everywhere: {allpos}; middle >= +1pt on FULL: {mid}; delta range {worst * 100:+.1f}..{best * 100:+.1f} pts)")
