"""SLEEVE round: intraday-only second sleeve on top of v2-FE; rules in PROTOCOL_CHANGES.md ROUND "SLEEVE". Run: <venv>/bin/python scripts/rm_sleeve.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
em, ep = L.em, L.ep; FULL, HOLD = L.FULL, L.HOLD; fl = L.fl
ELIST = ST.ELECT + ST.BUDGET

def sleeve_signal(env, kind, p):
    S = env['S']; k = S.E.bar_k if hasattr(S, 'E') else env['Ea'].bar_k; N = S.N; dc = S.dc; tdir = np.zeros(N, np.int8)
    if kind == 'SA':
        pc = S.d2b(S.dd.close.values); atr = L.daily_atr(env); er = S.d2b(S.er_daily(20)); dirday = {}
        for t in range(N):
            if k[t] == 0 and not np.isnan(atr[t]) and not np.isnan(er[t]) and er[t] < 0.30:
                m = (S.c[t] - pc[t]) / atr[t]; dirday[dc[t]] = -1 if m > p else (1 if m < -p else 0)
        for t in range(N):
            if 0 <= k[t] <= 22: tdir[t] = dirday.get(dc[t], 0)
    else:
        pos = 0; sm = 0.0; n = 0; cur = -1
        for t in range(N):
            if dc[t] != cur: cur = dc[t]; pos = 0; sm = 0.0; n = 0
            sm += S.c[t]; n += 1; stretch = (S.c[t] - sm / n) / S.atr15[t] if S.atr15[t] > 0 else 0.0
            if k[t] >= 23: pos = 0
            else:
                if pos == 0 and 4 <= k[t] <= 20:
                    if stretch > p: pos = -1
                    elif stretch < -p: pos = 1
                elif pos == -1 and stretch <= 0: pos = 0
                elif pos == 1 and stretch >= 0: pos = 0
            tdir[t] = pos
    return tdir

def sleeve_net(env, kind, p, cost):
    En = env['Ea']; td = sleeve_signal(env, kind, p); R = En.run(td, np.ones(En.N), cost=cost, min_chg=1)
    held_on = (R.posl != 0) & (En.bar_k >= 24); assert held_on.sum() == 0, 'sleeve holds overnight'      # flat by the 15:15 fill
    return pd.Series(R.net_d, index=En.days), len(R.trades)

CAND = [('SA x=0.5', 'SA', 0.5), ('SA x=0.75', 'SA', 0.75), ('SA x=1.0', 'SA', 1.0), ('SB z=3', 'SB', 3.0), ('SB z=4', 'SB', 4.0), ('SB z=5', 'SB', 5.0)]
if __name__ == '__main__':
    CP = {(w, c): ST.comps(env, c) for w, env in (('FULL', em), ('HOLD', ep)) for c in ('floor', 'real')}
    EV = {'FULL': ST.ev_mask(em, ELIST), 'HOLD': ST.ev_mask(ep, ELIST)}; SFE = 1.163
    FE = {(w, c): ST.stream(env, None, SFE, CP[(w, c)], EV[w]) for w, env in (('FULL', em), ('HOLD', ep)) for c in ('floor', 'real')}
    def solve(fn):
        lo, hi = 0.3, 2.5
        for _ in range(35):
            f = (lo + hi) / 2
            if V.met(em, fn(f), *FULL)['MaxDD'] >= -0.177: lo = f
            else: hi = f
        return lo
    f0 = solve(lambda f: f * FE[('FULL', 'floor')]); b = {}
    for w, env, win in (('FULL', em, FULL), ('HOLD', ep, HOLD)):
        for c in ('floor', 'real'): b[(w, c)] = V.met(env, f0 * FE[(w, c)], *win)
    print(f'v2-FE alone (scale {SFE}, f={f0:.3f}): floor FULL {fl(b[("FULL","floor")])} | HOLD {fl(b[("HOLD","floor")])} || real FULL {fl(b[("FULL","real")])} | HOLD {fl(b[("HOLD","real")])}\n')
    out = {}
    for name, kind, p in CAND:
        sl = {}
        for w, env in (('FULL', em), ('HOLD', ep)):
            for c in ('floor', 'real'): sl[(w, c)] = sleeve_net(env, kind, p, c)
        sf, ntr = sl[('FULL', 'floor')]; years = len(em['days']) / 252
        corr = np.corrcoef(sf['2017-04-03':], FE[('FULL', 'floor')]['2017-04-03':])[0, 1]
        f = solve(lambda g: g * (FE[('FULL', 'floor')] + sf)); row = {}
        for w, env, win in (('FULL', em, FULL), ('HOLD', ep, HOLD)):
            for c in ('floor', 'real'): row[(w, c)] = V.met(env, f * (FE[(w, c)] + sl[(w, c)][0]), *win)
        solo = {w: V.met(env, sl[(w, 'floor')][0], *win) for w, env, win in (('FULL', em, FULL), ('HOLD', ep, HOLD))}
        out[name] = (row, f); trial_log('SLEEVE_' + kind, {'p': p}, 'train', row[('FULL', 'floor')])
        print(f'### {name}: sleeve alone (1x, floor) FULL {fl(solo["FULL"])} | HOLD {fl(solo["HOLD"])}; trades/yr {ntr / years:.0f}; corr with v2-FE {corr:+.2f}')
        print(f'    combined (scaled x{f:.3f} to DD -17.7%): floor FULL {fl(row[("FULL","floor")])} | HOLD {fl(row[("HOLD","floor")])} || real FULL {fl(row[("FULL","real")])} | HOLD {fl(row[("HOLD","real")])}')
    print('\n## KEEP test (floor costs): all 3 cells beat v2-FE equal-drawdown CAGR on FULL and HOLD; middle cell >= +1.0 pt on FULL')
    for fam, names in (('SA', [c[0] for c in CAND[:3]]), ('SB', [c[0] for c in CAND[3:]])):
        dF = [out[n][0][('FULL', 'floor')]['CAGR'] - b[('FULL', 'floor')]['CAGR'] for n in names]; dH = [out[n][0][('HOLD', 'floor')]['CAGR'] - b[('HOLD', 'floor')]['CAGR'] for n in names]
        ok = all(x > 0 for x in dF + dH) and dF[1] >= 0.01
        print(f"- {fam}: {'KEEP' if ok else 'REJECT'}  (FULL deltas {[round(x * 100, 1) for x in dF]} pts, HOLD deltas {[round(x * 100, 1) for x in dH]} pts)")
