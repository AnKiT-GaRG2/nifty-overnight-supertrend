import sys; sys.path.insert(0,'scripts')
from btlib import *
import time
t=time.time()
b = load_15m(); print('bars',len(b), b.index.min(), b.index.max(), 'days', b.date.nunique(), 'bars/day', round(len(b)/b.date.nunique(),1), round(time.time()-t,1),'s')
b = b[b.index < '2024-01-01']            # EXPLORATION: no 2024+ data
st = supertrend(b,14,3.0)
want = (st['dir'].values==1).astype(int)
pos = state_machine(want, np.ones(len(b)), None)
net, held = pnl(b, pos)
print(report(net, held))
print('full 2017-23:', {k:round(v,2) for k,v in metrics(net,held).items()})
# no-carry sanity & buy&hold
bh = pnl(b, np.ones(len(b)))
print('buy&hold fut (incl carry)', {k:round(v,2) for k,v in metrics(bh[0],bh[1]).items()})
