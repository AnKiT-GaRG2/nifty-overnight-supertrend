"""Popular-strategy backtest on real NSE Nifty futures (daily, front-month, chained returns).
Train 2018-04..2021-12 | Valid 2022-01..2023-12 | Test 2024-01..2026-11 (first year of data = indicator warm-up for all strategies).
Signal at close t -> position earns close(t)->close(t+1). Costs 0.025%/side, 0.05% on a roll while positioned. No interest.
Two variants per family: 'default' (textbook params) and 'tuned' (grid, chosen on TRAIN Sharpe only).
Regimes use only information up to the previous close (no lookahead)."""
import itertools, numpy as np, pandas as pd
COST, ROLL = 0.00025, 0.0005
f = pd.read_csv('data/fut/nifty_fut.csv', parse_dates=['date', 'expiry']).drop_duplicates(['date', 'expiry'])
f = f[(f.open > 0) & (f.close > 0)].set_index(['date', 'expiry']).sort_index()
days = pd.DatetimeIndex(sorted(f.index.get_level_values(0).unique())); n = len(days)
ret = np.zeros(n); K = [None] * n; O = np.full(n, np.nan); H = O.copy(); L = O.copy(); C = O.copy(); rollf = np.zeros(n)
for i in range(1, n):
    t0, t1 = days[i - 1], days[i]
    ex0 = f.loc[t0].index; ex1 = f.loc[t1].index
    cand = [e for e in ex0 if e > t0 and e in ex1]
    k = min(cand); K[i] = k
    ret[i] = f.loc[(t1, k)].close / f.loc[(t0, k)].close - 1
    rollf[i] = float(K[i - 1] is not None and k != K[i - 1])
adjc = 100 * np.cumprod(1 + ret)
for i in range(1, n):
    r = f.loc[(days[i], K[i])]; s = adjc[i] / r.close; O[i], H[i], L[i], C[i] = r.open * s, r.high * s, r.low * s, adjc[i]
C[0] = 100.0; O[0] = H[0] = L[0] = 100.0
S = lambda a: pd.Series(a, index=days)
c, h, l, o = S(C), S(H), S(L), S(O)
vix = pd.read_csv('data/vix.csv', parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()
# ---------- indicators ----------
sma = lambda x, w: x.rolling(w).mean(); ema = lambda x, w: x.ewm(span=w, adjust=False).mean()
def rsi(x, w):
    d = x.diff(); up = d.clip(lower=0).ewm(alpha=1 / w, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / w, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))
def atr(w):
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1); return tr.ewm(alpha=1 / w, adjust=False).mean()
def supertrend(w, m):
    a = atr(w).values; hl = ((h + l) / 2).values; ub = hl + m * a; lb = hl - m * a; cl = c.values
    fu, fl, d = ub.copy(), lb.copy(), np.ones(n)
    for i in range(1, n):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or cl[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or cl[i - 1] < fl[i - 1]) else fl[i - 1]
        d[i] = 1 if (d[i - 1] == -1 and cl[i] > fu[i - 1]) else (-1 if (d[i - 1] == 1 and cl[i] < fl[i - 1]) else d[i - 1])
    return S(d)
def state(enter, exit_, lo=False):
    """stateful long (and short if lo) from boolean entry/exit series"""
    p = np.zeros(n); cur = 0.0; e, x = enter.fillna(False).values, exit_.fillna(False).values
    for i in range(n):
        if cur == 0 and e[i]: cur = 1.0
        elif cur == 1 and x[i]: cur = 0.0
        p[i] = cur
    return S(p)
def ls(sig, longshort): return sig if longshort else sig.clip(lower=0)
# ---------- strategy families: name -> (builder, default params, grid) ----------
def f_sma(a, b, lsf=False): return ls(np.sign(sma(c, a) - sma(c, b)).where(sma(c, b).notna(), 0), lsf)
def f_ema(a, b, lsf=False): return ls(np.sign(ema(c, a) - ema(c, b)).where(sma(c, b).notna(), 0), lsf)
def f_macd(a, b, s, lsf=False):
    m = ema(c, a) - ema(c, b); return ls(np.sign(m - ema(m, s)).where(sma(c, b).notna(), 0), lsf)
