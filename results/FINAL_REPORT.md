# Nifty futures: final backtest report (2013-2026)

Instrument: NSE Nifty index futures only (continuous front month, rolled at expiry). Signals use data up to the close of day t; trades fill at the next open. All figures are net of brokerage, exchange and SEBI charges, GST, stamp duty, STT (rate by date) and 0.01% slippage per side, plus a roll cost. Returns are on notional exposure. Windows: train 2013-2021, valid 2022-2023, test 2024-2026, full 2013-2026 (2012 is warm-up). Cells show CAGR / Sharpe / max drawdown.

## 1. Bottom line

- No textbook strategy, no OI-based strategy, no non-textbook idea and no factor portfolio beat futures buy-and-hold after costs in every window.
- The only combination that was positive in every window is **IBS mean-reversion + a panic-reversal pair**. It is small, mostly flat and statistically unproven.
- **A 10% CAGR with a 15% drawdown was not reached.** At the Sharpe these strategies deliver (about 0.6 to 0.7), return is roughly Sharpe times volatility and drawdown is roughly 2.5 times volatility, so 10% needs about -30% drawdown and a -15% limit allows about 5%. Reaching both needs a Sharpe above 1.2 that holds out of sample, which was not found.
- Recommended next step: paper trade IBS + Pair for 2-3 months before any real money.

## 2. Recommended candidate: IBS + Pair

- **IBS mean-reversion:** go long at the close when IBS = (close - low) / (high - low) is below 0.1, exit when it is above 0.8. Parameters frozen from the train period.
- **Panic-reversal pair:** long for one day after (a) India VIX jumps more than 12% in a day, or (b) Nifty has fallen more than 2.5% over 10 days while still above its 200-day average. Equal weight of the two.
- **Combination:** 50/50 on risk capital, then one fixed sizing rule: scale to a target annual volatility using trailing 60-day volatility known at the prior close, with a leverage cap.

| Series | Train 2013-21 | Valid 2022-23 | Test 2024-26 | Full 2013-26 |
|---|---|---|---|---|
| Buy and hold futures | 7.4% / 0.48 / -40.7% | 6.0% / 0.48 / -17.8% | -4.8% / -0.28 / -25.9% | 4.6% / 0.35 / -40.7% |
| IBS alone | 3.6% / 0.47 / -13.8% | 1.1% / 0.25 / -6.1% | 3.1% / 0.50 / -7.9% | 3.2% / 0.45 / -13.8% |
| Pair alone | 1.7% / 0.48 / -12.9% | 1.0% / 0.50 / -3.1% | 1.8% / 0.66 / -2.0% | 1.6% / 0.50 / -12.9% |
| IBS + Pair, 1x | 2.7% / 0.54 / -12.1% | 1.1% / 0.41 / -3.1% | 2.5% / 0.70 / -3.8% | 2.4% / 0.54 / -12.1% |
| IBS + Pair, 6% vol target, 3x cap | 4.6% / 0.63 / -11.9% | 3.7% / 0.63 / -4.6% | 5.3% / 0.73 / -7.7% | 4.6% / 0.65 / -11.9% |
| **IBS + Pair, 7% vol target, 3x cap** | 4.9% / 0.60 / -14.6% | 3.9% / 0.61 / -4.8% | 6.0% / 0.74 / -8.9% | **5.0% / 0.63 / -14.6%** |
| IBS + Pair, 8% vol target, 3x cap | 5.2% / 0.58 / -16.8% | 4.0% / 0.60 / -4.8% | 6.3% / 0.73 / -9.5% | 5.2% / 0.61 / -16.8% |

- The 7% setting fits a 15% drawdown limit: 5.0% a year against 4.6% for buy-and-hold, with a -14.6% drawdown against -40.7%.
- Block-bootstrap 90% range for the full-period Sharpe (8% setting): 0.25 to 1.04. Lower end above zero, but wide.
- Years negative at the 8% setting: 2016, 2018, 2023 and 2026 (2026 is partial); 10 of 14 years positive.
- It does not beat buy-and-hold in train or valid on CAGR. The advantage is lower risk and a better result in the 2024-26 down period.

## 3. Return versus drawdown: the trade-off

| Vol target / leverage cap | Avg leverage | Test 2024-26 | Full 2013-26 | Worst year |
|---|---|---|---|---|
| 7% / 3x | about 2x | 6.0% / 0.74 / -8.9% | 5.0% / 0.63 / -14.6% | -6.4% |
| 8% / 3x | 2.3x | 6.3% / 0.73 / -9.5% | 5.2% / 0.61 / -16.8% | -7.2% |
| 10% / 4x | 2.9x | 8.1% / 0.74 / -12.1% | 6.7% / 0.62 / -20.6% | -9.0% |
| 12% / 5x | 3.5x | 9.9% / 0.74 / -14.7% | 8.1% / 0.63 / -24.5% | -10.7% |
| 15% / 6x | 4.3x | 11.9% / 0.74 / -17.8% | 9.7% / 0.62 / -30.2% | -13.4% |

- The Sharpe stays near 0.6 at every size, so more return is more risk, not more skill.
- About 10% a year over the full period costs about a -30% drawdown, close to buy-and-hold's -40.7%.
- A drawdown brake (half size when equity is more than 7% below its peak) cut return by more than it cut drawdown and was dropped.
- These sleeves are in the market part of the time, so leverage lands on the active days. Margin and overnight gap risk are not modelled.

