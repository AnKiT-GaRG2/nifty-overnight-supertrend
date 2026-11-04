"""TF round: Supertrend on 5-minute / 1-minute bars. Rules in PROTOCOL_CHANGES.md ROUND "TF". Run: <venv>/bin/python scripts/rm_tf.py"""
import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_data, rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_hold2 as H
from rm_engine import Engine, cost_rates
from rm_ideas import make_sig, trial_log
from rm_signals import supertrend
ROOT = rm_data.ROOT; em = L.em; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); FULL = L.FULL; S0 = 1.163; fl = L.fl
DS = pd.read_pickle(f'{ROOT}/data/rm/dataset.pkl'); FUT = pd.read_csv(f'{ROOT}/data/fut/nifty_fut.csv', parse_dates=['date', 'expiry']).drop_duplicates(['date', 'expiry']); FUT = FUT[(FUT.open > 0) & (FUT.close > 0)].set_index(['date', 'expiry'])
class EngineTF(Engine):
    def __init__(self, ds, BL):
        self.BL = BL; super().__init__(ds)
        mt = ds['m1'].index.values; bs = ds['b15']['start'].values; self.bm1 = np.searchsorted(mt, bs + np.timedelta64(BL, 'm'), 'left').astype(np.int64)
        self.bar_k = ((self.hhmm - 555) // BL).astype(int)
def bars(BL):
    m1 = DS['m1']; b = m1.resample(f'{BL}min', origin='start_day', offset='9h15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    b['start'] = b.index; b.index = b.index + pd.Timedelta(minutes=BL); b.index.name = 'close_time'; b['date'] = b['start'].dt.normalize(); return b
def anchored(E, fut):
    E2 = copy.copy(E); D = E.D; nd = len(D); do = np.zeros(nd); dc = np.zeros(nd); fi = np.where(E.first_b)[0]; li = np.where(E.last_b)[0]
    for i in range(nd):
        key = (D.index[i], D['held'].iloc[i])
        if key in fut.index: r = fut.loc[key]; do[i] = r['open'] - E.fo[fi[i]]; dc[i] = r['close'] - E.fc[li[i]]
    f0 = (E.hhmm - 555) / 375.0; f1 = f0 + E.BL / 375.0; dcode = E.day_codes; off = lambda f: do[dcode] + (dc[dcode] - do[dcode]) * f
    fo = E.fo + off(f0); fc = E.fc + off(f1); mid = off((f0 + f1) / 2); fh = np.maximum(E.fh + mid, np.maximum(fo, fc)); fl_ = np.minimum(E.fl + mid, np.minimum(fo, fc))
    m1 = E.ds['m1']; mdc = pd.Index(D.index).get_indexer(m1['date'].values); mf = np.asarray((m1.index.hour * 60 + m1.index.minute) - 555) / 375.0; moff = do[mdc] + (dc[mdc] - do[mdc]) * mf
    E2.fo, E2.fc, E2.fh, E2.fl = fo, fc, fh, fl_; E2.mo, E2.mc, E2.mh, E2.ml = E.mo + moff, E.mc + moff, E.mh + moff, E.ml + moff
    prev = np.r_[fc[0], fc[:-1]].copy()
    for i in range(1, nd):
        t = fi[i]; key = (D.index[i - 1], D['held'].iloc[i]); prev[t] = fut.loc[key, 'close'] if key in fut.index else E.prev[t] + (fc[t - 1] - E.fc[t - 1])
    prev[0] = fo[0]; E2.prev = prev; return E2
ENV = {}
def env(BL):
    if BL in ENV: return ENV[BL]
    ds = dict(DS); ds['b15'] = bars(BL); E = EngineTF(ds, BL); Ea = anchored(E, FUT); S = make_sig(E)
    ENV[BL] = dict(Ea=Ea, S=S, days=E.days, ens=em['ens'], INT=em['INT']); return ENV[BL]
def with_st(BL, n, m):
    e = env(BL); S = e['S']; e2 = dict(e); S2 = copy.copy(S); S2.st = supertrend(S.h, S.l, S.c, n, m)[0]; e2['S'] = S2; return e2
def comps(e, cost='floor'):
    lt, lz, st, sz = V.signals(e, 'v2'); return H.comps(e, lt, lz, 1, st, sz, 1, cost)
if __name__ == '__main__':
    EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET); stream = lambda c: ST.stream(em, None, S0, c, EV)
    bnet = stream(ST.comps(em, 'floor')); bT = V.met(em, bnet, *TRAIN); bX = V.met(em, bnet, *TEST); print(f'base v2-FE (15-min) floor: TRAIN {fl(bT)} | TEST {fl(bX)}\n')
    e15 = env(15); atr15 = float(np.nanmean(supertrend(e15['S'].h, e15['S'].l, e15['S'].c, 14, 3.0)[1])); ctl = stream(comps(with_st(15, 14, 3.0))); print('control 15-min rebuilt: TRAIN', fl(V.met(em, ctl, *TRAIN)), '(must equal base)\n'); res = {}
    for BL in (5, 1):
        n = 14 * 15 // BL; e = env(BL); atr = float(np.nanmean(supertrend(e['S'].h, e['S'].l, e['S'].c, n, 3.0)[1])); m0 = 3.0 * atr15 / atr; print(f'{BL}-min: n={n}, mean ATR {atr:.2f} vs 15-min {atr15:.2f} -> m0 = {m0:.2f}, bars {e["Ea"].N:,}')
        for f in (0.8, 1.0, 1.25):
            c = comps(with_st(BL, n, m0 * f)); net = stream(c); dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; res[(BL, f)] = (dT, dX)
            trial_log(f'TF_{BL}m_{f}', {}, 'train', V.met(em, net, *TRAIN))
            print(f'  m={m0 * f:.2f} (x{f}): TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} | TEST {fl(V.met(em, net, *TEST))} delta {dX * 100:+.1f} | FULL {fl(V.met(em, net, *FULL))}')
    print()
    for BL in (5, 1):
        for f in (0.8, 1.0, 1.25):
            dT, dX = res[(BL, f)]; nb = [res[(BL, g)][0] for g in (0.8, 1.0, 1.25) if g != f]; ok = dT >= 0.02 and all(x > 0 for x in nb) and dX >= 0
            print(f'{BL}-min x{f}: {"PASS" if ok else "fail"}  (TRAIN {dT * 100:+.1f}, neighbours {[round(x * 100, 1) for x in nb]}, TEST {dX * 100:+.1f})')
