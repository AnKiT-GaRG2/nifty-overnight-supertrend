# Short-side roadmap results (train-only selection; see PROTOCOL_CHANGES.md)

## S0 flat-time diagnostic (train): shorts earn +5.4 bp/day while Supertrend is red (+2.4 bp excluding Feb-Apr 2020); about 1.9 bp/day of that is the synthetic basis decay. Gate (mean < 0 for a long outside Mar 2020): borderline pass, mostly carry.

## S1 naive shorts (benchmark, never kept)
- S1.1/S1.2 short leg alone, train: CAGR 4.7% MaxDD -17.6% Sharpe 0.45, trades/yr 87, win 36%; sell-off capture 6.6%/yr, outside-window P&L -1.3%/yr, balance 5.3%/yr

## S2 permission rules (train; short leg at full size, no stop)

S2.1: cell -> short-leg train CAGR / MaxDD / Sharpe / trades-yr / capture / outside P&L / time short
   100: 4.1% -10.7% 0.50 23 5.1% -0.7% 11%  nbrs>0:True
   150: 3.3% -10.4% 0.42 20 4.1% -0.5% 10%  nbrs>0:True
   200: 2.8% -12.1% 0.37 18 3.8% -0.8% 8%  nbrs>0:True
   250: 2.7% -12.1% 0.36 16 3.5% -0.6% 7%  nbrs>0:True
   -> chosen 150 (neighbour-mean Sharpe 0.43, balance 3.6%/yr)

S2.2: cell -> short-leg train CAGR / MaxDD / Sharpe / trades-yr / capture / outside P&L / time short
   20: 0.5% -15.3% 0.10 31 2.2% -1.5% 11%  nbrs>0:True
   50: 0.1% -13.0% 0.05 23 1.8% -1.4% 8%  nbrs>0:True
   100: -0.0% -11.7% 0.03 18 2.3% -2.1% 6%  nbrs>0:True
   -> chosen 50 (neighbour-mean Sharpe 0.06, balance 0.3%/yr)

S2.3: cell -> short-leg train CAGR / MaxDD / Sharpe / trades-yr / capture / outside P&L / time short
   1.0: 4.3% -12.7% 0.56 42 6.9% -2.3% 15%  nbrs>0:True
   1.1: 4.4% -9.6% 0.61 31 6.9% -2.4% 11%  nbrs>0:True
   1.25: 2.5% -15.1% 0.39 19 5.1% -2.4% 7%  nbrs>0:True
   1.5: 2.6% -8.2% 0.45 8 2.7% 0.0% 3%  nbrs>0:True
   -> chosen 1.1 (neighbour-mean Sharpe 0.52, balance 4.6%/yr)

S2.4: cell -> short-leg train CAGR / MaxDD / Sharpe / trades-yr / capture / outside P&L / time short
   50: 2.1% -16.4% 0.26 52 6.1% -3.5% 24%  nbrs>0:True
   60: 4.3% -12.5% 0.49 41 6.1% -1.5% 18%  nbrs>0:True
   67: 5.2% -10.4% 0.60 33 5.8% -0.4% 15%  nbrs>0:True
   75: 6.9% -9.8% 0.80 27 5.8% 1.3% 13%  nbrs>0:True
   80: 6.1% -9.8% 0.73 24 5.2% 1.1% 12%  nbrs>0:True
   -> chosen 75 (neighbour-mean Sharpe 0.71, balance 5.8%/yr)

S2.5 breadth: not testable (no equity bhavcopy data in repo).

**S2 winner: S2.4 = 75**
- Pair S2.4+S2.3: Sharpe 1.03 vs 0.80 / 0.61; pair beats both in 7/9 neighbour cells -> KEEP pair
- S2 system short leg train: CAGR 6.9% MaxDD -6.7% Sharpe 1.03, trades/yr 11

## S3 entry/exit variants (each vs S2 winner, train short-leg Sharpe; need +0.05 and no worse MaxDD)
   S3.1 2.0: CAGR 4.6% MaxDD -6.5% Sharpe 0.57 trades/yr 16
   S3.1 2.5: CAGR 6.3% MaxDD -7.4% Sharpe 0.79 trades/yr 12
   -> S3.1 best 2.5 Sharpe 0.79 vs 1.03: drop
   S3.2 None: CAGR 2.5% MaxDD -5.3% Sharpe 0.52 trades/yr 6
   -> S3.2 best None Sharpe 0.52 vs 1.03: drop
   S3.3 3: CAGR 6.9% MaxDD -6.7% Sharpe 1.03 trades/yr 11
   S3.3 5: CAGR 6.9% MaxDD -6.7% Sharpe 1.03 trades/yr 11
   S3.3 8: CAGR 6.9% MaxDD -6.7% Sharpe 1.03 trades/yr 11
   -> S3.3 best 3 Sharpe 1.03 vs 1.03: drop
   S3.4 1.5: CAGR 5.2% MaxDD -4.3% Sharpe 0.95 trades/yr 11
   S3.4 2.0: CAGR 6.9% MaxDD -6.7% Sharpe 0.93 trades/yr 11
   S3.4 3.0: CAGR 8.7% MaxDD -6.7% Sharpe 1.08 trades/yr 11
   -> S3.4 best 3.0 Sharpe 1.08 vs 1.03: drop
   S3.5 None: CAGR 2.1% MaxDD -5.5% Sharpe 0.36 trades/yr 16
   -> S3.5 best None Sharpe 0.36 vs 1.03: drop
