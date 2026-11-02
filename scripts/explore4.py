import sys; sys.path.insert(0,'scripts')
from strat import *
pd.set_option('display.width',250)
b, d, f, bf = prep(end='2024-01-01')
hm = b.index.strftime('%H:%M').values
o=b['open'].values; ret=pd.Series(np.r_[o[1:]/o[:-1]-1,0],index=b.index)*100
tr = ret.loc['2017-04-01':'2021-12-31']; va = ret.loc['2022-01-01':'2023-12-31']
t = pd.DataFrame({'train_mean_bp':tr.groupby(tr.index.strftime('%H:%M')).mean()*100,'valid_mean_bp':va.groupby(va.index.strftime('%H:%M')).mean()*100}).round(2)
print('Mean open->next-open return per 15-min bar, basis points (bar 15:15 = overnight):'); print(t.T.to_string())
last=(hm=='15:00'); st=get_st(b,14,3.0); dirn=st['dir'].values
c=b['close'].values; dist=np.abs(c-st['line'].values)/c
def show(name,pos):
    net,held=pnl(b,pos); rep=report(net,held); a,v=rep.loc['train 17-21'],rep.loc['valid 22-23']
    print(f"{name:60s} train {a['CAGR%']:5.1f}% DD {a['MaxDD%']:6.1f} Sh {a['Sharpe']:4.2f} | valid {v['CAGR%']:5.1f}% DD {v['MaxDD%']:6.1f} Sh {v['Sharpe']:4.2f} | tr/yr {a['trades/yr']:4.0f}")
    return net
sz=np.minimum(1.0,0.0075/np.maximum(dist,1e-4))
base=np.where(last&(dirn==1),sz,0.0)
print()
show('S5 overnight, exit at 09:15 open (original)', base)
# exit later: hold also through bar 09:15 (exit 09:30 open) / 09:30 (exit 09:45 open)
first1=(hm=='15:15'); first2=first1|(hm=='09:15')
def hold_extra(k):
    pos=base.copy(); sig=pd.Series(base,index=b.index)
    # pos[t]!=0 at 15:00 bar. extend: pos at the 15:15 bar (decided at its close) = same size -> held in 09:15 bar
    s=pd.Series(base,index=b.index); 
    ext=np.zeros(len(b)); idx=np.where(base>0)[0]
    for i in idx:
        for j in range(1,k+1):
            if i+j<len(b): ext[i+j]=base[i]
    return np.maximum(base,ext)
show('S5 exit 1 bar later (09:30 open)', hold_extra(1))
show('S5 exit 2 bars later (09:45 open)', hold_extra(2))
show('S5 exit 4 bars later (10:15 open)', hold_extra(4))
# entry 1 bar earlier (14:45 signal, fill 15:00 open)
ent=np.zeros(len(b)); idx=np.where(base>0)[0]
for i in idx: ent[i-1]=base[i]
show('S5 enter 1 bar earlier (15:00 open)', np.maximum(base,ent))
print('\nYear by year, S5 (net %):'); net=pnl(b,base)[0]
y=((1+net).groupby(net.index.year).prod()-1)*100; print(y.round(1).to_string())
print('\nWorst 8 overnight S5 trades (net %):'); 
tt=net[net!=0]; print((tt.nsmallest(8)*100).round(2).to_string())
