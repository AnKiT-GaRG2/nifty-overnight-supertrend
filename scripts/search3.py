import sys, json; sys.path.insert(0,'scripts')
from fast import *; from gates import build_gates
c=Ctx(); G=build_gates(c); P=c.periods(); days=c.days; hm=c.hm
A=G['ALWAYS']; N=G['NEVER']
def held(ng,dg,late='15:15',red=None,size=None):
    late_bar=hm>=late
    g=np.where(late_bar,ng[c.day_id],dg[c.day_id]).astype(float)
    sig=c.green_prev.astype(float)
    if red is not None:                                   # red-ST nights: hold only the LATE bars when the red-gate fires
        sig=np.where(c.green_prev,1.0,np.where(late_bar,red[c.day_id].astype(float),0.0))
    h=sig*g
    return h*size[c.day_id] if size is not None else h
def ev(ng,dg,**kw):
    r,net=c.daily_returns(held(ng,dg,**kw)); return {k:metrics(r,*P[k],days) for k in ['train','valid','test','full']},net
def row(name,m): return f'{name:50s} '+' | '.join(f'{k[:5]} {m[k]["CAGR"]:5.1f}/{m[k]["DD"]:6.1f}/{m[k]["Sharpe"]:4.2f}' for k in ['train','valid','test','full'])
J=lambda m,k: m[k]['J']
vj=G['vix1d>+8%(panic rebound)']; ng0=~vj
# ---- 1. entry-time sweep on the 2-gate strategy; choose by train+valid J only
print('A) entry time of the overnight leg (2-gate base):')
res={}
for late in ['15:15','15:00','14:45','14:30','14:00','13:30']:
    m,_=ev(ng0,vj,late=late); res[late]=m; print(row('enter '+late,m))
bestlate=max(res,key=lambda k: res[k]['train']['J']+res[k]['valid']['J']); print('-> chosen by train+valid J:',bestlate)
# ---- 2. greedy gates re-run with chosen late bar (train select, valid confirm)
names=[k for k in G if k not in('ALWAYS','NEVER')]
ng=A.copy(); dg=A.copy(); cur,_=ev(ng,dg,late=bestlate); path=[]
for step in range(6):
    best=None
    for leg in ['night','day']:
        for nm in names+(['NEVER'] if leg=='day' else []):
            nng,ndg=(ng&G[nm],dg) if leg=='night' else ((ng,dg&G[nm]) if nm!='NEVER' else (ng,N))
            m,_=ev(nng,ndg,late=bestlate)
            if J(m,'train')-J(cur,'train')>0.5 and J(m,'valid')-J(cur,'valid')>-0.25 and J(m,'train')>(best[0] if best else -1e9): best=(J(m,'train'),leg,nm,nng,ndg,m)
    if not best: break
    _,leg,nm,ng,dg,cur=best; path.append((leg,nm)); print(f'  +{leg}:{nm}  train {cur["train"]["CAGR"]:.1f}/{cur["train"]["DD"]:.1f}  valid {cur["valid"]["CAGR"]:.1f}/{cur["valid"]["DD"]:.1f}')
print('B) gates with entry',bestlate,path); m,_=ev(ng,dg,late=bestlate); print(row('gated + early entry',m))
# ---- 3. red-ST override: hold the late bars on red nights if a factor gate fires (greedy over single gates then pairs, train select / valid confirm)
print('\nC) red-Supertrend nights: hold late bars only if factor gate(s) fire')
curm=m; red=N.copy(); rp=[]
for step in range(3):
    best=None
    for nm in names:
        r2=red|G[nm] if step==0 else red&G[nm]           # first pick a base gate, then tighten with AND
        if step==0: r2=G[nm]
        m2,_=ev(ng,dg,late=bestlate,red=r2)
        if J(m2,'train')-J(curm,'train')>0.5 and J(m2,'valid')-J(curm,'valid')>-0.25 and J(m2,'train')>(best[0] if best else -1e9): best=(J(m2,'train'),nm,r2,m2)
    if not best: break
    _,nm,red,curm=best; rp.append(nm); print(f'  red gate {rp}: train {curm["train"]["CAGR"]:.1f}/{curm["train"]["DD"]:.1f} valid {curm["valid"]["CAGR"]:.1f}/{curm["valid"]["DD"]:.1f}')
print(row('gated + early entry + red override',curm))
np.save('results/s3_ng.npy',ng); np.save('results/s3_dg.npy',dg); np.save('results/s3_red.npy',red)
json.dump({'late':bestlate,'gates':path,'red':rp},open('results/s3_spec.json','w'))
