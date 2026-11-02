import sys, glob, os, json, time; sys.path.insert(0,'scripts')
from fast import *; from gates import build_gates; from factors import _asof
import pandas as pd
c=Ctx(); days=c.days; hm=c.hm; DX=os.path.join(DATA,'x')
PRICEONLY=bool(os.environ.get('PRICEONLY'))
G=build_gates(c)
if PRICEONLY:                                   # keep ONLY gates computed from the repo's own Nifty price series
    d_=c.d; cl_=d_['close']; trr=pd.concat([d_.high-d_.low,(d_.high-cl_.shift()).abs(),(d_.low-cl_.shift()).abs()],axis=1).max(axis=1)
    atrp_=trr.ewm(alpha=1/14,adjust=False).mean()/cl_*100; rng_=(d_.high-d_.low)/cl_*100
    sh_=lambda x: x.shift(1).reindex(days)
    for k in [1.5,2.0,2.5]: G[f'prev_range<{k}xATR']=(sh_(rng_)<k*sh_(atrp_)).fillna(True).values
    for k in [1.2,1.8]: G[f'prev_range%<{k}']=(sh_(rng_)<k).fillna(True).values
    for k in [10,20]: G[f'atr_jump5d<{k}%']=((sh_(atrp_)/atrp_.shift(6).reindex(days)-1)*100<k).fillna(True).values
    G['prev_ret>-1.5%']=(sh_(cl_.pct_change()*100)>-1.5).fillna(True).values
    PREF=('close>sma','sma50>sma200','adx>=','mom','dd252','rsi','atr%','rv10','prev_gap','prev_day_ret','prev_range','prev_ret','atr_jump')
    G={k:v for k,v in G.items() if k in('ALWAYS','NEVER') or k.startswith(PREF)}
    print('PRICE-ONLY mode: gates',len(G),flush=True)
# ---- auto templates over every extra series
INDIAN=('nifty_','hdfcbank','icicibank','reliance','infy','tcs','itc','sbin','lt','bhartiartl')
for f in ([] if PRICEONLY else sorted(glob.glob(f'{DX}/*.csv'))):
    nm=os.path.basename(f)[:-4]; s=pd.read_csv(f,parse_dates=['date']).set_index('date')['close'].astype(float).dropna()
    s=s[~s.index.duplicated()]
    if nm=='btc': s=s  # trades daily incl. weekends: asof handles it
    if nm.startswith(INDIAN): A=lambda x: x.reindex(days).ffill().shift(1)
    else: A=lambda x: _asof(x,days)
    def add(k,v): G[f'{nm}:{k}']=pd.Series(A(v)).reindex(days).fillna(True).astype(bool).values if False else (A(v).fillna(True).astype(bool).values if False else None)
    feats={'r1>0':s.pct_change()>0,'r1>-1%':s.pct_change()>-0.01,'r5>0':s.pct_change(5)>0,'r21>0':s.pct_change(21)>0,'>sma50':s>s.rolling(50).mean(),'>sma200':s>s.rolling(200).mean(),'r21>5%':s.pct_change(21)>0.05}
    for k,v in feats.items():
        a=A(v.astype(float).where(s.pct_change(21).notna()))        # keep NaN warm-up
        G[f'{nm}:{k}']=(a.fillna(1.0)>0.5).values
base_names=[k for k in G if k not in('ALWAYS','NEVER')]
for k in base_names: G['~'+k]=~G[k]
NAMES=[k for k in G if k not in('ALWAYS','NEVER')]
print('gates incl. negations:',len(NAMES),flush=True)
dir_=c.green_prev; red_prev=np.r_[False,(c.green==False)[:-1]]&(np.r_[0,np.zeros(len(c.green)-1)]==0)
from btlib import supertrend
stdir=supertrend(c.b,14,3.0)['dir'].values; red_prev=np.r_[False,stdir[:-1]==-1]
A_=G['ALWAYS']; N_=G['NEVER']
def held4(LN,LD,SN,SD,late='15:15'):
    lb=hm>=late
    lg=c.green_prev*np.where(lb,LN[c.day_id],LD[c.day_id])
    sh=red_prev*np.where(lb,SN[c.day_id],SD[c.day_id])
    return lg.astype(float)-sh.astype(float)
def span(a,b): return (np.searchsorted(days,pd.Timestamp(a)),np.searchsorted(days,pd.Timestamp(b),side='right'))
def evr(state,late='15:15'):
    r,net=c.daily_returns(held4(*state,late=late)); return r,net
