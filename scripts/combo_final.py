"""Pre-specified portfolio of the two sleeves that were positive in every window (IBS lo0.1/hi0.8 frozen from train; panic pair frozen rules).
NO new parameters tuned: equal risk-capital split, then ONE ex-ante scaling rule (trailing-60d vol target 8% p.a., leverage cap 3x, scale known at prior close).
NOTE: test (2024-26) was already seen for both sleeves, so this is a risk-sizing improvement, not clean out-of-sample evidence."""
import numpy as np, pandas as pd
src = open('scripts/report_futures_ext.py').read().split("FAM = [")[0]; exec(src)
full_src = open('scripts/report_futures_ext.py').read()
exec(full_src.split('# ------------------------------------------------------------------ engine')[1].split('RES = {}')[0])
c=D['c']; sma=lambda x,w:x.rolling(w).mean()
ibs=(D['c']-D['l'])/(D['h']-D['l']).replace(0,np.nan)
def state(lo,hi):
    s=np.zeros(len(lo)); cur=0.
    for i,(a,b) in enumerate(zip(lo.fillna(False).values,hi.fillna(False).values)):
        if a: cur=1.
        elif b: cur=0.
        s[i]=cur
    return pd.Series(s,index=lo.index)
I=evaluate('IBS',lambda D,ls=False:state(ibs<0.1,ibs>0.8),{})
v=D['vix']; sp=((v/v.shift()-1)>0.12).astype(float); dr=(((c/c.shift(10)-1)<-0.025)&(c>sma(c,200))).astype(float)
P=evaluate('Pair',lambda D,ls=False:(sp+dr)/2,{})
B=evaluate('BH',None,{}) if False else None
ri,rp=I['ret'],P['ret']; comb=0.5*ri+0.5*rp
vol=pd.Series(comb).rolling(60).std().shift(1)*np.sqrt(252)
# vol of a mostly-flat book is tiny -> cap leverage; use unconditional ex-ante: scale = min(3, 0.08/vol)
sc=np.minimum(3,0.08/vol.replace(0,np.nan)).fillna(1.0).values
lev=comb*sc
bh=pnl(np.ones(len(c)),0.0001) if 'pnl' in globals() else None
def row(l,x):
    return f"| {l} | "+" | ".join("{CAGR:.1f}% / {Sharpe:.2f} / {MaxDD:.1f}%".format(**met(x[IDX[k][0]:IDX[k][1]])) for k in ['train','valid','test','full'])+" |"
print("| Series | Train 13-21 | Valid 22-23 | Test 24-26 | Full |\n|---|---|---|---|---|")
for l,x in [('Buy&Hold futures',bh),('IBS',ri),('Pair',rp),('IBS+Pair 50/50 (1x)',comb),('IBS+Pair vol-targeted 8%, cap 3x',lev)]: print(row(l,x))
print('avg leverage',np.nanmean(sc),'max',sc.max())
yrs=pd.Series(lev,index=c.index); print((yrs.groupby(yrs.index.year).apply(lambda s:(1+s).prod()-1)*100).round(1).to_dict())
x=lev[IDX['full'][0]:IDX['full'][1]]; rng=np.random.default_rng(0); bs=[]
for _ in range(2000):
    idx=(rng.integers(0,len(x)//20,len(x)//20)[:,None]*20+np.arange(20)).ravel()%len(x); y=x[idx]; bs.append(y.mean()/y.std(ddof=1)*np.sqrt(252))
print('block-bootstrap Sharpe 5/50/95%:',np.percentile(bs,[5,50,95]).round(2))

print("\n## Risk ladder (same sleeves, only the vol target / cap changes; costs scale with size)")
print("| Vol target / cap | Avg lev | Train | Valid | Test | Full | Worst year |\n|---|---|---|---|---|---|---|")
for tv,cap in [(0.08,3),(0.10,4),(0.12,5),(0.15,6)]:
    s=np.minimum(cap,tv/vol.replace(0,np.nan)).fillna(1.0).values; x=comb*s
    yy=pd.Series(x,index=c.index); w=(yy.groupby(yy.index.year).apply(lambda q:(1+q).prod()-1)*100).loc[2013:2026].min()
    print(f"| {tv*100:.0f}% / {cap}x | {np.nanmean(s):.1f}x | "+" | ".join("{CAGR:.1f}% / {Sharpe:.2f} / {MaxDD:.1f}%".format(**met(x[IDX[k][0]:IDX[k][1]])) for k in ['train','valid','test','full'])+f" | {w:.1f}% |")

print("\n## Drawdown budget 15%: lower targets, plus ONE pre-set brake (half size while equity is >7% below its peak)")
def brake(x):
    eq=1.;pk=1.;out=np.zeros(len(x))
    for i,r in enumerate(x):
        k=0.5 if eq/pk-1<-0.07 else 1.0
        out[i]=r*k; eq*=1+out[i]; pk=max(pk,eq)
    return out
print("| Setting | Train | Valid | Test | Full | Worst year |\n|---|---|---|---|---|---|")
for tv,cap,br in [(0.06,3,False),(0.07,3,False),(0.08,3,True),(0.10,4,True),(0.12,5,True)]:
    s=np.minimum(cap,tv/vol.replace(0,np.nan)).fillna(1.0).values; x=comb*s; x=brake(x) if br else x
    yy=pd.Series(x,index=c.index); w=(yy.groupby(yy.index.year).apply(lambda q:(1+q).prod()-1)*100).loc[2013:2026].min()
    print(f"| {tv*100:.0f}%/{cap}x{' +brake' if br else ''} | "+" | ".join("{CAGR:.1f}% / {Sharpe:.2f} / {MaxDD:.1f}%".format(**met(x[IDX[k][0]:IDX[k][1]])) for k in ['train','valid','test','full'])+f" | {w:.1f}% |")

print("\n## Diversified: IBS + Pair + H1(spread) + H2b(post-expiry), equal risk-capital, sized to the vol budget")
nr=pickle_load=pd.read_pickle('results/novel_res.pkl')
def get(h,p): return [r for r in nr[h] if r['params']==p][0]['ret']
h1=get('H1 spread-collapse long',{'w':120,'th':1.0,'h':1,'f':'none'}); h2b=get('H2b long in window after expiry',{'a':1,'L':5})
S4={'IBS':ri,'Pair':rp,'H1':h1,'H2b':h2b}
a,b=IDX['train'][0],IDX['full'][1]
print(pd.DataFrame(S4).iloc[a:b].corr().round(2))
c4=np.mean([ri,rp,h1,h2b],axis=0); v4=pd.Series(c4).rolling(60).std().shift(1)*np.sqrt(252)
print("| Vol target / cap | Avg lev | Train | Valid | Test | Full | Worst year |\n|---|---|---|---|---|---|---|")
for tv,cap in [(0.06,4),(0.07,4),(0.08,4),(0.10,5)]:
    s=np.minimum(cap,tv/v4.replace(0,np.nan)).fillna(1.0).values; x=c4*s
    yy=pd.Series(x,index=c.index); w=(yy.groupby(yy.index.year).apply(lambda q:(1+q).prod()-1)*100).loc[2013:2026].min()
    print(f"| {tv*100:.0f}%/{cap}x | {np.nanmean(s):.1f}x | "+" | ".join("{CAGR:.1f}% / {Sharpe:.2f} / {MaxDD:.1f}%".format(**met(x[IDX[k][0]:IDX[k][1]])) for k in ['train','valid','test','full'])+f" | {w:.1f}% |")
