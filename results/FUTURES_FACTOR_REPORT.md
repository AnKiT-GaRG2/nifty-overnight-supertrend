# Nifty futures: factors that affect it, and their backtest (train / valid / test, full and regime-wise)

Author: Ankit Garg. Research only, not investment advice. **All numbers use real NSE Nifty futures prices** (daily bhavcopy, front month, premium and roll included). No spot-index results are used; the earlier spot 18% result is dropped.

Format of every cell: **CAGR / MaxDrawdown / Sharpe**. Periods: Train 2017-04 to 2021-12, Valid 2022-23, Test 2024-01 to 2026-10. Signal decided at 15:00 using only earlier data; fill at the last-30-minute VWAP; cost 0.025% per side plus 0.05% per roll (see section 3 for realistic costs).

*Two views of return:* **pure futures P&L** (price change including the premium decay a long pays; no interest) and **total return** (pure P&L plus 6% p.a. on capital, since futures need only margin). The pure view is the honest answer to the carry question; the total view is how idle cash is normally treated.

## 1. How many strategies were tried (overfitting accounting)

| Search | Futures variants |
|---|---|
| Real-futures search `rf_search.py` (signals x sizing x mode) | 378 |
| Factor permutation search `rf_factor_perm.py` (6 bases x 0-3 of 20 gates x 2 sizings x 2 modes) | 32,424 |
| Earlier spot-index searches (about 800 gates, not futures; excluded from all numbers) | not counted |
| **Total futures variants looked at** | **about 32,800** |

