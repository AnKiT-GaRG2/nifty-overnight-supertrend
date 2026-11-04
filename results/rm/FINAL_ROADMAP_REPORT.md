# Executive summary (added after the run; numbers below are copied from the sections that follow)

**Verdict: NO-GO.** The six-phase roadmap was implemented end to end (data pipeline, engine, baseline reproduction, protocol, 17 ideas / 127 configurations, risk layer, locked test).

- **Baseline reproduced** within the roadmap's tolerance: 17.0% CAGR / -13.4% MaxDD / 0.90 Sharpe over Apr 2017-Oct 2026 (paper: 17.1% / -12.8% / 0.94) and recent-regime Sharpe 0.57 (paper 0.56). It only reproduces with floor costs + 6% interest on collateral + Sharpe on excess return, which is the yardstick used throughout.
- **Phase 3**: of 17 ideas only the VIX-percentile filter (stand aside when prior-day VIX 252-day percentile > 80) passed train and validation. Shorts, daily-trend agreement, chop filters, intraday-only, opening range, gaps, RSI mean reversion, OI and US-overnight ideas all failed train or validation. Gate G3 (2-3 ideas from 2 families) was **not met**.
- **Frozen spec**: baseline Supertrend + VIX filter (p=80) + stop/risk sizing k=2.5 (0.75% of capital per trade); vol targeting, overnight cap, drawdown brake and daily loss limit did not earn a place.
- **Locked test (Jan 2024-Oct 2026)**: strategy 5.5% CAGR / -8.7% MaxDD / **-0.09 Sharpe** vs baseline 10.4% / -6.6% / **0.46** (floor costs); with realistic costs 0.09 vs 0.62. Buy-and-hold futures: 2.8% CAGR, -14.6% MaxDD, Sharpe -0.20 (synthetic). The 95% bootstrap CI for the Sharpe difference vs baseline is [-1.45, +0.04]. Pass criteria failed on 6 of 8 lines.
- **What did hold**: no lookahead (truncation, shuffled-future and extra-delay tests), per-trade loss at the stop <= 0.75% of capital (gaps through the stop reach 1.9%), no calendar year below -3.3%, drawdown on train/validation far better than the baseline's.
- **Caveats that matter**: the synthetic futures series is built from spot, whose 09:15 print differs from real futures (section 8: synthetic nights earn more and days less than real futures); a real-futures-anchored path (section 8b) gives the same ranking. Test-window Sharpe has ~0.6 standard error, PBO 49%, 127 configurations tried.

---

# Final report: Nifty 50 futures strategy research roadmap (generated 2026-11-03)

Frozen spec (`results/rm/FROZEN_SPEC.json`, sha256 `196112ad5cbf98ae...`): Supertrend(14,3) Wilder ATR 15-min spot, long-only, stand aside when prior-day India VIX 252d percentile > 80 (B2h); stop k=2.5 x ATR(15-min), lots = min(full, floor(0.0075 x Rs2cr / (k x ATR x 65))); no vol targeting / overnight cap / drawdown brake / daily loss limit (each failed to earn its place on train). Dataset sha256 `b6ca337fe078228d...`.

## 1. Results by window (floor costs = mandate yardstick; total return incl. 6% interest on collateral, Sharpe on excess return)

### Mandate floor costs (0.025%/side, 0.05%/roll)

|  | CAGR | MaxDD | Sharpe | Sortino | Calmar | Vol | TradesPerYr | WinRate | AvgWin/AvgLoss | TimeInMkt | CostDrag%/yr | LongLegCAGR | ShortLegCAGR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Train 2017-04..2021-12 — strategy | 19.3% | -6.2% | 1.68 | 2.95 | 3.11 | 7.1% | 67.24 | 43.1% | 2.19 | 40.7% | 3.44 | 11.4% | 0.0% |
| Train 2017-04..2021-12 — baseline | 22.8% | -13.4% | 1.15 | 1.84 | 1.71 | 13.3% | 87.22 | 43.3% | 1.96 | 56.7% | 4.65 | 15.0% | 0.0% |
| Validate 2022-01..2023-12 — strategy | 10.7% | -5.5% | 0.60 | 0.93 | 1.94 | 7.2% | 88.61 | 37.6% | 2.06 | 41.8% | 4.44 | 5.2% | 0.0% |
| Validate 2022-01..2023-12 — baseline | 13.3% | -7.7% | 0.73 | 1.13 | 1.74 | 9.2% | 100.39 | 41.3% | 1.78 | 54.0% | 5.20 | 7.7% | 0.0% |
| TEST 2024-01..2026-10 (locked, opened once) — strategy | 5.5% | -8.7% | -0.09 | -0.15 | 0.64 | 5.9% | 65.69 | 31.1% | 2.09 | 33.2% | 3.36 | -1.0% | 0.0% |
| TEST 2024-01..2026-10 (locked, opened once) — baseline | 10.4% | -6.6% | 0.46 | 0.72 | 1.58 | 9.2% | 86.15 | 36.7% | 1.99 | 52.9% | 4.46 | 3.8% | 0.0% |
| Recent 2022-01..2026-10 — strategy | 7.6% | -8.7% | 0.23 | 0.35 | 0.88 | 6.5% | 75.14 | 34.3% | 2.07 | 36.7% | 3.81 | 1.6% | 0.0% |
| Recent 2022-01..2026-10 — baseline | 11.6% | -7.7% | 0.57 | 0.89 | 1.52 | 9.2% | 92.02 | 38.8% | 1.89 | 53.4% | 4.77 | 5.4% | 0.0% |
| Full 2017-04..2026-10 — strategy | 13.3% | -8.7% | 0.98 | 1.62 | 1.53 | 6.8% | 71.22 | 38.4% | 2.17 | 38.7% | 3.63 | 6.5% | 0.0% |
| Full 2017-04..2026-10 — baseline | 17.0% | -13.4% | 0.90 | 1.42 | 1.27 | 11.4% | 89.64 | 41.0% | 1.95 | 55.0% | 4.71 | 10.1% | 0.0% |

