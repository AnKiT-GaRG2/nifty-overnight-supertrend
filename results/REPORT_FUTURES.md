# Nifty Futures: Popular Strategies and Trend(50) + Rising OI — Full Backtest Report

Research only, not investment advice. Prepared 2026-11-03. All results are on **real NSE Nifty index futures** (daily bhavcopy, 2017-04-03 to 2026-11-02, 2,367 trading days). The spot index is not used anywhere, and the earlier spot-based 18% result is dropped.

## 1. Verdict (short)

**Hinglish mein:** Trend(50) + rising OI strategy, kharche (brokerage, STT, charges, slippage) ke baad, seedha Nifty futures pakadne se behtar *nahi* nikli. Train aur valid mein achhi thi (11.3% aur 10.1% CAGR, drawdown bahut kam), par test period (2024 se 2026) mein -8.5% CAGR aur -24% drawdown, jabki buy-and-hold -4.8% aur -26% tha. Parameter 30/40/60/80 par bhi test mein sab fail. Is hisaab se paper trading ka gate (kharche ke baad B&H se behtar) abhi clear nahi hua.

**In English:**
- **Trend(50) + rising OI fails the gate** (net of all costs, beat futures buy-and-hold in every period). It beat buy-and-hold on CAGR, Sharpe and MaxDD in train and valid, but lost in test: -8.5% CAGR / -1.15 Sharpe / -23.9% MaxDD against buy-and-hold's -4.8% / -0.28 / -25.9%.
- **The parameter sweep suggests partial luck at N=50.** With expiry-adjusted OI, N=50 is the only value that beats buy-and-hold on all three metrics in train. N=30/40/60/80 do not. All five values lose money in test.
- **Expiry handling matters.** Naive total OI is corrupted by expiry: it falls about 23% on the day after each expiry, so "OI rising" is true on only 1% of those days versus 64% normally. Adjusting for it changes the results a lot (test CAGR -8.5% adjusted, -3.5% naive). That choice is itself a degree of freedom.
- **No strategy among the 35 tuned variants (about 20 families, long-only and long/short) beats futures buy-and-hold in all three periods and is also profitable in all three.** Trend-following worked in train/valid and failed in test.
- **Deflated Sharpe for the headline is 0.37** (a value near 0.95+ would be strong evidence). Its train+valid Sharpe of 1.19 is below the 1.33 that pure luck is expected to produce after ~2,350 trials.
- **Only a small, post-hoc "panic-reversal" idea is positive in all three periods** (see section 9). It earns about 1 to 2% a year, unlevered, and was found with knowledge of the test period.

## 2. Method (what exactly was done)

| Item | Choice |
|---|---|
| Instrument | Nifty index futures, front-month contract not expiring on the entry day; rolled the day it expires |
| Signal timing | Computed from data through the close of day t, including that day's price, VIX and **OI (published after close)**. Orders fill at the **next open (t+1)**. Position is held open-to-open on the same contract. |
| Costs | Brokerage, STT (date-dependent), exchange, SEBI, GST, stamp duty and slippage on every position change, plus a roll cost when a position is carried through expiry. Details in section 5. |
| Interest/carry | None added. Futures prices already contain the premium, so a long pays it and the buy-and-hold benchmark pays it too. If idle capital sits in a liquid fund (about 6.5%/yr), roughly that much is added to every strategy and to buy-and-hold equally; this does not change the comparison. |
| Periods (fixed in advance) | **Train** 2018-04-01 to 2021-12-31, **Valid** 2022-01-01 to 2023-12-31, **Test** 2024-01-01 to 2026-11-02. The first year of data is indicator warm-up. |
| Parameter selection | "Default" = textbook values, no fitting. "Tuned" = best net Sharpe on **train only**. Shortlist = Sharpe above 0.5 and CAGR above 0 in both train and valid. Test was never used to choose or change anything in this run. |
| Benchmark | Always-long Nifty futures, same costs and same roll rule |
| Regimes | Trend (price vs 200DMA), India VIX band (<15, 15-22, >22), 20-day momentum (+/-3%), drawdown from high (>10%). Each label uses information only up to the previous close. |

## 3. Results — textbook parameters, no fitting (CAGR% / Sharpe / MaxDD%, net of all costs)

