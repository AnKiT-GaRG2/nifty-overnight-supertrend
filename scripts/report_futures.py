"""Futures-only strategy report (Nifty index futures, NSE bhavcopy). Everything is priced on real futures contracts.
Execution: signal from data up to close t (incl. same-day OI, published after the close) -> trade at the OPEN of t+1 -> hold open->open on the same contract.
Costs per side: brokerage, STT (sell, date-dependent), exchange, SEBI, GST, stamp (buy), slippage; roll = sell near + buy far + extra spread.
Protocol (frozen before looking at test): train 2018-04..2021-12 | valid 2022-01..2023-12 | test 2024-01..2026-11. Params tuned on TRAIN only; shortlist by TRAIN+VALID; test shown once."""
import itertools, math, sys, json
import numpy as np, pandas as pd
from statistics import NormalDist
ND = NormalDist(); TRIALS = []                       # every (strategy, params) evaluated is logged here
# ------------------------------------------------------------------ data
f = pd.read_csv('data/fut/nifty_fut.csv', parse_dates=['date', 'expiry']).drop_duplicates(['date', 'expiry'])
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
vix = pd.read_csv('data/vix.csv', parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()
D = dict(c=S(adjc), h=S(Hh), l=S(Ll), vix=vix, oin=oin, oia=oia)
# ------------------------------------------------------------------ costs (fractions of notional per side)
BROK, EXCH, SEBI, STAMP = 0.000012, 0.000019, 0.000001, 0.00002
def stt(d): return np.where(d < pd.Timestamp('2023-04-01'), 0.0001, np.where(d < pd.Timestamp('2024-10-01'), 0.000125, 0.0002))
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
PER = {'train': ('2018-04-01', '2021-12-31'), 'valid': ('2022-01-01', '2023-12-31'), 'test': ('2024-01-01', '2026-12-31')}
sl = lambda a, b: (int(np.searchsorted(days.values, np.datetime64(a))), int(np.searchsorted(days.values, np.datetime64(b), side='right')))
IDX = {k: sl(*v) for k, v in PER.items()}; IDX['full'] = (IDX['train'][0], IDX['test'][1] - 1)
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
            best = None
            for vals in itertools.product(*grid.values()):
                P = dict(zip(grid.keys(), vals))
                if 'a' in P and 'b' in P and P['a'] >= P['b']: continue
                res = evaluate(tag, fn, P, L); RES[(tag, 'grid', str(P))] = res
                sh = res['m']['train']['Sharpe']
                if best is None or sh > best[0]: best = (sh, res)
            if best: RES[(tag, 'tuned')] = best[1]
for fam in FAM: run_family(*fam)
for fam in OIFAM: run_family(*fam[:5])
NT = len(TRIALS); print('strategy/param configurations evaluated in this report:', NT)

# ================================================================== PART 2: analysis, tests, tables
PRIOR_TRIALS = 2031                                   # earlier exploratory runs on the same data (zoo grid ~347, profit_search 303, research2 1381); all saw the test period
N_ALL = NT + PRIOR_TRIALS
BH = RES[('Buy & Hold futures', 'default')]; bhm = BH['m']
def fmt(m, k): return f"{m[k]['CAGR']:.1f} / {m[k]['Sharpe']:.2f} / {m[k]['MaxDD']:.1f}"
def beats(m, k): return (m[k]['CAGR'] > bhm[k]['CAGR']) and (m[k]['Sharpe'] > bhm[k]['Sharpe']) and (m[k]['MaxDD'] > bhm[k]['MaxDD'])
def row(label, res): m = res['m']; return f"| {label} | {fmt(m,'train')} | {fmt(m,'valid')} | {fmt(m,'test')} | {fmt(m,'full')} | {m['full']['Exposure']:.0f}% |"
HDR = "| Strategy | Train CAGR/Sharpe/MaxDD | Valid | Test | Full | Exposure |\n|---|---|---|---|---|---|"
md = {}
# ---- Table A: defaults (no fitting at all)
tags = sorted({k[0] for k in RES if k[1] == 'default'}, key=lambda t: -RES[(t, 'default')]['m']['train']['Sharpe'])
md['A'] = HDR + "\n" + "\n".join(row(t, RES[(t, 'default')]) for t in tags)
# ---- Table B: tuned on train only
tuned = {k[0]: RES[k] for k in RES if k[1] == 'tuned'}
md['B'] = HDR.replace('| Strategy', '| Strategy (params chosen on TRAIN)') + "\n" + "\n".join(row(f"{t} {tuned[t]['params']}", tuned[t]) for t in sorted(tuned, key=lambda t: -tuned[t]['m']['train']['Sharpe']))
# ---- shortlist rule (train+valid only), freeze, then show test
pool = [(t, r) for t, r in tuned.items() if not t.startswith('Buy & Hold') and r['m']['train']['Exposure'] > 5]
short = sorted([(t, r) for t, r in pool if r['m']['train']['Sharpe'] > 0.5 and r['m']['valid']['Sharpe'] > 0.5 and r['m']['train']['CAGR'] > 0 and r['m']['valid']['CAGR'] > 0],
               key=lambda x: -min(x[1]['m']['train']['Sharpe'], x[1]['m']['valid']['Sharpe']))
LOCK = short[:3]
print('SHORTLIST (train&valid Sharpe>0.5):', [t for t, _ in short]); print('LOCKED:', [(t, r['params']) for t, r in LOCK])
# ---- user's headline strategy
HEAD = RES[('Trend(N)+OI chg5 [expiry-adj OI]', 'default')]; HEAD_NAIVE = RES[('Trend(N)+OI chg5 [naive OI]', 'default')]; TREND_ONLY = RES[('Trend(50) only [no OI]', 'default')]
fin = [('Buy & Hold futures', BH), ('Trend(50)+rising OI (5d), expiry-adjusted OI', HEAD), ('Trend(50)+rising OI (5d), naive OI', HEAD_NAIVE), ('Trend(50) only (no OI)', TREND_ONLY)] + [(f"LOCKED: {t} {r['params']}", r) for t, r in LOCK]
md['C'] = HDR + "\n" + "\n".join(row(l, r) for l, r in fin)
# ---- Param sweep for the OI family + trend-only
sw = ["| Variant | N | Train CAGR/Sh/DD | Valid | Test | Beats B&H (T/V/Te)? |", "|---|---|---|---|---|---|"]
for lab in [f'Trend(N)+OI {h} [{l}]' for h in OI_HOW for l in ['expiry-adj OI', 'naive OI']] + ['Trend(50) only [no OI]']:
    for N in [30, 40, 50, 60, 80]:
        r = RES[(lab, 'grid', str(dict(N=N) if lab.startswith('Trend(N)') else dict(w=N)))]; m = r['m']
        sw.append(f"| {lab} | {N} | {fmt(m,'train')} | {fmt(m,'valid')} | {fmt(m,'test')} | {'Y' if beats(m,'train') else 'n'}/{'Y' if beats(m,'valid') else 'n'}/{'Y' if beats(m,'test') else 'n'} |")
md['SWEEP'] = "\n".join(sw)
# ---- Costs
fr = lambda r, s=0.0001, g=False: pnl(r['pos'], s, g)
cs = ["| Strategy | Gross (no costs) full | Net, slippage 0.01%/side full | Net, slippage 0.03%/side full | Round-trips (full) | Cost drag %/yr |", "|---|---|---|---|---|---|"]
for l, r in fin:
    i, j = IDX['full']; g = met(fr(r, g=True)[i:j]); a = met(fr(r)[i:j]); b = met(fr(r, 0.0003)[i:j]); rt = r['m']['full']['Trades'] / 2
    cs.append(f"| {l} | {g['CAGR']:.1f}% / {g['Sharpe']:.2f} | {a['CAGR']:.1f}% / {a['Sharpe']:.2f} | {b['CAGR']:.1f}% / {b['Sharpe']:.2f} | {rt:.0f} | {g['CAGR']-a['CAGR']:.2f} |")
md['COST'] = "\n".join(cs)
buy, sell = side_costs(0.0001); md['COSTUNIT'] = (f"Per side (fraction of notional): brokerage {BROK*100:.4f}% + exchange {EXCH*100:.4f}% + SEBI {SEBI*100:.4f}% + GST 18% on those + slippage 0.0100%; stamp {STAMP*100:.4f}% on buys; STT on sells 0.010% (to Mar 2023), 0.0125% (Apr 2023-Sep 2024), 0.020% (from Oct 2024). "
    f"Round trip today (STT 0.02%): {(buy[-1]+sell[-1])*100:.3f}% of notional (about {(buy[-1]+sell[-1])*24000:.1f} index points at 24,000). Rolling a held position costs one extra round trip + 0.01% spread = {(buy[-1]+sell[-1]+ROLL_EXTRA)*100:.3f}%.")
# ---- Expiry effect on OI
exp_days = pd.DatetimeIndex(sorted({e for g in G.values() for e in g.index if e in set(days)})); pos_after = [days.get_loc(e) + 1 for e in exp_days if days.get_loc(e) + 1 < n]
mask1 = np.zeros(n, bool); mask1[pos_after] = True
chg1n = (oin > oin.shift(1)).values; chg1a = (oia > oia.shift(1)).values; chg5n = (oin > oin.shift(5)).values; chg5a = (oia > oia.shift(5)).values
m5 = np.zeros(n, bool)
for p in pos_after: m5[p:p + 5] = True
ex = ["| OI signal | Share 'OI rising' on first day after expiry | Share on all other days | Share 'rising' in 5 days after expiry (5d change) | Share on other days |", "|---|---|---|---|---|"]
ex.append(f"| Naive total OI | {100*chg1n[mask1].mean():.0f}% | {100*chg1n[~mask1].mean():.0f}% | {100*chg5n[m5].mean():.0f}% | {100*chg5n[~m5].mean():.0f}% |")
ex.append(f"| Expiry-adjusted OI | {100*chg1a[mask1].mean():.0f}% | {100*chg1a[~mask1].mean():.0f}% | {100*chg5a[m5].mean():.0f}% | {100*chg5a[~m5].mean():.0f}% |")
md['EXP'] = "\n".join(ex); md['EXPN'] = f"{len(pos_after)} monthly expiries; naive total OI falls by {100*(1-(oin.shift(-0)[mask1].values/oin.shift(1)[mask1].values)).mean():.0f}% on average on the day after expiry"
md['EXPDIFF'] = f"Headline strategy: days where naive and adjusted signals differ: {int((HEAD['sig'].values!=HEAD_NAIVE['sig'].values).sum())} of {n}."
# ---- Look-ahead tests
rng = np.random.default_rng(7); cuts = sorted(rng.choice(np.arange(400, n - 5), 12, replace=False)); bad = 0; checked = 0
allfam = [(nm, fn, df, ls) for nm, fn, df, _, hl in FAM for ls in ([False, True] if hl else [False])] + [(nm, fn, df, False) for nm, fn, df, _, hl, k in OIFAM]
for m_ in cuts:
    Dp = {k: v.copy() for k, v in D.items()}
    for k in Dp: Dp[k].iloc[m_ + 1:] = rng.uniform(0.2, 5, n - m_ - 1) * (Dp[k].iloc[m_] if abs(Dp[k].iloc[m_]) > 0 else 1.0)       # poison every series after the cut
    for nm, fn, df, ls in allfam:
        a = fn(D, **df, ls=ls).iloc[:m_ + 1].values; b = fn(Dp, **df, ls=ls).iloc[:m_ + 1].values; checked += 1
        if not np.allclose(np.nan_to_num(a), np.nan_to_num(b)): bad += 1
pos_ok = all(np.array_equal(r['pos'][1:], np.nan_to_num(r['sig'].values)[:-1]) for r in [HEAD, HEAD_NAIVE, TREND_ONLY])
md['LOOK'] = f"Poison test: for {len(cuts)} random cut dates, every price/VIX/OI value after the cut was replaced by random numbers; {checked} (strategy x cut) signals were recomputed and compared up to the cut: {bad} mismatches. Position at day h equals signal at close h-1 (fills at the next open): {pos_ok}."
# ---- Regimes (labels known at previous close, applied to the holding day)
c = D['c']; s200 = sma(c, 200)
LAB = {'Trend (price vs 200DMA)': pd.Series(np.where(s200.isna(), 'NA', np.where(c > s200, 'Bull', 'Bear')), index=days),
       'Volatility (India VIX)': pd.Series(np.where(D['vix'] < 15, 'Low <15', np.where(D['vix'] < 22, 'Mid 15-22', 'High >22')), index=days),
       'Momentum (20d return)': pd.Series(np.where(c.pct_change(20) > 0.03, 'Up >3%', np.where(c.pct_change(20) < -0.03, 'Down <-3%', 'Flat')), index=days),
       'Drawdown from high': pd.Series(np.where(c / c.cummax() - 1 < -0.10, 'DD >10%', 'Near high'), index=days)}
LAB = {k: v.shift(1).fillna('NA').astype(str).values for k, v in LAB.items()}
def regime_table(items):
    out = ["| Regime | Period | Days | " + " | ".join(l for l, _ in items) + " |", "|---|---|---|" + "---|" * len(items)]
    for rs, lv in LAB.items():
        for g in [x for x in sorted(set(lv)) if x != 'NA']:
            for k in ['train', 'valid', 'test']:
                i, j = IDX[k]; msk = lv[i:j] == g
                if msk.sum() == 0: continue
                cells = []
                for _, r in items:
                    x = pnl(r['pos'])[i:j][msk]; sd = x.std(ddof=1)
                    cells.append(f"{100*x.mean()*252:.1f}% (Sh {x.mean()/sd*np.sqrt(252) if sd>0 else 0:.1f})" if msk.sum() >= 30 else f"{100*x.mean()*252:.0f}%*")
                out.append(f"| {rs}: {g} | {k} | {msk.sum()} | " + " | ".join(cells) + " |")
    return "\n".join(out)
md['REG'] = regime_table([('Buy & Hold', BH), ('Trend(50)+rising OI (adj.)', HEAD), ('Trend(50) only', TREND_ONLY)] + [(t.replace(' [long-only]', ' LO')[:34], r) for t, r in LOCK])
# ---- Overfitting accounting: Deflated Sharpe for the headline + locked strategies (selection sample = train+valid)
sr_all = np.array([t['sr_tv_daily'] for t in TRIALS]); V = sr_all.var(); g_ = 0.5772156649
SR0 = math.sqrt(V) * ((1 - g_) * ND.inv_cdf(1 - 1 / N_ALL) + g_ * ND.inv_cdf(1 - 1 / (N_ALL * math.e)))
def dsr(r):
    i, j = IDX['train'][0], IDX['valid'][1]; x = pnl(r['pos'])[i:j]; T = len(x); sr = x.mean() / x.std(ddof=1); z = (x - x.mean()) / x.std(ddof=1)
    sk, ku = (z ** 3).mean(), (z ** 4).mean(); return sr * np.sqrt(252), ND.cdf((sr - SR0) * math.sqrt(T - 1) / math.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2))
