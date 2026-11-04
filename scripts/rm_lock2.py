import sys; sys.path.insert(0,'scripts')
import numpy as np, pandas as pd, itertools, json
import rm_lock_dev as LD
from rm_engine import metrics_from
E,S,Ea,days,ens,INT = LD.E,LD.S,LD.Ea,LD.days,LD.ens,LD.INT; DATA=LD.DATA; RES=LD.RES
assert days.min()>=pd.Timestamp('2017-04-03') and days.max()<=pd.Timestamp('2023-12-31')
def rd(n): return pd.read_csv(f'{DATA}/{n}.csv',parse_dates=['date']).set_index('date')['close']
def prior(s,n=None,kind='pct'):
    s=s.dropna(); s=s[~s.index.duplicated()]; 
    if n is not None: s=(s/s.shift(n)-1) if kind=='pct' else (s-s.shift(n))
    p=np.searchsorted(s.index.values,days.values,side='left')-1; return pd.Series(np.where(p>=0,s.values[np.maximum(p,0)],np.nan),index=days)
bn,nf=rd('banknifty'),rd('nifty'); vix=pd.read_csv(f'{DATA}/vix_ext.csv',parse_dates=['date']).set_index('date')['close']
dc=pd.Series(S.D['close'].values,index=S.D.index)
vol20=(dc.pct_change().rolling(20).std()*np.sqrt(252)*100); vprem=(vix.reindex(S.D.index).ffill()-vol20); vpct=vprem.rolling(252,min_periods=60).apply(lambda x:(x[:-1]<x[-1]).mean()*100,raw=True)
def cond(name,v):
    if name=='T2L': c=(dc.shift(1)<dc.rolling(v).mean().shift(1))
    elif name=='S1': c=((prior(bn,v)-prior(nf,v))<0)
    elif name=='O3': c=(vpct.shift(1)<v)
    return c.reindex(days).fillna(False).astype(bool)
GRID={'T2L':[100,150,200,250],'S1':[10,20,40],'O3':[10,20,30]}; ROLE={'T2L':'L','S1':'L','O3':'B'}
PARTS={}
for cost in ('real','floor'):
    L,G,I,Sh=LD.run_legs(Ea,S,'base',cost); Lc=1.912*(ens.shift(1).fillna(1.0)*G+ens*I); Sc=0.956*Sh; PARTS[cost]=(Lc,Sc)
def stream(cost,name=None,v=None):
    Lc,Sc=PARTS[cost]
    if name is None: return Lc+Sc
    s=pd.Series(np.where(cond(name,v),0.5,1.0),index=days)
    return (s*Lc+s*Sc) if ROLE[name]=='B' else (s*Lc+Sc)
def met(net,a,z): ex=net[a:z]; return metrics_from(ex+INT[a:z],None,None,None,ex)
fl=lambda m:f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
def eqdd(net,ref,a,z):
    lo,hi=0.05,4.0
    for _ in range(40):
        s=(lo+hi)/2
        if met(net*s,a,z)['MaxDD']<ref: hi=s
        else: lo=s
    return lo,met(net*lo,a,z)
DEV=('2017-04-03','2023-12-31'); OOS0=pd.Timestamp('2020-04-01')
folds=[];a0=OOS0
while a0<=pd.Timestamp('2023-12-31'):
    z0=min(a0+pd.DateOffset(months=6)-pd.Timedelta(days=1),pd.Timestamp('2023-12-31')); folds.append((a0,z0,a0-pd.DateOffset(years=3),a0-pd.Timedelta(days=1))); a0+=pd.DateOffset(months=6)
STR={(c,n,v):stream(c,n,v) for c in ('real','floor') for n,g in GRID.items() for v in g}
for k in STR: LD.trial_log('LOCK2_'+k[1],{'v':k[2],'c':k[0]},'train',met(STR[k],*DEV))
def pick(cost,t0,t1):
    base=stream(cost); ref=met(base,t0,t1); best=None
    for n,grid in GRID.items():
        mets={v:met(STR[(cost,n,v)],t0,t1) for v in grid}; lift={v:mets[v]['Sharpe']-ref['Sharpe'] for v in grid}
        for v in (grid[1:-1] if len(grid)>=3 else grid):
            i=grid.index(v); nb=[grid[j] for j in (i-1,i+1) if 0<=j<len(grid)]
            if lift[v]>=0.05 and mets[v]['MaxDD']>=ref['MaxDD']-1e-9 and np.mean([lift[x]>0 for x in nb])>=0.7:
                sc=np.mean([lift[v]]+[lift[x] for x in nb]); 
                if best is None or sc>best[0]: best=(sc,n,v)
    return (best[1],best[2]) if best else None
print('# LOCK2: baseline (frozen executable) with Indian-data add-ons; usable data 2017-04..2023-12 only\n')
print('## Fixed cells on DEV 2017-04..2023-12 (descriptive; CAGR / MaxDD / Sharpe, and equal-drawdown CAGR vs baseline)\n')
for cost in ('real','floor'):
    base=stream(cost); mb=met(base,*DEV); print(f'{cost} costs. Baseline dev: {fl(mb)}'); print('| Add-on | CAGR / MaxDD / Sharpe | Equal-drawdown CAGR |'); print('|---|---|---|')
    for n,g in GRID.items():
        for v in g:
            net=STR[(cost,n,v)]; m=met(net,*DEV); sc,me=eqdd(net,mb['MaxDD'],*DEV); print(f"| {n} {v} | {fl(m)} | {me['CAGR']:.1%} |")
    print()
rows={}
for cost in ('real','floor'):
    P0=[];P1=[];picks=[]
    for a,z,t0,t1 in folds:
        sp=pick(cost,t0,t1); picks.append((str(a.date()),sp)); P0.append(stream(cost)[a:z]); P1.append((stream(cost,*sp) if sp else stream(cost))[a:z])
    s0,s1=pd.concat(P0),pd.concat(P1); a,z=str(folds[0][0].date()),str(folds[-1][1].date()); m0,m1=met(s0,a,z),met(s1,a,z); sc,me=eqdd(s1,m0['MaxDD'],a,z)
    ok=(m1['Sharpe']>=m0['Sharpe']+0.10) and (me['CAGR']>=m0['CAGR']+0.02); rows[cost]=ok
    print(f"## Walk-forward ({cost} costs): picks per fold {picks}\n   stitched OOS 2020-04..2023-12: baseline {fl(m0)} | with picked add-on {fl(m1)} | add-on scaled to baseline drawdown: CAGR {me['CAGR']:.1%} (scale {sc:.2f}) -> {'PASS' if ok else 'FAIL'}\n")
print('**LOCK2 verdict:** '+('an add-on passes under both cost models' if all(rows.values()) else 'no add-on passes under both cost models: baseline unchanged'))
