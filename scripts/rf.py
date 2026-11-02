"""Real-futures research framework (daily horizon, P&L from actual NSE Nifty futures prices).
A position s[i] in [-1,1] is decided at ~15:00 on day i (information up to the 15:00 bar) and filled at the last-30-minute VWAP.
 mode 'both' : hold close(i) -> close(i+1)   (night leg then day leg of day i+1)
 mode 'night': hold close(i) -> open(i+1)    mode 'day': hold open(i+1) -> close(i+1)
Costs 0.025%/side, 0.05% roll when a position is carried through an expiry close. Returns are real futures price P&L
(basis decay included); optional +6% p.a. interest on capital is reported separately."""
import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import numpy as np, pandas as pd
from btlib import DATA, load_15m, supertrend, daily_from, rsi, adx
COST = 0.00025; ROLL = 0.0005

class RF:
    def __init__(self, end='2026-10-31'):
        b = load_15m(); b = b[b.index < end]; self.b = b
        self.days = pd.DatetimeIndex(sorted(b['date'].unique())); days = self.days; n = self.n = len(days)
        hm = b.index.strftime('%H:%M')
        c1500 = b[hm == '15:00'].groupby('date')['close'].last().reindex(days)        # price known at the 15:15 decision
        self.X = c1500.ffill()
        d = daily_from(b); self.d = d.reindex(days)
        st = supertrend(b, 14, 3.0)['dir']; self.st15 = st[hm == '15:00'].groupby(b.index[hm == '15:00'].normalize()).last().reindex(days).fillna(0).values
        fut = pd.read_csv(os.path.join(DATA, 'fut', 'nifty_fut.csv'), parse_dates=['date', 'expiry']).drop_duplicates(['date', 'expiry'])
        fut = fut[(fut.open > 0) & (fut.close > 0)]; F = fut.set_index(['date', 'expiry']).sort_index()
        rd = np.zeros(n); rn = np.zeros(n); basis = np.full(n, np.nan); dte = np.full(n, np.nan); expday = np.zeros(n, bool)
        oi = np.full(n, np.nan); vol = np.full(n, np.nan)
        grp = fut.groupby('date')
        for i, t in enumerate(days):
            if t in grp.groups:
                g = grp.get_group(t); oi[i] = g.oi.sum(); vol[i] = g.volume.sum()
                ex = g.expiry.values; expday[i] = (ex == np.datetime64(t)).any()
            try:
                exs = F.loc[t].index; Fi = exs[exs >= t][0]; Gi = exs[exs > t][0]
                r = F.loc[(t, Fi)]; rd[i] = r.close / r.open - 1
                basis[i] = F.loc[(t, Gi)].close / self.X.values[i] - 1; dte[i] = (Gi - t).days
                if i + 1 < n: rn[i] = F.loc[(days[i + 1], Gi)].open / F.loc[(t, Gi)].close - 1
            except Exception: pass
        self.rd, self.rn, self.basis, self.dte, self.expday, self.oi, self.vol = rd, rn, basis, dte, expday, oi, vol
        self.cal = np.r_[[(days[i + 1] - days[i]).days for i in range(n - 1)], 1].astype(float)   # calendar days from i to i+1
    def run(self, s, mode='both', interest=False):
        """s[i] decided at 15:00 of day i. Returns daily net returns, attributed to day i+1 (shifted to index i+1)."""
        n = self.n; s = np.nan_to_num(np.asarray(s, float)); r = np.zeros(n)
        nxt = np.r_[s[:-1] * 0, 0.0]
        rn, rd = self.rn[:-1], np.r_[self.rd[1:]]
        if mode == 'both':
            g = (1 + rn) * (1 + self.rd[1:]) - 1
            prev = np.r_[0.0, s[:-2]] if False else s[:-1] * 0
            ret = s[:-1] * g
            chg = np.abs(s[:-1] - np.r_[0.0, s[:-2]])                               # trade at the close of day i
            roll = ROLL * np.minimum(np.abs(s[:-1]), np.abs(s[1:])) * (np.sign(s[:-1]) == np.sign(s[1:])) * self.expday[1:]
            cost = chg * COST + roll
            # exit of the final position isn't charged here (open at end of data)
        elif mode == 'night':
            ret = s[:-1] * rn; cost = 2 * COST * np.abs(s[:-1])
        else:
            ret = s[:-1] * self.rd[1:]; cost = 2 * COST * np.abs(s[:-1])
        r[1:] = ret - cost
        if interest: r[1:] += 0.06 / 365 * self.cal[:-1]
        return r

def periods(days):
    P = {'train': ('2017-04-01', '2021-12-31'), 'valid': ('2022-01-01', '2023-12-31'), 'test': ('2024-01-01', '2026-12-31'), 'full': ('2017-04-01', '2026-12-31')}
    return {k: (np.searchsorted(days, pd.Timestamp(a)), np.searchsorted(days, pd.Timestamp(b), side='right')) for k, (a, b) in P.items()}

def met(r, lo, hi, days):
    x = r[lo:hi]; eq = np.cumprod(1 + x); yrs = (days[hi - 1] - days[lo]).days / 365.25
    cagr = (eq[-1] ** (1 / yrs) - 1) * 100; dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
    return dict(CAGR=cagr, DD=dd, Sharpe=x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0, J=cagr - abs(dd))
