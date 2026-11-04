"""Roadmap Phase 1: one backtest engine for every idea (baseline included).
Rules built in: signal on the CLOSE of bar t -> order fills at the OPEN of bar t+1 (+ optional extra delay); whole lots of 65;
stops checked on 1-minute bars inside the 15-min bar (fill at stop, or at the 1-min open if gapped through; overnight gaps fill at
the 09:15 open); daily indicators must be pre-shifted by the caller (previous completed day). Prices are the synthetic futures
series from rm_data.py. Costs: 'floor' (0.025%/side, 0.05% roll) and 'real' (brokerage+exchange+SEBI+stamp+GST+1 tick, STT on sales
with the dated schedule, roll = two legs + calendar spread).
Run with the venv that has numba:  <venv>/bin/python scripts/rm_*.py"""
import os, numpy as np, pandas as pd
from numba import njit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPITAL = 2e7; LOT = 65; RF = 0.06
SPLITS = {'train': ('2017-04-01', '2021-12-31'), 'valid': ('2022-01-01', '2023-12-31'), 'test': ('2024-01-01', '2026-10-31'),
          'recent': ('2022-01-01', '2026-10-31'), 'full': ('2017-04-01', '2026-10-31'), 'dev': ('2017-04-01', '2023-12-31')}

@njit(cache=True)
def _sim(fo, fh, fl, fc, prev, last_b, day_id, roll_cl, mo, mh, ml, mc, bm0, bm1, tdir, tsize, sdist,
         buy_r, sell_r, roll_r, capital, lot, lev, risk_b, min_chg, ov_cap, delay, dd_on, dd_th, dl_lim, nostop, rebal, max_lots):
    N = len(fo)
    pnl = np.zeros(N); cost = np.zeros(N); posl = np.zeros(N, np.int64)
    trades = np.zeros((N // 2 + 10, 11)); ntr = 0
    dec_lots = np.zeros(N, np.int64); dec_sd = np.zeros(N); dec_v = np.zeros(N, np.bool_)
    pos = 0; entry_px = 0.0; stop_px = 0.0; stopped_dir = 0; base_lots = 0
    tr_g = 0.0; tr_c = 0.0; tr_eb = 0; tr_lots = 0; tr_side = 0
    eq = 0.0; peak = 0.0; brake = False; day_start = 0.0; cur_day = -1; dl_hit = False
    for t in range(N):
        if day_id[t] != cur_day:
            cur_day = day_id[t]; day_start = eq; dl_hit = False
        if pos != 0:
            g = pos * lot * (fo[t] - prev[t]); pnl[t] += g; tr_g += g
        k = t - 1 - delay
        if k >= 0 and dec_v[k]:
            d = dec_lots[k]
            if d != pos:
                if pos != 0 and (d == 0 or (d > 0) != (pos > 0)):
                    c = abs(pos) * lot * fo[t] * (sell_r[t] if pos > 0 else buy_r[t])
                    cost[t] += c; tr_c += c
                    trades[ntr, 0] = tr_eb; trades[ntr, 1] = t; trades[ntr, 2] = tr_side; trades[ntr, 3] = tr_lots
                    trades[ntr, 4] = entry_px; trades[ntr, 5] = fo[t]; trades[ntr, 6] = tr_g; trades[ntr, 7] = tr_c
                    trades[ntr, 8] = 0; trades[ntr, 9] = 0; trades[ntr, 10] = 0
                    ntr += 1; pos = 0
                if d != 0 and pos == 0:
                    c = abs(d) * lot * fo[t] * (buy_r[t] if d > 0 else sell_r[t])
                    cost[t] += c; tr_c = c; tr_g = 0.0; tr_eb = t; tr_lots = abs(d); tr_side = 1 if d > 0 else -1
                    pos = d; entry_px = fo[t]
                    stop_px = 0.0
                    if (not nostop) and dec_sd[k] > 0: stop_px = fo[t] - tr_side * dec_sd[k]
                elif d != 0 and pos != 0:
                    q = d - pos
                    c = abs(q) * lot * fo[t] * (buy_r[t] if q > 0 else sell_r[t])
                    cost[t] += c; tr_c += c; pos = d
        if pos != 0:
            stopped = False
            if stop_px > 0:
                for j in range(bm0[t], bm1[t]):
                    fill = 0.0
                    if pos > 0:
                        if mo[j] <= stop_px: fill = mo[j]
                        elif ml[j] <= stop_px: fill = stop_px
                    else:
                        if mo[j] >= stop_px: fill = mo[j]
                        elif mh[j] >= stop_px: fill = stop_px
                    if fill > 0:
                        g = pos * lot * (fill - fo[t]); pnl[t] += g; tr_g += g
                        c = abs(pos) * lot * fill * (sell_r[t] if pos > 0 else buy_r[t])
                        cost[t] += c; tr_c += c
                        side = 1 if pos > 0 else -1
                        trades[ntr, 0] = tr_eb; trades[ntr, 1] = t; trades[ntr, 2] = side; trades[ntr, 3] = abs(pos)
                        trades[ntr, 4] = entry_px; trades[ntr, 5] = fill; trades[ntr, 6] = tr_g; trades[ntr, 7] = tr_c
                        trades[ntr, 8] = 1
                        trades[ntr, 9] = side * (stop_px - entry_px) * abs(pos) * lot / capital       # loss at the stop price (no gap)
                        trades[ntr, 10] = side * (fill - entry_px) * abs(pos) * lot / capital          # loss at the actual fill (gap incl.)
                        ntr += 1; stopped_dir = side; pos = 0; stopped = True
                        break
            if not stopped:
                g = pos * lot * (fc[t] - fo[t]); pnl[t] += g; tr_g += g
        if pos != 0 and roll_cl[t]:
            c = abs(pos) * lot * fc[t] * roll_r[t]; cost[t] += c; tr_c += c
        eq += pnl[t] - cost[t]
        if eq > peak: peak = eq
        if dd_on:
            if (peak - eq) / (capital + peak) > dd_th: brake = True
            if eq >= peak: brake = False
        if dl_lim > 0 and (eq - day_start) < -dl_lim * capital: dl_hit = True
        # ---- decision at the close of bar t for the next bar
        dr = tdir[t]
        if stopped_dir != 0 and dr != stopped_dir: stopped_dir = 0
        if stopped_dir != 0 and dr == stopped_dir: dr = 0
        if dl_hit and (not last_b[t]): dr = 0
        if dr == 0:
            dl = 0
        else:
            if pos != 0 and ((pos > 0) == (dr > 0)):
                base = base_lots
                if rebal and roll_cl[t]:
                    base = int(np.floor(lev * capital / (fc[t] * lot))); base_lots = base      # buy-and-hold benchmark: back to 1x notional at each roll
            else:
                capl = int(np.floor(lev * capital / (fc[t] * lot)))
                base = capl
                if max_lots > 0 and base > max_lots: base = max_lots
                if risk_b > 0 and sdist[t] > 0:
                    rl = int(np.floor(risk_b * capital / (sdist[t] * lot)))
                    if rl < base: base = rl
                base_lots = base
            s = tsize[t]
            if brake: s *= 0.5
            n = int(np.floor(base * s + 1e-9))
            if ov_cap > 0 and (last_b[t] or (t + 1 < N and last_b[t + 1])):
                if n > ov_cap: n = ov_cap
            dl = n * dr
            if pos != 0 and dl != 0 and ((pos > 0) == (dl > 0)) and abs(dl - pos) < min_chg: dl = pos
        dec_lots[t] = dl; dec_sd[t] = sdist[t]; dec_v[t] = True
        posl[t] = pos
    return pnl, cost, posl, trades[:ntr]

def cost_rates(dates, close, kind):
    """Per-bar proportional cost rates (buy, sell, roll). dates: DatetimeIndex per bar."""
    n = len(dates); d = pd.DatetimeIndex(dates)
    if kind == 'floor':
        return np.full(n, 2.5e-4), np.full(n, 2.5e-4), np.full(n, 5e-4)
    stt = np.where(d < '2023-04-01', 1.0e-4, np.where(d < '2024-10-01', 1.25e-4, np.where(d < '2026-04-01', 2.0e-4, 5.0e-4)))
    brok, exch, sebi = 1.25e-5, 1.73e-5, 1.0e-6; gst = 0.18 * (brok + exch + sebi); stamp = 2.0e-5
    slip = 0.05 / close                                    # one tick
    base = brok + exch + sebi + gst
    buy = base + stamp + slip; sell = base + stt + slip
    roll = buy + sell + 0.5 / close                         # two legs + half-point calendar spread
    return buy, sell, roll

class Engine:
    def __init__(self, ds=None):
        ds = ds if ds is not None else pd.read_pickle(os.path.join(ROOT, 'data', 'rm', 'dataset.pkl'))
        self.ds = ds; b = ds['b15']; D = ds['daily']; m1 = ds['m1']
        self.b = b; self.D = D; self.N = len(b)
        dates = b['date']; self.dates = pd.DatetimeIndex(dates.values)
        self.day_codes = pd.Index(D.index).get_indexer(self.dates)
        mc_ = D['m_close'].values[self.day_codes]; mp_ = D['m_prevclose'].values[self.day_codes]
        self.mult = mc_
        o, h, l, c = (b[x].values for x in ('open', 'high', 'low', 'close'))
        self.so, self.sh, self.sl, self.sc = o, h, l, c            # spot (signals)
        self.fo, self.fh, self.fl, self.fc = o * mc_, h * mc_, l * mc_, c * mc_
        N = self.N; first = np.r_[True, self.day_codes[1:] != self.day_codes[:-1]]
        self.first_b = first; self.last_b = np.r_[first[1:], True]
        prev = np.r_[self.fc[0], self.fc[:-1]].copy()
        prev[first] = np.r_[np.nan, c[:-1]][first] * mp_[first]; prev[0] = self.fo[0]
        self.prev = prev
        self.roll_cl = self.last_b & D['roll'].values[self.day_codes]
        mmult = D['m_close'].values[pd.Index(D.index).get_indexer(m1['date'].values)]
        self.mo, self.mh, self.ml, self.mc = (m1[x].values * mmult for x in ('open', 'high', 'low', 'close'))
        mt = m1.index.values; bs = b['start'].values
        self.bm0 = np.searchsorted(mt, bs, 'left').astype(np.int64); self.bm1 = np.searchsorted(mt, bs + np.timedelta64(15, 'm'), 'left').astype(np.int64)
        self.hhmm = (b['start'].dt.hour * 60 + b['start'].dt.minute).values       # start minute of the bar
        self.bar_k = ((self.hhmm - 555) // 15).astype(int)                       # 0..24
        self.rates = {k: cost_rates(self.dates, self.fc, k) for k in ('floor', 'real')}
        days = D.index; self.days = days
        self.cal = np.r_[1, np.diff(days.values).astype('timedelta64[D]').astype(int)]
        self.nyears = {}

    def run(self, tdir, tsize=None, sdist=None, cost='real', delay=0, lev=1.0, risk=0.0, min_chg=1, ov_cap=0, dd_brake=False,
            dd_th=0.10, dl_lim=0.0, nostop=False, rebal=False, max_lots=0):
        N = self.N
        tdir = np.asarray(tdir).astype(np.int8)
        tsize = np.ones(N) if tsize is None else np.nan_to_num(np.asarray(tsize, float), nan=0.0)
        sdist = np.zeros(N) if sdist is None else np.nan_to_num(np.asarray(sdist, float), nan=0.0)
        br, sr, rr = self.rates[cost]
        pnl, cst, posl, trades = _sim(self.fo, self.fh, self.fl, self.fc, self.prev, self.last_b, self.day_codes.astype(np.int64), self.roll_cl,
                                     self.mo, self.mh, self.ml, self.mc, self.bm0, self.bm1, tdir, tsize, sdist, br, sr, rr,
                                     CAPITAL, LOT, lev, risk, min_chg, ov_cap, delay, dd_brake, dd_th, dl_lim, nostop, rebal, max_lots)
        return Result(self, pnl, cst, posl, trades)

class Result:
    def __init__(self, E, pnl, cost, posl, trades):
        self.E = E; nd = len(E.days)
        self.pnl_d = np.bincount(E.day_codes, weights=pnl, minlength=nd); self.cost_d = np.bincount(E.day_codes, weights=cost, minlength=nd)
        self.posl = posl; self.trades = trades
        self.inmkt_d = np.bincount(E.day_codes, weights=(posl != 0).astype(float), minlength=nd) / 25.0
        self.gross_d = self.pnl_d / CAPITAL; self.net_d = (self.pnl_d - self.cost_d) / CAPITAL
        self.int_d = RF * E.cal / 365.0                                # interest on idle collateral (calendar days since prior session)
        self.trade_day = E.day_codes[np.minimum(trades[:, 1].astype(int), E.N - 1)] if len(trades) else np.array([], int)

    def series(self, interest=True):
        r = self.net_d + (self.int_d if interest else 0.0)
        return pd.Series(r, index=self.E.days)

    def metrics(self, split='full', interest=True, lo=None, hi=None):
        a, z = SPLITS[split] if lo is None else (lo, hi)
        s = self.series(interest).loc[a:z]
        ex = pd.Series(self.net_d, index=self.E.days).loc[a:z]      # excess return = futures P&L after costs (interest removed)
        return metrics_from(s, self, a, z, ex)

def metrics_from(s, R=None, a=None, z=None, ex=None):
    ex = s if ex is None else ex
    n = len(s); yrs = n / 252.0
    if n < 5: return {}
    eq = (1 + s).cumprod(); cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = s.std() * np.sqrt(252); sh = ex.mean() / ex.std() * np.sqrt(252) if ex.std() > 0 else 0.0
    dn = s[s < 0]; so = ex.mean() / np.sqrt((np.minimum(ex, 0) ** 2).mean()) * np.sqrt(252) if (ex < 0).any() else np.nan
    pk = eq.cummax(); dd = eq / pk - 1; mdd = dd.min()
    # drawdown length (trading days from peak to recovery, longest)
    under = (dd < 0).astype(int).values; best = cur = 0
    for u in under:
        cur = cur + 1 if u else 0; best = max(best, cur)
    out = dict(CAGR=cagr, Vol=vol, Sharpe=sh, Sortino=so, MaxDD=mdd, DDdays=best, Calmar=cagr / abs(mdd) if mdd < 0 else np.nan, n=n)
    if R is not None:
        idx = R.E.days; m = (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(z))
        tr = R.trades
        if len(tr):
            td = R.trade_day; sel = m[td]
            T = tr[sel]; net = (T[:, 6] - T[:, 7])
            out['Trades'] = len(T); out['TradesPerYr'] = len(T) / yrs
            out['WinRate'] = (net > 0).mean() if len(T) else np.nan
            w = net[net > 0]; l = net[net <= 0]
            out['AvgWin/AvgLoss'] = (w.mean() / abs(l.mean())) if len(w) and len(l) and l.mean() != 0 else np.nan
            for nm, sd in (('LongLegCAGR', 1), ('ShortLegCAGR', -1)):
                out[nm] = net[T[:, 2] == sd].sum() / CAPITAL / yrs
            out['MaxLossAtStop'] = (-T[T[:, 8] == 1][:, 9]).max() if (T[:, 8] == 1).any() else 0.0
            out['MaxLossWithGap'] = (-T[T[:, 8] == 1][:, 10]).max() if (T[:, 8] == 1).any() else 0.0
        else:
            out['Trades'] = 0; out['TradesPerYr'] = 0
        out['TimeInMkt'] = R.inmkt_d[m].mean(); out['CostDrag%/yr'] = R.cost_d[m].sum() / CAPITAL / yrs * 100
    return out

def yearly(R, interest=True):
    s = R.series(interest)
    return s.groupby(s.index.year).apply(lambda x: (1 + x).prod() - 1)

def fmt(m):
    tp = m.get('TradesPerYr', float('nan')); wr = m.get('WinRate', float('nan'))
    return f"CAGR {m['CAGR']:.1%} MaxDD {m['MaxDD']:.1%} Sharpe {m['Sharpe']:.2f} Sortino {m['Sortino']:.2f} Calmar {m['Calmar']:.2f} Trades/yr {tp:.0f} Win {wr:.0%}"
