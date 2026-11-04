"""LOSSF round: diagnostic + long-leg loss filters on v2-FE (rules in PROTOCOL_CHANGES.md ROUND "LOSSF"). Run: <venv>/bin/python scripts/rm_lossf.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log, DATA
em, ep = L.em, L.ep; FULL, HOLD = L.FULL, L.HOLD; fl = L.fl; SFE = 1.163; ELIST = ST.ELECT + ST.BUDGET
def ser(pre, post):
    a = pd.read_csv(pre, parse_dates=['date']).set_index('date')['close']; b = pd.read_csv(post, parse_dates=['date']).set_index('date')['close']
    s = pd.concat([a, b]); return s[~s.index.duplicated(keep='first')].sort_index().dropna()
VIX = pd.read_csv(f'{DATA}/vix_ext.csv', parse_dates=['date']).set_index('date')['close']; FX = ser(f'{DATA}/pre/usdinr.csv', f'{DATA}/usdinr.csv'); BR = ser(f'{DATA}/pre/brent.csv', f'{DATA}/brent.csv')
def prior(days, s, n):
    s = s[~s.index.duplicated()].dropna(); r = s / s.shift(n) - 1; p = np.searchsorted(r.index.values, days.values, side='left') - 1
    return pd.Series(np.where(p >= 0, r.values[np.maximum(p, 0)], np.nan), index=days)
def stretch(env):
    D = env['S'].D; c = D['close']; pc = D['close'].shift(1); tr = pd.concat([D['high'] - D['low'], (D['high'] - pc).abs(), (D['low'] - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean(); z = (c - c.rolling(20).mean()) / atr; return z.shift(1)          # value known at the previous close
def cond(env, fam, j):
    days = env['days']
    if fam == 'VIX': return (prior(days, VIX, 5) > [0.20, 0.30, 0.40][j]).fillna(False).astype(bool)
    if fam == 'MACRO': return ((prior(days, FX, 5) > [0.01, 0.015, 0.02][j]) | (prior(days, BR, 5) > [0.08, 0.12, 0.16][j])).fillna(False).astype(bool)
    return (stretch(env).reindex(days) > [3, 4, 5][j]).fillna(False).astype(bool)
def fe_stream(env, cp, ev, mf=None, s=SFE):
    e2 = dict(env); e2['ens'] = env['ens'] * (mf if mf is not None else 1.0); return ST.stream(e2, None, s, cp, ev)
if __name__ == '__main__':
    CP = {(w, c): ST.comps(env, c) for w, env in (('FULL', em), ('HOLD', ep)) for c in ('floor',)}
    EV = {'FULL': ST.ev_mask(em, ELIST), 'HOLD': ST.ev_mask(ep, ELIST)}; base = fe_stream(em, CP[('FULL', 'floor')], EV['FULL'])['2017-04-03':]
    print('## STEP 1: 20 worst days of v2-FE (floor): date, day P&L, VIX 5d rise, USDINR 5d, Brent 5d, stretch(ATR), flags VIX20/MACRO(1%|8%)/STR3')
    z = stretch(em); vx, fx, br = prior(em['days'], VIX, 5), prior(em['days'], FX, 5), prior(em['days'], BR, 5); w20 = base.nsmallest(20); b20 = base.nlargest(20)
    for d, v in w20.items(): print(f'  {d.date()} {v:+.1%}  VIX {vx[d]:+.0%}  FX {fx[d]:+.1%}  Brent {br[d]:+.1%}  str {z[d]:+.1f}')
    gate = {}
    for fam in ('VIX', 'MACRO', 'STRETCH'):
        c = cond(em, fam, 0); nw, nb = int(c.reindex(w20.index).sum()), int(c.reindex(b20.index).sum()); gate[fam] = nw >= 4 and nb <= 4
        print(f'  gate {fam}: loosest cell flags {nw}/20 worst days, {nb}/20 best days, {c["2017-04-03":].mean():.1%} of all days -> {"TEST" if gate[fam] else "SKIP"}')
    eq = (1 + base).cumprod(); dd = eq / eq.cummax() - 1; st = dd.lt(0).ne(dd.lt(0).shift()).cumsum()[dd < 0]; ep_ = dd[dd < 0].groupby(st).agg(['min', 'idxmin', lambda x: x.index[0], lambda x: x.index[-1]]).nsmallest(10, 'min')
    print('\n10 worst drawdown stretches (depth, trough, start..end) and VIX/FX/Brent/stretch readings at the PRIOR close of the trough:')
    for _, r in ep_.iterrows():
        d = r['idxmin']; print(f"  {r['min']:.1%} trough {d.date()} ({r.iloc[2].date()}..{r.iloc[3].date()})  VIX {vx[d]:+.0%} FX {fx[d]:+.1%} Brent {br[d]:+.1%} str {z[d]:+.1f}")
    for fam in [f for f in gate if gate[f]]:
        print(f'\n## STEP 2: {fam} (floor costs; equal-drawdown CAGR vs v2-FE)')
        bF = V.met(em, fe_stream(em, CP[('FULL', 'floor')], EV['FULL']), *FULL); bH = V.met(ep, fe_stream(ep, CP[('HOLD', 'floor')], EV['HOLD']), *HOLD); ok = True; rows = []
        for j in range(3):
            mfF = pd.Series(np.where(cond(em, fam, j), 0.5, 1.0), index=em['days']); mfH = pd.Series(np.where(cond(ep, fam, j), 0.5, 1.0), index=ep['days'])
            nF = fe_stream(em, CP[('FULL', 'floor')], EV['FULL'], mfF); nH = fe_stream(ep, CP[('HOLD', 'floor')], EV['HOLD'], mfH)
            eF = L.eqdd(em, nF, bF['MaxDD'], *FULL); eH = L.eqdd(ep, nH, bH['MaxDD'], *HOLD); trial_log('LOSSF_' + fam, {'j': j}, 'train', V.met(em, nF, *FULL)); ok &= (eF > bF['CAGR']) and (eH > bH['CAGR'])
            rows.append((j, fl(V.met(em, nF, *FULL)), eF - bF['CAGR'], eH - bH['CAGR'], mfF['2017-04-03':].eq(0.5).mean()))
        for j, m, dF, dH, fr in rows: print(f'  cell {j + 1}: FULL {m} | equal-DD delta FULL {dF * 100:+.1f} pts, HOLD {dH * 100:+.1f} pts | days cut {fr:.0%}')
        print(f'  -> {fam}: {"PASS" if ok else "FAIL"}')
