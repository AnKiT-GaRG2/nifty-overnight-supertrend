# v2-FE specification and risk notes (written 2026-11-04)

## System
Nifty 50 futures only. Signals unchanged from baseline v2 (frozen, code hash in BASELINE_V2_FROZEN.md): long leg Supertrend(14,3) on 15-minute bars, held overnight; short leg when Supertrend is red and the prior daily close is below its 100-day average; long leg cut to 0.25 by each of 9 Nasdaq/US10Y cells (averaged), applied from the open. Fill at the next bar's open.
Size: scale 1.163 on v2's weights -> long 2.22x, short 1.11x of capital (chosen so the FULL-period drawdown under FLOOR costs is -17.7%, the cap the user approved on 2026-11-04). Per-trade loss rule (0.75%/1%) waived by the user's decision in favour of the drawdown cap plus the event rule below.

## Scheduled-event rule (E2)
On each listed event day, hold at most 1.0x notional from the PREVIOUS close through the close of the event day (reduce at the previous close, restore at the event-day close; both trades pay the normal costs). The rule never adds exposure.
Date list used in the backtest (fixed before the run, 2026-11-04):
- General-election results: 2014-05-16, 2019-05-23, 2024-06-04.
- Union Budget presentations: 2012-03-16, 2013-02-28, 2014-07-10, 2015-02-28, 2016-02-29, 2017-02-01, 2018-02-01, 2019-02-01, 2019-07-05, 2020-02-01, 2021-02-01, 2022-02-01, 2023-02-01, 2024-02-01, 2024-07-23, 2025-02-01, 2026-02-01.
- If a listed date is not a normal session (special weekend session or holiday), the cap applies to that special session if the exchange holds one, otherwise to the next trading day.
How future dates get added: (1) Budget: when the Finance Ministry announces the presentation date (normally in January), add it the same day; (2) general-election result day: add when the Election Commission announces the counting date (next due 2029); (3) interim/second budgets in election years count as Budget days; (4) each addition is appended to this file with its announcement date BEFORE the day, never after. State elections and RBI policy days are not in the rule (no reliable date list; RBI days can be a separately pre-declared, counted trial).
Expectation: plan on 31.2% to 34.4% full-period CAGR at floor costs, not 34.4%. About 6.9 of the 11.4 points of capital the cap saved came from the single day 2024-06-04; only three election days exist in the sample. Holdout 2012-16: the cap helped on 5 of 6 events.

## Risk notes (accepted knowingly)
- Gap tail is unhedged. The mandate excludes options and stops do not work across gaps. A 10% overnight gap against the position would cost about 22% of capital at 2.22x long; a 2.0x overnight cap would only turn that into about -20% for -1.1 pts of CAGR, which was judged poor value (STRESS round). The only real protection is the chosen size.
- Kill rule: stop trading if the drawdown from the equity peak passes -18% to -20% (not the -15% of the review, which this sizing would hit in normal running).
- Worst backtest day with the event cap: -7.8% of capital; without it -11.9% (scale 1.10). Longest time below a prior equity peak: 141 trading days at scale 1.22.
- Costs: headline is FLOOR costs (mandate). The realistic model (41.2% full period) holds only if actual contract notes confirm those costs; collecting a month of real contract notes and fill prices is the quickest way to settle it (user task).
- Interest: the 6% is assumed on the full capital including margin (pledged collateral); if only 75% earns it, CAGR is about 2 pts lower.
- Historical data caveats: synthetic intraday path with real session opens/closes; the 2012-16 holdout is timing-sensitive (one extra bar of delay: Sharpe 1.69 -> 1.13).

## v2-FEG addendum (adopted by the owner 2026-11-05)
Rule added to v2-FE: on a day when |open of the previous session / close of the session before - 1| is above the 80th percentile of its own previous 365 sessions (strictly earlier values), the LONG leg is multiplied by 1.25 from that day's open (existing mechanics: the overnight gap uses the previous day's multiplier). Short leg, US cut and event cap unchanged. Because the boost adds drawdown, the scale was re-solved to keep the owner's -17.7% floor-cost cap: scale 1.142 -> long 2.18x (2.73x on boosted days, about 20% of days) / short 1.09x.
Backtest (scripts/rm_v2feg.py), CAGR / MaxDD / Sharpe. Floor costs: train 2017-04..2021 50.2% / -17.7% / 1.44; valid 2022-23 30.1% / -10.5% / 1.20; TEST 2024-26 20.9% / -13.8% / 0.75; FULL 36.7% / -17.7% / 1.21; worst day -8.3%. Realistic costs: FULL 43.8% / -15.8% / 1.43 (train 59.5%, valid 38.1%, TEST 24.4%). v2-FE for comparison: FULL floor 34.4%, realistic 41.2%.
Honest caveats: it passed the declared FACT3 rules (TRAIN +3.5 pts vs random-timing p95 +3.0, TEST +0.7) but one of 102 cells passed and about 747 variants have been tried; the gain is concentrated in 2020 (170% -> 214%), 2022-23 is -1.2 pts (floor), cut-offs 70/75/85% give only +0.1..+1.3 pts, and the 2024-26 return is unchanged (20.9%). The boosted-day long exposure of 2.73x raises the single-day tail (worst day -8.3% vs -7.8% for v2-FE). Plan on the 2024-26 level (about 21-24%) rather than 43.8%. Kill rule unchanged (-18% to -20% from the equity peak).

## Scale change to 1.20 (owner decision 2026-11-05)
Scale raised from 1.142 to 1.20 (long 2.29x, 2.87x on boosted days / short 1.15x); signals unchanged. FULL 2017-04..2026-10: realistic 45.9% CAGR / -16.6% / 1.44; floor 38.3% / -18.6% / 1.21; TEST 2024-26 realistic 25.4%, floor 21.7%; worst day -8.6% (floor -8.8%). The floor drawdown now exceeds the earlier -17.7% cap by 0.9 pt; the kill rule (-18% to -20% from the equity peak) is unchanged and now sits close to the backtest drawdown. This is leverage only (Sharpe flat); plan on the 2024-26 level, not 45.9%. DATA4 round (13 option-OI, India sector and ETF features) found nothing to add; see PROTOCOL_CHANGES.md.
