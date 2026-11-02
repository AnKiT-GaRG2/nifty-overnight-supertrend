import sys; sys.path.insert(0,'scripts')
from strat import *
b, d, f, bf = prep(end='2024-01-01')        # EXPLORATION: no 2024+ bars
ideas = [
 ('E0 baseline long-only ST(14,3)',                dict(ma=None)),
 ('E1 + risk sizing 0.75%',                        dict(ma=None, risk=0.0075)),
 ('E2 + long only above 200DMA',                   dict(ma='sma200')),
 ('E3 E2 + risk sizing',                           dict(ma='sma200', risk=0.0075)),
 ('E4 symmetric shorts (no filter)',               dict(ma=None, shorts='all', risk=0.0075)),
 ('E5 shorts only below 200DMA + sizing',          dict(ma='sma200', shorts='bear', risk=0.0075)),
 ('E6 E3 + ADX>=20 filter',                        dict(ma='sma200', risk=0.0075, adx_thr=20)),
 ('E7 E3 + ADX>=25 filter',                        dict(ma='sma200', risk=0.0075, adx_thr=25)),
 ('E8 E3 + VIX>22 halves size',                    dict(ma='sma200', risk=0.0075, vix_cut=22)),
 ('E9 E5 + VIX>22 halves size',                    dict(ma='sma200', shorts='bear', risk=0.0075, vix_cut=22)),
]
rows=[]
for name,kw in ideas:
    rep,_,_ = run(b,bf,**kw)
    t,v = rep.loc['train 17-21'], rep.loc['valid 22-23']
    rows.append([name,t['CAGR%'],t['MaxDD%'],t['Sharpe'],v['CAGR%'],v['MaxDD%'],v['Sharpe'],t['trades/yr'],t['avg|pos|']])
out=pd.DataFrame(rows,columns=['idea','trCAGR','trDD','trSh','vaCAGR','vaDD','vaSh','trades/yr','avg|pos|']).round(2)
pd.set_option('display.width',250); pd.set_option('display.max_colwidth',45)
print(out.to_string(index=False))
