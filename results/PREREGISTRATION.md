# Pre-registration (written 2026-11-03, before any run of rf_prereg.py)

Instruments: NSE Nifty and Bank Nifty index futures only (front month, daily close-to-close, real bhavcopy prices). No spot.

## Acceptance targets (tests, not search goals)
A strategy is accepted only if, on data not used to build or choose it, ALL hold (total-return view = futures P&L + 6% p.a. on capital; pure futures P&L also reported):
1. CAGR > 15%
2. Max drawdown less than 10% (|MaxDD| < 10%)
3. Sharpe > 1.0
Also reported: same metrics for buy-and-hold Nifty futures. Costs 0.025%/side + 0.05% roll (stress x3 reported).

## Data split (fixed)
- Discovery: 2008-01-01 to 2016-12-31 (rank all variants here; score = weaker of two halves, 2008-12 and 2013-16, of CAGR minus |MaxDD|)
- Validation: 2017-01-01 to 2023-12-31 (choose among the top-30 discovery variants)
- Test: 2024-01-01 to 2026-10-31. Touched ONCE, for ONE finalist = the top-30 variant with the highest validation Sharpe. No retries, no edits after seeing test. If it fails, the answer is "not accepted".

## Search space (finite, declared in advance; trials counted and reported)
- Instruments: Nifty, Bank Nifty, 50/50 both
- Trend filter: close above SMA 50 / 100 / 200
- Stress score S = count of caution flags: US10Y +25bp/21d, USDINR +2%/21d, DXY +1.5%/21d, S&P500 -2%/21d, Brent +5%/5d, India VIX >= 25 (all lagged, strictly prior data)
- Long rule: long if trend up AND S <= s_max (0,1,2). Optional short: if trend down AND S >= s_min (1,2,3) at size 0.5 or 1.0
- Sideways sleeve (off / 0.5 weight): RSI(2) mean reversion when price within 2% of SMA100
- Sizing: none, or volatility target 8/10/12% with leverage cap 1x or 2x (20d realised vol, lagged)
- Not available before 2017 and therefore NOT used: FII flows, P/E.

## Rules of conduct
- No parameter or rule changes after test is viewed. Number of variants tried is printed with the result.
- Extra honesty checks reported: null rate (share of all variants meeting the targets on validation), pure-futures view, cost stress, regime-wise and year-wise results.
