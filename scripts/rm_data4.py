"""DATA4: option-OI and India sector/ETF features as long-leg cut/boost on v2-FEG, sequential train -> valid -> test rule. Rules in PROTOCOL_CHANGES.md ROUND "DATA4". Run: <venv>/bin/python scripts/rm_data4.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
em = L.em; days = em['days']; R = V.ROOT; TR = ('2017-04-03', '2021-12-31'); VA = ('2022-01-01', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.142; fl = L.fl
X3 = pd.read_csv(f'{R}/data/xmkt3/all_close.csv', parse_dates=['date']).set_index('date'); X4 = pd.read_csv(f'{R}/data/xmkt4/all_close.csv', parse_dates=['date']).set_index('date')
X = X3[['^NSEI', '^NSMIDCP', '^CNXSC']].join(X4, how='outer').sort_index(); X = X.reindex(X.index.union(days)).ffill()
rt = lambda s, n: s / s.shift(n) - 1; N = X['^NSEI']
SEC = ['^NSEBANK', '^CNXIT', '^CNXFMCG', '^CNXPHARMA', '^CNXMETAL', '^CNXAUTO', '^CNXREALTY', '^CNXENERGY', '^CNXPSUBANK', '^CNXINFRA', '^CNXPSE', '^CNXMNC']
G = {}
G['S1'] = pd.concat([rt(X[c], 10) for c in ('^NSEBANK', '^CNXAUTO', '^CNXMETAL', '^CNXREALTY')], axis=1).mean(axis=1) - pd.concat([rt(X[c], 10) for c in ('^CNXFMCG', '^CNXPHARMA')], axis=1).mean(axis=1)
G['S2'] = rt(X['^CNXPSUBANK'], 10) - rt(X['^NSEBANK'], 10); G['S3'] = rt(X['^NSMIDCP'], 10) - rt(N, 10); G['S4'] = rt(X['^CNXSC'], 10) - rt(N, 10); G['S5'] = rt(X['^NSEBANK'], 10) - rt(N, 10)
G['S6'] = pd.concat([rt(X[c], 5) for c in SEC], axis=1).std(axis=1); G['I1'] = rt(X['INDA'], 1) - rt(N, 1); G['I2'] = rt(X['INDA'], 5) - rt(N, 5)
O = pd.read_csv(f'{R}/data/opt/nifty_opt_monthly_2017_2026.csv', parse_dates=['date', 'expiry']); Fs = O[O.type == 'F'].set_index(['date', 'expiry']).settle; Q = O[O.type != 'F']
rows = {}
for d, g in Q.groupby('date'):
    ex = sorted(e for e in g.expiry.unique() if (e - d).days >= 5)
    if not ex: continue
    a = g[g.expiry == ex[0]]; f = Fs.get((d, ex[0]), np.nan)
    if not f > 0: continue
    ce = a[a.type == 'CE'].groupby('strike').oi.sum(); pe = a[a.type == 'PE'].groupby('strike').oi.sum()
    if ce.sum() <= 0 or pe.sum() <= 0: continue
    ks = np.array(sorted(set(ce.index) | set(pe.index)), dtype=float); cv = ce.reindex(ks).fillna(0).values; pv = pe.reindex(ks).fillna(0).values
    pay = [(np.maximum(k - ks, 0) * pv).sum() + (np.maximum(ks - k, 0) * cv).sum() for k in ks]      # writers' payout if expiry settles at k (max pain minimises it)
    up = ks >= f; dn = ks <= f
    rows[d] = dict(P1=pe.sum() / ce.sum(), P3=ks[int(np.argmin(pay))] / f - 1, P4=(ks[up][np.argmax(cv[up])] / f - 1) if up.any() else np.nan, P5=(ks[dn][np.argmax(pv[dn])] / f - 1) if dn.any() else np.nan)
D = pd.DataFrame(rows).T.sort_index().astype(float); D['P2'] = D['P1'] - D['P1'].shift(5); D = D.reindex(D.index.union(days)).ffill(limit=5).reindex(days)
for k in ('P1', 'P2', 'P3', 'P4', 'P5'): G[k] = D[k]
G = {k: v.reindex(days) for k, v in G.items()}; F = {k: v.shift(1) for k, v in G.items()}; print({k: f'{v.notna().mean():.0%}' for k, v in F.items()})
def pct(x): return x.rolling(365, min_periods=120).apply(lambda v: (v[:-1] < v[-1]).mean(), raw=True)
m1 = pd.read_pickle(f'{R}/data/rm/dataset.pkl')['m1']; g = m1.groupby('date'); dop, dcl = g.open.first(), g.close.last()
BOOST = (pct(((dop / dcl.shift(1) - 1).abs()).reindex(days).shift(1)) > 0.8).fillna(False)
CP = ST.comps(em, 'floor'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET); EN = em['ens'] * pd.Series(np.where(BOOST, 1.25, 1.0), index=days)
def stream(on, fac): e2 = dict(em); e2['ens'] = EN * pd.Series(np.where(on, fac, 1.0), index=days); return ST.stream(e2, None, S0, CP, EV)
base = stream(pd.Series(False, index=days), 1.0); b = {n: V.met(em, base, *w) for n, w in (('TRAIN', TR), ('VALID', VA), ('TEST', TEST))}
print('base v2-FEG floor:', ' | '.join(f'{n} {fl(m)}' for n, m in b.items()))
lp = (EN.shift(1).fillna(1.0) * CP[0] + EN * CP[1])[TR[0]:TR[1]]; worst, best = lp.nsmallest(20).index, lp.nlargest(20).index
rng = np.random.default_rng(1115); near = []; passed = []; ncell = 0
def dlt(net, n, w): return L.eqdd(em, net, b[n]['MaxDD'], *w) - b[n]['CAGR']
for k, v in F.items():
    p = pct(v)
    for tail, st in (('hi', p > 0.8), ('lo', p < 0.2)):
        st = st.fillna(False).astype(bool)
        for kind in ('CUT', 'BOOST'):
            ncell += 1; w = int(st[worst if kind == 'CUT' else best].sum()); sh = st[TR[0]:TR[1]].mean()
            if w >= 8: near.append(f'{kind} {k} {tail}: {w}/20 on {sh:.0%}')
            if not (w >= 10 and sh <= 0.25): continue
            fac = 0.5 if kind == 'CUT' else 1.25; net = stream(st, fac); dT, dV, dX = dlt(net, 'TRAIN', TR), dlt(net, 'VALID', VA), dlt(net, 'TEST', TEST); null = []
            for _ in range(200): kk = int(rng.integers(60, len(st) - 60)); null.append(dlt(stream(pd.Series(np.roll(st.values, kk), index=days), fac), 'TRAIN', TR))
            p95 = np.percentile(null, 95); ok = dT > 0 and dT > p95 and dV >= 0 and dX >= 0; trial_log(f'DATA4_{kind}{k}{tail}', {}, 'train', V.met(em, net, *TR)); passed += [(kind, f'{k} {tail}', st, fac)] if ok else []
            print(f'GATE PASS {kind} {k} {tail}: on {sh:.0%}, {w}/20 | TRAIN {dT * 100:+.1f} (p95 {p95 * 100:+.1f}) | VALID {dV * 100:+.1f} | TEST {dX * 100:+.1f} -> {"PASS" if ok else "fail"}')
print('\ncells:', ncell, '| near (8+/20):', near if near else 'none'); print('full passes:', [(a, n) for a, n, _, _ in passed])
if len(passed) >= 2:
    m = pd.Series(1.0, index=days)
    for _, _, st, fac in passed: m = m * pd.Series(np.where(st, fac, 1.0), index=days)
    e2 = dict(em); e2['ens'] = EN * m; net = ST.stream(e2, None, S0, CP, EV); print('COMBINED', ' | '.join(f'{n} {fl(V.met(em, net, *w))} d{dlt(net, n, w) * 100:+.1f}' for n, w in (('TRAIN', TR), ('VALID', VA), ('TEST', TEST))))
