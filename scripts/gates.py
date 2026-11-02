"""Gate library: each gate is a boolean array over Nifty trading days; True = factor allows holding. Every feature is known BEFORE the day starts."""
import numpy as np, pandas as pd
from btlib import DATA, adx, rsi
from factors import _asof

def build_gates(c):
    days=c.days; d=c.d; G={}
    L=lambda n: pd.read_csv(f'{DATA}/{n}.csv',parse_dates=['date']).set_index('date')['close'].astype(float)
    def add(name, s):                                       # NaN -> allow (warm-up)
        a=pd.Series(s,index=days) if not isinstance(s,pd.Series) else s.reindex(days)
        G[name]=a.fillna(True).astype(bool).values
    sh=lambda s: s.shift(1).reindex(days)                   # Nifty-calendar feature known at previous close
    cl=d['close']
    # ---- price trend / momentum
    for n in [20,50,100,200]: add(f'close>sma{n}', sh(cl)>sh(cl.rolling(n).mean()))
    add('sma50>sma200', sh(cl.rolling(50).mean())>sh(cl.rolling(200).mean()))
    for t in [15,20,25]: add(f'adx>={t}', sh(adx(d,14))>=t)
    add('mom20>0', sh(cl.pct_change(20))>0); add('mom60>0', sh(cl.pct_change(60))>0); add('mom5>0', sh(cl.pct_change(5))>0)
    hi=cl.rolling(252,min_periods=60).max()
    for t in [5,10,15]: add(f'dd252<{t}%', sh(cl/hi-1)>-t/100)
    add('rsi14>45', sh(rsi(cl,14))>45); add('rsi14<70', sh(rsi(cl,14))<70); add('rsi2<90', sh(rsi(cl,2))<90); add('rsi2>10', sh(rsi(cl,2))>10)
    tr=pd.concat([d.high-d.low,(d.high-cl.shift()).abs(),(d.low-cl.shift()).abs()],axis=1).max(axis=1)
    atrp=tr.ewm(alpha=1/14,adjust=False).mean()/cl*100
    for t in [1.0,1.3,1.6]: add(f'atr%<{t}', sh(atrp)<t)
    rv=cl.pct_change().rolling(10).std()*100
    for t in [0.7,1.0]: add(f'rv10<{t}', sh(rv)<t)
    gap=(d.open/cl.shift()-1)*100; add('prev_gap>-0.3', sh(gap)>-0.3); add('prev_day_ret>-1', sh(cl.pct_change()*100)>-1); add('prev_day_ret>0', sh(cl.pct_change())>0)
    # ---- volatility (India VIX)
    vx=L('vix').reindex(days).ffill()
    for t in [14,16,18,20,25]: add(f'vix<{t}', vx.shift(1)<t)
    add('vix<vix_ma20', vx.shift(1)<vx.rolling(20).mean().shift(1)); add('vix5d<+10%', vx.shift(1)/vx.shift(6)-1<0.10); add('vix1d<+8%', vx.shift(1)/vx.shift(2)-1<0.08)
    add('vix1d>+8%(panic rebound)', vx.shift(1)/vx.shift(2)-1>0.08)
    # ---- macro / global (value known strictly before the day)
    ur,dx,us,sp,nq,br,au=[L(k) for k in ['usdinr','dxy','us10y','spx','nasdaq','brent','gold']]
    ko,tw,jp,cn=[L(k) for k in ['krw','twd','jpy','cny']]
    A=lambda s: _asof(s,days)
    for t in [0.5,1,2]: add(f'rupee21<{t}%', A(ur.pct_change(21)*100)<t)
    add('rupee1d<0.3%', A(ur.pct_change()*100)<0.3); add('rupee5d<0.5%', A(ur.pct_change(5)*100)<0.5)
    for t in [0,1.5]: add(f'dxy21<{t}%', A(dx.pct_change(21)*100)<t)
    add('dxy1d<0.5%', A(dx.pct_change()*100)<0.5)
    for t in [0,0.25]: add(f'us10y21<{t}', A(us.diff(21))<t)
    add('us10y<4.5', A(us)<4.5)
    for t in [-2,0]: add(f'spx21>{t}%', A(sp.pct_change(21)*100)>t)
    add('spx>sma50', A(sp)>A(sp.rolling(50).mean())); add('spx>sma200', A(sp)>A(sp.rolling(200).mean()))
    for t in [-1,-0.5,0]: add(f'spx1d>{t}%', A(sp.pct_change()*100)>t)
    add('nasdaq1d>-1%', A(nq.pct_change()*100)>-1)
    add('brent21avg<100', A(br.rolling(21).mean())<100); add('brent21avg<90', A(br.rolling(21).mean())<90)
    for t in [5,10]: add(f'brent21<+{t}%', A(br.pct_change(21)*100)<t)
    add('brent5<+5%', A(br.pct_change(5)*100)<5)
    add('gold21<5%', A(au.pct_change(21)*100)<5)
    add('krw21<2%', A(ko.pct_change(21)*100)<2); add('twd21<2%', A(tw.pct_change(21)*100)<2); add('jpy21<3%', A(jp.pct_change(21)*100)<3); add('cny21<1%', A(cn.pct_change(21)*100)<1)
    add('krw1d<0.7%', A(ko.pct_change()*100)<0.7)
    bn=L('banknifty').reindex(days).ffill()
    add('banknifty>sma50', bn.shift(1)>bn.rolling(50).mean().shift(1)); add('banknifty>sma200', bn.shift(1)>bn.rolling(200).mean().shift(1))
    add('bank_rel20>0', (bn.pct_change(20)-cl.reindex(days).pct_change(20)).shift(1)>0)
    # ---- flows / valuation (see factors.py for data limits)
    from factors import build_flags
    F=build_flags(days)
    add('fii_last_month>-10k', ~F['fii_last_month_sell']); add('fii_12m>-2L', ~F['fii_12m_sell'])
    pe=F['pe_value']
    for t in [21,23,25]: add(f'pe<{t}', pe<t)
    # ---- calendar
    add('not_Jan/Feb', ~pd.Series(days.month.isin([1,2]),index=days)); add('Apr/Jul', pd.Series(days.month.isin([4,7]),index=days))
    wd=pd.Series(days.dayofweek,index=days)
    add('not_Fri', wd!=4); add('not_Mon', wd!=0); add('Tue-Thu', wd.isin([1,2,3]))
    G['ALWAYS']=np.ones(len(days),bool); G['NEVER']=np.zeros(len(days),bool)
    return G
