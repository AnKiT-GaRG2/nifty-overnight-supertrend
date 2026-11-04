"""Pre-2017 check v2: the EXACT frozen system on real 1-minute Nifty data 2012-2016 (source: rbhatia46 repo; see PROTOCOL_CHANGES.md for rules written beforehand).
Run: <venv>/bin/python scripts/rm_pre_exact.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_data, rm_final
from rm_engine import Engine, metrics_from, RF
from rm_ideas import make_sig
ROOT = rm_data.ROOT; DATA = rm_data.DATA; RES = rm_data.RES
EVAL = ('2012-07-02', '2016-08-31'); SUB = [('2012-07-02', '2014-12-31'), ('2015-01-01', '2016-08-31')]

def build_ds():
    m1 = pd.read_csv(f'{DATA}/pre_intraday/NIFTY_1min_2012-01_2016-08.csv', parse_dates=['Timestamp']).set_index('Timestamp').sort_index()
    m1 = m1[~m1.index.duplicated()]; hm = m1.index.strftime('%H:%M'); m1 = m1[(hm >= '09:15') & (hm <= '15:29')].copy(); m1['date'] = m1.index.normalize()
    b = m1.resample('15min', origin='start_day', offset='9h15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    b['start'] = b.index; b.index = b.index + pd.Timedelta(minutes=15); b.index.name = 'close_time'; b['date'] = b['start'].dt.normalize()
    g = b.groupby('date'); D = pd.DataFrame({'open': g['open'].first(), 'high': g['high'].max(), 'low': g['low'].min(), 'close': g['close'].last()})
    fut = pd.read_csv(f'{DATA}/fut/nifty_fut_pre2017.csv', parse_dates=['date', 'expiry']).drop_duplicates(['date', 'expiry']); fut = fut[(fut.open > 0) & (fut.close > 0)]
    exps = sorted(e for e in fut.expiry.unique() if e >= D.index[0]); held, roll = rm_data.synthetic(D, exps)
    D = D.copy(); D['held'] = held; D['roll'] = roll; D['m_close'] = [rm_data.mult(d, e) for d, e in zip(D.index, D.held)]
    D['m_prevclose'] = [rm_data.mult(D.index[i - 1], D.held.iloc[i]) if i > 0 else np.nan for i in range(len(D))]; D['syn_close'] = D.close * D.m_close
    return dict(m1=m1[['open', 'high', 'low', 'close', 'date']], b15=b, daily=D, flags={}, rq=rm_data.RQ, validation=None), fut.set_index(['date', 'expiry'])

def series(pre, post):
    a = pd.read_csv(pre, parse_dates=['date']).set_index('date')['close']; b = pd.read_csv(post, parse_dates=['date']).set_index('date')['close']
    s = pd.concat([a, b]); return s[~s.index.duplicated(keep='first')].sort_index()

def main():
    ds, futR = build_ds(); E = Engine(ds); S = make_sig(E); days = E.days; Ea, cov = rm_final.anchored_engine(E, futR)
    nq = series(f'{DATA}/pre/nasdaq.csv', f'{DATA}/nasdaq.csv'); us = series(f'{DATA}/pre/us10y.csv', f'{DATA}/us10y.csv')
    def prior(s, n, kind='pct'):
        s = s.dropna(); s = (s / s.shift(n) - 1) if kind == 'pct' else (s - s.shift(n)); p = np.searchsorted(s.index.values, days.values, side='left') - 1
        return pd.Series(np.where(p >= 0, s.values[np.maximum(p, 0)], np.nan), index=days)
    def cell(x, y, c=0.25):
        a = (prior(nq, 5) * 100 < -x).fillna(False); b = (prior(us, 5, 'diff') * 100 > y).fillna(False)
        return pd.Series(np.where(a, c, 1.0), index=days) * pd.Series(np.where(b, c, 1.0), index=days)
    ens = sum(cell(x, y) for x in (1, 2, 3) for y in (10, 15, 20)) / 9.0; nb3 = cell(2, 15)
    INT = pd.Series(E.cal * RF / 365.0, index=days); wl, ws = 2.0 * 0.956, 0.956
    tt, ss = S.A2(100); shortsig = np.where(tt == -1, -1, 0).astype(np.int8); lt, ls = S.baseline()
    rep = []; P = lambda *a: (print(*a), rep.append(' '.join(str(x) for x in a)))
    P('# Pre-2017 check v2: the exact frozen system on real 1-minute data, 2012-2016\n')
    P(f"Data: {len(ds['m1']):,} real 1-minute bars, {len(ds['daily'])} sessions {days[0].date()}..{days[-1].date()}; real-open/close coverage of sessions for the anchored path: {cov:.0%}. Evaluation window {EVAL[0]}..{EVAL[1]} (SMA100 warm-up before).\n")
    fl = lambda m: f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
    def met(net, a, z): ex = net[a:z]; return metrics_from(ex + INT[a:z], None, None, None, ex)
    out = {}
    for pname, En in (('REAL-ANCHORED path (verdict)', Ea), ('Synthetic path', E)):
        L = pd.Series(En.run(lt, ls, cost='floor').net_d, index=days); Sh = pd.Series(En.run(shortsig, ss, cost='floor').net_d, index=days)
        BH = pd.Series(En.run(np.ones(En.N, np.int8), np.ones(En.N), cost='floor', rebal=True).net_d, index=days)
        V = {'Plain long-only baseline': L, 'Buy and hold futures (1x)': BH, 'Same weights, no cuts (1.91/0.96)': wl * L + ws * Sh, 'NB3 fixed cell (2.0/1.0, NQ2%+MC3 15bp, cut 0.25)': 2.0 * nb3 * L + 1.0 * Sh,
             'FROZEN (1.91/0.96, 9-cell ensemble cut)': wl * ens * L + ws * Sh, 'Short leg alone (0.96)': ws * Sh, 'Long leg alone (1.91, ensemble cut)': wl * ens * L}
        out[pname] = V
        P(f'\n## {pname}: CAGR incl. 6% interest / MaxDD / Sharpe on futures P&L (floor costs)\n'); P('| System | 2012-07..2016-08 | 2012-07..2014-12 | 2015-01..2016-08 | whole window without interest |'); P('|---|---|---|---|---|')
        for k, net in V.items():
            ex = net[EVAL[0]:EVAL[1]]; P(f"| {k} | {fl(met(net, *EVAL))} | {fl(met(net, *SUB[0]))} | {fl(met(net, *SUB[1]))} | {fl(metrics_from(ex, None, None, None, ex))} |")
        yrs = {k: (V[k][EVAL[0]:EVAL[1]] + INT[EVAL[0]:EVAL[1]]).groupby(V[k][EVAL[0]:EVAL[1]].index.year).apply(lambda x: (1 + x).prod() - 1) for k in list(V)[:6]}
        P('\nCalendar-year total return (2012 = Jul-Dec, 2016 = Jan-Aug): '); P('| Year | ' + ' | '.join(['Plain', 'Buy&hold', 'No cuts', 'NB3 fixed', 'FROZEN', 'Short alone']) + ' |'); P('|---|' + '---|' * 6)
        for y in sorted(yrs['Plain long-only baseline'].index): P(f"| {y} | " + ' | '.join(f"{yrs[k][y]:.1%}" for k in list(V)[:6]) + ' |')
        mm = {k: met(v, *EVAL) for k, v in V.items()}; ex_ = lambda k, s: metrics_from(V[k][s[0]:s[1]], None, None, None, V[k][s[0]:s[1]])
        fk, bk, nk = 'FROZEN (1.91/0.96, 9-cell ensemble cut)', 'Plain long-only baseline', 'Same weights, no cuts (1.91/0.96)'
        E1a = mm[fk]['Sharpe'] > mm[bk]['Sharpe']; E1b = all(ex_(fk, s)['Sharpe'] > ex_(bk, s)['Sharpe'] for s in SUB); E2 = mm[fk]['Sharpe'] > mm['Buy and hold futures (1x)']['Sharpe']
        E3 = mm[fk]['Sharpe'] > mm[nk]['Sharpe'] and mm[fk]['MaxDD'] >= mm[nk]['MaxDD']; E4 = mm['Short leg alone (0.96)']['Sharpe'] > 0; R1 = mm[fk]['MaxDD'] > -0.15; R2 = yrs[fk].min() > -0.10
        P(f'\n### Pass criteria on the {pname}\n'); P('| Criterion | Result | Detail |'); P('|---|---|---|')
        P(f"| E1 frozen Sharpe > plain long-only (whole window and both sub-periods) | {'PASS' if (E1a and E1b) else ('PASS whole, regime-dependent' if E1a else 'FAIL')} | whole {mm[fk]['Sharpe']:.2f} vs {mm[bk]['Sharpe']:.2f}; {SUB[0][0][:7]}..{SUB[0][1][:7]} {ex_(fk, SUB[0])['Sharpe']:.2f} vs {ex_(bk, SUB[0])['Sharpe']:.2f}; {SUB[1][0][:7]}..{SUB[1][1][:7]} {ex_(fk, SUB[1])['Sharpe']:.2f} vs {ex_(bk, SUB[1])['Sharpe']:.2f} |")
        P(f"| E2 frozen Sharpe > buy and hold futures | {'PASS' if E2 else 'FAIL'} | {mm[fk]['Sharpe']:.2f} vs {mm['Buy and hold futures (1x)']['Sharpe']:.2f} |")
        P(f"| E3 cuts add value (Sharpe up and MaxDD not worse vs same weights without cuts) | {'PASS' if E3 else 'FAIL'} | Sharpe {mm[fk]['Sharpe']:.2f} vs {mm[nk]['Sharpe']:.2f}; MaxDD {mm[fk]['MaxDD']:.1%} vs {mm[nk]['MaxDD']:.1%} |")
        P(f"| E4 short leg alone positive excess Sharpe | {'PASS' if E4 else 'FAIL'} | {mm['Short leg alone (0.96)']['Sharpe']:.2f} |")
        P(f"| R1 max drawdown better than -15% | {'PASS' if R1 else 'FAIL'} | {mm[fk]['MaxDD']:.1%} |"); P(f"| R2 no calendar year worse than -10% | {'PASS' if R2 else 'FAIL'} | worst {yrs[fk].min():.1%} ({yrs[fk].idxmin()}) |")
        n_ok = sum([bool(E1a and E1b), bool(E2), bool(E3), bool(E4)]); verdict = 'SUPPORTS' if n_ok == 4 else ('PARTIAL' if n_ok >= 2 else 'DOES NOT SUPPORT')
        P(f"\n**Verdict on the {pname}: {verdict}** ({n_ok} of 4 edge criteria hold)"); out[pname + '_verdict'] = verdict
    open(f'{RES}/PRE2017_EXACT_REPORT.md', 'w').write('\n'.join(rep))
if __name__ == '__main__': main()
