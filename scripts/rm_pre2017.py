"""Pre-2017 out-of-sample check of the frozen 'ROBUST' system with a DAILY-BAR proxy on REAL futures prices.
Rules (written before running): results/rm/PROTOCOL_CHANGES.md, section 'PRE-2017 OUT-OF-SAMPLE CHECK'.
Run: <venv>/bin/python scripts/rm_pre2017.py"""
import os, sys, json, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from rm_engine import metrics_from, RF
from rm_signals import supertrend
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA = f'{ROOT}/data'; RES = f'{ROOT}/results/rm'
COST, ROLL = 0.00025, 0.0005

def load_fut():
    fs = [f'{DATA}/fut/nifty_fut_pre2017.csv', f'{DATA}/fut/nifty_fut_2012_2017.csv', f'{DATA}/fut/nifty_fut.csv']
    d = pd.concat([pd.read_csv(f, parse_dates=['date', 'expiry']) for f in fs]).drop_duplicates(['date', 'expiry'])
    return d[(d.open > 0) & (d.high > 0) & (d.low > 0) & (d.close > 0)].sort_values(['date', 'expiry'])

def build(fut):
    F = fut.set_index(['date', 'expiry']); dates = pd.DatetimeIndex(sorted(fut.date.unique())); pos = {d: i for i, d in enumerate(dates)}
    last = fut.groupby('expiry').date.max(); R = {}
    for e, ld in last.items():
        i = pos[ld]; R[e] = dates[i - 2] if (i >= 2 and ld >= e - pd.Timedelta(days=4)) else pd.Timestamp('2100-01-01')
    by = fut.groupby('date').expiry.apply(lambda s: sorted(s))
    rows = []; prevd = None
    for d in dates:
        c = by[d]; near = c[0]; use = near if (d <= R[near] or len(c) < 2) else c[1]
        r = F.loc[(d, use)]; prevc = F.loc[(prevd, use), 'close'] if (prevd is not None and (prevd, use) in F.index) else np.nan
        rows.append((d, use, r.open, r.high, r.low, r.close, prevc, (use == near) and (d == R[near])))
        prevd = d
    X = pd.DataFrame(rows, columns=['date', 'held', 'open', 'high', 'low', 'close', 'prev', 'roll']).set_index('date')
    X['prev'] = X['prev'].fillna(X['open'].shift(0)); X.iloc[0, X.columns.get_loc('prev')] = X.iloc[0]['open']
    k = (X.close / X.prev).fillna(1.0).values; adj = np.empty(len(X)); adj[0] = 100.0
    for i in range(1, len(X)): adj[i] = adj[i - 1] * k[i]
    pa = np.r_[adj[0], adj[:-1]]
    X['aclose'] = adj; X['aopen'] = pa * (X.open / X.prev).values; X['ahigh'] = pa * (X.high / X.prev).values; X['alow'] = pa * (X.low / X.prev).values
    X['ahigh'] = np.maximum.reduce([X.ahigh, X.aopen, X.aclose]); X['alow'] = np.minimum.reduce([X.alow, X.aopen, X.aclose])
    return X

def series(path_pre, path_post, col='close'):
    a = pd.read_csv(path_pre, parse_dates=['date']).set_index('date')[col]; b = pd.read_csv(path_post, parse_dates=['date']).set_index('date')[col]
    s = pd.concat([a, b]); return s[~s.index.duplicated(keep='first')].sort_index()

class Sys:
    def __init__(self):
        self.fut = load_fut(); self.X = build(self.fut); X = self.X; self.days = X.index
        self.cal = np.r_[1, np.diff(self.days.values).astype('timedelta64[D]').astype(int)]; self.INT = pd.Series(RF * self.cal / 365.0, index=self.days)
        self.nq = series(f'{DATA}/pre/nasdaq.csv', f'{DATA}/nasdaq.csv'); self.us = series(f'{DATA}/pre/us10y.csv', f'{DATA}/us10y.csv')
        self.sma = X.aclose.rolling(100).mean()
    def prior(self, s, n, kind='pct'):
        s = s.dropna(); s = (s / s.shift(n) - 1) if kind == 'pct' else (s - s.shift(n)); p = np.searchsorted(s.index.values, self.days.values, side='left') - 1
        return pd.Series(np.where(p >= 0, s.values[np.maximum(p, 0)], np.nan), index=self.days)
    def cell_scale(self, x, y, c=0.25):
        nq = (self.prior(self.nq, 5) * 100 < -x).fillna(False); mc = (self.prior(self.us, 5, 'diff') * 100 > y).fillna(False)
        return pd.Series(np.where(nq, c, 1.0), index=self.days) * pd.Series(np.where(mc, c, 1.0), index=self.days)
    def ens_scale(self): return sum(self.cell_scale(x, y) for x in (1, 2, 3) for y in (10, 15, 20)) / 9.0
    def st(self, n, m):
        X = self.X; d, _ = supertrend(X.ahigh.values, X.alow.values, X.aclose.values, n, m, warm=n); return pd.Series(d, index=self.days)
    def weights(self, n, m, wl, ws, scale=None, long_on=True, short_on=True):
        d = self.st(n, m).shift(1); cprev = self.X.aclose.shift(1); sprev = self.sma.shift(1)
        L = ((d == 1)).astype(float); Sh = ((d == -1) & (cprev < sprev)).astype(float)
        sc = pd.Series(1.0, index=self.days) if scale is None else scale
        return (wl * sc * L if long_on else 0 * L) - (ws * Sh if short_on else 0 * Sh)
    def backtest(self, pos):
        X = self.X; pp = pos.shift(1).fillna(0.0); gap = (X.open / X.prev - 1).fillna(0.0); day = (X.close / X.open - 1).fillna(0.0)
        gross = pp * gap + pos * day; cost = (pos - pp).abs() * COST + X.roll.astype(float) * pos.abs() * ROLL
        return gross - cost, (pos - pp).abs()
