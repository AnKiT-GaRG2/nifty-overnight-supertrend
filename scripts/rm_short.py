"""Short-side roadmap S0-S5 (see PROTOCOL_CHANGES.md 'SH' line, written before this ran).
Usage: <venv>/bin/python scripts/rm_short.py train      # S1-S4 on train only, prints stage tables, freezes the short spec
       <venv>/bin/python scripts/rm_short.py validate   # S5: ONE validation look + descriptive test/full"""
import os, sys, json, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rm_ideas import *
from rm_signals import supertrend

WIN = [('2018-09-01', '2018-12-31'), ('2020-02-20', '2020-04-30')]
class SH:
    def __init__(s):
        s.E = Engine(); s.S = make_sig(s.E); E, S = s.E, s.S
        s.D = S.D; s.dc = S.dc; s.N = E.N; s.red = (S.st == -1)
        s.int_d = pd.Series(E.cal * RF / 365.0, index=E.days)
        c = pd.Series(S.D['close'].values, index=S.D.index); s.c = c
        s.win_mask = np.zeros(len(E.days), bool)
        for a, z in WIN: s.win_mask |= (E.days >= pd.Timestamp(a)) & (E.days <= pd.Timestamp(z))
    # ---------- permissions (daily, previous completed day) -------------------------------------------
    def perm(s, rule, v):
        S = s.S; D = s.D
        if rule == 'S2.1': return S.d2b(D['close'].values) < S.d2b(S.sma_daily(v))
        if rule == 'S2.2':
            lh = (D['high'] < D['high'].shift(1)).values.astype(float)
            return (S.d2b(lh) == 1) & (S.d2b(D['close'].values) < S.d2b(S.sma_daily(v)))
        if rule == 'S2.3':
            r = c = s.c.pct_change(); r5 = r.rolling(5).std(); r20 = r.rolling(20).std(); return S.d2b((r5 / r20).values) > v
        if rule == 'S2.4': return S._vixpct() >= v
        raise ValueError(rule)
    GRID = {'S2.1': [100, 150, 200, 250], 'S2.2': [20, 50, 100], 'S2.3': [1.0, 1.1, 1.25, 1.5], 'S2.4': [50, 60, 67, 75, 80]}
    # ---------- short target builders -----------------------------------------------------------------
    def base_short(s, permmask, ms=3.0):
        st = s.S.st if ms == 3.0 else supertrend(s.S.h, s.S.l, s.S.c, 14, ms)[0]
        return np.where((st == -1) & permmask, -1, 0).astype(np.int8)
    def breakdown(s, b):  # S3.2: enter only on a close below the prior day's low while prior-day VIX is rising
        S = s.S; low1 = S.d2b(s.D['low'].values); v = S.vix.reindex(s.D.index).ffill().values
        rising = S.d2b(v, 1) > S.d2b(v, 2); trig = (S.c < low1) & rising
        out = np.zeros(s.N, np.int8); on = False
        for i in range(s.N):
            if b[i] == 0: on = False
            elif not on and trig[i]: on = True
            out[i] = -1 if (on and b[i] == -1) else 0
        return out
    def time_stop(s, b, n):  # S3.3
        S = s.S; c = s.c; newlow = (c < c.shift(1).rolling(10).min()).values.astype(float); rec = S.d2b(newlow) == 1
        out = np.zeros(s.N, np.int8); cnt = 0; dead = False; prevday = -1
        for i in range(s.N):
            if b[i] == 0: cnt = 0; dead = False
            if b[i] == -1 and not dead:
                if s.dc[i] != prevday and out[i - 1] == -1 and i > 0:
                    cnt += 1
                    if cnt >= n and not rec[i]: dead = True
                out[i] = 0 if dead else -1
            prevday = s.dc[i]
            if b[i] == -1 and out[i] == -1 and (i == 0 or out[i - 1] != -1): cnt = 0
        return out
    def target(s, b, k):  # S3.4
        atr = s.S.d2b(s.S.atr_daily(14)); out = np.zeros(s.N, np.int8); entry = None; dead = False
        for i in range(s.N):
            if b[i] == 0: entry = None; dead = False
            if b[i] == -1 and not dead:
                if entry is None: entry = s.S.c[i]
                if s.S.c[i] <= entry - k * atr[i]: dead = True; out[i] = 0
                else: out[i] = -1
        return out
    def intraday(s, b): return np.where(s.S.k >= 23, 0, b).astype(np.int8)
    # ---------- runs ------------------------------------------------------------------------------------
    def run_short(s, t, risk=0.0, k=2.5, cap=0, ov=0, cost='floor'):
        sd = k * s.S.atr15 * s.E.mult if risk > 0 else None
        return s.E.run(t, None, sd, cost=cost, risk=risk, max_lots=cap, ov_cap=ov)
    def leg_metrics(s, R, w):
        a, z = SPLITS[w]; ex = pd.Series(R.net_d, index=s.E.days)[a:z]; m = metrics_from(ex, R, a, z, ex)
        return m
    def capture(s, R):
        a, z = SPLITS['train']; net = pd.Series(R.net_d, index=s.E.days)[a:z]; wm = s.win_mask[(s.E.days >= pd.Timestamp(a)) & (s.E.days <= pd.Timestamp(z))]
        yrs = len(net) / 252; inside = net[wm].sum() / yrs; outside = net[~wm].sum() / yrs
        return dict(capture=inside, outside=outside, upyear_cost=max(0.0, -outside), balance=inside - max(0.0, -outside))
    def merged(s, Rshort, Rlong, w, short_w=1.0):
        a, z = SPLITS[w]; net = pd.Series(Rlong.net_d, index=s.E.days) + short_w * pd.Series(Rshort.net_d, index=s.E.days)
        ex = net[a:z]; tot = ex + s.int_d[a:z]; return metrics_from(tot, None, None, None, ex)

