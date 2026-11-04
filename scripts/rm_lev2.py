import sys; sys.path.insert(0, 'scripts')
exec(open('scripts/rm_lev.py').read().split("GR = {")[0])      # reuse data, series and factor functions
import itertools
def stack(ret, st):
    r = ret
    if 'R' in st: r = r * sc_R(st['R'])
    if 'V' in st: r = r * sc_V(st['V'])
    return r
STK = {'none': {}, 'R80': {'R': 80}, 'R70': {'R': 70}, 'V18': {'V': 0.18}, 'R80+V18': {'R': 80, 'V': 0.18}}
WLs = [1.0, 1.25, 1.5, 1.75, 2.0]; WSs = [0.5, 1.0, 1.5]
res = {}
for wl, ws, sk in itertools.product(WLs, WSs, STK):
    net = stack(wl * L + ws * Sh, STK[sk]); m = {w: metr(net, w) for w in ('train', 'valid', 'dev', 'test', 'full')}; res[(wl, ws, sk)] = m
    trial_log('LEV2', {'wl': wl, 'ws': ws, 'st': sk}, 'train', m['train'])
ok = lambda m: m['train']['MaxDD'] >= -0.14 and m['valid']['MaxDD'] >= -0.14 and m['dev']['MaxDD'] >= -0.14
feas = {k: v for k, v in res.items() if ok(v)}
print(f"feasible cells (train, valid, dev max DD all >= -14%): {len(feas)} of {len(res)}")
top = sorted(feas, key=lambda k: -feas[k]['dev']['CAGR'])[:10]
print('| wLong | wShort | Factors | Dev 2017-23 CAGR/DD/Sh | Train | Valid | Test (desc.) | Full |'); print('|---|---|---|---|---|---|---|---|')
for k in top:
    m = feas[k]; print(f"| {k[0]} | {k[1]} | {k[2]} | {f(m['dev'])} | {f(m['train'])} | {f(m['valid'])} | {f(m['test'])} | {f(m['full'])} |")
print('\nbest feasible per factor stack (by dev CAGR):')
for sk in STK:
    c = [k for k in feas if k[2] == sk]
    if c:
        k = max(c, key=lambda k: feas[k]['dev']['CAGR']); m = feas[k]; print(f"  {sk}: wL {k[0]}, wS {k[1]} -> dev {f(m['dev'])}, valid {f(m['valid'])}, test(desc.) {f(m['test'])}, full {f(m['full'])}")
    else: print(f'  {sk}: no feasible cell')
print('\nreference no-factor, no-leverage: plain A2 dev', f(res[(1.0,1.0,'none')]['dev']), 'full', f(res[(1.0,1.0,'none')]['full']))
