"""Futures-only strategy report (Nifty index futures, NSE bhavcopy). Everything is priced on real futures contracts.
Execution: signal from data up to close t (incl. same-day OI, published after the close) -> trade at the OPEN of t+1 -> hold open->open on the same contract.
Costs per side: brokerage, STT (sell, date-dependent), exchange, SEBI, GST, stamp (buy), slippage; roll = sell near + buy far + extra spread.
Protocol (frozen before looking at test): train 2018-04..2021-12 | valid 2022-01..2023-12 | test 2024-01..2026-11. Params tuned on TRAIN only; shortlist by TRAIN+VALID; test shown once."""
import itertools, math, sys, json
import numpy as np, pandas as pd
from statistics import NormalDist
ND = NormalDist(); TRIALS = []                       # every (strategy, params) evaluated is logged here
# ------------------------------------------------------------------ data
f = pd.concat([pd.read_csv('data/fut/nifty_fut_2012_2017.csv', parse_dates=['date', 'expiry']), pd.read_csv('data/fut/nifty_fut.csv', parse_dates=['date', 'expiry'])]).drop_duplicates(['date', 'expiry'])
f = f[(f.open > 0) & (f.close > 0)]
days = pd.DatetimeIndex(sorted(f.date.unique())); n = len(days); G = {d: g.set_index('expiry') for d, g in f.groupby('date')}
rcc = np.zeros(n); rho = np.zeros(n); rollx = np.zeros(n); Kx = [None] * n; Kc = [None] * n
for i in range(1, n):
    a, b = G[days[i - 1]], G[days[i]]; k = min(e for e in a.index if e > days[i - 1] and e in b.index); Kc[i] = k
    rcc[i] = b.close[k] / a.close[k] - 1
for h in range(n - 1):
    a, b = G[days[h]], G[days[h + 1]]; k = min(e for e in a.index if e > days[h] and e in b.index); Kx[h] = k
    rho[h] = b.open[k] / a.open[k] - 1; rollx[h] = float(h > 0 and Kx[h - 1] is not None and k != Kx[h - 1])
adjc = 100 * np.cumprod(1 + rcc); Hh = np.zeros(n); Ll = np.zeros(n); Hh[0] = Ll[0] = 100
for i in range(1, n):
    r_ = G[days[i]].loc[Kc[i]]; s_ = adjc[i] / r_.close; Hh[i], Ll[i] = r_.high * s_, r_.low * s_
S = lambda a: pd.Series(a, index=days)
oin = S([G[d].oi.sum() for d in days])                                            # naive: sum of OI over all listed contracts
dl = [0.0]
for i in range(1, n):                                                              # expiry-adjusted: like-for-like change over contracts present on both days
    a, b = G[days[i - 1]].oi, G[days[i]].oi; both = a.index.intersection(b.index); dl.append(float((b[both] - a[both]).sum()))
oia = S(oin.iloc[0] + np.cumsum(dl))
vix = pd.read_csv('data/vix_ext.csv', parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()
D = dict(c=S(adjc), h=S(Hh), l=S(Ll), vix=vix, oin=oin, oia=oia)
# ------------------------------------------------------------------ costs (fractions of notional per side)
BROK, EXCH, SEBI, STAMP = 0.000012, 0.000019, 0.000001, 0.00002
def stt(d): return np.where(d < pd.Timestamp('2013-10-01'), 0.00017, np.where(d < pd.Timestamp('2023-04-01'), 0.0001, np.where(d < pd.Timestamp('2024-10-01'), 0.000125, 0.0002)))
STT = stt(days.values)
def side_costs(slip):
    gst = 0.18 * (BROK + EXCH + SEBI); base = BROK + EXCH + SEBI + gst + slip
    return base + STAMP + 0 * STT, base + STT                       # (buy, sell) arrays
ROLL_EXTRA = 0.0001
def pnl(pos, slip=0.0001, gross=False):
    pos = np.nan_to_num(np.asarray(pos, float)); ret = pos * rho
    if gross: return ret
    buy, sell = side_costs(slip); prev = np.r_[0.0, pos[:-1]]; d = pos - prev
    cost = np.maximum(d, 0) * buy + np.maximum(-d, 0) * sell
    carried = np.where(np.sign(pos) == np.sign(prev), np.minimum(np.abs(pos), np.abs(prev)), 0.0)
    cost = cost + carried * rollx * (buy + sell + ROLL_EXTRA)
    return ret - cost
def to_pos(sig): return np.r_[0.0, np.nan_to_num(np.asarray(sig, float))[:-1]]      # signal at close t -> position from open t+1
PER = {'pre': ('2013-01-01', '2017-03-31'), 'train_old': ('2018-04-01', '2021-12-31'), 'train': ('2013-01-01', '2021-12-31'), 'valid': ('2022-01-01', '2023-12-31'), 'test': ('2024-01-01', '2026-12-31')}
sl = lambda a, b: (int(np.searchsorted(days.values, np.datetime64(a))), int(np.searchsorted(days.values, np.datetime64(b), side='right')))
IDX = {k: sl(*v) for k, v in PER.items()}; IDX['full'] = (IDX['train'][0], IDX['test'][1] - 1); IDX['full_old'] = (IDX['train_old'][0], IDX['test'][1] - 1)
def met(x):
    x = np.asarray(x)
    if len(x) < 30: return dict(CAGR=np.nan, Sharpe=np.nan, MaxDD=np.nan, Vol=np.nan)
    eq = np.cumprod(1 + x); cg = eq[-1] ** (252 / len(x)) - 1; sd = x.std(ddof=1); dd = (eq / np.maximum.accumulate(np.r_[1, eq])[1:] - 1).min()
    return dict(CAGR=100 * cg, Sharpe=(x.mean() / sd * np.sqrt(252) if sd > 0 else 0.0), MaxDD=100 * dd, Vol=100 * sd * np.sqrt(252))
# ------------------------------------------------------------------ indicators / strategy builders  (all take D, return signal series known at close t)
sma = lambda x, w: x.rolling(w).mean(); ema = lambda x, w: x.ewm(span=w, adjust=False).mean()
def rsi(x, w):
    d = x.diff(); u = d.clip(lower=0).ewm(alpha=1 / w, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / w, adjust=False).mean(); return 100 - 100 / (1 + u / dn.replace(0, np.nan))
def atr(D, w):
    c, h, l = D['c'], D['h'], D['l']; tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1); return tr.ewm(alpha=1 / w, adjust=False).mean()
