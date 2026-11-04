"""FAC line: catalogue factors on two reference bases (see PROTOCOL_CHANGES.md). Usage: rm_fac.py train | validate"""
import os, sys, json, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rm_ideas import *
check_protocol()
E = Engine(); S = make_sig(E); days = E.days; D = S.D
BL = E.run(*S.baseline(), cost='floor'); t, s_ = S.A2(100)
SHR = E.run(np.where(t == -1, -1, 0).astype(np.int8), s_, cost='floor')
L = pd.Series(BL.net_d, index=days); Sh = pd.Series(SHR.net_d, index=days); INT = pd.Series(E.cal * RF / 365.0, index=days)
BASES = {'NB1 (2.0 / 1.0)': (2.0, 1.0), 'NB2 (1.5 / 0.75)': (1.5, 0.75)}

def prior(series, n=None, kind='pct'):
    """series: dated close; value known strictly before day d: use the last observation dated < d, then n-day change"""
    s = series.dropna(); s = s[~s.index.duplicated()]
    if n is not None: s = (s / s.shift(n) - 1) if kind == 'pct' else (s - s.shift(n))
    pos = np.searchsorted(s.index.values, days.values, side='left') - 1
    return pd.Series(np.where(pos >= 0, s.values[np.maximum(pos, 0)], np.nan), index=days)
def rd(name): return pd.read_csv(f'{DATA}/{name}.csv', parse_dates=['date']).set_index('date')['close']
usd, brent, us10, dxy, bn, nf = rd('usdinr'), rd('brent'), rd('us10y'), rd('dxy'), rd('banknifty'), rd('nifty')
vix = pd.read_csv(f'{DATA}/vix_ext.csv', parse_dates=['date']).set_index('date')['close']
dc = pd.Series(D['close'].values, index=D.index)
vol20 = dc.pct_change().rolling(20).std() * np.sqrt(252) * 100
vprem = (vix.reindex(D.index).ffill() - vol20); vprem_pct = vprem.rolling(252, min_periods=60).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True)
FACT = {  # name: (grid values, builder(v) -> (long_scale, short_scale) as daily Series, label)
 'MC1': ([1, 2, 3], lambda x: (prior(usd, 20) * 100 > x, 'L')),
 'MC2': ([10, 15, 20], lambda x: (prior(brent, 20) * 100 > x, 'L')),
 'MC3': ([10, 15, 20, 25], lambda x: (prior(us10, 5, 'diff') * 100 > x, 'L')),
 'DXY': ([1, 1.5, 2], lambda x: (prior(dxy, 20) * 100 > x, 'L')),
 'S1':  ([10, 20, 40], lambda n: ((prior(bn, n) - prior(nf, n)) < 0, 'L')),
 'O3':  ([10, 20, 30], lambda q: (prior(vprem_pct, None) < q, 'B')),
 'T2L': ([100, 150, 200, 250], lambda L_: (prior(dc, None) < dc.rolling(L_).mean().shift(1).reindex(days).values, 'L')),
}
def scales(name, v):
    cond, role = FACT[name][1](v); cond = cond.reindex(days).fillna(False).astype(bool); s = pd.Series(np.where(cond, 0.5, 1.0), index=days)
    return s, (s if role == 'B' else pd.Series(1.0, index=days))
def stream(wl, ws, sl=None, ss=None):
    sl = 1.0 if sl is None else sl; ss = 1.0 if ss is None else ss; return wl * sl * L + ws * ss * Sh
def metr(net, w):
    a, z = SPLITS[w]; ex = net[a:z]; return metrics_from(ex + INT[a:z], None, None, None, ex)
def f(m): return f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
def apply(spec, wl, ws):
    sl = ss = None
    for name, v in spec:
        a, b = scales(name, v); sl = a if sl is None else sl * a; ss = b if ss is None else ss * b
    return stream(wl, ws, sl, ss)

