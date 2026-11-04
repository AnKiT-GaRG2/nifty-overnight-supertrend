import sys, json, itertools; sys.path.insert(0,'scripts')
import numpy as np, pandas as pd
import rm_data, rm_final
from rm_engine import Engine, metrics_from, RF, LOT, CAPITAL, SPLITS
from rm_ideas import make_sig, trial_log, RES, DATA
from rm_signals import supertrend
LOCK='2023-12-31'
ds=pd.read_pickle(f'{rm_data.DATA}/rm/dataset.pkl'); cut=pd.Timestamp(LOCK)
ds=dict(ds); ds['b15']=ds['b15'][ds['b15']['date']<=cut]; ds['m1']=ds['m1'][ds['m1']['date']<=cut]; ds['daily']=ds['daily'][ds['daily'].index<=cut]
E=Engine(ds); S=make_sig(E); days=E.days; assert days.max()<=cut, 'LOCK VIOLATED'
fut=pd.read_csv(f'{rm_data.DATA}/fut/nifty_fut.csv',parse_dates=['date','expiry']).drop_duplicates(['date','expiry']); fut=fut[(fut.open>0)&(fut.close>0)].set_index(['date','expiry'])
Ea,_=rm_final.anchored_engine(E,fut)
def series(pre,post):
    a=pd.read_csv(pre,parse_dates=['date']).set_index('date')['close']; b=pd.read_csv(post,parse_dates=['date']).set_index('date')['close']; s=pd.concat([a,b]); return s[~s.index.duplicated(keep='first')].sort_index()
nq=series(f'{DATA}/pre/nasdaq.csv',f'{DATA}/nasdaq.csv'); us=series(f'{DATA}/pre/us10y.csv',f'{DATA}/us10y.csv')
def make_ens(days):
    def prior(s,n,kind='pct'):
        s=s.dropna(); s=(s/s.shift(n)-1) if kind=='pct' else (s-s.shift(n)); p=np.searchsorted(s.index.values,days.values,side='left')-1
        return pd.Series(np.where(p>=0,s.values[np.maximum(p,0)],np.nan),index=days)
    def cell(x,y,c=0.25):
        a=(prior(nq,5)*100< -x).fillna(False); b=(prior(us,5,'diff')*100>y).fillna(False); return pd.Series(np.where(a,c,1.0),index=days)*pd.Series(np.where(b,c,1.0),index=days)
    return sum(cell(x,y) for x in (1,2,3) for y in (10,15,20))/9.0
ens=make_ens(days); INT=pd.Series(E.cal*RF/365.0,index=days)
CFG=[(n,m) for n in (10,14,20) for m in (2.5,3.0,3.5)]
def sma_mask(S):
    return (S.d2b(S.dd.close.values) < S.d2b(S.sma_daily(100)))
def legs_signals(S, idea, tau=None, med=None):
    N=S.N; mask=sma_mask(S); one=np.ones(N)
    if idea=='base':
        t=(S.st==1).astype(np.int8); s=np.where((S.st==-1)&mask,-1,0).astype(np.int8); return (t,one),(s,one)
    sts=np.array([supertrend(S.h,S.l,S.c,n,m)[0] for n,m in CFG]); fl=(sts==1).mean(0); fs=(sts==-1).mean(0)*mask
    Lt=(fl>0).astype(np.int8); Lz=fl; St=np.where(fs>0,-1,0).astype(np.int8); Sz=fs
    if idea=='I1': return (Lt,Lz),(St,Sz)
    return None
def day_u(S, tau, med):
    atrp=pd.Series(S.atr15/S.c); dayatr=atrp.groupby(S.dc).mean().reindex(range(len(S.D))).values
    prev=pd.Series(dayatr).shift(1).values; u=np.minimum(1.0, tau*med/prev); u=np.where(np.isnan(u),1.0,u); return u[S.dc]
