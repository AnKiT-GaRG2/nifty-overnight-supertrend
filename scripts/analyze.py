import json, sys
import numpy as np, pandas as pd

D = sys.argv[1]          # data dir
R = sys.argv[2]          # results dir
pd.set_option('display.width', 220); pd.set_option('display.max_columns', 30)

def load(n):
    df = pd.read_csv(f'{D}/{n}.csv', parse_dates=['date']).set_index('date')
    return df['close']

px = {n: load(n) for n in ['nifty','vix','brent','usdinr','spx','nasdaq','us10y','dxy','gold']}
START, END = pd.Timestamp('2016-10-03'), pd.Timestamp('2026-10-30')
px = {k: v[(v.index >= START) & (v.index <= END)] for k, v in px.items()}

# factor "moves": pct change, except US10Y (percentage-point change)
mv = {k: (v.diff() if k == 'us10y' else v.pct_change() * 100) for k, v in px.items()}
nifty = mv['nifty'].dropna().rename('nifty')
fac = [k for k in px if k != 'nifty']

def align(name, mode):
    """same: factor move on the same calendar date as the Nifty bar.
       prev: most recent factor move on a date strictly BEFORE the Nifty date
             (= information already known before Nifty opens; US sessions end after Nifty closes)."""
    f = mv[name].dropna().rename(name).reset_index()
    n = nifty.reset_index()
    if mode == 'same':
        out = n.merge(f, on='date', how='inner')
    else:
        out = pd.merge_asof(n, f, on='date', direction='backward', allow_exact_matches=False)
    return out.dropna().set_index('date')

periods = {'2017-21': ('2016-10-01', '2021-12-31'), '2022-23': ('2022-01-01', '2023-12-31'), '2024-26': ('2024-01-01', '2026-12-31')}

# ---------------- 1. correlations ----------------
rows = []
for f in fac:
    r = {'factor': f}
    for mode in ['same', 'prev']:
        a = align(f, mode)
        r[f'{mode}_all'] = a['nifty'].corr(a[f])
        for p, (s, e) in periods.items():
            b = a.loc[s:e]
            r[f'{mode}_{p}'] = b['nifty'].corr(b[f])
    rows.append(r)
corr = pd.DataFrame(rows).set_index('factor').round(2)
print('\n=== 1. DAILY CORRELATION: Nifty daily return vs factor move ===')
print('same = same calendar day | prev = factor move known BEFORE Nifty opens (tradable)')
print(corr.to_string())
corr.to_csv(f'{R}/corr_daily.csv')

# ---------------- 2. event rules (thresholds fixed in advance) ----------------
rules = [  # name, mode, direction, threshold, label
    ('brent',  'prev', 'up',   3.0,  'Brent crude rises >= 3%'),
    ('brent',  'prev', 'down', -3.0, 'Brent crude falls >= 3%'),
    ('usdinr', 'prev', 'up',   0.5,  'Rupee weakens (USDINR) >= 0.5%'),
    ('usdinr', 'prev', 'down', -0.5, 'Rupee strengthens >= 0.5%'),
    ('spx',    'prev', 'up',   1.0,  'S&P 500 rises >= 1%'),
    ('spx',    'prev', 'down', -1.0, 'S&P 500 falls >= 1%'),
    ('nasdaq', 'prev', 'down', -1.5, 'Nasdaq falls >= 1.5%'),
    ('us10y',  'prev', 'up',   0.08, 'US 10Y yield rises >= 8bp'),
    ('us10y',  'prev', 'down', -0.08, 'US 10Y yield falls >= 8bp'),
    ('dxy',    'prev', 'up',   0.7,  'Dollar index rises >= 0.7%'),
    ('dxy',    'prev', 'down', -0.7, 'Dollar index falls >= 0.7%'),
    ('gold',   'prev', 'down', -1.5, 'Gold falls >= 1.5%'),
    ('gold',   'prev', 'up',   1.5,  'Gold rises >= 1.5%'),
    ('vix',    'prev', 'up',   8.0,  'India VIX rises >= 8% (prev day)'),
    ('vix',    'prev', 'down', -8.0, 'India VIX falls >= 8% (prev day)'),
    ('vix',    'same', 'up',   8.0,  'India VIX rises >= 8% (same day, coincident)'),
    ('brent',  'same', 'up',   3.0,  'Brent rises >= 3% (same day)'),
]
rows = []
for f, mode, d, th, lab in rules:
    a = align(f, mode)
    base = a['nifty'].mean(); sd = a['nifty'].std()
    m = a[f] >= th if d == 'up' else a[f] <= th
    e = a.loc[m, 'nifty']
    n = len(e)
    tstat = (e.mean() - base) / (sd / np.sqrt(n)) if n > 1 else np.nan
    signs = []
    for p, (s, en) in periods.items():
        ee = e.loc[s:en]
        signs.append(np.sign(ee.mean() - a.loc[s:en, 'nifty'].mean()) if len(ee) >= 5 else 0)
    rows.append({'rule': lab, 'n_days': n, 'avg_nifty_%': round(e.mean(), 3), 'all_days_avg_%': round(base, 3),
                 'edge_%': round(e.mean() - base, 3), 'nifty_down_%days': round((e < 0).mean() * 100, 1),
                 't_stat': round(tstat, 2), 'edge_sign_by_period(17-21,22-23,24-26)': ''.join({1: '+', -1: '-', 0: '?'}[int(s)] for s in signs)})
ev = pd.DataFrame(rows)
print('\n=== 2. EVENT RULES: what did Nifty do the next session? (edge = event avg minus all-days avg) ===')
print(ev.to_string(index=False))
ev.to_csv(f'{R}/event_rules.csv', index=False)

