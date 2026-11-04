"""Roadmap Phase 5: the locked test, walk-forward, stress tests, statistics, lookahead tests, deliverables.
Opens the 2024-01..2026-10 test window ONCE (results/rm/test_opened.json); a second run is refused unless REOPEN=1 (logged as burned).
Run: <venv>/bin/python scripts/rm_final.py"""
import os, sys, json, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rm_ideas import *
from rm_phase4 import risk_arrays
from scipy.stats import norm, skew, kurtosis
from itertools import combinations

SPEC = json.load(open(f'{RES}/FROZEN_SPEC.json'))
PSET = [60, 70, 80, 90]; KSET = [2.0, 2.5, 3.0]

def strat(E, S, p, k, cost='floor', delay=0, tv=None, dl=0.0, dd=False, ds=None):
    t, _ = S.B2(p, 'high'); ts, sd = risk_arrays(E, S, k, tv)
    return E.run(t, ts, sd, cost=cost, risk=0.0075, min_chg=2, delay=delay, dl_lim=dl, dd_brake=dd)

def base(E, S, cost='floor', delay=0):
    t, s = S.baseline(); return E.run(t, s, cost=cost, delay=delay)

def md(df, floatfmt='{:.3f}'):
    cols = list(df.columns); L = ['| ' + ' | '.join([''] + [str(c) for c in cols]) + ' |', '|' + '---|' * (len(cols) + 1)]
    for i, r in df.iterrows():
        L.append('| ' + ' | '.join([str(i)] + [(floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v)) for v in r.values]) + ' |')
    return '\n'.join(L)

def row(m, keys=('CAGR', 'MaxDD', 'Sharpe', 'Sortino', 'Calmar', 'Vol', 'TradesPerYr', 'WinRate', 'AvgWin/AvgLoss', 'TimeInMkt', 'CostDrag%/yr', 'LongLegCAGR', 'ShortLegCAGR')):
    return {k: m.get(k, np.nan) for k in keys}

def pct_df(df):
    d = df.copy()
    for c in ('CAGR', 'MaxDD', 'Vol', 'WinRate', 'TimeInMkt', 'LongLegCAGR', 'ShortLegCAGR'):
        if c in d: d[c] = d[c].map(lambda v: f'{v:.1%}' if v == v else 'na')
    return d

def stitched(Rd, folds, interest=True):
    """Rd: dict fold -> Result; returns stitched (total, excess) OOS series"""
    parts_t, parts_e = [], []
    for (a, z), R in zip(folds, Rd):
        parts_t.append(R.series(True).loc[a:z]); parts_e.append(pd.Series(R.net_d, index=R.E.days).loc[a:z])
    return pd.concat(parts_t), pd.concat(parts_e)

def wf_folds(first_oos='2020-04-01', end='2026-10-31'):
    out = []; a = pd.Timestamp(first_oos)
    while a <= pd.Timestamp(end):
        z = min(a + pd.DateOffset(months=6) - pd.Timedelta(days=1), pd.Timestamp(end)); tr0 = a - pd.DateOffset(years=3); tr1 = a - pd.Timedelta(days=1)
        out.append(((str(a.date()), str(z.date())), (str(tr0.date()), str(tr1.date())))); a = a + pd.DateOffset(months=6)
    return out

def block_boot(d, B=4000, L=20, seed=1):
    """d: daily excess-return difference (strategy - baseline) -> CI on the Sharpe-difference proxy: annualised mean/std of the strategy and baseline must be
    resampled jointly, so pass a DataFrame with two columns"""
    rs = np.random.RandomState(seed); n = len(d); X = d.values; out = []
    nb = int(np.ceil(n / L))
    for _ in range(B):
        st = rs.randint(0, n - L + 1, nb); idx = (st[:, None] + np.arange(L)).ravel()[:n]; x = X[idx]
        sh = x.mean(0) / x.std(0) * np.sqrt(252); out.append(sh[0] - sh[1])
    return np.percentile(out, [2.5, 50, 97.5])

def pbo_cscv(M, S=10):
    """M: T x N daily returns of the candidate set. Combinatorially symmetric CV, S even partitions."""
    T, N = M.shape; parts = np.array_split(np.arange(T), S); logits = []
    sr = lambda x: x.mean(0) / (x.std(0) + 1e-12)
    for comb in combinations(range(S), S // 2):
        tr = np.concatenate([parts[i] for i in comb]); te = np.concatenate([parts[i] for i in range(S) if i not in comb])
        best = np.argmax(sr(M[tr])); r = sr(M[te]); rank = (r < r[best]).sum() / (N - 1)   # relative OOS rank of the IS winner
        rank = min(max(rank, 1e-3), 1 - 1e-3); logits.append(np.log(rank / (1 - rank)))
    return float(np.mean(np.array(logits) <= 0))

def dsr(x, trial_sharpes_daily, N):
    sr = x.mean() / x.std(); T = len(x); g = 0.5772156649
    sr0 = np.sqrt(np.var(trial_sharpes_daily)) * ((1 - g) * norm.ppf(1 - 1.0 / N) + g * norm.ppf(1 - 1.0 / (N * np.e)))
    sk = skew(x); ku = kurtosis(x, fisher=False)
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2)
    return float(norm.cdf(z)), float(sr0 * np.sqrt(252)), float(sr * np.sqrt(252))


