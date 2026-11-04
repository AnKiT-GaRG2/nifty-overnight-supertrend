"""Idea registry, runner, plateau rule, failure log, validation-look counter, lookahead tests. Roadmap Phases 1-3.
Run with the numba venv: python scripts/rm_ideas.py [train|validate|lookahead]"""
import os, sys, json, hashlib, itertools, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from rm_engine import *; from rm_signals import Sig, supertrend

RES = os.path.join(ROOT, 'results', 'rm'); DATA = os.path.join(ROOT, 'data')

def check_protocol():
    h = hashlib.sha256(open(f'{RES}/PROTOCOL.md', 'rb').read()).hexdigest(); lock = open(f'{RES}/protocol.lock').read().strip()
    if h != lock: raise SystemExit('PROTOCOL.md changed since it was locked; log the reason in PROTOCOL_CHANGES.md and re-lock deliberately')

def load_inputs():
    vix = pd.read_csv(f'{DATA}/vix_ext.csv', parse_dates=['date']).set_index('date')['close']
    spx = pd.read_csv(f'{DATA}/spx.csv', parse_dates=['date']).set_index('date')['close']
    fut = pd.read_csv(f'{DATA}/fut/nifty_fut.csv', parse_dates=['date']); oi = fut.groupby('date')['oi'].sum()
    return vix, spx, oi

def make_sig(E):
    vix, spx, oi = load_inputs(); return Sig(E, vix=vix, spx=spx, oi=oi)

# id: (family, method, grid, hypothesis, expected sign of effect on Sharpe vs baseline)
IDEAS = {
 'A1':  ('trend',   'A1',     {},                                   'Shorts pay in 2022 and 2024-25 sell-offs; short futures also earn the basis', '+'),
 'A2':  ('trend',   'A2',     {'L': [50, 100, 150, 200, 250]},      'Index drift makes shorts lose in bull phases; allow them only below the daily average', '+'),
 'A3':  ('trend',   'A3',     {'n': [7, 10, 14, 20], 'm': [2.0, 2.5, 3.0, 3.5]}, 'Higher-timeframe agreement cuts counter-trend whipsaws', '+'),
 'B1e': ('trend',   'B1_er',  {'n': [10, 20, 30], 'thr': [0.15, 0.2, 0.25, 0.3, 0.35]}, 'Standing aside when daily efficiency ratio is low removes 2022-23 whipsaw', '+'),
 'B1a': ('trend',   'B1_adx', {'n': [10, 14, 20], 'thr': [15, 20, 25, 30]}, 'Standing aside when daily ADX is low removes whipsaw', '+'),
 'B2h': ('trend',   'B2h',    {'p': [60, 70, 80, 90]},              'Trend signals fail in high-vol regimes: stand aside when prior-day VIX percentile is high', '+'),
 'B2l': ('trend',   'B2l',    {'p': [10, 20, 30, 40]},              'Trend signals fail in low-vol regimes: stand aside when prior-day VIX percentile is low', '+'),
 'C1':  ('trend',   'C1',     {'n': [1, 2, 3, 4, 6]},               'Confirmation bars on flips cut turnover; each skipped round trip saves >=0.05%', '+'),
 'D1':  ('time',    'D1',     {},                                   'Intraday-only removes gap risk but may lose the overnight drift', '-'),
 'D2':  ('time',    'D2',     {'orm': [15, 30, 45, 60], 'L': [20, 50, 100, 200]}, 'Early range sets the day direction on trend days', '+'),
 'D3':  ('time',    'D3',     {'first': [0, 1, 2], 'last': [0, 2, 4]}, 'Opening and closing bars are noisy and gap-driven; skip new entries there', '+'),
 'E1':  ('gap',     'E1',     {'small': [0.2, 0.4], 'large': [0.6, 0.8, 1.0, 1.2]}, 'Small gaps fill (fade), large gaps continue (follow)', '+'),
 'F1':  ('meanrev', 'F1',     {'lo': [5, 10, 15, 20], 'ert': [0.2, 0.3, 0.4]}, 'Short-term mean reversion pays in range regimes when trend signals lose', '+'),
 'G1':  ('diag',    'G1',     {},                                   'Diagnostic: long exposure held only overnight (night leg)', '?'),
 'G1b': ('diag',    'G1b',    {},                                   'Diagnostic: long exposure held only intraday (day leg)', '?'),
 'H1':  ('flow',    'H1',     {'n': [1, 2, 3, 5]},                  'Futures OI x price change quadrants add information', '+'),
 'H2':  ('flow',    'H2',     {'thr': [0.0, 0.0025, 0.005, 0.01]},  'US overnight return predicts the gap but is priced into the open (expected to fail)', '-'),
}

def sig_fn(S, idea, **kw):
    fam, meth, grid, hyp, sign = IDEAS[idea]
    if meth == 'B2h': return S.B2(kw['p'], 'high')
    if meth == 'B2l': return S.B2(kw['p'], 'low')
    return getattr(S, meth)(**kw)

def cells(idea):
    grid = IDEAS[idea][2]
    if not grid: return [{}]
    keys = list(grid); return [dict(zip(keys, v)) for v in itertools.product(*[grid[k] for k in keys])]

def neighbours(idea, cell):
    grid = IDEAS[idea][2]; out = []
    for c in cells(idea):
        if c == cell: continue
        if all(abs(grid[k].index(c[k]) - grid[k].index(cell[k])) <= 1 for k in grid): out.append(c)
    return out

