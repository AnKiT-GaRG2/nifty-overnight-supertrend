"""LONG2 option 3: options-implied features (skew, skew change, term slope, IV minus realised vol) as long-leg cut/boost. Rules in PROTOCOL_CHANGES.md "LONG2 OPTION 3".
Input: data/opt/nifty_opt_monthly_2017_2026.csv (date,expiry,strike,type,settle,oi,vol; type F = futures settle). Run: <venv>/bin/python scripts/rm_opt3.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy.stats import norm
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
em = L.em; days = em['days']; R = V.ROOT; S = em['S']; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; fl = L.fl; ST.WS = 1e-9; RF = 0.06
O = pd.read_csv(f'{R}/data/opt/nifty_opt_monthly_2017_2026.csv', parse_dates=['date', 'expiry']); O = O[O.settle > 0]
F = O[O.type == 'F'].set_index(['date', 'expiry']).settle; Q = O[O.type != 'F'].copy(); Q['F'] = [F.get((d, e), np.nan) for d, e in zip(Q.date, Q.expiry)]; Q = Q.dropna(subset=['F'])
Q['dte'] = (Q.expiry - Q.date).dt.days; Q = Q[Q.dte >= 3]; Q['T'] = Q.dte / 365.0
Q = Q[((Q.type == 'PE') & (Q.strike < Q.F)) | ((Q.type == 'CE') & (Q.strike >= Q.F))]                      # out-of-the-money only
def black76(F_, K, T, s, call): d1 = (np.log(F_ / K) + 0.5 * s * s * T) / (s * np.sqrt(T)); d2 = d1 - s * np.sqrt(T); df = np.exp(-RF * T); return df * np.where(call, F_ * norm.cdf(d1) - K * norm.cdf(d2), K * norm.cdf(-d2) - F_ * norm.cdf(-d1))
lo, hi = np.full(len(Q), 0.01), np.full(len(Q), 3.0); call = (Q.type == 'CE').values; Fv, Kv, Tv, Pv = Q.F.values, Q.strike.values.astype(float), Q['T'].values, Q.settle.values
for _ in range(50):
    mid = (lo + hi) / 2; p = black76(Fv, Kv, Tv, mid, call); up = p < Pv; lo = np.where(up, mid, lo); hi = np.where(up, hi, mid)
Q['iv'] = (lo + hi) / 2; Q = Q[(Q.iv > 0.03) & (Q.iv < 2.5)]; print('option rows with IV:', len(Q), 'days', Q.date.nunique())
rows = {}
for d, g in Q.groupby('date'):
    ex = sorted(g.expiry.unique()); ex = [e for e in ex if 15 <= (e - d).days <= 45]
    if not ex: continue
    e0 = ex[0]; a = g[g.expiry == e0]; Fx = a.F.iloc[0]
    def at(a, target, side=None):
        b = a.assign(dist=(a.strike / a.F - target).abs()); b = b[b.dist <= 0.015] if side is None else b[(b.dist <= 0.015)]
        return b.sort_values('dist').iv.iloc[0] if len(b) else np.nan
    atm = at(a, 1.0); skew = at(a[a.type == 'PE'], 0.95) - at(a[a.type == 'CE'], 1.05)
    nxt = [e for e in sorted(g.expiry.unique()) if e > e0]; atm2 = at(g[g.expiry == nxt[0]], 1.0) if nxt else np.nan
    rows[d] = dict(atm=atm, skew=skew, term=atm - atm2)
D = pd.DataFrame(rows).T.sort_index().astype(float); print(D.describe().round(3).to_string())
c = pd.Series(S.D['close'].values, index=S.D.index); rv = np.log(c).diff().rolling(20).std() * np.sqrt(252)
D = D.reindex(D.index.union(days)).ffill(limit=5).reindex(days)
Fe = {'O1': D['skew'], 'O2': D['skew'] - D['skew'].shift(5), 'O3': D['term'], 'O4': D['atm'] - rv.reindex(days)}; Fe = {k: v.shift(1) for k, v in Fe.items()}
def pct(x): return x.rolling(365, min_periods=120).apply(lambda v: (v[:-1] < v[-1]).mean(), raw=True)
m1 = pd.read_pickle(f'{R}/data/rm/dataset.pkl')['m1']; g = m1.groupby('date'); dop, dcl = g.open.first(), g.close.last()
BOOST = (pct(((dop / dcl.shift(1) - 1).abs()).reindex(days).shift(1)) > 0.8).fillna(False)
CP = ST.comps(em, 'floor'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET)
def stream(on, fac):
    f = pd.Series(np.where(BOOST, 1.25, 1.0), index=days) * pd.Series(np.where(on, fac, 1.0), index=days); e2 = dict(em); e2['ens'] = em['ens'] * f; return ST.stream(e2, None, S0, CP, EV)
off = pd.Series(False, index=days); base = stream(off, 1.0); bT = V.met(em, base, *TRAIN); bX = V.met(em, base, *TEST); print(f'\nlong-only base: TRAIN {fl(bT)} | TEST {fl(bX)}')
ens0 = em['ens'] * pd.Series(np.where(BOOST, 1.25, 1.0), index=days); lp = (ens0.shift(1).fillna(1.0) * CP[0] + ens0 * CP[1])[TRAIN[0]:TRAIN[1]]; worst, best = lp.nsmallest(20).index, lp.nlargest(20).index
rng = np.random.default_rng(1114); passed = []; near = []
for k, v in Fe.items():
    p = pct(v); print(f'{k}: coverage {v.notna().mean():.0%}')
    for tail, state in (('hi', p > 0.8), ('lo', p < 0.2)):
        state = state.fillna(False)
        for kind in ('CUT', 'BOOST'):
            w = int(state[worst if kind == 'CUT' else best].sum()); sh = state[TRAIN[0]:TRAIN[1]].mean(); gate = w >= 10 and sh <= 0.25
            if w >= 8: near.append(f'{kind} {k} {tail}: {w}/20 on {sh:.0%}')
            if not gate: continue
            fac = 0.5 if kind == 'CUT' else 1.25; net = stream(state, fac); dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; null = []
            for _ in range(200): kk = int(rng.integers(60, len(state) - 60)); null.append(L.eqdd(em, stream(pd.Series(np.roll(state.values, kk), index=days), fac), bT['MaxDD'], *TRAIN) - bT['CAGR'])
            p95 = np.percentile(null, 95); ok = dT > 0 and dT > p95 and dX >= 0; trial_log(f'OPT3_{kind}{k}{tail}', {}, 'train', V.met(em, net, *TRAIN)); passed += [(kind, k, tail)] if ok else []
            print(f'GATE PASS {kind} {k} {tail}: on {sh:.0%}, {w}/20 | TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} (p95 {p95 * 100:+.1f}) | TEST delta {dX * 100:+.1f} -> {"PASS" if ok else "fail"}')
print('near (8+/20):', near if near else 'none'); print('full passes:', passed)