# ---------------- 3. joint regression (daily, tradable lags only) ----------------
cols = ['spx', 'dxy', 'us10y', 'brent', 'gold', 'usdinr', 'vix']
X = None
for f in cols:
    a = align(f, 'prev')[[f]]
    X = a if X is None else X.join(a, how='inner')
X = X.join(nifty, how='inner').dropna()
def ols(X, cols, y='nifty'):
    Z = X[cols]; Zs = (Z - Z.mean()) / Z.std()
    A = np.column_stack([np.ones(len(Zs)), Zs.values]); yy = X[y].values
    b = np.linalg.lstsq(A, yy, rcond=None)[0]; e = yy - A @ b
    XtXi = np.linalg.inv(A.T @ A); n, k = A.shape
    cov = XtXi @ (A.T * e**2) @ A @ XtXi * n / (n - k)
    t = b / np.sqrt(np.diag(cov)); r2 = 1 - e.var() / yy.var()
    return pd.DataFrame({'beta_%_per_1sd': b[1:].round(3), 't_stat': t[1:].round(2)}, index=cols), r2
print('\n=== 3. JOINT REGRESSION: Nifty daily % return on factors known before the open ===')
for p, (s, e) in [('all', ('2016-10-01', '2026-12-31'))] + list(periods.items()):
    res, r2 = ols(X.loc[s:e], cols)
    print(f'-- {p}  (n={len(X.loc[s:e])}, R2={r2:.3f})'); print(res.T.to_string())

# ---------------- 4. monthly: factors incl. FPI flow ----------------
m_px = {k: v.resample('ME').last() for k, v in px.items()}
mm = pd.DataFrame({k: (v.diff() if k == 'us10y' else v.pct_change() * 100) for k, v in m_px.items()}).dropna()
y = json.load(open(f'{D}/fii/fpi_yearly_monthly.json'))['years']
mon = ['January','February','March','April','May','June','July','August','September','October','November','December']
fl = {}
for yr in range(2016, 2027):
    for m in y[str(yr)]['months']:
        if m['month'] in mon:
            fl[pd.Timestamp(yr, mon.index(m['month']) + 1, 1) + pd.offsets.MonthEnd(0)] = m['equity']
fii = pd.Series(fl).sort_index().rename('fpi_flow_cr')
mm = mm.join(fii, how='left')
mm['fpi_prev'] = mm['fpi_flow_cr'].shift(1)
mm = mm.loc['2016-11-30':'2026-03-31']
mc = mm.drop(columns=['fpi_prev']).corr()['nifty'].drop('nifty').round(2)
print('\n=== 4a. MONTHLY correlation with Nifty monthly return (same month) ===')
print(mc.to_string())
print('FPI flow of previous month vs Nifty this month:', round(mm['nifty'].corr(mm['fpi_prev']), 2))

print('\n=== 4b. MONTHLY FPI FLOW BUCKETS (Rs crore) -> Nifty same month and next month ===')
mm['nifty_next'] = mm['nifty'].shift(-1)
bins = [-1e9, -30000, -10000, 0, 10000, 30000, 1e9]
labs = ['< -30,000', '-30,000 to -10,000', '-10,000 to 0', '0 to 10,000', '10,000 to 30,000', '> 30,000']
mm['bucket'] = pd.cut(mm['fpi_flow_cr'], bins=bins, labels=labs)
g = mm.groupby('bucket', observed=True).agg(months=('nifty', 'size'), nifty_same_month_avg=('nifty', 'mean'),
        pct_months_up=('nifty', lambda s: (s > 0).mean() * 100), nifty_next_month_avg=('nifty_next', 'mean')).round(2)
print(g.to_string())
g.to_csv(f'{R}/fpi_buckets.csv')
by_p = []
for p, (s, e) in periods.items():
    b = mm.loc[s:e]; by_p.append((p, len(b), round(b['nifty'].corr(b['fpi_flow_cr']), 2)))
print('FPI flow vs same-month Nifty corr by period:', by_p)

print('\n=== 4c. MONTHLY brent buckets -> Nifty same month ===')
mm['brent_b'] = pd.cut(mm['brent'], [-100, -10, -3, 3, 10, 200], labels=['< -10%', '-10 to -3%', '-3 to +3%', '+3 to +10%', '> +10%'])
print(mm.groupby('brent_b', observed=True)['nifty'].agg(['size', 'mean', lambda s: (s > 0).mean() * 100]).round(2).rename(columns={'<lambda_0>': 'pct_up'}).to_string())

# ---------------- 5. yearly picture ----------------
yr = pd.DataFrame({
    'nifty_ret_%': px['nifty'].resample('YE').last().pct_change() * 100,
    'brent_ret_%': px['brent'].resample('YE').last().pct_change() * 100,
    'usdinr_ret_%': px['usdinr'].resample('YE').last().pct_change() * 100,
    'spx_ret_%': px['spx'].resample('YE').last().pct_change() * 100,
    'us10y_end': px['us10y'].resample('YE').last(),
    'vix_avg': px['vix'].resample('YE').mean(),
})
yr['fpi_equity_cr'] = fii.resample('YE').sum()
yr.index = yr.index.year
print('\n=== 5. YEAR BY YEAR (2016 and 2026 partial) ===')
print(yr.round(1).iloc[1:].to_string())
yr.to_csv(f'{R}/yearly.csv')

# extra: biggest Nifty down days and what preceded them
print('\n=== 6. Nifty worst 10 days ===')
w = nifty.nsmallest(10)
print(w.round(2).to_string())
print('\nNifty total:', round(px['nifty'].iloc[0]), '->', round(px['nifty'].iloc[-1]), '| daily n =', len(nifty))
