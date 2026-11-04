import sys, json, itertools; sys.path.insert(0, 'scripts'); sys.argv = ['x']
exec(open('scripts/rm_fac.py').read().split("if __name__")[0])
# extra candidate factors
nq, gld, krw, jpy = rd('nasdaq'), rd('gold'), rd('krw'), rd('jpy')
FACT.update({
 'NQ':  ([1, 2, 3], lambda x: (prior(nq, 5) * 100 < -x, 'L')),
 'GLD': ([3, 5, 8], lambda x: (prior(gld, 20) * 100 > x, 'L')),
 'KRW': ([1, 2, 3], lambda x: (prior(krw, 20) * 100 > x, 'L')),
 'JPY': ([1, 2, 3], lambda x: (prior(jpy, 20) * 100 < -x, 'L'))})
FAM = {'MC1': 'macro', 'MC2': 'macro', 'MC3': 'macro', 'DXY': 'macro', 'GLD': 'macro', 'KRW': 'emfx', 'NQ': 'global', 'JPY': 'global', 'S1': 'cross', 'T2L': 'trend', 'O3': 'options'}
wt = BASES['NB1 (2.0 / 1.0)']
# precompute daily streams for every factor cell (NB1; NB2 = 0.75 x NB1 exactly, same Sharpe)
STR = {(n, v): apply([(n, v)], *wt) for n, (g, _) in FACT.items() for v in g}; BASE0 = stream(*wt)
def window(net, a, z):
    ex = net[a:z]; return metrics_from(ex + INT[a:z], None, None, None, ex)
def pick(a, z):
    ref = window(BASE0, a, z); chosen = {}
    for n, (grid, _) in FACT.items():
        met = {v: window(STR[(n, v)], a, z) for v in grid}; lift = {v: met[v]['Sharpe'] - ref['Sharpe'] for v in grid}
        inter = grid[1:-1] if len(grid) >= 3 else grid; best = None
        for v in inter:
            i = grid.index(v); nb = [grid[j] for j in (i - 1, i + 1) if 0 <= j < len(grid)]
            if lift[v] >= 0.05 and met[v]['MaxDD'] >= ref['MaxDD'] - 1e-9 and np.mean([lift[x] > 0 for x in nb]) >= 0.7:
                sc = np.mean([lift[v]] + [lift[x] for x in nb])
                if best is None or sc > best[0]: best = (sc, v, lift[v])
        if best: chosen[n] = best
    fam_best = {}
    for n, (sc, v, l) in chosen.items():
        fm = FAM[n]
        if fm not in fam_best or l > fam_best[fm][2]: fam_best[fm] = (n, v, l)
    top = sorted(fam_best.values(), key=lambda x: -x[2])[:2]
    spec = [(n, v) for n, v, _ in top]
    if len(spec) == 2:
        mp = window(apply(spec, *wt), a, z)['Sharpe']; singles = [window(STR[s], a, z)['Sharpe'] for s in spec]
        if mp <= max(singles): spec = [spec[int(np.argmax(singles))]]
    return spec
folds = []; a0 = pd.Timestamp('2020-04-01')
while a0 <= pd.Timestamp('2026-10-31'):
    z0 = min(a0 + pd.DateOffset(months=6) - pd.Timedelta(days=1), pd.Timestamp('2026-10-31')); folds.append((a0, z0, a0 - pd.DateOffset(years=3), a0 - pd.Timedelta(days=1))); a0 += pd.DateOffset(months=6)
rep = []; P = lambda *a: (print(*a), rep.append(' '.join(str(x) for x in a)))
P('# FAC-WF: walk-forward test of factor selection (NB1 = 2.0/1.0; NB2 = 0.75 x NB1 has identical Sharpe)\n'); P('| OOS period | Factors chosen on the prior 3 years |'); P('|---|---|')
parts = {'none': [], 'fixed': [], 'wf': []}; FIX = [('MC1', 2), ('MC3', 15)]; fixed_stream = apply(FIX, *wt)
for a, z, t0, t1 in folds:
    spec = pick(t0, t1); P(f"| {a.date()}..{z.date()} | {spec if spec else 'none'} |")
    parts['none'].append(BASE0[a:z]); parts['fixed'].append(fixed_stream[a:z]); parts['wf'].append((apply(spec, *wt) if spec else BASE0)[a:z])
def stitch(k): return pd.concat(parts[k])
def mm(net, scale=1.0):
    n = net * scale; return metrics_from(n + INT.reindex(n.index), None, None, None, n)
def line(k, scale, sub=None):
    n = stitch(k) if sub is None else stitch(k)[sub[0]:sub[1]]; m = mm(n, scale); return f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
P('\n## Stitched out-of-sample results (CAGR / MaxDD / Sharpe), Apr 2020 - Oct 2026\n'); P('| Base | Stack | Dev-era OOS 2020-04..2023-12 | 2024-01..2026-10 (desc.) | Whole OOS |'); P('|---|---|---|---|---|')
for bn, sc in (('NB1 2.0/1.0', 1.0), ('NB2 1.5/0.75', 0.75)):
    for k, lab in (('none', 'no factors'), ('fixed', 'fixed MC1+MC3 (reference)'), ('wf', 'walk-forward selected')):
        P(f"| {bn} | {lab} | {line(k, sc, ('2020-04-01', '2023-12-31'))} | {line(k, sc, ('2024-01-01', '2026-10-31'))} | {line(k, sc)} |")
m0 = mm(stitch('none')); mw = mm(stitch('wf')); add = (mw['Sharpe'] - m0['Sharpe'] >= 0.1) and (mw['MaxDD'] >= m0['MaxDD'] - 1e-9)
P(f"\nVerdict rule (WF Sharpe >= no-factor + 0.1 and MaxDD not worse): WF {mw['Sharpe']:.2f} vs none {m0['Sharpe']:.2f}; MaxDD {mw['MaxDD']:.1%} vs {m0['MaxDD']:.1%} -> {'PROCESS ADDS VALUE' if add else 'PROCESS DOES NOT ADD VALUE'}")
open(f'{RES}/FAC_WF_REPORT.md', 'w').write('\n'.join(rep))
