# v2-FE paper-trading spec (written 2026-11-04)

Companion to `V2FE_SPEC.md` (system, event rule, risk notes). This file is the operating plan. Every number marked **[confirm]** is an assumption that must be checked before it is relied on. Nothing here is a promise of return.

## 1. What is traded
Nifty 50 index futures only (near-month contract). Capital in the model: Rs 2 crore. Drawdown cap chosen by the owner: **-17.7%** (floor-cost backtest max drawdown at this size, 2017-04 to 2026-10). The per-trade loss rule (0.75% / 1%) is waived in favour of the cap and the event rule.

## 2. Size
| Stage | When | Size vs full | Long leg | Short leg |
|---|---|---|---|---|
| Ramp 1 | month 1 | 0.50 | 1.11x capital | 0.56x |
| Ramp 2 | month 2 | 0.75 | 1.67x | 0.83x |
| Full | from month 3, only if section 8 checks pass | 1.00 | 2.18x (2.73x on boost days, see below) | 1.09x |

Lots = floor(weight x capital / (index level x lot size)). Lot size used by the backtest: 65 **[confirm the exchange's current Nifty lot size]**. At full size, Rs 2 crore:
| Index level | Long lots (full) | Short lots (full) | Half size (long / short) |
|---|---|---|---|
| 20,000 | 32 | 16 | 16 / 8 |
| 23,000 (last data 2026-10-30: 23,053) | 28 | 14 | 14 / 7 |
| 25,000 | 26 | 13 | 13 / 6 |
The long leg is further multiplied by the US-factor cut (section 3.3), so the lots held on a given day are often fewer. Margin: at about 12% of notional, full size needs roughly 25-30% of capital as margin **[confirm with the broker; the model assumes the rest of the capital earns 6% as pledged collateral]**.

## 3. Daily rules (what the backtest does, nothing else)
1. **Signal clock.** 15-minute bars of the index, 09:15 to 15:30. At each bar close compute Supertrend(ATR 14, Wilder, multiplier 3.0). Any order is sent at the **next bar's open** (a signal on the last bar fills at the next session's 09:15 open).
2. **Long leg.** Long while Supertrend is green; flat when red. Held overnight.
3. **US-factor cut (long leg only), applied from the open.** Before the Indian open read the previous US session: Nasdaq Composite 5-day return and US 10-year yield 5-day change. For each of 9 cells (x in {1, 2, 3}% Nasdaq fall, y in {10, 15, 20} bp yield rise) the cell multiplier is 0.25 if the 5-day Nasdaq return < -x%, times 0.25 if the 5-day yield rise > y bp, else 1. Long size = full long size x the average of the 9 cell multipliers. The overnight gap into a day is carried by the **previous** day's size; the new size starts at the open.
4. **Short leg.** Short while Supertrend is red **and** the previous completed daily close is below its 100-day simple mean; flat otherwise. Long and short never overlap.
5. **Event cap.** On each event day (list in `V2FE_SPEC.md`) hold at most 1.0x notional in total from the previous close to the close of the event day; reduce at the previous close, restore at the event-day close. Dates are added to `V2FE_SPEC.md` when announced (Union Budget in January for the February presentation; counting day for the next general election, due 2029) and **before** the day.
6. **Roll.** Roll the held position at the close of the trading day that is 2 trading days before the monthly expiry (backtest rule). Roll only a position actually held.
7. **No stops, no intraday overrides, no discretionary changes.** If something looks wrong, section 7 applies.

## 4. Pre-open checklist
- Is today an event day, or the day before one (cap the position at the previous close)?
- US data: Nasdaq 5-day return, US10Y 5-day change -> today's cut multiplier.
- Previous daily close vs 100-day mean -> is shorting allowed?
- Contract being held and days to roll.
- Broker margin used / available.

## 5. Fill log (one row per fill; file `paper_trading_log_template.csv`)
Date and time of the signal bar, signal, intended side and lots, **model price** (open of the next 15-minute bar), actual fill price and time, slippage in points and in % of price (signed so that positive = worse than model), brokerage, exchange charges, STT, stamp duty, GST, total cost in rupees and in % of notional, contract, event flag, size stage (ramp 1 / 2 / full), notes. Keep the contract note PDF for every trade day.