def f_rsi_mr(w, lo, hi, lsf=False):
    r = rsi(c, w); return state(r < lo, r > hi)
def f_rsi2(w, lo, hi, lsf=False):
    r = rsi(c, w); return state((r < lo) & (c > sma(c, 200)), (r > hi) | (c < sma(c, 200)) * 0)
def f_bb_mr(w, k, lsf=False):
    m, s = sma(c, w), c.rolling(w).std(); return state(c < m - k * s, c > m)
def f_bb_brk(w, k, lsf=False):
    m, s = sma(c, w), c.rolling(w).std(); return state(c > m + k * s, c < m)
def f_donch(en, ex, lsf=False):
    hi, lo = h.rolling(en).max().shift(), l.rolling(ex).min().shift(); return state(c > hi, c < lo)
def f_st(w, m, lsf=False): return ls(supertrend(w, m), lsf)
def f_200(w, lsf=False): return ls(np.sign(c - sma(c, w)).where(sma(c, w).notna(), 0), lsf)
def f_mom(w, lsf=False): return ls(np.sign(c / c.shift(w) - 1).fillna(0), lsf)
def f_mom121(w, lsf=False): return ls(np.sign(c.shift(21) / c.shift(w) - 1).fillna(0), lsf)
def f_adx(w, th, lsf=False):
    up, dn = h.diff(), -l.diff(); pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(w); pdi = 100 * S(pdm).ewm(alpha=1 / w, adjust=False).mean() / a; mdi = 100 * S(mdm).ewm(alpha=1 / w, adjust=False).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi); adx = dx.ewm(alpha=1 / w, adjust=False).mean()
    return ls(np.sign(pdi - mdi).where(adx > th, 0), lsf)
def f_stoch(w, lo, hi, lsf=False):
    k = 100 * (c - l.rolling(w).min()) / (h.rolling(w).max() - l.rolling(w).min()); k = k.rolling(3).mean(); return state(k < lo, k > hi)
def f_keltner(w, m, lsf=False):
    mid = ema(c, w); a = atr(w); return state(c > mid + m * a, c < mid)
def f_ibs(lo, hi, lsf=False):
    ibs = (c - l) / (h - l).replace(0, np.nan); return state(ibs < lo, ibs > hi)
def f_gap(th, lsf=False):  # buy after a close-to-close drop > th sigma (20d), exit next day
    r = c.pct_change(); z = r / r.rolling(20).std().shift(); return (z < -th).astype(float)
