# Pre-2017 out-of-sample check (daily-bar proxy on REAL NSE futures prices)

Data: real futures daily bars 2007-06-01..2026-11-02 (4762 sessions); continuous front-month, roll 2 trading days before expiry.

## Calibration of the daily Supertrend proxy on DEV only (2017-04..2023-12): corr of long-only daily excess returns with the real 15-min baseline, entries/yr

| n | m | corr with real baseline | entries/yr | proxy dev Sharpe |
|---|---|---|---|---|
| 3 | 0.25 | 0.49 | 36 | 0.58 |
| 2 | 0.25 | 0.49 | 36 | 0.55 |
| 14 | 0.25 | 0.49 | 36 | 0.58 |
| 7 | 0.25 | 0.49 | 35 | 0.57 |
| 10 | 0.25 | 0.49 | 35 | 0.61 |
| 5 | 0.25 | 0.49 | 36 | 0.51 |
| 10 | 0.5 | 0.47 | 26 | 0.80 |
| 14 | 0.5 | 0.47 | 26 | 0.78 |

No grid cell has 60-120 entries/yr: check INCONCLUSIVE.