| Strategy | Train CAGR/Sharpe/MaxDD | Valid | Test | Full | Exposure |
|---|---|---|---|---|---|
| Trend(50) only [no OI] | 15.1 / 1.31 / -12.6 | 1.6 / 0.22 / -16.8 | -4.6 / -0.50 / -15.7 | 5.1 / 0.55 / -17.7 | 58% |
| EMA cross 12/26 [long-only] | 14.9 / 1.23 / -13.1 | 6.9 / 0.79 / -7.9 | -5.2 / -0.51 / -17.3 | 6.0 / 0.61 / -17.3 | 59% |
| Trend(N)+OI sma20 [expiry-adj OI] | 13.5 / 1.22 / -13.3 | 5.8 / 0.72 / -10.9 | -3.3 / -0.36 / -11.6 | 5.9 / 0.65 / -13.3 | 53% |
| SMA cross 20/50 [long-only] | 14.2 / 1.13 / -17.7 | -4.4 / -0.44 / -18.0 | -0.6 / -0.02 / -10.8 | 4.6 / 0.47 / -23.9 | 60% |
| Trend(N)+OI chg5 [expiry-adj OI] | 11.3 / 1.11 / -11.7 | 10.1 / 1.47 / -4.4 | -8.5 / -1.15 / -23.9 | 4.0 / 0.50 / -23.9 | 43% |
| Bollinger breakout (20,2) | 7.5 / 1.04 / -9.5 | 8.8 / 1.43 / -4.3 | -10.0 / -2.04 / -25.5 | 1.6 / 0.28 / -25.8 | 21% |
| Supertrend daily (10,3) [long-only] | 11.9 / 1.03 / -20.0 | 10.2 / 1.20 / -7.0 | -12.5 / -1.36 / -32.0 | 2.8 / 0.32 / -32.0 | 56% |
| Trend(N)+OI chg1 [expiry-adj OI] | 9.7 / 1.01 / -10.8 | 0.4 / 0.10 / -10.7 | -2.9 / -0.42 / -12.3 | 3.2 / 0.43 / -12.3 | 36% |
| Keltner breakout (20,2) | 8.3 / 0.96 / -9.9 | 3.5 / 0.56 / -9.6 | -6.6 / -1.20 / -18.3 | 2.0 / 0.31 / -18.3 | 30% |
| Trend(N)+OI chg1 [naive OI] | 8.1 / 0.90 / -11.0 | -1.9 / -0.23 / -11.2 | -0.8 / -0.10 / -10.9 | 2.7 / 0.38 / -12.2 | 34% |
| Price > 200DMA [long-only] | 9.3 / 0.81 / -19.7 | -1.9 / -0.14 / -17.4 | -4.2 / -0.43 / -22.1 | 2.1 / 0.25 / -22.1 | 64% |
| EMA cross 12/26 [L/S] | 15.3 / 0.81 / -22.9 | 5.7 / 0.46 / -10.0 | -7.2 / -0.46 / -25.2 | 5.1 / 0.38 / -25.2 | 100% |
| Donchian 20/10 (turtle) | 8.3 / 0.80 / -20.9 | 6.4 / 0.82 / -7.9 | -8.4 / -1.06 / -22.6 | 2.0 / 0.27 / -22.6 | 43% |
| SMA cross 20/50 [L/S] | 14.1 / 0.76 / -27.3 | -15.5 / -1.10 / -32.8 | 2.0 / 0.21 / -16.9 | 2.6 / 0.23 / -43.8 | 100% |
| Buy & Hold futures | 11.0 / 0.62 / -40.7 | 6.0 / 0.48 / -17.8 | -4.8 / -0.28 / -25.9 | 4.4 / 0.34 / -40.7 | 100% |
| MACD 12/26/9 [long-only] | 6.3 / 0.59 / -16.4 | 9.9 / 1.10 / -10.9 | -5.8 / -0.63 / -17.4 | 2.9 / 0.33 / -17.6 | 48% |
| ADX/DI trend (14,25) [long-only] | 3.4 / 0.57 / -9.1 | 0.1 / 0.04 / -5.8 | -1.6 / -0.55 / -6.6 | 0.9 / 0.21 / -10.0 | 17% |
| Connors RSI(2) 10/70 | 4.1 / 0.57 / -9.1 | -1.8 / -0.31 / -7.0 | 4.6 / 0.97 / -3.1 | 2.8 / 0.48 / -10.8 | 15% |
| Trend(N)+OI sma20 [naive OI] | 4.3 / 0.55 / -9.0 | 1.3 / 0.23 / -7.8 | -0.3 / -0.02 / -6.0 | 2.1 / 0.33 / -9.5 | 28% |
| Supertrend daily (10,3) [L/S] | 9.4 / 0.55 / -30.6 | 12.1 / 0.87 / -12.4 | -21.1 / -1.62 / -51.9 | -1.3 / 0.01 / -51.9 | 100% |
| Long build-up (price&OI up over k) [expiry-adj OI] | 5.3 / 0.54 / -17.8 | 12.0 / 1.56 / -7.8 | -10.1 / -1.54 / -26.5 | 1.3 / 0.20 / -27.3 | 41% |
| Trend(N)+OI chg5 [naive OI] | 4.2 / 0.51 / -9.9 | 5.5 / 0.93 / -3.6 | -3.5 / -0.57 / -12.0 | 1.9 / 0.29 / -12.0 | 31% |
| Time-series momentum 252d [long-only] | 5.4 / 0.48 / -22.0 | -2.8 / -0.16 / -18.8 | -8.2 / -0.76 / -31.6 | -1.2 / -0.04 / -31.8 | 68% |
| Donchian 55/20 | 3.1 / 0.36 / -17.6 | 2.5 / 0.42 / -8.8 | -5.4 / -0.72 / -15.8 | 0.1 / 0.05 / -17.6 | 38% |
| Price > 200DMA [L/S] | 4.5 / 0.32 / -32.5 | -10.6 / -0.71 / -31.1 | -5.3 / -0.32 / -34.3 | -2.4 / -0.06 / -44.4 | 100% |
| SMA cross 50/200 [long-only] | 2.2 / 0.23 / -39.6 | 0.8 / 0.12 / -14.9 | -0.9 / -0.04 / -18.1 | 0.8 / 0.13 / -39.6 | 64% |
| ADX/DI trend (14,25) [L/S] | 2.3 / 0.22 / -25.2 | -5.6 / -0.61 / -17.7 | -0.3 / 0.02 / -10.9 | -0.4 / 0.03 / -33.9 | 37% |
| Buy-the-dip (-1.5 sigma) | 0.8 / 0.16 / -8.6 | -1.3 / -0.25 / -6.8 | 4.1 / 0.73 / -5.5 | 1.4 / 0.27 / -8.6 | 8% |
| IBS mean-reversion | 1.3 / 0.16 / -32.9 | -3.1 / -0.28 / -9.4 | -0.9 / -0.04 / -13.1 | -0.5 / 0.02 / -32.9 | 41% |
| Bollinger mean-rev (20,2) | 1.0 / 0.14 / -31.5 | 2.4 / 0.33 / -5.8 | 4.5 / 0.54 / -10.3 | 2.4 / 0.27 / -31.5 | 23% |
| Long build-up (price&OI up over k) [naive OI] | 0.7 / 0.12 / -13.3 | 5.8 / 0.93 / -9.4 | -7.1 / -1.48 / -18.6 | -0.8 / -0.08 / -20.3 | 29% |
| Stochastic mean-rev (14,20/80) | 0.3 / 0.10 / -33.9 | -1.7 / -0.11 / -11.9 | -0.8 / -0.03 / -16.6 | -0.5 / 0.03 / -33.9 | 42% |
| MACD 12/26/9 [L/S] | -1.7 / 0.02 / -31.0 | 11.7 / 0.84 / -15.9 | -8.5 / -0.56 / -33.3 | -1.1 / 0.02 / -41.1 | 100% |
| Time-series momentum 252d [L/S] | -2.0 / -0.00 / -44.3 | -11.7 / -0.79 / -30.7 | -12.8 / -0.91 / -45.0 | -8.0 / -0.40 / -62.2 | 100% |
| RSI(14) 30/50 mean-rev | -2.3 / -0.11 / -31.7 | 6.2 / 1.23 / -4.5 | -0.9 / -0.07 / -11.0 | 0.1 / 0.06 / -31.7 | 13% |
| SMA cross 50/200 [L/S] | -8.0 / -0.31 / -58.4 | -5.5 / -0.32 / -28.6 | 1.5 / 0.17 / -23.0 | -4.4 / -0.18 / -58.4 | 100% |

## 4. Results — parameters tuned on train only