### Realistic costs (dated STT, brokerage, exchange, SEBI, stamp, GST, 1 tick; roll = 2 legs + spread)

|  | CAGR | MaxDD | Sharpe | Sortino | Calmar | Vol | TradesPerYr | WinRate | AvgWin/AvgLoss | TimeInMkt | CostDrag%/yr | LongLegCAGR | ShortLegCAGR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Train 2017-04..2021-12 — strategy | 21.8% | -5.9% | 1.98 | 3.58 | 3.71 | 7.0% | 67.24 | 44.1% | 2.33 | 40.7% | 1.40 | 13.5% | 0.0% |
| Train 2017-04..2021-12 — baseline | 26.2% | -12.8% | 1.36 | 2.20 | 2.05 | 13.3% | 87.22 | 43.8% | 2.08 | 56.7% | 1.90 | 17.7% | 0.0% |
| Validate 2022-01..2023-12 — strategy | 13.6% | -4.0% | 0.98 | 1.54 | 3.44 | 7.1% | 88.61 | 40.5% | 2.04 | 41.8% | 1.86 | 7.8% | 0.0% |
| Validate 2022-01..2023-12 — baseline | 16.8% | -5.7% | 1.07 | 1.68 | 2.93 | 9.2% | 100.39 | 44.4% | 1.73 | 54.0% | 2.18 | 10.7% | 0.0% |
| TEST 2024-01..2026-10 (locked, opened once) — strategy | 6.7% | -7.6% | 0.09 | 0.14 | 0.87 | 5.9% | 65.69 | 31.1% | 2.22 | 33.2% | 2.30 | 0.1% | 0.0% |
| TEST 2024-01..2026-10 (locked, opened once) — baseline | 12.0% | -6.3% | 0.62 | 0.96 | 1.91 | 9.2% | 86.15 | 37.1% | 2.06 | 52.9% | 3.03 | 5.2% | 0.0% |
| Recent 2022-01..2026-10 — strategy | 9.5% | -7.6% | 0.49 | 0.78 | 1.24 | 6.4% | 75.14 | 35.7% | 2.12 | 36.7% | 2.12 | 3.3% | 0.0% |
| Recent 2022-01..2026-10 — baseline | 14.0% | -6.3% | 0.80 | 1.26 | 2.21 | 9.2% | 92.02 | 40.4% | 1.90 | 53.4% | 2.68 | 7.5% | 0.0% |
| Full 2017-04..2026-10 — strategy | 15.4% | -7.6% | 1.26 | 2.13 | 2.03 | 6.7% | 71.22 | 39.6% | 2.26 | 38.7% | 1.76 | 8.3% | 0.0% |
| Full 2017-04..2026-10 — baseline | 19.9% | -12.8% | 1.11 | 1.78 | 1.55 | 11.4% | 89.64 | 42.0% | 2.01 | 55.0% | 2.30 | 12.5% | 0.0% |

### Floor costs, WITHOUT interest on idle collateral (pure futures P&L; long pays the basis)