def trial_log(idea, cell, split, m):
    p = f'{RES}/trials.json'
    L = json.load(open(p)) if os.path.exists(p) else []
    L.append(dict(idea=idea, cell=cell, split=split, sharpe=float(m['Sharpe']), t=time.strftime('%Y-%m-%d %H:%M:%S'))); json.dump(L, open(p, 'w'))

def run_cell(E, S, idea, cell, cost='floor', **kw):
    t, s = sig_fn(S, idea, **cell); return E.run(t, s, cost=cost, **kw)

def train_idea(E, S, idea, base_tr, results_cache):
    rows = []
    for c in cells(idea):
        R = run_cell(E, S, idea, c); m = R.metrics('train'); results_cache[(idea, json.dumps(c))] = R
        rows.append(dict(cell=c, **{k: m[k] for k in ('Sharpe', 'MaxDD', 'CAGR', 'TradesPerYr', 'CostDrag%/yr')}))
        trial_log(idea, c, 'train', m)
    df = pd.DataFrame(rows); sh = {json.dumps(r['cell']): r['Sharpe'] for r in rows}
    best = None; info = {}
    for r in rows:
        nb = neighbours(idea, r['cell']); vals = [sh[json.dumps(n)] for n in nb] + [r['Sharpe']]
        r['nbr_mean'] = float(np.mean(vals)); r['nbr_beat'] = float(np.mean([sh[json.dumps(n)] > base_tr['Sharpe'] for n in nb])) if nb else float(r['Sharpe'] > base_tr['Sharpe'])
    grid = IDEAS[idea][2]
    def interior(c): return all(0 < grid[k].index(c[k]) < len(grid[k]) - 1 for k in grid if len(grid[k]) >= 3)
    cand = [r for r in rows if r['Sharpe'] > base_tr['Sharpe'] and interior(r['cell'])]
    if cand: best = max(cand, key=lambda r: r['nbr_mean'])
    if best is None: best = max(rows, key=lambda r: r['nbr_mean'])
    ok_a = best['nbr_beat'] >= 0.70; ok_b = best['Sharpe'] > base_tr['Sharpe']; ok_c = best['MaxDD'] >= base_tr['MaxDD'] - 0.02
    ok_d = best['TradesPerYr'] <= 2 * base_tr['TradesPerYr']
    passed = ok_a and ok_b and ok_c and ok_d
    return dict(idea=idea, rows=rows, best=best, passed=passed, checks=dict(plateau=ok_a, sharpe=ok_b, dd=ok_c, turnover=ok_d))

def validation_look(idea, cell, E, S, base_va):
    p = f'{RES}/validation_looks.json'
    L = json.load(open(p)) if os.path.exists(p) else {}
    if L.get(idea, 0) >= 2: raise SystemExit(f'{idea}: validation looks exhausted')
    L[idea] = L.get(idea, 0) + 1; json.dump(L, open(p, 'w'), indent=1)
    R = run_cell(E, S, idea, cell); m = R.metrics('valid'); trial_log(idea, cell, 'valid', m)
    ok = (m['Sharpe'] > base_va['Sharpe']) and (m['MaxDD'] >= base_va['MaxDD'] - 0.02) and (m['CAGR'] > 0)
    return ok, m, R

def pctl(x): return f'{x:.1%}'

def main_train():
    check_protocol(); E = Engine(); S = make_sig(E)
    bt, bs = S.baseline(); RB = E.run(bt, bs, cost='floor'); btr = RB.metrics('train'); bva = RB.metrics('valid')
    print('baseline train', fmt(btr)); print('baseline valid', fmt(bva))
    cache = {}; out = {}
    for idea in IDEAS:
        o = train_idea(E, S, idea, btr, cache); out[idea] = o
        b = o['best']; print(f"{idea:4s} best {b['cell']} train Sharpe {b['Sharpe']:.2f} DD {b['MaxDD']:.1%} tr/yr {b['TradesPerYr']:.0f} nbr_beat {b['nbr_beat']:.0%} -> {'PASS' if o['passed'] else 'fail'} {o['checks']}")
    json.dump({k: {'best': v['best'], 'passed': v['passed'], 'checks': v['checks'], 'rows': v['rows']} for k, v in out.items()}, open(f'{RES}/train_results.json', 'w'), indent=1, default=float)
    return out

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'train'
    if what == 'train': main_train()

PRIOR = {'A1': {}, 'A2': {'L': 50}, 'A3': {'n': 20, 'm': 3.5}, 'B2h': {'p': 90}}
def main_validate():
    check_protocol(); E = Engine(); S = make_sig(E)
    tr = json.load(open(f'{RES}/train_results.json'))
    bt, bs = S.baseline(); RB = E.run(bt, bs, cost='floor'); bva = RB.metrics('valid'); print('baseline valid', fmt(bva))
    out = {}
    for idea, v in tr.items():
        if not v['passed']: continue
        cell = v['best']['cell']
        if idea in PRIOR and PRIOR[idea] == cell: print(idea, cell, 'same as first pick (already validated); no new look'); continue
        ok, m, R = validation_look(idea, cell, E, S, bva)
        out[idea] = dict(cell=cell, passed=bool(ok), Sharpe=m['Sharpe'], MaxDD=m['MaxDD'], CAGR=m['CAGR'], TradesPerYr=m['TradesPerYr'])
        print(f"{idea} {cell} VALID {fmt(m)} -> {'PASS' if ok else 'fail'}")
    json.dump(out, open(f'{RES}/validation_results.json', 'w'), indent=1, default=float)
if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'validate': main_validate()
