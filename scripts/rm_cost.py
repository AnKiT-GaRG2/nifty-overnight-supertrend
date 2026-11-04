"""COST line: turnover/cost reduction on the baseline (see PROTOCOL_CHANGES.md, written before the run). Train selection, one validation look.
Run: <venv>/bin/python scripts/rm_cost.py [train|validate]"""
import os, sys, json, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rm_ideas import *

GRIDS = {'T1': {'n': [10, 14, 20], 'm': [2.5, 3.0, 3.5, 4.0]}, 'T2': {}, 'T4': {'tf': [30, 60], 'n': [10, 14, 20], 'm': [2.5, 3.0, 3.5]}}
def cells(i):
    g = GRIDS[i]
    return [{}] if not g else [dict(zip(g, v)) for v in itertools.product(*g.values())]
def nbrs(i, c):
    g = GRIDS[i]; return [d for d in cells(i) if d != c and all(abs(g[k].index(d[k]) - g[k].index(c[k])) <= 1 for k in g)]
def interior(i, c):
    g = GRIDS[i]; return all(0 < g[k].index(c[k]) < len(g[k]) - 1 for k in g if len(g[k]) >= 3)
def run(E, S, i, c, cost='floor'):
    t, s = getattr(S, i)(**c); return E.run(t, s, cost=cost)

def main(mode):
    check_protocol(); E = Engine(); S = make_sig(E)
    bt, bs = S.baseline(); B = {c: E.run(bt, bs, cost=c) for c in ('floor', 'real')}
    bm = {w: B['floor'].metrics(w) for w in ('train', 'valid')}; bmr = B['real'].metrics('train')
    print('baseline floor train', fmt(bm['train']), '| valid', fmt(bm['valid']), '| real train Sharpe %.2f' % bmr['Sharpe'])
    out = {}
    for i in GRIDS:
        rows = []
        for c in cells(i):
            m = run(E, S, i, c).metrics('train'); mr = run(E, S, i, c, 'real').metrics('train'); trial_log(i, c, 'train', m)
            rows.append(dict(cell=c, Sharpe=m['Sharpe'], CAGR=m['CAGR'], MaxDD=m['MaxDD'], tr=m['TradesPerYr'], drag=m['CostDrag%/yr'], ShReal=mr['Sharpe']))
        sh = {json.dumps(r['cell']): r['Sharpe'] for r in rows}
        for r in rows:
            nb = nbrs(i, r['cell']); r['nbr_mean'] = float(np.mean([sh[json.dumps(n)] for n in nb] + [r['Sharpe']]))
            r['nbr_beat'] = float(np.mean([sh[json.dumps(n)] > bm['train']['Sharpe'] for n in nb])) if nb else float(r['Sharpe'] > bm['train']['Sharpe'])
        cand = [r for r in rows if interior(i, r['cell'])]
        best = max(cand, key=lambda r: r['nbr_mean'])
        ok = (best['CAGR'] > bm['train']['CAGR'] and best['Sharpe'] >= bm['train']['Sharpe'] + 0.05 and best['MaxDD'] >= -0.15 and best['nbr_beat'] >= 0.7 and best['ShReal'] > bmr['Sharpe'])
        out[i] = dict(rows=rows, best=best, passed=bool(ok))
        print(f"\n{i}: grid train results (CAGR / MaxDD / Sharpe / trades-yr / cost drag %/yr):")
        for r in rows: print('  ', r['cell'], f"{r['CAGR']:.1%} {r['MaxDD']:.1%} {r['Sharpe']:.2f} {r['tr']:.0f} {r['drag']:.1f}  nbr_beat {r['nbr_beat']:.0%}")
        print(f"  chosen {best['cell']}: CAGR {best['CAGR']:.1%} MaxDD {best['MaxDD']:.1%} Sharpe {best['Sharpe']:.2f} nbr_beat {best['nbr_beat']:.0%} real-cost Sharpe {best['ShReal']:.2f} -> {'PASS' if ok else 'fail'}")
    json.dump(out, open(f'{RES}/cost_train.json', 'w'), indent=1, default=float)
    if mode == 'validate':
        vp = f'{RES}/validation_looks.json'; L = json.load(open(vp))
        for i, v in out.items():
            if not v['passed']: continue
            if L.get(i, 0) >= 2: continue
            L[i] = L.get(i, 0) + 1; json.dump(L, open(vp, 'w'), indent=1)
            m = run(E, S, i, v['best']['cell']).metrics('valid'); ok = m['CAGR'] > bm['valid']['CAGR'] and m['Sharpe'] >= bm['valid']['Sharpe'] and m['MaxDD'] >= -0.15
            print(f"VALIDATION {i} {v['best']['cell']}: {fmt(m)} -> {'PASS' if ok else 'fail'} (baseline valid {fmt(bm['valid'])})")
if __name__ == '__main__': main(sys.argv[1] if len(sys.argv) > 1 else 'train')
