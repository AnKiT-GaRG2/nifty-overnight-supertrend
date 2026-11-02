"""Factor-aware backtests. Reaction = position-size multiplier from the factor monitor (flags known before each day).
NOTE: the document's thresholds were derived on the full 2016-2026 sample, so NO period here is clean out-of-sample for them."""
import sys; sys.path.insert(0,'scripts')
import btlib
from strat import *
from factors import build_flags, CAUTION
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
b, d, f, bf = prep(end='2026-10-31')
hm=b.index.strftime('%H:%M').values; last=(hm=='15:00'); c=b['close'].values
tr=pd.Series(np.maximum.reduce([d.high-d.low,(d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs()]),index=d.index)
batr=((tr.ewm(alpha=1/14,adjust=False).mean()/d.close*100).shift(1)).reindex(b['date']).values
dirn=get_st(b,14,3.0)['dir'].values
F=build_flags(b['date'].unique())
FB=F.reindex(b['date']).set_axis(b.index)                       # flags per bar (by the bar's date)
def mult_from(cols, step=0.25, veto_at=None, half_cols=None):
    n=FB[cols].sum(axis=1).values.astype(float)
    m=np.maximum(0.0,1-step*n)
    if veto_at: m=np.where(n>=veto_at,0.0,m)
    return m
OTpos=np.where(last&(dirn==1),np.minimum(1.0,1.0/(2*batr)),0.0)
BASEpos=state_machine((dirn==1).astype(int),np.ones(len(b)),None)
FAST=['rupee_month','dollar_month','us10y_month','spx_month','crude_regime','crude_shock']
V={}
V['OT (no factors)']=OTpos
V['OT + FAST flags (-25% per flag, veto >=3)']=OTpos*mult_from(FAST,0.25,3)
V['OT + ALL 8 doc flags (-25% per flag, veto >=3)']=OTpos*mult_from(CAUTION,0.25,3)
V['OT + crude only (half size in crude regime/shock)']=OTpos*np.where(FB['crude_regime'].values|FB['crude_shock'].values,0.5,1.0)
V['OT + US10Y only (half size) [train/valid-selected]']=OTpos*np.where(FB['us10y_month'].values,0.5,1.0)
V['OT + rupee/dollar/S&P/US10Y (veto if >=2)']=OTpos*np.where(FB[['rupee_month','dollar_month','spx_month','us10y_month']].sum(axis=1).values>=2,0.0,1.0)
B={}
B['BASELINE (no factors)']=BASEpos
B['BASELINE + FAST flags']=BASEpos*mult_from(FAST,0.25,3)
B['BASELINE + ALL 8 flags']=BASEpos*mult_from(CAUTION,0.25,3)
P={'train 17-21':('2017-04-01','2021-12-31'),'valid 22-23':('2022-01-01','2023-12-31'),'test 24-26':('2024-01-01','2026-12-31'),'FULL':('2017-04-01','2026-12-31')}
def daily(net): return (1+net).groupby(net.index.normalize()).prod()-1
def m_(net,held):
    x=daily(net); eq=(1+x).cumprod(); yrs=(x.index[-1]-x.index[0]).days/365.25
    return {'CAGR%':(eq.iloc[-1]**(1/yrs)-1)*100,'MaxDD%':((eq/eq.cummax()-1).min())*100,'Sharpe':x.mean()/x.std()*np.sqrt(252)}
rows=[]
for grp in (V,B):
    for name,pos in grp.items():
        net,held=pnl(b,pos)
        r={'strategy':name}
        for p,(s,e) in P.items():
            z=m_(net.loc[s:e],held); r[f'{p[:5]}_Sh']=round(z['Sharpe'],2); r[f'{p[:5]}_CAGR']=round(z['CAGR%'],1); r[f'{p[:5]}_DD']=round(z['MaxDD%'],1)
        rows.append(r)
R=pd.DataFrame(rows).set_index('strategy')
print(R[[c for c in R.columns if c.endswith('Sh')]].to_string()); print(); print(R[[c for c in R.columns if c.endswith('CAGR')]].to_string()); print(); print(R[[c for c in R.columns if c.endswith('DD')]].to_string())
R.to_csv('results/factor_backtest.csv')
# how often does the layer act?
print('\nshare of OT-green nights where multiplier < 1 / = 0:')
for nm in list(V)[1:]:
    on=V['OT (no factors)']>0; ratio=np.where(on,V[nm]/np.where(V['OT (no factors)']>0,V['OT (no factors)'],1),np.nan)
    print(f'  {nm:55s} <1: {np.nanmean(ratio[on]<0.999)*100:5.1f}%   =0: {np.nanmean(ratio[on]<1e-9)*100:5.1f}%')
# 2026 stress regime detail
print('\n2026 only (Iran-war year): net return %')
for nm in ['OT (no factors)','OT + FAST flags (-25% per flag, veto >=3)','OT + crude only (half size in crude regime/shock)']:
    net=pnl(b,V[nm])[0].loc['2026']; print(f'  {nm:55s} {((1+net).prod()-1)*100:6.2f}%')
net=pnl(b,B['BASELINE (no factors)'])[0].loc['2026']; print(f'  {"BASELINE":55s} {((1+net).prod()-1)*100:6.2f}%')
net=pnl(b,B['BASELINE + FAST flags'])[0].loc['2026']; print(f'  {"BASELINE + FAST flags":55s} {((1+net).prod()-1)*100:6.2f}%')
