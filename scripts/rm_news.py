"""News / crisis factor diagnostic for the short leg (no trials). Run: <venv>/bin/python scripts/rm_news.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_batch2 as B, rm_noise as NZ, rm_stress as ST
En, S0, TR = B.En, 1.115, B.TRAIN; days = B.em['days']; DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'news')
def stress80(x, high=True, win='365D'):
    """stress ON when the value is in the worst 20% of the PRIOR year: above its 80th percentile (high=True) or below its 20th (high=False); the percentile uses values strictly before today."""
    q = x.shift(1).rolling(win, min_periods=60).quantile(0.8 if high else 0.2); return ((x > q) if high else (x < q)).astype(float).where(q.notna())
def known_on(days, s, extra_bdays=0):
    """state (0/1) known on each Indian day: the latest observation dated strictly before that day, optionally delayed by extra business days"""
    s = s.dropna()
    if extra_bdays: s = pd.Series(s.values, index=s.index + pd.offsets.BDay(extra_bdays))
    return (NZ.prior_val(days, s) == 1).reindex(days).fillna(False)
def load():
    f = {}
    g = pd.read_excel(os.path.join(DATA, 'gpr_daily_recent.xls')); g = g.set_index(pd.to_datetime(g['date']))['GPRD'].astype(float); f['N1 GPR daily > p80 of prior year (lag 1d)'] = known_on(days, stress80(g))
    t = pd.read_csv(os.path.join(DATA, 'gdelt_india_tone.csv'), parse_dates=['date']).set_index('date')['tone'].astype(float); t5 = t.rolling(5).mean(); f['N2 GDELT India tone, 5d avg, worst 20% of prior year (lag 1d)'] = known_on(days, stress80(t5, high=False))
    o = pd.read_csv(os.path.join(DATA, 'ofr_fsi.csv'), parse_dates=['Date']).set_index('Date')['OFR FSI'].astype(float); f['N3 OFR FSI > p80 of prior year (published with 2 business days delay)'] = known_on(days, stress80(o), extra_bdays=1)
    p = os.path.join(DATA, 'pit_promoter_sells.csv')
    if os.path.exists(p):
        a = pd.read_csv(p, parse_dates=['date']).set_index('date')['promoter_sell_value']; a = a.reindex(pd.date_range(a.index.min(), a.index.max())).fillna(0.0).rolling(5).sum(); f['N6 promoter sells of Nifty names, 5d sum by filing date > p80 of prior year (lag 1d)'] = known_on(days, stress80(a))
    return f
def short_trades():
    Rr = En.run(B.SH_BASE, B.one, cost='floor', min_chg=1); rows = []
    for tr in Rr.trades:
        if int(tr[2]) != -1: continue
        d = En.days[En.day_codes[int(tr[0])]]
        if pd.Timestamp(TR[0]) <= d <= pd.Timestamp(TR[1]): rows.append((d, (tr[6] - tr[7]) / 2e7 * 0.956 * S0))
    return pd.DataFrame(rows, columns=['d', 'pnl'])
if __name__ == '__main__':
    F = load(); df = short_trades(); top = df.nlargest(10, 'pnl'); los = df[df.pnl <= 0]
    print(f'SHORT DIAGNOSTIC TRAIN {TR[0]}..{TR[1]}: {len(df)} shorts; top 10 crash trades {top.pnl.sum():+.1%}; {len(los)} losing shorts ({los.pnl.sum():+.1%})\ncrash entry days: {[str(x.date()) for x in top.d]}\n')
    print('| factor (state at the entry day) | on-share of all TRAIN days | ON for the top-10 crash shorts | OFF for losing shorts | gate (>=8 of 10 and >=40% off) |'); print('|---|---|---|---|---|'); passed = []
    for n, s in F.items():
        k = int(sum(s[d] for d in top.d)); off = 1 - np.mean([s[d] for d in los.d]); ok = k >= 8 and off >= 0.40; passed += [n] if ok else []
        print(f'| {n} | {s[TR[0]:TR[1]].mean():.0%} | {k} of 10 ({"".join("1" if s[d] else "0" for d in top.d)}) | {off:.0%} | {"PASS" if ok else "no"} |')
    print('\npassing the gate:', passed or 'NONE')
