import sys, json, time, itertools; sys.path.insert(0,'scripts')
import numpy as np, pandas as pd
from psearch import *          # builds G, NAMES, held4, evr, span, select (greedy) ; main-guarded
import os
SUF=''
if os.environ.get('PRICEONLY'): SUF='_px'
if os.environ.get('GENERIC'):      # economically meaningful factors only: drop single-stock, weekday and calendar-quirk gates
    SUF='_gen'
    bad=('hdfcbank','icicibank','reliance','infy','tcs:','itc:','sbin','lt:','bhartiartl','not_Mon','not_Fri','Tue-Thu','Apr/Jul','not_Jan','btc')
    NAMES=[n for n in NAMES if not any(b in n for b in bad)]
    print('GENERIC mode: gates',len(NAMES),flush=True)
rng=np.random.default_rng(7)
LEGS=['LongNight','LongDay','ShortNight','ShortDay']
base_state=[A_,A_,N_,N_]
def apply_move(st,mv):
    leg,nm=mv; s=list(st)
    if leg<2: s[leg]=st[leg]&G[nm] if nm!='NEVER' else N_
    else: s[leg]=G[nm] if not st[leg].any() else st[leg]&G[nm]
    return s
ALL_MOVES=[(l,n) for l in range(4) for n in NAMES]+[(0,'NEVER'),(1,'NEVER')]
def J2(st,sp_tr,sp_va):
    r,_=evr(st); return Jspan(r,sp_tr),Jspan(r,sp_va),r
def screen(sp_tr,sp_va,K):
    jt0,jv0,_=J2(base_state,sp_tr,sp_va); out=[]
    for mv in ALL_MOVES:
        t,v,_=J2(apply_move(base_state,mv),sp_tr,sp_va)
        if t-jt0>0.5 and v-jv0>0.0: out.append((t-jt0+v-jv0,mv))
    out.sort(reverse=True); return [m for _,m in out[:K]],jt0,jv0
# ---------- techniques: each returns (state_list, description)
def t_greedy(tr,va): st,p=select(tr,va); return st,p
def t_beam(tr,va,W=4,steps=4):
    jt0,jv0,_=J2(base_state,tr,va); beam=[(0.0,base_state,[])]
    for s in range(steps):
        cand=[]
        for sc,st,path in beam:
            for mv in ALL_MOVES:
                if mv in path: continue
                st2=apply_move(st,mv); t,v,_=J2(st2,tr,va)
                if t-jt0>0 and v-jv0>0: cand.append((t+v,st2,path+[mv]))
        if not cand: break
        cand.sort(key=lambda x:-x[0]); beam=cand[:W]
    sc,st,path=beam[0]; return st,[(LEGS[l],n) for l,n in path]
def t_pairs(tr,va,K=150,K3=45):
    top,jt0,jv0=screen(tr,va,K); best=(None,-1e9); 
    for a,b in itertools.combinations(top,2):
        st=apply_move(apply_move(base_state,a),b); t,v,_=J2(st,tr,va)
        if t-jt0>0 and v-jv0>0 and t+v>best[1]: best=((a,b),t+v,st)
    best3=(None,-1e9)
    for a,b,cc in itertools.combinations(top[:K3],3):
        st=apply_move(apply_move(apply_move(base_state,a),b),cc); t,v,_=J2(st,tr,va)
        if t-jt0>0 and v-jv0>0 and t+v>best3[1]: best3=((a,b,cc),t+v,st)
    pick=best3 if best3[1]>best[1]+3 else best                       # need a clear gain to justify a third gate
    if pick[0] is None: return base_state,[]
    return pick[2],[(LEGS[l],n) for l,n in pick[0]]
def yearly(r,years): return np.array([Jspan(r,span(f'{y}-01-01',f'{y}-12-31')) for y in years])
def t_stable(tr,va,max_steps=4):
    y0=days[tr[0]].year; y1=days[va[1]-1].year; yrs=list(range(y0,y1+1))
    rb,_=evr(base_state); jb=yearly(rb,yrs); st=base_state; chosen=[]; cur=jb.copy()
    for s in range(max_steps):
        best=None
        for mv in ALL_MOVES:
            if mv in chosen: continue
            r,_=evr(apply_move(st,mv)); d=yearly(r,yrs)-cur
            frac=(d>0).mean(); m=d.mean()
            if frac>=0.75 and m>0.5 and (best is None or m-0.5*d.std()>best[0]): best=(m-0.5*d.std(),mv,yearly(r,yrs))
        if not best: break
        _,mv,cur=best; chosen.append(mv); st=apply_move(st,mv)
    return st,[(LEGS[l],n) for l,n in chosen]
