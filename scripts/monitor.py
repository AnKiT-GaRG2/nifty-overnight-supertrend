"""Live factor monitor. Usage: python3 scripts/monitor.py  -> prints every factor, its reading, threshold and state, and the suggested size multiplier.
Fresh Yahoo data is pulled into data/live (never touches the backtest inputs). FII / P/E are the document's own latest figures (manual, not verified)."""
import os, sys, time, requests, numpy as np, pandas as pd
sys.path.insert(0,'scripts')
from btlib import load_15m, supertrend, DATA
LIVE=os.path.join(DATA,'live'); os.makedirs(LIVE,exist_ok=True)
syms={'usdinr':'INR=X','dxy':'DX-Y.NYB','us10y':'^TNX','spx':'^GSPC','brent':'BZ=F','vix':'^INDIAVIX','krw':'KRW=X','twd':'TWD=X','jpy':'JPY=X','gold':'GC=F'}
p1=int(pd.Timestamp('2026-06-01').timestamp()); p2=int(pd.Timestamp.now().timestamp())+86400*2
S={}
for k,s in syms.items():
    j=requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}',params={'period1':p1,'period2':p2,'interval':'1d'},headers={'User-Agent':'Mozilla/5.0'},timeout=30).json()['chart']['result'][0]
    S[k]=pd.Series(j['indicators']['quote'][0]['close'],index=pd.to_datetime(j['timestamp'],unit='s').normalize()).dropna(); time.sleep(0.5)
last=lambda k:(S[k].index[-1].date(), S[k].iloc[-1])
rows=[]
def add(name,reading,thr,on,note=''): rows.append((name,reading,thr,'CAUTION' if on else 'ok',note))
x=S['usdinr']; v=(x.iloc[-1]/x.iloc[-22]-1)*100; add('Rupee (USD/INR) 21d chg',f'{v:+.2f}%  (spot {x.iloc[-1]:.2f}, {x.index[-1].date()})','> +2%',v>2)
x=S['dxy'];    v=(x.iloc[-1]/x.iloc[-22]-1)*100; add('Dollar index 21d chg',f'{v:+.2f}%  ({x.index[-1].date()})','> +1.5%',v>1.5)
x=S['us10y'];  v=x.iloc[-1]-x.iloc[-22];          add('US 10Y yield 21d chg',f'{v:+.2f} pt  (level {x.iloc[-1]:.2f}%)','> +0.25 pt',v>0.25)
x=S['spx'];    v=(x.iloc[-1]/x.iloc[-22]-1)*100; add('S&P 500 21d return',f'{v:+.2f}%  ({x.index[-1].date()})','< -2%',v<-2)
x=S['brent'];  m21=x.iloc[-21:].mean(); c5=(x.iloc[-1]/x.iloc[-6]-1)*100
add('Brent 21d average',f'${m21:.1f}  (last ${x.iloc[-1]:.1f}, {x.index[-1].date()})','> $100',m21>100,'war-type regime per doc')
add('Brent 5d change (shock)',f'{c5:+.1f}%','>= +10% and > $90',(c5>=10)&(x.iloc[-1]>90))
x=S['vix'];    v=(x.iloc[-1]/x.iloc[-2]-1)*100; add('India VIX 1d jump',f'{v:+.1f}%  (level {x.iloc[-1]:.1f}, {x.index[-1].date()})','> +20%',v>20,'level >25 = panic, not seen')
x=S['krw'];    v=(x.iloc[-1]/x.iloc[-2]-1)*100; add('Korean won 1d move (weaker = +)',f'{v:+.2f}%','> +0.7%',v>0.7,'link weak/decoupled in 2026')
x=S['twd'];    v=(x.iloc[-1]/x.iloc[-2]-1)*100; add('Taiwan dollar 1d move',f'{v:+.2f}%','> +0.5%',v>0.5,'link almost gone in 2026')
add('FII sold over past 12 months','~Rs 4.5 lakh cr (per document, to 23 Oct 2026)','> Rs 2 lakh cr sold',True,'manual input; not in free data')
add('Nifty P/E','~19 (per document, 23 Oct 2026)','> 23',False,'manual input')
add('Month seasonality (Jan/Feb weak)',f'month = {pd.Timestamp.now().month}','Jan, Feb',pd.Timestamp.now().month in (1,2),'tilt flag, not in the score')
# ignored-by-document factors (shown for completeness)
x=S['gold']; v=(x.iloc[-1]/x.iloc[-2]-1)*100; ig=[('Gold 1d',f'{v:+.2f}%'),('Yen 1d',f'{(S["jpy"].iloc[-1]/S["jpy"].iloc[-2]-1)*100:+.2f}%')]
df=pd.DataFrame(rows,columns=['factor','reading','caution threshold','state','note']); pd.set_option('display.width',250); pd.set_option('display.max_colwidth',60)
print(df.to_string(index=False))
fast=[0,1,2,3,4,5]; nfast=(df.loc[:5,'state']=='CAUTION').sum()
mult=0.0 if nfast>=3 else max(0,1-0.25*nfast)
print(f'\nFAST flags on: {nfast} of 6 -> factor-layer multiplier {mult:.2f}  (OT backtest says: leave it at 1.00, see report)')
print('Ignored by the document (no effect): ',ig)
b=load_15m(); st=supertrend(b,14,3.0)
print(f"\nOT signal state at last bar {b.index[-1]}: Supertrend {'GREEN (would hold overnight)' if st['dir'].iloc[-1]==1 else 'RED (flat)'}; last close {b['close'].iloc[-1]:.1f}, line {st['line'].iloc[-1]:.1f}")
