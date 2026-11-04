"""Signals for the roadmap ideas. Every function returns per-bar (tdir, tsize) decided at the CLOSE of the bar.
Daily indicators are computed on completed daily bars and shifted one day (the previous completed day) before being used."""
import numpy as np, pandas as pd

def wilder(x, n): return pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().values

def atr_series(h, l, c, n):
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)]); return wilder(tr, n)

def supertrend(h, l, c, n=14, m=3.0, warm=None, atr_kind='wilder'):
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    atr = wilder(tr, n) if atr_kind == 'wilder' else pd.Series(tr).rolling(n, min_periods=1).mean().values
    hl2 = (h + l) / 2; ub = hl2 + m * atr; lb = hl2 - m * atr
    N = len(c); fu = ub.copy(); fl = lb.copy(); d = np.ones(N, np.int8)
    for i in range(1, N):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if d[i - 1] == -1 and c[i] > fu[i - 1]: d[i] = 1
        elif d[i - 1] == 1 and c[i] < fl[i - 1]: d[i] = -1
        else: d[i] = d[i - 1]
    d[:(warm if warm is not None else n * 3)] = 0
    return d, atr

class Sig:
    """Holds the shared inputs once."""
    def __init__(self, E, vix=None, spx=None, oi=None):
        self.E = E; b = E.b; self.h, self.l, self.c, self.o = E.sh, E.sl, E.sc, E.so
        self.N = E.N; self.dc = E.day_codes; D = E.D; self.D = D
        self.st, self.atr15 = supertrend(self.h, self.l, self.c, 14, 3.0)
        self.first, self.last, self.k = E.first_b, E.last_b, E.bar_k
        # daily frame from spot bars
        self.dd = D[['open', 'high', 'low', 'close']].copy()
        self.vix = vix; self.spx = spx; self.oi = oi

    # --- helpers
    def d2b(self, daily, shift=1):
        """Map a daily series (indexed like D) to bars using the PREVIOUS completed day (shift=1)."""
        v = pd.Series(np.asarray(daily, float), index=self.D.index).shift(shift).values
        return v[self.dc]
    def daily_close_at(self, k=24):
        """close of the bar with bar index k each day (spot), mapped to bars of the same day only from that bar on (else prior day)."""
        raise NotImplementedError

    def baseline(self):
        return (self.st == 1).astype(np.int8), np.ones(self.N)

    def er_daily(self, n):
        c = self.dd['close']; ch = (c - c.shift(n)).abs(); vol = c.diff().abs().rolling(n).sum(); return (ch / vol).values
    def adx_daily(self, n):
        d = self.dd; h, l, c = d.high.values, d.low.values, d.close.values
        up = np.r_[0, h[1:] - h[:-1]]; dn = np.r_[0, l[:-1] - l[1:]]
        pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
        tr = np.maximum.reduce([h - l, np.abs(h - np.r_[c[0], c[:-1]]), np.abs(l - np.r_[c[0], c[:-1]])])
        atr = wilder(tr, n); pdi = 100 * wilder(pdm, n) / atr; mdi = 100 * wilder(mdm, n) / atr
        return wilder(100 * np.abs(pdi - mdi) / (pdi + mdi + 1e-12), n)
    def sma_daily(self, n): return self.dd['close'].rolling(n).mean().values
    def dst_daily(self, n, m):
        d, _ = supertrend(self.dd.high.values, self.dd.low.values, self.dd.close.values, n, m, warm=n); return d.astype(float)
    def atr_daily(self, n): return atr_series(self.dd.high.values, self.dd.low.values, self.dd.close.values, n)

    # --- ideas ---------------------------------------------------------------------------------------
    def A1(self):  # symmetric shorts
        return self.st.astype(np.int8), np.ones(self.N)
    def A2(self, L):  # shorts only when previous daily close < SMA(L)
        sma = self.d2b(self.sma_daily(L)); pc = self.d2b(self.dd.close.values)
        t = np.where(self.st == 1, 1, np.where((self.st == -1) & (pc < sma), -1, 0)).astype(np.int8); return t, np.ones(self.N)
    def A3(self, n, m):  # daily Supertrend agreement
        dd = self.d2b(self.dst_daily(n, m)); t = np.where((self.st == 1) & (dd == 1), 1, np.where((self.st == -1) & (dd == -1), -1, 0)).astype(np.int8); return t, np.ones(self.N)
    def B1_er(self, n, thr):  # long-only baseline with chop filter
        er = self.d2b(self.er_daily(n)); ok = er >= thr; t = np.where((self.st == 1) & ok, 1, 0).astype(np.int8); return t, np.ones(self.N)
    def B1_adx(self, n, thr):
        a = self.d2b(self.adx_daily(n)); ok = a >= thr; t = np.where((self.st == 1) & ok, 1, 0).astype(np.int8); return t, np.ones(self.N)
    def _vixpct(self, win=252):
        v = self.vix.reindex(self.D.index).ffill(); pr = v.rolling(win, min_periods=60).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True)
        return self.d2b(pr.values)
    def B2(self, p, mode='high'):  # stand aside when VIX percentile > p (mode high) or < p (mode low)
        vp = self._vixpct(); ok = (vp <= p) if mode == 'high' else (vp >= p); ok = np.where(np.isnan(vp), True, ok)
        t = np.where((self.st == 1) & ok, 1, 0).astype(np.int8); return t, np.ones(self.N)
    def C1(self, n):  # flip must persist n bars
        s = self.st; N = self.N; out = np.zeros(N, np.int8); cur = 0; cnt = 0; cand = 0
        for i in range(N):
            w = 1 if s[i] == 1 else 0
            if w == cur: cnt = 0; cand = w
            else:
                if w == cand: cnt += 1
                else: cand = w; cnt = 1
                if cnt >= n: cur = w; cnt = 0
            out[i] = cur
        return out, np.ones(self.N)
    def D1(self):  # intraday only: flat by 15:15 (decision at the bar starting 15:00 fills at 15:15 open)
        t = (self.st == 1).astype(np.int8); t = np.where(self.k >= 24 - 1, 0, t).astype(np.int8)   # k=23 is the 15:00 bar
        # the position must also not be re-entered after 15:15
        t = np.where(self.k >= 23, 0, t).astype(np.int8); return t, np.ones(self.N)
    def D2(self, orm, L):  # opening-range breakout with trend filter, flat 15:15
        nb = orm // 15; N = self.N; out = np.zeros(N, np.int8)
        sma = self.d2b(self.sma_daily(L)); pc = self.d2b(self.dd.close.values)
        ORH = ORL = None; cur = 0; day = -1
        for i in range(N):
            if self.dc[i] != day: day = self.dc[i]; cur = 0; hi = -1e18; lo = 1e18
            k = self.k[i]
            if k < nb:
                hi = max(hi, self.h[i]); lo = min(lo, self.l[i])
            else:
                up = pc[i] > sma[i]; dn = pc[i] < sma[i]
                if self.c[i] > hi and up: cur = 1
                elif self.c[i] < lo and dn: cur = -1
                elif cur == 1 and self.c[i] < lo: cur = 0
                elif cur == -1 and self.c[i] > hi: cur = 0
            out[i] = 0 if k >= 23 else cur
        return out, np.ones(self.N)
    def D3(self, first, last):  # no NEW entries in the first `first` bars or the last `last` bars
        N = self.N; base = (self.st == 1).astype(np.int8); out = np.zeros(N, np.int8); prev = 0
        for i in range(N):
            w = base[i]
            blocked = (self.k[i] < first) or (self.k[i] >= 25 - last)
            if w != prev and w != 0 and blocked: w = prev
            out[i] = w; prev = w
        return out, np.ones(self.N)
    def E1(self, small, large):  # gap fade (small) / follow (large) in ATR units; trade from the close of the first bar, flat 15:15
        N = self.N; out = np.zeros(N, np.int8)
        pcl = self.d2b(self.dd.close.values, 1); atr = self.d2b(self.atr_daily(14), 1)
        # gap known at 09:15 open of day; the signal bar is the first bar (its close)
        for i in range(N):
            if self.k[i] == 0:
                gap = (self.o[i] - pcl[i]) / atr[i] if atr[i] == atr[i] else 0.0
                j = i; cur = 0
                if abs(gap) > large: cur = 1 if gap > 0 else -1
                elif 0 < abs(gap) <= small: cur = -1 if gap > 0 else 1
                if cur != 0:
                    for q in range(i, N):
                        if self.dc[q] != self.dc[i]: break
                        out[q] = cur if self.k[q] < 23 else 0
        return out, np.ones(self.N)
    def _day_pos(self, sig_d, hold_overnight=True, flat_from=23):
        """sig_d[d] = position wanted for day d, known BEFORE the open of d. Bars k<flat_from (or k<24 if overnight) hold sig_d[d];
        the last bar's decision (filled at the next open) sets sig_d[d+1]."""
        sig_d = np.nan_to_num(np.asarray(sig_d, float)).astype(np.int8); nd = len(sig_d)
        nxt = np.r_[sig_d[1:], 0].astype(np.int8)
        cur = sig_d[self.dc]
        out = np.where(self.k == 24, nxt[self.dc], cur)
        if not hold_overnight: out = np.where(self.k == 23, 0, out)
        return out.astype(np.int8)
    def _px1515(self):
        idx = pd.Series(np.arange(self.N)).groupby(self.dc).apply(lambda x: x.iloc[min(len(x) - 1, 23)]).values
        return pd.Series(self.c[idx], index=self.D.index)
    def F1(self, lo, ert):  # mean reversion in range regimes (daily RSI(2) with today's 15:15 price), decided at the 15:15 bar close
        px = self._px1515(); n = 2; dl = px.diff(); up = dl.clip(lower=0); dn = (-dl).clip(lower=0)
        ru = up.ewm(alpha=1.0 / n, adjust=False).mean(); rd = dn.ewm(alpha=1.0 / n, adjust=False).mean()
        rsi = (100 - 100 / (1 + ru / (rd + 1e-12))).values; er = self.er_daily(20)
        nd = len(self.D); dec = np.zeros(nd, np.int8); cur = 0
        for d in range(1, nd):
            r = rsi[d]; e = er[d - 1]
            if cur == 0:
                if e == e and e < ert:
                    if r < lo: cur = 1
                    elif r > 100 - lo: cur = -1
            elif cur == 1 and r > 50: cur = 0
            elif cur == -1 and r < 50: cur = 0
            dec[d] = cur
        prev = np.r_[0, dec[:-1]].astype(np.int8)
        out = np.where(self.k < 23, prev[self.dc], dec[self.dc]).astype(np.int8)
        return out, np.ones(self.N)
    def G1(self):  # diagnostic: long only overnight (decision at the 15:15 bar, flat at the next open)
        return (self.k == 23).astype(np.int8), np.ones(self.N)
    def G1b(self):  # diagnostic: long only during the day (enter at first-bar close, out by 15:15)
        return ((self.k >= 0) & (self.k < 23)).astype(np.int8), np.ones(self.N)
    def H1(self, n):  # futures OI + price change quadrants from the previous completed day (OI published after the close)
        ch = pd.Series(self.D.close.values, index=self.D.index).pct_change(n)
        oi = self.oi.reindex(self.D.index).ffill(); dOI = oi.pct_change(n)
        s = np.sign(ch.values); o = np.sign(dOI.values); sig = np.zeros(len(s))
        sig[(s > 0) & (o > 0)] = 1; sig[(s < 0) & (o > 0)] = -1; sig[(s > 0) & (o < 0)] = 1; sig[(s < 0) & (o < 0)] = -1
        wanted = np.r_[0, sig[:-1]]               # day d uses day d-1 data
        return self._day_pos(wanted, hold_overnight=True), np.ones(self.N)
    def H2(self, thr):  # previous US session S&P return -> direction for the Indian day (flat 15:15)
        r = (self.spx / self.spx.shift(1) - 1).dropna()
        pos = np.searchsorted(r.index.values, self.D.index.values, side='left') - 1      # last US session dated strictly before day d
        rv = np.where(pos >= 0, r.values[np.maximum(pos, 0)], 0.0)
        wanted = np.where(rv > thr, 1, np.where(rv < -thr, -1, 0))
        return self._day_pos(wanted, hold_overnight=False), np.ones(self.N)

    # --- COST line: turnover reducers on the baseline signal -------------------------------------------
    def T1(self, n, m):  # slower Supertrend on 15-min bars, long-only
        d, _ = supertrend(self.h, self.l, self.c, n, m); return (d == 1).astype(np.int8), np.ones(self.N)
    def T2(self):  # baseline Supertrend state evaluated only at the 15:15 bar close (k == 23); held otherwise
        want = (self.st == 1).astype(np.int8); out = np.zeros(self.N, np.int8); cur = 0
        for i in range(self.N):
            if self.k[i] == 23: cur = want[i]
            out[i] = cur
        return out, np.ones(self.N)
    def T4(self, tf, n, m):  # Supertrend on tf-minute bars built inside each session; signal updates at the close of each completed bar
        g = tf // 15; N = self.N; grp = np.where(self.k // g == (self.k.max()) // g, self.k // g, self.k // g)
        # group id per session
        key = self.dc * 100 + (self.k // g)
        _, first = np.unique(key, return_index=True); order = np.sort(first); gid = np.searchsorted(order, np.arange(N), side='right') - 1
        ng = len(order); O = np.zeros(ng); H = np.full(ng, -1e18); L = np.full(ng, 1e18); C = np.zeros(ng)
        for i in range(N):
            j = gid[i]; H[j] = max(H[j], self.h[i]); L[j] = min(L[j], self.l[i]); C[j] = self.c[i]
        d, _ = supertrend(H, L, C, n, m)
        # a group is complete at its last 15-min bar: the bar before the next group starts (or end of session)
        last_of_group = np.r_[gid[1:] != gid[:-1], True]
        out = np.zeros(N, np.int8); cur = 0
        for i in range(N):
            if last_of_group[i]: cur = 1 if d[gid[i]] == 1 else 0
            out[i] = cur
        return out, np.ones(N)
