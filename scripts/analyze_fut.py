import sys; sys.path.insert(0,'scripts')
import fast
from fast import *; from gates import build_gates
pd.set_option('display.width',220)
c=Ctx(); G=build_gates(c); days=c.days; hm=c.hm; A=G['ALWAYS']; N=G['NEVER']
fut=pd.read_csv('data/fut/nifty_fut.csv',parse_dates=['date','expiry']).drop_duplicates(['date','expiry'])
fut=fut[(fut.open>0)&(fut.close>0)]
print('futures rows',len(fut),'dates',fut.date.nunique(),'of',len(days),'| range',fut.date.min().date(),fut.date.max().date())
F=fut.set_index(['date','expiry']).sort_index()
vx=pd.read_csv(f'{DATA}/vix.csv',parse_dates=['date']).set_index('date')['close'].reindex(days).ffill(); jump=(vx.shift(1)/vx.shift(2)-1).values*100
h=c.held(~(jump>8.0),N)                                    # CURRENT strategy position (unchanged)
idx=np.flatnonzero(hm=='15:15'); di=c.day_id[idx]
sig=np.zeros(len(days)); sig[di]=h[idx]                    # size held tonight (0/1) per day
# --- spot measures per day
b=c.b.copy(); b['t']=b.index.strftime('%H:%M'); b['typ']=(b.open+b.high+b.low+b.close)/4
late=b[b.t.isin(['15:00','15:15'])].groupby('date')['typ'].mean().reindex(days).values     # ~ VWAP of the last half hour
open1515=b[b.t=='15:15'].groupby('date')['open'].first().reindex(days).values
open0915=b[b.t=='09:15'].groupby('date')['open'].first().reindex(days).values
n=len(days); R_a=np.full(n,np.nan); R_b=np.full(n,np.nan); R_f=np.full(n,np.nan); R_fo=np.full(n,np.nan); basis=np.full(n,np.nan); dte=np.full(n,np.nan)
miss=0
for i in range(n-1):
    t,u=days[i],days[i+1]
    R_a[i]=open0915[i+1]/open1515[i]-1
    R_b[i]=open0915[i+1]/late[i]-1
    try:
        ex=F.loc[t].index; K=ex[ex>t][0]                    # front contract that does NOT expire today
        ft=F.loc[(t,K)]; fu=F.loc[(u,K)]
        R_f[i]=fu.open/ft.close-1                           # real: sell at next open vs bought at last-half-hour VWAP
        R_fo[i]=fu.open/ft.open-0                            # placeholder (not used)
        basis[i]=(ft.close/late[i]-1)*100; dte[i]=(K-t).days
    except Exception: miss+=1
print('nights without a usable futures pair:',miss)
cal=np.r_[[(days[i+1]-days[i]).days for i in range(n-1)],1].astype(float)
roll=np.zeros(n); roll[c.day_id[idx[c.is_roll[idx]]]]=1
def pack(R,carry=False,interest=False):
    r=np.where(sig>0,sig*(np.nan_to_num(R)) - 2*0.00025*sig - 0.0005*roll*sig,0.0)
    if carry: r=r+np.where(sig>0,sig*0.047/365*cal,0.0)
    if interest: r=r+0.06/365*cal
    return r
P={'train':('2017-04-01','2021-12-31'),'valid':('2022-01-01','2023-12-31'),'test':('2024-01-01','2026-12-31'),'full':('2017-04-01','2026-12-31')}
def sp(a,b_): return (np.searchsorted(days,pd.Timestamp(a)),np.searchsorted(days,pd.Timestamp(b_),side='right'))
def line(name,r): return f'{name:62s} '+' | '.join(f'{k} {metrics(r,*sp(*P[k]),days)["CAGR"]:5.1f}/{metrics(r,*sp(*P[k]),days)["DD"]:6.1f}/{metrics(r,*sp(*P[k]),days)["Sharpe"]:4.2f}' for k in P)
print('\nformat CAGR%/MaxDD%/Sharpe   (same signals, same nights, costs 0.025%/side + roll)')
ref=c.daily_returns(h)[0]
print(line('REFERENCE: original fast engine (spot, +4.7% carry)',ref))
print(line('1. spot, 15:15 open -> 09:15 open, + synthetic carry',pack(R_a,True)))
print(line('2. spot, last-30-min price -> 09:15 open, + synthetic carry',pack(R_b,True)))
print(line('3. spot, last-30-min price -> 09:15 open, NO carry',pack(R_b,False)))
print(line('4. REAL FUTURES (NSE), last-30-min VWAP -> next open, real basis',pack(R_f,False)))
print(line('5. REAL FUTURES + 6% interest on idle capital (total-return view)',pack(R_f,False,True)))
print(line('6. spot version of 5 (spot, no carry, +6% interest)',pack(R_b,False,True)))
ok=(sig>0)&~np.isnan(R_f)
print('\nPER-NIGHT averages on held nights (bp = 0.01%):')
for k,(a,b_) in P.items():
    lo,hi=sp(a,b_); m=np.zeros(n,bool); m[lo:hi]=True; m&=ok
    print(f'  {k:6s} n={m.sum():4d} | spot 15:15open->09:15open {np.mean(R_a[m])*1e4:6.1f} | spot last30->open {np.mean(R_b[m])*1e4:6.1f} | FUTURES {np.mean(R_f[m])*1e4:6.1f} | futures minus spot {np.mean(R_f[m]-R_b[m])*1e4:5.2f}bp | win% fut {np.mean(R_f[m]>0)*100:.0f}')
print('\nPer-night basis (futures last-30-min price vs spot): mean premium %.3f%% ; avg days-to-expiry %.0f ; implied annualised carry paid by a LONG ~ %.1f%%'%(np.nanmean(basis[ok]),np.nanmean(dte[ok]),np.nanmean(basis[ok]/np.maximum(dte[ok],1))*365))
d=(R_f-R_b)[ok]; print('real basis decay per night vs spot-based: mean %.2f bp (the model credits +%.1f bp/night of carry)'%(d.mean()*1e4,0.047/365*1.4*1e4))
print('\nYEAR BY YEAR (strategy 4 real futures | strategy 2 spot+carry | strategy 5 futures+interest)')
for y in range(2017,2027):
    lo,hi=sp(f'{y}-01-01',f'{y}-12-31'); f=lambda r:(np.prod(1+r[lo:hi])-1)*100
    print(f'  {y}: {f(pack(R_f)):6.1f} | {f(pack(R_b,True)):6.1f} | {f(pack(R_f,False,True)):6.1f}')
rr=pack(R_f); nn=sig>0; g=R_f[nn&ok]*100
print(f'\nreal futures nights: {int((nn&ok).sum())}, win {np.mean(g>0)*100:.0f}%, avg {g.mean():.3f}%, worst night {g.min():.2f}% on {days[np.nanargmin(np.where(nn&ok,R_f,np.nan))].date()}, nights < -1%: {(g<-1).sum()}, < -2%: {(g<-2).sum()}')
fast.COST_SIDE=0.0005
print('DONE_ANALYSIS')