def f(m): return f"CAGR {m['CAGR']:.1%} MaxDD {m['MaxDD']:.1%} Sharpe {m['Sharpe']:.2f}"

def train():
    check_protocol(); X = SH(); E = X.E; rep = []; P = lambda *a: (print(*a), rep.append(' '.join(str(x) for x in a)))
    BL = E.run(*X.S.baseline(), cost='floor'); out = {}
    P('# Short-side roadmap results (train-only selection; see PROTOCOL_CHANGES.md)\n')
    # ---- S0 (diagnostic, already run): record
    P('## S0 flat-time diagnostic (train): shorts earn +5.4 bp/day while Supertrend is red (+2.4 bp excluding Feb-Apr 2020); about 1.9 bp/day of that is the synthetic basis decay. Gate (mean < 0 for a long outside Mar 2020): borderline pass, mostly carry.\n')
    # ---- S1 benchmarks
    S1 = X.run_short(X.base_short(np.ones(X.N, bool)), cost='floor'); m1 = X.leg_metrics(S1, 'train'); m1x = X.capture(S1)
    P('## S1 naive shorts (benchmark, never kept)'); P(f"- S1.1/S1.2 short leg alone, train: {f(m1)}, trades/yr {m1['TradesPerYr']:.0f}, win {m1['WinRate']:.0%}; sell-off capture {m1x['capture']:.1%}/yr, outside-window P&L {m1x['outside']:.1%}/yr, balance {m1x['balance']:.1%}/yr")
    out['S1'] = dict(**{k: float(v) for k, v in m1.items() if isinstance(v, (int, float, np.floating))}, **m1x)
    # ---- S2
    P('\n## S2 permission rules (train; short leg at full size, no stop)'); best = {}
    for rule, grid in X.GRID.items():
        rows = {}
        for v in grid:
            R = X.run_short(X.base_short(X.perm(rule, v))); m = X.leg_metrics(R, 'train'); cp = X.capture(R); trial_log('SH_' + rule, {'v': v}, 'train', m)
            rows[v] = dict(Sharpe=m['Sharpe'], MaxDD=m['MaxDD'], CAGR=m['CAGR'], tr=m['TradesPerYr'], **cp, timeshort=m['TimeInMkt'], R=R)
        idx = list(rows); inter = idx[1:-1] if len(idx) >= 3 else idx
        for i, v in enumerate(idx):
            nb = [rows[idx[j]]['Sharpe'] for j in (i - 1, i, i + 1) if 0 <= j < len(idx)]; rows[v]['nbr_mean'] = float(np.mean(nb)); rows[v]['nbr_pos'] = all(x > 0 for x in nb)
        P(f"\n{rule}: cell -> short-leg train CAGR / MaxDD / Sharpe / trades-yr / capture / outside P&L / time short")
        for v, r in rows.items(): P(f"   {v}: {r['CAGR']:.1%} {r['MaxDD']:.1%} {r['Sharpe']:.2f} {r['tr']:.0f} {r['capture']:.1%} {r['outside']:.1%} {r['timeshort']:.0%}  nbrs>0:{r['nbr_pos']}")
        cand = [v for v in inter if rows[v]['nbr_pos'] and rows[v]['capture'] > rows[v]['upyear_cost']]
        if cand:
            b = max(cand, key=lambda v: rows[v]['nbr_mean']); best[rule] = (b, rows[b]); P(f"   -> chosen {b} (neighbour-mean Sharpe {rows[b]['nbr_mean']:.2f}, balance {rows[b]['balance']:.1%}/yr)")
        else: P('   -> no cell passes (all neighbours Sharpe>0 and capture > up-year cost): rule fails')
    P('\nS2.5 breadth: not testable (no equity bhavcopy data in repo).')
    if not best:
        P('\n**No permission rule passes the train gates: short side stops here (long-only baseline stays).**'); open(f'{RES}/SHORT_SIDE_REPORT.md', 'w').write('\n'.join(rep)); json.dump({'stopped': 'S2'}, open(f'{RES}/short_spec.json', 'w')); return
    win_rule = max(best, key=lambda r: best[r][1]['balance']); wv = best[win_rule][0]; base_mask = X.perm(win_rule, wv)
    P(f"\n**S2 winner: {win_rule} = {wv}**")
    # pairing check
    others = sorted([r for r in best if r != win_rule], key=lambda r: -best[r][1]['balance'])
    if others:
        o = others[0]; ov = best[o][0]; Rp = X.run_short(X.base_short(base_mask & X.perm(o, ov))); mp = X.leg_metrics(Rp, 'train'); ms = best[win_rule][1]['Sharpe']; mo = best[o][1]['Sharpe']
        gi = list(X.GRID[win_rule]); go = list(X.GRID[o]); ia, io = gi.index(wv), go.index(ov); wins_ = tot = 0
        for da in (-1, 0, 1):
            for do in (-1, 0, 1):
                ja, jo = ia + da, io + do
                if 0 <= ja < len(gi) and 0 <= jo < len(go):
                    Rq = X.run_short(X.base_short(X.perm(win_rule, gi[ja]) & X.perm(o, go[jo]))); sh = X.leg_metrics(Rq, 'train')['Sharpe']
                    sa = X.leg_metrics(X.run_short(X.base_short(X.perm(win_rule, gi[ja]))), 'train')['Sharpe']; so = X.leg_metrics(X.run_short(X.base_short(X.perm(o, go[jo]))), 'train')['Sharpe']
                    tot += 1; wins_ += sh > max(sa, so)
        pair_ok = mp['Sharpe'] > max(ms, mo) and wins_ / max(tot, 1) >= 0.7
        P(f"- Pair {win_rule}+{o}: Sharpe {mp['Sharpe']:.2f} vs {ms:.2f} / {mo:.2f}; pair beats both in {wins_}/{tot} neighbour cells -> {'KEEP pair' if pair_ok else 'single rule only'}")
        if pair_ok: base_mask = base_mask & X.perm(o, ov); win_rule = win_rule + '+' + o
    R2 = X.run_short(X.base_short(base_mask)); m2 = X.leg_metrics(R2, 'train'); P(f"- S2 system short leg train: {f(m2)}, trades/yr {m2['TradesPerYr']:.0f}")
    ref = dict(Sharpe=m2['Sharpe'], MaxDD=m2['MaxDD'])
    # ---- S3
    P('\n## S3 entry/exit variants (each vs S2 winner, train short-leg Sharpe; need +0.05 and no worse MaxDD)'); keep = []
    b0 = X.base_short(base_mask)
    variants = {'S3.1': [(2.0, lambda: X.base_short(base_mask, 2.0)), (2.5, lambda: X.base_short(base_mask, 2.5))],
                'S3.2': [(None, lambda: X.breakdown(b0))],
                'S3.3': [(n, (lambda n=n: X.time_stop(b0, n))) for n in (3, 5, 8)],
                'S3.4': [(k, (lambda k=k: X.target(b0, k))) for k in (1.5, 2.0, 3.0)],
                'S3.5': [(None, lambda: X.intraday(b0))]}
    for name, cells_ in variants.items():
        res = []
        for v, fn in cells_:
            R = X.run_short(fn()); m = X.leg_metrics(R, 'train'); trial_log('SH_' + name, {'v': v}, 'train', m); res.append((v, m, R)); P(f"   {name} {v}: {f(m)} trades/yr {m['TradesPerYr']:.0f}")
        bestv = max(res, key=lambda x: x[1]['Sharpe'])
        ok = bestv[1]['Sharpe'] >= ref['Sharpe'] + 0.05 and bestv[1]['MaxDD'] >= ref['MaxDD'] - 1e-9 and (len(res) < 3 or sum(r[1]['Sharpe'] > ref['Sharpe'] for r in res) >= 2)
        P(f"   -> {name} best {bestv[0]} Sharpe {bestv[1]['Sharpe']:.2f} vs {ref['Sharpe']:.2f}: {'KEEP candidate' if ok else 'drop'}")
        if ok: keep.append((name, bestv[0], bestv[1]['Sharpe']))
    keep = sorted(keep, key=lambda x: -x[2])[:2]; P(f"- Kept at most two: {keep}")
    def build(keep):
        b = X.base_short(base_mask); ms = 3.0
        for n, v, _ in keep:
            if n == 'S3.1': b = X.base_short(base_mask, v); ms = v
        for n, v, _ in keep:
            if n == 'S3.2': b = X.breakdown(b)
            if n == 'S3.3': b = X.time_stop(b, v)
            if n == 'S3.4': b = X.target(b, v)
            if n == 'S3.5': b = X.intraday(b)
        return b
    tfin = build(keep)
    if len(keep) == 2:
        Rc = X.run_short(tfin); mc = X.leg_metrics(Rc, 'train'); best1 = max(keep, key=lambda x: x[2])[2]
        P(f"- Combined two S3 changes: {f(mc)} (best single Sharpe {best1:.2f})")
        if mc['Sharpe'] < best1: keep = keep[:1]; tfin = build(keep); P(f"- combination worse than best single -> keep only {keep}")
    # ---- S4 sizing
    P('\n## S4 short sizing (risk 0.5% of capital at the stop, k=2.5 x ATR; train short leg)')
    szres = {}
    for cap in (6, 8, 12):
        for ov in (0, 6):
            if ov and cap < ov: continue
            R = X.run_short(tfin, risk=0.005, k=2.5, cap=cap, ov=ov); m = X.leg_metrics(R, 'train'); szres[(cap, ov)] = (m, R); trial_log('SH_S4', {'cap': cap, 'ov': ov}, 'train', m)
            P(f"   cap {cap} lots, overnight cap {ov or 'none'}: {f(m)}, max loss at stop {m.get('MaxLossAtStop', 0):.2%}, with gap {m.get('MaxLossWithGap', 0):.2%}")
    cap, ov = 8, 0
    if szres[(8, 6)][0]['Sharpe'] >= szres[(8, 0)][0]['Sharpe'] - 1e-9: ov = 6
    P(f"- Frozen convention: cap {cap}, overnight cap {ov or 'none'} (overnight cap kept only if train short Sharpe does not fall)")
    Rs = szres[(cap, ov)][1]; ms_ = szres[(cap, ov)][0]
    # ---- report metrics for the short leg
    a, z = SPLITS['train']; sn = pd.Series(Rs.net_d, index=E.days)[a:z]; ln = pd.Series(BL.net_d, index=E.days)[a:z]
    tr = Rs.trades; sel = (E.days[Rs.trade_day] >= pd.Timestamp(a)) & (E.days[Rs.trade_day] <= pd.Timestamp(z)); T = tr[sel]
    cp = X.capture(Rs); ex_mar = ~((sn.index >= '2020-02-20') & (sn.index <= '2020-04-30')); mx = metrics_from(sn[ex_mar], None, None, None, sn[ex_mar])
    P('\n## Short-leg metrics on train (frozen S2-S4 spec)')
    P(f"- Short-leg Sharpe {ms_['Sharpe']:.2f}, MaxDD {ms_['MaxDD']:.1%}, CAGR contribution {ms_['CAGR']:.1%}; excluding Feb-Apr 2020: Sharpe {mx['Sharpe']:.2f}, CAGR {mx['CAGR']:.1%}")
    P(f"- Sell-off capture {cp['capture']:.1%}/yr vs up-year cost {cp['upyear_cost']:.1%}/yr (outside-window P&L {cp['outside']:.1%}/yr)")
    P(f"- Time short {ms_['TimeInMkt']:.0%} of days; trades/yr {ms_['TradesPerYr']:.0f}; hit rate {ms_['WinRate']:.0%}; avg win/avg loss {ms_['AvgWin/AvgLoss']:.2f}")
    P(f"- Worst loss on a short incl. gap: {ms_.get('MaxLossWithGap', 0):.2%} of capital; at stop price {ms_.get('MaxLossAtStop', 0):.2%}; correlation of short-leg and long-leg daily returns: {sn.corr(ln):+.2f}")
    by = sn.groupby(sn.index.year).sum(); P('- Short-leg P&L by train year (sum of daily returns): ' + ', '.join(f'{y}: {v:+.1%}' for y, v in by.items()))
    P('- Same year table excluding Feb-Apr 2020: ' + ', '.join(f'{y}: {v:+.1%}' for y, v in sn[ex_mar].groupby(sn[ex_mar].index.year).sum().items()))
    # train gates
    nb_ok = best[win_rule.split('+')[0]][1]['nbr_pos']
    gates = {'short-leg Sharpe > 0 across neighbour grid (S2 rule)': nb_ok, 'sell-off capture > up-year cost': cp['capture'] > cp['upyear_cost'], 'short Sharpe > 0 on train': ms_['Sharpe'] > 0,
             'no short loses > 1% incl. gaps (train)': ms_.get('MaxLossWithGap', 0) <= 0.01}
    P('\n## Train gates'); [P(f"- {k}: {'PASS' if v else 'FAIL'}") for k, v in gates.items()]
    spec = dict(rule=win_rule, value=wv, keep=keep, cap=cap, ov=ov, risk=0.005, k=2.5, gates={k: bool(v) for k, v in gates.items()}, passed_train=bool(all(gates.values())))
    json.dump(spec, open(f'{RES}/short_spec.json', 'w'), indent=1, default=str); open(f'{RES}/SHORT_SIDE_REPORT.md', 'w').write('\n'.join(rep))
    P('\nSpec saved. Run "validate" for the single S5 validation look.' if spec['passed_train'] else '\nTrain gates failed: short side stops (no validation look taken).')

