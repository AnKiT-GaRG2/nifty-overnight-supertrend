import sys; sys.path.insert(0,'scripts')
from btlib import *

def prep(end=None):
    b = load_15m()
    if end: b = b[b.index < end]
    d = daily_from(b)
    vix = pd.read_csv(f'{DATA}/vix.csv', parse_dates=['date']).set_index('date')['close']
    f = pd.DataFrame(index=d.index)
    f['sma200'] = d['close'].rolling(200).mean()
    f['sma100'] = d['close'].rolling(100).mean()
    f['adx'] = adx(d, 14)
    f['vix'] = vix.reindex(d.index).ffill()
    f['rsi2'] = rsi(d['close'], 2)
    f['close'] = d['close']
    F = f.shift(1)                                    # known at the previous close -> no lookahead
    F['rsi2_prev'] = f['rsi2'].shift(1)
    bf = F.reindex(b['date']).set_axis(b.index)       # map to 15m bars
    return b, d, f, bf

_ST = {}
def get_st(b, n, m):
    k = (len(b), n, m)
    if k not in _ST: _ST[k] = supertrend(b, n, m)
    return _ST[k]

def trend_strategy(b, bf, n=14, m=3.0, shorts='none', ma='sma200', adx_thr=0, risk=None, vix_cut=None, vix_scale=0.5, tod_block=False):
    st = get_st(b, n, m); c = b['close'].values
    d = st['dir'].values
    if ma is None:
        bull = bear = np.ones(len(b), bool)
    else:
        px_prev = bf['close'].values; ma_v = bf[ma].values
        bull = px_prev > ma_v; bear = px_prev < ma_v
    trendok = np.ones(len(b), bool) if adx_thr <= 0 else (bf['adx'].values >= adx_thr)
    long_ok = trendok & bull
    want = np.zeros(len(b), dtype=int)
    want[(d == 1) & long_ok] = 1
    if shorts == 'bear':   want[(d == -1) & trendok & bear] = -1
    elif shorts == 'all':  want[(d == -1) & trendok] = -1
    dist = np.abs(c - st['line'].values) / c
    pos = state_machine(want, dist, risk)
    if vix_cut is not None:
        pos = pos * np.where(bf['vix'].values > vix_cut, vix_scale, 1.0)
    return pos

def run(b, bf, which=('train 17-21', 'valid 22-23'), **kw):
    pos = trend_strategy(b, bf, **kw)
    net, held = pnl(b, pos)
    return report(net, held, which), net, held