def t_score(tr,va,K=6):
    """bagging: per leg, average the top-K yearly-consistent gates (soft size 0..1) instead of hard AND"""
    y0=days[tr[0]].year; y1=days[va[1]-1].year; yrs=list(range(y0,y1+1)); rb,_=evr(base_state); jb=yearly(rb,yrs); st=list(base_state); desc=[]
    for leg in range(4):
        sc=[]
        for nm in NAMES:
            s2=apply_move(base_state,(leg,nm)); r,_=evr(s2); d=yearly(r,yrs)-jb
            if (d>0).mean()>=0.7 and d.mean()>0.3: sc.append((d.mean()-0.5*d.std(),nm))
        sc.sort(reverse=True); top=[n for _,n in sc[:K]]
        if top: st[leg]=np.mean([G[n].astype(float) for n in top],axis=0); desc.append((LEGS[leg],top))
    return st,desc
def t_random(tr,va,n=25000):
    jt0,jv0,_=J2(base_state,tr,va); best=(-1e9,None,None)
    for _ in range(n):
        k=rng.integers(1,4); mv=[ALL_MOVES[i] for i in rng.integers(0,len(ALL_MOVES),k)]; st=base_state
        for m in mv: st=apply_move(st,m)
        t,v,_=J2(st,tr,va)
        if t-jt0>0 and v-jv0>0 and t+v>best[0]: best=(t+v,st,mv)
    return (best[1] if best[1] else base_state),[(LEGS[l],n_) for l,n_ in (best[2] or [])]
TECH={'greedy':t_greedy,'beam':t_beam,'pairs':t_pairs,'stable':t_stable,'score':t_score,'random':t_random}
def stats(x,d):
    eq=np.cumprod(1+x); yrs=(d[-1]-d[0]).days/365.25
    return (eq[-1]**(1/yrs)-1)*100,(eq/np.maximum.accumulate(eq)-1).min()*100,x.mean()/x.std()*np.sqrt(252)
if __name__=='__main__':
    names=sys.argv[1:]; t0=time.time(); rb,_=evr(base_state); rn,_=evr([A_,N_,N_,N_])
    for tn in names:
        f=TECH[tn]; oos=[]; idx=[]; picks={}
        for Y in range(2021,2027):
            tr=span('2017-04-01',f'{Y-3}-12-31'); va=span(f'{Y-2}-01-01',f'{Y-1}-12-31'); sy=span(f'{Y}-01-01',f'{Y}-12-31')
            st,desc=f(tr,va); r,_=evr(st); lo,hi=sy; oos.append(r[lo:hi]); idx.append(days[lo:hi]); picks[Y]=str(desc)[:200]
            print(f'[{tn}] {Y}: OOS {((np.prod(1+r[lo:hi])-1)*100):6.1f}% (base {((np.prod(1+rb[lo:hi])-1)*100):5.1f}%) gates {str(desc)[:160]}  [{time.time()-t0:.0f}s]',flush=True)
        x=np.concatenate(oos); d=pd.DatetimeIndex(np.concatenate([np.array(i) for i in idx])); np.save(f'results/oos_{tn}{SUF}.npy',x)
        c1,d1,s1=stats(x,d)
        xb=np.concatenate([rb[span(f'{Y}-01-01',f'{Y}-12-31')[0]:span(f'{Y}-01-01',f'{Y}-12-31')[1]] for Y in range(2021,2027)]); cb,db,sb=stats(xb,d)
        print(f'[{tn}] OOS 2021-26: CAGR {c1:5.1f}%  MaxDD {d1:6.1f}%  Sharpe {s1:4.2f}   | BASELINE {cb:5.1f}% {db:6.1f}% {sb:4.2f}',flush=True)
        # final fit on everything through Oct-2026 (train 2017-04..2022-12, valid 2023-01..2026-10)
        tr=span('2017-04-01','2022-12-31'); va=span('2023-01-01','2026-12-31'); st,desc=f(tr,va); r,_=evr(st)
        fu=span('2017-04-01','2026-12-31'); m=metrics(r,*fu,days)
        print(f'[{tn}] FINAL FIT (in-sample, all data): CAGR {m["CAGR"]:.1f}% DD {m["DD"]:.1f}% Sharpe {m["Sharpe"]:.2f}  gates {str(desc)[:300]}  [{time.time()-t0:.0f}s]',flush=True)
        np.save(f'results/final_{tn}{SUF}.npy',r)
