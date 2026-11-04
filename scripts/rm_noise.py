"""NOISE round: shortlist factors vs a circular-shift noise benchmark (rules in PROTOCOL_CHANGES.md ROUND "NOISE"). Run: <venv>/bin/python scripts/rm_noise.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, requests
import rm_v2next as V, rm_v2lev as L, rm_stress as ST, rm_lossf as LF
from rm_ideas import trial_log, DATA
em, ep = L.em, L.ep; FULL, HOLD = L.FULL, L.HOLD; fl = L.fl; ELIST = ST.ELECT + ST.BUDGET
def yahoo(sym, name):
    p = f'{DATA}/pre/{name}.csv'
    if not os.path.exists(p):
        r = requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}', params={'period1': 1325376000, 'period2': 1793000000, 'interval': '1d'}, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30).json()['chart']['result'][0]
        s = pd.Series(r['indicators']['quote'][0]['close'], index=pd.to_datetime(r['timestamp'], unit='s').normalize()).dropna(); s.rename('close').rename_axis('date').to_csv(p)
    return pd.read_csv(p, parse_dates=['date']).set_index('date')['close']
NIFTY = LF.ser(f'{DATA}/pre/nifty.csv', f'{DATA}/nifty.csv'); BN = pd.concat([yahoo('%5ENSEBANK', 'banknifty_yahoo')[:'2016-09-30'], pd.read_csv(f'{DATA}/banknifty.csv', parse_dates=['date']).set_index('date')['close']]); BN = BN[~BN.index.duplicated()]
MID = yahoo('%5ENSEMDCP50', 'midcap50_yahoo')
def prior_val(days, s):
    s = s[~s.index.duplicated()].dropna().sort_index(); p = np.searchsorted(s.index.values, days.values, side='left') - 1
    return pd.Series(np.where(p >= 0, s.values[np.maximum(p, 0)], np.nan), index=days)
def rel(days, a, b, n):
    ra, rb = (a / a.shift(n) - 1), (b / b.shift(n) - 1); return prior_val(days, (ra - rb).dropna())
def vrp_pct(env):
    c = pd.Series(env['S'].D['close'].values, index=env['S'].D.index); vol = c.pct_change().rolling(20).std() * np.sqrt(252) * 100
    vp = LF.VIX.reindex(c.index).ffill() - vol; return vp.rolling(252, min_periods=60).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True).shift(1)
def tom_flag(days):
    f = pd.Series(False, index=days)
    for _, g in pd.Series(range(len(days)), index=days).groupby([days.year, days.month]):
        i = g.values; f.iloc[list(i[:3]) + list(i[-2:])] = True
    return f
def mult(env, fam, j):
    days = env['days']
    if fam == 'TOM':
        t = tom_flag(days); return pd.Series(np.where(t, 1.25, 1.0), index=days) if j == 0 else pd.Series(np.where(t, 1.0, 0.75), index=days)
    if fam == 'S1': c = (rel(days, BN, NIFTY, [10, 20, 40][j]) < 0)
    elif fam == 'O3': c = (vrp_pct(env).reindex(days) < [10, 20, 30][j])
    else: c = (rel(days, MID, NIFTY, 20) < -[0, 0.01, 0.02][j])
    return pd.Series(np.where(c.fillna(False), 0.5, 1.0), index=days)
FAMS = {'TOM': 2, 'S1': 3, 'O3': 3, 'MID': 3}
if __name__ == '__main__':
    rng = np.random.default_rng(20261104); CP = {w: ST.comps(env, 'floor') for w, env in (('FULL', em), ('HOLD', ep))}
    EV = {'FULL': ST.ev_mask(em, ELIST), 'HOLD': ST.ev_mask(ep, ELIST)}
    bF = V.met(em, LF.fe_stream(em, CP['FULL'], EV['FULL']), *FULL); bH = V.met(ep, LF.fe_stream(ep, CP['HOLD'], EV['HOLD']), *HOLD)
    d = tom_flag(em['days']); r = (LF.fe_stream(em, CP['FULL'], EV['FULL']))['2017-04-03':]; print(f'TOM diagnostic: mean daily v2-FE P&L on TOM days {r[d.reindex(r.index)].mean() * 1e4:.1f} bp ({d.reindex(r.index).mean():.0%} of days) vs other days {r[~d.reindex(r.index)].mean() * 1e4:.1f} bp\n')
    results = {}
    for fam, nc in FAMS.items():
        ok = True; print(f'## {fam}')
        for j in range(nc):
            mF, mH = mult(em, fam, j), mult(ep, fam, j)
            nF = LF.fe_stream(em, CP['FULL'], EV['FULL'], mF); nH = LF.fe_stream(ep, CP['HOLD'], EV['HOLD'], mH)
            eF = L.eqdd(em, nF, bF['MaxDD'], *FULL) - bF['CAGR']; eH = L.eqdd(ep, nH, bH['MaxDD'], *HOLD) - bH['CAGR']
            valid = mF.index >= pd.Timestamp('2017-04-03'); null = []
            for _ in range(200):
                k = int(rng.integers(60, len(mF) - 60)); ms = pd.Series(np.roll(mF.values, k), index=mF.index)
                null.append(L.eqdd(em, LF.fe_stream(em, CP['FULL'], EV['FULL'], ms), bF['MaxDD'], *FULL) - bF['CAGR'])
            p95 = np.percentile(null, 95); beat = (np.array(null) < eF).mean(); trial_log('NOISE_' + fam, {'j': j}, 'train', V.met(em, nF, *FULL))
            cellok = eF > 0 and eH > 0 and eF > p95; ok &= cellok
            print(f'  cell {j + 1}: FULL {fl(V.met(em, nF, *FULL))} | equal-DD delta FULL {eF * 100:+.1f} pts, HOLD {eH * 100:+.1f} pts | null 95th pct {p95 * 100:+.1f} pts, beats {beat:.0%} of shifts | {"ok" if cellok else "no"}')
        print(f'  -> {fam}: {"PASS" if ok else "FAIL"}'); results[fam] = ok
    print('\nVerdict:', results)
