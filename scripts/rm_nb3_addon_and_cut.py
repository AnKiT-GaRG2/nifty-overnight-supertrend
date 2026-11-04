import sys, json; sys.path.insert(0,'scripts')
exec(open('scripts/rm_wf_fac.py').read().split("wt = BASES")[0])
FACT.update({'NQS': ([1,2,3], lambda x: (prior(nq,5)*100 > x, 'S')), 'INRS': ([1,2,3], lambda x: (prior(usd,20)*100 < -x, 'S'))})
def scales(name, v):
    cond, role = FACT[name][1](v); cond = cond.reindex(days).fillna(False).astype(bool); s = pd.Series(np.where(cond, 0.5, 1.0), index=days); one = pd.Series(1.0, index=days)
    return (s, s) if role == 'B' else ((s, one) if role == 'L' else (one, s))
wt=(2.0,1.0); NB3=[('NQ',2),('MC3',15)]; BASE=apply(NB3,*wt)
POOL=['S1','T2L','O3','KRW','NQS','INRS']; FAM2={'S1':'cross','T2L':'trend','O3':'options','KRW':'emfx','NQS':'short','INRS':'short'}
STR={(n,v):apply(NB3+[(n,v)],*wt) for n in POOL for v in FACT[n][0]}
def window(net,a,z): ex=net[a:z]; return metrics_from(ex+INT[a:z],None,None,None,ex)
def pick(a,z):
    ref=window(BASE,a,z); best=None
    for n in POOL:
        grid=FACT[n][0]; met={v:window(STR[(n,v)],a,z) for v in grid}; lift={v:met[v]['Sharpe']-ref['Sharpe'] for v in grid}
        for v in (grid[1:-1] if len(grid)>=3 else grid):
            i=grid.index(v); nb=[grid[j] for j in (i-1,i+1) if 0<=j<len(grid)]
            if lift[v]>=0.05 and met[v]['MaxDD']>=ref['MaxDD']-1e-9 and np.mean([lift[x]>0 for x in nb])>=0.7:
                sc=np.mean([lift[v]]+[lift[x] for x in nb])
                if best is None or sc>best[0]: best=(sc,n,v)
    return [(best[1],best[2])] if best else []
folds=[];a0=pd.Timestamp('2020-04-01')
while a0<=pd.Timestamp('2026-10-31'):
    z0=min(a0+pd.DateOffset(months=6)-pd.Timedelta(days=1),pd.Timestamp('2026-10-31')); folds.append((a0,z0,a0-pd.DateOffset(years=3),a0-pd.Timedelta(days=1))); a0+=pd.DateOffset(months=6)
print('| OOS period | Add-on chosen on prior 3y |'); print('|---|---|'); P0=[];P1=[]
for a,z,t0,t1 in folds:
    sp=pick(t0,t1); print(f"| {a.date()}..{z.date()} | {sp if sp else 'none'} |"); P0.append(BASE[a:z]); P1.append((apply(NB3+sp,*wt) if sp else BASE)[a:z])
s0,s1=pd.concat(P0),pd.concat(P1)
def mm(n,sub=None):
    n=n if sub is None else n[sub[0]:sub[1]]; return metrics_from(n+INT.reindex(n.index),None,None,None,n)
fl=lambda m:f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
print('\n| Stitched OOS | 2020-04..2023-12 | 2024-01..2026-10 (desc.) | Whole OOS |'); print('|---|---|---|---|')
for lab,s in (('NB3 (no extra layer)',s0),('NB3 + walk-forward add-on',s1)): print(f"| {lab} | {fl(mm(s,('2020-04-01','2023-12-31')))} | {fl(mm(s,('2024-01-01','2026-10-31')))} | {fl(mm(s))} |")
m0,m1=mm(s0),mm(s1); print(f"\nVerdict: Sharpe {m1['Sharpe']:.2f} vs {m0['Sharpe']:.2f}; MaxDD {m1['MaxDD']:.1%} vs {m0['MaxDD']:.1%} -> {'EXTRA LAYER ADDS VALUE' if (m1['Sharpe']-m0['Sharpe']>=0.1 and m1['MaxDD']>=m0['MaxDD']-1e-9) else 'EXTRA LAYER DOES NOT ADD VALUE'}")
print('\n## Each add-on alone on NB3, descriptive (train / valid / test / full): CAGR/DD/Sharpe')
print('| Add-on | Train | Valid | Test | Full |'); print('|---|---|---|---|---|'); print('| NB3 | '+' | '.join(fl(metr(BASE,w)) for w in ('train','valid','test','full'))+' |')
for n in POOL:
    for v in FACT[n][0]: print(f"| +{n} {v} | "+' | '.join(fl(metr(STR[(n,v)],w)) for w in ('train','valid','test','full'))+' |')
# cut-fraction sensitivity
print('\n## Cut-fraction sensitivity for NQ and MC3 (both use the same fraction; 0.5 is the written convention); dev 2017-23 | valid | full')
for c in (0.0,0.25,0.5,0.75):
    def sc2(name,v,c=c):
        cond,role=FACT[name][1](v); cond=cond.reindex(days).fillna(False).astype(bool); return pd.Series(np.where(cond,c,1.0),index=days)
    net=wt[0]*sc2('NQ',2)*sc2('MC3',15)*L+wt[1]*Sh; print(f"   cut to {c}: dev {fl(metr(net,'dev'))} | valid {fl(metr(net,'valid'))} | full {fl(metr(net,'full'))}")
