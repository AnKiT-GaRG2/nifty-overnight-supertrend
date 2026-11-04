# Baseline v2 — frozen (2026-11-04)

Code hash (sha256 of rm_engine, rm_signals, rm_ideas, rm_final, rm_data, rm_lock_dev, rm_pre_exact, rm_v2next): `639f505f940d3dfa80d2b20b57a2c6b13edd51577b6006ef00cec2a19e7fd948`

Spec: long 1.912x Supertrend(14,3) Wilder ATR 15-min, held overnight; short 0.956x when Supertrend red AND prior daily close < SMA100; long leg cut to 0.25 by each of 9 Nasdaq/US10Y cells (average), applied from the open after the gap; fill at next bar open; Rs 2 crore, lot 65; collateral earns 6%.

Sharpe is computed on futures P&L after costs WITHOUT the 6% collateral interest, i.e. it is an excess-return Sharpe (risk-free already deducted). CAGR includes the interest. Interest shown as its own line.


## real costs

| Window | v2 CAGR / MaxDD / Sharpe(excess) | of which collateral interest (CAGR pts) | v2 rescaled to 1x (long 1.0 / short 0.5) | long-only x1 (with US cut) |
|---|---|---|---|---|
| train 2017-04..2021-12 | 45.6% / -14.4% / 1.62 | 8.6% | 26.0% / -7.1% / 1.62 | 23.5% / -5.9% / 1.51 |
| valid 2022-23 | 33.7% / -7.0% / 1.58 | 7.9% | 20.2% / -3.7% / 1.58 | 19.3% / -2.8% / 1.70 |
| test 2024-26 | 18.7% / -11.9% / 0.73 | 7.0% | 13.1% / -6.0% / 0.73 | 9.1% / -5.6% / 0.35 |
| FULL 2017-04..2026-10 | 34.6% / -14.4% / 1.36 | 8.0% | 20.8% / -7.1% / 1.36 | 18.2% / -5.9% / 1.21 |

Deflated Sharpe (full period, excess-return Sharpe 1.36, 620 trials, SD of trial Sharpes 0.64): expected-max Sharpe under luck SR0 = 1.99; DSR = 0.022 (probability that the true Sharpe is above SR0).

## floor costs

| Window | v2 CAGR / MaxDD / Sharpe(excess) | of which collateral interest (CAGR pts) | v2 rescaled to 1x (long 1.0 / short 0.5) | long-only x1 (with US cut) |
|---|---|---|---|---|
| train 2017-04..2021-12 | 38.3% / -16.1% / 1.37 | 8.2% | 22.7% / -7.9% / 1.37 | 20.7% / -6.6% / 1.28 |
| valid 2022-23 | 27.0% / -8.3% / 1.23 | 7.5% | 17.0% / -3.8% / 1.23 | 16.9% / -3.0% / 1.39 |
| test 2024-26 | 15.9% / -12.7% / 0.59 | 6.9% | 11.6% / -6.5% / 0.59 | 7.9% / -5.6% / 0.22 |
| FULL 2017-04..2026-10 | 29.0% / -16.1% / 1.12 | 7.6% | 18.1% / -7.9% / 1.12 | 16.0% / -6.6% / 1.00 |