def state(enter, exit_):
    e, x = enter.fillna(False).values, exit_.fillna(False).values; p = np.zeros(len(e)); cur = 0.0
    for i in range(len(e)):
        if cur == 0 and e[i]: cur = 1.0
        elif cur == 1 and x[i]: cur = 0.0
        p[i] = cur
    return pd.Series(p, index=enter.index)
ls_ = lambda s, L: s if L else s.clip(lower=0)
def b_bh(D, ls=False): return pd.Series(1.0, index=D['c'].index)
def b_sma(D, a, b, ls=False): c = D['c']; return ls_(np.sign(sma(c, a) - sma(c, b)).where(sma(c, b).notna(), 0), ls)
def b_ema(D, a, b, ls=False): c = D['c']; return ls_(np.sign(ema(c, a) - ema(c, b)).where(sma(c, b).notna(), 0), ls)
def b_macd(D, a, b, s, ls=False): c = D['c']; m = ema(c, a) - ema(c, b); return ls_(np.sign(m - ema(m, s)).where(sma(c, b).notna(), 0), ls)
def b_rsimr(D, w, lo, hi, ls=False): r = rsi(D['c'], w); return state(r < lo, r > hi)
def b_rsi2(D, w, lo, hi, ls=False): c = D['c']; r = rsi(c, w); return state((r < lo) & (c > sma(c, 200)), r > hi)
def b_bbmr(D, w, k, ls=False): c = D['c']; m, s = sma(c, w), c.rolling(w).std(); return state(c < m - k * s, c > m)
def b_bbbo(D, w, k, ls=False): c = D['c']; m, s = sma(c, w), c.rolling(w).std(); return state(c > m + k * s, c < m)
def b_donch(D, en, ex, ls=False): c, h, l = D['c'], D['h'], D['l']; return state(c > h.rolling(en).max().shift(), c < l.rolling(ex).min().shift())
def b_st(D, w, m, ls=False):
    c = D['c'].values; a = atr(D, w).values; hl = ((D['h'] + D['l']) / 2).values; ub, lb = hl + m * a, hl - m * a; fu, fl, d = ub.copy(), lb.copy(), np.ones(len(c))
    for i in range(1, len(c)):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]; fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        d[i] = 1 if (d[i - 1] == -1 and c[i] > fu[i - 1]) else (-1 if (d[i - 1] == 1 and c[i] < fl[i - 1]) else d[i - 1])
    return ls_(pd.Series(d, index=D['c'].index), ls)
def b_px(D, w, ls=False): c = D['c']; return ls_(np.sign(c - sma(c, w)).where(sma(c, w).notna(), 0), ls)
def b_tsm(D, w, ls=False): c = D['c']; return ls_(np.sign(c / c.shift(w) - 1).fillna(0), ls)
def b_adx(D, w, th, ls=False):
    h, l = D['h'], D['l']; up, dn = h.diff(), -l.diff(); idx = h.index
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=idx); mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=idx); a = atr(D, w)
    pdi = 100 * pdm.ewm(alpha=1 / w, adjust=False).mean() / a; mdi = 100 * mdm.ewm(alpha=1 / w, adjust=False).mean() / a
    adx = (100 * (pdi - mdi).abs() / (pdi + mdi)).ewm(alpha=1 / w, adjust=False).mean(); return ls_(np.sign(pdi - mdi).where(adx > th, 0), ls)
def b_stoch(D, w, lo, hi, ls=False):
    c, h, l = D['c'], D['h'], D['l']; k = (100 * (c - l.rolling(w).min()) / (h.rolling(w).max() - l.rolling(w).min())).rolling(3).mean(); return state(k < lo, k > hi)
def b_kelt(D, w, m, ls=False): c = D['c']; mid = ema(c, w); return state(c > mid + m * atr(D, w), c < mid)
def b_ibs(D, lo, hi, ls=False): ibs = (D['c'] - D['l']) / (D['h'] - D['l']).replace(0, np.nan); return state(ibs < lo, ibs > hi)
def b_dip(D, th, ls=False): r = D['c'].pct_change(); return ((r / r.rolling(20).std().shift()) < -th).astype(float)
def oi_cond(D, how, oikey):
    o = D[oikey]
    return {'chg5': o > o.shift(5), 'chg1': o > o.shift(1), 'sma20': o > sma(o, 20)}[how]
