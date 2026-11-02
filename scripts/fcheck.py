import sys; sys.path.insert(0,'scripts')
from fast import *
import time
c=Ctx(); t=time.time()
ones=np.ones(len(c.days),bool)
h=c.held(ones,ones); r,net=c.daily_returns(h)
P=c.periods()
for k in ['train','valid','test','full']:
    m=metrics(r,*P[k],c.days); print(k,{a:round(v,2) for a,v in m.items()})
print('eval time',round(time.time()-t,2),'s; days',len(c.days))
t=time.time()
for _ in range(100): c.daily_returns(c.held(ones,ones))
print('per eval ms',round((time.time()-t)*10,1))
