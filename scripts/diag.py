import sys; sys.path.insert(0,'scripts')
from strat import *
from factors import build_flags
pd.set_option('display.width',250); pd.set_option('display.max_columns',40)
b, d, f, bf = prep(end='2026-10-31')
hm=b.index.strftime('%H:%M').values; last=(hm=='15:00')
dirn=get_st(b,14,3.0)['dir'].values
o=b['open'].values
ret_oo=np.r_[o[1:]/o[:-1]-1,0.0]*100                      # open[t]->open[t+1]
ovn=pd.Series(np.r_[ret_oo[1:],0.0],index=b.index)         # at the 15:00 bar: return of the NEXT bar (15:15 -> next 09:15)
F=build_flags(b['date'].unique())
sel=(last&(dirn==1))
N=pd.DataFrame({'ovn':ovn[sel].values,'date':b['date'][sel].values}).set_index('date')
N=N.join(F)
P={'train 17-21':('2017-04-01','2021-12-31'),'valid 22-23':('2022-01-01','2023-12-31'),'test 24-26':('2024-01-01','2026-12-31')}
print('OT-green nights:',len(N),' mean overnight %.3f%%'%N.ovn.mean())
rows=[]
for fl in [c for c in F.columns if c!='pe_value']:
    r=[fl]
    for p,(s,e) in P.items():
        x=N.loc[s:e]; on=x[x[fl]]['ovn']; off=x[~x[fl]]['ovn']
        if len(on)<8: r+=[len(on),np.nan,np.nan]; continue
        se=np.sqrt(on.var()/len(on)+off.var()/len(off)); r+=[len(on),round(on.mean()-off.mean(),3),round((on.mean()-off.mean())/se,1)]
    rows.append(r)
cols=['flag']+[f'{p[:5]}_{x}' for p in P for x in ['n_on','diff%','t']]
print('diff% = mean overnight return (flag ON) minus (flag OFF), on nights the strategy would hold. Negative = flag identifies worse nights.')
print(pd.DataFrame(rows,columns=cols).to_string(index=False))
# share of nights flagged
print('\nshare of green nights flagged (%):'); print((N[[c for c in F.columns if c!="pe_value"]].mean()*100).round(1).to_string())