dl_ = ["| Strategy | Train+valid Sharpe (ann.) | Deflated Sharpe prob. (true Sharpe > 0 after N trials) | Test Sharpe (ann.) | Test CAGR |", "|---|---|---|---|---|"]
for l, r in fin[1:]:
    s_, p_ = dsr(r); dl_.append(f"| {l} | {s_:.2f} | {p_:.2f} | {r['m']['test']['Sharpe']:.2f} | {r['m']['test']['CAGR']:.1f}% |")
md['DSR'] = "\n".join(dl_); md['TRIALS'] = (f"Configurations evaluated in this report: {NT} (each family's default plus its parameter grid, long-only and long/short). Earlier exploratory runs on the same data (price-only signals, ~{PRIOR_TRIALS} configurations) also saw the test period, "
    f"so N for deflation = {N_ALL}. Expected best Sharpe from pure luck over N={N_ALL} trials on the train+valid sample: {SR0*np.sqrt(252):.2f} (annualised).")
# ---- "beats buy & hold" scoreboard over all tuned/default strategies
sb = ["| Strategy | beats B&H on CAGR+Sharpe+MaxDD: Train | Valid | Test | Positive CAGR: Train/Valid/Test |", "|---|---|---|---|---|"]
for t in sorted(tuned):
    if t.startswith('Buy & Hold'): continue
    m = tuned[t]['m']; sb.append(f"| {t} | {'Y' if beats(m,'train') else 'n'} | {'Y' if beats(m,'valid') else 'n'} | {'Y' if beats(m,'test') else 'n'} | {'+' if m['train']['CAGR']>0 else '-'}/{'+' if m['valid']['CAGR']>0 else '-'}/{'+' if m['test']['CAGR']>0 else '-'} |")
