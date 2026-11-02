import sys, numpy as np, pandas as pd
D=sys.argv[1]
nf = pd.read_csv(f'{D}/nifty.csv',parse_dates=['date']).set_index('date')
sp = pd.read_csv(f'{D}/spx.csv',parse_dates=['date']).set_index('date')['close'].pct_change().mul(100).dropna()
t = pd.DataFrame({'gap':(nf.open/nf.close.shift(1)-1)*100,'intraday':(nf.close/nf.open-1)*100}).dropna()
t['total']=t.gap+t.intraday
s = pd.merge_asof(t.reset_index(), sp.rename('spx').reset_index(), on='date', allow_exact_matches=False).dropna().set_index('date')
s = s.loc['2017-01-01':]
print('days',len(s),'| all-days avg  gap %.3f  open->close %.3f  total %.3f'%(s.gap.mean(),s.intraday.mean(),s.total.mean()))
for lab,m in [('S&P >= +1%',s.spx>=1),('S&P <= -1%',s.spx<=-1),('S&P <= -2%',s.spx<=-2)]:
    e=s[m]; print('%-11s n=%3d  gap %.3f | open->close %.3f (t=%.2f) | total %.3f | intraday down %.0f%%'%(lab,len(e),e.gap.mean(),e.intraday.mean(),(e.intraday.mean()-s.intraday.mean())/(s.intraday.std()/np.sqrt(len(e))),e.total.mean(),(e.intraday<0).mean()*100))
print('corr(spx, gap)=%.2f  corr(spx, open->close)=%.2f'%(s.spx.corr(s.gap), s.spx.corr(s.intraday)))
for p,(a,b) in {'2017-21':('2017','2021'),'2022-23':('2022','2023'),'2024-26':('2024','2026')}.items():
    x=s.loc[a:b]; print(p,'corr gap %.2f  open->close %.2f'%(x.spx.corr(x.gap),x.spx.corr(x.intraday)))
