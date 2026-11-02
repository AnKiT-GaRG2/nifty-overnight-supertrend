import requests, pandas as pd, sys, time
out=sys.argv[1]
syms={'krw':'KRW=X','twd':'TWD=X','jpy':'JPY=X','cny':'CNY=X','banknifty':'^NSEBANK'}
p1=int(pd.Timestamp('2016-10-01').timestamp()); p2=int(pd.Timestamp('2026-11-04').timestamp())
for k,s in syms.items():
    j=requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}',params={'period1':p1,'period2':p2,'interval':'1d'},headers={'User-Agent':'Mozilla/5.0'},timeout=30).json()['chart']['result'][0]
    q=j['indicators']['quote'][0]
    df=pd.DataFrame({'date':pd.to_datetime(j['timestamp'],unit='s').normalize(),'open':q['open'],'close':q['close']}).dropna()
    df.to_csv(f'{out}/{k}.csv',index=False); print(k,len(df),df.date.min().date(),df.date.max().date()); time.sleep(1)