def f_golden_vix(w, v, lsf=False): return ((c > sma(c, w)) & (vix < v)).astype(float)
FAM = {
 'Buy & Hold':            (lambda lsf=False: S(np.ones(n)), {}, {}),
 'SMA cross 50/200':      (f_sma, dict(a=50, b=200), dict(a=[10, 20, 30, 50], b=[100, 150, 200])),
 'SMA cross 20/50':       (f_sma, dict(a=20, b=50), dict(a=[5, 10, 20], b=[30, 50, 80])),
 'EMA cross 12/26':       (f_ema, dict(a=12, b=26), dict(a=[5, 9, 12, 20], b=[21, 26, 50, 100])),
 'MACD 12/26/9':          (f_macd, dict(a=12, b=26, s=9), dict(a=[8, 12, 16], b=[21, 26, 40], s=[7, 9, 12])),
 'RSI(14) 30/50 MR':      (f_rsi_mr, dict(w=14, lo=30, hi=50), dict(w=[7, 14, 21], lo=[20, 25, 30, 35], hi=[50, 60, 70])),
 'Connors RSI(2) 10/70':  (f_rsi2, dict(w=2, lo=10, hi=70), dict(w=[2, 3, 4], lo=[5, 10, 15, 20], hi=[60, 70, 80])),
 'Bollinger MR (20,2)':   (f_bb_mr, dict(w=20, k=2.0), dict(w=[10, 20, 30], k=[1.5, 2.0, 2.5])),
 'Bollinger breakout':    (f_bb_brk, dict(w=20, k=2.0), dict(w=[10, 20, 30, 50], k=[1.0, 1.5, 2.0, 2.5])),
 'Donchian 20/10 (turtle)':(f_donch, dict(en=20, ex=10), dict(en=[20, 40, 55, 100], ex=[10, 20, 30])),
 'Donchian 55/20':        (f_donch, dict(en=55, ex=20), dict(en=[40, 55, 80, 120], ex=[10, 20, 40])),
 'Supertrend daily (10,3)':(f_st, dict(w=10, m=3.0), dict(w=[7, 10, 14, 20], m=[2.0, 2.5, 3.0, 4.0])),
 'Price>200DMA':          (f_200, dict(w=200), dict(w=[50, 100, 150, 200, 250])),
 'TS momentum 252d':      (f_mom, dict(w=252), dict(w=[21, 63, 126, 252])),
 'Momentum 12-1':         (f_mom121, dict(w=252), dict(w=[126, 189, 252])),
 'ADX/DI trend (14,25)':  (f_adx, dict(w=14, th=25), dict(w=[10, 14, 20], th=[15, 20, 25, 30])),
 'Stochastic MR (14,20/80)':(f_stoch, dict(w=14, lo=20, hi=80), dict(w=[9, 14, 21], lo=[10, 20, 30], hi=[70, 80, 90])),
 'Keltner breakout':      (f_keltner, dict(w=20, m=2.0), dict(w=[10, 20, 40], m=[1.0, 1.5, 2.0, 3.0])),
 'IBS mean reversion':    (f_ibs, dict(lo=0.2, hi=0.8), dict(lo=[0.1, 0.2, 0.3], hi=[0.6, 0.7, 0.8])),
 'Buy-the-dip (-1.5σ)':   (f_gap, dict(th=1.5), dict(th=[1.0, 1.5, 2.0, 2.5])),
 'Trend + low-VIX (200DMA, VIX<22)':(f_golden_vix, dict(w=200, v=22), dict(w=[100, 200], v=[16, 18, 22, 25])),
}
LS_FAMS = {'SMA cross 50/200', 'SMA cross 20/50', 'EMA cross 12/26', 'MACD 12/26/9', 'Supertrend daily (10,3)', 'Price>200DMA', 'TS momentum 252d', 'Momentum 12-1', 'ADX/DI trend (14,25)'}
# ---------- engine ----------
PER = {'train': ('2018-04-01', '2021-12-31'), 'valid': ('2022-01-01', '2023-12-31'), 'test': ('2024-01-01', '2026-12-31'), 'full': ('2018-04-01', '2026-12-31')}
def pnl(sig):
    p = sig.fillna(0).values.astype(float); held = np.r_[0.0, p[:-1]]; prev = np.r_[0.0, held[:-1]]
    return held * ret - np.abs(held - prev) * COST - np.abs(held) * ROLL * rollf, held
def met(r):
    r = np.asarray(r); m = len(r)
    if m < 20: return dict(CAGR=np.nan, Vol=np.nan, Sharpe=np.nan, MaxDD=np.nan, Calmar=np.nan)
    eq = np.cumprod(1 + r); yrs = m / 252; cagr = eq[-1] ** (1 / yrs) - 1; sd = r.std(ddof=1)
    dd = (eq / np.maximum.accumulate(np.r_[1, eq])[1:] - 1).min()
    return dict(CAGR=100 * cagr, Vol=100 * sd * np.sqrt(252), Sharpe=(r.mean() / sd * np.sqrt(252) if sd > 0 else 0), MaxDD=100 * dd, Calmar=(cagr / -dd if dd < 0 else np.nan))
