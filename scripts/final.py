"""FROZEN SPEC (set before looking at 2024+):
 Overnight Trend (OT): Supertrend(14,3) on 15-min Nifty. At the close of the 15:00 bar, if green -> buy futures at the 15:15 open,
 size = min(1, 1.0% / (2 x ATR14_daily%)) using ATR known at the prior close; exit at next session 09:15 open.
 Conservative variant: exit at 09:30 open. Walk-forward grid: ST period {10,14,20} x mult {2.5,3,3.5}, pick by trailing-3y Sharpe."""
import sys; sys.path.insert(0,'scripts')
import btlib
from strat import *
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
b, d, f, bf = prep(end='2026-10-31')
hm=b.index.strftime('%H:%M').values; last=(hm=='15:00'); c=b['close'].values
tr=pd.Series(np.maximum.reduce([d.high-d.low,(d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs()]),index=d.index)
batr=((tr.ewm(alpha=1/14,adjust=False).mean()/d.close*100).shift(1)).reindex(b['date']).values

def extend(base,k):
    ext=np.zeros(len(b))
    for i in np.where(base>0)[0]:
        for j in range(1,k+1):
            if i+j<len(b): ext[i+j]=base[i]
    return np.maximum(base,ext)
def OT(n=14,m=3.0,r=1.0,k=2.0,delay=0):
    dirn=get_st(b,n,m)['dir'].values
    pos=np.where(last&(dirn==1),np.minimum(1.0,r/(k*batr)),0.0)
    return extend(pos,delay) if delay else pos
def BASE(n=14,m=3.0):
    dirn=get_st(b,n,m)['dir'].values
    return state_machine((dirn==1).astype(int),np.ones(len(b)),None)

P={'train 17-21':('2017-04-01','2021-12-31'),'valid 22-23':('2022-01-01','2023-12-31'),'test 24-26':('2024-01-01','2026-12-31'),
   'post-2022':('2022-01-01','2026-12-31'),'FULL':('2017-04-01','2026-12-31')}
def daily(net): return (1+net).groupby(net.index.normalize()).prod()-1
def m_(net,held=None):
    x=daily(net); eq=(1+x).cumprod(); yrs=(x.index[-1]-x.index[0]).days/365.25
    out={'CAGR%':(eq.iloc[-1]**(1/yrs)-1)*100,'MaxDD%':((eq/eq.cummax()-1).min())*100,'Sharpe':x.mean()/x.std()*np.sqrt(252),
         'Sharpe_ex6%':(x.mean()-0.06/252)/x.std()*np.sqrt(252)}
    if held is not None:
        h=held.loc[net.index]; out['trades/yr']=(h.diff().abs()>1e-9).sum()/2/yrs; out['avg|pos|']=h.abs().mean()
    return out
def table(strats,periods=P):
    rows={}
    for name,(net,held) in strats.items():
        for p,(s,e) in periods.items():
            rows[(name,p)]=m_(net.loc[s:e],held)
    return pd.DataFrame(rows).T.round(2)
def trades(net,held):
    h=held.values; n=net.values; out=[]; i=0
    while i<len(h):
        if h[i]!=0 and (i==0 or h[i-1]==0):
            j=i
            while j+1<len(h) and h[j+1]!=0: j+=1
            out.append((net.index[i], n[i:j+2].sum())); i=j+1
        else: i+=1
    return pd.Series(dict(out))
S={}
S['BASELINE ST(14,3) long-only']=pnl(b,BASE())
S['OT  (exit 09:15, brief protocol)']=pnl(b,OT())
S['OT-C (exit 09:30, conservative)']=pnl(b,OT(delay=1))
S['OT risk-dial k=1.5 (exit 09:15)']=pnl(b,OT(k=1.5))
out=[]
def say(x=''): print(x); out.append(str(x))
say('=== 1. HEADLINE (strategy vs baseline; same engine, costs, carry) ==='); say(table(S).to_string())
say('\n=== 2. TRADE STATISTICS (full period) ===')
for nm in ['OT  (exit 09:15, brief protocol)','OT-C (exit 09:30, conservative)','OT risk-dial k=1.5 (exit 09:15)']:
    net,held=S[nm]; t=trades(net,held)*100
    say(f'{nm}: trades {len(t)}, win rate {(t>0).mean()*100:.0f}%, avg {t.mean():.3f}%, avg win {t[t>0].mean():.3f}%, avg loss {t[t<0].mean():.3f}%, worst {t.min():.2f}%, trades losing >1%: {(t<-1).sum()}, >0.75%: {(t<-0.75).sum()}')
    for p in ['test 24-26']:
        s,e=P[p]; tt=t.loc[s:e]; say(f'    {p}: trades {len(tt)}, win {(tt>0).mean()*100:.0f}%, worst {tt.min():.2f}% on {tt.idxmin().date()}, losing >1%: {(tt<-1).sum()}')
say('\n=== 3. YEAR BY YEAR net return % ===')
yy=pd.DataFrame({k:((1+v[0]).groupby(v[0].index.year).prod()-1)*100 for k,v in S.items()}).round(1); say(yy.to_string())
say('\ncorrelation of daily returns OT vs BASELINE: %.2f'%daily(S['OT  (exit 09:15, brief protocol)'][0]).corr(daily(S['BASELINE ST(14,3) long-only'][0])))

say('\n=== 4. SENSITIVITY: Supertrend period x multiplier, OT sizing k=2 (Sharpe | MaxDD%) by period ===')
rows=[]
for n in [10,14,20]:
    for m in [2.5,3.0,3.5]:
        net,held=pnl(b,OT(n,m)); r=[f'{n}', f'{m}']
        for p in ['train 17-21','valid 22-23','test 24-26']:
            s,e=P[p]; z=m_(net.loc[s:e]); r+= [round(z['Sharpe'],2), round(z['MaxDD%'],1), round(z['CAGR%'],1)]
        rows.append(r)
cols=['ST_n','ST_mult']+[f'{p}_{x}' for p in ['train','valid','test'] for x in ['Sh','DD','CAGR']]
say(pd.DataFrame(rows,columns=cols).to_string(index=False))
say('\n--- sensitivity: sizing stress multiplier k (risk r=1%) ---')
rows=[]
for k in [1.0,1.5,2.0,3.0]:
    net,held=pnl(b,OT(k=k)); r=[k]
    for p in ['train 17-21','valid 22-23','test 24-26']:
        s,e=P[p]; z=m_(net.loc[s:e]); r+=[round(z['CAGR%'],1),round(z['MaxDD%'],1),round(z['Sharpe'],2)]
    t=trades(net,held)*100; r+=[round(t.min(),2),int((t<-1).sum())]
    rows.append(r)
say(pd.DataFrame(rows,columns=['k','tr_CAGR','tr_DD','tr_Sh','va_CAGR','va_DD','va_Sh','te_CAGR','te_DD','te_Sh','worst_trade%','n>1%loss']).to_string(index=False))

say('\n=== 5. COST STRESS (full period, OT exit 09:15 / OT-C exit 09:30 / BASELINE) ===')
rows=[]
for mult in [1,2,3]:
    btlib.COST_SIDE=0.00025*mult
    a=m_(pnl(b,OT())[0]); c2=m_(pnl(b,OT(delay=1))[0]); bb=m_(pnl(b,BASE())[0])
    rows.append([f'{mult}x ({0.025*mult:.3f}%/side)',round(a['Sharpe'],2),round(a['CAGR%'],1),round(c2['Sharpe'],2),round(c2['CAGR%'],1),round(bb['Sharpe'],2),round(bb['CAGR%'],1)])
btlib.COST_SIDE=0.00025
say(pd.DataFrame(rows,columns=['cost','OT_Sh','OT_CAGR','OT-C_Sh','OT-C_CAGR','BASE_Sh','BASE_CAGR']).to_string(index=False))

say('\n=== 6. WALK-FORWARD: each year pick (ST n, mult) from 9-grid by trailing-3y Sharpe, apply next year ===')
grid=[(n,m) for n in [10,14,20] for m in [2.5,3.0,3.5]]
res={}
for lab,fn in [('OT',lambda n,m: pnl(b,OT(n,m))),('OT-C',lambda n,m: pnl(b,OT(n,m,delay=1))),('BASELINE',lambda n,m: pnl(b,BASE(n,m)))]:
    nets={g:fn(*g) for g in grid}; parts=[]; helds=[]; picks=[]
    for Y in range(2020,2027):
        best=max(grid,key=lambda g: m_(nets[g][0].loc[f'{Y-3}-01-01':f'{Y-1}-12-31'])['Sharpe'])
        parts.append(nets[best][0].loc[str(Y)]); helds.append(nets[best][1].loc[str(Y)]); picks.append((Y,best))
    net=pd.concat(parts); held=pd.concat(helds); res[lab]=(net,held)
    z=m_(net,held); say(f'{lab:9s} WF 2020-26: CAGR {z["CAGR%"]:.1f}%  MaxDD {z["MaxDD%"]:.1f}%  Sharpe {z["Sharpe"]:.2f}  (excess-6% {z["Sharpe_ex6%"]:.2f})  picks {picks}')
    zz=m_(net.loc['2024-01-01':]); say(f'           WF 2024-26 only: CAGR {zz["CAGR%"]:.1f}%  MaxDD {zz["MaxDD%"]:.1f}%  Sharpe {zz["Sharpe"]:.2f}')
open('results/final_output.txt','w').write('\n'.join(out))
