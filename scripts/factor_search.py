"""Factor search, long-only AND long/short, short-term (1-20d) and long-term (60-250d) horizons.  Same engine/costs/next-open.
PROTOCOL (fixed before running): every candidate = one factor x one form (long/flat or long/short) x one direction (follow or fade) x one trigger (median or 20/80 tails),
thresholds from ROLLING 252d history only.  Selection on TRAIN 2013-21 Sharpe; shortlist needs train&valid(2022-23) Sharpe>0.4; final portfolio = shortlist equal-weighted,
vol-targeted (7% ann, 60d trailing, cap 4x).  Independent check: yearly walk-forward 2018-2026 (each year uses only candidates ranked on past years).
Test 2024-26 was already seen for earlier sleeves, so walk-forward OOS years are the cleaner evidence.  Every trial is counted."""
import numpy as np, pandas as pd
exec(open('scripts/novel_search.py').read().split('RES2 = {}')[0])
c=D['c']; h=D['h']; l=D['l']; o=D.get('o', c); r1=c.pct_change()
sm=lambda x,w:x.rolling(w).mean()
def rsi(x,w):
    d=x.diff(); u=d.clip(lower=0).rolling(w).mean(); dn=(-d.clip(upper=0)).rolling(w).mean(); return 100-100/(1+u/dn.replace(0,np.nan))
ibs=(c-l)/(h-l).replace(0,np.nan)
F={}
for k in [1,3,5,10]: F[f'ret{k}d (short-term reversal/mom)']=c/c.shift(k)-1
for k in [20,60,120,250]: F[f'mom{k}d']=c/c.shift(k)-1
F['mom12-1 (250 skip 20)']=c.shift(20)/c.shift(250)-1
F['dist50dma']=c/sm(c,50)-1; F['dist200dma']=c/sm(c,200)-1; F['ma50/200']=sm(c,50)/sm(c,200)-1
F['rsi2']=rsi(c,2); F['rsi14']=rsi(c,14); F['ibs']=ibs
F['rv20']=rv20; F['rv ratio 5/60']=r1.rolling(5).std()/r1.rolling(60).std()
F['vix']=vixs; F['vix chg1']=vixs.pct_change(); F['vix chg5']=vixs.pct_change(5); F['vix/ma20']=vixs/sm(vixs,20)
F['vix - rv20 (VRP)']=vixs-rv20
F['carry spread']=spread; F['spread chg5']=spread-spread.shift(5)
F['volume z60']=z(vsr,60); F['volume chg5']=vsr/sm(vsr,5)-1
F['oi chg1 (adj)']=oi.pct_change() if hasattr(oi,'pct_change') else oi; F['oi chg5']=oi.pct_change(5)
F['range/atr']=(h-l)/(h-l).rolling(14).mean(); F['gap']=(o/c.shift())-1
F['dd from 252d high']=c/c.rolling(252).max()-1
F['trading days to expiry']=pd.Series(FEATS['tdte'].values if hasattr(FEATS['tdte'],'values') else FEATS['tdte'],index=c.index)
TR=[];RET={}
for name,x in F.items():
    x=pd.Series(np.asarray(x,float),index=c.index)
    med=x.rolling(252).median(); q20=x.rolling(252).quantile(.2); q80=x.rolling(252).quantile(.8)
    trig={'median':(x>med,x<med),'tails':(x>q80,x<q20)}
    for tn,(hi,lo) in trig.items():
        for form in ['L/F','L/S']:
            for dr in ['follow','fade']:
                up,dn=(hi,lo) if dr=='follow' else (lo,hi)
                sig=pd.Series(0.0,index=c.index); sig[up]=1.0
                if form=='L/S': sig[dn]=-1.0
                sig=sig.where(x.notna(),0.0)
                lab=f'{name} | {tn} | {form} | {dr}'
                r=evaluate(lab,lambda D,ls=False,_s=sig:_s,{}); RET[lab]=r; TR.append(lab)
