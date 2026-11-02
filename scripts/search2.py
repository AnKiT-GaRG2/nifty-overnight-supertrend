import sys; sys.path.insert(0,'scripts')
from fast import *; from gates import build_gates
import pandas as pd
c=Ctx(); G=build_gates(c); P=c.periods(); days=c.days
def ev(ng,dg,size=None):
    h=c.held(ng,dg,size); r,net=c.daily_returns(h); return {k:metrics(r,*P[k],days) for k in ['train','valid','test','full']}, r, h, net
def line(name,m): return f'{name:46s} '+' | '.join(f'{k[:5]} {m[k]["CAGR"]:5.1f}/{m[k]["DD"]:6.1f}/{m[k]["Sh"] if "Sh" in m[k] else m[k]["Sharpe"]:4.2f}' for k in ['train','valid','test','full'])
print('format: CAGR%/MaxDD%/Sharpe')
A=G['ALWAYS']; N=G['NEVER']
m,_,_,_=ev(A,A); print(line('BASELINE ST(14,3)',m))
m,_,_,_=ev(A,N); print(line('night-only, ST green, no factors',m))
# stepwise (selected on train/valid only)
steps=[('vix1d>+8%(panic rebound)','day'),('vix1d<+8%','night'),('not_Mon','day'),('pe<25','day')]
ng=A.copy(); dg=A.copy(); dg=N.copy() if False else dg
# reproduce greedy path: step1 day gate = vix spike
dg=G['vix1d>+8%(panic rebound)'].copy(); m,_,_,_=ev(ng,dg); print(line('step1 day leg only after VIX spike',m))
ng=ng&G['vix1d<+8%']; m,_,_,_=ev(ng,dg); print(line('step2 + night skips after VIX spike  [2-gate]',m))
two=(ng.copy(),dg.copy())
dg=dg&G['not_Mon']; m,_,_,_=ev(ng,dg); print(line('step3 + day not Monday',m))
dg=dg&G['pe<25']; m,_,_,_=ev(ng,dg); print(line('step4 + day PE<25  [4-gate]',m))
four=(ng.copy(),dg.copy())
# ---- sizing on the 2-gate strategy: size = min(1, c/ATR%) (ATR known at prior close)
d=c.d; cl=d['close']; tr=pd.concat([d.high-d.low,(d.high-cl.shift()).abs(),(d.low-cl.shift()).abs()],axis=1).max(axis=1)
atrp=(tr.ewm(alpha=1/14,adjust=False).mean()/cl*100).shift(1).reindex(days).fillna(1.0).values
print('\nsizing c (size=min(1,c/ATR%)) on the 2-gate strategy:')
for cc in [None,2.0,1.5,1.2,1.0,0.8]:
    sz=None if cc is None else np.minimum(1.0,cc/atrp); m,_,h,net=ev(*two,size=sz)
    print(line(f'c={cc}',m)+f' | worst bar {net.min()*100:5.2f}%')
# ---- VIX-jump threshold sensitivity (2-gate, no sizing)
vx=pd.read_csv(f'{DATA}/vix.csv',parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()
j=(vx.shift(1)/vx.shift(2)-1).values*100
print('\nVIX-jump threshold sensitivity (day leg ON only after jump > t%, night leg skips those days):')
for t in [4,6,8,10,12,15,20]:
    up=j>t; m,_,_,_=ev(~up,up); print(line(f't={t}% ({up.mean()*100:.0f}% of days)',m))
print('\nvariants: day leg never (pure night) with night skip after VIX jump:')
m,_,_,_=ev(G['vix1d<+8%'],N); print(line('night skips VIX jump, no day leg',m))
m,_,_,_=ev(A,G['vix1d>+8%(panic rebound)']); print(line('night always, day only after VIX jump',m))
