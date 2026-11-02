import sys, json; sys.path.insert(0,'scripts')
from fast import *; from gates import build_gates
c=Ctx(); G=build_gates(c); P=c.periods(); n=len(c.days)
def ev(ng,dg,size=None):
    r,_=c.daily_returns(c.held(ng,dg,size)); return {k:metrics(r,*P[k],c.days) for k in ['train','valid','test','full']}, r
base,_=ev(G['ALWAYS'],G['ALWAYS'])
print('BASELINE ST(14,3) long-only :', {k:(round(v['CAGR'],1),round(v['DD'],1),round(v['Sharpe'],2)) for k,v in base.items()})
names=[k for k in G if k not in('ALWAYS','NEVER')]
# ---- greedy forward search using ONLY train (select) and valid (confirm). Test is never read here.
ng=G['ALWAYS'].copy(); dg=G['ALWAYS'].copy(); chosen=[('start','-')]
cur,_=ev(ng,dg); 
for step in range(1,7):
    best=None
    for leg in ['night','day']:
        for nm in names+(['NEVER'] if leg=='day' else []):
            nng,ndg=(ng&G[nm],dg) if leg=='night' else (ng,dg&G[nm]) if nm!='NEVER' else (ng,G['NEVER'])
            m,_=ev(nng,ndg)
            gt=m['train']['J']-cur['train']['J']; gv=m['valid']['J']-cur['valid']['J']
            if gt>0.5 and gv>-0.25 and m['train']['J']>(best[0] if best else -1e9):
                best=(m['train']['J'],leg,nm,nng,ndg,m)
    if not best: print('no further gate improves train J while holding valid'); break
    _,leg,nm,ng,dg,cur=best; chosen.append((leg,nm))
    print(f'step {step}: +{leg}:{nm:22s} train CAGR {cur["train"]["CAGR"]:5.1f} DD {cur["train"]["DD"]:6.1f} | valid CAGR {cur["valid"]["CAGR"]:5.1f} DD {cur["valid"]["DD"]:6.1f}')
print('\nSELECTED GATES:',chosen[1:])
m,r=ev(ng,dg)
print('\n           CAGR%   MaxDD%  Sharpe')
for k in ['train','valid','test','full']:
    print(f'{k:6s} base {base[k]["CAGR"]:6.1f} {base[k]["DD"]:7.1f} {base[k]["Sharpe"]:6.2f} | gated {m[k]["CAGR"]:6.1f} {m[k]["DD"]:7.1f} {m[k]["Sharpe"]:6.2f}')
json.dump({'chosen':chosen[1:]},open('results/selected_gates.json','w'))
np.save('results/sel_night.npy',ng); np.save('results/sel_day.npy',dg)
print('share of days night leg allowed: %.0f%%, day leg allowed: %.0f%%'%(ng.mean()*100,dg.mean()*100))