NT=len(TR); print('candidates (all counted):',NT)
def mm(r,k): a,b=IDX[k]; return met(r['ret'][a:b])
rows=[]
for lab,r in RET.items(): rows.append(dict(lab=lab,**{f'{k}_S':mm(r,k)['Sharpe'] for k in ['train','valid','test','full']},tr_cagr=mm(r,'train')['CAGR'],expo=np.mean(np.abs(r['pos'])>0)*100))
T=pd.DataFrame(rows)
print('best 8 by TRAIN Sharpe:');print(T.sort_values('train_S',ascending=False).head(8).round(2).to_string(index=False))
sl=T[(T.train_S>0.4)&(T.valid_S>0.4)&(T.expo>=8)].sort_values('train_S',ascending=False)
print('\nshortlist (train&valid Sharpe>0.4, exposure>=8%):',len(sl),' of which test>0:',int((sl.test_S>0).sum()));print(sl.head(15).round(2).to_string(index=False))
# luck check: expected max Sharpe among NT zero-skill trials over train+valid length
nobs=IDX['valid'][1]-IDX['train'][0]; print('luck benchmark: max annual Sharpe expected from',NT,'zero-skill trials ~',round(np.sqrt(2*np.log(NT))/np.sqrt(nobs/252),2))
def sized(x,tv=0.07,cap=4):
    v=pd.Series(x).rolling(60).std().shift(1)*np.sqrt(252); s=np.minimum(cap,tv/v.replace(0,np.nan)).fillna(1.0).values; return x*s
def show(l,x): print(f"| {l} | "+" | ".join("{CAGR:.1f}% / {Sharpe:.2f} / {MaxDD:.1f}%".format(**met(x[IDX[k][0]:IDX[k][1]])) for k in ['train','valid','test','full'])+" |")
print("\n| Portfolio | Train | Valid | Test | Full |\n|---|---|---|---|---|")
if len(sl):
    port=np.mean([RET[l]['ret'] for l in sl.lab],axis=0); show(f'Shortlist EW ({len(sl)} cands), 1x',port); show('Shortlist EW, vol-target 7%',sized(port))
    ls_only=sl[sl.lab.str.contains('L/S')]
    if len(ls_only): p2=np.mean([RET[l]['ret'] for l in ls_only.lab],axis=0); show(f'  long/short only ({len(ls_only)}), vol-target 7%',sized(p2))
    lf=sl[sl.lab.str.contains('L/F')]
    if len(lf): p3=np.mean([RET[l]['ret'] for l in lf.lab],axis=0); show(f'  long/flat only ({len(lf)}), vol-target 7%',sized(p3))
# walk-forward: for year Y use candidates with (past-only) Sharpe>0.4 over all days before Y (min 3y), top 10 by that Sharpe
dates=c.index; WF=np.zeros(len(c)); lab_list=list(RET); M=np.array([RET[l]['ret'] for l in lab_list])
for Y in range(2016,2027):
    a=np.searchsorted(dates,pd.Timestamp(f'{Y}-01-01')); b=np.searchsorted(dates,pd.Timestamp(f'{Y+1}-01-01')); s0=np.searchsorted(dates,pd.Timestamp('2013-01-01'))
    past=M[:,s0:a]; sh=past.mean(1)/np.maximum(past.std(1,ddof=1),1e-12)*np.sqrt(252); top=np.argsort(-sh)[:10]; WF[a:b]=M[top,a:b].mean(0)
a0=np.searchsorted(dates,pd.Timestamp('2016-01-01')); 
def show2(l,x): m=met(x[a0:]); print(f"| {l} | {m['CAGR']:.1f}% / {m['Sharpe']:.2f} / {m['MaxDD']:.1f}% |")
print("\nWalk-forward OOS 2016-2026 (top-10 of all candidates by past-only Sharpe, re-picked yearly)\n| Series | CAGR / Sharpe / MaxDD |\n|---|---|"); show2('WF top-10, 1x',WF); show2('WF top-10, vol-target 7%',sized(WF)); show2('Buy&Hold futures',pnl(np.ones(len(c)),0.0001))
pd.to_pickle(dict(T=T),'results/factor_search.pkl')
