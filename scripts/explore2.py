import sys; sys.path.insert(0,'scripts')
from strat import *
pd.set_option('display.width',250)
b, d, f, bf = prep(end='2024-01-01')
# X3: where does the baseline's gross P&L come from? (bar 15:15 holds the overnight gap)
st = get_st(b,14,3.0); pos = state_machine((st['dir'].values==1).astype(int), np.ones(len(b)), None)
net, held = pnl(b,pos)
o=b['open'].values; ret=pd.Series(np.r_[o[1:]/o[:-1]-1,0],index=b.index); g=held*ret
seg = np.where(b.index.strftime('%H:%M')=='15:15','late+overnight (15:15 open -> next 09:15 open)','intraday 09:15-15:15')
tr = g.loc['2017-04-01':'2021-12-31']; s2=pd.Series(seg,index=b.index).loc[tr.index]
print('X3 baseline gross P&L by segment, train (sum of bar returns, %):'); print((tr.groupby(s2).sum()*100).round(1).to_string())
print('   unconditional Nifty open->open bars, train (sum %):'); u=ret.loc[tr.index]; print((u.groupby(s2).sum()*100).round(1).to_string())
# X1: risk level
print('\nX1 risk-per-trade level (ST 14,3, no other filter)')
rows=[]
for r in [0.005,0.0075,0.01,0.015,None]:
    rep,_,_=run(b,bf,ma=None,risk=r); t,v=rep.loc['train 17-21'],rep.loc['valid 22-23']
    rows.append([r,t['CAGR%'],t['MaxDD%'],t['Sharpe'],v['CAGR%'],v['MaxDD%'],v['Sharpe'],t['avg|pos|']])
print(pd.DataFrame(rows,columns=['risk','trCAGR','trDD','trSh','vaCAGR','vaDD','vaSh','avg|pos|']).round(2).to_string(index=False))
# X2: Supertrend sensitivity with sizing 0.75%
print('\nX2 Supertrend (period x multiplier) sensitivity, risk 0.75%: Sharpe train / valid, MaxDD train / valid')
for n in [7,10,14,20,30]:
    line=[]
    for m in [2.0,2.5,3.0,3.5,4.0,5.0]:
        rep,_,_=run(b,bf,ma=None,risk=0.0075,n=n,m=m); t,v=rep.loc['train 17-21'],rep.loc['valid 22-23']
        line.append(f"{t['Sharpe']:.2f}/{v['Sharpe']:.2f} ({t['MaxDD%']:.0f}/{v['MaxDD%']:.0f}) t{t['trades/yr']:.0f}")
    print(f'n={n:>2} ', ' | '.join(f'm={m}: {x}' for m,x in zip([2.0,2.5,3.0,3.5,4.0,5.0],line)))