| Strategy (params chosen on TRAIN) | Train CAGR/Sharpe/MaxDD | Valid | Test | Full | Exposure |
|---|---|---|---|---|---|
| Connors RSI(2) 10/70 {'w': 4, 'lo': 10, 'hi': 80} | 5.2 / 1.46 / -0.4 | 1.0 / 0.18 / -11.6 | -3.0 / -0.61 / -12.7 | 1.4 / 0.31 / -13.5 | 8% |
| SMA cross 20/50 [long-only] {'a': 30, 'b': 50} | 17.5 / 1.35 / -12.2 | -7.8 / -0.79 / -18.3 | -0.8 / -0.04 / -11.4 | 5.0 / 0.50 / -26.7 | 60% |
| Price > 200DMA [long-only] {'w': 50} | 15.1 / 1.31 / -12.6 | 1.6 / 0.22 / -16.8 | -4.6 / -0.50 / -15.7 | 5.1 / 0.55 / -17.7 | 58% |
| Trend(50) only [no OI] {'w': 50} | 15.1 / 1.31 / -12.6 | 1.6 / 0.22 / -16.8 | -4.6 / -0.50 / -15.7 | 5.1 / 0.55 / -17.7 | 58% |
| MACD 12/26/9 [long-only] {'a': 16, 'b': 40, 's': 9} | 15.9 / 1.30 / -10.3 | 12.6 / 1.37 / -9.8 | -9.1 / -1.05 / -25.2 | 6.2 / 0.64 / -25.5 | 50% |
| EMA cross 12/26 [long-only] {'a': 12, 'b': 26} | 14.9 / 1.23 / -13.1 | 6.9 / 0.79 / -7.9 | -5.2 / -0.51 / -17.3 | 6.0 / 0.61 / -17.3 | 59% |
| Trend(N)+OI sma20 [expiry-adj OI] {'N': 50} | 13.5 / 1.22 / -13.3 | 5.8 / 0.72 / -10.9 | -3.3 / -0.36 / -11.6 | 5.9 / 0.65 / -13.3 | 53% |
| Bollinger breakout (20,2) {'w': 30, 'k': 2.5} | 9.1 / 1.14 / -9.1 | 1.9 / 0.69 / -2.3 | -1.3 / -0.69 / -4.7 | 3.9 / 0.72 / -9.1 | 15% |
| Supertrend daily (10,3) [long-only] {'w': 7, 'm': 2.0} | 12.4 / 1.13 / -13.2 | 13.8 / 1.43 / -11.1 | -6.1 / -0.71 / -19.1 | 6.2 / 0.66 / -19.1 | 55% |
| Trend(N)+OI chg5 [expiry-adj OI] {'N': 50} | 11.3 / 1.11 / -11.7 | 10.1 / 1.47 / -4.4 | -8.5 / -1.15 / -23.9 | 4.0 / 0.50 / -23.9 | 43% |
| SMA cross 20/50 [L/S] {'a': 30, 'b': 50} | 20.9 / 1.05 / -22.2 | -21.2 / -1.59 / -39.1 | 1.6 / 0.18 / -13.5 | 3.3 / 0.28 / -48.5 | 100% |
| Trend(N)+OI chg1 [expiry-adj OI] {'N': 50} | 9.7 / 1.01 / -10.8 | 0.4 / 0.10 / -10.7 | -2.9 / -0.42 / -12.3 | 3.2 / 0.43 / -12.3 | 36% |
| Keltner breakout (20,2) {'w': 20, 'm': 1.5} | 8.8 / 0.98 / -12.7 | 6.7 / 0.95 / -7.2 | -7.0 / -1.20 / -19.1 | 2.8 / 0.40 / -19.1 | 35% |
| Long build-up (price&OI up over k) [expiry-adj OI] {'k': 20} | 11.2 / 0.97 / -13.1 | 8.5 / 0.98 / -10.9 | -9.4 / -1.12 / -25.7 | 3.3 / 0.38 / -25.7 | 55% |
| SMA cross 50/200 [long-only] {'a': 20, 'b': 100} | 11.2 / 0.94 / -15.8 | 0.3 / 0.08 / -11.4 | 0.6 / 0.11 / -10.8 | 5.0 / 0.52 / -18.2 | 60% |
| Donchian 20/10 (turtle) {'en': 40, 'ex': 10} | 8.6 / 0.91 / -13.7 | 0.1 / 0.05 / -12.3 | -3.8 / -0.53 / -13.7 | 2.4 / 0.33 / -16.1 | 36% |
| Donchian 55/20 {'en': 40, 'ex': 10} | 8.6 / 0.91 / -13.7 | 0.1 / 0.05 / -12.3 | -3.8 / -0.53 / -13.7 | 2.4 / 0.33 / -16.1 | 36% |
| Trend(N)+OI chg1 [naive OI] {'N': 50} | 8.1 / 0.90 / -11.0 | -1.9 / -0.23 / -11.2 | -0.8 / -0.10 / -10.9 | 2.7 / 0.38 / -12.2 | 34% |
| Time-series momentum 252d [long-only] {'w': 63} | 10.3 / 0.89 / -12.8 | 5.7 / 0.66 / -9.3 | -6.0 / -0.69 / -18.3 | 3.6 / 0.40 / -18.3 | 60% |
| MACD 12/26/9 [L/S] {'a': 16, 'b': 40, 's': 9} | 17.2 / 0.89 / -14.6 | 17.4 / 1.19 / -11.0 | -14.9 / -1.08 / -41.0 | 5.4 / 0.40 / -41.0 | 100% |
| Price > 200DMA [L/S] {'w': 50} | 15.6 / 0.82 / -22.2 | -4.4 / -0.24 / -23.0 | -6.2 / -0.39 / -23.5 | 3.2 / 0.27 / -30.7 | 100% |
| EMA cross 12/26 [L/S] {'a': 12, 'b': 26} | 15.3 / 0.81 / -22.9 | 5.7 / 0.46 / -10.0 | -7.2 / -0.46 / -25.2 | 5.1 / 0.38 / -25.2 | 100% |
| Bollinger mean-rev (20,2) {'w': 10, 'k': 2.5} | 0.2 / 0.70 / -0.1 | 0.0 / 0.00 / 0.0 | 0.0 / 0.00 / 0.0 | 0.1 / 0.46 / -0.1 | 0% |
| Long build-up (price&OI up over k) [naive OI] {'k': 20} | 4.9 / 0.63 / -9.1 | 5.6 / 0.93 / -4.4 | -4.9 / -0.78 / -18.5 | 1.7 / 0.28 / -18.5 | 28% |
| ADX/DI trend (14,25) [long-only] {'w': 14, 'th': 30} | 3.1 / 0.61 / -5.9 | 1.7 / 0.43 / -4.3 | -0.5 / -0.27 / -2.8 | 1.6 / 0.40 / -5.9 | 11% |
| Supertrend daily (10,3) [L/S] {'w': 7, 'm': 2.0} | 10.1 / 0.58 / -23.1 | 19.8 / 1.33 / -11.5 | -9.3 / -0.62 / -30.2 | 5.3 / 0.39 / -30.2 | 100% |
| Trend(N)+OI sma20 [naive OI] {'N': 50} | 4.3 / 0.55 / -9.0 | 1.3 / 0.23 / -7.8 | -0.3 / -0.02 / -6.0 | 2.1 / 0.33 / -9.5 | 28% |
| Trend(N)+OI chg5 [naive OI] {'N': 50} | 4.2 / 0.51 / -9.9 | 5.5 / 0.93 / -3.6 | -3.5 / -0.57 / -12.0 | 1.9 / 0.29 / -12.0 | 31% |
| SMA cross 50/200 [L/S] {'a': 20, 'b': 100} | 8.0 / 0.48 / -29.0 | -6.8 / -0.42 / -21.7 | 4.3 / 0.37 / -15.8 | 3.2 / 0.27 / -29.0 | 100% |
| ADX/DI trend (14,25) [L/S] {'w': 14, 'th': 30} | 5.5 / 0.43 / -19.0 | -4.7 / -0.77 / -12.4 | -2.3 / -0.25 / -10.2 | 0.4 / 0.10 / -28.4 | 23% |
| Time-series momentum 252d [L/S] {'w': 63} | 6.3 / 0.40 / -27.3 | 3.4 / 0.31 / -18.8 | -9.0 / -0.60 / -26.0 | 0.3 / 0.10 / -31.2 | 100% |
| Stochastic mean-rev (14,20/80) {'w': 14, 'lo': 30, 'hi': 70} | 3.7 / 0.31 / -33.8 | -1.9 / -0.13 / -11.6 | 1.1 / 0.16 / -13.4 | 1.5 / 0.18 / -33.8 | 42% |
| IBS mean-reversion {'lo': 0.1, 'hi': 0.8} | 2.6 / 0.31 / -11.7 | 1.1 / 0.25 / -6.1 | 2.9 / 0.46 / -7.9 | 2.3 / 0.33 / -11.7 | 18% |
| Buy-the-dip (-1.5 sigma) {'th': 1.0} | 1.8 / 0.25 / -11.2 | -0.5 / -0.04 / -6.9 | 3.2 / 0.47 / -8.5 | 1.7 / 0.26 / -11.2 | 16% |
| RSI(14) 30/50 mean-rev {'w': 21, 'lo': 30, 'hi': 60} | 0.5 / 0.11 / -31.5 | 0.0 / 0.00 / 0.0 | -4.4 / -0.42 / -18.8 | -1.3 / -0.05 / -31.5 | 23% |

**Scoreboard: does the tuned strategy beat futures buy-and-hold (higher CAGR, higher Sharpe and shallower MaxDD) in each period, and is its CAGR positive?**

