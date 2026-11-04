"""LEV line: risk factors on the leveraged long/short combo (see PROTOCOL_CHANGES.md). Run: <venv>/bin/python scripts/rm_lev.py"""
import os, sys, json, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rm_ideas import *

E = Engine(); S = make_sig(E); days = E.days
BL = E.run(*S.baseline(), cost='floor'); t, s_ = S.A2(100)
SHR = E.run(np.where(t == -1, -1, 0).astype(np.int8), s_, cost='floor')
L = pd.Series(BL.net_d, index=days); Sh = pd.Series(SHR.net_d, index=days); INT = pd.Series(E.cal * RF / 365.0, index=days)
WL, WS = 2.0, 1.0; base = WL * L + WS * Sh
first = np.where(E.first_b)[0]
vp = pd.Series(S._vixpct()[first], index=days)                       # prior-day VIX percentile
c = pd.Series(S.D['close'].values, index=S.D.index); vol20 = (c.pct_change().rolling(20).std() * np.sqrt(252)).shift(1)

def sc_V(tau): return np.minimum(1.0, tau / vol20).fillna(1.0)
def sc_R(q): return pd.Series(np.where(vp > q, 0.5, 1.0), index=days)
def brake(r, d, pre=None):
    pre = pd.Series(1.0, index=days) if pre is None else pre; out = np.zeros(len(r)); eq = 1.0; peak = 1.0; on = False
    for i, (rv, iv, pv) in enumerate(zip(r.values, INT.values, pre.values)):
        sv = pv * (0.5 if on else 1.0); x = sv * rv; out[i] = x; eq *= (1 + x + iv); peak = max(peak, eq)
        on = (1 - eq / peak) > d if not (eq >= peak) else False
    return pd.Series(out, index=days)
def metr(net, w):
    a, z = SPLITS[w]; ex = net[a:z]; return metrics_from(ex + INT[a:z], None, None, None, ex)
def f(m): return f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"

GR = {'V': ('tau', [0.12, 0.15, 0.18, 0.21]), 'R': ('q', [60, 70, 80, 90]), 'B': ('d', [0.05, 0.075, 0.10, 0.125])}
def apply(kind, v, ret=None, pre=None):
    ret = base if ret is None else ret
    if kind == 'V': return ret * sc_V(v)
    if kind == 'R': return ret * sc_R(v)
    if kind == 'B': return brake(ret, v)
rep = []; Pr = lambda *a: (print(*a), rep.append(' '.join(str(x) for x in a)))
Pr('# Leveraged long/short combo + factors (floor costs; each cell: CAGR / MaxDD / Sharpe)\n')
Pr(f"Base combo (2x baseline long + 1x A2 short): train {f(metr(base,'train'))} | valid {f(metr(base,'valid'))} | test(desc.) {f(metr(base,'test'))} | full {f(metr(base,'full'))}\n")
best = {}
for kind, (pn, grid) in GR.items():
    rows = []
    for v in grid:
        net = apply(kind, v); m = {w: metr(net, w) for w in ('train', 'valid', 'test', 'full')}; trial_log('LEV_' + kind, {pn: v}, 'train', m['train']); rows.append((v, m))
    Pr(f"## Factor {kind} ({pn}) - train | valid | test(desc.) | full")
    for v, m in rows: Pr(f"   {pn}={v}: {f(m['train'])} | {f(m['valid'])} | {f(m['test'])} | {f(m['full'])}")
    ok = lambda m: m['train']['MaxDD'] >= -0.14 and m['valid']['MaxDD'] >= -0.14
    cand = []
    for i in range(1, len(rows) - 1):
        nbs = [rows[j] for j in (i - 1, i, i + 1)]
        if ok(rows[i][1]) and all(n[1]['train']['MaxDD'] >= -0.15 and n[1]['valid']['MaxDD'] >= -0.15 for n in nbs):
            cand.append((float(np.mean([n[1]['train']['CAGR'] for n in nbs])), rows[i]))
    if cand: b = max(cand, key=lambda x: x[0])[1]; best[kind] = b; Pr(f"   -> chosen {pn}={b[0]} (train {f(b[1]['train'])}, valid {f(b[1]['valid'])})")
    else: Pr('   -> no interior cell keeps train and valid drawdown within the buffer (with neighbours): factor fails alone')
# pairs
Pr('\n## Pairs (different factors; each factor at its own chosen cell; also neighbour-robustness shown)')
pairs = {}
for a_, b_ in itertools.combinations(best, 2):
    ret = apply(a_, best[a_][0]); net = apply(b_, best[b_][0], ret=ret) if b_ != 'B' else brake(ret, best[b_][0])
    if a_ == 'B': net = apply(b_, best[b_][0], ret=ret)
    m = {w: metr(net, w) for w in ('train', 'valid', 'test', 'full')}; pairs[(a_, b_)] = m; trial_log('LEV_pair', {'a': a_, 'b': b_}, 'train', m['train'])
    Pr(f"   {a_}+{b_}: {f(m['train'])} | {f(m['valid'])} | {f(m['test'])} | {f(m['full'])}")
Pr('\n## Summary (CAGR / MaxDD / Sharpe)\n'); Pr('| Stack | Train | Valid | Test (desc.) | Full |'); Pr('|---|---|---|---|---|')
Pr(f"| Combo 2x long + 1x short (no factors) | {f(metr(base,'train'))} | {f(metr(base,'valid'))} | {f(metr(base,'test'))} | {f(metr(base,'full'))} |")
for k, (v, m) in best.items(): Pr(f"| + {k} ({GR[k][0]}={v}) | {f(m['train'])} | {f(m['valid'])} | {f(m['test'])} | {f(m['full'])} |")
for (a_, b_), m in pairs.items(): Pr(f"| + {a_} & {b_} | {f(m['train'])} | {f(m['valid'])} | {f(m['test'])} | {f(m['full'])} |")
for nm, ret in (('Reference: baseline long-only', L), ('Reference: plain A2 (1x long + 1x short)', L + Sh)):
    Pr(f"| {nm} | {f(metr(ret,'train'))} | {f(metr(ret,'valid'))} | {f(metr(ret,'test'))} | {f(metr(ret,'full'))} |")
open(f'{RES}/LEV_REPORT.md', 'w').write('\n'.join(rep))