|  | CAGR | MaxDD | Sharpe | Sortino | Calmar | Vol | TradesPerYr | WinRate | AvgWin/AvgLoss | TimeInMkt | CostDrag%/yr | LongLegCAGR | ShortLegCAGR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Train 2017-04..2021-12 — strategy | 12.3% | -7.0% | 1.68 | 2.95 | 1.75 | 7.0% | 67.24 | 43.1% | 2.19 | 40.7% | 3.44 | 11.4% | 0.0% |
| Train 2017-04..2021-12 — baseline | 15.5% | -14.7% | 1.15 | 1.84 | 1.06 | 13.3% | 87.22 | 43.3% | 1.96 | 56.7% | 4.65 | 15.0% | 0.0% |
| Validate 2022-01..2023-12 — strategy | 4.2% | -9.3% | 0.60 | 0.93 | 0.45 | 7.2% | 88.61 | 37.6% | 2.06 | 41.8% | 4.44 | 5.2% | 0.0% |
| Validate 2022-01..2023-12 — baseline | 6.6% | -11.0% | 0.73 | 1.13 | 0.60 | 9.2% | 100.39 | 41.3% | 1.78 | 54.0% | 5.20 | 7.7% | 0.0% |
| TEST 2024-01..2026-10 (locked, opened once) — strategy | -0.7% | -13.5% | -0.09 | -0.15 | -0.05 | 5.9% | 65.69 | 31.1% | 2.09 | 33.2% | 3.36 | -1.0% | 0.0% |
| TEST 2024-01..2026-10 (locked, opened once) — baseline | 3.9% | -8.2% | 0.46 | 0.72 | 0.48 | 9.2% | 86.15 | 36.7% | 1.99 | 52.9% | 4.46 | 3.8% | 0.0% |
| Recent 2022-01..2026-10 — strategy | 1.3% | -13.5% | 0.23 | 0.35 | 0.09 | 6.4% | 75.14 | 34.3% | 2.07 | 36.7% | 3.81 | 1.6% | 0.0% |
| Recent 2022-01..2026-10 — baseline | 5.0% | -11.0% | 0.57 | 0.89 | 0.45 | 9.2% | 92.02 | 38.8% | 1.89 | 53.4% | 4.77 | 5.4% | 0.0% |
| Full 2017-04..2026-10 — strategy | 6.6% | -13.5% | 0.98 | 1.62 | 0.49 | 6.8% | 71.22 | 38.4% | 2.17 | 38.7% | 3.63 | 6.5% | 0.0% |
| Full 2017-04..2026-10 — baseline | 10.1% | -14.7% | 0.90 | 1.42 | 0.69 | 11.4% | 89.64 | 41.0% | 1.95 | 55.0% | 4.71 | 10.1% | 0.0% |

## 2. Calendar years (total return, floor costs unless stated; 2026 = Jan-Oct)

|  | strategy | baseline | strategy (real cost) | baseline (real cost) |
|---|---|---|---|---|
| 2017 | 8.3% | 5.5% | 10.0% | 7.8% |
| 2018 | 10.0% | 10.5% | 11.7% | 13.6% |
| 2019 | 13.6% | 14.9% | 16.3% | 18.1% |
| 2020 | 27.8% | 39.7% | 30.2% | 43.6% |
| 2021 | 31.7% | 39.1% | 34.7% | 42.5% |
| 2022 | 11.1% | 10.0% | 13.8% | 13.6% |
| 2023 | 9.8% | 16.0% | 12.8% | 19.2% |
| 2024 | -3.3% | 7.7% | -1.7% | 10.3% |
| 2025 | 14.7% | 14.7% | 16.4% | 16.6% |
| 2026 | 4.7% | 6.8% | 4.6% | 6.6% |

## 3. Rolling walk-forward (3y train, 6m OOS, 6m step; parameters re-picked per fold by the plateau rule; OOS stitched; run once)

|  | CAGR | MaxDD | Sharpe | Sortino | Calmar | Vol | TradesPerYr | WinRate | AvgWin/AvgLoss | TimeInMkt | CostDrag%/yr | LongLegCAGR | ShortLegCAGR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| strategy WF | 14.5% | -6.2% | 1.12 | 1.87 | 2.34 | 6.9% | nan | na | nan | na | nan | na | na |
| baseline WF | 20.8% | -7.7% | 1.29 | 2.12 | 2.72 | 10.3% | nan | na | nan | na | nan | na | na |

|  | train | p | k | train_sharpe |
|---|---|---|---|---|
| 2020-04-01..2020-09-30 | 2017-04-01..2020-03-31 | 80 | 2.50 | 0.73 |
| 2020-10-01..2021-03-31 | 2017-10-01..2020-09-30 | 80 | 2.50 | 1.16 |
| 2021-04-01..2021-09-30 | 2018-04-01..2021-03-31 | 80 | 2.50 | 1.67 |
| 2021-10-01..2022-03-31 | 2018-10-01..2021-09-30 | 80 | 2.50 | 1.98 |
| 2022-04-01..2022-09-30 | 2019-04-01..2022-03-31 | 80 | 2.50 | 1.99 |
| 2022-10-01..2023-03-31 | 2019-10-01..2022-09-30 | 80 | 2.50 | 2.02 |
| 2023-04-01..2023-09-30 | 2020-04-01..2023-03-31 | 80 | 2.50 | 1.77 |
| 2023-10-01..2024-03-31 | 2020-10-01..2023-09-30 | 80 | 2.50 | 1.51 |
| 2024-04-01..2024-09-30 | 2021-04-01..2024-03-31 | 70 | 2.50 | 1.05 |
| 2024-10-01..2025-03-31 | 2021-10-01..2024-09-30 | 70 | 2.50 | 0.16 |
| 2025-04-01..2025-09-30 | 2022-04-01..2025-03-31 | 70 | 2.50 | -0.16 |
| 2025-10-01..2026-03-31 | 2022-10-01..2025-09-30 | 70 | 2.50 | -0.10 |
| 2026-04-01..2026-09-30 | 2023-04-01..2026-03-31 | 70 | 2.50 | 0.63 |
| 2026-10-01..2026-10-31 | 2023-10-01..2026-09-30 | 70 | 2.50 | 0.31 |

