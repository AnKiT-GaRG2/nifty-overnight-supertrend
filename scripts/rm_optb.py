"""OPTB round: options + breadth add-ons on the executable frozen baseline, 2017-04..2023-12 only (see PROTOCOL_CHANGES.md).
Run: <venv>/bin/python scripts/rm_optb.py   (needs data/opt/nifty_options_daily_2017_2023.csv and data/opt/breadth_daily_2017_2023.csv)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_lock_dev as LD
from rm_engine import metrics_from
E, S, Ea, days, ens, INT = LD.E, LD.S, LD.Ea, LD.days, LD.ens, LD.INT; DATA, RES = LD.DATA, LD.RES
assert days.min() >= pd.Timestamp('2017-04-03') and days.max() <= pd.Timestamp('2023-12-31')
OC = ['date','expiry_today','near_expiry','call_oi_all','put_oi_all','call_vol_all','put_vol_all','call_oi_n','put_oi_n','call_vol_n','put_vol_n','call_wall_n','call_wall_oi_n','put_wall_n','put_wall_oi_n','maxpain_n','mon_expiry','call_oi_m','put_oi_m','call_wall_m','put_wall_m','maxpain_m']
BC = ['date','n_eq','adv','dec','unch','pct20','pct50','pct200','n20','n50','n200','new_hi','new_lo','tot_val']
opt = pd.read_csv(f'{DATA}/opt/nifty_options_daily_2017_2023.csv', names=OC, header=0, parse_dates=['date']).set_index('date').sort_index()
br = pd.read_csv(f'{DATA}/opt/breadth_daily_2017_2023.csv', names=BC, header=0, parse_dates=['date']).set_index('date').sort_index()
# ---- data-quality gates
print('# OPTB data-quality report')
print('rows by year options:', opt.groupby(opt.index.year).size().to_dict()); print('rows by year breadth:', br.groupby(br.index.year).size().to_dict())
gap_days = sorted(set(days) - set(opt.index)); print('Nifty trading days without option data:', len(gap_days), [str(d.date()) for d in gap_days[:10]])
gap_b = sorted(set(days) - set(br.index)); print('Nifty trading days without breadth data:', len(gap_b), [str(d.date()) for d in gap_b[:10]])
ok_opt = (opt.call_oi_all > 0).all() and (opt.put_oi_all > 0).all(); ok_br = ((br.adv + br.dec + br.unch) == br.n_eq).all() and br.pct50.dropna().between(0, 1).all() and br.pct200.dropna().between(0, 1).all()
print('options OI totals positive:', bool(ok_opt), '| breadth identity and ranges hold:', bool(ok_br))
opt = opt.reindex(days.union(opt.index)).ffill().reindex(days); br = br.reindex(days.union(br.index)).ffill().reindex(days)    # values dated d, aligned to Indian day d
def pct252(x): return x.rolling(252, min_periods=60).apply(lambda v: (v[:-1] < v[-1]).mean() * 100, raw=True)
spot = pd.Series(S.D['close'].values, index=S.D.index)
pcr_m = (opt.put_oi_m / opt.call_oi_m); pcr_pct = pct252(pcr_m)
ad = (br.adv / (br.adv + br.dec)).rolling(5, min_periods=3).mean(); ad_pct = pct252(ad)
wall_dist = (opt.call_wall_n - spot) / spot
def sh(x): return x.shift(1)      # value dated d-1 is usable at the open of day d
def cond(name, v):
    if name == 'O1a': c = sh(pcr_pct) < v
    elif name == 'O1b': c = sh(pcr_pct) > v
    elif name == 'O2': c = (sh(wall_dist) >= 0) & (sh(wall_dist) < v / 100.0)
    elif name == 'B1': c = sh(ad_pct) < v
    elif name == 'B2': c = sh(br.pct50) < v
    elif name == 'B3': c = sh(br.pct200) < v
    return c.reindex(days).fillna(False).astype(bool)
GRID = {'O1a': [10, 20, 30], 'O1b': [70, 80, 90], 'O2': [0.5, 1.0, 1.5], 'B1': [10, 20, 30], 'B2': [0.3, 0.4, 0.5], 'B3': [0.3, 0.4, 0.5]}
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
for k in STR: LD.trial_log('OPTB_' + k[1], {'v': k[2], 'c': k[0]}, 'train', met(STR[k], *DEV))
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
print('**OPTB verdict:** ' + ('an add-on passes under both cost models' if all(rows.values()) else 'no add-on passes under both cost models: baseline unchanged'))
