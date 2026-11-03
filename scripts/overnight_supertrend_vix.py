"""Overnight Supertrend + VIX panic filter (standalone).

Rules
  1. Supertrend(14, 3) on 15-minute Nifty spot bars.
  2. At the close of the 15:00 bar: if Supertrend is green AND India VIX did not rise more than 8% on the previous day,
     buy at the 15:15 bar open (full 1x size).
  3. Sell at the next session's 09:15 open. No intraday exposure, no shorts.
Accounting: 0.025% per side, 0.05% per roll (month-end night), carry 4.7% p.a. credited by calendar time held (as in the brief).

Data: 1-minute Nifty spot CSVs in data/intraday/ (python3 scripts/dl_intraday.py), India VIX daily closes in data/vix.csv
(downloaded from Yahoo ^INDIAVIX if missing). Run from the repo root:  python3 scripts/overnight_supertrend_vix.py
NOTE: spot-index fills at the 09:15 open are not tradable; on real NSE futures prices this edge largely disappears (see README).
"""
import glob, os
import numpy as np, pandas as pd

DATA = os.environ.get('NIFTY_DATA_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))
ST_N, ST_M, VIX_JUMP_PCT = 14, 3.0, 8.0
COST_SIDE, COST_ROLL, CARRY_PA = 0.00025, 0.0005, 0.047


def load_15m():
    files = sorted(glob.glob(os.path.join(DATA, 'intraday', 'NIFTY50_1min_*.csv')))
    df = pd.concat([pd.read_csv(f, usecols=['Timestamp', 'Open', 'High', 'Low', 'Close']) for f in files])
    df['ts'] = pd.to_datetime(df['Timestamp']); df = df.drop(columns='Timestamp').set_index('ts').sort_index()
    df = df[~df.index.duplicated()].between_time('09:15', '15:29')
    b = df.resample('15min', origin='start_day', offset='9h15min').agg(
        {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    b.columns = ['open', 'high', 'low', 'close']
    b['date'] = b.index.normalize()
    return b


def supertrend(b, n=14, m=3.0):
    """Returns +1 (green) / -1 (red) per bar; 0 during the warm-up."""
    h, l, c = b['high'].values, b['low'].values, b['close'].values
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    atr = pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().values        # Wilder ATR
    hl2 = (h + l) / 2; ub = hl2 + m * atr; lb = hl2 - m * atr
    fu, fl = ub.copy(), lb.copy(); d = np.ones(len(c), dtype=np.int8)
    for i in range(1, len(c)):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if d[i - 1] == -1 and c[i] > fu[i - 1]: d[i] = 1
        elif d[i - 1] == 1 and c[i] < fl[i - 1]: d[i] = -1
        else: d[i] = d[i - 1]
    d[:n * 3] = 0
    return d


def load_vix(days):
    path = os.path.join(DATA, 'vix.csv')
    if not os.path.exists(path):
        import requests
        j = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/%5EINDIAVIX',
                         params={'period1': 1475280000, 'period2': 1793000000, 'interval': '1d'},
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=30).json()['chart']['result'][0]
        pd.DataFrame({'date': pd.to_datetime(j['timestamp'], unit='s').normalize(),
                      'close': j['indicators']['quote'][0]['close']}).dropna().to_csv(path, index=False)
    return pd.read_csv(path, parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()


def backtest(end='2026-10-31'):
    b = load_15m(); b = b[b.index < end]
    days = pd.DatetimeIndex(sorted(b['date'].unique()))
    hm = b.index.strftime('%H:%M').values
    green_prev = np.r_[False, supertrend(b, ST_N, ST_M)[:-1] == 1]            # decided at the previous bar's close

    vix = load_vix(days)
    vix_jump = (vix.shift(1) / vix.shift(2) - 1).values * 100                  # previous day's VIX change (%)
    day_ok = vix_jump <= VIX_JUMP_PCT                                         # skip tonight after a panic day (no VIX data -> skip)
    day_id = pd.Series(np.arange(len(days)), index=days).reindex(b['date']).values

    night_bar = hm == '15:15'                                                  # the bar that is held overnight
    held = (green_prev & night_bar & day_ok[day_id]).astype(float)             # 1.0 on the 15:15 bar of a "go" night

    o = b['open'].values
    ret = np.r_[o[1:] / o[:-1] - 1, 0.0]                                       # open[t] -> open[t+1] (15:15 open -> next 09:15 open)
    ix = b.index.to_series()
    cal_days = ((ix.shift(-1) - ix).dt.total_seconds() / 86400.0).fillna(0.0).values
    last_td = b['date'].groupby(b['date'].dt.to_period('M')).transform('max')
    is_roll = ((b['date'] == last_td).values) & night_bar                      # position carried over the month-end roll

    prev = np.r_[0.0, held[:-1]]
    cost = np.abs(held - prev) * COST_SIDE + np.abs(held) * COST_ROLL * is_roll
    net = held * ret + held * CARRY_PA / 365.0 * cal_days - cost
    start = np.flatnonzero(np.r_[True, np.diff(day_id) != 0])
    daily = pd.Series(np.expm1(np.add.reduceat(np.log1p(net), start)), index=days)
    return daily, held, b


def stats(r):
    eq = (1 + r).cumprod(); yrs = (r.index[-1] - r.index[0]).days / 365.25
    return (eq.iloc[-1] ** (1 / yrs) - 1) * 100, (eq / eq.cummax() - 1).min() * 100, r.mean() / r.std() * np.sqrt(252)


if __name__ == '__main__':
    r, held, b = backtest()
    print('Overnight Supertrend(14,3) + VIX panic filter   CAGR% / MaxDD% / Sharpe')
    for name, (a, z) in {'2017-21 (train)': ('2017-04-01', '2021-12-31'), '2022-23 (valid)': ('2022-01-01', '2023-12-31'),
                         '2024-26 (test)': ('2024-01-01', '2026-12-31'), 'FULL 2017-26': ('2017-04-01', '2026-12-31')}.items():
        c, d, s = stats(r[a:z]); print(f'{name:18s} {c:6.1f} / {d:6.1f} / {s:5.2f}')
    print(f'nights held: {int((held > 0).sum())}')
