"""Clean real-futures test. P&L = real NSE Nifty futures open-to-open (same contract, front month not expiring today).
Signals use only information up to the previous close (spot); fills at the futures open. Costs 0.025%/side, 0.05% roll on last trading day of month."""
import sys; sys.path.insert(0,'scripts')
from fast import *; from btlib import supertrend, adx
c=Ctx(); days=c.days; n=len(days); hm=c.hm
fut=pd.read_csv('data/fut/nifty_fut.csv',parse_dates=['date','expiry']).drop_duplicates(['date','expiry']); fut=fut[(fut.open>0)&(fut.close>0)]
F=fut.set_index(['date','expiry']).sort_index()
r_oo=np.full(n,np.nan)                                   # return of holding from futures open of day i to open of day i+1
for i in range(n-1):
    t,u=days[i],days[i+1]
    try:
        ex=F.loc[t].index; K=ex[ex>t][0]; r_oo[i]=F.loc[(u,K)].open/F.loc[(t,K)].open-1
    except Exception: pass
r_oo=np.nan_to_num(r_oo)
d=c.d; cl=d['close'].reindex(days)
st15=supertrend(c.b,14,3.0)['dir'].values
idx_last=np.flatnonzero(hm=='15:15'); st_close=np.zeros(n); st_close[c.day_id[idx_last]]=st15[idx_last]      # 15m Supertrend dir at the day's close
dd=pd.DataFrame({'high':d.high,'low':d.low,'close':d.close}).reindex(days)
def daily_st(nn,m):
    h,l,cc=dd.high.values,dd.low.values,dd.close.values; pc=np.r_[cc[0],cc[:-1]]
    tr=np.maximum.reduce([h-l,np.abs(h-pc),np.abs(l-pc)]); atr=pd.Series(tr).ewm(alpha=1/nn,adjust=False).mean().values
    hl2=(h+l)/2; ub=hl2+m*atr; lb=hl2-m*atr; fu=ub.copy(); fl=lb.copy(); di=np.ones(len(cc))
    for i in range(1,len(cc)):
        fu[i]=ub[i] if (ub[i]<fu[i-1] or cc[i-1]>fu[i-1]) else fu[i-1]; fl[i]=lb[i] if (lb[i]>fl[i-1] or cc[i-1]<fl[i-1]) else fl[i-1]
        di[i]=1 if (di[i-1]==-1 and cc[i]>fu[i-1]) else (-1 if (di[i-1]==1 and cc[i]<fl[i-1]) else di[i-1])
    return di
sma200=cl.rolling(200).mean().values
vx=pd.read_csv(f'{DATA}/vix.csv',parse_dates=['date']).set_index('date')['close'].reindex(days).ffill().values
dates=pd.Series(days); lastday=dates.groupby(dates.dt.to_period('M')).transform('max').values; is_last=(days.values==lastday)
def run(sig,interest=False):
    pos=np.r_[0.0,sig[:-1]]                                  # signal known at close of i-1 -> held during day i (from open i)... shift so pos[i] earns r_oo[i]
    pos=sig                                                  # sig[i] decided at close of day i, earns r_oo[i+1-1]: fill at open of i+1
    held=np.r_[0.0,pos[:-1]]                                 # held[j] = decision at close of j-1, earns open_j -> open_j+1
    ret=held*np.r_[0.0,r_oo[1:]]*0                           # placeholder
    ret=np.zeros(n); ret[1:]=held[1:]*r_oo[1:]               # holding during day j starts at open_j
    prev=np.r_[0.0,held[:-1]]; cost=np.abs(held-prev)*COST_SIDE+np.abs(held)*COST_ROLL*is_last
    out=ret-cost
    if interest: out=out+0.06/365*np.r_[1,[(days[i]-days[i-1]).days for i in range(1,n)]]
    return out
P={'2017-21':('2017-04-01','2021-12-31'),'2022-23':('2022-01-01','2023-12-31'),'2024-26':('2024-01-01','2026-12-31'),'FULL':('2017-04-01','2026-12-31')}
def sp(a,b): return np.searchsorted(days,pd.Timestamp(a)),np.searchsorted(days,pd.Timestamp(b),side='right')
def show(name,r):
    print(f'{name:56s} '+' | '.join(f'{k} {metrics(r,*sp(*P[k]),days)["CAGR"]:5.1f}/{metrics(r,*sp(*P[k]),days)["DD"]:6.1f}/{metrics(r,*sp(*P[k]),days)["Sharpe"]:4.2f}' for k in P))
g=(st_close==1).astype(float); s2=np.where(st_close==1,1.0,-1.0); s2[st_close==0]=0
dst=daily_st(10,3.0); 
print('REAL NSE FUTURES, open-to-open, pure futures P&L (no interest, no synthetic carry). CAGR/MaxDD/Sharpe')
show('Buy & hold futures (always long)',run(np.ones(n)))
show('Supertrend(14,3) 15m state at close, long-only (baseline proxy)',run(g))
show('Supertrend(14,3) 15m state at close, long/short',run(s2))
show('Daily Supertrend(10,3), long-only',run((dst==1).astype(float)))
show('Daily Supertrend(10,3), long/short',run(dst.astype(float)))
show('Spot above 200-day average, long-only',run((cl.values>sma200).astype(float)))
show('Spot above 200DMA long / below flat + VIX<25',run(((cl.values>sma200)&(vx<25)).astype(float)))
show('Supertrend(14,3) long-only & VIX<22',run(((st_close==1)&(vx<22)).astype(float)))
print('\nSame, plus 6% interest on idle capital (total-return view):')
show('Buy & hold futures + interest',run(np.ones(n),True))
show('Supertrend(14,3) long-only + interest',run(g,True))
show('Spot above 200DMA long-only + interest',run((cl.values>sma200).astype(float),True))
show('Cash only (6%)',run(np.zeros(n),True))