## 6. Monthly comparison with the backtest
Run the frozen model on the same calendar month (same signals, same size stage) and compare: (a) number of trades and entry/exit dates; (b) average slippage vs the model's next-bar open; (c) total cost % of capital vs the floor model (0.025% per side, 0.05% per roll) and vs the realistic model; (d) month P&L and drawdown vs the model. Differences larger than the pre-set tolerances (section 8) go in the review note; the model itself is not re-tuned.

## 7. Stop rules (proposed; edit before starting)
- **Review at -10% drawdown from the equity peak:** no change in size unless live fills or costs differ materially from the model (section 6).
- **Halve size at -17.7%** (the backtest's own worst case at this size) and hold a full review.
- **Stop trading at -20%** (about two points beyond the backtest worst case, since a gap beyond anything in 2017-2026 is possible) and decide whether to restart.
- **Unhedged gap tail, accepted knowingly:** a 10% overnight gap against a full-size long leg costs about 21% of capital; the mandate excludes options and stops do not work across gaps. The only protection is the size chosen.

## 8. Conditions to move from ramp to full size
All must hold after month 2 (or later): (1) broker margin confirmed for the full-size position with a buffer; (2) average slippage <= 0.03% of price per fill [pre-set; edit]; (3) total cost <= the realistic model's cost [pre-set; edit]; (4) no unexplained signal or fill differences vs the model; (5) drawdown inside the review limit. The remaining research item, **one look at the 2012-2016 holdout for the frozen final version**, is reserved for this moment and runs **only if the owner releases the holdout** (it has been set aside by instruction).

## 9. Expectations
Backtest at -17.7% cap (scale 1.163, owner-approved 2026-11-04), full period 2017-04 to 2026-10: floor costs 34.4% (train 40.5%, test 2024-26 20.9%); realistic costs 41.2%. Plan on the **test-window level, about 20%, as the more likely live figure**, with 31-33% as the upper range at floor costs. Part of the event cap's gain depends on one day (2024-06-04). 698 variants were tried; the Deflated Sharpe of the first v2 version was 0.022.

## 10. Comparison script
`scripts/paper_compare.py` (numba venv, repo root): `python scripts/paper_compare.py --log results/rm/paper_trading_log.csv --month YYYY-MM --stage 0.5 [--mark-price P] [--carry-in LOTS@PRICE] [--out report.md]`. `signal` values in the log: ENTER_LONG, EXIT_LONG, ENTER_SHORT, EXIT_SHORT (matched against the model by date and signal), ROLL, EVENT_REDUCE, EVENT_RESTORE, US_CUT_RESIZE, OTHER (reported, not matched); `side` BUY or SELL. It reports slippage (positive = worse than the model price), costs against the floor and the realistic models, model fills missing from the log and the reverse, live P&L from fills against the model's month P&L at the chosen stage. The model runs only for months inside the repo data (currently to 2026-10-30): to compare a later month, first extend the 1-minute intraday files, futures bhavcopy and Nasdaq/US10Y closes; until then the live-side statistics still run. `--demo` builds a synthetic log for 2026-09 and checks the pipeline end to end.

## 12. v2-FEG boost rule (added 2026-11-05, owner-adopted)
Each morning before the open compute g = |open of the previous session / close of the session before that - 1| and its rank among the previous 365 sessions' values (strictly earlier). If the rank is above 80% the long target is multiplied by 1.25 (about 20% of days; full-size long 2.18x -> 2.73x, ramp stages scale the same way). Log the rank and the multiplier in the fill log. Sizes in section 2 use the re-solved scale 1.142 (v2-FEG) instead of 1.163. Caveats are in `V2FE_SPEC.md` (v2-FEG addendum): treat the boost as weak evidence and compare live results with the model month by month; if the boosted days underperform the unboosted ones over the first months, drop the boost.
