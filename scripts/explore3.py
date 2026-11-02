import sys; sys.path.insert(0,'scripts')
from strat import *
pd.set_option('display.width',250)
b, d, f, bf = prep(end='2024-01-01')
hm = b.index.strftime('%H:%M').values
last = (hm=='15:00')                      # signal at close of the 15:00 bar -> fill at 15:15 open -> exit next 09:15 open
st = get_st(b,14,3.0); dirn = st['dir'].values
def show(name,pos):
    net,held=pnl(b,pos); rep=report(net,held); t,v=rep.loc['train 17-21'],rep.loc['valid 22-23']
    print(f"{name:55s} train {t['CAGR%']:6.1f}% DD {t['MaxDD%']:6.1f} Sh {t['Sharpe']:4.2f} | valid {v['CAGR%']:6.1f}% DD {v['MaxDD%']:6.1f} Sh {v['Sharpe']:4.2f} | tr/yr {t['trades/yr']:5.0f} |pos| {t['avg|pos|']:.2f}")
    return net,held
show('B  baseline ST long-only (reference)', state_machine((dirn==1).astype(int),np.ones(len(b)),None))
show('S1 overnight long EVERY night', np.where(last,1.0,0.0))
show('S2 overnight long when ST green', np.where(last&(dirn==1),1.0,0.0))
sma=bf['sma200'].values; pxp=bf['close'].values
show('S2b overnight long when ST green & >200DMA', np.where(last&(dirn==1)&(pxp>sma),1.0,0.0))
show('S2c overnight long when above 200DMA only', np.where(last&(pxp>sma),1.0,0.0))
# intraday short (hold 09:15 open -> 15:15 open) when previous-evening ST red
prev_red = pd.Series(dirn==-1,index=b.index).shift(1).fillna(False).values
first = (hm=='15:15')                     # decided at prior 15:15 bar close -> fills 09:15
intr = np.zeros(len(b)); 
dirn_s = pd.Series(dirn,index=b.index)
# pos for bars from 15:15 (prev day) .. 14:45 is -1 if ST red at prior day's final bar
dlast = dirn_s.groupby(b['date']).transform('last')            # ST dir at end of day
prior_dir = dlast.groupby(b['date']).first().shift(1)           # per-day, previous day's end dir
pd_map = b['date'].map(prior_dir).values                        # for bar of day D: prior day's closing dir
# bars of day D (09:15..15:00) held -> pos at bar t-1; simpler: build held directly then convert
held_short = np.where((pd_map==-1)&(hm!='15:15'),-1.0,0.0)      # bars 09:15..15:00 of day D held short
pos_short = np.r_[held_short[1:],0.0]                           # pos[t] = held[t+1]
show('S3 intraday short when prior-day ST red', pos_short)
S2=np.where(last&(dirn==1),1.0,0.0)
show('S4 S2 + S3 (overnight long + intraday short)', S2+pos_short)
# overnight long with trend sizing: ST-line distance at 15:00 (risk 1% / dist), cap 1
c=b['close'].values; dist=np.abs(c-st['line'].values)/c
for r in [0.0075,0.01,0.02]:
    show(f'S5 overnight when ST green, size=min(1,{r}/dist)', np.where(last&(dirn==1),np.minimum(1.0,r/np.maximum(dist,1e-4)),0.0))
