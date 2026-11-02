import sys, os; sys.path.insert(0, 'scripts'); os.environ['RF_QUIET'] = '1'
import rf_search as S
from rf import *
R, days, n, P, Xv = S.R, S.days, S.n, S.P, S.Xv
X = S.X
smas = {k: X.rolling(k).mean().values for k in [20, 30, 50, 75, 100, 150]}
oi = pd.Series(R.oi)
def show(name, pos, mode='both', interest=True, ks=('train', 'valid', 'test', 'full')):
    r = R.run(pos, mode, interest); m = {k: met(r, *P[k], days) for k in P}
    print(f'{name:48s} ' + ' | '.join(f'{k} {m[k]["CAGR"]:5.1f}/{m[k]["DD"]:6.1f}/{m[k]["Sharpe"]:4.2f}' for k in ks)); return r
print('=== 1. SENSITIVITY of "trend(n) & OI(w-day change) rising, long-only, full size, both legs" : full-period CAGR/DD/Sharpe | test CAGR/DD')
print('rows = SMA n ; cols = OI window w')
for nn in [20, 30, 50, 75, 100, 150]:
    row = []
    for w in [3, 5, 10, 20]:
        chg = oi.pct_change(w).shift(1).values; pos = np.where((Xv > smas[nn]) & (chg > 0), 1.0, 0.0)
        r = R.run(pos, 'both', True); f_, t_ = met(r, *P['full'], days), met(r, *P['test'], days)
        row.append(f'w{w}: {f_["CAGR"]:4.1f}/{f_["DD"]:5.1f}/{f_["Sharpe"]:4.2f} | {t_["CAGR"]:4.1f}/{t_["DD"]:5.1f}')
    print(f'n={nn:<4}', '   '.join(row))
chg5 = oi.pct_change(5).shift(1).values
print('\n=== 2. sleeves (all long-only, full size, both legs)')
s_oi50 = np.where((Xv > smas[50]) & (chg5 > 0), 1.0, 0.0); s_oi100 = np.where((Xv > smas[100]) & (chg5 > 0), 1.0, 0.0)
s_mom60 = S.sigs['momentum60 long'] * S.sizings['volT10']; s_st = S.sigs['supertrend15m long'] * S.sizings['volT10']; s_tv = S.sigs['trend200 & vix<22 long']
show('A trend50 & OI5 rising', s_oi50); show('B trend100 & OI5 rising', s_oi100); show('C momentum60 volT10', s_mom60); show('D supertrend15m volT10', s_st); show('E trend200 & vix<22', s_tv)
ens = (s_oi50 + s_mom60 + s_st + s_tv) / 4; show('ENSEMBLE A+C+D+E (equal weight)', ens)
ens2 = (s_oi50 + s_oi100 + s_mom60) / 3; show('ENSEMBLE A+B+C', ens2)
print('\n=== 3. adding shorts: short when price<sma50 and OI rising (short build-up)')
for sc in [1.0, 0.5]:
    pos = s_oi50 - sc * np.where((Xv < smas[50]) & (chg5 > 0), 1.0, 0.0); show(f'long A, short build-up x{sc}', pos)
pos = s_oi50 - 0.5 * np.where((Xv < smas[50]), 1.0, 0.0) ; show('long A, short whenever below sma50 x0.5', pos)
print('\n=== 4. legs and cost stress for A (trend50 & OI5 rising)')
for mode in ['both', 'night', 'day']: show(f'A mode={mode}', s_oi50, mode)
import rf
for mult in [1, 2, 3]:
    rf.COST = 0.00025 * mult; rf.ROLL = 0.0005 * mult; show(f'A with {mult}x costs', s_oi50)
rf.COST = 0.00025; rf.ROLL = 0.0005
print('\n=== 5. A: pure futures P&L (no interest) and year-by-year (total-return | pure | buy&hold total)')
show('A pure futures P&L', s_oi50, 'both', False)
rt = R.run(s_oi50, 'both', True); rp = R.run(s_oi50, 'both', False); rb = R.run(np.ones(n), 'both', True)
for y in range(2017, 2027):
    lo, hi = np.searchsorted(days, pd.Timestamp(f'{y}-01-01')), np.searchsorted(days, pd.Timestamp(f'{y}-12-31'), side='right')
    f = lambda r: (np.prod(1 + r[lo:hi]) - 1) * 100
    print(f'  {y}: {f(rt):6.1f} | {f(rp):6.1f} | {f(rb):6.1f}')
held = np.abs(s_oi50) > 0; print(f'in market {held.mean()*100:.0f}% of days; trades/yr {(np.abs(np.diff(s_oi50))>0).sum()/ (n/252):.0f}')
# how often is the OI signal on, by year (stability of the rule)
