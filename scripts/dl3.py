import requests, pandas as pd, sys, time
out=sys.argv[1]
syms={'copper':'HG=F','aluminium':'ALI=F','natgas':'NG=F','silver':'SI=F','wheat':'ZW=F','sugar':'SB=F','cotton':'CT=F','soy':'ZS=F','platinum':'PL=F',
 'nikkei':'^N225','hangseng':'^HSI','shanghai':'000001.SS','kospi':'^KS11','dax':'^GDAXI','ftse':'^FTSE','usvix':'^VIX','us5y':'^FVX','us30y':'^TYX','hyg':'HYG','eem':'EEM','ewy':'EWY','ewt':'EWT','inda':'INDA','fxi':'FXI','btc':'BTC-USD','soxx':'^SOX','russell':'^RUT',
 'nifty_it':'^CNXIT','nifty_fmcg':'^CNXFMCG','nifty_auto':'^CNXAUTO','nifty_metal':'^CNXMETAL','nifty_pharma':'^CNXPHARMA','nifty_realty':'^CNXREALTY','nifty_energy':'^CNXENERGY','nifty_psubank':'^CNXPSUBANK','nifty_midcap':'^CNXMIDCAP','nifty_smallcap':'^CNXSC','nifty_next50':'^NSMIDCP',
 'hdfcbank':'HDFCBANK.NS','icicibank':'ICICIBANK.NS','reliance':'RELIANCE.NS','infy':'INFY.NS','tcs':'TCS.NS','itc':'ITC.NS','sbin':'SBIN.NS','lt':'LT.NS','bhartiartl':'BHARTIARTL.NS'}
p1=int(pd.Timestamp('2016-06-01').timestamp()); p2=int(pd.Timestamp('2026-11-04').timestamp()); ok=[]
for k,s in syms.items():
    try:
        r=requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}',params={'period1':p1,'period2':p2,'interval':'1d'},headers={'User-Agent':'Mozilla/5.0'},timeout=30)
        j=r.json()['chart']['result'][0]; q=j['indicators']['quote'][0]
        df=pd.DataFrame({'date':pd.to_datetime(j['timestamp'],unit='s').normalize(),'close':q['close']}).dropna()
        if len(df)<1500: print('SHORT',k,len(df)); 
        df.to_csv(f'{out}/{k}.csv',index=False); ok.append(k); print(k,len(df),df.date.min().date(),df.date.max().date())
    except Exception as e: print('FAIL',k,s,str(e)[:60])
    time.sleep(0.4)