| Strategy | beats B&H on CAGR+Sharpe+MaxDD: Train | Valid | Test | Positive CAGR: Train/Valid/Test |
|---|---|---|---|---|
| ADX/DI trend (14,25) [L/S] | n | n | Y | +/-/- |
| ADX/DI trend (14,25) [long-only] | n | n | Y | +/+/- |
| Bollinger breakout (20,2) | n | n | n | +/+/- |
| Bollinger mean-rev (20,2) | n | n | Y | +/-/- |
| Buy-the-dip (-1.5 sigma) | n | n | Y | +/-/+ |
| Connors RSI(2) 10/70 | n | n | n | +/+/- |
| Donchian 20/10 (turtle) | n | n | n | +/+/- |
| Donchian 55/20 | n | n | n | +/+/- |
| EMA cross 12/26 [L/S] | Y | n | n | +/+/- |
| EMA cross 12/26 [long-only] | Y | Y | n | +/+/- |
| IBS mean-reversion | n | n | Y | +/+/+ |
| Keltner breakout (20,2) | n | Y | n | +/+/- |
| Long build-up (price&OI up over k) [expiry-adj OI] | Y | Y | n | +/+/- |
| Long build-up (price&OI up over k) [naive OI] | n | n | n | +/+/- |
| MACD 12/26/9 [L/S] | Y | Y | n | +/+/- |
| MACD 12/26/9 [long-only] | Y | Y | n | +/+/- |
| Price > 200DMA [L/S] | Y | n | n | +/-/- |
| Price > 200DMA [long-only] | Y | n | n | +/+/- |
| RSI(14) 30/50 mean-rev | n | n | n | +/-/- |
| SMA cross 20/50 [L/S] | Y | n | Y | +/-/+ |
| SMA cross 20/50 [long-only] | Y | n | Y | +/-/- |
| SMA cross 50/200 [L/S] | n | n | Y | +/-/+ |
| SMA cross 50/200 [long-only] | Y | n | Y | +/+/+ |
| Stochastic mean-rev (14,20/80) | n | n | Y | +/-/+ |
| Supertrend daily (10,3) [L/S] | n | Y | n | +/+/- |
| Supertrend daily (10,3) [long-only] | Y | Y | n | +/+/- |
| Time-series momentum 252d [L/S] | n | n | n | +/+/- |
| Time-series momentum 252d [long-only] | n | n | n | +/+/- |
| Trend(50) only [no OI] | Y | n | n | +/+/- |
| Trend(N)+OI chg1 [expiry-adj OI] | n | n | n | +/+/- |
| Trend(N)+OI chg1 [naive OI] | n | n | Y | +/-/- |
| Trend(N)+OI chg5 [expiry-adj OI] | Y | Y | n | +/+/- |
| Trend(N)+OI chg5 [naive OI] | n | n | n | +/+/- |
| Trend(N)+OI sma20 [expiry-adj OI] | Y | n | n | +/+/- |
| Trend(N)+OI sma20 [naive OI] | n | n | Y | +/+/- |

Note that "beats buy-and-hold" in test is easy: buy-and-hold lost money. No row is Y/Y/Y. The only two rows with positive CAGR in all three periods are IBS mean-reversion (1 to 3% a year, losing to buy-and-hold in train and valid) and SMA 50/200 long-only (11.2% in train but only 0.3% in valid and 0.6% in test).

## 5. Costs

Per side (fraction of notional): brokerage 0.0012% + exchange 0.0019% + SEBI 0.0001% + GST 18% on those + slippage 0.0100%; stamp 0.0020% on buys; STT on sells 0.010% (to Mar 2023), 0.0125% (Apr 2023-Sep 2024), 0.020% (from Oct 2024). Round trip today (STT 0.02%): 0.050% of notional (about 11.9 index points at 24,000). Rolling a held position costs one extra round trip + 0.01% spread = 0.060%.

| Strategy | Gross (no costs) full | Net, slippage 0.01%/side full | Net, slippage 0.03%/side full | Round-trips (full) | Cost drag %/yr |
|---|---|---|---|---|---|
| Buy & Hold futures | 5.0% / 0.37 | 4.4% / 0.34 | 3.9% / 0.31 | 0 | 0.67 |
| Trend(50)+rising OI (5d), expiry-adjusted OI | 5.0% / 0.61 | 4.0% / 0.50 | 3.2% / 0.41 | 140 | 0.96 |
| Trend(50)+rising OI (5d), naive OI | 2.9% / 0.42 | 1.9% / 0.29 | 0.9% / 0.17 | 153 | 1.00 |
| Trend(50) only (no OI) | 5.8% / 0.62 | 5.1% / 0.55 | 4.5% / 0.49 | 74 | 0.73 |
| LOCKED: MACD 12/26/9 [long-only] {'a': 16, 'b': 40, 's': 9} | 6.9% / 0.70 | 6.2% / 0.64 | 5.7% / 0.59 | 62 | 0.64 |
| LOCKED: Supertrend daily (10,3) [long-only] {'w': 7, 'm': 2.0} | 6.8% / 0.72 | 6.2% / 0.66 | 5.7% / 0.61 | 56 | 0.64 |
| LOCKED: Trend(N)+OI chg5 [expiry-adj OI] {'N': 50} | 5.0% / 0.61 | 4.0% / 0.50 | 3.2% / 0.41 | 140 | 0.96 |

- Trend(50)+rising OI makes about 140 round trips over the full period, so costs reduce its CAGR by roughly 1 percentage point a year. Buy-and-hold loses about 0.7 points a year, from rolls.
- Doubling the slippage assumption to 0.03% per side takes the headline strategy's full-period CAGR from 4.0% to 3.2%. Costs are not what decides the result; the test-period loss is.

## 6. Trend(50) + rising OI: the exact test the checklist asked for

Strategy as tested: long when close is above its 50-day average **and** total Nifty futures OI is higher than 5 trading days ago. Flat otherwise. (I could not reproduce the earlier 9.4% figure; its exact definition and data were not shared. The closest comparable full-period net figure here is 4.0% CAGR.)

| Strategy | Train CAGR/Sharpe/MaxDD | Valid | Test | Full | Exposure |
|---|---|---|---|---|---|
| Buy & Hold futures | 11.0 / 0.62 / -40.7 | 6.0 / 0.48 / -17.8 | -4.8 / -0.28 / -25.9 | 4.4 / 0.34 / -40.7 | 100% |
| Trend(50)+rising OI (5d), expiry-adjusted OI | 11.3 / 1.11 / -11.7 | 10.1 / 1.47 / -4.4 | -8.5 / -1.15 / -23.9 | 4.0 / 0.50 / -23.9 | 43% |
| Trend(50)+rising OI (5d), naive OI | 4.2 / 0.51 / -9.9 | 5.5 / 0.93 / -3.6 | -3.5 / -0.57 / -12.0 | 1.9 / 0.29 / -12.0 | 31% |
| Trend(50) only (no OI) | 15.1 / 1.31 / -12.6 | 1.6 / 0.22 / -16.8 | -4.6 / -0.50 / -15.7 | 5.1 / 0.55 / -17.7 | 58% |
| LOCKED: MACD 12/26/9 [long-only] {'a': 16, 'b': 40, 's': 9} | 15.9 / 1.30 / -10.3 | 12.6 / 1.37 / -9.8 | -9.1 / -1.05 / -25.2 | 6.2 / 0.64 / -25.5 | 50% |
| LOCKED: Supertrend daily (10,3) [long-only] {'w': 7, 'm': 2.0} | 12.4 / 1.13 / -13.2 | 13.8 / 1.43 / -11.1 | -6.1 / -0.71 / -19.1 | 6.2 / 0.66 / -19.1 | 55% |
| LOCKED: Trend(N)+OI chg5 [expiry-adj OI] {'N': 50} | 11.3 / 1.11 / -11.7 | 10.1 / 1.47 / -4.4 | -8.5 / -1.15 / -23.9 | 4.0 / 0.50 / -23.9 | 43% |

