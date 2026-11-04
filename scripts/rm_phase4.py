"""Roadmap Phase 4: risk layer on the surviving signal (baseline Supertrend), gap-risk study, guardrails, spec freeze (G4).
Run: <venv>/bin/python scripts/rm_phase4.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rm_ideas import *

def risk_arrays(E, S, k, tv=None):
    sd = k * S.atr15 * E.mult                                   # stop distance in futures points (ATR of 15-min bars)
    if tv is None: return np.ones(E.N), sd
    dret = pd.Series(S.D['close'].values, index=S.D.index).pct_change()
    vol = dret.rolling(20).std() * np.sqrt(252); scale = np.minimum(1.0, tv / vol).shift(1).fillna(1.0).values   # previous completed day only
    return scale[S.dc], sd

def cfg_run(E, S, k, tv=None, ov=0, dd=False, dl=0.0, cost='floor', delay=0):
    t, _ = S.B2(80, 'high'); ts, sd = risk_arrays(E, S, k, tv)     # surviving signal: Supertrend + VIX-percentile filter (B2h, p=80 validated)
    return E.run(t, ts, sd, cost=cost, risk=0.0075, min_chg=2, ov_cap=ov, dd_brake=dd, dl_lim=dl, delay=delay)

def earns(m, stage): return (m['Sharpe'] >= stage['Sharpe'] + 0.02) and (m['MaxDD'] >= stage['MaxDD'] + 0.0025)

def pick(rows, key_cells):
    """plateau rule on a 1-D grid: best mean(self+neighbours) Sharpe"""
    sh = [r['Sharpe'] for r in rows]
    for i, r in enumerate(rows):
        nb = [sh[j] for j in (i - 1, i, i + 1) if 0 <= j < len(sh)]; r['nbr_mean'] = float(np.mean(nb))
    inter = rows[1:-1] if len(rows) >= 3 else rows        # interior cells only (addendum 2)
    return max(inter, key=lambda r: r['nbr_mean'])

def main():
    check_protocol(); E = Engine(); S = make_sig(E); out = {}
    bt, bs = S.baseline(); RB = E.run(bt, bs, cost='floor'); btr = RB.metrics('train'); print('baseline (no risk layer) train', fmt(btr))
    # ---- gap risk on the train set
    d = S.D; gap = (d['open'] / d['close'].shift(1) - 1)[SPLITS['train'][0]:SPLITS['train'][1]]
    full_notional_loss = gap.abs()                                    # at 1x notional a gap of g costs g of capital
    out['gap'] = dict(n=int(len(gap)), p_gap_down_1pct=float((gap < -0.01).mean()), n_gap_down_1pct=int((gap < -0.01).sum()),
                      p_gap_up_1pct=float((gap > 0.01).mean()), worst=float(gap.min()), q01=float(gap.quantile(0.01)), q99=float(gap.quantile(0.99)),
                      n_abs_gt_1pct=int((gap.abs() > 0.01).sum()))
    print('gap study (train, spot 09:15 open vs prior close):', out['gap'])
    # ---- stage 1: stop + risk sizing, grid k
    rows = []
    for k in (2.0, 2.5, 3.0):
        R = cfg_run(E, S, k); m = R.metrics('train'); trial_log('P4_k', {'k': k}, 'train', m)
        rows.append(dict(k=k, Sharpe=m['Sharpe'], MaxDD=m['MaxDD'], CAGR=m['CAGR'], TradesPerYr=m['TradesPerYr'], MaxLossStop=m.get('MaxLossAtStop'), MaxLossGap=m.get('MaxLossWithGap')))
        print('k', k, fmt(m), 'max loss @stop', m.get('MaxLossAtStop'), 'with gap', m.get('MaxLossWithGap'))
    kb = pick(rows, 'k'); k = kb['k']; out['k_grid'] = rows; out['k'] = k; print('chosen k (plateau centre):', k)
    stage = cfg_run(E, S, k).metrics('train'); cur = dict(tv=None, ov=0, dd=False, dl=0.0); log = [('stop+sizing k=%.1f' % k, stage)]
    # ---- stage 2: vol targeting
    rows = []
    for tv in (0.12, 0.15, 0.18):
        m = cfg_run(E, S, k, tv=tv).metrics('train'); trial_log('P4_tv', {'tv': tv}, 'train', m); rows.append(dict(tv=tv, Sharpe=m['Sharpe'], MaxDD=m['MaxDD'], CAGR=m['CAGR']))
        print('tv', tv, fmt(m))
    tb = pick(rows, 'tv'); out['tv_grid'] = rows
    m = cfg_run(E, S, k, tv=tb['tv']).metrics('train')
    keep = earns(m, stage); out['tv_kept'] = bool(keep); out['tv_best'] = tb['tv']
    print('vol targeting', tb['tv'], 'train', fmt(m), 'vs stage', fmt(stage), '-> KEEP' if keep else '-> dropped')
    if keep: cur['tv'] = tb['tv']; stage = m; log.append(('vol target %.0f%%' % (tb['tv'] * 100), m))
    # ---- stage 3: overnight cap
    m = cfg_run(E, S, k, cur['tv'], ov=8).metrics('train'); trial_log('P4_ov', {'ov': 8}, 'train', m)
    keep = earns(m, stage); out['ov_kept'] = bool(keep); print('overnight cap 8', fmt(m), '-> KEEP' if keep else '-> dropped')
    if keep: cur['ov'] = 8; stage = m; log.append(('overnight cap 8 lots', m))
    # ---- stage 4: drawdown brake
    m = cfg_run(E, S, k, cur['tv'], cur['ov'], dd=True).metrics('train'); trial_log('P4_dd', {'dd': True}, 'train', m)
    keep = earns(m, stage); out['dd_kept'] = bool(keep); print('dd brake', fmt(m), '-> KEEP' if keep else '-> dropped')
    if keep: cur['dd'] = True; stage = m; log.append(('drawdown brake', m))
    # ---- stage 5: daily loss limit
    m = cfg_run(E, S, k, cur['tv'], cur['ov'], cur['dd'], dl=0.015).metrics('train'); trial_log('P4_dl', {'dl': 0.015}, 'train', m)
    keep = earns(m, stage); out['dl_kept'] = bool(keep); print('daily loss limit', fmt(m), '-> KEEP' if keep else '-> dropped')
    if keep: cur['dl'] = 0.015; stage = m; log.append(('daily loss limit 1.5%', m))
    out['spec'] = dict(signal='Supertrend(14,3) Wilder ATR 15-min spot, long-only, stand aside when prior-day India VIX 252d percentile > 80 (B2h)', k=k, **cur); out['train_stages'] = [(n, {kk: float(v) for kk, v in m.items() if kk in ('Sharpe', 'MaxDD', 'CAGR', 'TradesPerYr')}) for n, m in log]
    # ---- validation look (risk layer): rule pre-declared in PROTOCOL_CHANGES.md
    vp = f'{RES}/validation_looks.json'; L = json.load(open(vp)) if os.path.exists(vp) else {}
    if L.get('RISK', 0) >= 2: raise SystemExit('risk layer validation looks exhausted')
    L['RISK'] = L.get('RISK', 0) + 1; json.dump(L, open(vp, 'w'), indent=1)
    R = cfg_run(E, S, k, cur['tv'], cur['ov'], cur['dd'], cur['dl']); m = R.metrics('valid'); mb = RB.metrics('valid')
    ok = (m['MaxDD'] >= mb['MaxDD'] - 1e-9) and (m.get('MaxLossAtStop', 0) <= 0.01)
    out['validation'] = dict(passed=bool(ok), metrics={kk: float(v) for kk, v in m.items()}, baseline={kk: float(v) for kk, v in mb.items()})
    print('VALIDATION risk layer:', fmt(m), 'maxloss@stop', m.get('MaxLossAtStop'), 'gap', m.get('MaxLossWithGap'), '| baseline', fmt(mb), '->', 'PASS' if ok else 'fail')
    json.dump(out, open(f'{RES}/phase4_results.json', 'w'), indent=1, default=float)
    if ok:
        spec = dict(out['spec'], frozen='2026-11-03', protocol_sha=open(f'{RES}/protocol.lock').read().strip(), dataset_sha=json.load(open(f'{DATA}/rm/dataset_version.json'))['sha256'])
        json.dump(spec, open(f'{RES}/FROZEN_SPEC.json', 'w'), indent=1); print('G4: spec frozen ->', spec)
if __name__ == '__main__': main()