def train():
    rep = []; P = lambda *a: (print(*a), rep.append(' '.join(str(x) for x in a)))
    P('# FAC: catalogue factors on the two reference bases (floor costs; CAGR / MaxDD / Sharpe)\n')
    ref = {b: {w: metr(stream(*wt), w) for w in ('train', 'valid', 'test', 'full')} for b, wt in BASES.items()}
    for b in BASES: P(f"{b}: train {f(ref[b]['train'])} | valid {f(ref[b]['valid'])} | test(desc.) {f(ref[b]['test'])} | full {f(ref[b]['full'])}")
    out = {}
    for name, (grid, _, ) in [(k, (v[0], 0)) for k, v in FACT.items()]:
        rows = {}
        for v in grid:
            rows[v] = {}
            for b, wt in BASES.items():
                m = metr(apply([(name, v)], *wt), 'train'); rows[v][b] = m; trial_log('FAC_' + name, {'v': v, 'b': b}, 'train', m)
        P(f"\n## {name}  (cell: train CAGR/DD/Sharpe for NB1 | NB2; uplift vs base in Sharpe)")
        for v in grid:
            P(f"   {v}: " + ' | '.join(f"{f(rows[v][b])} ({rows[v][b]['Sharpe'] - ref[b]['train']['Sharpe']:+.2f})" for b in BASES))
        lift = lambda v, b: rows[v][b]['Sharpe'] - ref[b]['train']['Sharpe']
        ok_cell = lambda v: all(lift(v, b) >= 0.05 and rows[v][b]['MaxDD'] >= ref[b]['train']['MaxDD'] - 1e-9 for b in BASES)
        inter = grid[1:-1] if len(grid) >= 3 else grid; cand = []
        for v in inter:
            i = grid.index(v); nb = [grid[j] for j in (i - 1, i + 1) if 0 <= j < len(grid)]
            frac = np.mean([all(lift(n, b) > 0 for b in BASES) for n in nb])
            if ok_cell(v) and frac >= 0.7: cand.append((np.mean([lift(v, b) for b in BASES] + [lift(n, b) for n in nb for b in BASES]), v))
        if cand: bv = max(cand)[1]; out[name] = bv; P(f"   -> PASS train, chosen {bv}")
        else: P('   -> fail train (needs +0.05 Sharpe, no worse DD on both bases, >=70% neighbours lift)')
    P('\n## Pair check (different factors, chosen cells, train)')
    pairs = {}
    for a_, b_ in itertools.combinations(out, 2):
        ok = True; txt = []
        for b, wt in BASES.items():
            ma = metr(apply([(a_, out[a_])], *wt), 'train'); mb = metr(apply([(b_, out[b_])], *wt), 'train'); mp = metr(apply([(a_, out[a_]), (b_, out[b_])], *wt), 'train')
            trial_log('FAC_pair', {'a': a_, 'b': b_, 'base': b}, 'train', mp); ok &= mp['Sharpe'] > max(ma['Sharpe'], mb['Sharpe']); txt.append(f"{b}: pair {mp['Sharpe']:.2f} vs {ma['Sharpe']:.2f}/{mb['Sharpe']:.2f}")
        P(f"   {a_}+{b_}: " + '; '.join(txt) + (' -> KEEP' if ok else ' -> single only'))
        if ok: pairs[(a_, b_)] = sum(1 for _ in [0])
    spec = [[k, v] for k, v in out.items()]
    if pairs: pa, pb = max(pairs, key=lambda k: 0); spec = [[pa, out[pa]], [pb, out[pb]]]
    elif len(out) > 1:   # no pair beats singles: keep best single by mean train lift
        best1 = max(out, key=lambda k: np.mean([metr(apply([(k, out[k])], *wt), 'train')['Sharpe'] for wt in BASES.values()])); spec = [[best1, out[best1]]]
    json.dump(dict(passed=out, final=spec), open(f'{RES}/fac_train.json', 'w'), indent=1); open(f'{RES}/FAC_REPORT.md', 'w').write('\n'.join(rep))
    P(f"\nTrain-passing factors: {out}; stack carried to validation: {spec}")

def validate():
    sp = json.load(open(f'{RES}/fac_train.json')); stack_ = [tuple(x) for x in sp['final']]
    if not stack_: raise SystemExit('no factor passed train; no validation look')
    vp = f'{RES}/validation_looks.json'; Lk = json.load(open(vp))
    if Lk.get('FAC', 0) >= 1: raise SystemExit('FAC validation look already used')
    Lk['FAC'] = 1; json.dump(Lk, open(vp, 'w'), indent=1)
    rep = []; P = lambda *a: (print(*a), rep.append(' '.join(str(x) for x in a)))
    P(f"\n## Validation look (one) for stack {stack_}: CAGR / MaxDD / Sharpe\n"); P('| Base | Window | Reference | With factors |'); P('|---|---|---|---|')
    ok_all = True
    for b, wt in BASES.items():
        for w in ('train', 'valid', 'test', 'full'):
            m0 = metr(stream(*wt), w); m1 = metr(apply(stack_, *wt), w); P(f"| {b} | {w}{' (desc.)' if w in ('test','full') else ''} | {f(m0)} | {f(m1)} |")
            if w == 'valid': ok_all &= (m1['Sharpe'] > m0['Sharpe'] and m1['MaxDD'] >= m0['MaxDD'] - 1e-9)
    P(f"\nValidation rule (Sharpe up AND MaxDD no worse on both bases): {'PASS' if ok_all else 'FAIL'}")
    open(f'{RES}/FAC_REPORT.md', 'a').write('\n' + '\n'.join(rep))
if __name__ == '__main__': {'train': train, 'validate': validate}[sys.argv[1] if len(sys.argv) > 1 else 'train']()