def sl(a, b): return np.searchsorted(days.values, np.datetime64(a)), np.searchsorted(days.values, np.datetime64(b), side='right')
# ---------- regimes (known at previous close) ----------
sma200 = sma(c, 200); trend = np.where(c > sma200, 'Bull', 'Bear'); trend = np.where(sma200.isna(), 'NA', trend)
volr = np.where(vix < 15, 'LowVol(<15)', np.where(vix < 22, 'MidVol(15-22)', 'HighVol(>22)'))
r20 = c.pct_change(20); dirr = np.where(r20 > 0.03, 'Up20d>3%', np.where(r20 < -0.03, 'Down20d<-3%', 'Flat20d'))
dd_ = c / c.cummax() - 1; ddr = np.where(dd_ < -0.10, 'Drawdown>10%', 'Near-high')
REG = {'Trend (price vs 200DMA)': pd.Series(trend, index=days), 'Volatility (India VIX)': pd.Series(volr, index=days),
       'Momentum (20d return)': pd.Series(dirr, index=days), 'Drawdown state': pd.Series(ddr, index=days)}
REG = {k: v.shift(1) for k, v in REG.items()}              # label known at prior close, applies to day t's return
rows, reg_rows, curves = [], [], {}
def evaluate(name, variant, params, sig):
    r, held = pnl(sig); curves[(name, variant)] = r
    for per, (a, b) in PER.items():
        i, j = sl(a, b); m = met(r[i:j]); m['Exposure%'] = 100 * np.mean(np.abs(held[i:j]) > 0)
        m['Trades'] = int(np.sum(np.abs(np.diff(np.r_[0, held[i:j]])) > 0)); rows.append(dict(strategy=name, variant=variant, params=str(params), period=per, **m))
        if per == 'full': continue
        for rn, lab in REG.items():
            for L_ in sorted(set(lab.values[i:j]) - {'NA'}):
                msk = lab.values[i:j] == L_; x = r[i:j][msk]
                if len(x) < 10: continue
                sd = x.std(ddof=1); reg_rows.append(dict(strategy=name, variant=variant, period=per, regime_set=rn, regime=L_, days=len(x),
                    ann_ret=100 * x.mean() * 252, Sharpe=(x.mean() / sd * np.sqrt(252) if sd > 0 else 0), hit=100 * np.mean(x[np.abs(held[i:j][msk]) > 0] > 0) if (np.abs(held[i:j][msk]) > 0).any() else np.nan,
                    exposure=100 * np.mean(np.abs(held[i:j][msk]) > 0)))
ti, tj = sl(*PER['train'])
for name, (fn, dflt, grid) in FAM.items():
    lsopts = [False, True] if name in LS_FAMS else [False]
    for lsf in lsopts:
        tag = name + (' [L/S]' if lsf else (' [long-only]' if name in LS_FAMS else ''))
        kw = {'lsf': lsf} if name != 'Buy & Hold' else {}
        evaluate(tag, 'default', dflt, fn(**dflt, **kw))
        if grid:
            best = None
            for vals in itertools.product(*grid.values()):
                P = dict(zip(grid.keys(), vals))
                if 'a' in P and 'b' in P and P['a'] >= P['b']: continue
                try: s = fn(**P, **kw)
                except Exception: continue
                m = met(pnl(s)[0][ti:tj])
                if np.isnan(m['Sharpe']): continue
                if best is None or m['Sharpe'] > best[0]: best = (m['Sharpe'], P, s)
            if best: evaluate(tag, 'tuned', best[1], best[2])
R = pd.DataFrame(rows); G = pd.DataFrame(reg_rows)
R.to_csv('results/zoo_summary.csv', index=False); G.to_csv('results/zoo_regimes.csv', index=False)
pd.to_pickle(curves, 'results/zoo_curves.pkl')
print('done', len(R), len(G))
