"""Monthly live-vs-model comparison for the v2-FE paper-trading log.

Usage (numba venv, from the repo root):
  <venv>/bin/python scripts/paper_compare.py --log results/rm/paper_trading_log.csv --month 2026-11 --stage 0.5 [--mark-price 23000] [--out report.md]
  <venv>/bin/python scripts/paper_compare.py --demo            # builds a synthetic log from the model for 2026-09 and runs the comparison (self-test)

Log format = results/rm/paper_trading_log_template.csv. Allowed `signal` values: ENTER_LONG, EXIT_LONG, ENTER_SHORT, EXIT_SHORT (matched against the model),
and ROLL, EVENT_REDUCE, EVENT_RESTORE, US_CUT_RESIZE, OTHER (reported but not matched). `side` is BUY or SELL. Slippage is positive when worse than the model price.
The model can only be run for months present in data/rm/dataset.pkl (currently to 2026-10-30); for later months extend the data first (intraday 1-minute bars, futures
bhavcopy, Nasdaq/US10Y closes) - without it the script still reports the live-side statistics and says so."""
import sys, os, argparse, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd

SCALE = 1.115; WL, WS = 1.912, 0.956; LOT = 65; CAPITAL = 2e7; TOL_SLIP_PCT = 0.0003            # tolerances: edit here and in the spec together
SIGNAL = ['ENTER_LONG', 'EXIT_LONG', 'ENTER_SHORT', 'EXIT_SHORT']

def load_log(path, month):
    df = pd.read_csv(path, parse_dates=['date']); need = ['date', 'signal', 'side', 'lots_intended', 'model_price_next_bar_open', 'fill_price', 'total_cost_rupees']
    miss = [c for c in need if c not in df.columns]
    if miss: raise SystemExit(f'log is missing columns: {miss}')
    df['signal'] = df['signal'].astype(str).str.upper().str.strip(); df['side'] = df['side'].astype(str).str.upper().str.strip()
    df = df[df.date.dt.strftime('%Y-%m') == month].copy(); sgn = np.where(df.side == 'BUY', 1.0, -1.0)
    df['slip_pts'] = (df.fill_price - df.model_price_next_bar_open) * sgn; df['slip_pct'] = df.slip_pts / df.model_price_next_bar_open
    df['notional'] = df.fill_price * df.lots_intended * LOT; df['cost_pct'] = df.total_cost_rupees / df.notional
    return df

def live_stats(df, out):
    P = out.append; P('## Live side (from the fill log)\n')
    if df.empty: P('No fills in this month.\n'); return {}
    P(f'- fills: {len(df)} ({df.signal.value_counts().to_dict()})')
    P(f'- slippage vs model price (positive = worse): mean {df.slip_pts.mean():+.2f} pts = {df.slip_pct.mean():+.4%}; worst {df.slip_pct.max():+.4%}; fills over the {TOL_SLIP_PCT:.2%} tolerance: {(df.slip_pct > TOL_SLIP_PCT).sum()}')
    P(f'- costs: total Rs {df.total_cost_rupees.sum():,.0f} = {df.total_cost_rupees.sum() / CAPITAL:.2%} of capital; mean {df.cost_pct.mean():.4%} of notional per fill (floor model: 0.0250% per side, 0.0500% per roll)')
    P(f'- slippage cost on top of the model: {(df.slip_pts * df.lots_intended * LOT).sum():+,.0f} Rs = {(df.slip_pts * df.lots_intended * LOT).sum() / CAPITAL:+.3%} of capital')
    flags = []
    if df.slip_pct.mean() > TOL_SLIP_PCT: flags.append(f'MEAN SLIPPAGE {df.slip_pct.mean():.4%} > tolerance {TOL_SLIP_PCT:.2%}')
    if df.cost_pct.mean() > 0.00025 * 1.5: flags.append('mean cost per fill more than 1.5x the floor model - compare with the realistic model below')
    P('- flags: ' + ('; '.join(flags) if flags else 'none') + '\n'); return dict(slip=df.slip_pct.mean(), cost=df.total_cost_rupees.sum() / CAPITAL)