def b_trend_oi(D, N, how, oikey, ls=False): c = D['c']; return ((c > sma(c, N)) & oi_cond(D, how, oikey)).astype(float)
def b_buildup(D, k, oikey, ls=False): c = D['c']; return ((c > c.shift(k)) & (D[oikey] > D[oikey].shift(k))).astype(float)
FAM = [  # (name, builder, default, grid, has_ls)
 ('Buy & Hold futures', b_bh, {}, {}, False),
 ('SMA cross 50/200', b_sma, dict(a=50, b=200), dict(a=[20, 30, 50, 100], b=[100, 150, 200]), True),
 ('SMA cross 20/50', b_sma, dict(a=20, b=50), dict(a=[10, 15, 20, 30], b=[40, 50, 80]), True),
 ('EMA cross 12/26', b_ema, dict(a=12, b=26), dict(a=[8, 12, 20], b=[21, 26, 50]), True),
 ('MACD 12/26/9', b_macd, dict(a=12, b=26, s=9), dict(a=[8, 12, 16], b=[21, 26, 40], s=[9]), True),
 ('RSI(14) 30/50 mean-rev', b_rsimr, dict(w=14, lo=30, hi=50), dict(w=[7, 14, 21], lo=[25, 30, 35], hi=[50, 60]), False),
 ('Connors RSI(2) 10/70', b_rsi2, dict(w=2, lo=10, hi=70), dict(w=[2, 3, 4], lo=[5, 10, 15], hi=[60, 70, 80]), False),
 ('Bollinger mean-rev (20,2)', b_bbmr, dict(w=20, k=2.0), dict(w=[10, 20, 30], k=[1.5, 2.0, 2.5]), False),
 ('Bollinger breakout (20,2)', b_bbbo, dict(w=20, k=2.0), dict(w=[10, 20, 30, 50], k=[1.5, 2.0, 2.5]), False),
 ('Donchian 20/10 (turtle)', b_donch, dict(en=20, ex=10), dict(en=[20, 40, 55], ex=[10, 20]), False),
 ('Donchian 55/20', b_donch, dict(en=55, ex=20), dict(en=[40, 55, 80], ex=[10, 20, 40]), False),
 ('Supertrend daily (10,3)', b_st, dict(w=10, m=3.0), dict(w=[7, 10, 14], m=[2.0, 3.0, 4.0]), True),
 ('Price > 200DMA', b_px, dict(w=200), dict(w=[50, 100, 150, 200]), True),
 ('Time-series momentum 252d', b_tsm, dict(w=252), dict(w=[63, 126, 252]), True),
 ('ADX/DI trend (14,25)', b_adx, dict(w=14, th=25), dict(w=[10, 14, 20], th=[20, 25, 30]), True),
 ('Stochastic mean-rev (14,20/80)', b_stoch, dict(w=14, lo=20, hi=80), dict(w=[9, 14, 21], lo=[20, 30], hi=[70, 80]), False),
 ('Keltner breakout (20,2)', b_kelt, dict(w=20, m=2.0), dict(w=[10, 20, 40], m=[1.5, 2.0, 3.0]), False),
 ('IBS mean-reversion', b_ibs, dict(lo=0.2, hi=0.8), dict(lo=[0.1, 0.2, 0.3], hi=[0.7, 0.8]), False),
 ('Buy-the-dip (-1.5 sigma)', b_dip, dict(th=1.5), dict(th=[1.0, 1.5, 2.0, 2.5]), False),
 ('Trend(50) only [no OI]', b_px, dict(w=50), dict(w=[30, 40, 50, 60, 80]), False),
]
OI_HOW = ['chg5', 'chg1', 'sma20']
OIFAM = [(f'Trend(N)+OI {how} [{lab}]', (lambda D, N, _h=how, _k=key, ls=False: b_trend_oi(D, N, _h, _k)), dict(N=50), dict(N=[30, 40, 50, 60, 80]), False, key)
         for how in OI_HOW for lab, key in [('naive OI', 'oin'), ('expiry-adj OI', 'oia')]]
OIFAM += [(f'Long build-up (price&OI up over k) [{lab}]', (lambda D, k, _k=key, ls=False: b_buildup(D, k, _k)), dict(k=5), dict(k=[3, 5, 10, 20]), False, key) for lab, key in [('naive OI', 'oin'), ('expiry-adj OI', 'oia')]]
# ------------------------------------------------------------------ engine
def evaluate(name, fn, params, ls=False, slip=0.0001, log=True):
    sig = fn(D, **params, ls=ls) if fn is not None else None
    pos = to_pos(sig); r = pnl(pos, slip); out = {}
    for k, (i, j) in IDX.items():
        m = met(r[i:j]); m['Exposure'] = 100 * np.mean(np.abs(pos[i:j]) > 0); m['Trades'] = int(np.sum(np.diff(np.r_[0, pos[i:j]]) != 0)); out[k] = m
    if log: TRIALS.append(dict(name=name, params=str(params), ls=ls, sr_tv_daily=float(np.nan_to_num(r[IDX['train'][0]:IDX['valid'][1]].mean() / max(r[IDX['train'][0]:IDX['valid'][1]].std(ddof=1), 1e-12)))))
    return dict(name=name, params=params, ls=ls, sig=sig, pos=pos, ret=r, m=out)
RES = {}   # (label)-> result
def run_family(name, fn, default, grid, has_ls, key=None):
    for L in ([False, True] if has_ls else [False]):
        tag = name + (' [L/S]' if L else (' [long-only]' if has_ls else ''))
        RES[(tag, 'default')] = evaluate(tag, fn, default, L)
        if grid:
            best = None; best_old = None
            for vals in itertools.product(*grid.values()):
                P = dict(zip(grid.keys(), vals))
                if 'a' in P and 'b' in P and P['a'] >= P['b']: continue
                res = evaluate(tag, fn, P, L); RES[(tag, 'grid', str(P))] = res
                sh = res['m']['train']['Sharpe']
                if best is None or sh > best[0]: best = (sh, res)
                sho = res['m']['train_old']['Sharpe']
                if best_old is None or sho > best_old[0]: best_old = (sho, res)
            if best: RES[(tag, 'tuned')] = best[1]
            if best_old: RES[(tag, 'tuned_old')] = best_old[1]
