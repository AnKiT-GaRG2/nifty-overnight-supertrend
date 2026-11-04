"""Pre-registered strategy search on NSE Nifty + Bank Nifty FUTURES. Rules are in results/PREREGISTRATION.md (written before this ran).
Discovery 2008-2016 -> pick top-30 -> validation 2017-2023 picks ONE finalist (highest validation Sharpe) -> test 2024-26 viewed ONCE.
Engine: position decided at close t earns close(t)->close(t+1) of the front month; cost 0.025%/side, 0.05% roll; total = pure + 6% p.a. on capital.
Run from repo root after data/fut/banknifty_fut.csv exists."""
import sys, os, itertools, time, json
sys.path.insert(0, 'scripts')
import numpy as np, pandas as pd
import warnings; warnings.filterwarnings('ignore')
from factors import _asof
t0 = time.time(); D = 'data'; LOCK = 'results/prereg_test_lock.json'
COST, ROLL, RFR = 0.00025, 0.0005, 0.06

def chain(fcsv):
    f = pd.concat([pd.read_csv(p, parse_dates=['date', 'expiry']) for p in fcsv]).drop_duplicates(['date', 'expiry'])
    f = f[f.close > 0].set_index(['date', 'expiry']).sort_index(); dd = pd.DatetimeIndex(sorted(f.index.get_level_values(0).unique()))
    grp = {d: g for d, g in f.reset_index().groupby('date')}; r = np.zeros(len(dd)); rl = np.zeros(len(dd)); pk = None; oi = np.array([grp[d].oi.sum() for d in dd], float)
    for i in range(1, len(dd)):
        a, b = grp[dd[i - 1]], grp[dd[i]]; c = sorted(set(a.expiry[a.expiry > dd[i - 1]]) & set(b.expiry))
        if not c: continue
        k = c[0]; r[i] = f.loc[(dd[i], k)].close / f.loc[(dd[i - 1], k)].close - 1; rl[i] = float(pk is not None and k != pk); pk = k
    return dd, r, rl, oi
dN, rN, rlN, _ = chain([f'{D}/fut/nifty_fut_pre2017.csv', f'{D}/fut/nifty_fut.csv'])
dB, rB, rlB, _ = chain([f'{D}/fut/banknifty_fut.csv'])
days = dN; n = len(days)
def align(dd, r, rl):                                  # put Bank Nifty on the Nifty calendar via the adjusted close level
    lvl = pd.Series(100 * np.cumprod(1 + r), index=dd).reindex(days).ffill(); rr = lvl.pct_change().fillna(0).values
    rol = pd.Series(rl, index=dd).reindex(days).fillna(0).values; return rr, rol
rB, rlB = align(dB, rB, rlB)
INST = {'Nifty': (rN, rlN), 'BankNifty': (rB, rlB)}
cal = np.r_[0, np.diff(days.values).astype('timedelta64[D]').astype(float)]
print(f'Nifty {n} days, Bank Nifty from {dB[0].date()}  ({time.time()-t0:.0f}s)')

def L(k):
    a = pd.read_csv(f'{D}/pre/{k}.csv', parse_dates=['date']); b = pd.read_csv(f'{D}/{k}.csv', parse_dates=['date'])
    return pd.concat([a, b]).drop_duplicates('date').set_index('date').sort_index()['close'].astype(float)
A_ = lambda s: _asof(s, days).values
usd, dxy, us, sp, br, vx = [L(k) for k in ['usdinr', 'dxy', 'us10y', 'spx', 'brent', 'vix']]
vprev = pd.Series(vx.reindex(days).ffill().values, index=days).shift(1).values
flags = np.vstack([A_(us.diff(21)) >= 0.25, A_(usd.pct_change(21) * 100) >= 2, A_(dxy.pct_change(21) * 100) >= 1.5, A_(sp.pct_change(21) * 100) <= -2, A_(br.pct_change(5) * 100) >= 5, vprev >= 25])
S = np.nansum(np.where(np.isnan(flags.astype(float)), 0, flags.astype(float)), axis=0)

def rsi(x, w):
    d = x.diff(); up = d.clip(lower=0).ewm(alpha=1 / w, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / w, adjust=False).mean(); return 100 - 100 / (1 + up / dn.replace(0, np.nan))
