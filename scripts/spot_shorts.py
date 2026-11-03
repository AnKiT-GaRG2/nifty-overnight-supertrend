"""Short-selling test on the SPOT data with the brief's protocol (fill at next bar open, 0.025%/side, 0.05% roll, carry 4.7% p.a.:
longs earn it, shorts pay it). Positions are decided at the 15:00 bar close. Modes: both (continuous), day (09:15->15:15 only), night (15:15->09:15 only)."""
import sys; sys.path.insert(0, 'scripts')
from fast import *
from btlib import supertrend, rsi
c = Ctx(); days = c.days; n = len(days); hm = c.hm; b = c.b
X = b[hm == '15:00'].groupby('date')['close'].last().reindex(days).ffill(); Xv = X.values
sma = {k: X.rolling(k).mean().values for k in (50, 200)}
vix = pd.read_csv(f'{DATA}/vix.csv', parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()
vprev = vix.shift(1).values; ok = ((vix.shift(1) / vix.shift(2) - 1).values * 100) <= 8.0
mom20 = X.pct_change(20).values; low20 = X.rolling(20).min().shift(1).values; r2 = rsi(X, 2).values
stv = supertrend(b, 14, 3.0)['dir'].values; st15 = pd.Series(stv[hm == '15:00'], index=b.index[hm == '15:00'].normalize()).reindex(days).fillna(0).values
shorts = {
 'always short': -np.ones(n),
 'below 200-day': np.where(Xv < sma[200], -1.0, 0), 'below 200-day & VIX>18': np.where((Xv < sma[200]) & (vprev > 18), -1.0, 0),
 'below 200-day & VIX>22': np.where((Xv < sma[200]) & (vprev > 22), -1.0, 0),
 'confirmed downtrend (50d<200d, <50d)': np.where((Xv < sma[50]) & (sma[50] < sma[200]), -1.0, 0),
 '20-day momentum < -3%': np.where(mom20 < -0.03, -1.0, 0), 'breakdown below 20-day low': np.where(Xv < low20, -1.0, 0),
 'Supertrend red': np.where(st15 == -1, -1.0, 0), 'Supertrend red & below 200-day': np.where((st15 == -1) & (Xv < sma[200]), -1.0, 0),
 'sell the bounce (downtrend & RSI2>90)': np.where((Xv < sma[200]) & (r2 > 90), -1.0, 0)}
def held_from(s, mode):
    prev = np.r_[0.0, s[:-1]]; nb = c.night_bar
    if mode == 'both': return np.where(nb, s[c.day_id], prev[c.day_id])
    if mode == 'day': return np.where(nb, 0.0, prev[c.day_id])
    return np.where(nb, s[c.day_id], 0.0)
def sp(a, z): return np.searchsorted(days, pd.Timestamp(a)), np.searchsorted(days, pd.Timestamp(z), side='right')
PER = {'train': ('2017-04-01', '2021-12-31'), 'valid': ('2022-01-01', '2023-12-31'), 'test': ('2024-01-01', '2026-12-31'), 'full': ('2017-04-01', '2026-12-31')}
def fm(r, k): m = metrics(r, *sp(*PER[k]), days); return f'{m["CAGR"]:5.1f}/{m["DD"]:6.1f}/{m["Sharpe"]:5.2f}'
def row(name, r): print(f'{name:48s} ' + ' | '.join(f'{k} {fm(r, k)}' for k in PER))
print('SPOT data, short-only strategies. CAGR/MaxDD/Sharpe')
for mode in ['both', 'day', 'night']:
    print(f'\n-- mode: {mode}')
    for k, s in shorts.items(): row(k, c.daily_returns(held_from(s, mode))[0])
print('\n=== combined with the long strategy (overnight Supertrend + VIX filter): day-only shorts never overlap the overnight long')
c.green_prev = np.r_[False, supertrend(b, 14, 3.0)['dir'].values[:-1] == 1]
long_h = c.held(ok, np.zeros(n, bool)); row('LONG only (overnight ST + VIX)', c.daily_returns(long_h)[0])
for k, s in shorts.items():
    for sc in [1.0, 0.5]:
        row(f'long + day-short [{k[:30]}] x{sc}', c.daily_returns(long_h + sc * held_from(s, 'day'))[0])
base = c.daily_returns(c.held(np.ones(n, bool), np.ones(n, bool)))[0]; row('\nplain Supertrend long-only baseline', base)
