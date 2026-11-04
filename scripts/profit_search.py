import itertools, numpy as np, pandas as pd, sys
COST, ROLL = 0.00025, 0.0005
f = pd.read_csv('data/fut/nifty_fut.csv', parse_dates=['date','expiry']).drop_duplicates(['date','expiry'])
f = f[(f.open>0)&(f.close>0)].set_index(['date','expiry']).sort_index()
days = pd.DatetimeIndex(sorted(f.index.get_level_values(0).unique())); n=len(days)
rcc=np.zeros(n); rnight=np.zeros(n); rday=np.zeros(n); rollf=np.zeros(n); Kp=None
Cc=np.full(n,np.nan);Hh=Cc.copy();Ll=Cc.copy()
for i in range(1,n):
    t0,t1=days[i-1],days[i]; ex0=f.loc[t0].index; ex1=f.loc[t1].index
    k=min(e for e in ex0 if e>t0 and e in ex1); a=f.loc[(t0,k)]; b=f.loc[(t1,k)]
    rcc[i]=b.close/a.close-1; rnight[i]=b.open/a.close-1; rday[i]=b.close/b.open-1
    rollf[i]=float(Kp is not None and k!=Kp); Kp=k
S=lambda a:pd.Series(a,index=days)
c=S(100*np.cumprod(1+rcc)); vix=pd.read_csv('data/vix.csv',parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()
r=S(rcc); sma=lambda x,w:x.rolling(w).mean()
PER={'train':('2018-04-01','2021-12-31'),'valid':('2022-01-01','2023-12-31'),'test':('2024-01-01','2026-12-31')}
sl=lambda a,b:(np.searchsorted(days.values,np.datetime64(a)),np.searchsorted(days.values,np.datetime64(b),side='right'))
IDX={k:sl(*v) for k,v in PER.items()}
def pnl(sig,leg='cc'):
    p=np.nan_to_num(np.asarray(sig,float)); 
    if leg=='cc':
        held=np.r_[0.0,p[:-1]]; prev=np.r_[0.0,held[:-1]]
        return held*rcc-np.abs(held-prev)*COST-np.abs(held)*ROLL*rollf
    if leg=='night': # signal at close t -> hold close t -> open t+1
        held=np.r_[0.0,p[:-1]]; return held*rnight-2*COST*np.abs(held)
    if leg=='day':   # signal known at close t-1 -> hold open t -> close t
        held=np.r_[0.0,p[:-1]]; return held*rday-2*COST*np.abs(held)
def met(x):
    if len(x)<30: return (np.nan,np.nan,np.nan,0)
    eq=np.cumprod(1+x); cg=eq[-1]**(252/len(x))-1; sd=x.std(ddof=1); dd=(eq/np.maximum.accumulate(np.r_[1,eq])[1:]-1).min()
    return (100*cg,(x.mean()/sd*np.sqrt(252) if sd>0 else 0),100*dd,float(np.mean(x!=0)))
cands=[]
def add(name,sig,leg='cc'): cands.append((name,sig,leg))
# --- calendar: turn of month
dts=S(days); ym=dts.dt.to_period('M'); posm=dts.groupby(ym).cumcount(); nm=dts.groupby(ym).transform('count'); toend=nm-posm-1
for pre in [1,2,3,4,5]:
    for post in [0,1,2,3,4]:
        add(f'TOM long last{pre}+first{post}',((toend<pre)|(posm<post)).astype(float).values)
for dow_set in [(0,),(1,),(2,),(3,),(4,),(0,1),(3,4),(0,3,4),(1,2,3)]:
    add(f'Long hold into days {dow_set} (by weekday of held day)',np.roll(dts.dt.dayofweek.isin(dow_set).values.astype(float),-1))
# --- dips
z=lambda w:(r/r.rolling(w).std().shift())
for w,th,hold,filt in itertools.product([20,60],[1.0,1.5,2.0],[1,2,3,5],['none','200','vix<25','200&vix<25']):
    sig=(z(w)<-th)
    if filt=='200':sig&=c>sma(c,200)
    elif filt=='vix<25':sig&=vix<25
    elif filt=='200&vix<25':sig&=(c>sma(c,200))&(vix<25)
    add(f'Dip z{w}<-{th} hold{hold} filt={filt}',sig.astype(float).rolling(hold,min_periods=1).max().values)
for n_dn,hold,filt in itertools.product([2,3,4],[1,2,3,5],['none','200']):
    dn=(r<0).rolling(n_dn).sum()==n_dn
    if filt=='200':dn&=c>sma(c,200)
    add(f'{n_dn} down days hold{hold} filt={filt}',dn.astype(float).rolling(hold,min_periods=1).max().values)
# --- VIX spike
for x,hold,filt in itertools.product([0.05,0.08,0.12,0.2],[1,3,5,10],['none','c<200']):
    sp=(vix/vix.shift()-1)>x
    if filt=='c<200':sp&=c<sma(c,200)
    add(f'VIX spike>{x} hold{hold} {filt}',sp.astype(float).rolling(hold,min_periods=1).max().values)
for lv,hold in itertools.product([20,25,30],[5,10,20]):
    add(f'VIX>{lv} long hold{hold}',(vix>lv).astype(float).rolling(hold,min_periods=1).max().values)
# --- IBS / RSI2 with trend and vol filters
hh=S(np.nan_to_num(c.values))  # close-only IBS proxy unavailable; skip
def rsi(x,w):
    d=x.diff(); u=d.clip(lower=0).ewm(alpha=1/w,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/w,adjust=False).mean(); return 100-100/(1+u/dn)
for w,lo,hold,filt in itertools.product([2,3,5],[5,10,20],[1,2,3,5],['none','200']):
    s=rsi(c,w)<lo
    if filt=='200':s&=c>sma(c,200)
    add(f'RSI{w}<{lo} hold{hold} filt={filt}',s.astype(float).rolling(hold,min_periods=1).max().values)
# --- legs: night/day with trend filter
for filt in ['none','c>200','c>50','vix<20','vix<15','c>200&vix<20']:
    m=pd.Series(True,index=days)
    if filt=='c>200':m=c>sma(c,200)
    if filt=='c>50':m=c>sma(c,50)
    if filt=='vix<20':m=vix<20
    if filt=='vix<15':m=vix<15
    if filt=='c>200&vix<20':m=(c>sma(c,200))&(vix<20)
    add(f'NIGHT leg long filt={filt}',m.astype(float).values,'night')
    add(f'DAY leg long filt={filt}',m.astype(float).values,'day')
    add(f'NIGHT short filt={filt}',-m.astype(float).values,'night')
    add(f'DAY short filt={filt}',-m.astype(float).values,'day')
# --- trend with vol-scaling
for w,tv in itertools.product([50,100,200],[0.08,0.12,0.15]):
    vol=r.rolling(20).std().shift()*np.sqrt(252); sc=(tv/vol).clip(upper=1.0)
    add(f'Price>{w}DMA volTarget{tv}',((c>sma(c,w))*sc).fillna(0).values)
for w,hold in itertools.product([50,100,200],[1]):
    add(f'Price>{w}DMA & VIX falling',((c>sma(c,w))&(vix<sma(vix,10))).astype(float).values)
res=[]
for name,sig,leg in cands:
    x=pnl(sig,leg); row={'name':name}
    for k,(i,j) in IDX.items():
        cg,sh,dd,ex=met(x[i:j]); row.update({f'cagr_{k}':cg,f'sh_{k}':sh,f'dd_{k}':dd,f'exp_{k}':ex})
    res.append(row)
D=pd.DataFrame(res); D['tv_min']=D[['sh_train','sh_valid']].min(axis=1)
D.to_csv('results/profit_search.csv',index=False)
print('candidates',len(D))
sel=D[(D.cagr_train>0)&(D.cagr_valid>0)&(D.sh_train>0.5)&(D.sh_valid>0.5)&(D.exp_train>0.02)].sort_values('tv_min',ascending=False)
print('selected on train+valid:',len(sel),' of which test CAGR>0:',(sel.cagr_test>0).sum())
pd.set_option('display.width',250); pd.set_option('display.max_colwidth',60)
print(sel[['name','cagr_train','sh_train','cagr_valid','sh_valid','cagr_test','sh_test','dd_test','exp_train']].round(2).head(30).to_string())
print('\nUnconditional base rate: share of ALL candidates with test CAGR>0:',round((D.cagr_test>0).mean(),2))

# ---- event-sleeve portfolio, rule fixed from train+valid only
ev=sel[sel.exp_train<0.10]; print('\nEvent sleeves (exposure<10%) chosen on train+valid:',len(ev)); print(ev.name.tolist())
lookup={nm:(sg,lg) for nm,sg,lg in cands}
legs=np.array([pnl(*lookup[nm]) for nm in ev.name]); port=legs.mean(axis=0)
tv_i=IDX['train'][0]; tv_j=IDX['valid'][1]; vol_tv=port[tv_i:tv_j].std(ddof=1)*np.sqrt(252)
print('portfolio vol (train+valid, unlevered) %.2f%%'%(100*vol_tv))
for lev in [1,3,5,'10% vol target']:
    L=(0.10/vol_tv) if lev=='10% vol target' else lev; x=port*L
    out=[f'{k}: {met(x[i:j])[0]:.1f}% / Sh {met(x[i:j])[1]:.2f} / DD {met(x[i:j])[2]:.1f}%' for k,(i,j) in IDX.items()]
    print(f'lev {L:.1f}x ->',' | '.join(out))