import copy
def anchored_engine(E, fut):
    """Same bars, but every session's open and close are pinned to the REAL futures open/close (NSE bhavcopy, held contract); intraday path = spot path,
    offset interpolated linearly through the session. Overnight gaps then equal real futures gaps."""
    E2 = copy.copy(E); D = E.D; nd = len(D)
    do = np.zeros(nd); dc = np.zeros(nd); has = np.zeros(nd, bool)
    first_idx = np.where(E.first_b)[0]; last_idx = np.where(E.last_b)[0]
    for i in range(nd):
        key = (D.index[i], D['held'].iloc[i])
        if key in fut.index:
            r = fut.loc[key]; do[i] = r['open'] - E.fo[first_idx[i]]; dc[i] = r['close'] - E.fc[last_idx[i]]; has[i] = True
    f0 = ((E.hhmm - 555) / 375.0); f1 = f0 + 15 / 375.0; dcode = E.day_codes
    off = lambda f: do[dcode] + (dc[dcode] - do[dcode]) * f
    fo = E.fo + off(f0); fc = E.fc + off(f1); mid = off((f0 + f1) / 2)
    fh = np.maximum(E.fh + mid, np.maximum(fo, fc)); fl = np.minimum(E.fl + mid, np.minimum(fo, fc))
    m1 = E.ds['m1']; mdc = pd.Index(D.index).get_indexer(m1['date'].values); mf = np.asarray((m1.index.hour * 60 + m1.index.minute) - 555) / 375.0
    moff = do[mdc] + (dc[mdc] - do[mdc]) * mf
    E2.fo, E2.fc, E2.fh, E2.fl = fo, fc, fh, fl
    E2.mo, E2.mc, E2.mh, E2.ml = E.mo + moff, E.mc + moff, E.mh + moff, E.ml + moff
    prev = np.r_[fc[0], fc[:-1]].copy()
    for i in range(1, nd):
        t = first_idx[i]; key = (D.index[i - 1], D['held'].iloc[i])
        prev[t] = fut.loc[key, 'close'] if key in fut.index else E.prev[t] + dc[i - 1] * 0.0 + (fc[t - 1] - E.fc[t - 1])
    prev[0] = fo[0]; E2.prev = prev
    return E2, float(has.mean())

def bh(E, cost='floor'):
    return E.run(np.ones(E.N, np.int8), np.ones(E.N), cost=cost, rebal=True)

def regime_table(E, S, Rs, wins):
    D = S.D; c = pd.Series(D['close'].values, index=D.index); sma = c.rolling(200).mean().shift(1); pc = c.shift(1)
    up = (pc > sma).values; vp = S._vixpct()
    # per-day (bar-0) prior-day VIX percentile
    first = np.where(E.first_b)[0]; vd = vp[first]; high = vd > 80
    rows = {}
    for w, wn in wins:
        a, z = SPLITS[w]; m = (E.days >= pd.Timestamp(a)) & (E.days <= pd.Timestamp(z)); yrs = m.sum() / 252
        for rn, rm in (('all days', np.ones(len(E.days), bool)), ('uptrend (>200DMA)', up), ('downtrend (<200DMA)', ~up), ('high VIX (pct>80)', high), ('normal VIX', ~high)):
            mm = m & rm
            if mm.sum() < 10: continue
            for nm_, R in Rs.items():
                ex = pd.Series(R.net_d, index=E.days)[mm]
                rows[(f'{wn} — {rn}', nm_)] = dict(days=int(mm.sum()), ann_return=ex.sum() / yrs, ann_sharpe=ex.mean() / ex.std() * np.sqrt(252) if ex.std() > 0 else np.nan)
    df = pd.DataFrame(rows).T; df.index = [f'{a} — {b}' for a, b in df.index]; df['ann_return'] = df['ann_return'].map(lambda v: f'{v:.1%}')
    return df

