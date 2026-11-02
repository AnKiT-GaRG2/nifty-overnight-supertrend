import sys; sys.path.insert(0,'scripts')
from fast import *; from gates import build_gates
c=Ctx(); G=build_gates(c); days=c.days; A=G['ALWAYS']; N=G['NEVER']
def sp(a,b): return (np.searchsorted(days,pd.Timestamp(a)),np.searchsorted(days,pd.Timestamp(b),side='right'))
def st(r,a,b):
    lo,hi=sp(a,b); m=metrics(r,lo,hi,days); return f'{m["CAGR"]:5.1f}% / {m["DD"]:6.1f}% / {m["Sharpe"]:4.2f}'
R={}
R['BASELINE ST(14,3)']=c.daily_returns(c.held(A,A))[0]
R['night-only, ST green (no factors)']=c.daily_returns(c.held(A,N))[0]
vj=G['vix1d>+8%(panic rebound)']
R['night-only, skip after VIX jump>8%']=c.daily_returns(c.held(~vj,N))[0]
for sz in [1.5,1.0]:
    d=c.d; cl=d['close']; tr=pd.concat([d.high-d.low,(d.high-cl.shift()).abs(),(d.low-cl.shift()).abs()],axis=1).max(axis=1)
    atrp=(tr.ewm(alpha=1/14,adjust=False).mean()/cl*100).shift(1).reindex(days).fillna(1.0).values
    R[f'night-only skip VIX jump, size min(1,{sz}/ATR%)']=c.daily_returns(c.held(~vj,N,np.minimum(1,sz/atrp)))[0]
print('CAGR / MaxDD / Sharpe'); print(f'{"":52s} {"OOS-era 2021-26":28s} {"2024-26":28s} {"2017-26":28s}')
for k,r in R.items(): print(f'{k:52s} {st(r,"2021-01-01","2026-12-31"):28s} {st(r,"2024-01-01","2026-12-31"):28s} {st(r,"2017-04-01","2026-12-31")}')
