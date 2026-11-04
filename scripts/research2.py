import itertools, numpy as np, pandas as pd
exec(open('scripts/profit_search.py').read().split("cands=[]")[0])      # reuse data build + pnl/met helpers
cands=[]
def add(name,sig,leg='cc'): cands.append((name,np.nan_to_num(np.asarray(sig,float)),leg))
R=lambda s,h:s.astype(float).rolling(h,min_periods=1).max().values
hi=lambda x,w:x.rolling(w).max().shift(); lo=lambda x,w:x.rolling(w).min().shift()
def rsi(x,w):
    d=x.diff(); u=d.clip(lower=0).ewm(alpha=1/w,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/w,adjust=False).mean(); return 100-100/(1+u/dn)
FILT={'none':pd.Series(True,index=days),'c>200':c>sma(c,200),'c>100':c>sma(c,100),'c>50':c>sma(c,50),'vix<25':vix<25,'vix<20':vix<20,'c>200&vix<25':(c>sma(c,200))&(vix<25),'c<200':c<sma(c,200)}
# 1 dips (z-score), N-day drop, RSI reversal  (long)
for w,th,h,fk in itertools.product([10,20,60],[1.0,1.5,2.0,2.5],[1,2,3,5],['none','c>200','vix<25','c>200&vix<25','c<200']):
    add(f'Dip z{w}<-{th} h{h} {fk}',R(((r/r.rolling(w).std().shift())<-th)&FILT[fk],h))
for nd,x,h,fk in itertools.product([3,5,10],[0.015,0.025,0.04],[1,3,5,10],['none','c>200','vix<25','c<200']):
    add(f'{nd}d drop>{x} h{h} {fk}',R((c/c.shift(nd)-1<-x)&FILT[fk],h))
for w,lo_,h,fk in itertools.product([2,3,5,7,10],[5,10,15,20,30],[1,2,3,5],['none','c>200','c>50','vix<25','c<200']):
    add(f'RSI{w}<{lo_} h{h} {fk}',R((rsi(c,w)<lo_)&FILT[fk],h))
# 2 VIX based
for x,h,fk in itertools.product([0.05,0.08,0.12,0.2],[1,2,3,5,10],['none','c>200','c<200']):
    add(f'VIX spike>{x} h{h} {fk}',R(((vix/vix.shift()-1)>x)&FILT[fk],h))
for k,h in itertools.product([1.1,1.2,1.3,1.5],[1,3,5,10]):
    add(f'VIX>{k}xSMA20 h{h}',R(vix>k*sma(vix,20),h))
for lv,h in itertools.product([18,20,25,30],[3,5,10,20]):
    add(f'VIX>{lv} h{h}',R(vix>lv,h))
# 3 trend / breakout long-only with filters
for w in [20,50,100,150,200]:
    for fk in ['none','vix<25','vix<20']:
        add(f'Price>{w}DMA {fk}',((c>sma(c,w))&FILT[fk]).astype(float).values)
for a,b in [(5,20),(10,50),(20,50),(20,100),(50,200)]: add(f'SMA{a}>{b}',(sma(c,a)>sma(c,b)).astype(float).values)
for en,fk in itertools.product([10,20,40,60,100],['none','vix<25']): add(f'Close>{en}d high h-until-10d-low {fk}',None) if False else None
for w,tv in itertools.product([50,100,200],[0.06,0.08,0.12]):
    vol=r.rolling(20).std().shift()*np.sqrt(252); add(f'Price>{w}DMA volT{tv}',((c>sma(c,w))*(tv/vol).clip(upper=1.5)).fillna(0).values)
# 4 shorts (overbought in downtrend, vol spikes)
for w,hi_,h in itertools.product([2,5,10],[80,90,95],[1,3,5]):
    add(f'SHORT RSI{w}>{hi_} h{h} c<200',-R((rsi(c,w)>hi_)&(c<sma(c,200)),h))
    add(f'SHORT RSI{w}>{hi_} h{h} none',-R(rsi(c,w)>hi_,h))
# 5 seasonality
dts=S(days); ym=dts.dt.to_period('M'); posm=dts.groupby(ym).cumcount(); nm=dts.groupby(ym).transform('count'); toend=nm-posm-1
for pre,post in itertools.product([1,2,3,5],[0,1,2,3,4]):
    for fk in ['none','c>200','vix<25']: add(f'TOM last{pre}+first{post} {fk}',(((toend<pre)|(posm<post))&FILT[fk]).astype(float).values)
