"""NEW strategy (separate file; current strategy untouched): Gap-Reversal Day Sleeve.
Signal after the 09:15 bar closes (gap = 09:15 open / previous close - 1). Entry at 09:30 open, exit at 15:15 open (no overnight).
fade: long after gap-down <= -g%, short after gap-up >= +g%.  follow: the opposite.  Sides: long-only or long+short."""
import sys, itertools; sys.path.insert(0,'scripts')
import fast
from fast import *; from gates import build_gates
c=Ctx(); G=build_gates(c); days=c.days; hm=c.hm; A=G['ALWAYS']; N=G['NEVER']
vx=pd.read_csv(f'{DATA}/vix.csv',parse_dates=['date']).set_index('date')['close'].reindex(days).ffill()
jump=(vx.shift(1)/vx.shift(2)-1).values*100
d=c.d; gap=((d['open']/d['close'].shift(1)-1)*100).reindex(days).values
def sp(a,b): return (np.searchsorted(days,pd.Timestamp(a)),np.searchsorted(days,pd.Timestamp(b),side='right'))
PER={'train':('2017-04-01','2021-12-31'),'valid':('2022-01-01','2023-12-31'),'test':('2024-01-01','2026-12-31'),'full':('2017-04-01','2026-12-31')}
day_bar=(hm>='09:30')&(hm<='15:00')
def sleeve(g,mode,sides):
    s=np.zeros(len(days))
    dn=gap<=-g; up=gap>=g
    if mode=='fade': s[dn]=1.0; 
    else: s[up]=1.0
    if sides=='both':
        if mode=='fade': s[up]=-1.0
        else: s[dn]=-1.0
    s[np.isnan(gap)]=0
    return np.where(day_bar,s[c.day_id],0.0)
def run(h): r,_=c.daily_returns(h); return r
def M(r,k): m=metrics(r,*sp(*PER[k]),days); return m
night=c.held(~(jump>8.0),N)                       # the CURRENT strategy's position (unchanged)
r_night=run(night)
print('CURRENT strategy (reference):',' | '.join(f'{k} {M(r_night,k)["CAGR"]:.1f}/{M(r_night,k)["DD"]:.1f}/{M(r_night,k)["Sharpe"]:.2f}' for k in PER))
rows=[]
for g,mode,sides in itertools.product([0.2,0.3,0.4,0.5,0.7,1.0],['fade','follow'],['long','both']):
    h=sleeve(g,mode,sides); r=run(h)
    if (h!=0).sum()==0: continue
    tr,va,te=M(r,'train'),M(r,'valid'),M(r,'test')
    rows.append((g,mode,sides,tr['J']+va['J'],tr,va,te,r,h))
rows.sort(key=lambda x:-x[3])
print('\nSTANDALONE day sleeve, ranked by train+valid J (CAGR-|DD|). format CAGR/DD/Sharpe')
for g,mode,sides,sc,tr,va,te,r,h in rows[:12]:
    print(f'g={g:<4} {mode:6s} {sides:5s} | train {tr["CAGR"]:5.1f}/{tr["DD"]:6.1f}/{tr["Sharpe"]:5.2f} | valid {va["CAGR"]:5.1f}/{va["DD"]:6.1f}/{va["Sharpe"]:5.2f} | test {te["CAGR"]:5.1f}/{te["DD"]:6.1f}/{te["Sharpe"]:5.2f}')
print('\nall 24 configs: how many have positive CAGR in train / valid / test:',sum(x[4]['CAGR']>0 for x in rows),sum(x[5]['CAGR']>0 for x in rows),sum(x[6]['CAGR']>0 for x in rows),'of',len(rows))
# ---- pre-committed choice: best train+valid config ONLY (test never used to choose)
g,mode,sides,sc,tr,va,te,rs,hs=rows[0]
print(f'\nCHOSEN on train+valid: g={g} {mode} {sides}')
comb=run(night+hs)
print('COMBINED = current night strategy + day sleeve (positions add; never above 1x since they do not overlap):')
for k in PER:
    a,b,cc=M(r_night,k),M(rs,k),M(comb,k)
    print(f'{k:6s} current {a["CAGR"]:5.1f}/{a["DD"]:6.1f}/{a["Sharpe"]:5.2f} | sleeve {b["CAGR"]:5.1f}/{b["DD"]:6.1f}/{b["Sharpe"]:5.2f} | COMBINED {cc["CAGR"]:5.1f}/{cc["DD"]:6.1f}/{cc["Sharpe"]:5.2f}')
print('correlation of daily returns, sleeve vs current: %.2f'%np.corrcoef(rs,r_night)[0,1])
print('days traded per year: %.0f, win rate %.0f%%'%(((hs!=0)&(hm=='09:30')).sum()/(len(days)/252), (np.array([np.prod(1+run(hs)[i:i+1])-1 for i in range(len(days))])[np.array([ (hs[c.starts[i]:c.starts[i+1] if i+1<len(c.starts) else None]!=0).any() for i in range(len(days))])]>0).mean()*100))
fast.COST_SIDE=0.0005; r2=run(night+hs); print('combined with 2x costs: full %.1f/%.1f/%.2f vs current at 2x %.1f/%.1f/%.2f'%(M(r2,'full')['CAGR'],M(r2,'full')['DD'],M(r2,'full')['Sharpe'],M(run(night),'full')['CAGR'],M(run(night),'full')['DD'],M(run(night),'full')['Sharpe']))
fast.COST_SIDE=0.00025
print('DONE')
