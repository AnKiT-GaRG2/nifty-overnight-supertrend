import sys, numpy as np, pandas as pd
D=sys.argv[1]
ld=lambda n: pd.read_csv(f'{D}/{n}.csv',parse_dates=['date']).set_index('date')['close']
nf, br, usd, vix = ld('nifty'), ld('brent'), ld('usdinr'), ld('vix')
# monthly path 2025-10 -> 2026-10
m = pd.DataFrame({'nifty':nf.resample('ME').last(),'brent':br.resample('ME').last(),'usdinr':usd.resample('ME').last(),'vix':vix.resample('ME').mean()})
print(m.loc['2025-09':].round(1).to_string())
# daily, 2026 only, tradable lag
n = nf.pct_change().dropna()*100; b = br.pct_change().dropna()*100
bl = pd.merge_asof(n.rename('nifty').reset_index(), b.rename('brent').reset_index(), on='date', allow_exact_matches=False).dropna().set_index('date')
for lab,(s,e) in {'2026':('2026-01-01','2026-12-31'),'2017-25':('2017-01-01','2025-12-31')}.items():
    x=bl.loc[s:e]; up=x[x.brent>=3]
    print(lab,'corr prev-day brent vs nifty',round(x.nifty.corr(x.brent),2),'| brent>=3% days',len(up),'avg nifty next',round(up.nifty.mean(),3),'vs all',round(x.nifty.mean(),3))
# multi-day: Nifty return over next 5 sessions after a 5-day Brent surge >=10%
b5 = br.pct_change(5)*100; n5f = nf.pct_change(5).shift(-5)*100
d = pd.concat([b5.rename('b5'), n5f.rename('n5f')],axis=1).dropna()
d = d.reindex(nf.index).dropna()
for lab,cond in [('Brent +10% in 5d',d.b5>=10),('Brent -10% in 5d',d.b5<=-10)]:
    e=d[cond]; print(lab,'episodes(days)',len(e),'avg next-5d Nifty',round(e.n5f.mean(),2),'vs all',round(d.n5f.mean(),2))
# Brent level regimes
lv = pd.concat([br.rename('brent'), nf.pct_change().mul(100).rename('nifty')],axis=1).dropna()
lv['reg']=pd.cut(lv.brent,[0,60,80,100,200],labels=['<60','60-80','80-100','>100'])
print(lv.groupby('reg',observed=True)['nifty'].agg(['size','mean','std']).round(3).to_string())