for d in [(0,),(1,),(2,),(3,),(4,),(0,4),(3,4)]: add(f'Hold into weekdays {d}',np.roll(dts.dt.dayofweek.isin(d).values.astype(float),-1))
# 6 legs
for fk in ['none','c>200','c>50','vix<20','vix<25','c>200&vix<25']:
    for nm_,sg in [('long',1),('short',-1)]:
        add(f'NIGHT {nm_} {fk}',sg*FILT[fk].astype(float).values,'night'); add(f'DAY {nm_} {fk}',sg*FILT[fk].astype(float).values,'day')
# 7 regime switch composites
bull=(c>sma(c,200)); lowv=vix<18; highv=vix>=22
add('RegimeSwitch: trend(c>50) if vix<18 else dip(RSI5<20)',np.where(lowv,(c>sma(c,50)).astype(float),R(rsi(c,5)<20,3)))
add('RegimeSwitch: bull->long, bear->dip only',np.where(bull,1.0,R(rsi(c,5)<15,3)))
add('RegimeSwitch: bull&lowvol long, highvol dip-buy',np.where(bull&lowv,1.0,np.where(highv,R(rsi(c,5)<25,5),0.0)))
base=[(nm,sg,lg) for nm,sg,lg in cands if lg=='cc' and 0.2<np.mean(sg>0)<0.9 and np.all(sg>=0)]
for nm,sg,lg in base: cands.append((nm+' [L/S always-in]',np.where(sg>0,1.0,-1.0),'cc'))
D=[]
for name,sig,leg in cands:
    x=pnl(sig,leg); row={'name':name}
    for k,(i,j) in IDX.items():
        cg,sh,dd,ex=met(x[i:j]); row.update({f'cagr_{k}':cg,f'sh_{k}':sh,f'dd_{k}':dd,f'exp_{k}':ex})
    yrs=[]
    for Y in range(2018,2024):
        a_,b_=sl(f'{Y}-04-01' if Y==2018 else f'{Y}-01-01',f'{Y}-12-31'); yrs.append(np.prod(1+x[a_:b_])-1)
    row['yrs_pos_tv']=float(np.mean(np.array(yrs)>0)); row['worst_yr_tv']=100*min(yrs)
    row['trades_tv']=int(np.sum(np.diff(np.r_[0,np.abs(sig[IDX['train'][0]:IDX['valid'][1]])>0])!=0)//2); D.append(row)
D=pd.DataFrame(D); D['tv_min']=D[['sh_train','sh_valid']].min(axis=1); D.to_csv('results/research2_all.csv',index=False)
N=len(D); print('candidates tried:',N)
sel=D[(D.cagr_train>0)&(D.cagr_valid>0)&(D.sh_train>0.5)&(D.sh_valid>0.5)&(D.exp_train>0.02)&(D.trades_tv>=25)&(D.yrs_pos_tv>=0.83)].sort_values('tv_min',ascending=False)
print('pass train+valid:',len(sel),'| of those test CAGR>0:',int((sel.cagr_test>0).sum()),'| base rate all:',round((D.cagr_test>0).mean(),2))
pd.set_option('display.width',260); pd.set_option('display.max_colwidth',55)
print(sel[['name','cagr_train','sh_train','cagr_valid','sh_valid','cagr_test','sh_test','dd_test','exp_train','trades_tv','yrs_pos_tv','worst_yr_tv']].round(2).head(25).to_string())
# --- ensemble: greedy diversified top-K chosen on train+valid
lookup={nm:(sg,lg) for nm,sg,lg in cands}; PX={nm:pnl(*lookup[nm]) for nm in sel.name}
tv=slice(IDX['train'][0],IDX['valid'][1]); chosen=[]
for nm in sel.name:
    if all(abs(np.corrcoef(PX[nm][tv],PX[o][tv])[0,1])<0.5 for o in chosen): chosen.append(nm)
    if len(chosen)==8: break
print('\nDiversified finalists (chosen on train+valid):'); [print(' -',x) for x in chosen]
port=np.mean([PX[x] for x in chosen],axis=0)
def line(x): return ' | '.join(f'{k}: {met(x[i:j])[0]:5.1f}% Sh {met(x[i:j])[1]:4.2f} DD {met(x[i:j])[2]:6.1f}%' for k,(i,j) in IDX.items())
vol=port[tv].std(ddof=1)*np.sqrt(252); print(f'\nEnsemble(8) 1x   : {line(port)}  (exposure-weighted vol {100*vol:.1f}%)')
print(f'Ensemble(8) 10%vol: {line(port*0.10/vol)}'); print(f'Buy&Hold         : {line(pnl(np.ones(n)))}')
# --- walk-forward: each year pick top5 by prior Sharpe (all earlier data), trade the year
oos=np.zeros(n); mask=np.zeros(n,bool); names=list(cands)
full={nm:pnl(sg,lg) for nm,sg,lg in cands}
y0=np.searchsorted(days.values,np.datetime64('2018-04-01'))
for Y in range(2021,2027):
    a,b=sl(f'{Y}-01-01',f'{Y}-12-31'); sc=[]
    for nm,x in full.items():
        h_=x[y0:a]; 
        if np.mean(h_!=0)<0.02 or (h_.std()==0): continue
        sc.append((h_.mean()/h_.std(),nm))
    top=[nm for _,nm in sorted(sc,reverse=True)[:5]]; oos[a:b]=np.mean([full[t][a:b] for t in top],axis=0); mask[a:b]=True
    print(f'WF {Y}: picked {top[:3]}... OOS year return {100*(np.prod(1+oos[a:b])-1):.1f}%')
print('Walk-forward OOS 2021-2026:',f'CAGR {met(oos[mask])[0]:.1f}% Sh {met(oos[mask])[1]:.2f} DD {met(oos[mask])[2]:.1f}%')
pd.to_pickle(dict(chosen=chosen,port=port,PX=PX,oos=oos,mask=mask),'results/research2_final.pkl')

# ===== Final: rule-based event-sleeve portfolio (exposure<10% among train+valid passers), full + regime-wise =====
ev=sel[sel.exp_train<0.10]; print('\nEVENT SLEEVES (rule: pass train+valid screens AND exposure<10%):',len(ev)); [print(' -',x) for x in ev.name]
evp=np.mean([PX[x] for x in ev.name],axis=0); volev=evp[tv].std(ddof=1)*np.sqrt(252)
PER4={**IDX,'full':sl('2018-04-01','2026-12-31')}
def lines(x,lab): print(f'{lab:28s}'+' | '.join(f'{k}: {met(x[i:j])[0]:5.1f}% Sh {met(x[i:j])[1]:4.2f} DD {met(x[i:j])[2]:6.1f}%' for k,(i,j) in PER4.items()))
lines(evp,'Event portfolio 1x'); lines(evp*3,'Event portfolio 3x'); lines(evp*5,'Event portfolio 5x'); lines(pnl(np.ones(n)),'Buy & Hold')
for nm in ev.name: lines(PX[nm],'  sleeve '+nm[:20])
sma200=sma(c,200); lab={'Trend':pd.Series(np.where(sma200.isna(),'NA',np.where(c>sma200,'Bull','Bear')),index=days),
 'Volatility':pd.Series(np.where(vix<15,'Low<15',np.where(vix<22,'Mid15-22','High>22')),index=days),
 'Momentum20d':pd.Series(np.where(c.pct_change(20)>0.03,'Up>3%',np.where(c.pct_change(20)<-0.03,'Down<-3%','Flat')),index=days),
 'Drawdown':pd.Series(np.where(c/c.cummax()-1<-0.10,'DD>10%','Near-high'),index=days)}
lab={k:v.shift(1).fillna('NA').astype(str).values for k,v in lab.items()}
bh=pnl(np.ones(n)); rows=[]
pair=np.mean([PX['VIX spike>0.12 h1 none'],PX['10d drop>0.025 h1 c>200']],axis=0)
print('\n(Post-hoc, test-informed) PAIR of sleeves positive in all 3 periods: VIX spike>12% h1 + 10d drop>2.5% in uptrend h1'); lines(pair,'Pair 1x'); lines(pair*5,'Pair 5x')
for ttl,evp in [('RULE-BASED 4-sleeve portfolio',evp),('PAIR',pair)]:
  print('\nREGIME-WISE:',ttl)
  for rs,lv in lab.items():
    for g in [x for x in sorted(set(lv)) if x!='NA']:
        o=[f'{rs:11s}{g:10s}']
        for k in ['train','valid','test']:
            i,j=IDX[k]; m=lv[i:j]==g; e=evp[i:j][m]; b=bh[i:j][m]
            if m.sum()<5: o.append(f'{k}: n={m.sum():3d} -'); continue
            o.append(f'{k}: n={m.sum():3d} Strat {100*e.mean()*252:5.1f}%/yr B&H {100*b.mean()*252:6.1f}%/yr')
        print(' | '.join(o))
import sys; sys.exit()
for rs,lv in lab.items():
    for g in [x for x in sorted(set(lv)) if x not in('NA','nan') and isinstance(x,str)]:
        o=[f'{rs:11s}{g:10s}']
        for k in ['train','valid','test']:
            i,j=IDX[k]; m=lv[i:j]==g; e=evp[i:j][m]; b=bh[i:j][m]
            o.append(f'{k}: n={m.sum():3d} Event {100*e.mean()*252:5.1f}%/yr (Sh {e.mean()/e.std(ddof=1)*np.sqrt(252) if e.std()>0 else 0:4.1f}) B&H {100*b.mean()*252:6.1f}%/yr')
        print(' | '.join(o))
pd.to_pickle(dict(evp=evp,names=list(ev.name)),'results/research2_event.pkl')
