import requests, pandas as pd, sys, time
out = sys.argv[1]
syms = {'nifty':'^NSEI','vix':'^INDIAVIX','brent':'BZ=F','wti':'CL=F','usdinr':'INR=X','spx':'^GSPC','us10y':'^TNX','dxy':'DX-Y.NYB','gold':'GC=F','nasdaq':'^IXIC'}
p1 = int(pd.Timestamp('2016-10-01').timestamp()); p2 = int(pd.Timestamp('2026-11-02').timestamp())
for k,s in syms.items():
    r = requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}', params={'period1':p1,'period2':p2,'interval':'1d'}, headers={'User-Agent':'Mozilla/5.0'}, timeout=30)
    j = r.json()['chart']['result'][0]
    q = j['indicators']['quote'][0]
    df = pd.DataFrame({'date':pd.to_datetime(j['timestamp'],unit='s').normalize(),'open':q['open'],'close':q['close']}).dropna()
    df.to_csv(f'{out}/{k}.csv',index=False)
    print(k, len(df), df.date.min().date(), df.date.max().date(), round(df.close.iloc[-1],2))
    time.sleep(1)