for fam in FAM: run_family(*fam)
for fam in OIFAM: run_family(*fam[:5])
NT = len(TRIALS); print('strategy/param configurations evaluated in this report:', NT)


# ================================================================== PART 2 (extended-history analysis)
PRIOR_TRIALS = 2354; N_ALL = NT + PRIOR_TRIALS       # earlier work on 2018-26 data: 2,031 exploratory + 323 in the first futures report
BH = RES[('Buy & Hold futures', 'default')]; bhm = BH['m']
COLS = ['pre', 'train', 'valid', 'test', 'full']; CN = {'train_old': 'Old train 2018-21', 'pre': 'Pre 2013-17', 'train': 'Train 2013-21', 'valid': 'Valid 2022-23', 'test': 'Test 2024-26', 'full': 'Full 2013-26'}
def fmt(m, k): return f"{m[k]['CAGR']:.1f} / {m[k]['Sharpe']:.2f} / {m[k]['MaxDD']:.1f}"
def beats(m, k): return (m[k]['CAGR'] > bhm[k]['CAGR']) and (m[k]['Sharpe'] > bhm[k]['Sharpe']) and (m[k]['MaxDD'] > bhm[k]['MaxDD'])
HDR = "| Strategy | " + " | ".join(CN[c] for c in COLS) + " | Exposure |\n|---|" + "---|" * (len(COLS) + 1)
def row(label, res, cols=COLS): m = res['m']; return f"| {label} | " + " | ".join(fmt(m, c) for c in cols) + f" | {m['full']['Exposure']:.0f}% |"
md = {}
tags = sorted({k[0] for k in RES if k[1] == 'default'}, key=lambda t: -RES[(t, 'default')]['m']['full']['Sharpe'])
md['A'] = HDR + "\n" + "\n".join(row(t, RES[(t, 'default')]) for t in tags)
# --- Stage 1: parameters frozen from the FIRST report (tuned on 2018-04..2021-12 only), run on never-seen 2013-17
told = {k[0]: RES[k] for k in RES if k[1] == 'tuned_old'}
HDR1 = "| Strategy (params frozen from 2018-21 train) | **Pre 2013-17 (never seen)** | Old train 2018-21 | Valid 2022-23 | Test 2024-26 | Beats B&H on pre? |\n|---|---|---|---|---|---|"
def row1(l, r): m = r['m']; return f"| {l} | **{fmt(m,'pre')}** | {fmt(m,'train_old')} | {fmt(m,'valid')} | {fmt(m,'test')} | {'YES' if beats(m,'pre') else 'no'} |"
md['FZ'] = HDR1 + "\n" + "\n".join(row1(f"{t} {told[t]['params']}", told[t]) for t in sorted(told, key=lambda t: -told[t]['m']['pre']['Sharpe']) if not t.startswith('Buy & Hold')) + "\n" + row1('Buy & Hold futures', BH)
# --- Stage 2: re-tune on extended train 2013-2021
tuned = {k[0]: RES[k] for k in RES if k[1] == 'tuned'}
md['B'] = HDR.replace('| Strategy', '| Strategy (params tuned on TRAIN 2013-21)') + "\n" + "\n".join(row(f"{t} {tuned[t]['params']}", tuned[t]) for t in sorted(tuned, key=lambda t: -tuned[t]['m']['train']['Sharpe']))
pool = [(t, r) for t, r in tuned.items() if not t.startswith('Buy & Hold') and r['m']['train']['Exposure'] > 5]
short = sorted([(t, r) for t, r in pool if r['m']['train']['Sharpe'] > 0.5 and r['m']['valid']['Sharpe'] > 0.5 and r['m']['train']['CAGR'] > 0 and r['m']['valid']['CAGR'] > 0], key=lambda x: -min(x[1]['m']['train']['Sharpe'], x[1]['m']['valid']['Sharpe']))
LOCK = short[:3]; print('SHORTLIST:', [t for t, _ in short]); print('LOCKED:', [(t, r['params']) for t, r in LOCK])
HEAD = RES[('Trend(N)+OI chg5 [expiry-adj OI]', 'default')]; HEAD_NAIVE = RES[('Trend(N)+OI chg5 [naive OI]', 'default')]; TREND_ONLY = RES[('Trend(50) only [no OI]', 'default')]
fin = [('Buy & Hold futures', BH), ('Trend(50)+rising OI (5d), expiry-adjusted OI', HEAD), ('Trend(50)+rising OI (5d), naive OI', HEAD_NAIVE), ('Trend(50) only (no OI)', TREND_ONLY)] + [(f"RE-TUNED LOCK: {t} {r['params']}", r) for t, r in LOCK]
md['C'] = HDR + "\n" + "\n".join(row(l, r) for l, r in fin)
sb = ["| Strategy (tuned 2013-21) | Beats B&H (CAGR+Sharpe+MaxDD) Pre/Train/Valid/Test | Positive CAGR Pre/Train/Valid/Test |", "|---|---|---|"]
for t in sorted(tuned):
    if t.startswith('Buy & Hold'): continue
    m = tuned[t]['m']; ks = ['pre', 'train', 'valid', 'test']
    sb.append(f"| {t} | {'/'.join('Y' if beats(m,k) else 'n' for k in ks)} | {'/'.join('+' if m[k]['CAGR']>0 else '-' for k in ks)} |")
