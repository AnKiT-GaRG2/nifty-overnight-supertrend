# Pre-2017 check v2: the exact frozen system on real 1-minute data, 2012-2016

Data: 430,888 real 1-minute bars, 1154 sessions 2012-01-02..2016-08-31; real-open/close coverage of sessions for the anchored path: 99%. Evaluation window 2012-07-02..2016-08-31 (SMA100 warm-up before).


## REAL-ANCHORED path (verdict): CAGR incl. 6% interest / MaxDD / Sharpe on futures P&L (floor costs)

| System | 2012-07..2016-08 | 2012-07..2014-12 | 2015-01..2016-08 | whole window without interest |
|---|---|---|---|---|
| Plain long-only baseline | 24.8% / -6.4% / 1.47 | 30.9% / -5.7% / 1.81 | 16.3% / -6.4% / 0.91 | 17.4% / -8.0% / 1.47 |
| Buy and hold futures (1x) | 12.6% / -22.4% / 0.45 | 19.1% / -13.5% / 0.82 | 3.6% / -22.4% / -0.09 | 5.9% / -26.9% / 0.45 |
| Same weights, no cuts (1.91/0.96) | 51.3% / -13.4% / 1.69 | 62.3% / -9.7% / 1.96 | 36.2% / -13.4% / 1.27 | 42.3% / -13.7% / 1.69 |
| NB3 fixed cell (2.0/1.0, NQ2%+MC3 15bp, cut 0.25) | 57.2% / -12.5% / 1.90 | 66.2% / -12.5% / 2.07 | 44.7% / -9.8% / 1.63 | 47.9% / -13.2% / 1.90 |
| FROZEN (1.91/0.96, 9-cell ensemble cut) | 54.4% / -10.1% / 1.95 | 62.7% / -10.1% / 2.13 | 42.8% / -8.1% / 1.66 | 45.2% / -10.8% / 1.95 |
| Short leg alone (0.96) | 12.5% / -4.7% / 0.85 | 10.4% / -4.0% / 0.72 | 15.7% / -4.7% / 1.02 | 5.8% / -5.3% / 0.85 |
| Long leg alone (1.91, ensemble cut) | 45.8% / -8.9% / 1.73 | 56.6% / -8.7% / 1.97 | 31.1% / -8.9% / 1.31 | 37.2% / -10.3% / 1.73 |

Calendar-year total return (2012 = Jul-Dec, 2016 = Jan-Aug): 
| Year | Plain | Buy&hold | No cuts | NB3 fixed | FROZEN | Short alone |
|---|---|---|---|---|---|---|
| 2012 | 8.0% | 11.1% | 9.8% | 14.5% | 15.1% | 0.8% |
| 2013 | 27.5% | 6.6% | 66.6% | 60.4% | 57.7% | 18.8% |
| 2014 | 39.9% | 29.2% | 78.4% | 88.1% | 80.8% | 6.4% |
| 2015 | 11.3% | -5.4% | 26.3% | 21.2% | 26.3% | 16.2% |
| 2016 | 15.0% | 11.9% | 31.3% | 51.0% | 41.8% | 9.3% |

### Pass criteria on the REAL-ANCHORED path (verdict)

| Criterion | Result | Detail |
|---|---|---|
| E1 frozen Sharpe > plain long-only (whole window and both sub-periods) | PASS | whole 1.95 vs 1.47; 2012-07..2014-12 2.13 vs 1.81; 2015-01..2016-08 1.66 vs 0.91 |
| E2 frozen Sharpe > buy and hold futures | PASS | 1.95 vs 0.45 |
| E3 cuts add value (Sharpe up and MaxDD not worse vs same weights without cuts) | PASS | Sharpe 1.95 vs 1.69; MaxDD -10.1% vs -13.4% |
| E4 short leg alone positive excess Sharpe | PASS | 0.85 |
| R1 max drawdown better than -15% | PASS | -10.1% |
| R2 no calendar year worse than -10% | PASS | worst 15.1% (2012) |