### 6.1 Parameter sweep (N = 30, 40, 50, 60, 80), three OI definitions, expiry-adjusted vs naive OI

| Variant | N | Train CAGR/Sh/DD | Valid | Test | Beats B&H (T/V/Te)? |
|---|---|---|---|---|---|
| Trend(N)+OI chg5 [expiry-adj OI] | 30 | 5.6 / 0.59 / -16.3 | 12.4 / 1.72 / -5.9 | -10.3 / -1.35 / -28.8 | n/Y/n |
| Trend(N)+OI chg5 [expiry-adj OI] | 40 | 7.7 / 0.78 / -12.9 | 10.8 / 1.55 / -4.5 | -9.5 / -1.22 / -26.6 | n/Y/n |
| Trend(N)+OI chg5 [expiry-adj OI] | 50 | 11.3 / 1.11 / -11.7 | 10.1 / 1.47 / -4.4 | -8.5 / -1.15 / -23.9 | Y/Y/n |
| Trend(N)+OI chg5 [expiry-adj OI] | 60 | 10.4 / 1.03 / -8.7 | 8.1 / 1.18 / -4.5 | -7.0 / -0.92 / -19.3 | n/Y/n |
| Trend(N)+OI chg5 [expiry-adj OI] | 80 | 8.0 / 0.82 / -10.1 | 11.0 / 1.55 / -5.1 | -7.2 / -0.94 / -19.8 | n/Y/n |
| Trend(N)+OI chg5 [naive OI] | 30 | 0.4 / 0.09 / -13.0 | 6.8 / 1.11 / -5.3 | -5.1 / -0.89 / -15.6 | n/Y/n |
| Trend(N)+OI chg5 [naive OI] | 40 | 2.4 / 0.32 / -12.6 | 5.9 / 0.99 / -4.6 | -4.4 / -0.73 / -14.6 | n/n/n |
| Trend(N)+OI chg5 [naive OI] | 50 | 4.2 / 0.51 / -9.9 | 5.5 / 0.93 / -3.6 | -3.5 / -0.57 / -12.0 | n/n/n |
| Trend(N)+OI chg5 [naive OI] | 60 | 2.7 / 0.35 / -9.7 | 3.8 / 0.64 / -4.0 | -2.5 / -0.39 / -11.1 | n/n/n |
| Trend(N)+OI chg5 [naive OI] | 80 | -1.6 / -0.14 / -17.1 | 6.3 / 1.03 / -4.7 | -3.2 / -0.49 / -11.5 | n/Y/n |
| Trend(N)+OI chg1 [expiry-adj OI] | 30 | 0.5 / 0.10 / -23.6 | 4.0 / 0.55 / -13.5 | -7.2 / -1.05 / -20.0 | n/n/n |
| Trend(N)+OI chg1 [expiry-adj OI] | 40 | 2.2 / 0.28 / -20.8 | 2.1 / 0.31 / -11.5 | -4.9 / -0.69 / -14.4 | n/n/n |
| Trend(N)+OI chg1 [expiry-adj OI] | 50 | 9.7 / 1.01 / -10.8 | 0.4 / 0.10 / -10.7 | -2.9 / -0.42 / -12.3 | n/n/n |
| Trend(N)+OI chg1 [expiry-adj OI] | 60 | 8.2 / 0.88 / -11.4 | 1.7 / 0.28 / -8.4 | -1.4 / -0.18 / -8.2 | n/n/Y |
| Trend(N)+OI chg1 [expiry-adj OI] | 80 | 5.5 / 0.61 / -11.9 | 3.6 / 0.53 / -7.8 | -1.8 / -0.24 / -9.6 | n/n/Y |
| Trend(N)+OI chg1 [naive OI] | 30 | -0.0 / 0.05 / -24.4 | 0.7 / 0.13 / -13.5 | -5.5 / -0.83 / -17.9 | n/n/n |
| Trend(N)+OI chg1 [naive OI] | 40 | 2.1 / 0.27 / -19.5 | -0.3 / 0.00 / -12.0 | -3.6 / -0.51 / -11.7 | n/n/n |
| Trend(N)+OI chg1 [naive OI] | 50 | 8.1 / 0.90 / -11.0 | -1.9 / -0.23 / -11.2 | -0.8 / -0.10 / -10.9 | n/n/Y |
| Trend(N)+OI chg1 [naive OI] | 60 | 6.7 / 0.76 / -11.2 | -0.6 / -0.06 / -9.3 | 0.6 / 0.12 / -7.2 | n/n/Y |
| Trend(N)+OI chg1 [naive OI] | 80 | 4.5 / 0.52 / -11.6 | 0.9 / 0.16 / -9.3 | -0.2 / -0.00 / -8.7 | n/n/Y |
| Trend(N)+OI sma20 [expiry-adj OI] | 30 | 5.9 / 0.56 / -23.6 | 12.6 / 1.45 / -7.4 | -5.1 / -0.60 / -16.5 | n/Y/n |
| Trend(N)+OI sma20 [expiry-adj OI] | 40 | 8.6 / 0.78 / -19.5 | 8.5 / 0.99 / -9.7 | -4.1 / -0.47 / -14.6 | n/Y/n |
| Trend(N)+OI sma20 [expiry-adj OI] | 50 | 13.5 / 1.22 / -13.3 | 5.8 / 0.72 / -10.9 | -3.3 / -0.36 / -11.6 | Y/n/n |
| Trend(N)+OI sma20 [expiry-adj OI] | 60 | 10.6 / 0.97 / -12.1 | 7.6 / 0.95 / -8.8 | -1.9 / -0.20 / -10.2 | n/Y/Y |
| Trend(N)+OI sma20 [expiry-adj OI] | 80 | 8.2 / 0.77 / -17.7 | 9.7 / 1.19 / -7.4 | -2.9 / -0.31 / -10.6 | n/Y/n |
| Trend(N)+OI sma20 [naive OI] | 30 | 0.4 / 0.10 / -13.2 | 5.8 / 0.90 / -4.7 | -1.0 / -0.18 / -8.1 | n/n/Y |
| Trend(N)+OI sma20 [naive OI] | 40 | 2.9 / 0.38 / -11.7 | 3.9 / 0.61 / -6.9 | -0.9 / -0.16 / -7.3 | n/n/Y |
| Trend(N)+OI sma20 [naive OI] | 50 | 4.3 / 0.55 / -9.0 | 1.3 / 0.23 / -7.8 | -0.3 / -0.02 / -6.0 | n/n/Y |
| Trend(N)+OI sma20 [naive OI] | 60 | 0.9 / 0.14 / -9.8 | 0.6 / 0.13 / -8.7 | -0.3 / -0.03 / -5.7 | n/n/Y |
| Trend(N)+OI sma20 [naive OI] | 80 | -3.1 / -0.34 / -20.6 | 1.7 / 0.29 / -9.7 | 0.1 / 0.04 / -5.7 | n/n/Y |
| Trend(50) only [no OI] | 30 | 8.5 / 0.75 / -18.0 | 7.3 / 0.81 / -16.2 | -8.2 / -0.93 / -22.9 | n/Y/n |
| Trend(50) only [no OI] | 40 | 10.4 / 0.90 / -16.5 | 4.5 / 0.51 / -15.0 | -7.4 / -0.84 / -20.4 | n/n/n |
| Trend(50) only [no OI] | 50 | 15.1 / 1.31 / -12.6 | 1.6 / 0.22 / -16.8 | -4.6 / -0.50 / -15.7 | Y/n/n |
| Trend(50) only [no OI] | 60 | 13.5 / 1.14 / -12.1 | 2.4 / 0.31 / -14.9 | -2.8 / -0.29 / -10.7 | Y/n/n |
| Trend(50) only [no OI] | 80 | 9.4 / 0.82 / -15.3 | 5.9 / 0.69 / -7.7 | -3.6 / -0.40 / -11.8 | n/n/n |

