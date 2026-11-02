import sys; sys.path.insert(0,'scripts')
from strat import *
from factors import build_flags
pd.set_option('display.width',250)
b, d, f, bf = prep(end='2026-10-31')
F=build_flags(b['date'].unique())
# intraday return: open 09:15 -> open 15:15 same day (what a 09:15 short/long would earn), in %
hm=b.index.strftime('%H:%M')
o09=b['open'][hm=='09:15']; o09.index=o09.index.normalize()
o15=b['open'][hm=='15:15']; o15.index=o15.index.normalize()
I=pd.DataFrame({'intraday':(o15/o09-1)*100}).dropna()
I['n_fast']=F.loc[I.index,['rupee_month','dollar_month','us10y_month','spx_month','crude_regime','crude_shock']].sum(axis=1)
for c in ['rupee_month','dollar_month','us10y_month','spx_month','crude_regime','crude_shock','vix_jump','won_weak','twd_weak','rupee_day']:
    I[c]=F.loc[I.index,c]
P={'train 17-21':('2017-04-01','2021-12-31'),'valid 22-23':('2022-01-01','2023-12-31'),'test 24-26':('2024-01-01','2026-12-31')}
print('mean INTRADAY return % (09:15 open -> 15:15 open), all days by period:',{p:round(I.loc[s:e].intraday.mean(),3) for p,(s,e) in P.items()})
rows=[]
for lab,m in [('n_fast>=1',I.n_fast>=1),('n_fast>=2',I.n_fast>=2),('n_fast>=3',I.n_fast>=3)]+[(c,I[c]) for c in ['rupee_month','dollar_month','us10y_month','spx_month','crude_regime','crude_shock','vix_jump','won_weak','twd_weak','rupee_day']]:
    r=[lab]
    for p,(s,e) in P.items():
        x=I.loc[s:e]; mm=m.loc[x.index].astype(bool); on=x[mm].intraday
        r+= [len(on), round(on.mean(),3) if len(on)>=8 else np.nan]
    rows.append(r)
print('mean intraday % on flagged days  (negative -> a short would earn; round-trip cost is ~0.05%)')
print(pd.DataFrame(rows,columns=['flag']+[f'{p[:5]}_{x}' for p in P for x in ['n','mean%']]).to_string(index=False))
