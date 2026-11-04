"""NEWSTRAT: spread/trend sleeves on v2-FE. Rules in PROTOCOL_CHANGES.md ROUND "NEWSTRAT". Run: <venv>/bin/python scripts/rm_newstrat.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
em = L.em; days = em['days']; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.163; fl = L.fl; R = V.ROOT
def load(paths):
    f = pd.concat([pd.read_csv(f'{R}/data/fut/{p}', parse_dates=['date', 'expiry']) for p in paths]).drop_duplicates(['date', 'expiry'])
    return f[(f.open > 0) & (f.close > 0)].sort_values(['date', 'expiry'])
def series(f):
    """per date: contract (nearest expiry > d), open, close, next-session open of the same expiry"""
    op = f.pivot(index='date', columns='expiry', values='open'); cl = f.pivot(index='date', columns='expiry', values='close'); dts = op.index; exps = op.columns.values; rows = []
    for i, d in enumerate(dts[:-1]):
        valid = [e for e in exps if e > d and not np.isnan(op.at[d, e])]
        if not valid: continue
        e = min(valid); nxt = op.at[dts[i + 1], e] if e in op.columns else np.nan
        rows.append((d, e, op.at[d, e], cl.at[d, e], nxt))
    return pd.DataFrame(rows, columns=['date', 'exp', 'open', 'close', 'nopen']).set_index('date')
nf = series(load(['nifty_fut_2012_2017.csv', 'nifty_fut.csv'])); bf = series(load(['banknifty_fut.csv']))
idx = nf.index.intersection(bf.index); nf, bf = nf.loc[idx], bf.loc[idx]
rn = (nf.nopen / nf.open - 1); rb = (bf.nopen / bf.open - 1); rollN = (nf.exp != nf.exp.shift(1)).astype(float); rollB = (bf.exp != bf.exp.shift(1)).astype(float)
CS, CR = 2.5e-4, 5e-4
def pnl(wn, wb):
    """wn, wb: notional per leg held from open d (decided with data to d-1)"""
    gross = wn * rn.fillna(0) + wb * rb.fillna(0); dn = wn.diff().abs().fillna(0); db = wb.diff().abs().fillna(0)
    cost = CS * (dn + db) + CR * (rollN * wn.abs() + rollB * wb.abs()); return gross - cost
def to_days(s):   # return open d -> open d+1 is booked on day d+1 (when it is realised)
    return s.shift(1).reindex(days).fillna(0.0)
# P1 / P2
r = np.log(bf.close / nf.close); z = (r.shift(1) - r.shift(1).rolling(60).mean()) / r.shift(1).rolling(60).std()
pos = np.zeros(len(z)); cur = 0
for i, v in enumerate(z.values):
    if np.isnan(v): pos[i] = 0; continue
    if cur == 0:
        if v < -2: cur = 1
        elif v > 2: cur = -1
    elif abs(v) < 0.5 or (cur == 1 and v > 2) or (cur == -1 and v < -2): cur = 0 if abs(v) < 0.5 else (-cur)
    pos[i] = cur
p1 = pd.Series(pos, index=idx); P1 = pnl(-p1, p1)                      # +1 = long BN / short Nifty
mom = np.sign(r.shift(1) - r.shift(21)).fillna(0); P2 = pnl(-mom, mom)
c = nf.close; sma = c.rolling(100).mean(); vol = np.log(c).diff().rolling(20).std() * np.sqrt(252)
w3 = (np.minimum(2.5, 0.12 / vol.shift(1)) * (c.shift(1) > sma.shift(1))).fillna(0); P3 = pnl(w3, w3 * 0)
CP = ST.comps(em, 'floor'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET); base = ST.stream(em, None, S0, CP, EV); bT = V.met(em, base, *TRAIN); bX = V.met(em, base, *TEST)
sh = lambda x, w: (lambda y: y.mean() / y.std() * np.sqrt(252))(x[w[0]:w[1]])
print(f'base v2-FE: TRAIN {fl(bT)} | TEST {fl(bX)}\n'); rng = np.random.default_rng(1107); sdB = base[TRAIN[0]:TRAIN[1]].std()
for name, P in (('P1 spread mean-reversion', P1), ('P2 spread momentum', P2), ('P3 vol-managed daily trend', P3)):
    s = to_days(P); print(f'{name}: standalone excess Sharpe TRAIN {sh(s, TRAIN):.2f} TEST {sh(s, TEST):.2f}; corr with v2-FE (TRAIN) {s[TRAIN[0]:TRAIN[1]].corr(base[TRAIN[0]:TRAIN[1]]):+.2f}')
    k = 0.5 * sdB / s[TRAIN[0]:TRAIN[1]].std(); net = base + k * s; dT = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; dX = L.eqdd(em, net, bX['MaxDD'], *TEST) - bX['CAGR']; null = []
    for _ in range(200):
        kk = int(rng.integers(60, len(s) - 60)); null.append(L.eqdd(em, base + k * pd.Series(np.roll(s.values, kk), index=days), bT['MaxDD'], *TRAIN) - bT['CAGR'])
    p95 = np.percentile(null, 95); ok = dT > 0 and dT > p95 and dX >= 0; trial_log('NEWSTRAT_' + name[:2], {}, 'train', V.met(em, net, *TRAIN))
    print(f'   sleeve k={k:.2f}: TRAIN {fl(V.met(em, net, *TRAIN))} delta {dT * 100:+.1f} pts (null p95 {p95 * 100:+.1f}); TEST {fl(V.met(em, net, *TEST))} delta {dX * 100:+.1f} -> {"PASS" if ok else "FAIL"}')
