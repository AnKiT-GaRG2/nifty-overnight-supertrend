"""(pre-2017 variant) Download NSE daily F&O bhavcopy for every Nifty trading day; keep only NIFTY index futures rows. Resumable."""
import sys, io, os, time, zipfile, threading
import requests, pandas as pd
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,'scripts')
OUT='data/fut/banknifty_fut.csv'; DAYS=list(pd.bdate_range('2007-06-01','2026-11-02'))   # weekdays; holidays simply fail
H={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
done=set(pd.read_csv(OUT,parse_dates=['date'])['date'].dt.strftime('%Y-%m-%d')) if os.path.exists(OUT) else set()
tried_fail=set(); lock=threading.Lock(); rows=[]; cnt=[0]
def urls(d):
    old=f'https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{d:%Y}/{d:%b}'.upper().replace(f'{d:%b}'.upper(),f'{d:%b}'.upper())+f'/fo{d:%d}{d:%b}{d:%Y}bhav.csv.zip'
    old=f'https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{d:%Y}/{d:%b}'.upper()
    old=f'https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{d:%Y}/{d.strftime("%b").upper()}/fo{d:%d}{d.strftime("%b").upper()}{d:%Y}bhav.csv.zip'
    new=f'https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip'
    return [new,old] if d>=pd.Timestamp('2024-07-08') else [old,new]
def parse(z):
    df=pd.read_csv(io.BytesIO(zipfile.ZipFile(io.BytesIO(z)).read(zipfile.ZipFile(io.BytesIO(z)).namelist()[0])),low_memory=False)
    if 'INSTRUMENT' in df.columns:
        x=df[(df.INSTRUMENT=='FUTIDX')&(df.SYMBOL=='BANKNIFTY')]
        return pd.DataFrame({'expiry':pd.to_datetime(x.EXPIRY_DT,format='%d-%b-%Y'),'open':x.OPEN,'high':x.HIGH,'low':x.LOW,'close':x.CLOSE,'settle':x.SETTLE_PR,'last':float('nan'),'volume':x.CONTRACTS,'oi':x.OPEN_INT})
    x=df[(df.FinInstrmTp=='IDF')&(df.TckrSymb=='BANKNIFTY')]
    return pd.DataFrame({'expiry':pd.to_datetime(x.XpryDt),'open':x.OpnPric,'high':x.HghPric,'low':x.LwPric,'close':x.ClsPric,'settle':x.SttlmPric,'last':x.LastPric,'volume':x.TtlTradgVol,'oi':x.OpnIntrst})
def get(d):
    if d.strftime('%Y-%m-%d') in done: return
    for u in urls(d):
        for attempt in range(3):
            try:
                r=requests.get(u,headers=H,timeout=40)
                if r.status_code==200 and len(r.content)>1000:
                    p=parse(r.content); p.insert(0,'date',d)
                    with lock: rows.append(p); cnt[0]+=1
                    return
                if r.status_code in (403,429): time.sleep(5*(attempt+1)); continue
                break
            except Exception as e: time.sleep(2)
    with lock: tried_fail.add(d.strftime('%Y-%m-%d'))
def flush():
    global rows
    with lock:
        if rows:
            new=pd.concat(rows); rows=[]
            new.to_csv(OUT,mode='a',header=not os.path.exists(OUT),index=False)
t=time.time(); todo=[d for d in DAYS if d.strftime('%Y-%m-%d') not in done]
print('days to fetch',len(todo),flush=True)
with ThreadPoolExecutor(8) as ex:
    for i in range(0,len(todo),120):
        list(ex.map(get,todo[i:i+120])); flush()
        print(f'{i+120}/{len(todo)} fetched {cnt[0]} failed {len(tried_fail)}  {time.time()-t:.0f}s',flush=True)
open('data/fut/failed_days_banknifty.txt','w').write('\n'.join(sorted(tried_fail)))
print('DONE_BANK',flush=True)
