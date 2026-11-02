import sys, os, itertools; sys.path.insert(0, 'scripts')
from rf import *
from factors import _asof
R = RF(); days = R.days; n = R.n; P = periods(days); X = R.X
L = lambda k: pd.read_csv(os.path.join(DATA, f'{k}.csv'), parse_dates=['date']).set_index('date')['close'].astype(float)
vix = L('vix').reindex(days).ffill().shift(1).values                       # previous day's close
A = lambda s: _asof(s, days).values
spx21 = A(L('spx').pct_change(21)); dxy21 = A(L('dxy').pct_change(21)); inr21 = A(L('usdinr').pct_change(21)); us10_21 = A(L('us10y').diff(21)); br21 = A(L('brent').pct_change(21))
ret = X.pct_change(); rv20 = (ret.rolling(20).std() * np.sqrt(252)).values
sma = {k: X.rolling(k).mean().values for k in [50, 100, 150, 200]}; Xv = X.values
rsi2 = rsi(X, 2).values
prem_ann = pd.Series(R.basis * 365 / np.maximum(R.dte, 1)).shift(1).values            # yesterday's annualised premium
oi_chg = pd.Series(R.oi).pct_change(5).shift(1).values
fii = pd.read_csv(os.path.join(DATA, 'fii2', 'fii_dii.csv'), parse_dates=['trade_date']); fii = fii[fii.trade_date < '2026-01-01'].set_index('trade_date')['net_purchase_sales_fii']
fii.index = fii.index.to_period('M').to_timestamp('M') + pd.Timedelta(days=1); fii_last = A(fii)                    # last completed month (stale after Dec 2025)
def sgn(cond_long, cond_short=None):
    s = np.where(cond_long, 1.0, 0.0)
    if cond_short is not None: s = np.where(cond_short, -1.0, s)
    return s
def state_dip(th, exit_th=65):
    s = np.zeros(n); pos = 0
    for i in range(n):
        if pos == 0 and rsi2[i] < th and Xv[i] > sma[200][i]: pos = 1
        elif pos == 1 and (rsi2[i] > exit_th or Xv[i] < sma[200][i]): pos = 0
        s[i] = pos
    return s
sigs = {}
for k in [50, 100, 150, 200]:
    sigs[f'trend sma{k} long'] = sgn(Xv > sma[k]); sigs[f'trend sma{k} long/short'] = sgn(Xv > sma[k], Xv < sma[k])
sigs['supertrend15m long'] = sgn(R.st15 == 1); sigs['supertrend15m long/short'] = sgn(R.st15 == 1, R.st15 == -1)
for k in [20, 60, 120, 250]:
    m = X.pct_change(k).values; sigs[f'momentum{k} long'] = sgn(m > 0); sigs[f'momentum{k} long/short'] = sgn(m > 0, m < 0)
for th in [15, 18, 22, 25]: sigs[f'vix<{th} long'] = sgn(vix < th)
for th in [18, 22, 25]: sigs[f'trend200 & vix<{th} long'] = sgn((Xv > sma[200]) & (vix < th)); sigs[f'trend200 long & vix>{th} short'] = sgn((Xv > sma[200]) & (vix < th), (Xv < sma[200]) & (vix > th))
for th in [5, 10, 15]: sigs[f'rsi2<{th} dip in uptrend'] = state_dip(th)
for q in [3, 5, 7]: sigs[f'cheap futures premium<{q}% long'] = sgn(prem_ann < q / 100)
sigs['trend50 & OI rising long'] = sgn((Xv > sma[50]) & (oi_chg > 0)); sigs['trend100 & OI rising long'] = sgn((Xv > sma[100]) & (oi_chg > 0))
sigs['trend200 & SPX21>0 long'] = sgn((Xv > sma[200]) & (spx21 > 0)); sigs['trend200 & dollar21<1.5% long'] = sgn((Xv > sma[200]) & (dxy21 < 0.015))
sigs['trend200 & rupee21<2% long'] = sgn((Xv > sma[200]) & (inr21 < 0.02)); sigs['trend200 & brent21<10% long'] = sgn((Xv > sma[200]) & (br21 < 0.10))
sigs['trend200 & FIIlastmonth>-10k long'] = sgn((Xv > sma[200]) & (fii_last > -10000))
sigs['buy&hold'] = np.ones(n)
sizings = {'full': np.ones(n), 'volT10': np.minimum(1, 0.10 / np.maximum(rv20, 0.05)), 'volT15': np.minimum(1, 0.15 / np.maximum(rv20, 0.05))}
sizings = {k: np.nan_to_num(v, nan=1.0) for k, v in sizings.items()}
rows = []
RF_QUIET = os.environ.get('RF_QUIET')
for (sn, s), (zn, z), mode in itertools.product(sigs.items(), sizings.items(), ['both', 'night', 'day']):
    pos = s * z
    r_tr = R.run(pos, mode, True)                                              # total-return view (futures + 6% interest on capital)
    r_px = R.run(pos, mode, False)
    m = {k: met(r_tr, *P[k], days) for k in P}; mp = {k: met(r_px, *P[k], days) for k in P}
    rows.append(dict(name=sn, size=zn, mode=mode, tv=m, px=mp, sel=m['train']['J'] + m['valid']['J'], pos=pos))