Picks were made on **train + valid only** (score = the weaker of the two periods' CAGR minus |MaxDD|). Test was never used to choose or change anything. After the picks, ablation and neighbour-threshold runs were done as diagnostics only; they did not change the strategy.

Because ~32,800 variants were tried, the best train+valid score is optimistic. Check on test: of the 100 best train+valid variants, the median test CAGR was 3.8% (buy-and-hold futures 0.4%); 87% beat buy-and-hold on test CAGR and 95% had a smaller test drawdown. The single top variant ranks only at the 40th percentile of all variants on test (CAGR minus drawdown). Rank correlation between train+valid and test score is 0.28: real but weak.

## 2. Frozen strategies vs simply holding Nifty futures

- **Hold** = buy Nifty futures and keep them (rolling each month).
- **A: Trend(50) + rising OI**: long when the 15:00 price is above its 50-day average AND total futures open interest rose over the last 5 days (OI known to the previous close). Otherwise flat.
- **B: Factor-gated**: long unless USD/INR rose >2% in 21 days, OR US 10Y yield rose >=25bp in 21 days, OR it is January/February. Chosen as best of the 32,424 on train+valid.

**Total return (futures P&L + 6% interest on capital):**

| Strategy | Train 2017-21 | Valid 2022-23 | Test 2024-26 | Full |
|---|---|---|---|---|
| Hold futures | 16.7% / -38.3% / 0.93 | 11.9% / -15.3% / 0.88 | 0.4% / -18.6% / 0.10 | 10.6% / -38.3% / 0.71 |
| A: Trend50 & OI | 11.3% / -8.2% / 1.47 | 12.8% / -2.9% / 2.25 | 4.2% / -7.1% / 0.70 | 9.4% / -8.2% / 1.38 |
| B: Factor-gated | 25.7% / -10.1% / 2.04 | 23.9% / -5.2% / 2.57 | 8.1% / -10.0% / 0.77 | 19.8% / -10.1% / 1.73 |

**Pure futures P&L (no interest; includes the premium a long pays):**

| Strategy | Train 2017-21 | Valid 2022-23 | Test 2024-26 | Full |
|---|---|---|---|---|
| Hold futures | 9.9% / -41.0% / 0.60 | 5.4% / -17.4% / 0.45 | -5.4% / -27.9% / -0.35 | 4.2% / -41.0% / 0.34 |
| A: Trend50 & OI | 4.8% / -10.9% / 0.66 | 6.2% / -3.8% / 1.15 | -1.8% / -8.6% / -0.27 | 3.1% / -10.9% / 0.48 |
| B: Factor-gated | 18.4% / -11.0% / 1.52 | 16.6% / -5.5% / 1.86 | 1.8% / -14.9% / 0.22 | 12.8% / -14.9% / 1.18 |

Reading: in total-return terms both beat holding futures on Sharpe and drawdown in every period (A's CAGR is lower than holding in train, 11.3% vs 16.7%, and higher in valid and test). In pure-price terms holding futures lost money in test (-5.4%), A is slightly negative (-1.8%) and B slightly positive (+1.8%). A cuts drawdown by roughly 60-80% but does not make high returns; B earns more but with a bigger drawdown than A. Neither makes real money from price alone in the test years.

## 3. Costs: brokerage, STT, exchange charges, slippage

Assumed per futures lot of about Rs 15 lakh notional: brokerage ~Rs 20/order (~0.0013%), STT 0.02% on the sell side (a 0.05% STT is covered by the x1.6 scenario below), exchange charges 0.00183%, SEBI 0.0001%, stamp duty 0.002% on buy, GST 18% on brokerage and exchange charges, slippage 1bp per side (Nifty futures are very liquid). Round trip comes to about **0.048%**, i.e. 0.024% per side, almost exactly the 0.025% per side the model already used. Scenarios: x1 (0.025%/side), x1.6 (0.04%/side: higher STT plus 2bp slippage), x3 (stress).

| Strategy | Train 2017-21 | Valid 2022-23 | Test 2024-26 | Full |
|---|---|---|---|---|
| A costs x1 | 11.3% / -8.2% / 1.47 | 12.8% / -2.9% / 2.25 | 4.2% / -7.1% / 0.70 | 9.4% / -8.2% / 1.38 |
| B costs x1 | 25.7% / -10.1% / 2.04 | 23.9% / -5.2% / 2.57 | 8.1% / -10.0% / 0.77 | 19.8% / -10.1% / 1.73 |
| A costs x1.6 | 10.4% / -8.6% / 1.36 | 12.1% / -2.9% / 2.14 | 3.5% / -7.4% / 0.59 | 8.6% / -8.6% / 1.27 |
| B costs x1.6 | 25.1% / -10.1% / 2.00 | 23.2% / -5.2% / 2.51 | 7.6% / -10.5% / 0.72 | 19.2% / -10.5% / 1.69 |
| A costs x3 | 8.3% / -9.6% / 1.11 | 10.4% / -3.2% / 1.86 | 1.8% / -7.9% / 0.31 | 6.8% / -9.6% / 1.01 |
| B costs x3 | 23.6% / -10.2% / 1.90 | 21.7% / -5.3% / 2.37 | 6.4% / -11.7% / 0.62 | 17.8% / -11.7% / 1.58 |
| Hold futures (1 entry, ~1 roll/month) | 16.7% / -38.3% / 0.93 | 11.9% / -15.3% / 0.88 | 0.4% / -18.6% / 0.10 | 10.6% / -38.3% / 0.71 |

Trading frequency: A holds 35% of days, about 20 round trips a year; B holds 64% of days, about 9 round trips a year. Low turnover is why costs barely matter; at 3x costs both still beat holding futures on Sharpe and drawdown (A's test CAGR falls to 1.8%).

## 4. Parameter check: is 50 a fluke?

Trend(N) AND OI(5-day) rising, total-return view:

| Strategy | Train 2017-21 | Valid 2022-23 | Test 2024-26 | Full |
|---|---|---|---|---|
| Trend(30) & OI5 | 9.7% / -8.2% / 1.26 | 15.8% / -2.6% / 2.65 | 1.8% / -8.9% / 0.34 | 8.5% / -8.9% / 1.25 |
| Trend(40) & OI5 | 11.2% / -7.5% / 1.46 | 13.2% / -3.7% / 2.28 | 1.5% / -9.9% / 0.27 | 8.6% / -9.9% / 1.26 |
| Trend(50) & OI5 | 11.3% / -8.2% / 1.47 | 12.8% / -2.9% / 2.25 | 4.2% / -7.1% / 0.70 | 9.4% / -8.2% / 1.38 |
| Trend(60) & OI5 | 10.2% / -8.2% / 1.32 | 10.4% / -3.7% / 1.82 | 5.4% / -7.1% / 0.89 | 8.8% / -8.2% / 1.28 |
| Trend(80) & OI5 | 7.1% / -9.6% / 0.96 | 10.4% / -3.8% / 1.73 | 5.7% / -6.1% / 0.93 | 7.4% / -9.6% / 1.08 |
| Trend(100) & OI5 | 7.5% / -7.7% / 1.01 | 11.1% / -4.4% / 1.84 | 5.9% / -6.1% / 0.94 | 7.8% / -7.7% / 1.13 |
| Trend(150) & OI5 | 8.8% / -7.0% / 1.18 | 13.1% / -4.9% / 1.90 | 7.1% / -6.1% / 1.11 | 9.2% / -7.0% / 1.30 |

Same, pure futures P&L:

| Strategy | Train 2017-21 | Valid 2022-23 | Test 2024-26 | Full |
|---|---|---|---|---|
| Trend(30) & OI5 | 3.3% / -10.0% / 0.47 | 9.0% / -3.6% / 1.58 | -4.1% / -11.9% / -0.69 | 2.2% / -11.9% / 0.36 |
| Trend(40) & OI5 | 4.7% / -9.3% / 0.65 | 6.5% / -4.9% / 1.19 | -4.5% / -12.6% / -0.72 | 2.3% / -12.7% / 0.37 |
| Trend(50) & OI5 | 4.8% / -10.9% / 0.66 | 6.2% / -3.8% / 1.15 | -1.8% / -8.6% / -0.27 | 3.1% / -10.9% / 0.48 |
| Trend(60) & OI5 | 3.8% / -10.9% / 0.53 | 3.9% / -4.9% / 0.73 | -0.7% / -8.6% / -0.09 | 2.4% / -10.9% / 0.39 |
| Trend(80) & OI5 | 0.9% / -12.3% / 0.16 | 3.9% / -4.9% / 0.70 | -0.5% / -7.6% / -0.04 | 1.1% / -12.3% / 0.20 |

Reading: N = 30 to 150 all give a similar shape (full CAGR 7.4-9.4%, drawdown 7-10% in total-return view), so 50 is not a lucky spike. Honest caveats: in pure futures P&L the test period is negative for every N (-0.5% to -4.5%), and the shorter averages (30, 40) are clearly worse in test than the longer ones, so 50 to 150 are the safer range.

## 5. Expiry effect on OI

How handled: the OI used is the **sum of open interest across all live Nifty contracts**, not the front month. When positions roll from the expiring contract to the next one, OI moves between contracts but the sum barely changes, so the roll does not create a fake rise or fall. Checks:

- Front-month-only OI would be wrong around expiry: it agrees with total-OI on 53% of all days but only 32% on days within 3 days before expiry.

| Strategy | Train 2017-21 | Valid 2022-23 | Test 2024-26 | Full |
|---|---|---|---|---|
| A with total OI (used) | 11.3% / -8.2% / 1.47 | 12.8% / -2.9% / 2.25 | 4.2% / -7.1% / 0.70 | 9.4% / -8.2% / 1.38 |
| A with front-month OI only | 12.3% / -7.0% / 1.63 | 8.7% / -4.3% / 1.70 | -4.2% / -13.6% / -0.65 | 6.4% / -14.0% / 0.99 |
| A with OI gate frozen in last 3 days before expiry | 11.2% / -8.8% / 1.36 | 14.5% / -2.9% / 2.50 | 4.2% / -5.6% / 0.71 | 9.7% / -8.8% / 1.36 |

Reading: using total OI (or freezing the gate near expiry) gives the same results; the front-month-only version is the one that is distorted (test CAGR -4.2% instead of +4.2%). Rolls also pay 0.05% in the cost model whenever a position is carried across expiry.

## 6. Timing: no future data in the signal

- Decision is made at 15:00 on day t. The price used is the 15:00 bar close; the position is filled at the last-30-minute VWAP after that.
- OI for day t is published after close, so the signal uses `OI[t-1]` (OI is shifted one day and the 5-day change is taken on the shifted series). The 5-day change at day t is OI(t-1)/OI(t-6)-1.
- All macro series (USD/INR, US10Y, DXY, S&P, Brent, VIX) are the latest close **strictly before** day t; FII monthly flows are used only from the next month.
Proof by experiment:

| Strategy | Train 2017-21 | Valid 2022-23 | Test 2024-26 | Full |
|---|---|---|---|---|
| A as used (OI lagged 1 day) | 11.3% / -8.2% / 1.47 | 12.8% / -2.9% / 2.25 | 4.2% / -7.1% / 0.70 | 9.4% / -8.2% / 1.38 |
| A cheating: same-day OI (not allowed) | 6.7% / -12.7% / 0.82 | 10.4% / -4.4% / 1.98 | 4.6% / -6.1% / 0.74 | 6.8% / -12.7% / 0.95 |
| A with OI lagged 2 days | 11.7% / -7.3% / 1.48 | 11.7% / -3.1% / 1.98 | 3.8% / -8.1% / 0.53 | 9.3% / -8.1% / 1.26 |

A leak would make the used version look better than the safer lagged versions. It does not: lag-1 (9.4% full) is about the same as lag-2 (9.3%), and the same-day OI row is not better (6.8%). So the one-day lag is not hiding any advantage, and no future OI is used. The OI series and gates are built from the previous close only.

## 7. Factors from the Nifty document: what each one does (standalone, on futures)

Each factor is a gate on 'always long futures': allow holding only when the factor is calm. 'Blocked-day return' is the annualised pure-futures return on the days the gate said stay out. **A good factor has a blocked-day return below the allowed-day return.** Train / Valid / Test shown separately.

| Factor (caution when…) | Days blocked | Blocked-day ann. return Train / Valid / Test | Allowed-day ann. return Train / Valid / Test | Gated-long (total return) Train / Valid / Test CAGR | Verdict |
|---|---|---|---|---|---|
| Rupee weak: USD/INR +2% in 21d | 11% | -31% / 97% / 19% | 19% / -1% / -7% | 22.4% / 5.6% / -1.0% | mixed |
| Rupee weak: +0.3% yesterday | 17% | 23% / -1% / -23% | 7% / 6% / -3% | 10.0% / 10.4% / 2.5% | works in 2 of 3 |
| Dollar index +1.5% in 21d | 20% | 20% / 16% / -27% | 9% / -1% / 1% | 13.4% / 5.6% / 6.4% | mixed |
| US 10Y +25bp in 21d | 15% | -36% / -29% / -20% | 14% / 32% / -3% | 19.8% / 26.1% / 3.2% | works in all 3 |
| S&P 500 down >2% in 21d | 18% | -7% / -10% / 51% | 13% / 14% / -12% | 17.6% / 15.7% / -4.8% | works in 2 of 3 |
| S&P 500 below 200DMA | 21% | -7% / 6% / 73% | 14% / 4% / -10% | 18.0% / 8.8% / -3.3% | mixed |
| Brent 21d avg >$100 | 8% | n/a / 19% / 4% | 10% / 1% / -7% | 16.7% / 7.8% / 0.0% | too few blocked days in some period |
| Brent +5% in 5d | 14% | 48% / -14% / -8% | 5% / 9% / -5% | 10.3% / 12.7% / 1.0% | works in 2 of 3 |
| India VIX >=20 | 18% | 23% / 29% / 53% | 6% / -0% / -8% | 10.5% / 6.6% / -2.2% | does not work |
| India VIX >=25 | 6% | 54% / n/a / n/a | 6% / 4% / -9% | 12.1% / 11.4% / -3.0% | too few blocked days in some period |
| India VIX +8% yesterday | 6% | -57% / -53% / 8% | 18% / 9% / -6% | 22.5% / 15.1% / -0.7% | works in 2 of 3 |
| FII sold >10k cr last month | 47% | 8% / 1% / -10% | 11% / 10% / 5% | 14.2% / 10.5% / 7.7% | works in all 3 |
| FII sold >2 lakh cr in 12m | 32% | n/a / -0% / -10% | 10% / 11% / 5% | 16.7% / 12.1% / 7.7% | too few blocked days in some period |
| Nifty P/E >=25 | 42% | 12% / n/a / n/a | 2% / 6% / -6% | 6.4% / 12.8% / 0.4% | too few blocked days in some period |
| Jan/Feb seasonality | 16% | -10% / -31% / -25% | 14% / 14% / -1% | 18.5% / 18.9% / 5.7% | works in all 3 |
| Korean won weak 2% in 21d | 20% | 34% / 7% / -27% | 7% / 4% / 1% | 11.6% / 9.4% / 6.7% | mixed |
| Bank Nifty below 50DMA | 39% | 2% / 7% / -3% | 15% / 3% / -8% | 15.6% / 7.5% / 1.0% | mixed |
| Futures OI falling over 5d | 43% | 16% / -11% / -7% | 6% / 19% / -4% | 8.4% / 16.0% / 2.5% | works in 2 of 3 |
| Futures premium >=5% annualised | 49% | -7% / 2% / -20% | 21% / 8% / 31% | 17.8% / 9.4% / 14.1% | works in all 3 |

Blocked-day returns are noisy where blocked days are few (Brent >$100, VIX >=25, P/E, FII 12m are 'n/a' where a period has under 20 blocked days; the rupee 2% figure in valid is a handful of crisis days). Gated-long CAGR is in the total-return view. 'Works' means blocked-day return < allowed-day return in that period.

Hold futures (total return) CAGR for reference: 16.7% / 11.9% / 0.4%. Factors the document called 'no effect' (gold, India 10Y yield, yen, US inflation, expiry week) were not tested as drivers.

FII monthly flows: data file ends 27 Jan 2026, so FII gates carry the last value forward after that (stale). P/E file ends 1 Jul 2026. Treat both as less reliable for 2026.

## 8. Regime-wise results in Train / Valid / Test / Full

Annualised total return % / Sharpe in each market regime (regime known at the decision day; return is the next holding period). Hold = buy-and-hold futures, A = Trend50 & OI, B = factor-gated. `n` = days. '-' = fewer than 20 days. Where a strategy is mostly in cash, its volatility is tiny and the Sharpe is inflated (values like 25 are artefacts; read the return column).

### Trend (price vs 200DMA)

| Regime | Period | n | Hold | A | B |
|---|---|---|---|---|---|
| Bear (below) | train | 205 | 20.6% / 0.71 | 17.6% / 2.38 | 59.3% / 2.80 |
| Bear (below) | valid | 105 | 60.0% / 2.60 | 7.9% / 2.48 | 31.1% / 2.05 |
| Bear (below) | test | 250 | 3.3% / 0.28 | 2.5% / 0.79 | 10.6% / 0.88 |
| Bear (below) | full | 560 | 18.7% / 0.81 | 8.8% / 1.76 | 30.5% / 1.90 |
| Bull (above) | train | 768 | 13.7% / 0.99 | 12.1% / 1.44 | 20.9% / 1.84 |
| Bull (above) | valid | 386 | 0.8% / 0.13 | 14.5% / 2.28 | 21.4% / 3.00 |
| Bull (above) | test | 451 | -1.2% / -0.03 | 5.3% / 0.73 | 6.9% / 0.70 |
| Bull (above) | full | 1607 | 6.5% / 0.54 | 10.7% / 1.39 | 17.2% / 1.68 |

### Volatility (India VIX)

| Regime | Period | n | Hold | A | B |
|---|---|---|---|---|---|
| High >=22 | train | 205 | 43.5% / 1.21 | 14.1% / 1.46 | 47.5% / 2.41 |
| High >=22 | valid | 48 | 30.7% / 1.24 | 6.3% / 27.12 | 54.1% / 2.75 |
| High >=22 | test | 20 | -30.3% / -0.82 | 25.8% / 1.92 | -22.4% / -0.67 |
| High >=22 | full | 273 | 33.9% / 1.04 | 13.5% / 1.49 | 41.8% / 2.02 |
| Low <15 | train | 485 | 7.7% / 0.79 | 8.2% / 1.26 | 7.5% / 0.90 |
| Low <15 | valid | 249 | 16.6% / 1.65 | 15.0% / 2.67 | 27.5% / 3.55 |
| Low <15 | test | 491 | -9.8% / -0.86 | 3.7% / 0.64 | 0.1% / 0.05 |
| Low <15 | full | 1225 | 2.0% / 0.24 | 7.7% / 1.26 | 8.2% / 1.00 |
| Mid 15-22 | train | 481 | 16.6% / 1.06 | 13.8% / 1.67 | 38.9% / 2.81 |
| Mid 15-22 | valid | 194 | 0.7% / 0.12 | 12.2% / 1.84 | 11.9% / 1.51 |
| Mid 15-22 | test | 190 | 37.5% / 2.23 | 3.9% / 0.64 | 37.2% / 2.51 |
| Mid 15-22 | full | 867 | 17.5% / 1.12 | 11.2% / 1.50 | 32.5% / 2.53 |

### Momentum (20d return)

| Regime | Period | n | Hold | A | B |
|---|---|---|---|---|---|
| Down <-3% | train | 143 | -33.4% / -0.86 | 6.4% / 25.27 | 14.6% / 1.20 |
| Down <-3% | valid | 85 | 57.0% / 2.49 | 4.9% / 1.64 | 31.1% / 2.32 |
| Down <-3% | test | 112 | -20.9% / -1.24 | 6.6% / 25.67 | -2.9% / -0.19 |
| Down <-3% | full | 340 | -12.7% / -0.33 | 6.1% / 3.97 | 12.2% / 1.03 |
| Flat | train | 595 | 24.0% / 1.56 | 10.4% / 1.33 | 33.0% / 2.55 |
| Flat | valid | 244 | -13.1% / -0.98 | 7.4% / 1.87 | 13.1% / 1.85 |
| Flat | test | 462 | 9.5% / 0.83 | 6.4% / 0.92 | 16.6% / 1.63 |
| Flat | full | 1302 | 11.3% / 0.87 | 8.4% / 1.21 | 23.5% / 2.14 |
| Up >3% | train | 414 | 30.7% / 1.99 | 15.3% / 1.62 | 21.4% / 1.64 |
| Up >3% | valid | 162 | 34.8% / 2.60 | 27.0% / 3.02 | 36.3% / 3.59 |
| Up >3% | test | 127 | -9.6% / -0.58 | -4.8% / -0.73 | -9.2% / -0.58 |
| Up >3% | full | 704 | 23.1% / 1.58 | 13.9% / 1.59 | 18.3% / 1.45 |

### Drawdown (from 252d high)

| Regime | Period | n | Hold | A | B |
|---|---|---|---|---|---|
| Deep >10% | train | 135 | 86.7% / 1.72 | 13.8% / 1.57 | 109.7% / 3.73 |
| Deep >10% | valid | 62 | 34.9% / 1.63 | 15.3% / 4.67 | 4.5% / 0.36 |
| Deep >10% | test | 136 | 15.9% / 0.98 | 7.8% / 11.37 | 37.8% / 2.69 |
| Deep >10% | full | 333 | 44.7% / 1.39 | 11.6% / 2.00 | 55.2% / 2.73 |
| Near high <5% | train | 687 | 16.6% / 1.29 | 11.2% / 1.34 | 22.2% / 2.14 |
| Near high <5% | valid | 281 | 3.1% / 0.34 | 14.5% / 2.06 | 19.3% / 2.51 |
| Near high <5% | test | 347 | -0.6% / 0.01 | 5.7% / 0.74 | 3.5% / 0.39 |
| Near high <5% | full | 1316 | 8.9% / 0.76 | 10.4% / 1.31 | 16.3% / 1.68 |
| Pullback 5-10% | train | 291 | -5.1% / -0.25 | 12.8% / 1.86 | 9.4% / 0.85 |
| Pullback 5-10% | valid | 148 | 18.6% / 1.11 | 9.4% / 2.65 | 41.0% / 5.03 |
| Pullback 5-10% | test | 218 | -6.7% / -0.45 | 0.0% / 0.03 | 0.0% / 0.06 |
| Pullback 5-10% | full | 658 | -0.1% / 0.07 | 7.6% / 1.35 | 13.1% / 1.20 |

### Calendar year (full-period strategy returns, total return view)

| Year | Hold | A | B |
|---|---|---|---|
| 2017 | 16.5% | 0.5% | 13.9% |
| 2018 | 6.4% | 15.9% | 13.3% |
| 2019 | 11.8% | 14.6% | 19.5% |
| 2020 | 20.5% | 16.7% | 54.0% |
| 2021 | 24.6% | 6.6% | 24.6% |
| 2022 | 7.0% | 10.3% | 19.3% |
| 2023 | 16.9% | 15.2% | 28.2% |
| 2024 | 7.3% | 7.6% | 12.6% |
| 2025 | 8.5% | 5.5% | 16.9% |
| 2026 | -13.1% | -1.0% | -5.4% |

## 9. Verdict against the checklist

1. Futures only: yes, every number above. Spot results are dropped.
2. Carry: a long pays the premium; it is inside every pure-futures figure. Hold futures made 4.2% a year over the full period in pure terms and lost money in test.
3. Costs: realistic all-in costs are about the 0.025% per side already modelled; at 3x costs both strategies still beat holding futures.
4. Versus holding futures: A and B both beat it on Sharpe and drawdown in train, valid and test (total-return view). In pure futures P&L, B beats holding in every period; A does so only on drawdown and Sharpe, and its price-only return in train (4.8%) is below holding (9.9%).
5. Train / valid / test: shown separately everywhere. Both strategies earn less in test than in train/valid.
6. Expiry: total OI across contracts is used; front-month-only OI is distorted near expiry.
7. Timing: OI lagged one day; lagging two days gives the same result and same-day OI is not better, so there is no hidden look-ahead advantage.
8. Parameters: Trend 30 to 150 behave similarly, not a lucky 50.
9. Overfitting: about 32,800 futures variants tried; picks on train+valid only; test untouched; top-100 median test CAGR 3.8% vs 0.4% for holding.

**Honest limits.** (a) Test (2024 to Oct 2026) is only 2.8 years, with a flat-to-falling Nifty, so it favours any strategy that sits out. (b) Pure-futures test returns for A and B are about -2% to +2% a year; the headline test numbers rely on interest earned on idle capital. (c) B's thresholds come from a document written with the full 2016-26 history in view, so B is less blind than A. (d) Daily data only; execution at VWAP is assumed.

**Suggested next step:** paper-trade A (simplest, 2 parameters, smallest drawdown) and B side by side for 2-3 months, with the rules frozen as written here; compare each with simply holding Nifty futures after real costs.