md['SCORE'] = "\n".join(sb)
allpos = [t for t in tuned if not t.startswith('Buy & Hold') and all(tuned[t]['m'][k]['CAGR'] > 0 for k in ['pre', 'train', 'valid', 'test'])]
allbeat = [t for t in tuned if not t.startswith('Buy & Hold') and all(beats(tuned[t]['m'], k) for k in ['pre', 'valid', 'test'])]
print('positive in all four periods:', allpos); print('beat B&H in pre+valid+test:', allbeat)
# --- OI sweep with 5 N values on all periods
sw = ["| Variant | N | Pre 2013-17 | Train 2013-21 | Valid 2022-23 | Test 2024-26 | Beats B&H (Pre/Valid/Test) |", "|---|---|---|---|---|---|---|"]
for lab in [f'Trend(N)+OI {h} [{l}]' for h in OI_HOW for l in ['expiry-adj OI', 'naive OI']] + ['Trend(50) only [no OI]']:
    for N in [30, 40, 50, 60, 80]:
        r = RES[(lab, 'grid', str(dict(N=N) if lab.startswith('Trend(N)') else dict(w=N)))]; m = r['m']
        sw.append(f"| {lab} | {N} | {fmt(m,'pre')} | {fmt(m,'train')} | {fmt(m,'valid')} | {fmt(m,'test')} | {'/'.join('Y' if beats(m,k) else 'n' for k in ['pre','valid','test'])} |")
md['SWEEP'] = "\n".join(sw)
# --- Costs
fr = lambda r, s=0.0001, g=False: pnl(r['pos'], s, g)
cs = ["| Strategy | Gross full 2013-26 | Net (slip 0.01%) | Net (slip 0.03%) | Round trips | Cost drag %/yr |", "|---|---|---|---|---|---|"]
for l, r in fin:
    i, j = IDX['full']; g = met(fr(r, g=True)[i:j]); a = met(fr(r)[i:j]); b = met(fr(r, 0.0003)[i:j]); rt = r['m']['full']['Trades'] / 2
    cs.append(f"| {l} | {g['CAGR']:.1f}% / {g['Sharpe']:.2f} | {a['CAGR']:.1f}% / {a['Sharpe']:.2f} | {b['CAGR']:.1f}% / {b['Sharpe']:.2f} | {rt:.0f} | {g['CAGR']-a['CAGR']:.2f} |")
md['COST'] = "\n".join(cs)
buy, sell = side_costs(0.0001)
md['COSTUNIT'] = (f"Per side: brokerage {BROK*100:.4f}% + exchange {EXCH*100:.4f}% + SEBI {SEBI*100:.4f}% + 18% GST on those + slippage 0.0100%; stamp {STAMP*100:.4f}% on buys; STT on sells 0.017% (to Sep 2013), 0.010% (Oct 2013-Mar 2023), 0.0125% (Apr 2023-Sep 2024), 0.020% (from Oct 2024). Round trip today: {(buy[-1]+sell[-1])*100:.3f}% of notional; roll = {(buy[-1]+sell[-1]+ROLL_EXTRA)*100:.3f}%.")
# --- Expiry effect
exp_days = pd.DatetimeIndex(sorted({e for g in G.values() for e in g.index if e in set(days)})); pos_after = [days.get_loc(e) + 1 for e in exp_days if days.get_loc(e) + 1 < n]
mask1 = np.zeros(n, bool); mask1[pos_after] = True; m5 = np.zeros(n, bool)
for p in pos_after: m5[p:p + 5] = True
c1n, c1a, c5n, c5a = (oin > oin.shift(1)).values, (oia > oia.shift(1)).values, (oin > oin.shift(5)).values, (oia > oia.shift(5)).values
md['EXP'] = "\n".join(["| OI signal | 'OI rising' day after expiry | Other days | 5d-change 'rising' in 5 days after expiry | Other days |", "|---|---|---|---|---|",
    f"| Naive total OI | {100*c1n[mask1].mean():.0f}% | {100*c1n[~mask1].mean():.0f}% | {100*c5n[m5].mean():.0f}% | {100*c5n[~m5].mean():.0f}% |",
    f"| Expiry-adjusted OI | {100*c1a[mask1].mean():.0f}% | {100*c1a[~mask1].mean():.0f}% | {100*c5a[m5].mean():.0f}% | {100*c5a[~m5].mean():.0f}% |"])
md['EXPN'] = f"{len(pos_after)} monthly expiries in 2012-2026; naive total OI falls {100*(1-(oin[mask1].values/oin.shift(1)[mask1].values)).mean():.0f}% on average on the day after expiry"
# --- Look-ahead poison test
rng = np.random.default_rng(11); cuts = sorted(rng.choice(np.arange(400, n - 5), 10, replace=False)); bad = 0; chk = 0
allfam = [(nm, fn, df, ls) for nm, fn, df, _, hl in FAM for ls in ([False, True] if hl else [False])] + [(nm, fn, df, False) for nm, fn, df, _, hl, k in OIFAM]
for m_ in cuts:
    Dp = {k: v.copy() for k, v in D.items()}
    for k in Dp: Dp[k].iloc[m_ + 1:] = rng.uniform(0.2, 5, n - m_ - 1) * (Dp[k].iloc[m_] if abs(Dp[k].iloc[m_]) > 0 else 1.0)
    for nm, fn, df, ls in allfam:
        a = fn(D, **df, ls=ls).iloc[:m_ + 1].values; b = fn(Dp, **df, ls=ls).iloc[:m_ + 1].values; chk += 1
        if not np.allclose(np.nan_to_num(a), np.nan_to_num(b)): bad += 1