def components(r):
    X = pd.Series(100 * np.cumprod(1 + r), index=days);
    sm = {k: X.rolling(k).mean().values for k in [50, 100, 200]}; Xv = X.values
    rv = (pd.Series(r, index=days).rolling(20).std() * np.sqrt(252)).values
    rs = rsi(X, 2).values; side = np.abs(Xv / sm[100] - 1) < 0.02
    mr = np.zeros(n); pos = 0
    for i in range(n):
        if np.isnan(rs[i]): mr[i] = 0; continue
        if pos == 0 and side[i]: pos = 1 if rs[i] < 10 else (-1 if rs[i] > 90 else 0)
        elif pos == 1 and rs[i] > 50: pos = 0
        elif pos == -1 and rs[i] < 50: pos = 0
        mr[i] = pos
    return Xv, sm, rv, mr
def run_pure(pos, r, rl):
    pos = np.nan_to_num(pos); prev = np.r_[0.0, pos[:-1]]; chg = np.abs(prev - np.r_[0.0, prev[:-1]])
    return prev * r - chg * COST - ROLL * np.abs(prev) * rl
SEGS = {'disc': ('2008-01-01', '2016-12-31'), 'disc1': ('2008-01-01', '2012-12-31'), 'disc2': ('2013-01-01', '2016-12-31'), 'val': ('2017-01-01', '2023-12-31'), 'test': ('2024-01-01', '2026-12-31')}
ix = lambda s: int(np.searchsorted(days, pd.Timestamp(s)))
SI = {k: (ix(a), min(ix(b) + 1, n) if ix(b) < n else n) for k, (a, b) in SEGS.items()}
def met(r, lo, hi):
    x = r[lo:hi]; eq = np.cumprod(1 + x); yrs = max((days[hi - 1] - days[lo]).days / 365.25, 1e-9)
    return (eq[-1] ** (1 / yrs) - 1) * 100, (eq / np.maximum.accumulate(eq) - 1).min() * 100, (x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0)
tot = lambda pure: pure + RFR / 365 * cal
passes = lambda m: m[0] > 15 and abs(m[1]) < 10 and m[2] > 1.0

TRENDS = [50, 100, 200]; SMAX = [0, 1, 2]; SHORT = [None] + [(s, f) for s in [1, 2, 3] for f in [0.5, 1.0]]; SLEEVE = [0, 0.5]
SIZING = [None] + [(tv, cap) for tv in [0.08, 0.10, 0.12] for cap in [1.0, 2.0]]; INSTR = ['Nifty', 'BankNifty', 'both']
comp = {k: components(v[0]) for k, v in INST.items()}
def positions(k, tr, smax, sh, sl, sz):
    Xv, sm, rv, mr = comp[k]; up = Xv > sm[tr]; ok = ~np.isnan(sm[tr])
    p = np.where(ok & up & (S <= smax), 1.0, 0.0)
    if sh: p = np.where(ok & (~up) & (S >= sh[0]), -sh[1], p)
    if sl:
        m = mr * sl
        if not sh: m = np.where(m > 0, m, 0.0)
        p = np.clip(p + m, -1, 1)
    if sz: p = p * np.minimum(sz[1], sz[0] / np.maximum(np.nan_to_num(rv, nan=1.0), 0.04))
    return p
combos = list(itertools.product(TRENDS, SMAX, SHORT, SLEEVE, SIZING, INSTR))
print(f'declared variants: {len(combos)}')
rows = []; PUR = np.zeros((len(combos), n), np.float32)
cache = {}
for j, (tr, smax, sh, sl, sz, ins) in enumerate(combos):
    def one(k):
        key = (k, tr, smax, sh, sl, sz)
        if key not in cache: cache[key] = run_pure(positions(k, tr, smax, sh, sl, sz), *INST[k])
        return cache[key]
    pure = 0.5 * (one('Nifty') + one('BankNifty')) if ins == 'both' else one(ins)
    PUR[j] = pure
TOT = PUR.astype(np.float64) + RFR / 365 * cal
def seg_metrics(M, a, b):
    x = M[:, a:b]; eq = np.cumprod(1 + x, axis=1); yrs = (days[b - 1] - days[a]).days / 365.25
    c = (eq[:, -1] ** (1 / yrs) - 1) * 100; dd = (eq / np.maximum.accumulate(eq, axis=1) - 1).min(axis=1) * 100
    sh = x.mean(axis=1) / np.where(x.std(axis=1) > 0, x.std(axis=1), np.nan) * np.sqrt(252); return c, dd, np.nan_to_num(sh)
