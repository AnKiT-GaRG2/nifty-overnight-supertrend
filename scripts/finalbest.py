import sys; sys.path.insert(0,'scripts')
import fast
from fast import *; from gates import build_gates; from btlib import supertrend
c=Ctx(); G=build_gates(c); days=c.days; hm=c.hm; A=G['ALWAYS']; N=G['NEVER']
vx=pd.read_csv(f'{DATA}/vix.csv',parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()
jump=(vx.shift(1)/vx.shift(2)-1).values*100
def sp(a,b): return (np.searchsorted(days,pd.Timestamp(a)),np.searchsorted(days,pd.Timestamp(b),side='right'))
PER={'2017-21 (train)':('2017-04-01','2021-12-31'),'2022-23 (valid)':('2022-01-01','2023-12-31'),'2024-26 (test)':('2024-01-01','2026-12-31'),'2021-26 (walk-fwd era)':('2021-01-01','2026-12-31'),'FULL 2017-26':('2017-04-01','2026-12-31')}
def S(r,a,b): m=metrics(r,*sp(a,b),days); return m
def strat(th=8.0,green=None,delay=False,size=None):
    if green is not None: old=c.green_prev; c.green_prev=green
    h=c.held(jump<=th,N,size)           # night leg only, skip nights after a VIX jump > th%
    if delay:                            # exit one bar later (09:30 open): keep the position through the 09:15 bar
        h2=h.copy(); idx=np.flatnonzero(hm=='09:15'); idx=idx[idx>0]; h2[idx]=h[idx-1]; h=h2
    r,net=c.daily_returns(h)
    if green is not None: c.green_prev=old
    return r,h,net
base=c.daily_returns(c.held(A,A))[0]
R,H,NET=strat()
print('=== FINAL: Overnight Supertrend + panic filter (full size, 1x) vs BASELINE ===')
print(f'{"period":26s} {"STRATEGY CAGR/DD/Sharpe":28s} {"BASELINE CAGR/DD/Sharpe":28s}')
for k,(a,b) in PER.items():
    m=S(R,a,b); bm=S(base,a,b); print(f'{k:26s} {m["CAGR"]:6.1f}% /{m["DD"]:7.1f}% /{m["Sharpe"]:5.2f}      {bm["CAGR"]:6.1f}% /{bm["DD"]:7.1f}% /{bm["Sharpe"]:5.2f}')
print('\n=== YEAR BY YEAR net return % (strategy | baseline) ===')
for y in range(2017,2027):
    lo,hi=sp(f'{y}-01-01',f'{y}-12-31'); print(f'{y}: {(np.prod(1+R[lo:hi])-1)*100:6.1f} | {(np.prod(1+base[lo:hi])-1)*100:6.1f}')
nights=(H>0)&(hm=='15:15'); g=(H*c.ret_oo)[nights]*100
print(f'\nnights held: {nights.sum()} ({nights.sum()/ (len(days)/252)/1:.0f}/yr, {nights.sum()/len(days)*100:.0f}% of days) | win rate {(g>0).mean()*100:.0f}% | avg {g.mean():.3f}% | worst night {g.min():.2f}% | nights losing >1%: {(g<-1).sum()}, >2%: {(g<-2).sum()}')
print('\n=== SENSITIVITY: VIX-jump threshold (skip night after VIX up > t%) -> FULL / 2021-26 / 2024-26 CAGR,DD,Sharpe ===')
for t in [4,6,8,10,12,15,20,999]:
    r,_,_=strat(t); print(f't={t:>3}%  '+' | '.join(f'{lab} {S(r,*PER[k])["CAGR"]:5.1f}/{S(r,*PER[k])["DD"]:6.1f}/{S(r,*PER[k])["Sharpe"]:4.2f}' for lab,k in [('full','FULL 2017-26'),('21-26','2021-26 (walk-fwd era)'),('24-26','2024-26 (test)')]))
print('\n=== SENSITIVITY: Supertrend period x multiplier (same rules) -> FULL CAGR/DD/Sharpe | 2024-26 CAGR/DD/Sharpe ===')
for n in [10,14,20]:
    row=[]
    for m_ in [2.5,3.0,3.5]:
        st=supertrend(c.b,n,m_); gp=np.r_[False,st['dir'].values[:-1]==1]; r,_,_=strat(green=gp)
        a,b=S(r,*PER['FULL 2017-26']),S(r,*PER['2024-26 (test)']); row.append(f'({n},{m_}): {a["CAGR"]:4.1f}/{a["DD"]:5.1f}/{a["Sharpe"]:4.2f} | {b["CAGR"]:4.1f}/{b["DD"]:5.1f}/{b["Sharpe"]:4.2f}')
    print('  '.join(row))
print('\n=== STRESS: costs and exit timing (FULL / 2024-26) ===')
for mult in [1,2,3]:
    fast.COST_SIDE=0.00025*mult; r,_,_=strat(); rb=c.daily_returns(c.held(A,A))[0]
    print(f'costs {mult}x: strategy {S(r,*PER["FULL 2017-26"])["CAGR"]:5.1f}%/{S(r,*PER["FULL 2017-26"])["Sharpe"]:4.2f} (24-26: {S(r,*PER["2024-26 (test)"])["CAGR"]:5.1f}%/{S(r,*PER["2024-26 (test)"])["Sharpe"]:4.2f}) | baseline {S(rb,*PER["FULL 2017-26"])["CAGR"]:5.1f}%/{S(rb,*PER["FULL 2017-26"])["Sharpe"]:4.2f} (24-26: {S(rb,*PER["2024-26 (test)"])["CAGR"]:5.1f}%/{S(rb,*PER["2024-26 (test)"])["Sharpe"]:4.2f})')
fast.COST_SIDE=0.00025
r,_,_=strat(delay=True); print('exit at 09:30 open instead of 09:15: '+' | '.join(f'{k} {S(r,a,b)["CAGR"]:4.1f}%/{S(r,a,b)["DD"]:5.1f}%/{S(r,a,b)["Sharpe"]:4.2f}' for k,(a,b) in [('full',PER['FULL 2017-26']),('24-26',PER['2024-26 (test)'])]))
print('\n=== LOWER-DRAWDOWN VARIANT: size = min(1, c/ATR%) ===')
d=c.d; cl=d['close']; tr=pd.concat([d.high-d.low,(d.high-cl.shift()).abs(),(d.low-cl.shift()).abs()],axis=1).max(axis=1)
atrp=(tr.ewm(alpha=1/14,adjust=False).mean()/cl*100).shift(1).reindex(days).fillna(1.0).values
for cc in [2.0,1.5,1.0]:
    r,h,_=strat(size=np.minimum(1,cc/atrp)); nn=(h>0)&(hm=='15:15'); gg=(h*c.ret_oo)[nn]*100
    print(f'c={cc}: '+' | '.join(f'{k} {S(r,a,b)["CAGR"]:5.1f}%/{S(r,a,b)["DD"]:5.1f}%/{S(r,a,b)["Sharpe"]:4.2f}' for k,(a,b) in [('full',PER['FULL 2017-26']),('21-26',PER['2021-26 (walk-fwd era)']),('24-26',PER['2024-26 (test)'])])+f' | worst night {gg.min():.2f}%  avg size {h[nn].mean():.2f}')