- Kept at most two: []

## S4 short sizing (risk 0.5% of capital at the stop, k=2.5 x ATR; train short leg)
   cap 6 lots, overnight cap none: CAGR 1.2% MaxDD -1.1% Sharpe 1.04, max loss at stop 0.28%, with gap 0.28%
   cap 6 lots, overnight cap 6: CAGR 1.2% MaxDD -1.1% Sharpe 1.04, max loss at stop 0.28%, with gap 0.28%
   cap 8 lots, overnight cap none: CAGR 1.4% MaxDD -1.5% Sharpe 0.99, max loss at stop 0.37%, with gap 0.37%
   cap 8 lots, overnight cap 6: CAGR 1.2% MaxDD -1.2% Sharpe 1.00, max loss at stop 0.32%, with gap 0.32%
   cap 12 lots, overnight cap none: CAGR 1.7% MaxDD -2.1% Sharpe 0.90, max loss at stop 0.47%, with gap 0.53%
   cap 12 lots, overnight cap 6: CAGR 1.4% MaxDD -1.8% Sharpe 0.89, max loss at stop 0.47%, with gap 0.47%
- Frozen convention: cap 8, overnight cap 6 (overnight cap kept only if train short Sharpe does not fall)

## Short-leg metrics on train (frozen S2-S4 spec)
- Short-leg Sharpe 1.00, MaxDD -1.2%, CAGR contribution 1.2%; excluding Feb-Apr 2020: Sharpe 0.36, CAGR 0.3%
- Sell-off capture 1.2%/yr vs up-year cost 0.0%/yr (outside-window P&L 0.0%/yr)
- Time short 5% of days; trades/yr 11; hit rate 53%; avg win/avg loss 2.44
- Worst loss on a short incl. gap: 0.32% of capital; at stop price 0.32%; correlation of short-leg and long-leg daily returns: +0.04
- Short-leg P&L by train year (sum of daily returns): 2017: +0.2%, 2018: +1.5%, 2019: -0.2%, 2020: +4.2%, 2021: +0.0%
- Same year table excluding Feb-Apr 2020: 2017: +0.2%, 2018: +1.5%, 2019: -0.2%, 2020: -0.2%, 2021: +0.0%

## Train gates
- short-leg Sharpe > 0 across neighbour grid (S2 rule): PASS
- sell-off capture > up-year cost: PASS
- short Sharpe > 0 on train: PASS
- no short loses > 1% incl. gaps (train): PASS

## S5 merged system vs no-shorts baseline (validation = the ONE look; test/full are descriptive, window already opened for this project)

| Window | Baseline CAGR/DD/Sharpe | Merged CAGR/DD/Sharpe | Short leg alone CAGR/DD/Sharpe | Short-leg corr w/ long |
|---|---|---|---|---|
| train | CAGR 22.8% MaxDD -13.4% Sharpe 1.15 | CAGR 24.3% MaxDD -10.3% Sharpe 1.23 | CAGR 1.2% MaxDD -2.0% Sharpe 0.70 | -0.03 |
| valid | CAGR 13.3% MaxDD -7.7% Sharpe 0.73 | CAGR 13.1% MaxDD -7.6% Sharpe 0.69 | CAGR -0.2% MaxDD -1.7% Sharpe -0.06 | -0.01 |
| test | CAGR 10.4% MaxDD -6.6% Sharpe 0.46 | CAGR 9.1% MaxDD -8.4% Sharpe 0.31 | CAGR -1.2% MaxDD -8.2% Sharpe -0.42 | +0.05 |
| full | CAGR 17.0% MaxDD -13.4% Sharpe 0.90 | CAGR 17.2% MaxDD -10.3% Sharpe 0.90 | CAGR 0.2% MaxDD -8.2% Sharpe 0.09 | -0.00 |

- Validation: merged beats no-shorts on Sharpe (0.69 vs 0.73) and drawdown (-7.6% vs -7.7%) -> FAIL
- Worst short loss incl. gap, validation: 0.50%; merged max drawdown full period -10.3% (limit -15%)
- Short leg with and without the Feb-Apr 2020 crash and up-year cost were reported in the train section.