rows.sort(key=lambda r: -r['sel'])
if not RF_QUIET:
    bh = [r for r in rows if r['name'] == 'buy&hold' and r['size'] == 'full' and r['mode'] == 'both'][0]
    fm = lambda m: ' | '.join(f'{k} {m[k]["CAGR"]:5.1f}/{m[k]["DD"]:6.1f}/{m[k]["Sharpe"]:4.2f}' for k in ['train', 'valid', 'test', 'full'])
    print(f'{len(rows)} strategy variants evaluated on REAL futures. Total-return view (futures P&L + 6% interest). CAGR/MaxDD/Sharpe')
    print('BUY&HOLD  ', fm(bh['tv']))
    print('\nTOP 12 chosen on train+valid only (test is just reported):')
    for r in rows[:12]: print(f"{r['name']:34s} {r['size']:6s} {r['mode']:5s}", fm(r['tv']))
    print('\nsame top strategies, PURE futures price P&L (no interest):')
    for r in rows[:5]: print(f"{r['name']:34s} {r['size']:6s} {r['mode']:5s}", fm(r['px']))
    better = sum(1 for r in rows if r['tv']['test']['CAGR'] > bh['tv']['test']['CAGR'] and r['tv']['test']['DD'] > bh['tv']['test']['DD'])
    print(f'\nvariants that beat buy&hold on BOTH test CAGR and test drawdown: {better} of {len(rows)}')
    top = rows[0]; print('CHOSEN:', top['name'], top['size'], top['mode'])
    # ---- walk-forward of the whole selection procedure (yearly re-pick on all prior years, J = CAGR-|DD| in total-return view)
    oos = []; di = []
    for Y in range(2021, 2027):
        lo_tr, hi_tr = np.searchsorted(days, pd.Timestamp('2017-04-01')), np.searchsorted(days, pd.Timestamp(f'{Y}-01-01'))
        best = max(rows, key=lambda r: met(R.run(r['pos'], r['mode'], True), lo_tr, hi_tr, days)['J'])
        lo, hi = np.searchsorted(days, pd.Timestamp(f'{Y}-01-01')), np.searchsorted(days, pd.Timestamp(f'{Y}-12-31'), side='right')
        rr = R.run(best['pos'], best['mode'], True)[lo:hi]; oos.append(rr); di.append(days[lo:hi])
        print(f'  WF {Y}: picked {best["name"]} / {best["size"]} / {best["mode"]}  OOS year {((np.prod(1+rr)-1)*100):6.1f}%  (buy&hold {((np.prod(1+R.run(np.ones(n),"both",True)[lo:hi])-1)*100):6.1f}%)')
    x = np.concatenate(oos); d = pd.DatetimeIndex(np.concatenate([np.array(a) for a in di])); eq = np.cumprod(1 + x); yrs = (d[-1] - d[0]).days / 365.25
    xb = np.concatenate([R.run(np.ones(n), 'both', True)[np.searchsorted(days, pd.Timestamp(f'{Y}-01-01')):np.searchsorted(days, pd.Timestamp(f'{Y}-12-31'), side='right')] for Y in range(2021, 2027)]); eb = np.cumprod(1 + xb)
    print(f'WALK-FORWARD OOS 2021-26: CAGR {(eq[-1]**(1/yrs)-1)*100:5.1f}%  MaxDD {((eq/np.maximum.accumulate(eq)-1).min()*100):6.1f}%  Sharpe {x.mean()/x.std()*np.sqrt(252):4.2f}   | BUY&HOLD {(eb[-1]**(1/yrs)-1)*100:5.1f}%  {((eb/np.maximum.accumulate(eb)-1).min()*100):6.1f}%  {xb.mean()/xb.std()*np.sqrt(252):4.2f}')
    import pickle; pickle.dump([(r['name'], r['size'], r['mode']) for r in rows[:40]], open('results/rf_top.pkl', 'wb'))
    