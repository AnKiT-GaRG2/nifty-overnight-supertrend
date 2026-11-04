"""Robustness checks for the factor-permutation winner (rf framework, real futures).
Run from repo root after rf_factor_perm.py."""
import sys, os; sys.path.insert(0, 'scripts')
import warnings; warnings.filterwarnings('ignore')
from rf import *
from factors import _asof
R = RF(); days = R.days; n = R.n; P = periods(days); X = R.X
L = lambda k: pd.read_csv(os.path.join(DATA, f'{k}.csv'), parse_dates=['date']).set_index('date')['close'].astype(float)
A = lambda s: _asof(s, days).values
inr21 = A(L('usdinr').pct_change(21) * 100); us21 = A(L('us10y').diff(21)); vix = L('vix').reindex(days).ffill().shift(1).values
month = np.array(days.month)
def stats(r, tag, extra=''):
    m = {k: met(r, *P[k], days) for k in P}
    print(f"{tag:58s}", ' | '.join(f"{k} {m[k]['CAGR']:5.1f}/{m[k]['DD']:6.1f}/{m[k]['Sharpe']:4.2f}" for k in ['train', 'valid', 'test', 'full']), extra)
def run(sig, mode='both', interest=True, costx=1.0):
    import rf as _rf; c0, r0 = _rf.COST, _rf.ROLL; _rf.COST, _rf.ROLL = c0 * costx, r0 * costx
    try: return R.run(sig, mode, interest)
    finally: _rf.COST, _rf.ROLL = c0, r0
g_inr = inr21 < 2.0; g_us = us21 < 0.25; g_cal = ~np.isin(month, [1, 2])
W = (g_inr & g_us & g_cal).astype(float)
bh = np.ones(n)
print('--- winner vs B&H, total-return (futures P&L + 6% interest on capital) and PURE futures price P&L')
stats(run(bh), 'B&H total'); stats(run(W), 'WINNER total'); stats(run(bh, interest=False), 'B&H pure price'); stats(run(W, interest=False), 'WINNER pure price')
chg = np.abs(np.diff(W)).sum() / 2 / ((days[-1] - days[0]).days / 365.25)
print(f'exposure {W.mean()*100:.0f}% of days in market, round trips/yr {chg:.1f}')
print('\n--- ablation: drop one gate (and each gate alone)')
for name, sig in [('inr+us (no calendar)', g_inr & g_us), ('inr+cal (no us10y)', g_inr & g_cal), ('us+cal (no rupee)', g_us & g_cal), ('rupee only', g_inr), ('us10y only', g_us), ('not Jan/Feb only', g_cal)]: stats(run(sig.astype(float)), name)
print('\n--- neighbouring thresholds (rupee 21d x US10Y 21d change, with not Jan/Feb)')
for a in [1.0, 1.5, 2.0, 3.0]:
    for b in [0.0, 0.15, 0.25, 0.40, 0.60]:
        s = ((inr21 < a) & (us21 < b) & g_cal).astype(float); r = run(s)
        m = {k: met(r, *P[k], days) for k in ['train', 'valid', 'test', 'full']}
        print(f"  rupee<{a:3.1f}% us10y<{b:4.2f}  " + ' | '.join(f"{k} {m[k]['CAGR']:5.1f}/{m[k]['DD']:6.1f}" for k in m))
print('\n--- cost stress'); [stats(run(W, costx=c), f'WINNER costs x{c}') for c in [1, 2, 3]]
print('\n--- legs'); stats(run(W, 'night'), 'WINNER night only'); stats(run(W, 'day'), 'WINNER day only')
print('\n--- calendar leakage check: drop Jan/Feb gate, add 20DMA/VIX guard instead (non-calendar, price/vol based)')
stats(run(((g_inr & g_us) & (vix < 25)).astype(float)), 'inr & us10y & vix<25 (no calendar)')
stats(run(((g_inr & g_us) & (X.values > X.rolling(200).mean().values)).astype(float)), 'inr & us10y & trend200')
print('\n--- ex-2026 test (2024-2025 only) for winner vs B&H')
lo, hi = np.searchsorted(days, pd.Timestamp('2024-01-01')), np.searchsorted(days, pd.Timestamp('2025-12-31'), side='right')
for tag, s in [('B&H', bh), ('WINNER', W)]:
    m = met(run(s), lo, hi, days); print(f"  {tag}: {m['CAGR']:.1f}/{m['DD']:.1f}/{m['Sharpe']:.2f}")
print('\n--- FII data staleness: last date of FII monthly file =', pd.read_csv(os.path.join(DATA, 'fii2', 'fii_dii.csv'), parse_dates=['trade_date']).trade_date.max().date(), ' (fii gates carry-forward after that)')