## 4. Stress tests on the test window (reported, never used to pick parameters)

|  | CAGR | MaxDD | Sharpe | Sortino | Calmar | Vol | TradesPerYr | WinRate | AvgWin/AvgLoss | TimeInMkt | CostDrag%/yr | LongLegCAGR | ShortLegCAGR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| strategy, floor | 5.5% | -8.7% | -0.09 | -0.15 | 0.64 | 5.9% | 65.69 | 31.1% | 2.09 | 33.2% | 3.36 | -1.0% | 0.0% |
| baseline, floor | 10.4% | -6.6% | 0.46 | 0.72 | 1.58 | 9.2% | 86.15 | 36.7% | 1.99 | 52.9% | 4.46 | 3.8% | 0.0% |
| strategy, costs x2 (floor) | 2.0% | -11.3% | -0.65 | -0.98 | 0.18 | 6.0% | 65.69 | 30.1% | 1.83 | 33.2% | 6.73 | -4.3% | 0.0% |
| baseline, costs x2 (floor) | 5.6% | -7.5% | -0.02 | -0.04 | 0.75 | 9.3% | 86.15 | 34.6% | 1.85 | 52.9% | 8.93 | -0.6% | 0.0% |
| strategy, costs x2 (real) | 4.2% | -8.8% | -0.30 | -0.46 | 0.48 | 6.0% | 65.69 | 30.6% | 2.00 | 33.2% | 4.60 | -2.2% | 0.0% |
| baseline, costs x2 (real) | 8.7% | -6.8% | 0.28 | 0.43 | 1.28 | 9.3% | 86.15 | 35.4% | 1.98 | 52.9% | 6.07 | 2.2% | 0.0% |
| strategy, fill 1 bar later | 1.3% | -6.9% | -0.80 | -1.16 | 0.19 | 5.8% | 88.31 | 29.3% | 1.82 | 33.6% | 4.57 | -5.1% | 0.0% |
| baseline, fill 1 bar later | 9.3% | -6.3% | 0.36 | 0.56 | 1.49 | 9.0% | 86.15 | 35.4% | 2.01 | 52.9% | 4.48 | 2.7% | 0.0% |
| strategy, best 10 trades removed | -3.1% | -13.0% | -1.14 | -1.40 | -0.24 | 7.8% | nan | na | nan | na | nan | na | na |
| param neighbour p=70, k=2.5 | 5.8% | -4.6% | -0.06 | -0.10 | 1.26 | 5.1% | 54.56 | 32.2% | 2.05 | 27.1% | 2.78 | -0.3% | 0.0% |
| param neighbour p=90, k=2.5 | 3.9% | -11.3% | -0.31 | -0.48 | 0.35 | 6.6% | 78.97 | 31.8% | 1.90 | 39.3% | 4.05 | -2.5% | 0.0% |
| param neighbour p=80, k=2.0 | 4.0% | -6.9% | -0.37 | -0.58 | 0.57 | 5.6% | 66.05 | 28.8% | 2.16 | 30.2% | 3.38 | -2.1% | 0.0% |
| param neighbour p=80, k=3.0 | 6.1% | -5.3% | -0.00 | -0.01 | 1.15 | 6.0% | 65.69 | 32.8% | 2.00 | 35.2% | 3.32 | -0.4% | 0.0% |
| param neighbour p=70, k=2.0 | 4.8% | -4.2% | -0.27 | -0.43 | 1.13 | 4.8% | 54.56 | 29.6% | 2.14 | 24.6% | 2.79 | -1.3% | 0.0% |
| param neighbour p=90, k=3.0 | 4.1% | -8.2% | -0.28 | -0.43 | 0.50 | 6.7% | 78.97 | 33.2% | 1.81 | 41.4% | 3.99 | -2.3% | 0.0% |

Best 10 trades: Rs 4,664,786 of net trade P&L vs Rs -546,230 for all 183 test-window trades (positive net total = the best 10 are most of the profit; negative = they were offsetting losses).