c1, d1, _ = seg_metrics(TOT, *SI['disc1']); c2, d2, _ = seg_metrics(TOT, *SI['disc2']); disc_score = np.minimum(c1 - np.abs(d1), c2 - np.abs(d2))
cd, dd_, sd = seg_metrics(TOT, *SI['disc']); cv, dv, sv = seg_metrics(TOT, *SI['val'])
nm = lambda j: (lambda t: f"{t[5]} trend{t[0]} S<={t[1]} short={t[2]} MR={t[3]} size={t[4]}")(combos[j])
hold = np.ones(n) * 0; hold_ret = rN; hold_tot = tot(run_pure(np.ones(n), rN, rlN))
print(f'built {len(combos)} variants in {time.time()-t0:.0f}s')
print('\nHOLD Nifty futures (total view):', ' | '.join(f"{k} {met(hold_tot, *SI[k])[0]:5.1f}/{met(hold_tot, *SI[k])[1]:6.1f}/{met(hold_tot, *SI[k])[2]:4.2f}" for k in ['disc', 'val', 'test']))
okd = (cd > 15) & (np.abs(dd_) < 10) & (sd > 1); okv = (cv > 15) & (np.abs(dv) < 10) & (sv > 1)
print(f'null rates: variants meeting all 3 targets on discovery {okd.mean()*100:.1f}% ({okd.sum()}), on validation {okv.mean()*100:.1f}% ({okv.sum()}); on BOTH {np.mean(okd&okv)*100:.1f}% ({int((okd&okv).sum())})')
top = np.argsort(-disc_score)[:30]
print('\nTOP 30 by discovery score -> validation (2017-23) CAGR/DD/Sharpe (test NOT shown)')
for j in top: print(f'{nm(j):75s} disc {cd[j]:5.1f}/{dd_[j]:6.1f}/{sd[j]:4.2f} | val {cv[j]:5.1f}/{dv[j]:6.1f}/{sv[j]:4.2f} {"PASS" if okv[j] else ""}')
fin = int(top[np.argmax(sv[top])]); print(f'\nFINALIST (best validation Sharpe among top-30): {nm(fin)}')
print(f'  validation passes all 3 targets: {bool(okv[fin])}   (top-30 variants passing validation: {int(okv[top].sum())})')
if os.path.exists(LOCK):
    prev = json.load(open(LOCK))
    if prev['finalist'] != nm(fin): print('ABORT: finalist changed after test was viewed:', prev['finalist']); sys.exit(1)
json.dump({'finalist': nm(fin), 'n_variants': len(combos)}, open(LOCK, 'w'))
print('\n=== TEST 2024-26, viewed once for the finalist ===')
t = met(TOT[fin], *SI['test']); u = met(PUR[fin].astype(float), *SI['test']); h = met(hold_tot, *SI['test'])
print(f'FINALIST total return CAGR/MaxDD/Sharpe: {t[0]:.1f}% / {t[1]:.1f}% / {t[2]:.2f}   pure futures: {u[0]:.1f}% / {u[1]:.1f}% / {u[2]:.2f}')
print(f'HOLD Nifty futures total               : {h[0]:.1f}% / {h[1]:.1f}% / {h[2]:.2f}')
print(f'ACCEPTED (CAGR>15, |MaxDD|<10, Sharpe>1.0): {passes(t)}')
# descriptive extras (after the single test look; nothing is changed because of them)
x3 = tot(np.zeros(n));
tr_, smax, sh, sl, sz, ins = combos[fin]
def pure_c(cx):
    global COST, ROLL
    c0, r0 = COST, ROLL; COST, ROLL = c0 * cx, r0 * cx
    try: return (0.5 * (run_pure(positions('Nifty', tr_, smax, sh, sl, sz), *INST['Nifty']) + run_pure(positions('BankNifty', tr_, smax, sh, sl, sz), *INST['BankNifty'])) if ins == 'both' else run_pure(positions(ins, tr_, smax, sh, sl, sz), *INST[ins]))
    finally: COST, ROLL = c0, r0
print('cost stress (total view, disc/val/test):')
for cx in [1, 3]:
    r = tot(pure_c(cx)); print(f'  x{cx}: ' + ' | '.join(f"{k} {met(r, *SI[k])[0]:5.1f}/{met(r, *SI[k])[1]:6.1f}/{met(r, *SI[k])[2]:4.2f}" for k in ['disc', 'val', 'test']))
print('year by year total return % (finalist / Hold):')
for y in range(2008, 2027):
    a, b = ix(f'{y}-01-01'), min(ix(f'{y}-12-31') + 1, n); print(f'  {y}: {(np.prod(1+TOT[fin][a:b])-1)*100:6.1f} / {(np.prod(1+hold_tot[a:b])-1)*100:6.1f}')
print(f'\ndone {time.time()-t0:.0f}s')
