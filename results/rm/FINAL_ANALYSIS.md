# Final analysis (2026-11-03): candidate "NB3" and how far to trust it

## Candidate strategy (honest spec: cut fraction 0.25, the interior pick)
Instrument: Nifty 50 futures (synthetic series from spot; real bhavcopy used for checks). Capital Rs 2 crore, lot 65, floor costs (0.025%/side, 0.05%/roll), 6% interest on idle collateral.
- Long leg x2.0: Supertrend(14,3), Wilder ATR, 15-min bars, long when green, fill at next bar open.
- Short leg x1.0 (A2): short when Supertrend red AND prior daily close < 100-day average.
- Long-leg risk-off cut (to 0.25 of size) on days when prior-US-session Nasdaq 5-day return < -2% (NQ) OR US 10-year yield rose > 15 bp in 5 days (MC3). Inputs dated strictly before the Indian open.
- Returns = linear sum of the legs' daily returns (no whole-lot / margin modelling).

## Results (CAGR / MaxDD / Sharpe, floor costs)
| Setup | 2017-23 (dev) | Validation 2022-23 | Test 2024-26 (desc.) | Full |
|---|---|---|---|---|
| Baseline long-only | 22.8% (train) / -13.4% / 1.15 | 13.3% / -7.7% / 0.73 | 10.4% / -6.6% / 0.46 | 17.0% / -13.4% / 0.90 |
| 2.0/1.0 combo (no factors) | 32.0% full / -21.2% / 1.02 | 18.0% / -21.2% / 0.62 | 21.3% / -16.0% / 0.77 | 32.0% / -21.2% / 1.02 |
| NB3, cut 0.5 | 43.3% / -14.0% / 1.52 | 26.3% / -11.3% / 1.09 | 23.7% / -14.7% / 0.92 | 37.2% / -14.7% / 1.36 |
| NB3, cut 0.25 (candidate) | 44.9% / -13.2% / 1.65 | 28.8% / -10.7% / 1.24 | see sensitivity | 38.6% / -14.2% / 1.46 |
| NB3, cut 0 (edge value, not adopted) | 45.3% / -13.0% / 1.68 | 30.3% / -10.6% / 1.31 | - | 39.3% / -13.9% / 1.50 |

## Reliability
See chat summary: the machinery is reproduced and lookahead-checked for the first frozen strategy; later layers (shorts, factors, weights, cut fraction) were selected on the same history after the test window was opened (351 distinct configurations tried, 187 of them after the first test failed).
The first frozen strategy FAILED the locked test (Sharpe -0.09 vs baseline 0.46). Treat every number above as an optimistic in-sample-ish estimate.
Scripts: scripts/rm_*.py, scripts/rm_nb3_addon_and_cut.py (run from repo root with the numba venv); decisions in results/rm/PROTOCOL_CHANGES.md.

## Update: pre-2017 out-of-sample check (2012-07..2016-08, real 1-minute data, exact frozen system, single run)
Frozen version (weights 1.91/0.96, 9-cell ensemble cut, no stops) vs plain long-only baseline, real-anchored path, floor costs: 54.4% / -10.1% / 1.95 vs 24.8% / -6.4% / 1.47 (buy-and-hold 12.6% / -22.4% / 0.45).
All four edge criteria and both risk criteria held (see PRE2017_EXACT_REPORT.md). Sharpe uplift over the baseline: +0.48 pre-2017 vs +0.61 in 2017-26, so the RELATIVE edge replicated on data the system never saw.
Limits: 4.2 years of a strong bull market, no crash year, third-party data source. This raises confidence; it does not remove the selection concern behind the 2017-26 numbers.

## CORRECTION (supersedes the factor-cut numbers above)
The Nasdaq/US-yield cuts were applied before the overnight gap, which cannot be executed. Executable results (real-anchored, floor costs): frozen 29.0% / -16.1% / 1.12 over 2017-26 (not 38.8% / -14.0% / 1.51); pre-2017 verdict PARTIAL, not SUPPORTS.
Honest candidate = leveraged long/short (Supertrend + A2 shorts), sized to the drawdown limit: ~1.42 long / 0.71 short, full 25.9% / -14.0% / 1.04 (test 17.8% / -10.3% / 0.79); the cut adds roughly nothing. See PROTOCOL_CHANGES.md (CORRECTION entry).