md['LOOK'] = f"Poison test: for {len(cuts)} random cut dates every price/VIX/OI value after the cut was replaced by random numbers; {chk} (strategy x cut) signals recomputed and compared up to the cut: {bad} mismatches. Position at day h equals signal at close h-1: {all(np.array_equal(r['pos'][1:], np.nan_to_num(r['sig'].values)[:-1]) for r in [HEAD, HEAD_NAIVE, TREND_ONLY])}."
# --- Regimes
c = D['c']; s200 = sma(c, 200)
LAB = {'Trend (price vs 200DMA)': pd.Series(np.where(s200.isna(), 'NA', np.where(c > s200, 'Bull', 'Bear')), index=days),
       'Volatility (India VIX)': pd.Series(np.where(D['vix'] < 15, 'Low <15', np.where(D['vix'] < 22, 'Mid 15-22', 'High >22')), index=days),
       'Momentum (20d return)': pd.Series(np.where(c.pct_change(20) > 0.03, 'Up >3%', np.where(c.pct_change(20) < -0.03, 'Down <-3%', 'Flat')), index=days),
       'Drawdown from high': pd.Series(np.where(c / c.cummax() - 1 < -0.10, 'DD >10%', 'Near high'), index=days)}
LAB = {k: v.shift(1).fillna('NA').astype(str).values for k, v in LAB.items()}
def regime_table(items, periods=('pre', 'valid', 'test')):
    out = ["| Regime | Period | Days | " + " | ".join(l for l, _ in items) + " |", "|---|---|---|" + "---|" * len(items)]
    for rs, lv in LAB.items():
        for g in [x for x in sorted(set(lv)) if x != 'NA']:
            for k in periods:
                i, j = IDX[k]; msk = lv[i:j] == g
                if msk.sum() == 0: continue
                cells = []
                for _, r in items:
                    x = pnl(r['pos'])[i:j][msk]; sd = x.std(ddof=1)
                    cells.append(f"{100*x.mean()*252:.1f}% (Sh {x.mean()/sd*np.sqrt(252) if sd>0 else 0:.1f})" if msk.sum() >= 30 else f"{100*x.mean()*252:.0f}%*")
                out.append(f"| {rs}: {g} | {k} | {msk.sum()} | " + " | ".join(cells) + " |")
    return "\n".join(out)
md['REG'] = regime_table([('Buy & Hold', BH), ('Trend(50)+rising OI (adj.)', HEAD), ('Trend(50) only', TREND_ONLY)] + [(t.replace(' [long-only]', ' LO')[:30], r) for t, r in LOCK])
# --- Deflated Sharpe on train+valid selection sample (2013-2023)
sr_all = np.array([t['sr_tv_daily'] for t in TRIALS]); V = sr_all.var(); g_ = 0.5772156649
SR0 = math.sqrt(V) * ((1 - g_) * ND.inv_cdf(1 - 1 / N_ALL) + g_ * ND.inv_cdf(1 - 1 / (N_ALL * math.e)))
def dsr(r):
    i, j = IDX['train'][0], IDX['valid'][1]; x = pnl(r['pos'])[i:j]; T = len(x); sr = x.mean() / x.std(ddof=1); z = (x - x.mean()) / x.std(ddof=1)
    sk, ku = (z ** 3).mean(), (z ** 4).mean(); return sr * np.sqrt(252), ND.cdf((sr - SR0) * math.sqrt(T - 1) / math.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2))
dl_ = ["| Strategy | Train+valid 2013-23 Sharpe | Deflated Sharpe prob. | Test Sharpe | Test CAGR |", "|---|---|---|---|---|"]
for l, r in fin[1:]:
    s_, p_ = dsr(r); dl_.append(f"| {l} | {s_:.2f} | {p_:.2f} | {r['m']['test']['Sharpe']:.2f} | {r['m']['test']['CAGR']:.1f}% |")
md['DSR'] = "\n".join(dl_); md['TRIALS'] = f"Configurations evaluated in this run: {NT}; earlier work on 2018-26 data: {PRIOR_TRIALS}; N for deflation = {N_ALL}. Expected best annualised Sharpe from luck alone over N trials on the 2013-23 selection sample: {SR0*np.sqrt(252):.2f}."
# --- post-hoc panic reversal
def b_vixspike(D, x, ls=False): v = D['vix']; return ((v / v.shift() - 1) > x).astype(float)
def b_dropup(D, nd, x, ls=False): c = D['c']; return ((c / c.shift(nd) - 1 < -x) & (c > sma(c, 200))).astype(float)
PH = {'VIX spike >12% (long 1 day)': evaluate('VIX spike >12%', b_vixspike, dict(x=0.12)), '10-day drop >2.5% in uptrend (long 1 day)': evaluate('10d drop uptrend', b_dropup, dict(nd=10, x=0.025))}
sig_pair = (PH['VIX spike >12% (long 1 day)']['sig'] + PH['10-day drop >2.5% in uptrend (long 1 day)']['sig']) / 2
PH['Pair (equal weight)'] = evaluate('Pair', lambda D, ls=False: sig_pair, {})
md['POSTHOC'] = HDR + "\n" + "\n".join(row(l, r) for l, r in PH.items())
md['REG_POSTHOC'] = regime_table([('Buy & Hold', BH), ('Pair (1x)', PH['Pair (equal weight)'])])
# --- 2013-17 only: yearly table for B&H, headline, trend-only
yr = ["| Year | Buy & Hold | Trend(50)+rising OI (adj.) | Trend(50)+rising OI (naive) | Trend(50) only | Pair |", "|---|---|---|---|---|---|"]
for Y in range(2013, 2027):
    a, b = sl(f'{Y}-01-01', f'{Y}-12-31'); cells = [f"{100*(np.prod(1+pnl(r['pos'])[a:b])-1):.1f}%" for r in [BH, HEAD, HEAD_NAIVE, TREND_ONLY, PH['Pair (equal weight)']]]
    yr.append(f"| {Y} | " + " | ".join(cells) + " |")