Reading it:
- With the 5-day OI definition and adjusted OI, every N is strong in valid (8 to 12% CAGR, drawdown about -4 to -6%) but every N loses in test (-7% to -10%).
- In train, only N=50 beats buy-and-hold on all three metrics. N=60 comes close on Sharpe and drawdown but gives up 0.6 points of CAGR.
- Adding OI to a plain trend filter helped in valid and did not help in test: Trend(50) only lost 4.6%, and the OI version lost 8.5%.

### 6.2 Expiry effect on OI

| OI signal | Share 'OI rising' on first day after expiry | Share on all other days | Share 'rising' in 5 days after expiry (5d change) | Share on other days |
|---|---|---|---|---|
| Naive total OI | 1% | 64% | 11% | 71% |
| Expiry-adjusted OI | 77% | 64% | 91% | 71% |

116 monthly expiries; naive total OI falls by 23% on average on the day after expiry. Headline strategy: days where naive and adjusted signals differ: 277 of 2367.

- **Problem:** each month the expiring contract's OI disappears from the file. Total OI therefore drops sharply right after expiry, and a naive "OI rising" test is false almost every time. The signal flips because of the calendar, not because of positioning.
- **Fix used:** an expiry-adjusted OI series that adds up only the day-to-day OI change of contracts present on both days. The expiring contract's removal then no longer counts as a drop.
- **Residual bias:** the adjusted series slightly overstates "rising" right after expiry (91% of days vs 71%), because the newly listed far contract starts near zero and its build-up counts as new OI. A cleaner treatment (for example excluding the first 3 to 5 days after expiry) is a possible next step.
- **Consequence:** the headline result depends on this choice (train 11.3% adjusted vs 4.2% naive), so I show both in every table.

### 6.3 Look-ahead check

Poison test: for 12 random cut dates, every price/VIX/OI value after the cut was replaced by random numbers; 432 (strategy x cut) signals were recomputed and compared up to the cut: 0 mismatches. Position at day h equals signal at close h-1 (fills at the next open): True.

- **How the test works:** it replaces all price, VIX and OI values after a chosen date with random numbers, recomputes every strategy's signals, and confirms the signals up to that date do not change. A signal that peeked at future data would change.
- **OI timing:** OI for day t enters the signal at the close of t, and the order is placed at the open of t+1, so the after-close publication of OI is respected.

## 7. Overfitting accounting