def met(sy, net, a, z):
    ex = net[a:z]; return metrics_from(ex + sy.INT[a:z], None, None, None, ex)
fl = lambda m: f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
def entries_per_year(pos, a, z):
    p = pos[a:z] > 0; e = ((p) & (~p.shift(1, fill_value=False))).sum(); return e / (len(p) / 252)

def main():
    sy = Sys(); rep = []; P = lambda *a: (print(*a), rep.append(' '.join(str(x) for x in a)))
    DEV = ('2017-04-03', '2023-12-31'); PRE = ('2008-03-03', '2017-03-31')
    # ---- calibration on DEV only
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from rm_ideas import Engine, make_sig
    E = Engine(); S = make_sig(E); real = pd.Series(E.run(*S.baseline(), cost='floor').net_d, index=E.days)
    P('# Pre-2017 out-of-sample check (daily-bar proxy on REAL NSE futures prices)\n')
    P(f"Data: real futures daily bars {sy.days[0].date()}..{sy.days[-1].date()} ({len(sy.days)} sessions); continuous front-month, roll 2 trading days before expiry.\n")
    P('## Calibration of the daily Supertrend proxy on DEV only (2017-04..2023-12): corr of long-only daily excess returns with the real 15-min baseline, entries/yr\n')
    best = None; rows = []
    for n, m in itertools.product([1, 2, 3, 5, 7, 10, 14], [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]):
        pos = sy.weights(n, m, 1.0, 0.0, short_on=False); net, _ = sy.backtest(pos); idx = net[DEV[0]:DEV[1]].index.intersection(real[DEV[0]:DEV[1]].index)
        corr = net[idx].corr(real[idx]); ent = entries_per_year(pos, *DEV); rows.append((n, m, corr, ent, met(sy, net, *DEV)['Sharpe']))
        if 60 <= ent <= 120 and (best is None or corr > best[2]): best = (n, m, corr, ent)
    P('| n | m | corr with real baseline | entries/yr | proxy dev Sharpe |'); P('|---|---|---|---|---|')
    for r in sorted(rows, key=lambda r: -r[2])[:8]: P(f"| {r[0]} | {r[1]} | {r[2]:.2f} | {r[3]:.0f} | {r[4]:.2f} |")
    if best is None: P('\nNo grid cell has 60-120 entries/yr: check INCONCLUSIVE.'); open(f'{RES}/PRE2017_REPORT.md', 'w').write('\n'.join(rep)); return
    n, m, corr, ent = best; P(f"\nChosen proxy (highest dev correlation with 60-120 entries/yr): Supertrend({n}, {m}) on daily bars; dev correlation {corr:.2f}, {ent:.0f} entries/yr (real system ~90/yr).")
    if corr < 0.5: P('\nDev correlation below 0.5 -> the check is declared INCONCLUSIVE (proxy does not resemble the system). Stopping.'); open(f'{RES}/PRE2017_REPORT.md', 'w').write('\n'.join(rep)); return
    # ---- systems
    ens = sy.ens_scale(); wl, ws = 2.0 * 0.956, 1.0 * 0.956
    V = {'Plain long-only (proxy baseline)': sy.weights(n, m, 1.0, 0.0, short_on=False),
         'Buy and hold futures (1x)': pd.Series(1.0, index=sy.days),
         'Same weights, no cuts (1.91 long / 0.96 short)': sy.weights(n, m, wl, ws),
         'NB3 fixed cell (2.0/1.0, NQ2% + MC3 15bp, cut 0.25)': sy.weights(n, m, 2.0, 1.0, scale=sy.cell_scale(2, 15)),
         'FROZEN (1.91/0.96, 9-cell ensemble cut)': sy.weights(n, m, wl, ws, scale=ens),
         'Short leg alone (0.96)': sy.weights(n, m, 0.0, ws, long_on=False),
         'Long leg alone (1.91, ensemble cut)': sy.weights(n, m, wl, 0.0, scale=ens, short_on=False)}
    V['Buy and hold futures (1x)'].iloc[0] = 0.0
    NET = {k: sy.backtest(v)[0] for k, v in V.items()}
    wins = [('FULL PRE-2017 2008-03..2017-03', PRE), ('2008-03..2011-12', ('2008-03-03', '2011-12-31')), ('2012-01..2017-03', ('2012-01-02', '2017-03-31')), ('DEV 2017-04..2023-12 (fidelity check)', DEV)]
    for wn, (a, z) in wins:
        P(f'\n## {wn}  (CAGR incl. 6% interest / MaxDD / Sharpe on futures P&L, floor costs)\n'); P('| System | CAGR / MaxDD / Sharpe | CAGR / MaxDD / Sharpe without interest |'); P('|---|---|---|')
        for k, net in NET.items():
            ex = net[a:z]; m2 = metrics_from(ex, None, None, None, ex); P(f"| {k} | {fl(met(sy, net, a, z))} | {fl(m2)} |")
    # years
    P('\n## Calendar-year total return, pre-2017 (incl. interest)\n'); P('| Year | ' + ' | '.join(['Plain long-only', 'Buy&hold', 'No cuts', 'NB3 fixed', 'FROZEN', 'Short leg alone']) + ' |'); P('|---|' + '---|' * 6)
    ks = list(NET)[:6]; yrs = {k: (NET[k][PRE[0]:PRE[1]] + sy.INT[PRE[0]:PRE[1]]).groupby(NET[k][PRE[0]:PRE[1]].index.year).apply(lambda x: (1 + x).prod() - 1) for k in ks}
    for y in sorted(yrs[ks[0]].index): P(f"| {y} | " + ' | '.join(f"{yrs[k][y]:.1%}" for k in ks) + ' |')
    # ---- criteria
    a, z = PRE; mm = {k: met(sy, NET[k], a, z) for k in NET}; ex_ = lambda k, aa, zz: metrics_from(NET[k][aa:zz], None, None, None, NET[k][aa:zz])
    fk, bk = 'FROZEN (1.91/0.96, 9-cell ensemble cut)', 'Plain long-only (proxy baseline)'
    sub = [('2008-03-03', '2011-12-31'), ('2012-01-02', '2017-03-31')]
    E1a = mm[fk]['Sharpe'] > mm[bk]['Sharpe']; E1b = all(ex_(fk, *s)['Sharpe'] > ex_(bk, *s)['Sharpe'] for s in sub)
    E2 = mm[fk]['Sharpe'] > mm['Buy and hold futures (1x)']['Sharpe']
    nk = 'Same weights, no cuts (1.91 long / 0.96 short)'; E3 = mm[fk]['Sharpe'] > mm[nk]['Sharpe'] and mm[fk]['MaxDD'] >= mm[nk]['MaxDD']
    E4 = mm['Short leg alone (0.96)']['Sharpe'] > 0
    R1 = mm[fk]['MaxDD'] > -0.15; R2 = yrs[fk].min() > -0.10
    P('\n## Pass criteria (written before the run)\n'); P('| Criterion | Result | Detail |'); P('|---|---|---|')
    P(f"| E1 frozen Sharpe > plain long-only, full and both sub-periods | {'PASS' if (E1a and E1b) else ('PASS full, regime-dependent' if E1a else 'FAIL')} | full {mm[fk]['Sharpe']:.2f} vs {mm[bk]['Sharpe']:.2f}; 2008-11 {ex_(fk, *sub[0])['Sharpe']:.2f} vs {ex_(bk, *sub[0])['Sharpe']:.2f}; 2012-17 {ex_(fk, *sub[1])['Sharpe']:.2f} vs {ex_(bk, *sub[1])['Sharpe']:.2f} |")
    P(f"| E2 frozen Sharpe > buy and hold futures | {'PASS' if E2 else 'FAIL'} | {mm[fk]['Sharpe']:.2f} vs {mm['Buy and hold futures (1x)']['Sharpe']:.2f} |")
    P(f"| E3 cuts add value (Sharpe up, MaxDD not worse than same weights without cuts) | {'PASS' if E3 else 'FAIL'} | Sharpe {mm[fk]['Sharpe']:.2f} vs {mm[nk]['Sharpe']:.2f}; MaxDD {mm[fk]['MaxDD']:.1%} vs {mm[nk]['MaxDD']:.1%} |")
    P(f"| E4 short leg alone has positive excess Sharpe | {'PASS' if E4 else 'FAIL'} | {mm['Short leg alone (0.96)']['Sharpe']:.2f} |")
    P(f"| R1 max drawdown better than -15% (risk) | {'PASS' if R1 else 'FAIL'} | {mm[fk]['MaxDD']:.1%} |"); P(f"| R2 no calendar year worse than -10% (risk) | {'PASS' if R2 else 'FAIL'} | worst {yrs[fk].min():.1%} ({yrs[fk].idxmin()}) |")
    n_ok = sum([bool(E1a and E1b), bool(E2), bool(E3), bool(E4)])
    P(f"\n**Verdict: {'SUPPORTS' if n_ok == 4 else ('PARTIAL' if n_ok >= 2 else 'DOES NOT SUPPORT')}** ({n_ok} of 4 edge criteria hold).")
    open(f'{RES}/PRE2017_REPORT.md', 'w').write('\n'.join(rep))
if __name__ == '__main__': main()