md['SCORE'] = "\n".join(sb)
json.dump(md, open('results/report_tables.json', 'w'), indent=1)
pd.to_pickle(dict(RES={k: {kk: vv for kk, vv in v.items() if kk != 'sig'} for k, v in RES.items()}), 'results/report_res.pkl')
for k in ['C', 'SWEEP', 'COST', 'COSTUNIT', 'EXP', 'EXPN', 'EXPDIFF', 'LOOK', 'DSR', 'TRIALS']: print('\n##', k); print(md[k])

# ---- POST-HOC section (ideas found earlier with test knowledge; re-run under this report's stricter next-open execution)
def b_vixspike(D, x, ls=False): v = D['vix']; return ((v / v.shift() - 1) > x).astype(float)
def b_dropup(D, nd, x, ls=False): c = D['c']; return ((c / c.shift(nd) - 1 < -x) & (c > sma(c, 200))).astype(float)
PH = {'VIX spike >12% (long 1 day)': evaluate('VIX spike >12%', b_vixspike, dict(x=0.12)),
      '10-day drop >2.5% in uptrend (long 1 day)': evaluate('10d drop uptrend', b_dropup, dict(nd=10, x=0.025))}
sig_pair = (PH['VIX spike >12% (long 1 day)']['sig'] + PH['10-day drop >2.5% in uptrend (long 1 day)']['sig']) / 2
PH['Pair (equal weight)'] = evaluate('Pair', lambda D, ls=False: sig_pair, {})
PH5 = dict(PH['Pair (equal weight)']); PH5['pos'] = PH['Pair (equal weight)']['pos'] * 5
rows_ = []
for l, r in list(PH.items()) + [('Pair at 5x notional', None)]:
    if r is None:
        x = pnl(PH5['pos']); m = {k: {**met(x[i:j]), 'Exposure': 100 * np.mean(np.abs(PH5['pos'][i:j]) > 0)} for k, (i, j) in IDX.items()}; r = dict(m=m)
    rows_.append(row(l, r))
md['POSTHOC'] = HDR + "\n" + "\n".join(rows_)
md['REG_POSTHOC'] = regime_table([('Buy & Hold', BH), ('Pair (1x)', PH['Pair (equal weight)'])])
json.dump(md, open('results/report_tables.json', 'w'), indent=1)
for k in ['A', 'B', 'SCORE', 'POSTHOC']: print('\n##', k); print(md[k])
print('\n## REG'); print(md['REG']); print('\n## REG_POSTHOC'); print(md['REG_POSTHOC'])