md['YEARS'] = "\n".join(yr)
md['ALLPOS'] = ', '.join(allpos) or 'none'; md['ALLBEAT'] = ', '.join(allbeat) or 'none'
md['SHORT'] = ', '.join(t for t, _ in short)
md['NDAYS'] = f"{n} trading days; {len(exp_days)} expiries"
json.dump(md, open('results/report_ext_tables.json', 'w'), indent=1)
pd.to_pickle({k: {kk: vv for kk, vv in v.items() if kk != 'sig'} for k, v in RES.items()}, 'results/report_ext_res.pkl')
for k in ['FZ', 'C', 'SWEEP', 'COST', 'EXP', 'EXPN', 'LOOK', 'DSR', 'TRIALS', 'POSTHOC', 'YEARS', 'ALLPOS', 'ALLBEAT', 'SHORT']: print('\n##', k); print(md[k])

# ---- Walk-forward re-tuning over the whole 2013-2026 history: each year Y trade the top-5 by trailing Sharpe (all candidates, data before Y only)
cand = {}
for k, r in RES.items():
    if k[0].startswith('Buy & Hold'): continue
    key = (k[0], str(r['params']), r['ls'])
    if key not in cand: cand[key] = r['ret']
y0 = IDX['pre'][0]; wf = np.zeros(n); msk = np.zeros(n, bool); wf_rows = ["| Year | Picked (top 3 of 5 by trailing Sharpe) | WF return | Buy & Hold |", "|---|---|---|---|"]
for Y in range(2015, 2027):
    a, b = sl(f'{Y}-01-01', f'{Y}-12-31'); sc = []
    for key, x in cand.items():
        h_ = x[y0:a]
        if np.mean(h_ != 0) < 0.02 or h_.std() == 0: continue
        sc.append((h_.mean() / h_.std(), key))
    top = [kk for _, kk in sorted(sc, reverse=True)[:5]]; wf[a:b] = np.mean([cand[t][a:b] for t in top], axis=0); msk[a:b] = True
    wf_rows.append(f"| {Y} | {'; '.join(t[0].split(' [')[0] + ' ' + t[1][:22] for t in top[:3])} | {100*(np.prod(1+wf[a:b])-1):.1f}% | {100*(np.prod(1+pnl(np.ones(n))[a:b])-1):.1f}% |")
bhx = pnl(np.ones(n)); pairx = PH['Pair (equal weight)']['ret']
ww = lambda x: met(x[msk]); md['WF'] = "\n".join(wf_rows)
md['WFSUM'] = "| Series (2015-2026, out-of-sample years only) | CAGR | Sharpe | MaxDD |\n|---|---|---|---|\n" + "\n".join(f"| {l} | {ww(x)['CAGR']:.1f}% | {ww(x)['Sharpe']:.2f} | {ww(x)['MaxDD']:.1f}% |" for l, x in [('Walk-forward top-5 (re-tuned yearly)', wf), ('Buy & Hold futures', bhx), ('Panic-reversal pair (post-hoc, fixed rules)', pairx)])
json.dump(md, open('results/report_ext_tables.json', 'w'), indent=1)
print('\n## WF'); print(md['WF']); print(md['WFSUM'])

# ======== Deep-dive: IBS mean-reversion (long when close is in the bottom of the day's range, exit when it recovers) ========
IBS = told['IBS mean-reversion']                                   # params frozen from the 2018-21 train only
print('\nIBS frozen params:', IBS['params'])
sw = ["| lo \\ hi | " + " | ".join(f"hi={h}" for h in [0.6, 0.7, 0.8, 0.9]) + " |", "|---|---|---|---|---|"]
for lo_ in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
    cells = []
    for hi_ in [0.6, 0.7, 0.8, 0.9]:
        r = evaluate('IBS grid', b_ibs, dict(lo=lo_, hi=hi_)); m = r['m']
        cells.append(f"Pre {m['pre']['CAGR']:.1f} / Val {m['valid']['CAGR']:.1f} / Te {m['test']['CAGR']:.1f}")
    sw.append(f"| lo={lo_} | " + " | ".join(cells) + " |")
md['IBSGRID'] = "\n".join(sw)
md['IBS'] = HDR + "\n" + row(f"IBS mean-reversion {IBS['params']} (frozen from 2018-21)", IBS) + "\n" + row('Buy & Hold futures', BH) + "\n" + row('Panic-reversal pair (post-hoc)', PH['Pair (equal weight)'])
ibsx = IBS['ret']; combo = 0.5 * ibsx + 0.5 * pairx
md['IBS_COMBO'] = "| Series | " + " | ".join(CN[c] for c in COLS) + " |\n|---|" + "---|" * len(COLS) + "\n" + "\n".join(
    f"| {l} | " + " | ".join(f"{met(x[IDX[c][0]:IDX[c][1]])['CAGR']:.1f} / {met(x[IDX[c][0]:IDX[c][1]])['Sharpe']:.2f} / {met(x[IDX[c][0]:IDX[c][1]])['MaxDD']:.1f}" for c in COLS) + " |"
    for l, x in [('IBS + Pair, 50/50', combo), ('IBS alone', ibsx), ('Buy & Hold', bhx)])