def lookahead_tests(E, S, ds, p, k, rep):
    """truncation, extra delay, shuffled future on the frozen strategy signals/P&L"""
    out = {}
    t, ts = S.B2(p, 'high'); _, sd = risk_arrays(E, S, k)
    rs = np.random.RandomState(11); D = E.days
    cut_days = [D[i] for i in rs.choice(np.arange(600, len(D) - 50), 3, replace=False)]
    for dday in cut_days:
        # ---- truncation: signals on data up to (excluding) dday equal to signals on full data before dday
        m1 = ds['m1']; b = ds['b15']; Dd = ds['daily']
        ds2 = dict(m1=m1[m1['date'] < dday], b15=b[b['date'] < dday], daily=Dd[Dd.index < dday], flags=ds['flags'], rq=ds['rq'], validation=ds['validation'])
        E2 = Engine(ds2); S2 = make_sig(E2); t2, ts2 = S2.B2(p, 'high'); _, sd2 = risk_arrays(E2, S2, k); n2 = E2.N
        same_dir = bool((t2 == t[:n2]).all()); same_sz = bool(np.allclose(ts2, ts[:n2])) and bool(np.allclose(sd2, sd[:n2], equal_nan=True))
        # also baseline Supertrend signal
        tb2, _ = S2.baseline(); tb, _ = S.baseline(); same_b = bool((tb2 == tb[:n2]).all())
        # ---- shuffled future: permute bars/minutes/daily rows after dday; everything before dday must not change
        rs2 = np.random.RandomState(5)
        b3 = b.copy(); fut = np.where(b3['date'] >= dday)[0]; perm = rs2.permutation(fut)
        for c in ('open', 'high', 'low', 'close'): b3.iloc[fut, b3.columns.get_loc(c)] = b3[c].values[perm]
        m3 = m1.copy(); fm = np.where(m3['date'] >= dday)[0]; pm = rs2.permutation(fm)
        for c in ('open', 'high', 'low', 'close'): m3.iloc[fm, m3.columns.get_loc(c)] = m3[c].values[pm]
        D3 = Dd.copy(); fd = np.where(D3.index >= dday)[0]; pdx = rs2.permutation(fd)
        for c in ('open', 'high', 'low', 'close'): D3.iloc[fd, D3.columns.get_loc(c)] = D3[c].values[pdx]
        ds3 = dict(m1=m3, b15=b3, daily=D3, flags=ds['flags'], rq=ds['rq'], validation=ds['validation'])
        E3 = Engine(ds3); S3 = make_sig(E3)
        vix = S3.vix.copy(); vm = vix.index >= dday; vix.loc[vm] = rs2.permutation(vix.values[vm]); S3.vix = vix
        t3, ts3 = S3.B2(p, 'high'); _, sd3 = risk_arrays(E3, S3, k)
        pre = np.where(b['date'].values < dday)[0]; same_sh = bool((t3[pre] == t[pre]).all() and np.allclose(ts3[pre], ts[pre]) and np.allclose(sd3[pre], sd[pre], equal_nan=True))
        R1 = E.run(t, ts, sd, risk=0.0075, min_chg=2); R3 = E3.run(t3, ts3, sd3, risk=0.0075, min_chg=2)
        i0 = int(np.searchsorted(D.values, np.datetime64(dday))); pnl_same = bool(np.allclose(R1.net_d[:i0 - 1], R3.net_d[:i0 - 1]))
        out[str(dday.date())] = dict(truncation_strategy=same_dir and same_sz, truncation_baseline=same_b, shuffle_signals=same_sh, shuffle_pnl_before=pnl_same)
        rep.append(f'- cut {dday.date()}: truncation (strategy signals) {"identical" if same_dir and same_sz else "DIFFER"}; truncation (baseline) {"identical" if same_b else "DIFFER"}; '
                   f'shuffled-future signals before cut {"identical" if same_sh else "DIFFER"}; shuffled-future daily P&L before cut {"identical" if pnl_same else "DIFFER"}')
    return out

