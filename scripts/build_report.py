import json
T = json.load(open('results/report_tables.json'))
doc = f"""# Nifty Futures: Popular Strategies and Trend(50) + Rising OI — Full Backtest Report

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

{T['A']}

## 4. Results — parameters tuned on train only

{T['B']}

**Scoreboard: does the tuned strategy beat futures buy-and-hold (higher CAGR, higher Sharpe and shallower MaxDD) in each period, and is its CAGR positive?**

{T['SCORE']}

Note that "beats buy-and-hold" in test is easy: buy-and-hold lost money. No row is Y/Y/Y. The only two rows with positive CAGR in all three periods are IBS mean-reversion (1 to 3% a year, losing to buy-and-hold in train and valid) and SMA 50/200 long-only (11.2% in train but only 0.3% in valid and 0.6% in test).

## 5. Costs

{T['COSTUNIT']}

{T['COST']}

- Trend(50)+rising OI makes about 140 round trips over the full period, so costs reduce its CAGR by roughly 1 percentage point a year. Buy-and-hold loses about 0.7 points a year, from rolls.
- Doubling the slippage assumption to 0.03% per side takes the headline strategy's full-period CAGR from 4.0% to 3.2%. Costs are not what decides the result; the test-period loss is.

## 6. Trend(50) + rising OI: the exact test the checklist asked for

Strategy as tested: long when close is above its 50-day average **and** total Nifty futures OI is higher than 5 trading days ago. Flat otherwise. (I could not reproduce the earlier 9.4% figure; its exact definition and data were not shared. The closest comparable full-period net figure here is 4.0% CAGR.)

{T['C']}

### 6.1 Parameter sweep (N = 30, 40, 50, 60, 80), three OI definitions, expiry-adjusted vs naive OI

{T['SWEEP']}

Reading it:
- With the 5-day OI definition and adjusted OI, every N is strong in valid (8 to 12% CAGR, drawdown about -4 to -6%) but every N loses in test (-7% to -10%).
- In train, only N=50 beats buy-and-hold on all three metrics. N=60 comes close on Sharpe and drawdown but gives up 0.6 points of CAGR.
- Adding OI to a plain trend filter helped in valid and did not help in test: Trend(50) only lost 4.6%, and the OI version lost 8.5%.

### 6.2 Expiry effect on OI

{T['EXP']}

{T['EXPN']}. {T['EXPDIFF']}

- **Problem:** each month the expiring contract's OI disappears from the file. Total OI therefore drops sharply right after expiry, and a naive "OI rising" test is false almost every time. The signal flips because of the calendar, not because of positioning.
- **Fix used:** an expiry-adjusted OI series that adds up only the day-to-day OI change of contracts present on both days. The expiring contract's removal then no longer counts as a drop.
- **Residual bias:** the adjusted series slightly overstates "rising" right after expiry (91% of days vs 71%), because the newly listed far contract starts near zero and its build-up counts as new OI. A cleaner treatment (for example excluding the first 3 to 5 days after expiry) is a possible next step.
- **Consequence:** the headline result depends on this choice (train 11.3% adjusted vs 4.2% naive), so I show both in every table.

### 6.3 Look-ahead check

{T['LOOK']}

- **How the test works:** it replaces all price, VIX and OI values after a chosen date with random numbers, recomputes every strategy's signals, and confirms the signals up to that date do not change. A signal that peeked at future data would change.
- **OI timing:** OI for day t enters the signal at the close of t, and the order is placed at the open of t+1, so the after-close publication of OI is respected.

## 7. Overfitting accounting

{T['TRIALS']}

{T['DSR']}

- **Reading the deflated Sharpe:** it is the probability that the true Sharpe is above zero once the number of trials is taken into account. Values near 0.95 or higher would be strong evidence. All the strategies here are far below that (0.05 to 0.48), and then lost money in the untouched test.
- **Frozen picks (chosen on train+valid before test was shown):** (1) MACD 12/26/9 long-only with a=16, b=40, s=9, (2) Supertrend daily long-only with w=7, m=2.0, (3) Trend(50)+rising OI with expiry-adjusted OI. Test results are in section 6 and none beat buy-and-hold.
- **Not pristine:** earlier exploratory runs on the same data looked at the test period, so test is no longer fully independent for price-based ideas. I counted those trials in N.

## 8. Regime-wise results (annualised return, Sharpe in brackets; `*` = fewer than 30 days)

{T['REG']}

What the regimes show:
- **Trend-following earned its money in bull, low-vol and "up" regimes in train and valid** (for example Trend(50)+OI: 11.3% in train bull, 14.7% in valid bull) **and gave it back in test.** In the test-period bull regime it lost 16%/yr, against buy-and-hold's -7%.
- **It does not protect in high-VIX regimes.** In valid high-VIX (48 days) it lost 6%/yr while buy-and-hold gained 16%. The test high-VIX sample has only 20 days.
- **The edge in test is negative in "near high" and "up >3%" conditions.** Entries after a rally were followed by reversals. That is the pattern of a trend signal buying near the top in a choppy market.

## 9. Post-hoc check: panic-reversal (found earlier, re-run under the stricter next-open rule)

Two ideas, each long for one day: (a) India VIX up more than 12% in a day, (b) 10-day price drop of more than 2.5% while above the 200DMA. These were found in earlier searches **with knowledge of the test period**, so treat this section as a hypothesis, not a validated result. It is not one of the frozen picks.

{T['POSTHOC']}

{T['REG_POSTHOC']}

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
"""
open('results/REPORT_FUTURES.md', 'w').write(doc); print(len(doc.splitlines()), 'lines')
