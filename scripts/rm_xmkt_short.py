"""Short-leg cross-market diagnostic (+ conditional long-side gate). Run: <venv>/bin/python scripts/rm_xmkt_short.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import rm_xmkt as X, rm_batch2 as B, rm_noise as NZ, rm_lossf as LF, rm_stress as ST, rm_v2next as V
em, days, En = X.em, X.days, B.En; TRAIN = X.TRAIN
VIXU = X.rd('VIX', 'close'); HG, GC, JPY = X.rd('HG', 'close'), X.rd('GC', 'close'), X.rd('JPY', 'close'); CG = (HG / GC).dropna()
def onser(s): return (NZ.prior_val(days, s.astype(float)) == 1).reindex(days).fillna(False)
SF = {'EM weakness: EEM < 50d mean': onser(X.EEM < X.EEM.rolling(50).mean()), 'Credit stress: HYG/IEF < 20d mean': onser(X.RATIO < X.RATIO.rolling(20).mean()),
      'Dollar strength: DXY > 50d mean': onser(X.DXY > X.DXY.rolling(50).mean()), 'US fear: VIX > 20': onser(VIXU > 20)}
LF_ = {'copper/gold < 50d mean': onser(CG < CG.rolling(50).mean()), 'Brent > 50d mean and up over 20d': onser((LF.BR > LF.BR.rolling(50).mean()) & (LF.BR / LF.BR.shift(20) - 1 > 0)), 'USDJPY < 50d mean': onser(JPY < JPY.rolling(50).mean())}
def short_trades():
    Rr = En.run(B.SH_BASE, B.one, cost='floor', min_chg=1); rows = []
    for tr in Rr.trades:
        if int(tr[2]) != -1: continue
        d = En.days[En.day_codes[int(tr[0])]]
        if pd.Timestamp(TRAIN[0]) <= d <= pd.Timestamp(TRAIN[1]): rows.append((d, (tr[6] - tr[7]) / 2e7 * 0.956 * X.S0))
    return pd.DataFrame(rows, columns=['d', 'pnl'])
df = short_trades(); top = df.nlargest(10, 'pnl'); los = df[df.pnl <= 0]
print(f'SHORT DIAGNOSTIC on TRAIN: {len(df)} shorts; top 10 crash trades {top.pnl.sum():+.1%} of capital ({", ".join(str(x.date()) for x in top.d)}); {len(los)} losing shorts ({los.pnl.sum():+.1%})\n')
print('| factor (prior close) | on for top-10 crash shorts | OFF for losing shorts | on-share of all TRAIN days | gate (>=8 of 10 and >=40% off) |'); print('|---|---|---|---|---|'); passed = []
for n, s in SF.items():
    k = int(sum(s[d] for d in top.d)); off = 1 - np.mean([s[d] for d in los.d]); ok = k >= 8 and off >= 0.40; passed += [n] if ok else []
    print(f'| {n} | {k} of 10 | {off:.0%} | {s[TRAIN[0]:TRAIN[1]].mean():.0%} | {"PASS" if ok else "no"} |')
print('\nShort-side factors passing the gate:', passed or 'NONE')
if not passed:
    cp = ST.comps(em, 'floor'); import rm_ddsplit as DS
    net = ST.stream(em, None, X.S0, cp, X.EV); long, short, cost = DS.legs_pnl(em, cp, X.EV); a, z = TRAIN; r = (net + em['INT'])[a:z]; eq = (1 + r).cumprod(); dd = eq / eq.cummax() - 1; und = dd < 0; grp = (~und).cumsum()[und]; rows = []
    for g, idx in dd[und].groupby(grp): tr = idx.idxmin(); rows.append((idx.min(), eq[:tr].idxmax(), tr))
    rows = sorted(rows)[:5]; lm = long[a:z].groupby([long[a:z].index.year, long[a:z].index.month]).sum(); best = set(lm.nlargest(max(int(round(0.1 * len(lm))), 1)).index); mask = pd.Series([(d.year, d.month) in best for d in days], index=days)[a:z]
    print('\nLONG-SIDE GATE (same five TRAIN drawdowns and best-month set as the XMKT round):'); print('| factor | on-share all days | on in drawdowns | best-month days on | gate |'); print('|---|---|---|---|---|')
    for n, s in LF_.items():
        per = [s[p:t].mean() for _, p, t in rows]; k = sum(x >= 0.5 for x in per); bs = s[a:z][mask].mean(); ok = k >= 3 and bs <= 0.25
        print(f'| {n} | {s[a:z].mean():.0%} | {k} of 5 ({", ".join(f"{x:.0%}" for x in per)}) | {bs:.0%} | {"TEST" if ok else "SKIP"} |')
