"""FIIOI round: FII/DII participant open-interest add-ons on the executable frozen baseline, 2017-04..2023-12 only (see PROTOCOL_CHANGES.md).
Run: <venv>/bin/python scripts/rm_fii.py   (needs data/opt/fii_participant_oi_2017_2023.csv)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_lock_dev as LD
from rm_engine import metrics_from
E, S, Ea, days, ens, INT = LD.E, LD.S, LD.Ea, LD.days, LD.ens, LD.INT; DATA, RES = LD.DATA, LD.RES
assert days.min() >= pd.Timestamp('2017-04-03') and days.max() <= pd.Timestamp('2023-12-31')
raw = pd.read_csv(f'{DATA}/opt/fii_participant_oi_2017_2023.csv', parse_dates=['date']); raw.columns = [c.strip() for c in raw.columns]; raw['Client Type'] = raw['Client Type'].str.strip()
for c in raw.columns[2:]: raw[c] = pd.to_numeric(raw[c].astype(str).str.replace(',', '', regex=False), errors='coerce')   # 2019-12-12 has thousands separators
fii = raw[raw['Client Type'] == 'FII'].set_index('date').sort_index(); dii = raw[raw['Client Type'] == 'DII'].set_index('date').sort_index()
print('# FIIOI data-quality report'); print('rows by year:', fii.groupby(fii.index.year).size().to_dict())
gap = sorted(set(days) - set(fii.index)); print('Nifty trading days without FII data:', len(gap), [str(d.date()) for d in gap[:10]])
assert (fii['Future Index Long'] > 0).all() and (fii['Future Index Short'] > 0).all()
fii = fii.reindex(days.union(fii.index)).ffill().reindex(days)
ratio = (fii['Future Index Long'] - fii['Future Index Short']) / (fii['Future Index Long'] + fii['Future Index Short'])
dch = ratio - ratio.shift(5)
def pct252(x): return x.rolling(252, min_periods=60).apply(lambda v: (v[:-1] < v[-1]).mean() * 100, raw=True)
r_pct = pct252(ratio); d_pct = pct252(dch)
def sh(x): return x.shift(1)      # published after the close of d-1 -> usable at the open of d
def cond(name, v):
    if name == 'F1a': c = sh(r_pct) < v
    elif name == 'F1b': c = sh(r_pct) > v
    elif name == 'F2': c = sh(d_pct) < v
    elif name == 'F3': c = sh(ratio) < v
    return c.reindex(days).fillna(False).astype(bool)
GRID = {'F1a': [10, 20, 30], 'F1b': [70, 80, 90], 'F2': [10, 20, 30], 'F3': [0.2, 0.4, 0.6]}
PARTS = {}
for cost in ('real', 'floor'):
    L, G, I, Sh = LD.run_legs(Ea, S, 'base', cost); PARTS[cost] = (G, I, 0.956 * Sh)
def stream(cost, name=None, v=None):
    G, I, Sc = PARTS[cost]; m = ens.copy()
    if name is not None: m = ens * pd.Series(np.where(cond(name, v), 0.5, 1.0), index=days)
    return 1.912 * (m.shift(1).fillna(1.0) * G + m * I) + Sc
def met(net, a, z): ex = net[a:z]; return metrics_from(ex + INT[a:z], None, None, None, ex)
fl = lambda m: f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
def eqdd(net, ref, a, z):
    lo, hi = 0.05, 4.0
    for _ in range(40):
        s = (lo + hi) / 2
        if met(net * s, a, z)['MaxDD'] < ref: hi = s
        else: lo = s
    return lo, met(net * lo, a, z)
DEV = ('2017-04-03', '2023-12-31'); STR = {(c, n, v): stream(c, n, v) for c in ('real', 'floor') for n, g in GRID.items() for v in g}
for k in STR: LD.trial_log('FIIOI_' + k[1], {'v': k[2], 'c': k[0]}, 'train', met(STR[k], *DEV))
print('\n## Fixed cells on DEV 2017-04..2023-12 (descriptive; CAGR / MaxDD / Sharpe; equal-drawdown CAGR; share of days triggered)\n')
for cost in ('real', 'floor'):
    base = stream(cost); mb = met(base, *DEV); print(f'{cost} costs. Baseline dev: {fl(mb)}'); print('| Factor | CAGR / MaxDD / Sharpe | Equal-drawdown CAGR | Days triggered |'); print('|---|---|---|---|')
    for n, g in GRID.items():
        for v in g:
            net = STR[(cost, n, v)]; sc, me = eqdd(net, mb['MaxDD'], *DEV); print(f"| {n} {v} | {fl(met(net, *DEV))} | {me['CAGR']:.1%} | {cond(n, v).mean():.0%} |")
    print()
folds = []; a0 = pd.Timestamp('2020-04-01')
while a0 <= pd.Timestamp('2023-12-31'):
    z0 = min(a0 + pd.DateOffset(months=6) - pd.Timedelta(days=1), pd.Timestamp('2023-12-31')); folds.append((a0, z0, a0 - pd.DateOffset(years=3), a0 - pd.Timedelta(days=1))); a0 += pd.DateOffset(months=6)
def pick(cost, t0, t1):
    ref = met(stream(cost), t0, t1); best = None
    for n, grid in GRID.items():
        mets = {v: met(STR[(cost, n, v)], t0, t1) for v in grid}; lift = {v: mets[v]['Sharpe'] - ref['Sharpe'] for v in grid}
        for v in grid[1:-1]:
            i = grid.index(v); nb = [grid[j] for j in (i - 1, i + 1)]
            if lift[v] >= 0.05 and mets[v]['MaxDD'] >= ref['MaxDD'] - 1e-9 and np.mean([lift[x] > 0 for x in nb]) >= 0.7:
                sc = np.mean([lift[v]] + [lift[x] for x in nb])
                if best is None or sc > best[0]: best = (sc, n, v)
    return (best[1], best[2]) if best else None
rows = {}
for cost in ('real', 'floor'):
    P0, P1, picks = [], [], []
    for a, z, t0, t1 in folds:
        sp = pick(cost, t0, t1); picks.append((str(a.date()), sp)); P0.append(stream(cost)[a:z]); P1.append((stream(cost, *sp) if sp else stream(cost))[a:z])
    s0, s1 = pd.concat(P0), pd.concat(P1); a, z = str(folds[0][0].date()), str(folds[-1][1].date()); m0, m1 = met(s0, a, z), met(s1, a, z); sc, me = eqdd(s1, m0['MaxDD'], a, z)
    ok = (m1['Sharpe'] >= m0['Sharpe'] + 0.10) and (me['CAGR'] >= m0['CAGR'] + 0.02); rows[cost] = ok
    print(f"## Walk-forward ({cost} costs): picks per fold {picks}\n   stitched OOS 2020-04..2023-12: baseline {fl(m0)} | with picked add-on {fl(m1)} | scaled to baseline drawdown: CAGR {me['CAGR']:.1%} (scale {sc:.2f}) -> {'PASS' if ok else 'FAIL'}\n")
print('**FIIOI verdict:** ' + ('an add-on passes under both cost models' if all(rows.values()) else 'no add-on passes under both cost models: baseline unchanged'))