## 4. What did not work

**Textbook strategies and OI.** About 20 families (moving averages, MACD, RSI, Bollinger, Donchian, Supertrend, ADX, Stochastic, Keltner, momentum and others) win in 2013-2023 pockets and lose in 2024-26. Trend(50) + rising OI fails the gate of beating futures buy-and-hold after costs in all windows, the best N is not stable across 30/40/50/60/80, and the way expiry is handled materially changes the OI signal (naive total OI falls about 23-25% the day after each expiry).

**Non-textbook hypotheses (175 trials).** Term-structure spread, expiry-cycle windows, OI flush, volatility risk premium, volume capitulation, volatility-managed beta and a crowding gate.

| Hypothesis (best on train) | Train | Valid | Test |
|---|---|---|---|
| Spread-collapse long | 8.2% / 0.91 / -18.9% | -1.9% / -0.32 / -10.0% | 2.2% / 0.37 / -6.1% |
| Long in 5 days after expiry | 6.8% / 0.77 / -23.8% | 7.2% / 1.08 / -10.3% | -2.3% / -0.22 / -13.9% |
| Long in window before expiry | 5.5% / 0.60 / -17.9% | 4.0% / 0.54 / -9.9% | -3.6% / -0.38 / -15.4% |
| Beta unless crowded OI and weak trend | 11.0% / 0.88 / -23.1% | 2.7% / 0.33 / -15.1% | -7.7% / -0.84 / -21.9% |
| Buy and hold futures | 7.4% / 0.48 / -40.7% | 6.0% / 0.48 / -17.8% | -4.8% / -0.28 / -25.9% |

The two shortlisted ones (expiry windows) lost money on test. The OI-flush rule never triggered.

**Factor search, long-only and long/short (256 candidates).** 32 factors: returns over 1 to 250 days, 12-1 momentum, distance from moving averages, RSI, IBS, realised volatility, VIX level and change, VIX minus realised volatility, term-structure carry, volume, OI change, drawdown from the 252-day high and days to expiry. Each was used as long/flat or long/short, following or fading, with a median or tail trigger from rolling 252-day history.

- Best on train: carry spread (fade), Sharpe 0.87, then 0.07 on valid and 0.09 on test. With 256 zero-skill trials, a best Sharpe of about 1.0 is expected from luck alone.
- 13 candidates had train and valid Sharpe above 0.4; only 1 was positive on test. None of them was long/short.
- Shortlist portfolio at 1x: 5.8% train, 7.6% valid, **-5.5% test** (-15.9% drawdown). At a 7% vol target: -8.0% test, -22.9% drawdown.
- Yearly walk-forward 2016-2026 (top 10 by past-only Sharpe, re-picked each year): **0.2% CAGR**, Sharpe 0.07, against 5.0% for buy-and-hold.
- A four-strategy portfolio (IBS, Pair, spread-collapse, post-expiry window) looked strong on train (Sharpe 0.98) but lost 1.2% to 1.7% a year on test at every size, so it was discarded.

## 5. Overfitting controls

- Parameters were chosen on train only; shortlists required train and valid; the test period was shown once per search; no changes were made after seeing it.
- Trials counted: about 3,000 configurations across all work on this data (about 2,350 earlier, 175 non-textbook, 256 factors, plus a few portfolio variants). Deflated Sharpe for IBS and the pair was only 0.10-0.19.
- A poison test that replaced all data after a random cut with noise gave 0 signal mismatches, so no signal uses future data. OI is used only from the previous close.
- **The 2024-26 test period is not clean.** Earlier exploratory runs looked at it, and the choice of IBS and Pair was made after seeing their results. The test figures above are therefore optimistic. Only live or paper results are clean evidence.

## 6. Limitations

- Daily data, fills at the open plus 0.01% slippage per side. Real fills at volatile opens can be worse.
- One instrument; the 2020 crash appears once and 2022-2026 has few trending years.
- No margin, lot-size, funding or tax modelling; returns are on notional exposure.
- Roughly 11 IBS trades a year, so a 2-3 month paper trade gives only a handful of trades. Use it to check fills, signal timing and gaps at the open, not to judge profit.

## 7. Next steps

- Paper trade IBS + Pair at the 7% setting (start at 1x) for 2-3 months and compare against this backtest.
- Move to the 7% / 3x sizing only if paper results track the backtest. Treat 10% volatility or more as an explicit decision to accept a -20% to -30% drawdown.
- Stop searching this 14-year sample. New evidence has to come from untouched data or live results.

## 8. Files

- Code: `scripts/combo_final.py` (IBS + Pair and sizing), `scripts/factor_search.py` (256 factor candidates), `scripts/novel_search.py` (175 trials), `scripts/report_futures_ext.py` (baseline engine and earlier results).
- Data: `data/fut/nifty_fut.csv`, `data/fut/nifty_fut_2012_2017.csv`, `data/vix_ext.csv`.
- Results: `results/factor_search.pkl`, `results/novel_res.pkl`, `results/REPORT_FUTURES_2013_2026.pdf` (earlier full report).
