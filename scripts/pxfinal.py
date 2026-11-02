import sys, os; sys.path.insert(0,'scripts')
os.environ['PRICEONLY']='1'
from fast import *; from gates import build_gates
c=Ctx(); days=c.days; G=build_gates(c); A=G['ALWAYS']; N=G['NEVER']
d_=c.d; cl_=d_['close']; trr=pd.concat([d_.high-d_.low,(d_.high-cl_.shift()).abs(),(d_.low-cl_.shift()).abs()],axis=1).max(axis=1)
atrp_=trr.ewm(alpha=1/14,adjust=False).mean()/cl_*100; rng_=(d_.high-d_.low)/cl_*100; sh_=lambda x: x.shift(1).reindex(days)
for k in [1.5,2.0,2.5]: G[f'prev_range<{k}xATR']=(sh_(rng_)<k*sh_(atrp_)).fillna(True).values
for k in [1.2,1.8]: G[f'prev_range%<{k}']=(sh_(rng_)<k).fillna(True).values
for k in [10,20]: G[f'atr_jump5d<{k}%']=((sh_(atrp_)/atrp_.shift(6).reindex(days)-1)*100<k).fillna(True).values
G['prev_ret>-1.5%']=(sh_(cl_.pct_change()*100)>-1.5).fillna(True).values
PREF=('close>sma','sma50>sma200','adx>=','mom','dd252','rsi','atr%','rv10','prev_gap','prev_day_ret','prev_range','prev_ret','atr_jump')
names=[k for k in G if k.startswith(PREF)]
def sp(a,b): return (np.searchsorted(days,pd.Timestamp(a)),np.searchsorted(days,pd.Timestamp(b),side='right'))
PER={'train':('2017-04-01','2021-12-31'),'valid':('2022-01-01','2023-12-31'),'test':('2024-01-01','2026-12-31'),'full':('2017-04-01','2026-12-31'),'2021-26':('2021-01-01','2026-12-31')}
def M(r,k): return metrics(r,*sp(*PER[k]),days)
def fmt(r,ks=('train','valid','test','full')): return ' | '.join(f'{k} {M(r,k)["CAGR"]:5.1f}/{M(r,k)["DD"]:6.1f}/{M(r,k)["Sharpe"]:4.2f}' for k in ks)
base=c.daily_returns(c.held(A,A))[0]; night=c.daily_returns(c.held(A,N))[0]
rows=[]
for nm in names:
    r=c.daily_returns(c.held(G[nm],N))[0]; rows.append((M(r,'train')['J']+M(r,'valid')['J'],nm,r))
rows.sort(key=lambda x:-x[0])
print('CAGR/MaxDD/Sharpe   [repo data only, price-derived factors]')
print('BASELINE ST(14,3) long-only         ',fmt(base)); print('night-only Supertrend, no filter     ',fmt(night))
print('\nnight-only + ONE price gate, ranked on train+valid J:')
for sc,nm,r in rows[:8]: print(f'  {nm:24s}',fmt(r))
best=rows[0]; print('\nCHOSEN (train+valid only):',best[1]); r=best[2]
print('FINAL ',fmt(r,('train','valid','test','full','2021-26')))
print('BASE  ',fmt(base,('train','valid','test','full','2021-26')))
print('year by year (strategy | baseline):',' '.join(f'{y}:{(np.prod(1+r[sp(f"{y}-01-01",f"{y}-12-31")[0]:sp(f"{y}-01-01",f"{y}-12-31")[1]])-1)*100:.0f}|{(np.prod(1+base[sp(f"{y}-01-01",f"{y}-12-31")[0]:sp(f"{y}-01-01",f"{y}-12-31")[1]])-1)*100:.0f}' for y in range(2017,2027)))
# robustness of the neighbours: how many single gates beat baseline drawdown AND keep CAGR >= baseline-3 on test
ok=sum(1 for _,nm,rr in rows if M(rr,'test')['DD']>M(base,'test')['DD'] and M(rr,'test')['CAGR']>M(base,'test')['CAGR']); print(f'\nsingle price gates beating baseline on BOTH test CAGR and test DD: {ok} of {len(rows)}')
