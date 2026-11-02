import sys; sys.path.insert(0,'scripts')
from strat import *
pd.set_option('display.width',250)
b, d, f, bf = prep(end='2024-01-01')
hm = b.index.strftime('%H:%M').values; last=(hm=='15:00')
st=get_st(b,14,3.0); dirn=st['dir'].values; c=b['close'].values
# daily ATR% (14, Wilder) known at previous close
tr=pd.Series(np.maximum.reduce([d.high-d.low,(d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs()]),index=d.index)
atrp=(tr.ewm(alpha=1/14,adjust=False).mean()/d.close*100).shift(1)
batr=atrp.reindex(b['date']).values
vix=bf['vix'].values
def extend(base,k):
    ext=np.zeros(len(b)); 
    for i in np.where(base>0)[0]:
        for j in range(1,k+1):
            if i+j<len(b): ext[i+j]=base[i]
    return np.maximum(base,ext)
def stats(name,base,k=0):
    pos=extend(base,k) if k else base
    net,held=pnl(b,pos); rep=report(net,held); a,v=rep.loc['train 17-21'],rep.loc['valid 22-23']
    tt=net[net!=0]; worst=tt.min()*100; nbad=(tt<-0.01).sum()
    print(f"{name:52s} train {a['CAGR%']:5.1f}% DD {a['MaxDD%']:6.1f} Sh {a['Sharpe']:4.2f} | valid {v['CAGR%']:5.1f}% DD {v['MaxDD%']:6.1f} Sh {v['Sharpe']:4.2f} | worst trade {worst:5.2f}% #loss>1% {nbad}")
green=last&(dirn==1)
dist=np.abs(c-st['line'].values)/c
print('--- sizing for overnight-when-green (exit 09:15 open)')
stats('fixed 1.0 exposure', np.where(green,1.0,0.0))
stats('ST-line distance, r=0.75%', np.where(green,np.minimum(1,0.0075/np.maximum(dist,1e-4)),0.0))
for r,m in [(0.01,2.0),(0.01,3.0),(0.01,1.5),(0.0075,2.0),(0.005,2.0)]:
    stats(f'daily-ATR: min(1, r={r:.4f}/(m={m}*ATR%))', np.where(green,np.minimum(1,r*100/(m*batr)),0.0))
for r in [0.01,0.0075]:
    stats(f'VIX-based: min(1, r={r:.4f}/(2*VIX/15.9%))', np.where(green,np.minimum(1,r*100/(2*vix/15.9)),0.0))
print('--- same, conservative exit one bar later (09:30 open)')
stats('fixed 1.0 exposure', np.where(green,1.0,0.0),1)
stats('daily-ATR r=1.0% m=2', np.where(green,np.minimum(1,1.0/(2*batr)),0.0),1)
stats('daily-ATR r=1.0% m=3', np.where(green,np.minimum(1,1.0/(3*batr)),0.0),1)
stats('ST-line distance r=0.75%', np.where(green,np.minimum(1,0.0075/np.maximum(dist,1e-4)),0.0),1)
print('--- second signal: also hold overnight if oversold (RSI2<10 prior day) in uptrend (>200DMA) with ST red')
os_=(bf['rsi2'].values<10)&(bf['close'].values>bf['sma200'].values)
size=np.minimum(1,1.0/(2*batr))
stats('S2+MR: green OR oversold-uptrend', np.where(last&((dirn==1)|os_),size,0.0))
stats('MR only: oversold-uptrend', np.where(last&os_,size,0.0))
print('--- stricter trend for the overnight hold')
stats('green & ADX>=20', np.where(green&(bf["adx"].values>=20),size,0.0))
stats('green & >200DMA', np.where(green&(bf["close"].values>bf["sma200"].values),size,0.0))
stats('green & VIX<25', np.where(green&(vix<25),size,0.0))