def realistic_check(df, out):
    import rm_engine as E
    if df.empty: return
    rb, rs, _ = E.cost_rates(pd.DatetimeIndex(df.date), df.fill_price.values, 'real'); rate = np.where(df.side == 'BUY', rb, rs); model = (rate * df.notional).sum()
    out.append(f'- realistic cost model for the same fills (brokerage, exchange, SEBI, stamp, GST, 1 tick, dated STT): Rs {model:,.0f} vs actual Rs {df.total_cost_rupees.sum():,.0f} ({df.total_cost_rupees.sum() / model - 1:+.0%}); floor model would be Rs {(0.00025 * df.notional).sum():,.0f}\n')

def model_events(month, stage):
    import rm_v2next as V, rm_stress as ST, rm_batch2 as B
    em = B.em; En = B.En
    days = em['days']; sel = days[days.strftime('%Y-%m') == month]
    if len(sel) == 0: return None
    lt, lz, st, sz = V.signals(em, 'v2'); ev = []
    for leg, d, s in (('LONG', lt, lz), ('SHORT', st, sz)):
        R = En.run(d, s, cost='floor', min_chg=1)
        for tr in R.trades:
            eb, xb, side = int(tr[0]), int(tr[1]), int(tr[2])
            for bar, kind in ((eb, 'ENTER'), (xb, 'EXIT')):
                if bar >= En.N: continue
                t = En.b['start'].iloc[bar]
                if t.strftime('%Y-%m') == month: ev.append(dict(time=t, date=t.normalize(), signal=f'{kind}_{leg}', side=('BUY' if (leg == 'LONG') == (kind == 'ENTER') else 'SELL'), model_price=float(En.fo[bar]), lots=int(abs(tr[3]))))
    cp = ST.comps(em, 'floor'); EV = ST.ev_mask(em, ST.ELECT + ST.BUDGET)
    net = ST.stream(em, None, SCALE * stage, cp, EV); pnl = net[sel[0]:sel[-1]].sum(); return pd.DataFrame(ev).sort_values('time').reset_index(drop=True), pnl, sel

def compare(df, out, month, stage, mark, carry=None):
    res = model_events(month, stage)
    if res is None: out.append('## Model side\n\nThe model cannot be run for this month: the data set ends before it. Extend the data (see the docstring) and re-run. Live-side statistics above are still valid.\n'); return
    mev, mpnl, sel = res; P = out.append; P('## Model side (frozen v2-FE, floor costs, stage %.2f of full size)\n' % stage)
    live = df[df.signal.isin(SIGNAL)].copy(); live['key'] = live.date.dt.normalize().astype(str) + '|' + live.signal
    mev['key'] = mev.date.astype(str) + '|' + mev.signal; mk, lk = set(mev.key), set(live.key)
    P(f'- model signal fills: {len(mev)}; logged signal fills: {len(live)}; matched on (date, signal): {len(mk & lk)}')
    miss = sorted(mk - lk); extra = sorted(lk - mk)
    P(f'- in the model but NOT in the log ({len(miss)}): {miss[:12]}'); P(f'- in the log but NOT in the model ({len(extra)}): {extra[:12]}')
    m = live.merge(mev[['key', 'model_price']], on='key', how='inner')
    if len(m): d = (m.model_price_next_bar_open - m.model_price); P(f'- logged model price vs engine price (data-feed check, points): mean {d.mean():+.1f}, mean abs {d.abs().mean():.1f}  [engine opens are spot-path based inside the day; use your own feed as the reference]')
    nonsig = df[~df.signal.isin(SIGNAL)]; P(f'- non-signal fills (roll / event cap / US cut): {len(nonsig)} {nonsig.signal.value_counts().to_dict()}')
    # realised P&L from the log (FIFO per direction); open lots marked at --mark-price if given
    pos = [carry] if carry else []; real = 0.0; warn = []
    for r in df.sort_values('date').itertuples():
        q = r.lots_intended * (1 if r.side == 'BUY' else -1); px = r.fill_price
        if r.signal.startswith('EXIT') and not pos: warn.append(f'{r.date.date()} {r.signal}')
        while q != 0 and pos and np.sign(pos[0][0]) != np.sign(q):
            lq, lp = pos[0]; matched = min(abs(lq), abs(q)); real += (px - lp) * np.sign(lq) * matched * LOT      # long: px-lp, short: lp-px
            lq2 = lq - np.sign(lq) * matched
            if abs(lq2) < 1e-9: pos.pop(0)
            else: pos[0] = (lq2, lp)
            q -= np.sign(q) * matched
        if q != 0: pos.append((q, px))
    mtm = sum((mark - p) * q * LOT for q, p in pos) if mark and pos else 0.0; cost = df.total_cost_rupees.sum()
    P(f'- live P&L from fills: realised (gross) {real / CAPITAL:+.2%} of capital, logged costs {-cost / CAPITAL:.2%}, net realised {(real - cost) / CAPITAL:+.2%}' + (f', open position marked at {mark}: {mtm / CAPITAL:+.2%}, net incl. mark {(real + mtm - cost) / CAPITAL:+.2%}' if mark else ', open positions not marked (pass --mark-price)'))
    if warn: P(f'- WARNING: exit fills with no open position in the log ({warn[:4]}): a position carried in from the previous month is missing; pass --carry-in LOTS@PRICE (signed lots, entry price, e.g. 28@23100 or -14@23450). The live P&L line is unreliable until then.')
    P(f'- model P&L for the month at this stage (futures P&L after floor costs, excluding interest): {mpnl:+.2%} of capital\n')
    P('## Read-across\n\nDifferences in fill count or dates are the first thing to explain (late order, missed signal, data-feed mismatch). Slippage and cost differences feed section 8 of PAPER_TRADING_SPEC.md. Do not re-tune the model on one month.\n')