def run_legs(En, S, idea, cost, tau=None, med=None):
    (lt,lz),(st,sz)=legs_signals(S, 'I1' if idea in ('I1','I3') else 'base')
    if idea in ('I2','I3'): u=day_u(S,tau,med); lz=lz*u; sz=sz*u
    mc=2 if idea in ('I1','I2','I3') else 1
    R=En.run(lt,lz,cost=cost,min_chg=mc); fb=np.where(En.first_b)[0]; lb=np.where(En.last_b)[0]; net=pd.Series(R.net_d,index=En.days); gap=np.zeros(len(fb))
    for i in range(1,len(fb)): gap[i]=R.posl[lb[i-1]]*LOT*(En.fo[fb[i]]-En.prev[fb[i]])/CAPITAL
    gap=pd.Series(gap,index=En.days); Sh=pd.Series(En.run(st,sz,cost=cost,min_chg=mc).net_d,index=En.days); return net,gap,net-gap,Sh
def stream(En,S,idea,cost,ens,tau=None,med=None):
    L,G,I,Sh=run_legs(En,S,idea,cost,tau,med); return 1.912*(ens.shift(1).fillna(1.0)*G+ens*I)+0.956*Sh
def met(net,a,z,INT): ex=net[a:z]; return metrics_from(ex+INT[a:z],None,None,None,ex)
fl_=lambda m:f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
def eq_dd_cagr(net,ref_dd,a,z,INT):
    lo,hi=0.05,4.0
    for _ in range(40):
        s=(lo+hi)/2
        if met(net*s,a,z,INT)['MaxDD']<ref_dd: hi=s
        else: lo=s
    return lo, met(net*lo,a,z,INT)
DEV=('2017-04-03',LOCK); TRN=('2017-04-03','2021-12-31')
if __name__=='__main__':
    # train median of the previous-day ATR%
    atrp=pd.Series(S.atr15/S.c); dayatr=atrp.groupby(S.dc).mean(); dd_idx=S.D.index; dayatr.index=dd_idx[dayatr.index]; MED=float(dayatr[TRN[0]:TRN[1]].median()); print('train median daily ATR% =',round(MED*100,4),'%\n')
    json.dump({'MED':MED},open(f'{RES}/lock_med.json','w'))
    out={}
    for cost in ('real','floor'):
        B=stream(Ea,S,'base',cost,ens); mb=met(B,*DEV,INT); print(f'### {cost} costs, real-anchored, DEV 2017-04..2023-12 (data after 2023 is locked). Baseline: {fl_(mb)}')
        print('| Idea | Sharpe/CAGR/MaxDD | Equal-drawdown CAGR (scale) | Sharpe vs baseline |'); print('|---|---|---|---|')
        cells={'Baseline':('base',None)}; cells.update({'I1 ensemble':('I1',None)}); cells.update({f'I2 vol-scaled tau={t}':('I2',t) for t in (1.0,1.25,1.5)}); cells.update({f'I3 = I1 + I2 tau={t}':('I3',t) for t in (1.0,1.25,1.5)})
        for n,(idea,tau) in cells.items():
            net=B if idea=='base' else stream(Ea,S,idea,cost,ens,tau,MED); m=met(net,*DEV,INT); sc,me=eq_dd_cagr(net,mb['MaxDD'],*DEV,INT); out[(cost,n)]=(m,sc,me)
            if idea!='base': trial_log('LOCK_'+idea,{'tau':tau,'cost':cost},'train',m)
            print(f"| {n} | {fl_(m)} | {me['CAGR']:.1%} ({sc:.2f}) | {m['Sharpe']-mb['Sharpe']:+.2f} |")
        print()
    pickle_out={f'{k[0]}|{k[1]}':[v[0]['Sharpe'],v[0]['CAGR'],v[0]['MaxDD'],v[1],v[2]['CAGR']] for k,v in out.items()}; json.dump(pickle_out,open(f'{RES}/lock_dev_results.json','w'),indent=1)
