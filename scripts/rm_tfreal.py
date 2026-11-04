"""TFREAL: Supertrend on real futures 15/5/1-minute bars (2017-04..2020-12). Rules in PROTOCOL_CHANGES.md ROUND "TFREAL". Run: <venv>/bin/python scripts/rm_tfreal.py"""
import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_data, rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_hold2 as H, rm_tf as T, rm_pre_exact as P
from rm_engine import RF
from rm_ideas import make_sig, trial_log, DATA
from rm_signals import supertrend
ROOT = rm_data.ROOT; W = ('2017-04-03', '2020-12-31'); S0 = 1.163; fl = L.fl
F = pd.read_csv(f'{ROOT}/data/fut_intraday/nifty_f1_1min_2017_2020.csv', parse_dates=['timestamp']).set_index('timestamp').sort_index()
F.index = F.index - pd.Timedelta(minutes=1); hm = F.index.strftime('%H:%M'); F = F[(hm >= '09:15') & (hm <= '15:29')].copy(); F['date'] = F.index.normalize()
bh = pd.concat([pd.read_csv(f'{ROOT}/data/fut/{n}', parse_dates=['date', 'expiry']) for n in ('nifty_fut_2012_2017.csv', 'nifty_fut.csv')]).drop_duplicates(['date', 'expiry']); bh = bh[(bh.open > 0) & (bh.close > 0)]
settle = bh.set_index(['date', 'expiry'])['settle']; exps = np.sort(bh.expiry.unique())
g = F.groupby('date'); D = pd.DataFrame({'open': g.open.first(), 'high': g.high.max(), 'low': g.low.min(), 'close': g.close.last()}); days = D.index
D['held'] = pd.DatetimeIndex([pd.Timestamp(exps[np.searchsorted(exps, np.datetime64(d))]) for d in days]); D['roll'] = (D.held.shift(-1) != D.held) & D.held.shift(-1).notna()
D['m_close'] = 1.0; D['m_prevclose'] = 1.0; D['syn_close'] = D.close
ds = dict(m1=F[['open', 'high', 'low', 'close', 'date']], daily=D, flags={}, rq=rm_data.RQ, validation=None)
def bars(BL):
    b = F.resample(f'{BL}min', origin='start_day', offset='9h15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    b['start'] = b.index; b.index = b.index + pd.Timedelta(minutes=BL); b.index.name = 'close_time'; b['date'] = b['start'].dt.normalize(); return b
nq = P.series(f'{DATA}/pre/nasdaq.csv', f'{DATA}/nasdaq.csv'); us = P.series(f'{DATA}/pre/us10y.csv', f'{DATA}/us10y.csv')
def prior(s, n, kind='pct'):
    s = s.dropna(); s = (s / s.shift(n) - 1) if kind == 'pct' else (s - s.shift(n)); p = np.searchsorted(s.index.values, days.values, side='left') - 1
    return pd.Series(np.where(p >= 0, s.values[np.maximum(p, 0)], np.nan), index=days)
def cell(x, y, c=0.25):
    a = (prior(nq, 5) * 100 < -x).fillna(False); b = (prior(us, 5, 'diff') * 100 > y).fillna(False); return pd.Series(np.where(a, c, 1.0), index=days) * pd.Series(np.where(b, c, 1.0), index=days)
ENS = sum(cell(x, y) for x in (1, 2, 3) for y in (10, 15, 20)) / 9.0
ENV = {}
def env(BL):
    if BL in ENV: return ENV[BL]
    d2 = dict(ds); d2['b15'] = bars(BL); E = T.EngineTF(d2, BL); fi = np.where(E.first_b)[0]; prev = E.prev.copy()
    for i in range(1, len(days)):
        o, n = D.held.iloc[i - 1], D.held.iloc[i]
        if o != n and (days[i - 1], o) in settle.index and (days[i - 1], n) in settle.index: prev[fi[i]] = E.fc[fi[i] - 1] + (settle[(days[i - 1], n)] - settle[(days[i - 1], o)])
    E.prev = prev; S = make_sig(E); ENV[BL] = dict(Ea=E, S=S, days=E.days, ens=ENS, INT=pd.Series(E.cal * RF / 365.0, index=E.days)); return ENV[BL]
def with_st(BL, n, m):
    e = env(BL); S = e['S']; e2 = dict(e); S2 = copy.copy(S); S2.st = supertrend(S.h, S.l, S.c, n, m)[0]; e2['S'] = S2; return e2
def run(e, cost='floor'):
    lt, lz, st, sz = V.signals(e, 'v2'); c = H.comps(e, lt, lz, 1, st, sz, 1, cost); EV = ST.ev_mask(e, ST.ELECT + ST.BUDGET); return ST.stream(e, None, S0, c, EV)
if __name__ == '__main__':
    e15 = with_st(15, 14, 3.0); base = run(e15); bm = V.met(e15, base, *W); atr15 = float(np.nanmean(supertrend(e15['S'].h, e15['S'].l, e15['S'].c, 14, 3.0)[1]))
    print(f'real 15-min baseline {W[0]}..{W[1]}: {fl(bm)}  (sessions {len(days)}, ATR15 {atr15:.1f})')
    ep = L.em; cp = ST.comps(ep, 'floor'); EVp = ST.ev_mask(ep, ST.ELECT + ST.BUDGET); pn = ST.stream(ep, None, S0, cp, EVp); print(f'spot-proxy 15-min v2-FE same window: {fl(V.met(ep, pn, *W))}')
    print('  proxy minus real: CAGR %+.1f pts' % ((V.met(ep, pn, *W)['CAGR'] - bm['CAGR']) * 100), '\n'); res = {}
    for BL in (5, 1):
        n = 14 * 15 // BL; e = env(BL); atr = float(np.nanmean(supertrend(e['S'].h, e['S'].l, e['S'].c, n, 3.0)[1])); m0 = 3.0 * atr15 / atr; print(f'{BL}-min: n={n}, m0={m0:.2f}')
        for f in (0.8, 1.0, 1.25):
            net = run(with_st(BL, n, m0 * f)); m = V.met(e15, net, *W); d = L.eqdd(e15, net, bm['MaxDD'], *W) - bm['CAGR']; res[(BL, f)] = d; trial_log(f'TFREAL_{BL}m_{f}', {}, 'train', m)
            print(f'  m={m0 * f:.2f} (x{f}): {fl(m)} equal-DD delta {d * 100:+.1f} pts')
    print()
    for BL in (5, 1):
        for f in (0.8, 1.0, 1.25):
            nb = [res[(BL, g)] for g in (0.8, 1.0, 1.25) if g != f]; ok = res[(BL, f)] >= 0.02 and all(x > 0 for x in nb); print(f'{BL}-min x{f}: {"PASS (candidate)" if ok else "fail"} (delta {res[(BL, f)] * 100:+.1f}, neighbours {[round(x * 100, 1) for x in nb]})')
