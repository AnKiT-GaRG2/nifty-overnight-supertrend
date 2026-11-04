"""LONGML: ML size modifier for the long leg. Rules in PROTOCOL_CHANGES.md ROUND "LONGML". Run: <venv>/bin/python scripts/rm_longml.py"""
import sys, os, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
from sklearn.linear_model import Ridge
from sklearn.preprocessing import QuantileTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
em = L.em; days = em['days']; R = V.ROOT; D = lambda p: f'{R}/data/{p}'; fl = L.fl
OOS = ('2020-01-01', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; ST.WS = 1e-9
CP = ST.comps(em, 'floor'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET)
def ser(path, col='close'):
    d = pd.read_csv(D(path), parse_dates=['date']).set_index('date').sort_index()[col]; d = d[~d.index.duplicated()]
    return d.reindex(d.index.union(days)).ffill().reindex(days)
nd = pd.Series(em['S'].D['close'].values, index=em['S'].D.index); hi_ = pd.Series(em['S'].D['high'].values, index=em['S'].D.index); lo_ = pd.Series(em['S'].D['low'].values, index=em['S'].D.index); op_ = pd.Series(em['S'].D['open'].values, index=em['S'].D.index)
nd, hi_, lo_, op_ = (x.reindex(days) for x in (nd, hi_, lo_, op_)); r1 = nd.pct_change(); F = {}
for n in (1, 5, 20, 60): F[f'ret{n}'] = nd.pct_change(n)
for n in (20, 50, 200): F[f'dsma{n}'] = nd / nd.rolling(n).mean() - 1
atr = (hi_ - lo_).rolling(14).mean() / nd; F['atr'] = atr; v20, v60 = r1.rolling(20).std(), r1.rolling(60).std(); F['rv20'], F['rv60'], F['rvr'] = v20, v60, v20 / v60
F['range1'] = (hi_ - lo_) / nd; F['gap1'] = op_ / nd.shift(1) - 1; up = (r1 > 0).astype(int); F['streak'] = up.groupby((up != up.shift()).cumsum()).cumcount() * np.where(up > 0, 1, -1)
F['pos20'] = (nd - nd.rolling(20).min()) / (nd.rolling(20).max() - nd.rolling(20).min())
vix = ser('vix_ext.csv'); F['vix'] = vix; F['vix5'] = vix / vix.shift(5) - 1; F['vixp'] = vix.rolling(252).apply(lambda v: (v[:-1] < v[-1]).mean(), raw=True); F['vixrv'] = vix / 100 - v20 * np.sqrt(252)
for nm, p in (('usdinr', 'usdinr.csv'), ('brent', 'brent.csv'), ('wti', 'wti.csv'), ('gold', 'gold.csv'), ('dxy', 'dxy.csv'), ('spx', 'spx.csv'), ('nasdaq', 'nasdaq.csv')):
    s = ser(p); F[nm + '5'] = s / s.shift(5) - 1
    if nm in ('spx', 'nasdaq'): F[nm + '1'] = s / s.shift(1) - 1
F['us10y5'] = ser('us10y.csv') - ser('us10y.csv').shift(5); bn = ser('banknifty.csv'); F['bnrel10'] = (bn / bn.shift(10) - 1) - nd.pct_change(10)
F['hyg_ief5'] = (lambda s: s / s.shift(5) - 1)(ser('xmkt/HYG.csv') / ser('xmkt/IEF.csv')); F['eem5'] = (lambda s: s / s.shift(5) - 1)(ser('xmkt/EEM.csv'))
f = pd.read_csv(D('fut/nifty_fut.csv'), parse_dates=['date', 'expiry']); rows = {}
for d, g in f.groupby('date'):
    g = g.sort_values('expiry'); g = g[g.expiry >= d]
    if len(g) >= 2: n, x = g.iloc[0], g.iloc[1]; rows[d] = dict(f1=(x.close / n.close - 1) * 365 / max((x.expiry - n.expiry).days, 1), oi=g.oi.sum(), vol=g.volume.sum(), f4=n.oi / g.oi.sum(), dte=(n.expiry - d).days)
FD = pd.DataFrame(rows).T.sort_index().astype(float).reindex(days.union(pd.DatetimeIndex(list(rows)))).ffill().reindex(days)
F['f1'], F['f2'], F['f3'], F['f4'], F['dte'] = FD.f1, FD.oi / FD.oi.shift(5) - 1, FD.vol / FD.vol.rolling(20).mean(), FD.f4, FD.dte
X = pd.read_csv(D('xmkt2/all_close.csv'), parse_dates=['date']).set_index('date').sort_index(); X = X.reindex(X.index.union(days)).ffill()
sec = X[['^CNXIT', '^CNXFMCG', '^CNXAUTO', '^CNXPHARMA', '^CNXMETAL', '^CNXREALTY', '^CNXENERGY', '^CNXPSUBANK', '^CNXINFRA']]; fgn = X[['^N225', '^HSI', '^KS11', '^AXJO', '^FTSE', '^GDAXI']]; hw = X[['HDFCBANK.NS', 'RELIANCE.NS', 'ICICIBANK.NS', 'INFY.NS', 'TCS.NS']]
ndx = nd.reindex(X.index.union(days)).ffill().reindex(X.index)
d1 = (np.log(sec[['^CNXFMCG', '^CNXPHARMA']].mean(axis=1)) - np.log(sec[['^CNXAUTO', '^CNXMETAL', '^CNXREALTY']].mean(axis=1))).diff(10)
for nm, s in (('d1', d1), ('d2', (sec > sec.rolling(50).mean()).mean(axis=1)), ('d3', (fgn / fgn.shift(5) - 1).mean(axis=1)), ('d4', (hw / hw.shift(10) - 1).mean(axis=1) - (ndx / ndx.shift(10) - 1)), ('d5', (sec['^CNXIT'] / sec['^CNXIT'].shift(10) - 1) - (ndx / ndx.shift(10) - 1))):
    F[nm] = s.reindex(days)
F['dow'] = pd.Series(days.dayofweek, index=days).astype(float); F['mon'] = pd.Series(days.month, index=days).astype(float)
Fd = pd.DataFrame(F).shift(1); Fd['dow'] = F['dow']; Fd['mon'] = F['mon']; Fd['dte'] = F['dte'].shift(1)          # calendar items are known in advance
Fd = Fd.replace([np.inf, -np.inf], np.nan); print('features:', Fd.shape[1])
GL, IL, FL = CP[0], CP[1], CP[2]; y = (GL + IL); active = ((FL > 0) | (IL.abs() > 0)); y = y.clip(y.quantile(0.01), y.quantile(0.99))
def fit(kind, tr):
    Xt = Fd.loc[tr]; yt = y.loc[tr]; Xt = Xt[active.loc[tr]]; yt = yt[active.loc[tr]]
    if kind == 'M1':
        med = Xt.median(); q = QuantileTransformer(n_quantiles=200, output_distribution='normal').fit(Xt.fillna(med)); m = Ridge(alpha=300).fit(q.transform(Xt.fillna(med)), yt); return lambda Z: pd.Series(m.predict(q.transform(Z.fillna(med))), index=Z.index)
    m = HistGradientBoostingRegressor(max_depth=2, max_iter=80, learning_rate=0.05, min_samples_leaf=40, l2_regularization=5.0, random_state=1).fit(Xt, yt); return lambda Z: pd.Series(m.predict(Z), index=Z.index)
def preds(kind, years):
    out = []
    for yr in years:
        tr = days[(days >= '2017-04-03') & (days < f'{yr}-01-01')]; te = days[(days.year == yr)]; out.append(fit(kind, tr)(Fd.loc[te]))
    return pd.concat(out)
def to_m(p):
    m = pd.Series(1.0, index=p.index); hist = []
    for d, v in p.items():
        if len(hist) >= 60: a = np.array(hist); lo, hi = np.percentile(a, 30), np.percentile(a, 70); m[d] = 0.5 if v < lo else (1.5 if v > hi else 1.0)
        hist.append(v)
    return m
def stream(m):
    e2 = dict(em); e2['ens'] = em['ens'] * m.reindex(days).fillna(1.0); return ST.stream(e2, None, S0, CP, EV)
base = stream(pd.Series(1.0, index=days)); bO = V.met(em, base, *OOS); bX = V.met(em, base, *TEST); print(f'long-only base: OOS 2020-23 {fl(bO)} | TEST {fl(bX)}\n'); rng = np.random.default_rng(1109)
P = {k: preds(k, (2020, 2021, 2022, 2023)) for k in ('M1', 'M2')}
rk = lambda p: p.expanding(min_periods=60).apply(lambda v: (v[:-1] < v[-1]).mean() if len(v) > 1 else .5, raw=True).fillna(0.5)
for kind in tuple(os.environ.get('KINDS', 'M1,M2,M3').split(',')):
    p = P[kind] if kind != 'M3' else (rk(P['M1']) + rk(P['M2'])) / 2
    ic = np.corrcoef(p[active.reindex(p.index)].values, y.reindex(p.index)[active.reindex(p.index)].values)[0, 1]; m = to_m(p) if kind != 'M3' else to_m(p)
    net = stream(m); dO = L.eqdd(em, net, bO['MaxDD'], *OOS) - bO['CAGR']; null = []
    for _ in range(200): k = int(rng.integers(60, len(m) - 60)); null.append(L.eqdd(em, stream(pd.Series(np.roll(m.values, k), index=m.index)), bO['MaxDD'], *OOS) - bO['CAGR'])
    p95 = np.percentile(null, 95); trial_log(f'LONGML_{kind}', {}, 'train', V.met(em, net, *OOS)); okO = dO > 0 and dO > p95
    print(f'{kind}: OOS IC {ic:+.3f}; OOS {fl(V.met(em, net, *OOS))} delta {dO * 100:+.1f} pts (null p95 {p95 * 100:+.1f}, beats {(np.array(null) < dO).mean():.0%}) -> {"OOS pass" if okO else "OOS fail"}')
    if okO:
        trs = days[(days >= '2017-04-03') & (days <= '2023-12-31')]; tes = days[days >= '2024-01-01']
        if kind == 'M3': pt = pd.concat([P['M1'], fit('M1', trs)(Fd.loc[tes])]); pq = pd.concat([P['M2'], fit('M2', trs)(Fd.loc[tes])]); pall = (rk(pt) + rk(pq)) / 2
        else: pall = pd.concat([P[kind], fit(kind, trs)(Fd.loc[tes])])
        mt = to_m(pall); nt = stream(mt); dX = L.eqdd(em, nt, bX['MaxDD'], *TEST) - bX['CAGR']; print(f'   FROZEN TEST {fl(V.met(em, nt, *TEST))} vs base {fl(bX)}: delta {dX * 100:+.1f} pts -> {"PASS" if dX >= 0 else "FAIL"}')
