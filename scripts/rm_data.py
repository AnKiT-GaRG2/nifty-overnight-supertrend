"""Roadmap Phase 0: clean versioned dataset (1-min spot, 15-min bars labelled by CLOSE time, daily bars) and the
synthetic continuous futures series. Output: data/rm/dataset.pkl, results/rm/G0_data_report.md.
Run: python3 scripts/rm_data.py
Convention (written before coding): futures F = S * (1 + (r - q) * dte/365), r=6%, q=1.3% (dated inputs in RQ).
A long position therefore LOSES the basis as it decays to spot; a short earns it; idle collateral interest (r) is added
separately and reported both with and without."""
import os, glob, hashlib, json
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data'); OUT = os.path.join(DATA, 'rm'); RES = os.path.join(ROOT, 'results', 'rm')
os.makedirs(OUT, exist_ok=True); os.makedirs(RES, exist_ok=True)
END = '2026-10-31'
RQ = [('2000-01-01', 0.06, 0.013)]      # (valid_from, r, q): dated so they can later follow T-bill / dividend yield

def rq_on(d):
    r = q = None
    for s, rr, qq in RQ:
        if d >= pd.Timestamp(s): r, q = rr, qq
    return r, q

def load_1min():
    fs = sorted(glob.glob(f'{DATA}/intraday/NIFTY50_1min_*.csv'))
    df = pd.concat([pd.read_csv(f) for f in fs])
    df['ts'] = pd.to_datetime(df['Timestamp']); df = df.drop(columns=['Timestamp', 'Epoch']).set_index('ts').sort_index()
    return df