def validate():
    check_protocol(); sp = json.load(open(f'{RES}/short_spec.json'))
    if 'rule' not in sp: raise SystemExit('short side stopped at S2')
    if not sp['passed_train']: raise SystemExit('train gates failed; no validation look')
    vp = f'{RES}/validation_looks.json'; L = json.load(open(vp))
    if L.get('SH', 0) >= 1: raise SystemExit('the single S5 validation look was already used')
    L['SH'] = 1; json.dump(L, open(vp, 'w'), indent=1)
    X = SH(); E = X.E; keys = sp['rule'].split('+'); mask = np.ones(X.N, bool); v = sp['value']
    mask = X.perm(keys[0], float(v) if '.' in str(v) else int(v))
    b = X.base_short(mask)
    for n, vv, _ in sp['keep']:
        if n == 'S3.1': b = X.base_short(mask, float(vv))
    for n, vv, _ in sp['keep']:
        if n == 'S3.2': b = X.breakdown(b)
        if n == 'S3.3': b = X.time_stop(b, int(vv))
        if n == 'S3.4': b = X.target(b, float(vv))
        if n == 'S3.5': b = X.intraday(b)
    Rs = X.run_short(b, risk=sp['risk'], k=sp['k'], cap=sp['cap'], ov=sp['ov']); BL = E.run(*X.S.baseline(), cost='floor')
    rep = []; P = lambda *a: (print(*a), rep.append(' '.join(str(x) for x in a)))
    P('\n## S5 merged system vs no-shorts baseline (validation = the ONE look; test/full are descriptive, window already opened for this project)\n')
    P('| Window | Baseline CAGR/DD/Sharpe | Merged CAGR/DD/Sharpe | Short leg alone CAGR/DD/Sharpe | Short-leg corr w/ long |'); P('|---|---|---|---|---|')
    res = {}
    for w in ('train', 'valid', 'test', 'full'):
        a, z = SPLITS[w]; mb = BL.metrics(w); mm = X.merged(Rs, BL, w); msl = X.leg_metrics(Rs, w); cr = pd.Series(Rs.net_d, index=E.days)[a:z].corr(pd.Series(BL.net_d, index=E.days)[a:z])
        P(f"| {w} | {f(mb)} | {f(mm)} | {f(msl)} | {cr:+.2f} |"); res[w] = (mb, mm, msl)
    mb, mm, msl = res['valid']; ok_v = mm['Sharpe'] > mb['Sharpe'] and mm['MaxDD'] >= mb['MaxDD'] - 1e-9
    gap = msl.get('MaxLossWithGap', 0); full = res['full'][1]
    P(f"\n- Validation: merged beats no-shorts on Sharpe ({mm['Sharpe']:.2f} vs {mb['Sharpe']:.2f}) and drawdown ({mm['MaxDD']:.1%} vs {mb['MaxDD']:.1%}) -> {'PASS' if ok_v else 'FAIL'}")
    P(f"- Worst short loss incl. gap, validation: {gap:.2%}; merged max drawdown full period {full['MaxDD']:.1%} (limit -15%)")
    P('- Short leg with and without the Feb-Apr 2020 crash and up-year cost were reported in the train section.')
    open(f'{RES}/SHORT_SIDE_REPORT.md', 'a').write('\n' + '\n'.join(rep)); json.dump(dict(valid_pass=bool(ok_v)), open(f'{RES}/short_validation.json', 'w'))
if __name__ == '__main__':
    {'train': train, 'validate': validate}[sys.argv[1] if len(sys.argv) > 1 else 'train']()
