"""Factor monitor: every flag for Nifty trading day D uses only information dated strictly BEFORE D
(US/FX/commodity closes of earlier dates, Indian closes of D-1, completed months). Thresholds are the ones stated in the
'Nifty 50 What Moves It' document; none were tuned here.
flag=True means CAUTION (doc says Nifty tends to fall / overnight risk is higher)."""
import os
import numpy as np, pandas as pd
DATA = os.environ.get('NIFTY_DATA_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))

def _ld(n):
    return pd.read_csv(f'{DATA}/{n}.csv', parse_dates=['date']).set_index('date')['close'].astype(float)

def _asof(series, days):
    """value of `series` at the latest date strictly before each Nifty day"""
    s = series.dropna().rename('v').rename_axis('date').reset_index()
    t = pd.DataFrame({'date': days})
    return pd.merge_asof(t, s, on='date', allow_exact_matches=False).set_index('date')['v']

def build_flags(days):
    days = pd.DatetimeIndex(sorted(set(days)))
    L = {k: _ld(k) for k in ['usdinr', 'dxy', 'us10y', 'spx', 'brent', 'vix', 'krw', 'twd', 'jpy', 'cny']}
    F = pd.DataFrame(index=days)
    F['rupee_month'] = _asof(L['usdinr'].pct_change(21) * 100, days) > 2.0          # rupee down >2% in a month
    F['rupee_day'] = _asof(L['usdinr'].pct_change() * 100, days) > 0.5              # rupee down >0.5% yesterday
    F['dollar_month'] = _asof(L['dxy'].pct_change(21) * 100, days) > 1.5            # dollar index +1.5% in a month
    F['us10y_month'] = _asof(L['us10y'].diff(21), days) > 0.25                      # US 10Y +25bp in a month
    F['spx_month'] = _asof(L['spx'].pct_change(21) * 100, days) < -2.0              # S&P 500 down >2% in a month
    F['crude_regime'] = _asof(L['brent'].rolling(21).mean(), days) > 100.0          # Brent avg above $100
    F['crude_shock'] = (_asof(L['brent'].pct_change(5) * 100, days) >= 10.0) & (_asof(L['brent'], days) > 90.0)  # war-type spike
    F['vix_jump'] = _asof(L['vix'].pct_change() * 100, days) > 20.0                 # India VIX +20% yesterday
    F['vix_high'] = _asof(L['vix'], days) > 25.0
    F['won_weak'] = _asof(L['krw'].pct_change() * 100, days) > 0.7                  # Korean won -0.7% yesterday
    F['twd_weak'] = _asof(L['twd'].pct_change() * 100, days) > 0.5
    F['yen_jump'] = _asof(L['jpy'].pct_change().abs() * 100, days) > 1.5            # doc: no effect (control)
    F['season_weak'] = pd.Series(days.month.isin([1, 2]), index=days)               # Jan/Feb weak
    F['season_strong'] = pd.Series(days.month.isin([4, 7]), index=days)             # Apr/Jul strong (tailwind, not caution)
    # ---- FII monthly (NSE provisional, Rs cr), month M known from the 1st of M+1; stale after the last full month in file
    fi = pd.read_csv(f'{DATA}/fii2/fii_dii.csv', parse_dates=['trade_date'])
    fi = fi[fi.trade_date < '2026-01-01'].set_index('trade_date')['net_purchase_sales_fii']
    fi.index = fi.index.to_period('M').to_timestamp('M')                           # month-end
    avail = fi.copy(); avail.index = (avail.index + pd.Timedelta(days=1))          # usable from the next day
    m1 = _asof(avail.shift(0), days); F['fii_last_month_sell'] = m1 < -10000        # last month FIIs sold >10,000 cr
    r12 = fi.rolling(12).sum(); r12.index = r12.index + pd.Timedelta(days=1)
    F['fii_12m_sell'] = _asof(r12, days) < -200000                                  # >2 lakh cr sold in 12 months
    # ---- valuation (P/E): known daily; file ends 1 Jul 2026 -> carried forward after
    pe = pd.read_csv(f'{DATA}/fii2/nifty_pe_pb_div.csv'); pe['Date'] = pd.to_datetime(pe['Date'], format='%d %b %Y')
    pe = pe.set_index('Date')['PE'].sort_index()
    p = _asof(pe, days); F['pe_high'] = p > 23.0; F['pe_low'] = p < 21.0
    F['pe_value'] = p
    return F

CAUTION = ['rupee_month', 'dollar_month', 'us10y_month', 'spx_month', 'crude_regime', 'crude_shock', 'fii_12m_sell', 'pe_high']