def make_demo(month='2026-09', stage=0.5):
    import rm_v2next as V, rm_batch2 as B
    mev, _, _ = model_events(month, stage); rng = np.random.default_rng(1); rows = []
    for r in mev.itertuples():
        side = r.side; slip = abs(rng.normal(0.0001, 0.0001)) * r.model_price * (1 if side == 'BUY' else -1); fill = r.model_price + slip
        lots = max(int(round(r.lots * stage * SCALE * (WL if 'LONG' in r.signal else WS))), 1); notional = fill * lots * LOT; cost = notional * 0.00035
        rows.append(dict(date=r.date.date(), signal_bar_close_time=str(r.time.time()), signal=r.signal, side=side, lots_intended=lots, model_price_next_bar_open=round(r.model_price + rng.normal(0, 3), 2), fill_price=round(fill, 2), fill_time=str(r.time.time()),
                         slippage_points='', slippage_pct_of_price='', brokerage=round(cost * 0.2, 2), exchange_charges=round(cost * 0.2, 2), stt=round(cost * 0.4 if side == 'SELL' else 0, 2), stamp_duty=round(cost * 0.1, 2), gst=round(cost * 0.1, 2), total_cost_rupees=round(cost, 2), total_cost_pct_of_notional='', contract='NIFTY-NEAR', event_day_flag='N', size_stage=stage, notes='demo'))
    rows = rows[:-1]                                              # drop one fill to show the "in model, not in log" check
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'rm', 'paper_trading_log_DEMO.csv'); pd.DataFrame(rows).to_csv(path, index=False); return path

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--log'); ap.add_argument('--month'); ap.add_argument('--stage', type=float, default=0.5); ap.add_argument('--mark-price', type=float); ap.add_argument('--out'); ap.add_argument('--carry-in', help='signed lots@entry price of the position open at the start of the month, e.g. 28@23100'); ap.add_argument('--demo', action='store_true'); a = ap.parse_args()
    if a.demo: a.month = '2026-09'; a.log = make_demo(a.month, a.stage); print('demo log written to', a.log)
    if not (a.log and a.month): raise SystemExit('need --log and --month (or --demo)')
    out = [f'# Paper trading vs model: {a.month}, size stage {a.stage:.2f} of full (full = long {WL * SCALE:.2f}x / short {WS * SCALE:.2f}x)\n']
    df = load_log(a.log, a.month); live_stats(df, out); realistic_check(df, out); carry = None
    if a.carry_in: q, p_ = a.carry_in.split('@'); carry = (float(q), float(p_))
    compare(df, out, a.month, a.stage, a.mark_price, carry)
    txt = '\n'.join(out); print(txt)
    if a.out: open(a.out, 'w').write(txt)
