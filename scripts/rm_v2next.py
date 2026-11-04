"""V2NEXT round: freeze baseline v2 and test pre-declared candidates (see results/rm/PROTOCOL_CHANGES.md, ROUND "V2NEXT").
Run from repo root with the numba venv:  <venv>/bin/python scripts/rm_v2next.py [freeze|cand]"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_data, rm_final, rm_pre_exact as P
from rm_engine import Engine, metrics_from, RF, LOT, CAPITAL
from rm_ideas import make_sig, trial_log, RES, DATA
ROOT = rm_data.ROOT

def env_main():
    src = open(os.path.join(ROOT, 'scripts/rm_lock_dev.py')).read().split("if __name__=='__main__':")[0].replace("LOCK='2023-12-31'", "LOCK='2026-12-31'")
    ns = {'__name__': 'lock_dev_unlocked'}; os.chdir(ROOT); exec(compile(src, 'lock_dev_unlocked', 'exec'), ns)
    return dict(Ea=ns['Ea'], S=ns['S'], days=ns['days'], ens=ns['ens'], INT=ns['INT'])

def env_pre():
    ds, futR = P.build_ds(); E = Engine(ds); S = make_sig(E); days = E.days; Ea, _ = rm_final.anchored_engine(E, futR)
    nq = P.series(f'{DATA}/pre/nasdaq.csv', f'{DATA}/nasdaq.csv'); us = P.series(f'{DATA}/pre/us10y.csv', f'{DATA}/us10y.csv')
    def prior(s, n, kind='pct'):
        s = s.dropna(); s = (s / s.shift(n) - 1) if kind == 'pct' else (s - s.shift(n)); p = np.searchsorted(s.index.values, days.values, side='left') - 1
        return pd.Series(np.where(p >= 0, s.values[np.maximum(p, 0)], np.nan), index=days)
    def cell(x, y, c=0.25):
        a = (prior(nq, 5) * 100 < -x).fillna(False); b = (prior(us, 5, 'diff') * 100 > y).fillna(False)
        return pd.Series(np.where(a, c, 1.0), index=days) * pd.Series(np.where(b, c, 1.0), index=days)
    ens = sum(cell(x, y) for x in (1, 2, 3) for y in (10, 15, 20)) / 9.0
    return dict(Ea=Ea, S=S, days=days, ens=ens, INT=pd.Series(E.cal * RF / 365.0, index=days))

def signals(env, variant, h=4):
    """returns (long_dir, long_size, short_dir, short_size) per 15-min bar"""
    En, S = env['Ea'], env['S']; tt, _ = S.A2(100)
    lt = (S.st == 1).astype(np.int8); stt = np.where(tt == -1, -1, 0).astype(np.int8); one = np.ones(En.N)
    if variant in ('v2', 'SIMP'): return lt, one, stt, one
    if variant == 'MH':
        def hold(raw):
            out = raw.copy(); last = 0; cur = raw[0]
            for t in range(1, len(raw)):
                if raw[t] != cur and t - last >= h: cur = raw[t]; last = t
                out[t] = cur
            return out
        # min hold applied to the Supertrend direction itself, then re-derived into long and A2-permitted short legs
        stm = hold(S.st.astype(np.int8)); pc = (tt == -1) | (S.st == 1)           # tt==-1 only where st==-1 and permitted
        perm = (S.st == -1) & (tt == -1)
        # permission is daily: take it from the bar where it was evaluated
        permd = np.where(S.st == -1, tt == -1, False)
        # carry daily permission to every bar: pc<sma of that day
        sma = S.d2b(S.sma_daily(100)); pcl = S.d2b(S.dd.close.values); allow = pcl < sma
        return (stm == 1).astype(np.int8), one, np.where((stm == -1) & allow, -1, 0).astype(np.int8), one
    if variant == 'C2C':
        k = En.bar_k; day = En.day_codes; N = En.N
        sma = S.d2b(S.sma_daily(100)); pcl = S.d2b(S.dd.close.values); allow = pcl < sma
        lng = np.zeros(N, np.int8); sht = np.zeros(N, np.int8); curL = 0; curS = 0
        for t in range(N):
            if k[t] == 23:                                    # bar 15:00-15:15 closes: decide once, fill at the 15:15 open
                curL = 1 if S.st[t] == 1 else 0; curS = -1 if (S.st[t] == -1 and allow[t]) else 0
            lng[t] = curL; sht[t] = curS
        return lng, one, sht, one
    raise ValueError(variant)

def legs(env, sig, cost):
    En = env['Ea']; lt, lz, st, sz = sig
    R = En.run(lt, lz, cost=cost, min_chg=1); fb = np.where(En.first_b)[0]; lb = np.where(En.last_b)[0]; net = pd.Series(R.net_d, index=En.days); gap = np.zeros(len(fb))
    for i in range(1, len(fb)): gap[i] = R.posl[lb[i - 1]] * LOT * (En.fo[fb[i]] - En.prev[fb[i]]) / CAPITAL
    gap = pd.Series(gap, index=En.days); Sh = pd.Series(En.run(st, sz, cost=cost, min_chg=1).net_d, index=En.days)
    return net, gap, net - gap, Sh, R

def stream(env, variant, cost, wl=1.912, ws=0.956, cut=True, h=4):
    sig = signals(env, variant, h); L, G, I, Sh, R = legs(env, sig, cost); ens = env['ens']
    long = wl * ((ens.shift(1).fillna(1.0) * G + ens * I) if cut else (G + I))
    return long + ws * Sh, len(R.trades)

def met(env, net, a, z): ex = net[a:z]; return metrics_from(ex + env['INT'][a:z], None, None, None, ex)
fl = lambda m: f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
MAIN = {'train 2017-04..2021-12': ('2017-04-03', '2021-12-31'), 'valid 2022-23': ('2022-01-01', '2023-12-31'), 'test 2024-26': ('2024-01-01', '2026-12-31'), 'FULL 2017-04..2026-10': ('2017-04-03', '2026-12-31')}
PRE = ('2012-07-02', '2016-08-31')

def code_hash():
    h = hashlib.sha256()
    for f in ['rm_engine.py', 'rm_signals.py', 'rm_ideas.py', 'rm_final.py', 'rm_data.py', 'rm_lock_dev.py', 'rm_pre_exact.py', 'rm_v2next.py']:
        h.update(open(os.path.join(ROOT, 'scripts', f), 'rb').read())
    return h.hexdigest()

def deflated_sharpe(net_excess, n_trials):
    from scipy.stats import norm, skew, kurtosis
    t = json.load(open(f'{RES}/trials.json')); sr = np.array([r['sharpe'] for r in t if r.get('sharpe') is not None and np.isfinite(r['sharpe'])]) / np.sqrt(252)
    V = sr.var(ddof=1); g = 0.5772156649; N = max(n_trials, 2)
    sr0 = np.sqrt(V) * ((1 - g) * norm.ppf(1 - 1 / N) + g * norm.ppf(1 - 1 / (N * np.e)))
    x = net_excess.dropna(); s = x.mean() / x.std(); sk = skew(x); ku = kurtosis(x, fisher=False); T = len(x)
    dsr = norm.cdf((s - sr0) * np.sqrt(T - 1) / np.sqrt(1 - sk * s + (ku - 1) / 4 * s * s))
    return dict(SR_daily=s, SR_annual=s * np.sqrt(252), SR0_annual=sr0 * np.sqrt(252), DSR=dsr, trials=N, trial_sr_sd_annual=np.sqrt(V) * np.sqrt(252), T=T)

def freeze():
    env = env_main(); out = ['# Baseline v2 — frozen (2026-11-04)\n']
    out.append(f'Code hash (sha256 of rm_engine, rm_signals, rm_ideas, rm_final, rm_data, rm_lock_dev, rm_pre_exact, rm_v2next): `{code_hash()}`\n')
    out.append('Spec: long 1.912x Supertrend(14,3) Wilder ATR 15-min, held overnight; short 0.956x when Supertrend red AND prior daily close < SMA100; long leg cut to 0.25 by each of 9 Nasdaq/US10Y cells (average), applied from the open after the gap; fill at next bar open; Rs 2 crore, lot 65; collateral earns 6%.\n')
    out.append('Sharpe is computed on futures P&L after costs WITHOUT the 6% collateral interest, i.e. it is an excess-return Sharpe (risk-free already deducted). CAGR includes the interest. Interest shown as its own line.\n')
    for cost in ('real', 'floor'):
        net, ntr = stream(env, 'v2', cost); net1, _ = stream(env, 'v2', cost, wl=1.912 / 1.912, ws=0.956 / 1.912)
        out.append(f'\n## {cost} costs\n'); out.append('| Window | v2 CAGR / MaxDD / Sharpe(excess) | of which collateral interest (CAGR pts) | v2 rescaled to 1x (long 1.0 / short 0.5) | long-only x1 (with US cut) |'); out.append('|---|---|---|---|---|')
        Ls, _ = stream(env, 'v2', cost, wl=1.0, ws=0.0)
        for n, (a, z) in MAIN.items():
            m = met(env, net, a, z); ex = net[a:z]; m0 = metrics_from(ex, None, None, None, ex)
            out.append(f"| {n} | {fl(m)} | {m['CAGR'] - m0['CAGR']:.1%} | {fl(met(env, net1, a, z))} | {fl(met(env, Ls, a, z))} |")
        if cost == 'real':
            d = deflated_sharpe(net['2017-04-03':'2026-12-31'], len(json.load(open(f'{RES}/trials.json'))))
            out.append(f"\nDeflated Sharpe (full period, excess-return Sharpe {d['SR_annual']:.2f}, {d['trials']} trials, SD of trial Sharpes {d['trial_sr_sd_annual']:.2f}): expected-max Sharpe under luck SR0 = {d['SR0_annual']:.2f}; DSR = {d['DSR']:.3f} (probability that the true Sharpe is above SR0).")
    open(f'{RES}/BASELINE_V2_FROZEN.md', 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))

def cand():
    em, ep = env_main(), env_pre(); NT0 = len(json.load(open(f'{RES}/trials.json')))
    cells = [('v2', 'v2', {}), ('C2C', 'C2C', {}), ('MH h=2', 'MH', {'h': 2}), ('MH h=4', 'MH', {'h': 4}), ('MH h=8', 'MH', {'h': 8}), ('SIMP 2.0/1.0 no cut', 'SIMP', {'wl': 2.0, 'ws': 1.0, 'cut': False})]
    res = {}
    for cost in ('real', 'floor'):
        print(f'\n### {cost} costs: CAGR / MaxDD / Sharpe(excess)  [trades per year main]')
        print('| Candidate | FULL 2017-04..2026-10 | train | valid | test | HOLDOUT 2012-07..2016-08 | trades/yr (full) |'); print('|---|---|---|---|---|---|---|')
        for name, var, kw in cells:
            nm, trm = stream(em, var, cost, **kw); np_, _ = stream(ep, var, cost, **kw); yrs = len(em['days']) / 252
            ms = {w: met(em, nm, a, z) for w, (a, z) in MAIN.items()}; mp = met(ep, np_, *PRE); res[(cost, name)] = (ms, mp)
            print(f"| {name} | {fl(ms['FULL 2017-04..2026-10'])} | {fl(ms['train 2017-04..2021-12'])} | {fl(ms['valid 2022-23'])} | {fl(ms['test 2024-26'])} | {fl(mp)} | {trm / yrs:.0f} |")
            if name != 'v2': trial_log('V2NEXT_' + var, {'cell': name, 'cost': cost}, 'train', ms['FULL 2017-04..2026-10'])
    print('\n## Keep rule (full CAGR up AND full MaxDD better than -15% AND holdout Sharpe and CAGR not worse, under BOTH cost models)')
    for name, var, kw in cells[1:]:
        ok = True; det = []
        for cost in ('real', 'floor'):
            ms, mp = res[(cost, name)]; bs, bp = res[(cost, 'v2')]; f, bf = ms['FULL 2017-04..2026-10'], bs['FULL 2017-04..2026-10']
            c1 = f['CAGR'] > bf['CAGR']; c2 = f['MaxDD'] > -0.15; c3 = mp['Sharpe'] >= bp['Sharpe'] and mp['CAGR'] >= bp['CAGR']; ok &= c1 and c2 and c3; det.append(f'{cost}: CAGR up {c1}, DD>-15% {c2}, holdout not worse {c3}')
        print(f"- {name}: {'KEEP' if ok else 'REJECT'}  ({'; '.join(det)})")
    print(f'\ntrial count {NT0} -> {len(json.load(open(f"{RES}/trials.json")))}')

if __name__ == '__main__':
    {'freeze': freeze, 'cand': cand}[sys.argv[1] if len(sys.argv) > 1 else 'freeze']()
