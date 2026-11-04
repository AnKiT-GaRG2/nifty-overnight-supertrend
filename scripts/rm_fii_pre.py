"""STEP 6 FII-PRE: pre-declared FII add-on on the pre-2017 holdout (see PROTOCOL_CHANGES.md 'STEP 6'). Run: <venv>/bin/python scripts/rm_fii_pre.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V
from rm_engine import metrics_from
from rm_ideas import trial_log
env = V.env_pre(); days = env['days']; INT = env['INT']; ens = env['ens']
f = pd.read_csv(f'{V.ROOT}/data/opt/fii_idx_oi_2012_2017.csv', parse_dates=['date']).set_index('date').sort_index()
print('Nifty sessions without an FII file:', len(set(days) - set(f.index)), [str(d.date()) for d in sorted(set(days) - set(f.index))[:8]])
f = f.reindex(days.union(f.index)).ffill().reindex(days)
ratio = (f.fii_idx_long - f.fii_idx_short) / (f.fii_idx_long + f.fii_idx_short); dch = ratio - ratio.shift(5)
pct = lambda x: x.rolling(252, min_periods=60).apply(lambda v: (v[:-1] < v[-1]).mean() * 100, raw=True)
rp, dp = pct(ratio), pct(dch)
cond = lambda fam, q: ((rp if fam == 'F1a' else dp).shift(1) < q).fillna(False).astype(bool)
sig = V.signals(env, 'v2'); WIN = {'primary 2013-07..2016-08': ('2013-07-01', '2016-08-31'), 'whole 2012-07..2016-08': ('2012-07-02', '2016-08-31')}
met = lambda net, a, z: (lambda ex: metrics_from(ex + INT[a:z], None, None, None, ex))(net[a:z])
fl = lambda m: f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
def eqdd(net, ref, a, z):
    lo, hi = 0.05, 4.0
    for _ in range(40):
        s = (lo + hi) / 2
        if met(net * s, a, z)['MaxDD'] < ref: hi = s
        else: lo = s
    return met(net * lo, a, z)['CAGR']
verdict = {}
for cost in ('real', 'floor'):
    L, G, I, Sh, R = V.legs(env, sig, cost); mult = lambda m: 1.912 * (m.shift(1).fillna(1.0) * G + m * I) + 0.956 * Sh
    base = mult(ens); print(f'\n### {cost} costs (CAGR / MaxDD / Sharpe)')
    for wn, (a, z) in WIN.items():
        mb = met(base, a, z); print(f'\n{wn}: baseline v2 {fl(mb)}'); print('| cell | result | Sharpe lift | equal-drawdown CAGR (baseline CAGR %.1f%%) | days triggered |' % (mb['CAGR'] * 100)); print('|---|---|---|---|---|')
        for fam in ('F1a', 'F2'):
            for q in (10, 20, 30):
                c = cond(fam, q); net = mult(ens * pd.Series(np.where(c, 0.5, 1.0), index=days)); m = met(net, a, z)
                ed = eqdd(net, mb['MaxDD'], a, z); lift = m['Sharpe'] - mb['Sharpe']; verdict[(cost, wn, fam, q)] = (lift, ed - mb['CAGR'])
                print(f"| {fam} q={q} | {fl(m)} | {lift:+.2f} | {ed:.1%} | {c[a:z].mean():.0%} |")
                if wn.startswith('primary'): trial_log('FIIPRE_' + fam, {'q': q, 'cost': cost}, 'train', m)
print('\n## PASS test (primary window, BOTH cost models: plateau lift>0 for q=10,20,30; q=20 lift>=+0.10; q=20 equal-drawdown CAGR >= +2 pts)')
for fam in ('F1a', 'F2'):
    ok = True; det = []
    for cost in ('real', 'floor'):
        w = 'primary 2013-07..2016-08'; l = [verdict[(cost, w, fam, q)][0] for q in (10, 20, 30)]; e = verdict[(cost, w, fam, 20)][1]
        c = all(x > 0 for x in l) and l[1] >= 0.10 and e >= 0.02; ok &= c; det.append(f'{cost}: lifts {[round(x, 2) for x in l]}, eq-DD CAGR {e:+.1%} -> {c}')
    print(f"- {fam}: {'PASS' if ok else 'FAIL'}  ({'; '.join(det)})")
