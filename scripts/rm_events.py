"""EVENTS2: tiers of extra event days added to the event cap (lists frozen in results/rm/EVENT_LISTS.md). Run: <venv>/bin/python scripts/rm_events.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_v2next as V, rm_v2lev as L, rm_stress as ST
from rm_ideas import trial_log
em = L.em; days = em['days']; TRAIN = ('2017-04-03', '2023-12-31'); TEST = ('2024-01-01', '2026-12-31'); S0 = 1.115; fl = L.fl
TIER_A = ['2017-12-18', '2018-05-15', '2018-12-11', '2019-10-24', '2020-11-10', '2021-05-02', '2022-03-10', '2022-12-08', '2023-03-02', '2023-05-13', '2023-12-03', '2024-11-23', '2025-11-14', '2026-05-04']        # first trading day on/after
FOMC = {2017: '05-03 06-14 07-26 09-20 11-01 12-13', 2018: '01-31 03-21 05-02 06-13 08-01 09-26 11-08 12-19', 2019: '01-30 03-20 05-01 06-19 07-31 09-18 10-30 12-11', 2020: '01-29 04-29 06-10 07-29 09-16 11-05 12-16',
        2021: '01-27 03-17 04-28 06-16 07-28 09-22 11-03 12-15', 2022: '01-26 03-16 05-04 06-15 07-27 09-21 11-02 12-14', 2023: '02-01 03-22 05-03 06-14 07-26 09-20 11-01 12-13', 2024: '01-31 03-20 05-01 06-12 07-31 09-18 11-07 12-18',
        2025: '01-29 03-19 05-07 06-18 07-30 09-17 10-29 12-10', 2026: '01-28 03-18 04-29 06-17 07-29 09-16 10-28'}
TIER_C = [f'{y}-{md}' for y, v in FOMC.items() for md in v.split()]
def mask(dates, after=False):
    m = pd.Series(False, index=days)
    for d in dates:
        t = pd.Timestamp(d); i = days.searchsorted(t, side=('right' if after else 'left'))
        if 0 <= i < len(days) and (days[0] <= t <= days[-1]): m.iloc[i] = True
    return m
E2 = ST.ev_mask(em, ST.ELECT + ST.BUDGET); CP = ST.comps(em, 'floor')
def ntr(m, w): return int(m[w[0]:w[1]].sum())
def stream(m): return ST.stream(em, None, S0, CP, m)
if __name__ == '__main__':
    base = stream(E2); bT = V.met(em, base, *TRAIN); bX = V.met(em, base, *TEST); rng = np.random.default_rng(6611)
    print(f'base v2-FE (-17% cap, scale {S0}) with E2 only: TRAIN {fl(bT)} | TEST {fl(bX)}\n')
    for name, m in (('A state elections', mask(TIER_A)), ('C FOMC reaction sessions', mask(TIER_C, after=True))):
        nt, nx = ntr(m, TRAIN), ntr(m, TEST)
        if nt < 6: print(f'{name}: only {nt} TRAIN event days -> not tested'); continue
        u = m | E2; net = stream(u); delta = L.eqdd(em, net, bT['MaxDD'], *TRAIN) - bT['CAGR']; null = []
        for _ in range(200):
            k = int(rng.integers(60, len(m) - 60)); ms = pd.Series(np.roll(m.values, k), index=m.index) | E2; null.append(L.eqdd(em, stream(ms), bT['MaxDD'], *TRAIN) - bT['CAGR'])
        p95 = np.percentile(null, 95); keep = delta > 0 and delta > p95; trial_log('EVENTS2_' + name[0], {}, 'train', V.met(em, net, *TRAIN))
        print(f'{name}: {nt} TRAIN / {nx} TEST event days | with cap: TRAIN {fl(V.met(em, net, *TRAIN))} | TEST {fl(V.met(em, net, *TEST))} || equal-DD delta TRAIN {delta * 100:+.1f} pts, TEST {(L.eqdd(em, net, bX["MaxDD"], *TEST) - bX["CAGR"]) * 100:+.1f} pts; null median {np.median(null) * 100:+.1f}, p95 {p95 * 100:+.1f}, beats {(np.array(null) < delta).mean():.0%} -> {"PASS" if keep else "no"}')
        d = pd.DataFrame({'uncapped': base, 'capped': net})[m & ~E2]; d['saved'] = d.capped - d.uncapped
        for lab, w in (('TRAIN', TRAIN), ('TEST', TEST)):
            x = d[w[0]:w[1]]; print(f'   per-event {lab}: {len(x)} events, cap helped on {(x.saved > 0).sum()}, hurt on {(x.saved < 0).sum()}; net {x.saved.sum() * 100:+.2f}% of capital; worst uncapped day {x.uncapped.min():+.1%}; best uncapped day {x.uncapped.max():+.1%}')
        if name.startswith('A'): print(d.round(4).to_string())
