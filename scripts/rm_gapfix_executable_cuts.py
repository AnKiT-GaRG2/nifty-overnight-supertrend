import sys; sys.path.insert(0,'scripts')
exec(open('scripts/rm_wf_fac.py').read().split("wt = BASES")[0])
import rm_final
from rm_engine import LOT, CAPITAL
fut = pd.read_csv(f'{ROOT}/data/fut/nifty_fut.csv', parse_dates=['date','expiry']).drop_duplicates(['date','expiry']); fut = fut[(fut.open>0)&(fut.close>0)].set_index(['date','expiry'])
Ea,_ = rm_final.anchored_engine(E, fut)
tt, ss = S.A2(100); shortsig = np.where(tt==-1,-1,0).astype(np.int8); lt, ls = S.baseline()
def split_leg(En, tdir, tsz):
    R = En.run(tdir, tsz, cost='floor'); fb = np.where(En.first_b)[0]; lb = np.where(En.last_b)[0]
    net = pd.Series(R.net_d, index=En.days); gap = np.zeros(len(fb))
    for i in range(1, len(fb)):
        pos_before = R.posl[lb[i-1]]; gap[i] = pos_before*LOT*(En.fo[fb[i]] - En.prev[fb[i]])/CAPITAL
    gap = pd.Series(gap, index=En.days); return net, gap, net-gap
def cell(x,y,c=0.25):
    a=trig('NQ',x); b=trig('MC3',y); return pd.Series(np.where(a,c,1.0),index=days)*pd.Series(np.where(b,c,1.0),index=days)
def trig(name,v):
    cond,_=FACT[name][1](v); return cond.reindex(days).fillna(False).astype(bool)
ens = sum(cell(x,y) for x in (1,2,3) for y in (10,15,20))/9.0; nb3 = cell(2,15)
def lin(s,L,G,I): return s*L                       # old method: scale the whole day incl. the overnight gap
def exe(s,L,G,I): return s.shift(1).fillna(1.0)*G + s*I   # executable: previous day's size carries the gap; the new size starts at the open
fl=lambda m:f"{m['CAGR']:.1%} / {m['MaxDD']:.1%} / {m['Sharpe']:.2f}"
for pname,En in (('real-anchored',Ea),('synthetic',E)):
    L,G,I = split_leg(En, lt, ls); Sh = pd.Series(En.run(shortsig, ss, cost='floor').net_d, index=days)
    wl,ws=1.912,0.956
    print(f'\n### {pname} path, floor costs  (CAGR / MaxDD / Sharpe)'); print('| System | Train | Valid | Test | Full |'); print('|---|---|---|---|---|')
    rows={'Plain long-only baseline':L,'Same weights, no cuts':wl*L+ws*Sh,
      'NB3 old (scale whole day, incl. gap)':2.0*lin(nb3,L,G,I)+Sh,'NB3 executable (cut after the gap)':2.0*exe(nb3,L,G,I)+Sh,
      'Frozen old (scale whole day, incl. gap)':wl*lin(ens,L,G,I)+ws*Sh,'Frozen executable (cut after the gap)':wl*exe(ens,L,G,I)+ws*Sh}
    for n,net in rows.items(): print(f'| {n} | '+' | '.join(fl(metr(net,w)) for w in ('train','valid','test','full'))+' |')
    g=G[A:Z] if False else G['2017-04-01':'2026-10-31']; print(f'   share of long-leg P&L that is overnight gap (full): {G.sum()/L.sum():.0%}')

# ---- size each executable variant to dev max DD = -14% (anchored path), then report all windows
print('\n\n=== Sized to 2017-23 max drawdown of -14% (real-anchored, floor costs; executable timing) ===')
L,G,I = split_leg(Ea, lt, ls); Sh = pd.Series(Ea.run(shortsig, ss, cost='floor').net_d, index=days)
cands={'Long 1.0 only (plain baseline)':L,'Leveraged long+short, no cuts (weights 2:1)':2.0*L+Sh,'Leveraged long+short + Nasdaq/US10Y ensemble cut (executable)':2.0*exe(ens,L,G,I)+Sh,'Leveraged long only, no cuts (2.0)':2.0*L}
for n,net in cands.items():
    lo,hi=0.2,1.5
    for _ in range(40):
        s=(lo+hi)/2
        if metr(net*s,'dev')['MaxDD'] < -0.14: hi=s
        else: lo=s
    s=lo; print(f"{n}: scale {s:.2f} -> dev {fl(metr(net*s,'dev'))} | valid {fl(metr(net*s,'valid'))} | test {fl(metr(net*s,'test'))} | full {fl(metr(net*s,'full'))}")