def build():
    rep = []; P = rep.append
    raw = load_1min(); P(f'- raw 1-min rows: {len(raw):,}; duplicates dropped: {raw.index.duplicated().sum()}')
    raw = raw[~raw.index.duplicated()]
    raw = raw[raw.index < pd.Timestamp(END) + pd.Timedelta(days=1)]
    hm = raw.index.strftime('%H:%M')
    outside = ((hm < '09:15') | (hm > '15:29'))
    muhurat_days = sorted(set(raw.index[outside].normalize().strftime('%Y-%m-%d')))
    P(f'- minutes outside 09:15-15:29 dropped: {outside.sum():,} (on {len(muhurat_days)} days; Muhurat/special evening sessions)')
    m1 = raw[~outside].copy(); m1['date'] = m1.index.normalize()
    cnt = m1.groupby('date').size()
    P(f'- trading days: {len(cnt)}; days with all 375 minutes: {(cnt == 375).sum()}; days with missing minutes: {(cnt < 375).sum()}; '
      f'total missing minutes: {int((375 - cnt).clip(lower=0).sum())}')
    short = cnt[cnt < 340]
    P(f'- days with <340 minutes (flagged special/short sessions): {len(short)} -> ' + ', '.join(f'{d:%Y-%m-%d}({n})' for d, n in short.items()))
    sat = [d for d in cnt.index if d.weekday() >= 5]
    P(f'- weekend sessions (Budget Saturdays etc.) kept and flagged: ' + (', '.join(f'{d:%Y-%m-%d}' for d in sat) or 'none'))
    flat = ((m1.Open == m1.High) & (m1.High == m1.Low) & (m1.Low == m1.Close))
    P(f'- flat (O=H=L=C) minutes: {flat.sum():,} ({flat.mean():.2%}); zero-volume minutes (files with volume only): '
      f'{int((m1["Volume"] == 0).sum()) if "Volume" in m1 else 0}')
    bad = ((m1.High < m1[['Open', 'Close', 'Low']].max(axis=1)) | (m1.Low > m1[['Open', 'Close', 'High']].min(axis=1))).sum()
    P(f'- minutes with inconsistent OHLC: {bad}')
    # 15-min bars anchored 09:15, 25 per day, LABELLED BY CLOSE TIME (start + 15 min): bar uses only minutes before its label
    b = m1.resample('15min', origin='start_day', offset='9h15min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    b.columns = ['open', 'high', 'low', 'close']; b['start'] = b.index; b.index = b.index + pd.Timedelta(minutes=15); b.index.name = 'close_time'
    b['date'] = b['start'].dt.normalize()
    nb = b.groupby('date').size()
    P(f'- 15-min bars: {len(b):,}; days with 25 bars: {(nb == 25).sum()}; days with fewer: {(nb < 25).sum()}')
    rng = (b.high - b.low) / b.close
    P(f'- 15-min bars with range > 2%: {(rng > 0.02).sum()} (kept, flagged; max {rng.max():.2%})')
    P(f'- 1-min bars with range > 2%: {int(((m1.High - m1.Low) / m1.Close > 0.02).sum())}')
    g = b.groupby('date')
    D = pd.DataFrame({'open': g['open'].first(), 'high': g['high'].max(), 'low': g['low'].min(), 'close': g['close'].last()})
    # independent check: Yahoo daily closes in data/nifty.csv
    y = pd.read_csv(f'{DATA}/nifty.csv', parse_dates=['date']).set_index('date')
    j = D.join(y, rsuffix='_y', how='inner'); err = (j.close / j.close_y - 1).abs()
    rs = np.random.RandomState(7); spot = j.index[rs.choice(len(j), 20, replace=False)]
    P(f'- daily close vs independent Yahoo close ({len(j)} common days): within 0.05%: {(err <= 0.0005).mean():.2%}; '
      f'median abs diff {err.median():.4%}; 20 random days max diff {err.loc[spot].max():.4%}; days off by >0.05%: {(err > 0.0005).sum()}')
    P('  (days off by >0.05%: ' + ', '.join(f'{d:%Y-%m-%d}={e:.2%}' for d, e in err[err > 0.0005].head(15).items()) + ')')
    return m1, b, D, rep, dict(muhurat=muhurat_days, short=[str(d.date()) for d in short.index], weekend=[str(d.date()) for d in sat])

def expiry_calendar(days):
    """Rule: last Thursday of month until Aug 2025, last Tuesday from Sep 2025; holiday -> previous trading day.
    Actual bhavcopy expiries (2012+) take precedence; the rule fills the future months."""
    act = set()
    for f in ['nifty_fut.csv', 'nifty_fut_2012_2017.csv']:
        p = f'{DATA}/fut/{f}'
        if os.path.exists(p):
            act |= set(pd.to_datetime(pd.read_csv(p, usecols=['expiry'])['expiry']).unique())
    days = pd.DatetimeIndex(days); rule = []
    for y in range(2017, 2028):
        for mth in range(1, 13):
            wd = 3 if (y, mth) < (2025, 9) else 1
            last = (pd.Timestamp(y, mth, 1) + pd.offsets.MonthEnd(0))
            while last.weekday() != wd: last -= pd.Timedelta(days=1)
            # holiday shift: back to the prior trading day (days index up to Oct 2026; beyond it assume weekdays)
            while (days[0] <= last <= days[-1] and last not in days) or last.weekday() >= 5: last -= pd.Timedelta(days=1)
            rule.append(last)
    rule = sorted(set(rule))
    act_in = sorted(d for d in act if d >= pd.Timestamp('2017-04-01'))
    mism = [d for d in act_in if d not in set(rule)]
    exps = sorted(set(act_in) | {d for d in rule if d > max(act_in)})
    return exps, rule, mism, act_in

def synthetic(D, exps):
    """Per day: contract held (expiry), roll day, multiplier for the held contract at close of previous day, etc."""
    days = D.index; tdays = list(days)
    exps = [e for e in exps if e >= days[0]]
    pos = {d: i for i, d in enumerate(tdays)}
    def prev_td(e, k):
        # k trading days before expiry e (e is a trading day)
        i = pos.get(e);
        if i is None: i = int(np.searchsorted(days.values, np.datetime64(e)))
        return tdays[max(i - k, 0)]
    roll_day = {e: prev_td(e, 2) for e in exps if e <= days[-1]}
    held = []; roll_flag = np.zeros(len(days), bool)
    for i, d in enumerate(days):
        # near contract = first expiry >= d; rolled at close of roll day -> from the NEXT day, hold the next one
        k = next(j for j, e in enumerate(exps) if e >= d)
        e = exps[k]
        rd = roll_day.get(e, None)
        if rd is not None and d > rd: e = exps[k + 1]       # after the roll the position sits in the next contract
        elif rd is not None and d == rd: roll_flag[i] = True
        held.append(e)
    held = pd.DatetimeIndex(held)
    return held, roll_flag

def mult(date, expiry):
    r, q = rq_on(date)
    dte = np.maximum((expiry - date).days, 0)
    return 1 + (r - q) * dte / 365.0

def main():
    m1, b, D, rep, flags = build()
    exps, rule, mism, act = expiry_calendar(D.index)
    rep.append(f'- expiry calendar: {len(act)} actual bhavcopy expiries since 2017-04; rule-based dates disagreeing with an actual expiry: {len(mism)} ' + (str([str(x.date()) for x in mism[:10]]) if mism else ''))
    held, roll_flag = synthetic(D, exps)
    D = D.copy(); D['held'] = held; D['roll'] = roll_flag
    # 'held' contract valued at each date: multiplier at that day's close (and at previous day's close in the same contract)
    D['m_close'] = [mult(d, e) for d, e in zip(D.index, D.held)]
    D['m_prevclose'] = [mult(D.index[i - 1], D.held.iloc[i]) if i > 0 else np.nan for i in range(len(D))]
    D['syn_close'] = D.close * D.m_close
    # validation against actual near-month closes from bhavcopy
    fut = pd.concat([pd.read_csv(f'{DATA}/fut/nifty_fut.csv', parse_dates=['date', 'expiry']),
                     pd.read_csv(f'{DATA}/fut/nifty_fut_2012_2017.csv', parse_dates=['date', 'expiry'])]).drop_duplicates(['date', 'expiry'])
    fut = fut[fut.close > 0].set_index(['date', 'expiry'])['close']
    rows = []
    for d, e in zip(D.index, D.held):
        if (d, e) in fut.index:
            rows.append((d, e, fut[(d, e)], D.close[d] * mult(d, e)))
    V = pd.DataFrame(rows, columns=['date', 'expiry', 'actual', 'synthetic']); V['err'] = V.synthetic / V.actual - 1
    V['ym'] = V.date.dt.to_period('M')
    mon = V.groupby('ym')['err'].agg(['mean', lambda x: x.abs().mean()]); mon.columns = ['mean_err', 'mean_abs_err']
    # month-level tracking error: the monthly mean signed error (systematic basis mismatch)
    rep.append(f'- synthetic vs actual held-contract close ({len(V)} day-contract pairs, {len(mon)} months): mean error {V.err.mean():+.3%}, '
               f'mean abs {V.err.abs().mean():.3%}, 95th pct abs {V.err.abs().quantile(.95):.3%}; months with |mean err| <= 0.10%: {(mon.mean_err.abs() <= 0.001).mean():.1%}; '
               f'months with mean abs err <= 0.10%: {(mon.mean_abs_err <= 0.001).mean():.1%}')
    rep.append(f'- tracking error by year (mean signed / mean abs): ' + '; '.join(f'{y}: {g.err.mean():+.2%}/{g.err.abs().mean():.2%}' for y, g in V.groupby(V.date.dt.year)))
    # daily-return tracking: synthetic held-contract close-to-close return vs actual
    V = V.sort_values(['expiry', 'date']); V['ra'] = V.groupby('expiry').actual.pct_change(); V['rs'] = V.groupby('expiry').synthetic.pct_change()
    rr = (V.rs - V.ra).dropna()
    rep.append(f'- daily-return tracking error within contract: mean {rr.mean():+.4%}, std {rr.std():.4%}, correlation {V.ra.corr(V.rs):.4f}')
    # save dataset
    m1 = m1[['Open', 'High', 'Low', 'Close']].rename(columns=str.lower); m1['date'] = m1.index.normalize()
    ds = dict(m1=m1, b15=b, daily=D, flags=flags, rq=RQ, validation=V)
    pd.to_pickle(ds, f'{OUT}/dataset.pkl')
    h = hashlib.sha256()
    for a in (m1.values.tobytes(), b[['open', 'high', 'low', 'close']].values.tobytes(), D[['open', 'high', 'low', 'close', 'm_close']].values.tobytes()):
        h.update(a)
    ver = h.hexdigest()
    json.dump({'sha256': ver, 'rows_1min': len(m1), 'bars_15m': len(b), 'days': len(D)}, open(f'{OUT}/dataset_version.json', 'w'), indent=1)
    ok = (mon.mean_abs_err <= 0.001).mean()
    g0 = ('PASS' if (mon.mean_err.abs() <= 0.001).mean() > 0.95 else 'PARTIAL/FAIL: see tracking error above')
    txt = '# Gate G0: data report (generated by scripts/rm_data.py)\n\n' + '\n'.join(rep) + f'\n\n- dataset sha256: `{ver}`\n- G0 tracking-error check (95% of months with |mean error| <= 0.10%): **{g0}**\n'
    open(f'{RES}/G0_data_report.md', 'w').write(txt); print(txt)

if __name__ == '__main__':
    main()