Long and short legs separately (strategy is long-only by design; the symmetric-short version A1 failed validation): strategy test long-leg CAGR -1.0%, short-leg CAGR 0.0%; baseline long-leg 3.8%.

## 5. Stops, gaps and the per-trade loss cap

- Full period: 236 stop-outs out of 669 trades. Max loss at the stop price 0.75% of capital (cap 0.75%, hard limit 1%); max loss at the actual fill (gaps through the stop included) 1.89%.
- Test window: max loss at stop 0.74%; with gaps 1.89%; stop-outs with fill loss > 1% of capital (gap-driven): 5 (all windows).
- Train gap study: 39 of 1173 sessions (3.3%) opened more than 1% below the prior close (worst -9.2%); a gap of that size at full size costs more than 1% of capital. The overnight cap (8 lots) was tested and dropped on train (Sharpe collapsed because the overnight leg carries the return); the intraday-only variant D1 failed train (Sharpe -0.71).

## 6. Statistics

- 20-day block bootstrap (4000 draws), Sharpe(strategy) - Sharpe(baseline), test 2024-01..2026-10: median -0.63, 95% CI [-1.45, +0.04] (CI includes 0: not distinguishable)
- 20-day block bootstrap (4000 draws), Sharpe(strategy) - Sharpe(baseline), recent 2022-01..2026-10: median -0.42, 95% CI [-1.01, +0.13] (CI includes 0: not distinguishable)
- Configurations tried (unique idea x parameter cells, all phases): **127**. Deflated Sharpe Ratio on the test window: SR -0.09 annualised vs the expected best-of-127-noise SR0 1.81; DSR (probability the true Sharpe > 0 after deflation) = 0.00.
- Probability of Backtest Overfitting (CSCV, 10 partitions, 96 candidate configs, 2017-04..2023-12): **49%**.

## 7. Lookahead tests

- cut 2025-01-16: truncation (strategy signals) identical; truncation (baseline) identical; shuffled-future signals before cut identical; shuffled-future daily P&L before cut identical
- cut 2023-07-17: truncation (strategy signals) identical; truncation (baseline) identical; shuffled-future signals before cut identical; shuffled-future daily P&L before cut identical
- cut 2022-08-29: truncation (strategy signals) identical; truncation (baseline) identical; shuffled-future signals before cut identical; shuffled-future daily P&L before cut identical
- Extra delay (fill one bar later), test window: strategy Sharpe -0.09 -> -0.80; baseline 0.46 -> 0.36 (large collapse would mean the edge lives in the fill bar).

## 8. Synthetic series vs real NSE futures (daily bhavcopy): is the overnight edge real?

- train: mean night return real futures +2.7 bp vs synthetic +14.0 bp; mean day return real +2.0 bp vs synthetic -9.9 bp (n=1170)
- validate: mean night return real futures +1.3 bp vs synthetic +5.8 bp; mean day return real +1.5 bp vs synthetic -3.1 bp (n=467)
- test: mean night return real futures +0.7 bp vs synthetic +2.3 bp; mean day return real -2.2 bp vs synthetic -3.0 bp (n=682)
- Correlation night real vs synthetic 0.94, day 0.96. The synthetic series inherits the spot index's 09:15 "open"; if the night-leg means differ, overnight-heavy results (this strategy holds mostly overnight) are overstated on the synthetic series. Intraday real futures bars are not in the data, so this cannot be corrected here.

## 8b. Robustness: same signals on a REAL-futures-anchored price path (each session's open and close pinned to the actual NSE futures open/close; coverage 98% of sessions)

