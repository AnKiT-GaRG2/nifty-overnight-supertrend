"""Brief-protocol checks for the overnight Supertrend + VIX filter: post-2022 results, yearly walk-forward over a small
Supertrend grid, and a loss-capped (sized) version. Spot data, fills at next bar open."""
import sys; sys.path.insert(0, 'scripts')
from fast import *
from btlib import supertrend
c = Ctx(); days = c.days; n = len(days); hm = c.hm
vix = pd.read_csv(f'{DATA}/vix.csv', parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()
ok = ((vix.shift(1) / vix.shift(2) - 1).values * 100) <= 8.0
A, N = np.ones(n, bool), np.zeros(n, bool)
def sp(a, b): return np.searchsorted(days, pd.Timestamp(a)), np.searchsorted(days, pd.Timestamp(b), side='right')
def M(r, a, b): return metrics(r, *sp(a, b), days)
def fmt(m): return f'{m["CAGR"]:5.1f}% / {m["DD"]:6.1f}% / {m["Sharpe"]:4.2f}'
def rets(nn, mm, kind, size=None):
    c.green_prev = np.r_[False, supertrend(c.b, nn, mm)['dir'].values[:-1] == 1]
    return c.daily_returns(c.held(ok, N, size) if kind == 'strat' else c.held(A, A))[0]
S, B = rets(14, 3.0, 'strat'), rets(14, 3.0, 'base')
print('CAGR / MaxDD / Sharpe        STRATEGY (overnight ST + VIX)      BASELINE (plain Supertrend, same engine)')
for lab, (a, b) in {'2022-Oct 2026 (post-2022)': ('2022-01-01', '2026-12-31'), '2023-Oct 2026': ('2023-01-01', '2026-12-31'), '2024-Oct 2026 (test)': ('2024-01-01', '2026-12-31'), 'Full Apr 2017-Oct 2026': ('2017-04-01', '2026-12-31')}.items():
    print(f'{lab:28s} {fmt(M(S, a, b)):34s} {fmt(M(B, a, b))}')
# ---- walk-forward: each year pick (period, multiplier) from a 9-cell grid by trailing-3-year Sharpe
grid = [(a, b) for a in [10, 14, 20] for b in [2.5, 3.0, 3.5]]
RS = {g: rets(g[0], g[1], 'strat') for g in grid}; RB = {g: rets(g[0], g[1], 'base') for g in grid}
def wf(R):
    parts, picks = [], []
    for Y in range(2020, 2027):
        lo, hi = sp(f'{Y-3}-01-01', f'{Y-1}-12-31'); best = max(grid, key=lambda g: metrics(R[g], lo, hi, days)['Sharpe'])
        a, b = sp(f'{Y}-01-01', f'{Y}-12-31'); parts.append(R[best][a:b]); picks.append((Y, best))
    x = np.concatenate(parts); d = np.concatenate([days[sp(f'{Y}-01-01', f'{Y}-12-31')[0]:sp(f'{Y}-01-01', f'{Y}-12-31')[1]] for Y in range(2020, 2027)])
    eq = np.cumprod(1 + x); yrs = (d[-1] - d[0]).astype('timedelta64[D]').astype(int) / 365.25
    return (eq[-1] ** (1 / yrs) - 1) * 100, (eq / np.maximum.accumulate(eq) - 1).min() * 100, x.mean() / x.std() * np.sqrt(252), picks
ws, wb = wf(RS), wf(RB)
print(f'\nWALK-FORWARD 2020-26 (yearly re-pick from 9-cell grid): strategy {ws[0]:.1f}% / {ws[1]:.1f}% / {ws[2]:.2f}   baseline {wb[0]:.1f}% / {wb[1]:.1f}% / {wb[2]:.2f}')
print('picks:', ws[3])
# ---- loss-capped version (brief: max loss per trade 0.5-1% of capital)
d_ = c.d; cl = d_['close']; tr = pd.concat([d_.high - d_.low, (d_.high - cl.shift()).abs(), (d_.low - cl.shift()).abs()], axis=1).max(axis=1)
atrp = (tr.ewm(alpha=1 / 14, adjust=False).mean() / cl * 100).shift(1).reindex(days).fillna(1.0).values
print('\nLOSS-CAPPED version: size = min(1, r / (k x ATR%))  -> worst single night, nights losing > cap, results')
c.green_prev = np.r_[False, supertrend(c.b, 14, 3.0)['dir'].values[:-1] == 1]
for r_, k in [(1.0, 2.0), (1.0, 3.0), (0.75, 2.0)]:
    sz = np.minimum(1.0, r_ / (k * atrp)); h = c.held(ok, N, sz); rr = c.daily_returns(h)[0]
    nn = (h > 0) & (hm == '15:15'); g = (h * c.ret_oo)[nn] * 100
    print(f'cap r={r_}% k={k}: worst night {g.min():5.2f}%, nights < -{r_}%: {(g < -r_).sum():3d} | full {fmt(M(rr, "2017-04-01", "2026-12-31"))} | post-2022 {fmt(M(rr, "2022-01-01", "2026-12-31"))}')