yr = ["| Year | Buy & Hold | IBS mean-reversion | Pair | IBS + Pair |", "|---|---|---|---|---|"]
for Y in range(2013, 2027):
    a, b = sl(f'{Y}-01-01', f'{Y}-12-31'); yr.append(f"| {Y} | " + " | ".join(f"{100*(np.prod(1+x[a:b])-1):.1f}%" for x in [bhx, ibsx, pairx, combo]) + " |")
md['IBS_YEARS'] = "\n".join(yr)
i_, j_ = IDX['full']; cst = ["| Slippage per side | Full-period CAGR / Sharpe / MaxDD | Round trips |", "|---|---|---|"]
for s_ in [0.0, 0.0001, 0.0003, 0.0005]:
    x = pnl(IBS['pos'], s_); m = met(x[i_:j_]); cst.append(f"| {s_*100:.2f}% | {m['CAGR']:.1f}% / {m['Sharpe']:.2f} / {m['MaxDD']:.1f}% | {IBS['m']['full']['Trades']/2:.0f} |")
md['IBS_COST'] = "\n".join(cst)
md['IBS_REG'] = regime_table([('Buy & Hold', BH), ('IBS mean-reversion', IBS), ('Pair', PH['Pair (equal weight)'])], periods=('pre', 'train_old', 'valid', 'test'))
s_, p_ = dsr(IBS); md['IBS_DSR'] = f"IBS: train+valid(2013-23) Sharpe {s_:.2f}, Deflated Sharpe probability {p_:.2f} (N={N_ALL})."
json.dump(md, open('results/report_ext_tables.json', 'w'), indent=1)
for k in ['IBS', 'IBSGRID', 'IBS_COMBO', 'IBS_YEARS', 'IBS_COST', 'IBS_DSR']: print('\n##', k); print(md[k])

# ---- Regime-conditioned IBS: only hold when India VIX (known at the signal close) >= threshold. Threshold 15 = the Low/Mid boundary fixed before this test (from the 2018-21 regime split).
ibs_sig = b_ibs(D, **IBS['params']); rows_ = ["| VIX filter | " + " | ".join(CN[c] for c in ['pre', 'train_old', 'valid', 'test', 'full']) + " | Exposure |", "|---|---|---|---|---|---|---|"]
FIL = {}
for thr in [None, 12, 14, 15, 16, 18, 20]:
    sg = ibs_sig if thr is None else ibs_sig.where(D['vix'] >= thr, 0.0)
    r = evaluate('IBS+VIX filter', lambda D, thr=None, ls=False, _s=sg: _s, {} if thr is None else dict(thr=thr)); FIL[thr] = r; m = r['m']
    rows_.append(f"| {'none (plain IBS)' if thr is None else 'VIX >= %d' % thr} | " + " | ".join(fmt(m, k) for k in ['pre', 'train_old', 'valid', 'test', 'full']) + f" | {m['full']['Exposure']:.0f}% |")
md['IBSVIX'] = "\n".join(rows_)
fx = FIL[15]['ret']; fcombo = 0.5 * fx + 0.5 * pairx
md['IBSVIX_COMBO'] = "| Series | " + " | ".join(CN[c] for c in COLS) + " |\n|---|" + "---|" * len(COLS) + "\n" + "\n".join(
    f"| {l} | " + " | ".join(f"{met(x[IDX[c][0]:IDX[c][1]])['CAGR']:.1f} / {met(x[IDX[c][0]:IDX[c][1]])['Sharpe']:.2f} / {met(x[IDX[c][0]:IDX[c][1]])['MaxDD']:.1f}" for c in COLS) + " |"
    for l, x in [('IBS (VIX>=15) + Pair, 50/50', fcombo), ('IBS (VIX>=15) alone', fx), ('Buy & Hold', bhx)])
yr = ["| Year | Buy & Hold | IBS plain | IBS (VIX>=15) |", "|---|---|---|---|"]
for Y in range(2013, 2027):
    a, b = sl(f'{Y}-01-01', f'{Y}-12-31'); yr.append(f"| {Y} | " + " | ".join(f"{100*(np.prod(1+x[a:b])-1):.1f}%" for x in [bhx, ibsx, fx]) + " |")
md['IBSVIX_YEARS'] = "\n".join(yr)
s_, p_ = dsr(FIL[15]); md['IBSVIX_DSR'] = f"IBS (VIX>=15): train+valid Sharpe {s_:.2f}, Deflated Sharpe probability {p_:.2f} (N={N_ALL + 7})."
md['IBSVIX_COST'] = "| Slippage per side | Full CAGR / Sharpe / MaxDD |\n|---|---|\n" + "\n".join(f"| {s*100:.2f}% | " + "{:.1f}% / {:.2f} / {:.1f}%".format(*[met(pnl(FIL[15]['pos'], s)[IDX['full'][0]:IDX['full'][1]])[k] for k in ['CAGR', 'Sharpe', 'MaxDD']]) + " |" for s in [0.0, 0.0001, 0.0003, 0.0005])
md['IBSVIX_RT'] = f"{FIL[15]['m']['full']['Trades']/2:.0f}"
json.dump(md, open('results/report_ext_tables.json', 'w'), indent=1)
for k in ['IBSVIX', 'IBSVIX_COMBO', 'IBSVIX_YEARS', 'IBSVIX_DSR', 'IBSVIX_COST', 'IBSVIX_RT']: print('\n##', k); print(md[k])