**Verdict on the REAL-ANCHORED path (verdict): SUPPORTS** (4 of 4 edge criteria hold)

## Synthetic path: CAGR incl. 6% interest / MaxDD / Sharpe on futures P&L (floor costs)

| System | 2012-07..2016-08 | 2012-07..2014-12 | 2015-01..2016-08 | whole window without interest |
|---|---|---|---|---|
| Plain long-only baseline | 23.0% / -6.8% / 1.43 | 28.3% / -5.3% / 1.80 | 15.6% / -6.8% / 0.86 | 15.7% / -8.7% / 1.43 |
| Buy and hold futures (1x) | 14.4% / -21.9% / 0.56 | 21.7% / -13.5% / 0.98 | 4.3% / -21.9% / -0.04 | 7.6% / -26.4% / 0.56 |
| Same weights, no cuts (1.91/0.96) | 47.6% / -13.9% / 1.67 | 57.7% / -9.2% / 2.00 | 33.6% / -13.9% / 1.19 | 38.8% / -14.3% / 1.67 |
| NB3 fixed cell (2.0/1.0, NQ2%+MC3 15bp, cut 0.25) | 53.3% / -11.0% / 1.91 | 61.0% / -11.0% / 2.12 | 42.5% / -8.1% / 1.58 | 44.2% / -11.8% / 1.91 |
| FROZEN (1.91/0.96, 9-cell ensemble cut) | 50.6% / -9.2% / 1.95 | 57.6% / -9.2% / 2.17 | 40.7% / -7.7% / 1.61 | 41.6% / -9.9% / 1.95 |
| Short leg alone (0.96) | 12.7% / -4.9% / 0.86 | 11.2% / -3.6% / 0.84 | 14.9% / -4.9% / 0.92 | 6.0% / -5.5% / 0.86 |
| Long leg alone (1.91, ensemble cut) | 42.0% / -7.7% / 1.71 | 50.6% / -7.7% / 1.97 | 30.2% / -7.3% / 1.29 | 33.6% / -8.7% / 1.71 |

Calendar-year total return (2012 = Jul-Dec, 2016 = Jan-Aug): 
| Year | Plain | Buy&hold | No cuts | NB3 fixed | FROZEN | Short alone |
|---|---|---|---|---|---|---|
| 2012 | 5.7% | 12.2% | 5.6% | 10.3% | 10.6% | 1.1% |
| 2013 | 29.4% | 9.1% | 74.2% | 68.3% | 65.6% | 20.8% |
| 2014 | 34.3% | 32.1% | 65.3% | 72.3% | 65.6% | 6.2% |
| 2015 | 12.8% | -3.7% | 27.8% | 21.3% | 26.1% | 14.6% |
| 2016 | 12.3% | 11.3% | 25.6% | 47.1% | 38.6% | 9.5% |

### Pass criteria on the Synthetic path

| Criterion | Result | Detail |
|---|---|---|
| E1 frozen Sharpe > plain long-only (whole window and both sub-periods) | PASS | whole 1.95 vs 1.43; 2012-07..2014-12 2.17 vs 1.80; 2015-01..2016-08 1.61 vs 0.86 |
| E2 frozen Sharpe > buy and hold futures | PASS | 1.95 vs 0.56 |
| E3 cuts add value (Sharpe up and MaxDD not worse vs same weights without cuts) | PASS | Sharpe 1.95 vs 1.67; MaxDD -9.2% vs -13.9% |
| E4 short leg alone positive excess Sharpe | PASS | 0.86 |
| R1 max drawdown better than -15% | PASS | -9.2% |
| R2 no calendar year worse than -10% | PASS | worst 10.6% (2012) |

**Verdict on the Synthetic path: SUPPORTS** (4 of 4 edge criteria hold)