Signals are unchanged (spot). Only the P&L path changes, so overnight gaps equal real futures gaps. Not a gating test (the protocol's official yardstick is the synthetic series), but it shows how much of the result depends on the spot-open artefact.

|  | CAGR | MaxDD | Sharpe | Sortino | Calmar | Vol | TradesPerYr | WinRate | AvgWin/AvgLoss | TimeInMkt | CostDrag%/yr | LongLegCAGR | ShortLegCAGR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Train 2017-04..2021-12 — strategy | 19.7% | -5.8% | 1.65 | 2.90 | 3.39 | 7.4% | 67.24 | 42.8% | 2.23 | 40.0% | 3.44 | 11.8% | 0.0% |
| Train 2017-04..2021-12 — baseline | 23.1% | -15.6% | 1.11 | 1.77 | 1.48 | 14.0% | 87.22 | 43.1% | 1.97 | 56.7% | 4.65 | 15.2% | 0.0% |
| Train 2017-04..2021-12 — buy & hold futures | 18.7% | -33.9% | 0.70 | 0.99 | 0.55 | 18.0% | 0.00 | na | nan | 99.9% | 0.63 | na | na |
| Validate 2022-01..2023-12 — strategy | 12.6% | -3.9% | 0.81 | 1.27 | 3.22 | 7.4% | 88.61 | 37.6% | 2.20 | 41.0% | 4.46 | 6.9% | 0.0% |
| Validate 2022-01..2023-12 — baseline | 16.5% | -5.7% | 1.01 | 1.58 | 2.88 | 9.5% | 100.39 | 43.4% | 1.76 | 54.0% | 5.21 | 10.5% | 0.0% |
| Validate 2022-01..2023-12 — buy & hold futures | 13.0% | -15.3% | 0.51 | 0.71 | 0.85 | 13.8% | 0.00 | na | nan | 100.0% | 0.61 | na | na |
| TEST 2024-01..2026-10 (locked, opened once) — strategy | 4.8% | -7.5% | -0.22 | -0.34 | 0.63 | 5.8% | 65.69 | 36.6% | 1.56 | 32.8% | 3.36 | -1.7% | 0.0% |
| TEST 2024-01..2026-10 (locked, opened once) — baseline | 10.6% | -6.4% | 0.47 | 0.71 | 1.67 | 9.5% | 86.15 | 42.5% | 1.57 | 52.9% | 4.47 | 4.0% | 0.0% |
| TEST 2024-01..2026-10 (locked, opened once) — buy & hold futures | 1.0% | -15.8% | -0.33 | -0.45 | 0.06 | 12.9% | 0.00 | na | nan | 99.7% | 0.61 | na | na |
| Recent 2022-01..2026-10 — strategy | 7.9% | -7.5% | 0.26 | 0.41 | 1.05 | 6.5% | 75.14 | 37.1% | 1.86 | 36.2% | 3.82 | 1.8% | 0.0% |
| Recent 2022-01..2026-10 — baseline | 13.0% | -6.4% | 0.69 | 1.07 | 2.04 | 9.5% | 92.02 | 42.9% | 1.66 | 53.4% | 4.77 | 6.7% | 0.0% |
| Recent 2022-01..2026-10 — buy & hold futures | 5.8% | -15.8% | 0.03 | 0.04 | 0.37 | 13.3% | 0.00 | na | nan | 99.8% | 0.61 | na | na |
| Full 2017-04..2026-10 — strategy | 13.6% | -7.5% | 0.99 | 1.65 | 1.80 | 7.0% | 71.22 | 39.8% | 2.07 | 38.1% | 3.63 | 6.8% | 0.0% |
| Full 2017-04..2026-10 — baseline | 17.9% | -15.6% | 0.92 | 1.45 | 1.15 | 12.0% | 89.64 | 43.0% | 1.82 | 55.0% | 4.71 | 10.9% | 0.0% |
| Full 2017-04..2026-10 — buy & hold futures | 12.0% | -33.9% | 0.41 | 0.57 | 0.35 | 15.8% | 0.00 | na | nan | 99.9% | 0.62 | na | na |

### Comparison with simply holding Nifty futures (1x, always long, rolled; same costs, same interest convention)

|  | CAGR | MaxDD | Sharpe | Sortino | Calmar | Vol | TradesPerYr | WinRate | AvgWin/AvgLoss | TimeInMkt | CostDrag%/yr | LongLegCAGR | ShortLegCAGR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Train 2017-04..2021-12 — buy & hold (synthetic) | 17.1% | -33.7% | 0.63 | 0.88 | 0.51 | 17.7% | 0.00 | na | nan | 99.9% | 0.63 | na | na |
| Train 2017-04..2021-12 — strategy (synthetic) | 19.3% | -6.2% | 1.68 | 2.95 | 3.11 | 7.1% | 67.24 | 43.1% | 2.19 | 40.7% | 3.44 | 11.4% | 0.0% |
| Validate 2022-01..2023-12 — buy & hold (synthetic) | 12.8% | -16.0% | 0.50 | 0.69 | 0.80 | 13.8% | 0.00 | na | nan | 100.0% | 0.61 | na | na |
| Validate 2022-01..2023-12 — strategy (synthetic) | 10.7% | -5.5% | 0.60 | 0.93 | 1.94 | 7.2% | 88.61 | 37.6% | 2.06 | 41.8% | 4.44 | 5.2% | 0.0% |
| TEST 2024-01..2026-10 (locked, opened once) — buy & hold (synthetic) | 2.8% | -14.6% | -0.20 | -0.28 | 0.19 | 12.7% | 0.00 | na | nan | 99.7% | 0.61 | na | na |
| TEST 2024-01..2026-10 (locked, opened once) — strategy (synthetic) | 5.5% | -8.7% | -0.09 | -0.15 | 0.64 | 5.9% | 65.69 | 31.1% | 2.09 | 33.2% | 3.36 | -1.0% | 0.0% |
| Recent 2022-01..2026-10 — buy & hold (synthetic) | 6.8% | -16.0% | 0.10 | 0.14 | 0.42 | 13.1% | 0.00 | na | nan | 99.8% | 0.61 | na | na |
| Recent 2022-01..2026-10 — strategy (synthetic) | 7.6% | -8.7% | 0.23 | 0.35 | 0.88 | 6.5% | 75.14 | 34.3% | 2.07 | 36.7% | 3.81 | 1.6% | 0.0% |
| Full 2017-04..2026-10 — buy & hold (synthetic) | 11.8% | -33.7% | 0.40 | 0.55 | 0.35 | 15.6% | 0.00 | na | nan | 99.9% | 0.62 | na | na |
| Full 2017-04..2026-10 — strategy (synthetic) | 13.3% | -8.7% | 0.98 | 1.62 | 1.53 | 6.8% | 71.22 | 38.4% | 2.17 | 38.7% | 3.63 | 6.5% | 0.0% |

### Regime-wise results inside train / validate / test (annualised return contribution and Sharpe of futures P&L after floor costs; regimes from prior-day data)

|  | days | ann_return | ann_sharpe |
|---|---|---|---|
| Train 2017-04..2021-12 — all days — strategy | 1173 | 11.8% | 1.68 |
| Train 2017-04..2021-12 — all days — baseline | 1173 | 15.3% | 1.15 |
| Train 2017-04..2021-12 — all days — buy&hold | 1173 | 11.2% | 0.63 |
| Train 2017-04..2021-12 — uptrend (>200DMA) — strategy | 763 | 8.2% | 1.70 |
| Train 2017-04..2021-12 — uptrend (>200DMA) — baseline | 763 | 9.3% | 1.51 |
| Train 2017-04..2021-12 — uptrend (>200DMA) — buy&hold | 763 | 4.3% | 0.48 |
| Train 2017-04..2021-12 — downtrend (<200DMA) — strategy | 410 | 3.6% | 1.64 |
| Train 2017-04..2021-12 — downtrend (<200DMA) — baseline | 410 | 6.1% | 0.94 |
| Train 2017-04..2021-12 — downtrend (<200DMA) — buy&hold | 410 | 6.9% | 0.85 |
| Train 2017-04..2021-12 — high VIX (pct>80) — strategy | 285 | 0.0% | 0.32 |
| Train 2017-04..2021-12 — high VIX (pct>80) — baseline | 285 | 1.4% | 0.28 |
| Train 2017-04..2021-12 — high VIX (pct>80) — buy&hold | 285 | -3.9% | -0.61 |
| Train 2017-04..2021-12 — normal VIX — strategy | 888 | 11.8% | 1.93 |
| Train 2017-04..2021-12 — normal VIX — baseline | 888 | 13.9% | 1.93 |
| Train 2017-04..2021-12 — normal VIX — buy&hold | 888 | 15.2% | 1.46 |
| Validate 2022-01..2023-12 — all days — strategy | 492 | 4.3% | 0.60 |
| Validate 2022-01..2023-12 — all days — baseline | 492 | 6.8% | 0.73 |
| Validate 2022-01..2023-12 — all days — buy&hold | 492 | 6.8% | 0.50 |
| Validate 2022-01..2023-12 — uptrend (>200DMA) — strategy | 386 | 2.2% | 0.40 |
| Validate 2022-01..2023-12 — uptrend (>200DMA) — baseline | 386 | 3.4% | 0.55 |
| Validate 2022-01..2023-12 — uptrend (>200DMA) — buy&hold | 386 | -1.5% | -0.16 |
| Validate 2022-01..2023-12 — downtrend (<200DMA) — strategy | 106 | 2.1% | 1.26 |
| Validate 2022-01..2023-12 — downtrend (<200DMA) — baseline | 106 | 3.4% | 1.21 |
| Validate 2022-01..2023-12 — downtrend (<200DMA) — buy&hold | 106 | 8.4% | 2.17 |
| Validate 2022-01..2023-12 — high VIX (pct>80) — strategy | 62 | 0.5% | 2.64 |
| Validate 2022-01..2023-12 — high VIX (pct>80) — baseline | 62 | 2.8% | 1.67 |
| Validate 2022-01..2023-12 — high VIX (pct>80) — buy&hold | 62 | 4.6% | 1.68 |
| Validate 2022-01..2023-12 — normal VIX — strategy | 430 | 3.8% | 0.57 |
| Validate 2022-01..2023-12 — normal VIX — baseline | 430 | 3.9% | 0.53 |
| Validate 2022-01..2023-12 — normal VIX — buy&hold | 430 | 2.3% | 0.21 |
| TEST 2024-01..2026-10 (locked, opened once) — all days — strategy | 702 | -0.6% | -0.09 |
| TEST 2024-01..2026-10 (locked, opened once) — all days — baseline | 702 | 4.2% | 0.46 |
| TEST 2024-01..2026-10 (locked, opened once) — all days — buy&hold | 702 | -2.6% | -0.20 |
| TEST 2024-01..2026-10 (locked, opened once) — uptrend (>200DMA) — strategy | 452 | -2.2% | -0.67 |
| TEST 2024-01..2026-10 (locked, opened once) — uptrend (>200DMA) — baseline | 452 | -0.3% | -0.05 |
| TEST 2024-01..2026-10 (locked, opened once) — uptrend (>200DMA) — buy&hold | 452 | -3.2% | -0.44 |
| TEST 2024-01..2026-10 (locked, opened once) — downtrend (<200DMA) — strategy | 250 | 1.6% | 0.65 |
| TEST 2024-01..2026-10 (locked, opened once) — downtrend (<200DMA) — baseline | 250 | 4.5% | 1.16 |
| TEST 2024-01..2026-10 (locked, opened once) — downtrend (<200DMA) — buy&hold | 250 | 0.6% | 0.12 |
| TEST 2024-01..2026-10 (locked, opened once) — high VIX (pct>80) — strategy | 180 | -0.6% | -0.88 |
| TEST 2024-01..2026-10 (locked, opened once) — high VIX (pct>80) — baseline | 180 | 3.7% | 1.07 |
| TEST 2024-01..2026-10 (locked, opened once) — high VIX (pct>80) — buy&hold | 180 | 5.7% | 1.29 |
| TEST 2024-01..2026-10 (locked, opened once) — normal VIX — strategy | 522 | -0.0% | -0.00 |
| TEST 2024-01..2026-10 (locked, opened once) — normal VIX — baseline | 522 | 0.5% | 0.10 |
| TEST 2024-01..2026-10 (locked, opened once) — normal VIX — buy&hold | 522 | -8.2% | -1.04 |

- H1 (OI x price, prior-day data, n=1) on train, all days: Sharpe 0.40, MaxDD -18.3%, CAGR 12.3%
- H1 (OI x price, prior-day data, n=1) on train, excluding sessions within 3 days of expiry: Sharpe 0.25, MaxDD -19.4%, CAGR 9.3%
- OI lookahead: OI is published after the close, so day d uses only day d-1 OI (signal shifted one day in `Sig.H1`); H1 is not part of the frozen strategy.


## 9. Pass criteria (all must hold) and roadmap targets

| Criterion | Result | Detail |
|---|---|---|
| Sharpe above baseline on test (floor) | FAIL | -0.09 vs 0.46 |
| Sharpe above baseline on 2022-01..2026-10 (floor) | FAIL | 0.23 vs 0.57 |
| Sharpe above baseline on test (realistic costs) | FAIL | 0.09 vs 0.62 |
| MaxDD better than -15% on every window and better than the baseline's | FAIL | train: -6.2% vs -13.4%; valid: -5.5% vs -7.7%; test: -8.7% vs -6.6%; recent: -8.7% vs -7.7%; full: -8.7% vs -13.4% |
| Walk-forward Sharpe above baseline's, drawdown better than -15% | FAIL | Sharpe 1.12 vs 1.29; MaxDD -6.2% (baseline -7.7%) |
| No calendar year worse than -10% | PASS | worst -3.3% (2024) |
| Still beats the baseline with doubled costs (test, floor and real) | FAIL | floor x2: -0.65 vs -0.02; real x2: -0.30 vs 0.28 |
| No trade lost more than 1% of capital at its stop (gaps reported separately) | PASS | max 0.75% at the stop; 1.89% incl. gaps |

Roadmap targets (floor costs):

| Target | Met? | Value |
|---|---|---|
| Sharpe Apr 2017-Oct 2026 >= 1.0 | no | 0.98 (baseline 0.90) |
| Sharpe Jan 2022-Oct 2026 >= 0.8 | no | 0.23 (baseline 0.57) |
| Max drawdown better than -12% (hard limit -15%) | yes | -8.7% (baseline -13.4%) |
| Walk-forward CAGR >= 15% and MaxDD better than -15% | no | CAGR 14.5%, MaxDD -6.2% (baseline 20.8% / -7.7%) |
| Sharpe on locked test above baseline | no | -0.09 vs 0.46 |
| Loss per trade at the stop <= 0.75% (cap 1%) | yes | 0.75% |

## 10. Gate G5 verdict: **NO-GO: not all pass criteria hold**

On the real-anchored path (section 8b) the test-window Sharpe is -0.22 for the strategy vs 0.47 for the baseline and -0.33 for buy-and-hold futures; full-period 0.99 / 0.92 / 0.41.

Honest limits: (i) Gate G3 not met (only one idea validated); (ii) prices are synthetic futures from spot, and section 8 quantifies how the overnight leg differs from real futures; (iii) the test window's Sharpe has a standard error near 0.6, so no single number proves superiority; (iv) earlier work in this repo had already looked at 2024-26 for other strategies; (v) two implementation corrections were made after the first validation looks (PROTOCOL_CHANGES.md).