Configurations evaluated in this report: 323 (each family's default plus its parameter grid, long-only and long/short). Earlier exploratory runs on the same data (price-only signals, ~2031 configurations) also saw the test period, so N for deflation = 2354. Expected best Sharpe from pure luck over N=2354 trials on the train+valid sample: 1.33 (annualised).

| Strategy | Train+valid Sharpe (ann.) | Deflated Sharpe prob. (true Sharpe > 0 after N trials) | Test Sharpe (ann.) | Test CAGR |
|---|---|---|---|---|
| Trend(50)+rising OI (5d), expiry-adjusted OI | 1.19 | 0.37 | -1.15 | -8.5% |
| Trend(50)+rising OI (5d), naive OI | 0.62 | 0.05 | -0.57 | -3.5% |
| Trend(50) only (no OI) | 0.98 | 0.21 | -0.50 | -4.6% |
| LOCKED: MACD 12/26/9 [long-only] {'a': 16, 'b': 40, 's': 9} | 1.31 | 0.48 | -1.05 | -9.1% |
| LOCKED: Supertrend daily (10,3) [long-only] {'w': 7, 'm': 2.0} | 1.22 | 0.40 | -0.71 | -6.1% |
| LOCKED: Trend(N)+OI chg5 [expiry-adj OI] {'N': 50} | 1.19 | 0.37 | -1.15 | -8.5% |

- **Reading the deflated Sharpe:** it is the probability that the true Sharpe is above zero once the number of trials is taken into account. Values near 0.95 or higher would be strong evidence. All the strategies here are far below that (0.05 to 0.48), and then lost money in the untouched test.
- **Frozen picks (chosen on train+valid before test was shown):** (1) MACD 12/26/9 long-only with a=16, b=40, s=9, (2) Supertrend daily long-only with w=7, m=2.0, (3) Trend(50)+rising OI with expiry-adjusted OI. Test results are in section 6 and none beat buy-and-hold.
- **Not pristine:** earlier exploratory runs on the same data looked at the test period, so test is no longer fully independent for price-based ideas. I counted those trials in N.

## 8. Regime-wise results (annualised return, Sharpe in brackets; `*` = fewer than 30 days)

| Regime | Period | Days | Buy & Hold | Trend(50)+rising OI (adj.) | Trend(50) only | MACD 12/26/9 LO | Supertrend daily (10,3) LO | Trend(N)+OI chg5 [expiry-adj OI] |
|---|---|---|---|---|---|---|---|---|
| Trend (price vs 200DMA): Bear | train | 266 | 9.5% (Sh 0.3) | 10.9% (Sh 1.0) | 19.6% (Sh 1.7) | 27.0% (Sh 1.5) | 14.5% (Sh 1.2) | 10.9% (Sh 1.0) |
| Trend (price vs 200DMA): Bear | valid | 163 | 24.1% (Sh 1.4) | 0.1% (Sh 0.0) | 7.9% (Sh 1.3) | 21.5% (Sh 2.4) | 23.9% (Sh 2.7) | 0.1% (Sh 0.0) |
| Trend (price vs 200DMA): Bear | test | 340 | -0.8% (Sh -0.0) | -0.7% (Sh -0.2) | 2.0% (Sh 0.3) | -4.2% (Sh -0.5) | 4.1% (Sh 0.5) | -0.7% (Sh -0.2) |
| Trend (price vs 200DMA): Bull | train | 661 | 13.7% (Sh 1.0) | 11.3% (Sh 1.1) | 12.8% (Sh 1.1) | 10.8% (Sh 1.3) | 11.5% (Sh 1.1) | 11.3% (Sh 1.1) |
| Trend (price vs 200DMA): Bull | valid | 329 | -1.6% (Sh -0.1) | 14.7% (Sh 1.9) | -0.9% (Sh -0.1) | 7.7% (Sh 0.9) | 8.1% (Sh 0.9) | 14.7% (Sh 1.9) |
| Trend (price vs 200DMA): Bull | test | 363 | -7.0% (Sh -0.6) | -16.1% (Sh -1.7) | -10.2% (Sh -1.0) | -13.8% (Sh -1.7) | -15.4% (Sh -1.7) | -16.1% (Sh -1.7) |
| Volatility (India VIX): High >22 | train | 205 | 31.4% (Sh 0.9) | 26.5% (Sh 2.0) | 34.0% (Sh 2.3) | 29.0% (Sh 1.6) | 29.4% (Sh 1.9) | 26.5% (Sh 2.0) |
| Volatility (India VIX): High >22 | valid | 48 | 16.1% (Sh 0.6) | -6.0% (Sh -2.3) | -7.4% (Sh -1.3) | 19.7% (Sh 2.2) | 27.1% (Sh 2.8) | -6.0% (Sh -2.3) |
| Volatility (India VIX): High >22 | test | 20 | 98%* | -56%* | -56%* | -10%* | -29%* | -56%* |
| Volatility (India VIX): Low <15 | train | 278 | 2.0% (Sh 0.2) | 11.6% (Sh 1.4) | 9.4% (Sh 1.0) | 10.4% (Sh 1.4) | 7.3% (Sh 0.9) | 11.6% (Sh 1.4) |
| Volatility (India VIX): Low <15 | valid | 249 | 7.2% (Sh 0.7) | 9.4% (Sh 1.5) | 10.2% (Sh 1.4) | 12.7% (Sh 1.8) | 17.7% (Sh 2.6) | 9.4% (Sh 1.5) |
| Volatility (India VIX): Low <15 | test | 491 | -20.0% (Sh -1.6) | -7.2% (Sh -1.1) | -7.2% (Sh -1.0) | -12.2% (Sh -1.6) | -8.5% (Sh -1.1) | -7.2% (Sh -1.1) |
| Volatility (India VIX): Mid 15-22 | train | 444 | 10.3% (Sh 0.6) | 3.9% (Sh 0.4) | 9.2% (Sh 0.9) | 12.4% (Sh 1.1) | 7.6% (Sh 0.8) | 3.9% (Sh 0.4) |
| Volatility (India VIX): Mid 15-22 | valid | 195 | 4.2% (Sh 0.3) | 14.3% (Sh 1.8) | -6.2% (Sh -0.5) | 10.0% (Sh 0.9) | 4.3% (Sh 0.4) | 14.3% (Sh 1.8) |
| Volatility (India VIX): Mid 15-22 | test | 192 | 26.4% (Sh 1.7) | -7.5% (Sh -0.8) | 8.5% (Sh 0.8) | -1.4% (Sh -0.1) | 2.8% (Sh 0.3) | -7.5% (Sh -0.8) |
| Momentum (20d return): Down <-3% | train | 142 | -22.3% (Sh -0.6) | -1.0% (Sh -1.4) | -1.0% (Sh -1.5) | 21.5% (Sh 1.7) | -3.5% (Sh -1.0) | -1.0% (Sh -1.4) |
| Momentum (20d return): Down <-3% | valid | 102 | 16.2% (Sh 0.9) | -0.1% (Sh -1.6) | -4.7% (Sh -1.6) | 5.6% (Sh 1.4) | 1.3% (Sh 0.2) | -0.1% (Sh -1.6) |
| Momentum (20d return): Down <-3% | test | 137 | -8.5% (Sh -0.5) | 0.0% (Sh 0.0) | 0.0% (Sh 0.0) | 2.2% (Sh 1.0) | 1.1% (Sh 0.4) | 0.0% (Sh 0.0) |
| Momentum (20d return): Flat | train | 449 | 15.8% (Sh 1.1) | 14.4% (Sh 1.4) | 15.6% (Sh 1.4) | 10.8% (Sh 1.1) | 12.9% (Sh 1.3) | 14.4% (Sh 1.4) |
| Momentum (20d return): Flat | valid | 249 | -5.8% (Sh -0.5) | -0.8% (Sh -0.1) | -8.0% (Sh -1.0) | 8.1% (Sh 1.1) | 9.3% (Sh 1.1) | -0.8% (Sh -0.1) |
| Momentum (20d return): Flat | test | 467 | 4.4% (Sh 0.4) | -3.8% (Sh -0.5) | -0.8% (Sh -0.1) | -6.2% (Sh -0.8) | -2.6% (Sh -0.3) | -3.8% (Sh -0.5) |
| Momentum (20d return): Up >3% | train | 336 | 22.7% (Sh 1.5) | 12.1% (Sh 1.0) | 20.2% (Sh 1.5) | 19.2% (Sh 1.4) | 18.2% (Sh 1.3) | 12.1% (Sh 1.0) |
| Momentum (20d return): Up >3% | valid | 141 | 22.6% (Sh 1.6) | 35.8% (Sh 3.8) | 24.6% (Sh 1.9) | 24.4% (Sh 1.8) | 29.1% (Sh 2.3) | 35.8% (Sh 3.8) |
| Momentum (20d return): Up >3% | test | 99 | -37.1% (Sh -2.3) | -43.3% (Sh -3.7) | -26.8% (Sh -2.0) | -39.2% (Sh -2.5) | -32.0% (Sh -2.3) | -43.3% (Sh -3.7) |
| Drawdown from high: DD >10% | train | 224 | 20.5% (Sh 0.6) | 12.6% (Sh 1.1) | 26.3% (Sh 2.2) | 32.8% (Sh 1.7) | 24.1% (Sh 1.8) | 12.6% (Sh 1.1) |
| Drawdown from high: DD >10% | valid | 104 | 35.4% (Sh 1.9) | -1.7% (Sh -1.8) | 8.5% (Sh 1.6) | 19.8% (Sh 2.0) | 18.3% (Sh 1.8) | -1.7% (Sh -1.8) |
| Drawdown from high: DD >10% | test | 384 | 0.1% (Sh 0.0) | 0.3% (Sh 0.1) | 2.3% (Sh 0.4) | -4.4% (Sh -0.5) | 4.7% (Sh 0.6) | 0.3% (Sh 0.1) |
| Drawdown from high: Near high | train | 703 | 9.9% (Sh 0.7) | 10.8% (Sh 1.1) | 11.0% (Sh 1.0) | 9.9% (Sh 1.2) | 8.6% (Sh 0.9) | 10.8% (Sh 1.1) |
| Drawdown from high: Near high | valid | 388 | -0.7% (Sh -0.1) | 12.9% (Sh 1.7) | 0.3% (Sh 0.0) | 10.3% (Sh 1.2) | 12.0% (Sh 1.3) | 12.9% (Sh 1.7) |
| Drawdown from high: Near high | test | 319 | -8.8% (Sh -0.7) | -19.4% (Sh -1.9) | -12.2% (Sh -1.1) | -15.0% (Sh -1.7) | -18.8% (Sh -2.0) | -19.4% (Sh -1.9) |

What the regimes show:
- **Trend-following earned its money in bull, low-vol and "up" regimes in train and valid** (for example Trend(50)+OI: 11.3% in train bull, 14.7% in valid bull) **and gave it back in test.** In the test-period bull regime it lost 16%/yr, against buy-and-hold's -7%.
- **It does not protect in high-VIX regimes.** In valid high-VIX (48 days) it lost 6%/yr while buy-and-hold gained 16%. The test high-VIX sample has only 20 days.
- **The edge in test is negative in "near high" and "up >3%" conditions.** Entries after a rally were followed by reversals. That is the pattern of a trend signal buying near the top in a choppy market.

## 9. Post-hoc check: panic-reversal (found earlier, re-run under the stricter next-open rule)

Two ideas, each long for one day: (a) India VIX up more than 12% in a day, (b) 10-day price drop of more than 2.5% while above the 200DMA. These were found in earlier searches **with knowledge of the test period**, so treat this section as a hypothesis, not a validated result. It is not one of the frozen picks.

| Strategy | Train CAGR/Sharpe/MaxDD | Valid | Test | Full | Exposure |
|---|---|---|---|---|---|
| VIX spike >12% (long 1 day) | 1.4 / 0.23 / -11.2 | -0.5 / -0.13 / -4.6 | 1.1 / 0.37 / -2.3 | 0.8 / 0.19 / -11.2 | 2% |
| 10-day drop >2.5% in uptrend (long 1 day) | 2.5 / 0.46 / -10.1 | 2.5 / 1.06 / -1.9 | 2.5 / 0.79 / -4.0 | 2.5 / 0.59 / -10.1 | 5% |
| Pair (equal weight) | 2.0 / 0.45 / -9.1 | 1.0 / 0.50 / -3.1 | 1.8 / 0.66 / -2.0 | 1.7 / 0.49 / -9.1 | 7% |
| Pair at 5x notional | 8.3 / 0.45 / -40.2 | 4.7 / 0.50 / -15.0 | 8.5 / 0.66 / -9.8 | 7.5 / 0.49 / -40.2 | 7% |

| Regime | Period | Days | Buy & Hold | Pair (1x) |
|---|---|---|---|---|
| Trend (price vs 200DMA): Bear | train | 266 | 9.5% (Sh 0.3) | -1.2% (Sh -0.2) |
| Trend (price vs 200DMA): Bear | valid | 163 | 24.1% (Sh 1.4) | 0.6% (Sh 0.2) |
| Trend (price vs 200DMA): Bear | test | 340 | -0.8% (Sh -0.0) | 0.6% (Sh 0.7) |
| Trend (price vs 200DMA): Bull | train | 661 | 13.7% (Sh 1.0) | 3.5% (Sh 0.9) |
| Trend (price vs 200DMA): Bull | valid | 329 | -1.6% (Sh -0.1) | 1.3% (Sh 0.8) |
| Trend (price vs 200DMA): Bull | test | 363 | -7.0% (Sh -0.6) | 2.9% (Sh 0.8) |
| Volatility (India VIX): High >22 | train | 205 | 31.4% (Sh 0.9) | 10.5% (Sh 1.2) |
| Volatility (India VIX): High >22 | valid | 48 | 16.1% (Sh 0.6) | 0.0% (Sh 0.0) |
| Volatility (India VIX): High >22 | test | 20 | 98%* | 48%* |
| Volatility (India VIX): Low <15 | train | 278 | 2.0% (Sh 0.2) | -1.7% (Sh -1.2) |
| Volatility (India VIX): Low <15 | valid | 249 | 7.2% (Sh 0.7) | 0.4% (Sh 0.5) |
| Volatility (India VIX): Low <15 | test | 491 | -20.0% (Sh -1.6) | -0.0% (Sh -0.0) |
| Volatility (India VIX): Mid 15-22 | train | 444 | 10.3% (Sh 0.6) | 0.7% (Sh 0.2) |
| Volatility (India VIX): Mid 15-22 | valid | 195 | 4.2% (Sh 0.3) | 2.1% (Sh 1.1) |
| Volatility (India VIX): Mid 15-22 | test | 192 | 26.4% (Sh 1.7) | 1.7% (Sh 0.9) |
| Momentum (20d return): Down <-3% | train | 142 | -22.3% (Sh -0.6) | 8.4% (Sh 0.8) |
| Momentum (20d return): Down <-3% | valid | 102 | 16.2% (Sh 0.9) | 7.5% (Sh 2.8) |
| Momentum (20d return): Down <-3% | test | 137 | -8.5% (Sh -0.5) | -0.6% (Sh -0.3) |
| Momentum (20d return): Flat | train | 449 | 15.8% (Sh 1.1) | 1.2% (Sh 0.4) |
| Momentum (20d return): Flat | valid | 249 | -5.8% (Sh -0.5) | -1.0% (Sh -0.4) |
| Momentum (20d return): Flat | test | 467 | 4.4% (Sh 0.4) | 2.9% (Sh 0.9) |
| Momentum (20d return): Up >3% | train | 336 | 22.7% (Sh 1.5) | 0.7% (Sh 0.5) |
| Momentum (20d return): Up >3% | valid | 141 | 22.6% (Sh 1.6) | 0.0% (Sh 0.0) |
| Momentum (20d return): Up >3% | test | 99 | -37.1% (Sh -2.3) | 0.0% (Sh 0.0) |
| Drawdown from high: DD >10% | train | 224 | 20.5% (Sh 0.6) | 3.7% (Sh 0.5) |
| Drawdown from high: DD >10% | valid | 104 | 35.4% (Sh 1.9) | 4.4% (Sh 1.9) |
| Drawdown from high: DD >10% | test | 384 | 0.1% (Sh 0.0) | 0.8% (Sh 0.8) |
| Drawdown from high: Near high | train | 703 | 9.9% (Sh 0.7) | 1.6% (Sh 0.5) |
| Drawdown from high: Near high | valid | 388 | -0.7% (Sh -0.1) | 0.1% (Sh 0.1) |
| Drawdown from high: Near high | test | 319 | -8.8% (Sh -0.7) | 3.0% (Sh 0.8) |

- **Under next-open fills the edge is smaller than the 3 to 4% unlevered figure I reported before** (which assumed same-close fills). It is about 2.0%, 1.0% and 1.8% CAGR in train, valid and test, with Sharpe 0.45, 0.50 and 0.66.
- **It is in the market only about 7% of days** and has a tiny drawdown (-9% to -2%) because it is mostly flat.
- **5x leverage:** this produced a -40% drawdown in train (March 2020), so it is not a safe way to scale it.
- **Why it does not clear the gate:** it earns far less than buy-and-hold in train and valid (2.0% vs 11.0% and 1.0% vs 6.0%).
- **Where it does help:** it was positive in all three periods overall and in test, when buy-and-hold lost. Regime-wise it is slightly negative in the train bear regime and in low-VIX train days, so it is not a clean crisis hedge.

## 10. Limitations

- **Daily data only.** Fills assume the first print at the open plus 0.01% slippage per side. Real fills in volatile opens can be worse.
- **One instrument and one 8.6-year window.** There are 116 monthly expiries and only three regimes' worth of data; 2020 is the only crash, and it sits in train.
- **No margin, lot-size, funding or tax modeling.** Returns are on notional exposure.
- **Total OI includes calendar-spread and hedging positions.** It is not a clean directional-positioning measure.
- **Regime thresholds** (VIX 15/22, momentum +/-3%, drawdown 10%) were fixed once and not tuned. Regime results use many small cells, so single numbers are noisy.
- **The test period is not completely untouched** (see section 7).

## 11. Recommended next steps

1. **Do not start paper trading on Trend(50)+rising OI as it stands.** It fails the gate (does not beat futures buy-and-hold after costs in all periods).
2. **Get older futures data (2012 to 2017).** This gives more regimes and a fresh out-of-sample period. It needs a download from the NSE archive, which I did not run. The earlier request was blocked by the permission check.
3. **Run a proper walk-forward test** (re-tune each year, trade the next year) on the OI family, with a stricter expiry rule such as ignoring OI for the first 3 to 5 days after expiry.
4. **If paper trading is wanted anyway,** the panic-reversal pair is the only candidate that is positive in all three periods. Run it unlevered, with realistic expectations of about 2%/yr, as a test of execution rather than of returns.

## 12. Files

- Code: `scripts/report_futures.py` (all results), `scripts/build_report.py` (this document)
- Results: `results/report_tables.json`, `results/report_res.pkl`
- Earlier exploratory runs: `scripts/strategy_zoo.py`, `scripts/profit_search.py`, `scripts/research2.py`
