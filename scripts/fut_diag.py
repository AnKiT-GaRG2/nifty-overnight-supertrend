import sys; sys.path.insert(0,'scripts')
from fast import *
c=Ctx(); days=c.days; hm=c.hm; n=len(days)
fut=pd.read_csv('data/fut/nifty_fut.csv',parse_dates=['date','expiry']).drop_duplicates(['date','expiry']); fut=fut[(fut.open>0)&(fut.close>0)]
F=fut.set_index(['date','expiry']).sort_index()
b=c.b.copy(); b['t']=b.index.strftime('%H:%M'); b['typ']=(b.open+b.high+b.low+b.close)/4
late=b[b.t.isin(['15:00','15:15'])].groupby('date')['typ'].mean().reindex(days).values
o1515=b[b.t=='15:15'].groupby('date')['open'].first().reindex(days).values
o0915=b[b.t=='09:15'].groupby('date')['open'].first().reindex(days).values
cl=c.d['close'].reindex(days).values; op=c.d['open'].reindex(days).values
fn=np.full(n,np.nan); fd=np.full(n,np.nan); sn=np.full(n,np.nan); sd=np.full(n,np.nan); Rf=np.full(n,np.nan)
for i in range(n-1):
    t,u=days[i],days[i+1]
    try:
        ex=F.loc[t].index; K=ex[ex>t][0]; ft=F.loc[(t,K)]; fu=F.loc[(u,K)]
        fn[i]=fu.open/ft.close-1; fd[i+1]=fu.close/fu.open-1; Rf[i]=fn[i]
    except Exception: pass
    sn[i]=o0915[i+1]/late[i]-1; sd[i+1]=late[i+1]/o0915[i+1]-1
def per(a,b_): return np.searchsorted(days,pd.Timestamp(a)),np.searchsorted(days,pd.Timestamp(b_),side='right')
print('UNCONDITIONAL mean per day (bp), all days: night = last-30-min price -> next open ; day = open -> last-30-min price')
for k,(a,b_) in {'2017-21':('2017-04-01','2021-12-31'),'2022-23':('2022-01-01','2023-12-31'),'2024-26':('2024-01-01','2026-12-31'),'full':('2017-04-01','2026-12-31')}.items():
    lo,hi=per(a,b_); s=slice(lo,hi)
    print(f'  {k:8s} SPOT night {np.nanmean(sn[s])*1e4:6.1f} day {np.nanmean(sd[s])*1e4:6.1f} | FUTURES night {np.nanmean(fn[s])*1e4:6.1f} day {np.nanmean(fd[s])*1e4:6.1f} | futures-spot night {np.nanmean(fn[s]-sn[s])*1e4:6.1f} day {np.nanmean(fd[s]-sd[s])*1e4:6.1f}')
# ---- baseline & strategy with the night leg replaced by real futures (like-for-like entry at 15:15 open)
Rfa=(1+Rf)*(late/o1515)-1                              # futures return from ~15:15 to next open
def real_run(held,use_carry=False):
    ret=c.ret_oo.copy(); idx=np.flatnonzero(hm=='15:15'); dd=c.day_id[idx]
    rep=np.where(np.isnan(Rfa[dd]),ret[idx],Rfa[dd]); ret[idx]=rep
    prev=np.r_[0.0,held[:-1]]; cost=np.abs(held-prev)*COST_SIDE+np.abs(held)*COST_ROLL*c.is_roll
    net=held*ret-cost+(held*c.carry if use_carry else 0)
    return np.expm1(np.add.reduceat(np.log1p(net),c.starts))
G=None
A=np.ones(n,bool); N=np.zeros(n,bool)
vx=pd.read_csv(f'{DATA}/vix.csv',parse_dates=['date']).set_index('date')['close'].reindex(days).ffill(); jump=(vx.shift(1)/vx.shift(2)-1).values*100
H={'BASELINE Supertrend (14,3) long-only':c.held(A,A),'CURRENT overnight Supertrend + panic filter':c.held(~(jump>8),N),'night-only Supertrend, no filter':c.held(A,N),'buy&hold long (always)':c.green_prev*0+np.where(True,1.0,0)}
H['buy&hold long (always)']=np.ones(len(hm))
P={'train':('2017-04-01','2021-12-31'),'valid':('2022-01-01','2023-12-31'),'test':('2024-01-01','2026-12-31'),'full':('2017-04-01','2026-12-31')}
print('\nREAL-FUTURES night leg, spot day leg, NO synthetic carry   (CAGR/MaxDD/Sharpe)')
for nm,h in H.items():
    r=real_run(h); sp_=c.daily_returns(h)[0]
    print(f'{nm:46s} REAL '+' | '.join(f'{k} {metrics(r,*per(*P[k]),days)["CAGR"]:5.1f}/{metrics(r,*per(*P[k]),days)["DD"]:6.1f}/{metrics(r,*per(*P[k]),days)["Sharpe"]:4.2f}' for k in ['valid','test','full'])+f' || spot-model full {metrics(sp_,*per(*P["full"]),days)["CAGR"]:.1f}/{metrics(sp_,*per(*P["full"]),days)["DD"]:.1f}')