def main():
    check_protocol()
    DRY = os.environ.get('DRYRUN') == '1'
    op = f'{RES}/test_opened.json'
    if DRY:   # code-path test only: the 'test' and 'recent' windows are swapped for TRAIN data so nothing locked is read; outputs go to dryrun/
        SPLITS['test'] = ('2019-01-01', '2021-12-31'); SPLITS['recent'] = ('2019-01-01', '2021-12-31'); SPLITS['full'] = ('2017-04-01', '2021-12-31')
        globals()['WF_END'] = '2021-12-31'
    elif os.path.exists(op) and os.environ.get('REOPEN') != '1':
        raise SystemExit(f'Test window already opened: {open(op).read()}\nRe-running burns the test (set REOPEN=1 only deliberately).')
    spec_hash = hashlib.sha256(open(f'{RES}/FROZEN_SPEC.json', 'rb').read()).hexdigest()
    ds = pd.read_pickle(f'{ROOT}/data/rm/dataset.pkl'); E = Engine(ds); S = make_sig(E)
    for kk in ('floor', 'real'): E.rates[kk + '2'] = tuple(2 * x for x in E.rates[kk])
    p, k = 80, SPEC['k']; assert SPEC['tv'] is None and not SPEC['dd'] and SPEC['dl'] == 0.0 and SPEC['ov'] == 0
    rep = []; P = rep.append; R = {}
    for c in ('floor', 'real', 'floor2', 'real2'):
        R[('S', c)] = strat(E, S, p, k, cost=c); R[('B', c)] = base(E, S, cost=c)
    P(f'# Final report: Nifty 50 futures strategy research roadmap (generated {time.strftime("%Y-%m-%d")})\n')
    P(f'Frozen spec (`results/rm/FROZEN_SPEC.json`, sha256 `{spec_hash[:16]}...`): {SPEC["signal"]}; stop k={k} x ATR(15-min), lots = min(full, floor(0.0075 x Rs2cr / (k x ATR x 65))); '
      f'no vol targeting / overnight cap / drawdown brake / daily loss limit (each failed to earn its place on train). Dataset sha256 `{SPEC["dataset_sha"][:16]}...`.\n')
    # ----------------------------------------------------------------- section 1: windows
    wins = [('train', 'Train 2017-04..2021-12'), ('valid', 'Validate 2022-01..2023-12'), ('test', 'TEST 2024-01..2026-10 (locked, opened once)'), ('recent', 'Recent 2022-01..2026-10'), ('full', 'Full 2017-04..2026-10')]
    P('## 1. Results by window (floor costs = mandate yardstick; total return incl. 6% interest on collateral, Sharpe on excess return)\n')
    for cost, nm in (('floor', 'Mandate floor costs (0.025%/side, 0.05%/roll)'), ('real', 'Realistic costs (dated STT, brokerage, exchange, SEBI, stamp, GST, 1 tick; roll = 2 legs + spread)')):
        rows = {}
        for w, wn in wins:
            rows[f'{wn} — strategy'] = row(R[('S', cost)].metrics(w)); rows[f'{wn} — baseline'] = row(R[('B', cost)].metrics(w))
        P(f'### {nm}\n'); P(md(pct_df(pd.DataFrame(rows).T), '{:.2f}')); P('')
    ni = {}
    for w, wn in wins:
        ni[f'{wn} — strategy'] = row(R[('S', 'floor')].metrics(w, interest=False)); ni[f'{wn} — baseline'] = row(R[('B', 'floor')].metrics(w, interest=False))
    P('### Floor costs, WITHOUT interest on idle collateral (pure futures P&L; long pays the basis)\n'); P(md(pct_df(pd.DataFrame(ni).T), '{:.2f}')); P('')
    # ----------------------------------------------------------------- section 2: calendar years
    ys = pd.DataFrame({'strategy': yearly(R[('S', 'floor')]), 'baseline': yearly(R[('B', 'floor')]), 'strategy (real cost)': yearly(R[('S', 'real')]), 'baseline (real cost)': yearly(R[('B', 'real')])})
    P('## 2. Calendar years (total return, floor costs unless stated; 2026 = Jan-Oct)\n'); P(md(ys.map(lambda v: f'{v:.1%}'))); P('')
    # ----------------------------------------------------------------- section 3: walk-forward (run once)
    folds = wf_folds(end=globals().get('WF_END', '2026-10-31')); grid = {(pp, kk): strat(E, S, pp, kk) for pp in PSET for kk in KSET}
    RB = R[('B', 'floor')]; picks = []; fl = []; Rs = []
    for (a, z), (t0, t1) in folds:
        sc = {c: grid[c].metrics('full', lo=t0, hi=t1)['Sharpe'] for c in grid}
        inter = [(pp, kk) for (pp, kk) in grid if 0 < PSET.index(pp) < len(PSET) - 1 and 0 < KSET.index(kk) < len(KSET) - 1]
        def nm(c):
            vals = [sc[d] for d in grid if abs(PSET.index(d[0]) - PSET.index(c[0])) <= 1 and abs(KSET.index(d[1]) - KSET.index(c[1])) <= 1]; return np.mean(vals)
        best = max(inter, key=nm); picks.append(dict(oos=f'{a}..{z}', train=f'{t0}..{t1}', p=best[0], k=best[1], train_sharpe=sc[best])); fl.append((a, z)); Rs.append(grid[best])
    ws_t, ws_e = stitched(Rs, fl); wb_t, wb_e = stitched([RB] * len(fl), fl)
    mw = metrics_from(ws_t, None, None, None, ws_e); mwb = metrics_from(wb_t, None, None, None, wb_e)
    P('## 3. Rolling walk-forward (3y train, 6m OOS, 6m step; parameters re-picked per fold by the plateau rule; OOS stitched; run once)\n')
    P(md(pct_df(pd.DataFrame({'strategy WF': row(mw), 'baseline WF': row(mwb)}).T), '{:.2f}')); P('')
    P(md(pd.DataFrame(picks).set_index('oos'), '{:.2f}')); P('')
    # ----------------------------------------------------------------- section 4: stress tests (test window)
    P('## 4. Stress tests on the test window (reported, never used to pick parameters)\n'); stress = {}
    S0 = R[('S', 'floor')]; B0 = R[('B', 'floor')]
    stress['strategy, floor'] = S0.metrics('test'); stress['baseline, floor'] = B0.metrics('test')
    stress['strategy, costs x2 (floor)'] = R[('S', 'floor2')].metrics('test'); stress['baseline, costs x2 (floor)'] = R[('B', 'floor2')].metrics('test')
    stress['strategy, costs x2 (real)'] = R[('S', 'real2')].metrics('test'); stress['baseline, costs x2 (real)'] = R[('B', 'real2')].metrics('test')
    Sd = strat(E, S, p, k, delay=1); Bd = base(E, S, delay=1)
    stress['strategy, fill 1 bar later'] = Sd.metrics('test'); stress['baseline, fill 1 bar later'] = Bd.metrics('test')
    a, z = SPLITS['test']; sel = (E.days[S0.trade_day] >= pd.Timestamp(a)) & (E.days[S0.trade_day] <= pd.Timestamp(z)); T = S0.trades[sel]; net = T[:, 6] - T[:, 7]
    top = np.argsort(-net)[:10]; s_tot = S0.series(True).copy(); s_ex = pd.Series(S0.net_d, index=E.days).copy()
    for i in top:
        dday = E.days[S0.trade_day[np.where(sel)[0][i]]]; s_tot.loc[dday] -= net[i] / CAPITAL; s_ex.loc[dday] -= net[i] / CAPITAL
    stress['strategy, best 10 trades removed'] = metrics_from(s_tot.loc[a:z], None, None, None, s_ex.loc[a:z])
    P_share = (net[top].sum(), net.sum())
    for (pp, kk) in [(70, 2.5), (90, 2.5), (80, 2.0), (80, 3.0), (70, 2.0), (90, 3.0)]:
        stress[f'param neighbour p={pp}, k={kk}'] = grid[(pp, kk)].metrics('test')
    P(md(pct_df(pd.DataFrame({kx: row(v) for kx, v in stress.items()}).T), '{:.2f}')); P('')
    P(f'Best 10 trades: Rs {P_share[0]:,.0f} of net trade P&L vs Rs {P_share[1]:,.0f} for all {len(net)} test-window trades (positive net total = the best 10 are most of the profit; negative = they were offsetting losses).\n')
    P(f'Long and short legs separately (strategy is long-only by design; the symmetric-short version A1 failed validation): strategy test long-leg CAGR {S0.metrics("test").get("LongLegCAGR", np.nan):.1%}, short-leg CAGR {S0.metrics("test").get("ShortLegCAGR", np.nan):.1%}; baseline long-leg {B0.metrics("test").get("LongLegCAGR", np.nan):.1%}.\n')
    # ----------------------------------------------------------------- section 5: gap risk and stops
    P('## 5. Stops, gaps and the per-trade loss cap\n')
    allm = S0.metrics('full'); tm = S0.metrics('test')
    tr = S0.trades; stp = tr[tr[:, 8] == 1]
    P(f'- Full period: {len(stp)} stop-outs out of {len(tr)} trades. Max loss at the stop price {allm["MaxLossAtStop"]:.2%} of capital (cap 0.75%, hard limit 1%); max loss at the actual fill (gaps through the stop included) {allm["MaxLossWithGap"]:.2%}.')
    P(f'- Test window: max loss at stop {tm["MaxLossAtStop"]:.2%}; with gaps {tm["MaxLossWithGap"]:.2%}; stop-outs with fill loss > 1% of capital (gap-driven): {int((-stp[:, 10] > 0.01).sum())} (all windows).')
    phase4 = json.load(open(f'{RES}/phase4_results.json')); g = phase4['gap']
    P(f'- Train gap study: {g["n_gap_down_1pct"]} of {g["n"]} sessions ({g["p_gap_down_1pct"]:.1%}) opened more than 1% below the prior close (worst {g["worst"]:.1%}); a gap of that size at full size costs more than 1% of capital. '
      f'The overnight cap (8 lots) was tested and dropped on train (Sharpe collapsed because the overnight leg carries the return); the intraday-only variant D1 failed train (Sharpe -0.71).\n')
    # ----------------------------------------------------------------- section 6: statistics
    P('## 6. Statistics\n')
    idx = (E.days >= pd.Timestamp(a)) & (E.days <= pd.Timestamp(z)); idr = (E.days >= pd.Timestamp(SPLITS['recent'][0])) & (E.days <= pd.Timestamp(SPLITS['recent'][1]))
    for nm_, ix in (('test 2024-01..2026-10', idx), ('recent 2022-01..2026-10', idr)):
        X = pd.DataFrame({'s': S0.net_d[ix] / CAPITAL, 'b': B0.net_d[ix] / CAPITAL})
        ci = block_boot(X); P(f'- 20-day block bootstrap (4000 draws), Sharpe(strategy) - Sharpe(baseline), {nm_}: median {ci[1]:+.2f}, 95% CI [{ci[0]:+.2f}, {ci[2]:+.2f}] ' + ('(CI includes 0: not distinguishable)' if ci[0] <= 0 <= ci[2] else ''))
    TL = json.load(open(f'{RES}/trials.json')); uniq = {(x['idea'], json.dumps(x['cell'], sort_keys=True)) for x in TL}
    Ntr = len(uniq) + len(SPEC.get('_extra', [])); trs = np.array([x['sharpe'] for x in TL if x['split'] == 'train']) / np.sqrt(252)
    ds_, sr0, srx = dsr(S0.net_d[idx] / CAPITAL, trs, Ntr)
    P(f'- Configurations tried (unique idea x parameter cells, all phases): **{Ntr}**. Deflated Sharpe Ratio on the test window: SR {srx:.2f} annualised vs the expected best-of-{Ntr}-noise SR0 {sr0:.2f}; DSR (probability the true Sharpe > 0 after deflation) = {ds_:.2f}.')
    # PBO on the candidate set: all Phase-4 style configs over the dev window
    cfgs = []; cols = []
    for pp in PSET:
        for kk in KSET:
            for tv in (None, 0.12, 0.15, 0.18):
                for dl in (0.0, 0.015):
                    Rx = strat(E, S, pp, kk, tv=tv, dl=dl); cols.append(Rx.series(False).loc[SPLITS['dev'][0]:SPLITS['dev'][1]].values); cfgs.append((pp, kk, tv, dl))
    M = np.array(cols).T; pbo = pbo_cscv(M, 10)
    P(f'- Probability of Backtest Overfitting (CSCV, 10 partitions, {len(cfgs)} candidate configs, 2017-04..2023-12): **{pbo:.0%}**.')
    # ----------------------------------------------------------------- section 7: lookahead
    P('\n## 7. Lookahead tests\n'); lk = lookahead_tests(E, S, ds, p, k, rep)
    sh0 = S0.metrics('test')['Sharpe']; shd = Sd.metrics('test')['Sharpe']; bh0 = B0.metrics('test')['Sharpe']; bhd = Bd.metrics('test')['Sharpe']
    P(f'- Extra delay (fill one bar later), test window: strategy Sharpe {sh0:.2f} -> {shd:.2f}; baseline {bh0:.2f} -> {bhd:.2f} (large collapse would mean the edge lives in the fill bar).')
    # ----------------------------------------------------------------- section 8: synthetic vs real futures
    fut = pd.read_csv(f'{ROOT}/data/fut/nifty_fut.csv', parse_dates=['date', 'expiry']).drop_duplicates(['date', 'expiry']); fut = fut[(fut.open > 0) & (fut.close > 0)].set_index(['date', 'expiry'])
    D_ = E.D; rn = []; sn = []; rd = []; sd_ = []; dts = []
    first_idx = np.where(E.first_b)[0]; last_idx = np.where(E.last_b)[0]
    for i in range(1, len(D_)):
        d0, d1, e = D_.index[i - 1], D_.index[i], D_['held'].iloc[i]
        if (d0, e) in fut.index and (d1, e) in fut.index:
            rn.append(fut.loc[(d1, e), 'open'] / fut.loc[(d0, e), 'close'] - 1); fb = first_idx[i]; sn.append(E.fo[fb] / E.prev[fb] - 1)
            rd.append(fut.loc[(d1, e), 'close'] / fut.loc[(d1, e), 'open'] - 1); sd_.append(E.fc[last_idx[i]] / E.fo[fb] - 1); dts.append(d1)
    V = pd.DataFrame({'real_night': rn, 'syn_night': sn, 'real_day': rd, 'syn_day': sd_}, index=dts)
    P('\n## 8. Synthetic series vs real NSE futures (daily bhavcopy): is the overnight edge real?\n')
    for w, wn in (('train', 'train'), ('valid', 'validate'), ('test', 'test')):
        v = V.loc[SPLITS[w][0]:SPLITS[w][1]]
        P(f'- {wn}: mean night return real futures {v.real_night.mean() * 1e4:+.1f} bp vs synthetic {v.syn_night.mean() * 1e4:+.1f} bp; mean day return real {v.real_day.mean() * 1e4:+.1f} bp vs synthetic {v.syn_day.mean() * 1e4:+.1f} bp (n={len(v)})')
    P(f'- Correlation night real vs synthetic {V.real_night.corr(V.syn_night):.2f}, day {V.real_day.corr(V.syn_day):.2f}. The synthetic series inherits the spot index\'s 09:15 "open"; if the night-leg means differ, '
      'overnight-heavy results (this strategy holds mostly overnight) are overstated on the synthetic series. Intraday real futures bars are not in the data, so this cannot be corrected here.')
    # ----------------------------------------------------------------- section 8b: real-futures-anchored series, buy and hold, regimes
    fut_all = fut
    Ea, cov = anchored_engine(E, fut_all); Sa = make_sig(Ea)
    Sa_S = strat(Ea, S, p, k); Sa_B = base(Ea, S); Sa_H = bh(Ea); BH = bh(E)
    P('\n## 8b. Robustness: same signals on a REAL-futures-anchored price path (each session\'s open and close pinned to the actual NSE futures open/close; coverage ' + f'{cov:.0%} of sessions)\n')
    P('Signals are unchanged (spot). Only the P&L path changes, so overnight gaps equal real futures gaps. Not a gating test (the protocol\'s official yardstick is the synthetic series), but it shows how much of the result depends on the spot-open artefact.\n')
    rr = {}
    for w, wn in wins:
        rr[f'{wn} — strategy'] = row(Sa_S.metrics(w)); rr[f'{wn} — baseline'] = row(Sa_B.metrics(w)); rr[f'{wn} — buy & hold futures'] = row(Sa_H.metrics(w))
    P(md(pct_df(pd.DataFrame(rr).T), '{:.2f}')); P('')
    P('### Comparison with simply holding Nifty futures (1x, always long, rolled; same costs, same interest convention)\n'); hh = {}
    for w, wn in wins:
        hh[f'{wn} — buy & hold (synthetic)'] = row(BH.metrics(w)); hh[f'{wn} — strategy (synthetic)'] = row(S0.metrics(w))
    P(md(pct_df(pd.DataFrame(hh).T), '{:.2f}')); P('')
    P('### Regime-wise results inside train / validate / test (annualised return contribution and Sharpe of futures P&L after floor costs; regimes from prior-day data)\n')
    rt = regime_table(E, S, {'strategy': S0, 'baseline': B0, 'buy&hold': BH}, [w for w in wins if w[0] in ('train', 'valid', 'test')])
    P(md(rt.astype({'days': int}).astype({'days': str, 'ann_sharpe': str}).assign(ann_sharpe=rt.ann_sharpe.map('{:.2f}'.format)))); P('')
    # expiry effect on the OI idea (H1) - it failed train, but the check is reported
    t1, _ = S.H1(1); dte = (E.D['held'] - E.D.index.to_series()).dt.days.values[E.day_codes]; near = dte <= 3
    for lab, tt in (('all days', t1), ('excluding sessions within 3 days of expiry', np.where(near, 0, t1).astype(np.int8))):
        mH = E.run(tt, None).metrics('train'); P(f'- H1 (OI x price, prior-day data, n=1) on train, {lab}: Sharpe {mH["Sharpe"]:.2f}, MaxDD {mH["MaxDD"]:.1%}, CAGR {mH["CAGR"]:.1%}')
    P('- OI lookahead: OI is published after the close, so day d uses only day d-1 OI (signal shifted one day in `Sig.H1`); H1 is not part of the frozen strategy.\n')
    # ----------------------------------------------------------------- section 9: pass criteria
    P('\n## 9. Pass criteria (all must hold) and roadmap targets\n')
    ms, mb = {w: R[('S', 'floor')].metrics(w) for w, _ in wins}, {w: R[('B', 'floor')].metrics(w) for w, _ in wins}
    msr, mbr = {w: R[('S', 'real')].metrics(w) for w, _ in wins}, {w: R[('B', 'real')].metrics(w) for w, _ in wins}
    chk = []
    def C(name, ok, detail): chk.append((name, bool(ok), detail))
    C('Sharpe above baseline on test (floor)', ms['test']['Sharpe'] > mb['test']['Sharpe'], f"{ms['test']['Sharpe']:.2f} vs {mb['test']['Sharpe']:.2f}")
    C('Sharpe above baseline on 2022-01..2026-10 (floor)', ms['recent']['Sharpe'] > mb['recent']['Sharpe'], f"{ms['recent']['Sharpe']:.2f} vs {mb['recent']['Sharpe']:.2f}")
    C('Sharpe above baseline on test (realistic costs)', msr['test']['Sharpe'] > mbr['test']['Sharpe'], f"{msr['test']['Sharpe']:.2f} vs {mbr['test']['Sharpe']:.2f}")
    dd_ok = all(ms[w]['MaxDD'] > -0.15 and ms[w]['MaxDD'] >= mb[w]['MaxDD'] for w in ms)
    C('MaxDD better than -15% on every window and better than the baseline\'s', dd_ok, '; '.join(f"{w}: {ms[w]['MaxDD']:.1%} vs {mb[w]['MaxDD']:.1%}" for w in ms))
    C('Walk-forward Sharpe above baseline\'s, drawdown better than -15%', mw['Sharpe'] > mwb['Sharpe'] and mw['MaxDD'] > -0.15, f"Sharpe {mw['Sharpe']:.2f} vs {mwb['Sharpe']:.2f}; MaxDD {mw['MaxDD']:.1%} (baseline {mwb['MaxDD']:.1%})")
    C('No calendar year worse than -10%', ys['strategy'].min() > -0.10, f"worst {ys['strategy'].min():.1%} ({ys['strategy'].idxmin()})")
    C('Still beats the baseline with doubled costs (test, floor and real)', stress['strategy, costs x2 (floor)']['Sharpe'] > stress['baseline, costs x2 (floor)']['Sharpe'] and stress['strategy, costs x2 (real)']['Sharpe'] > stress['baseline, costs x2 (real)']['Sharpe'],
      f"floor x2: {stress['strategy, costs x2 (floor)']['Sharpe']:.2f} vs {stress['baseline, costs x2 (floor)']['Sharpe']:.2f}; real x2: {stress['strategy, costs x2 (real)']['Sharpe']:.2f} vs {stress['baseline, costs x2 (real)']['Sharpe']:.2f}")
    C('No trade lost more than 1% of capital at its stop (gaps reported separately)', allm['MaxLossAtStop'] <= 0.01, f"max {allm['MaxLossAtStop']:.2%} at the stop; {allm['MaxLossWithGap']:.2%} incl. gaps")
    P('| Criterion | Result | Detail |\n|---|---|---|'); [P(f"| {n} | {'PASS' if ok else 'FAIL'} | {dt} |") for n, ok, dt in chk]
    P('\nRoadmap targets (floor costs):\n')
    tg = [('Sharpe Apr 2017-Oct 2026 >= 1.0', ms['full']['Sharpe'] >= 1.0, f"{ms['full']['Sharpe']:.2f} (baseline {mb['full']['Sharpe']:.2f})"),
          ('Sharpe Jan 2022-Oct 2026 >= 0.8', ms['recent']['Sharpe'] >= 0.8, f"{ms['recent']['Sharpe']:.2f} (baseline {mb['recent']['Sharpe']:.2f})"),
          ('Max drawdown better than -12% (hard limit -15%)', ms['full']['MaxDD'] > -0.12, f"{ms['full']['MaxDD']:.1%} (baseline {mb['full']['MaxDD']:.1%})"),
          ('Walk-forward CAGR >= 15% and MaxDD better than -15%', mw['CAGR'] >= 0.15 and mw['MaxDD'] > -0.15, f"CAGR {mw['CAGR']:.1%}, MaxDD {mw['MaxDD']:.1%} (baseline {mwb['CAGR']:.1%} / {mwb['MaxDD']:.1%})"),
          ('Sharpe on locked test above baseline', ms['test']['Sharpe'] > mb['test']['Sharpe'], f"{ms['test']['Sharpe']:.2f} vs {mb['test']['Sharpe']:.2f}"),
          ('Loss per trade at the stop <= 0.75% (cap 1%)', allm['MaxLossAtStop'] <= 0.0076, f"{allm['MaxLossAtStop']:.2%}")]
    P('| Target | Met? | Value |\n|---|---|---|'); [P(f"| {n} | {'yes' if ok else 'no'} | {dt} |") for n, ok, dt in tg]
    allpass = all(ok for _, ok, _ in chk)
    verdict = 'GO to paper trading' if allpass else 'NO-GO: not all pass criteria hold'
    anc = f"On the real-anchored path (section 8b) the test-window Sharpe is {Sa_S.metrics('test')['Sharpe']:.2f} for the strategy vs {Sa_B.metrics('test')['Sharpe']:.2f} for the baseline and {Sa_H.metrics('test')['Sharpe']:.2f} for buy-and-hold futures; full-period {Sa_S.metrics('full')['Sharpe']:.2f} / {Sa_B.metrics('full')['Sharpe']:.2f} / {Sa_H.metrics('full')['Sharpe']:.2f}."
    P(f'\n## 10. Gate G5 verdict: **{verdict}**\n'); P(anc + '\n')
    P('Honest limits: (i) Gate G3 not met (only one idea validated); (ii) prices are synthetic futures from spot, and section 8 quantifies how the overnight leg differs from real futures; (iii) the test window\'s Sharpe has a standard error near 0.6, so no single number proves superiority; '
      '(iv) earlier work in this repo had already looked at 2024-26 for other strategies; (v) two implementation corrections were made after the first validation looks (PROTOCOL_CHANGES.md).')
    # ----------------------------------------------------------------- deliverables
    if DRY: pass
    os.makedirs(f'{RES}/trades' if not DRY else f'{RES}/dryrun_trades', exist_ok=True); bi = E.b.index
    for nm_, Rx in (('strategy', S0), ('baseline', B0), ('strategy_real', R[('S', 'real')]), ('baseline_real', R[('B', 'real')])):
        tt = Rx.trades; df = pd.DataFrame({'entry_time': bi[tt[:, 0].astype(int)], 'exit_time': bi[tt[:, 1].astype(int)], 'side': tt[:, 2].astype(int), 'lots': tt[:, 3].astype(int), 'entry_px': tt[:, 4], 'exit_px': tt[:, 5],
                                          'gross_pnl_rs': tt[:, 6], 'costs_rs': tt[:, 7], 'net_pnl_rs': tt[:, 6] - tt[:, 7], 'stopped': tt[:, 8].astype(int)})
        df.to_csv(f'{RES}/' + ('dryrun_trades' if DRY else 'trades') + f'/trades_{nm_}.csv', index=False)
        eq = pd.DataFrame({'net_return': Rx.net_d / CAPITAL, 'interest': Rx.int_d, 'total_return': Rx.net_d / CAPITAL + Rx.int_d}, index=E.days); eq['equity_total'] = (1 + eq.total_return).cumprod(); eq.to_csv(f'{RES}/' + ('dryrun_trades' if DRY else 'trades') + f'/daily_equity_{nm_}.csv')
    pd.DataFrame({'stitched_total_strategy': ws_t, 'stitched_total_baseline': wb_t}).to_csv(f'{RES}/' + ('dryrun_trades' if DRY else 'trades') + '/walkforward_stitched.csv')
    json.dump(dict(checks=chk, verdict=verdict, picks=picks, lookahead=lk, pbo=pbo, dsr=ds_, N=Ntr), open(f'{RES}/' + ('dryrun_summary.json' if DRY else 'final_summary.json'), 'w'), indent=1, default=str)
    if DRY:
        open(f'{RES}/dryrun_report.md', 'w').write('\n'.join(rep)); print('DRY RUN OK (train-window data only)'); print('\n'.join(rep)[:3000]); return
    json.dump(dict(opened=time.strftime('%Y-%m-%d %H:%M:%S'), spec_sha256=spec_hash, reopen=os.environ.get('REOPEN') == '1'), open(op, 'w'))
    open(f'{RES}/FINAL_ROADMAP_REPORT.md', 'w').write('\n'.join(rep)); print('\n'.join(rep))

if __name__ == '__main__': main()
