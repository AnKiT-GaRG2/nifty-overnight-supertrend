"""Fast vectorised evaluator for Supertrend(14,3) with per-day factor gates on the DAY leg (09:15..15:00 bars) and NIGHT leg (15:15 bar).
Matches btlib.pnl() accounting: fill at next bar open, 0.025%/side, 0.05% roll, carry 4.7% by calendar time."""
import numpy as np, pandas as pd
from btlib import load_15m, daily_from, adx, rsi, supertrend, DATA, COST_SIDE, COST_ROLL, CARRY_PA

class Ctx:
    def __init__(self, end='2026-10-31'):
        b = load_15m(); b = b[b.index < end]; self.b = b
        self.hm = b.index.strftime('%H:%M').values
        self.night_bar = self.hm == '15:15'
        o = b['open'].values; self.ret_oo = np.r_[o[1:] / o[:-1] - 1, 0.0]
        ix = b.index.to_series(); self.dt_days = ((ix.shift(-1) - ix).dt.total_seconds() / 86400.0).fillna(0.0).values
        dates = b['date']; lastday = dates.groupby(dates.dt.to_period('M')).transform('max')
        self.is_roll = ((dates == lastday) & (self.hm == '15:15')).values
        self.days = pd.DatetimeIndex(sorted(b['date'].unique()))
        codes = pd.Series(np.arange(len(self.days)), index=self.days)
        self.day_id = codes.reindex(b['date']).values
        self.starts = np.r_[0, np.flatnonzero(np.diff(self.day_id)) + 1]
        st = supertrend(b, 14, 3.0); self.green = (st['dir'].values == 1)
        self.line = st['line'].values; self.close = b['close'].values
        self.green_prev = np.r_[False, self.green[:-1]]            # decision from the previous bar close
        self.d = daily_from(b)
        self.carry = CARRY_PA / 365.0 * self.dt_days

    def periods(self):
        P = {'train': ('2017-04-01', '2021-12-31'), 'valid': ('2022-01-01', '2023-12-31'), 'test': ('2024-01-01', '2026-12-31'),
             'full': ('2017-04-01', '2026-12-31'), 'pre24': ('2017-04-01', '2023-12-31')}
        return {k: (np.searchsorted(self.days, pd.Timestamp(s)), np.searchsorted(self.days, pd.Timestamp(e), side='right')) for k, (s, e) in P.items()}

    def held(self, night_gate, day_gate, size=None):
        g = np.where(self.night_bar, night_gate[self.day_id], day_gate[self.day_id]).astype(float)
        h = self.green_prev * g
        if size is not None: h = h * size[self.day_id]
        return h

    def daily_returns(self, held):
        prev = np.r_[0.0, held[:-1]]
        cost = np.abs(held - prev) * COST_SIDE + np.abs(held) * COST_ROLL * self.is_roll
        net = held * self.ret_oo + held * self.carry - cost
        return np.expm1(np.add.reduceat(np.log1p(net), self.starts)), net

def metrics(r, lo, hi, days):
    x = r[lo:hi]
    if len(x) < 30: return None
    eq = np.cumprod(1 + x); yrs = (days[hi - 1] - days[lo]).days / 365.25
    cagr = (eq[-1] ** (1 / yrs) - 1) * 100; dd = (eq / np.maximum.accumulate(eq) - 1).min() * 100
    sh = x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
    return {'CAGR': cagr, 'DD': dd, 'Sharpe': sh, 'J': cagr - abs(dd)}
