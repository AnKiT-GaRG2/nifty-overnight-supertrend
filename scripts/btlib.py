"""Backtest library: Nifty futures on 15-min bars (spot series + carry), no lookahead.
Position unit: fraction of capital in notional (1.0 = full 1x = ~12 lots today). Range [-1, 1].
Signal computed at the CLOSE of bar t, filled at the OPEN of bar t+1.
Return of position decided at bar t = open[t+2]/open[t+1]-1 (held open-to-open), plus carry.
"""
import glob, os, pickle
import numpy as np, pandas as pd

DATA = os.environ.get('NIFTY_DATA_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))
COST_SIDE = 0.00025      # 0.025% per side
COST_ROLL = 0.0005       # 0.05% per roll (charged on last trading day of each month if in a position)
CARRY_PA = 0.047         # 6% - 1.3%; earned by longs, paid by shorts
BARS_PER_DAY = 25

def load_15m():
    cache = f'{DATA}/bars15.pkl'
    if os.path.exists(cache):
        return pickle.load(open(cache, 'rb'))
    fs = sorted(glob.glob(f'{DATA}/intraday/NIFTY50_1min_*.csv'))
    df = pd.concat([pd.read_csv(f, usecols=['Timestamp', 'Open', 'High', 'Low', 'Close']) for f in fs])
    df['ts'] = pd.to_datetime(df['Timestamp']); df = df.drop(columns='Timestamp').set_index('ts').sort_index()
    df = df[~df.index.duplicated()]
    df = df.between_time('09:15', '15:29')          # drop muhurat evening sessions
    b = df.resample('15min', origin='start_day', offset='9h15min').agg(
        {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    b.columns = ['open', 'high', 'low', 'close']
    b['date'] = b.index.normalize()
    pickle.dump(b, open(cache, 'wb'))
    return b

def daily_from(b):
    g = b.groupby('date')
    d = pd.DataFrame({'open': g['open'].first(), 'high': g['high'].max(), 'low': g['low'].min(), 'close': g['close'].last()})
    return d

def adx(d, n=14):
    h, l, c = d['high'].values, d['low'].values, d['close'].values
    up = np.r_[0, h[1:] - h[:-1]]; dn = np.r_[0, l[:-1] - l[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.maximum.reduce([h - l, np.abs(h - np.r_[c[0], c[:-1]]), np.abs(l - np.r_[c[0], c[:-1]])])
    a = 1.0 / n
    rma = lambda x: pd.Series(x).ewm(alpha=a, adjust=False).mean().values
    atr = rma(tr); pdi = 100 * rma(pdm) / atr; mdi = 100 * rma(mdm) / atr
    dx = 100 * np.abs(pdi - mdi) / (pdi + mdi + 1e-12)
    return pd.Series(rma(dx), index=d.index)

def rsi(close, n=2):
    dlt = close.diff(); up = dlt.clip(lower=0); dn = (-dlt).clip(lower=0)
    ru = up.ewm(alpha=1 / n, adjust=False).mean(); rd = dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + ru / (rd + 1e-12))

def supertrend(b, n=14, m=3.0):
    h, l, c = b['high'].values, b['low'].values, b['close'].values
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    atr = pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().values
    hl2 = (h + l) / 2; ub = hl2 + m * atr; lb = hl2 - m * atr
    N = len(c); fu = ub.copy(); fl = lb.copy(); dirn = np.ones(N, dtype=np.int8); line = np.zeros(N)
    for i in range(1, N):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if dirn[i - 1] == -1 and c[i] > fu[i - 1]: dirn[i] = 1
        elif dirn[i - 1] == 1 and c[i] < fl[i - 1]: dirn[i] = -1
        else: dirn[i] = dirn[i - 1]
    line = np.where(dirn == 1, fl, fu)
    warm = n * 3
    dirn[:warm] = 0
    return pd.DataFrame({'dir': dirn, 'line': line}, index=b.index)

def state_machine(want, dist, risk, cap=1.0):
    """want: desired side per bar (+1/-1/0) decided at bar close. Position changes only when side changes;
    size set at entry = min(cap, risk/dist) (risk=None -> cap). Returns position decided at each bar close."""
    N = len(want); pos = np.zeros(N); side = 0; size = 0.0
    for i in range(N):
        w = want[i]
        if w != side:
            side = w
            size = 0.0 if w == 0 else (cap if risk is None else min(cap, risk / max(dist[i], 1e-4)))
        pos[i] = side * size
    return pos

def pnl(b, pos):
    """pos[t] decided at close of bar t, filled at open[t+1], held to open[t+2]. Returns per-bar net return series
    indexed by the bar whose open starts the holding interval (t+1)."""
    o = b['open'].values; N = len(o)
    p = pd.Series(pos, index=b.index)
    held = p.shift(1).fillna(0.0)                         # position held during bar t (decided at t-1 close, filled at open t)
    ret_oo = pd.Series(np.r_[o[1:] / o[:-1] - 1, 0.0], index=b.index)   # open[t] -> open[t+1]
    gross = held * ret_oo
    ix = b.index.to_series()
    dt_days = ((ix.shift(-1) - ix).dt.total_seconds() / 86400.0).fillna(0.0)    # calendar time to next bar open
    carry = held * CARRY_PA / 365.0 * dt_days
    prev = held.shift(1).fillna(0.0)
    cost = (held - prev).abs() * COST_SIDE                # trades happen at open of bar t
    # roll: last bar of last trading day of month, if in position
    dates = b['date']; lastday = dates.groupby(dates.dt.to_period('M')).transform('max')
    is_roll = (dates == lastday) & (ix.dt.strftime('%H:%M') == '15:15')   # position carried into the roll night
    cost = cost + held.abs() * COST_ROLL * is_roll
    net = gross + carry - cost
    return net, held

def metrics(net, held=None, label=''):
    d = (1 + net).groupby(net.index.normalize()).prod() - 1      # daily returns
    d = d[d.index.dayofweek < 7]
    eq = (1 + d).cumprod()
    yrs = (d.index[-1] - d.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else np.nan
    dd = (eq / eq.cummax() - 1).min()
    sh = d.mean() / d.std() * np.sqrt(252) if d.std() > 0 else np.nan
    out = {'CAGR%': cagr * 100, 'MaxDD%': dd * 100, 'Sharpe': sh}
    if held is not None:
        h = held.loc[net.index]
        trades = (h.diff().abs() > 1e-9).sum() / 2.0      # entries+exits ≈ 2 changes per round trip
        out['trades/yr'] = trades / yrs
        out['avg|pos|'] = h.abs().mean()
    return out

PERIODS = {'train 17-21': ('2017-04-01', '2021-12-31'), 'valid 22-23': ('2022-01-01', '2023-12-31'),
           'test 24-26': ('2024-01-01', '2026-12-31')}

def report(net, held, which=('train 17-21', 'valid 22-23')):
    rows = {}
    for k in which:
        s, e = PERIODS[k]
        n = net.loc[s:e]
        if len(n) < 100: continue
        rows[k] = metrics(n, held, k)
    return pd.DataFrame(rows).T.round(2)
