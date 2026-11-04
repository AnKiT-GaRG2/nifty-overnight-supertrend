import sys; sys.path.insert(0,'scripts')
import numpy as np, pandas as pd
import rm_pre_exact as P, rm_final, rm_data
from rm_engine import Engine, metrics_from, RF, LOT, CAPITAL
from rm_ideas import make_sig
ds, futR = P.build_ds(); E = Engine(ds); S = make_sig(E); days = E.days; Ea,_ = rm_final.anchored_engine(E, futR)
nq = P.series(f'{P.DATA}/pre/nasdaq.csv', f'{P.DATA}/nasdaq.csv'); us = P.series(f'{P.DATA}/pre/us10y.csv', f'{P.DATA}/us10y.csv')
def prior(s, n, kind='pct'):
    s = s.dropna(); s = (s / s.shift(n) - 1) if kind == 'pct' else (s - s.shift(n)); p = np.searchsorted(s.index.values, days.values, side='left') - 1
    return pd.Series(np.where(p >= 0, s.values[np.maximum(p, 0)], np.nan), index=days)
def cell(x, y, c=0.25):
    a=(prior(nq,5)*100 < -x).fillna(False); b=(prior(us,5,'diff')*100 > y).fillna(False); return pd.Series(np.where(a,c,1.0),index=days)*pd.Series(np.where(b,c,1.0),index=days)
ens = sum(cell(x,y) for x in (1,2,3) for y in (10,15,20))/9.0; nb3=cell(2,15)
INT = pd.Series(E.cal*RF/365.0, index=days); tt, ss = S.A2(100); shortsig=np.where(tt==-1,-1,0).astype(np.int8); lt, ls = S.baseline(); EV=P.EVAL
def split_leg(En, tdir, tsz):
    R = En.run(tdir, tsz, cost='floor'); fb=np.where(En.first_b)[0]; lb=np.where(En.last_b)[0]; net=pd.Series(R.net_d,index=En.days); gap=np.zeros(len(fb))
    for i in range(1,len(fb)): gap[i]=R.posl[lb[i-1]]*LOT*(En.fo[fb[i]]-En.prev[fb[i]])/CAPITAL
    gap=pd.Series(gap,index=En.days); return net,gap,net-gap
exe=lambda s,G,I: s.shift(1).fillna(1.0)*G + s*I
fl=lambda m:f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
def met(net,a,z): ex=net[a:z]; return metrics_from(ex+INT[a:z],None,None,None,ex)
wl,ws=1.912,0.956
for pname,En in (('real-anchored',Ea),('synthetic',E)):
    L,G,I = split_leg(En,lt,ls); Sh=pd.Series(En.run(shortsig,ss,cost='floor').net_d,index=days); BH=pd.Series(En.run(np.ones(En.N,np.int8),np.ones(En.N),cost='floor',rebal=True).net_d,index=days)
    print(f'\n### Pre-2017 (2012-07..2016-08), {pname} path, floor costs: CAGR / MaxDD / Sharpe  | share of long-leg P&L from overnight gap: {G[EV[0]:EV[1]].sum()/L[EV[0]:EV[1]].sum():.0%}')
    rows={'Plain long-only baseline':L,'Buy and hold futures':BH,'Same weights, no cuts':wl*L+ws*Sh,'NB3 old (cut applied before the gap)':2.0*nb3*L+Sh,'NB3 executable (cut after the gap)':2.0*exe(nb3,G,I)+Sh,
          'Frozen old (cut applied before the gap)':wl*ens*L+ws*Sh,'Frozen executable (cut after the gap)':wl*exe(ens,G,I)+ws*Sh,'Short leg alone':ws*Sh}
    print('| System | 2012-07..2016-08 | 2012-07..2014-12 | 2015-01..2016-08 |'); print('|---|---|---|---|')
    for n,net in rows.items(): print(f'| {n} | {fl(met(net,*EV))} | {fl(met(net,*P.SUB[0]))} | {fl(met(net,*P.SUB[1]))} |')
