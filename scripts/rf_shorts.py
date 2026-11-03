"""Focused test of SHORT selling on real NSE Nifty futures (daily horizon, positions decided at 15:00, filled near the close)."""
import sys, os; sys.path.insert(0, 'scripts'); os.environ['RF_QUIET'] = '1'
import rf_search as S
from rf import *
R, days, n, P, Xv, X = S.R, S.days, S.n, S.P, S.Xv, S.X
vix, sma, rsi2 = S.vix, S.sma, S.rsi2
oi5 = pd.Series(R.oi).pct_change(5).shift(1).values
mom20 = X.pct_change(20).values; low20 = X.rolling(20).min().shift(1).values
def fm(m): return f'{m["CAGR"]:5.1f}/{m["DD"]:6.1f}/{m["Sharpe"]:5.2f}'
def line(name, pos, pure=True):
    rp, rt = R.run(pos, 'both', False), R.run(pos, 'both', True)
    mp = {k: met(rp, *P[k], days) for k in P}
    print(f'{name:44s} PURE futures P&L: ' + ' | '.join(f'{k} {fm(mp[k])}' for k in ['train', 'valid', 'test', 'full']) + f' | in-mkt {np.mean(pos!=0)*100:3.0f}%')
    return rp, rt
shorts = {
 'below 50-day & OI rising (short build-up)': np.where((Xv < sma[50]) & (oi5 > 0), -1.0, 0),
 'below 200-day': np.where(Xv < sma[200], -1.0, 0),
 'below 200-day & VIX>18': np.where((Xv < sma[200]) & (vix > 18), -1.0, 0),
 'below 200-day & VIX>22': np.where((Xv < sma[200]) & (vix > 22), -1.0, 0),
 'confirmed downtrend (50d<200d, price<50d)': np.where((Xv < sma[50]) & (sma[50] < sma[200]), -1.0, 0),
 '20-day momentum < -3%': np.where(mom20 < -0.03, -1.0, 0),
 'breakdown: close below 20-day low': np.where(Xv < low20, -1.0, 0),
 'Supertrend15m red & below 200-day': np.where((R.st15 == -1) & (Xv < sma[200]), -1.0, 0),
 'sell the bounce: downtrend & RSI2>90': np.where((Xv < sma[200]) & (S.rsi2 > 90), -1.0, 0),
}
print('=== A. SHORT-ONLY strategies on real futures (CAGR/MaxDD/Sharpe; a short earns the premium decay but loses when Nifty rises)')
print('buy&hold SHORT (reference)'.ljust(44), end=' '); line('', -np.ones(n))
res = {}
for k, v in shorts.items(): res[k] = line(k, v)
print('\n=== B. the long strategy A (trend50 & OI rising) + each short sleeve (total-return view = futures P&L + 6% interest)')
longA = np.where((Xv > sma[50]) & (oi5 > 0), 1.0, 0.0)
base = R.run(longA, 'both', True); mb = {k: met(base, *P[k], days) for k in P}
print(f'{"long A only":44s} ' + ' | '.join(f'{k} {fm(mb[k])}' for k in ['train', 'valid', 'test', 'full']))
for k, v in shorts.items():
    for sc in [1.0, 0.5]:
        pos = longA + sc * v; r = R.run(pos, 'both', True); m = {kk: met(r, *P[kk], days) for kk in P}
        print(f'long A + short [{k[:34]}] x{sc}'.ljust(44) + ' ' + ' | '.join(f'{kk} {fm(m[kk])}' for kk in ['train', 'valid', 'test', 'full']))
print('\n=== C. do shorts earn in the real bear phases? pure futures P&L, calendar-year returns % for the best-looking short sleeve')
for k in ['below 200-day', 'confirmed downtrend (50d<200d, price<50d)', '20-day momentum < -3%']:
    r = R.run(shorts[k], 'both', False)
    print(f'  {k[:40]:40s}', ' '.join(f'{y}:{(np.prod(1+r[np.searchsorted(days,pd.Timestamp(f"{y}-01-01")):np.searchsorted(days,pd.Timestamp(f"{y}-12-31"),side="right")])-1)*100:5.1f}' for y in range(2017, 2027)))
print('  Nifty price return by year:', ' '.join(f'{y}:{(X[(X.index.year==y)].iloc[-1]/X[(X.index.year==y)].iloc[0]-1)*100:5.1f}' for y in range(2017, 2027)))