def Jspan(r,sp): m=metrics(r,*sp,days); return m['J'] if m else -1e9
def select(sp_tr,sp_va,late='15:15',max_steps=5,allow_short=True,verbose=False):
    st=[A_.copy(),A_.copy(),N_.copy(),N_.copy()]; r,_=evr(st,late); jt,jv=Jspan(r,sp_tr),Jspan(r,sp_va); path=[]
    for step in range(max_steps):
        best=None
        for leg in range(4 if allow_short else 2):
            for nm in NAMES+(['NEVER'] if leg in(0,1) else []):
                if leg<2: new=st[leg]&G[nm] if nm!='NEVER' else N_
                else: new=G[nm] if not st[leg].any() else st[leg]&G[nm]
                s2=list(st); s2[leg]=new; r2,_=evr(s2,late); t2,v2=Jspan(r2,sp_tr),Jspan(r2,sp_va)
                if t2-jt>0.75 and v2-jv>0.0 and (best is None or t2+v2>best[0]): best=(t2+v2,leg,nm,s2,t2,v2)
        if not best: break
        _,leg,nm,st,jt,jv=best; path.append((['LongNight','LongDay','ShortNight','ShortDay'][leg],nm))
        if verbose: print('   +',path[-1],round(jt,1),round(jv,1),flush=True)
    return st,path
if __name__=='__main__':
    t0=time.time()
    # ===== A) the brief's split: select on 2017-21, confirm 2022-23, report 2024-26
    tr,va,te,fu=span('2017-04-01','2021-12-31'),span('2022-01-01','2023-12-31'),span('2024-01-01','2026-12-31'),span('2017-04-01','2026-12-31')
    print('A) brief split search (long+short)',flush=True)
    st,path=select(tr,va,verbose=True)
    r,net=evr(st); rb,_=evr([A_,A_,N_,N_]); rn,_=evr([A_,N_,N_,N_])
    def rowm(nm,rr): 
        return f'{nm:34s} '+' | '.join(f'{k} {metrics(rr,*s,days)["CAGR"]:5.1f}/{metrics(rr,*s,days)["DD"]:6.1f}/{metrics(rr,*s,days)["Sharpe"]:4.2f}' for k,s in [('train',tr),('valid',va),('test',te),('full',fu)])
    print(rowm('BASELINE',rb)); print(rowm('night-only (no gates)',rn)); print(rowm('SEARCHED long+short',r)); print('path',path,flush=True)
    json.dump(path,open('results/psearch_brief.json','w'))
    # ===== B) walk-forward: each year selected only on data before it
    print('\nB) walk-forward OOS (select on <=Y-3 train / Y-2..Y-1 valid, apply to Y)',flush=True)
    oos_s=[];oos_b=[];oos_n=[];idxs=[]
    for Y in range(2021,2027):
        sp_tr=span('2017-04-01',f'{Y-3}-12-31'); sp_va=span(f'{Y-2}-01-01',f'{Y-1}-12-31'); sp_y=span(f'{Y}-01-01',f'{Y}-12-31')
        stY,pY=select(sp_tr,sp_va); rY,_=evr(stY)
        lo,hi=sp_y; oos_s.append(rY[lo:hi]); oos_b.append(rb[lo:hi]); oos_n.append(rn[lo:hi]); idxs.append(days[lo:hi])
        print(f' {Y}: gates {pY}  OOS year ret {((np.prod(1+rY[lo:hi])-1)*100):6.1f}% (base {((np.prod(1+rb[lo:hi])-1)*100):5.1f}%)  [{time.time()-t0:.0f}s]',flush=True)
    for nm,arr in [('BASELINE',oos_b),('night-only no gates',oos_n),('SEARCHED walk-forward',oos_s)]:
        x=np.concatenate(arr); d=np.concatenate([np.array(i) for i in idxs]); eq=np.cumprod(1+x); yrs=(d[-1]-d[0]).days/365.25
        print(f' OOS 2021-26 {nm:24s} CAGR {(eq[-1]**(1/yrs)-1)*100:5.1f}%  MaxDD {((eq/np.maximum.accumulate(eq)-1).min()*100):6.1f}%  Sharpe {x.mean()/x.std()*np.sqrt(252):4.2f}')
    print('total time',round(time.time()-t0),'s')
