> **Important correction (added after the real-futures test).** The results in sections 1-7 below use the *spot index* 1-minute file, whose 09:15 "open" is about 10bp above where Nifty futures first trade. On real NSE futures prices the overnight edge largely disappears (full-period CAGR 2.2% price-only, 8.5% with 6% interest on idle capital). Treat the headline numbers below as spot-index results, not tradable futures returns. See the README.

# Nifty 50 futures: Overnight Trend (OT) strategy

Data: technovusin/nifty50-historical-data 1-min spot bars (Apr 2017 - Oct 2026) resampled to 15-min; India VIX and daily features from Yahoo Finance (^INDIAVIX).
Engine: signal on bar close, fill at next bar open. Costs 0.025%/side, 0.05% per roll (month-end), carry 4.7% p.a. (long earns, short pays) by calendar time held.
Split: train 2017-21, validate 2022-23, test 2024 - Oct 2026 (run once, after the spec was frozen). Code: scripts/btlib.py, strat.py, final.py.

## 1. Strategy (frozen spec)
1. Compute Supertrend(14, 3) on 15-min Nifty (same indicator as the baseline).
2. At the close of the 15:00 bar (15:15 IST), if Supertrend is green: BUY Nifty futures at the 15:15 bar open.
3. Size = min(1.0, 1.0% / (2 x ATR14_daily%)), ATR taken at the previous close. A 2-ATR adverse overnight gap then costs about 1% of capital.
4. EXIT at the next session's 09:15 open. No intraday exposure, no shorts.
Free parameters: 1 (stress multiplier k=2). Supertrend (14,3) and ATR14 are inherited/standard; r=1% is the mandate limit.

Why: in train data the baseline earned +115% (summed bar returns) from the 15:15->09:15 overnight bar and -8% from all intraday bars. Unconditional Nifty: +191% overnight, -120% intraday. The trend filter picks which nights to hold.

## 2. Results (same engine for both)
| Period | Strategy | CAGR% | MaxDD% | Sharpe | Baseline CAGR / DD / Sharpe |
|---|---|---|---|---|---|
| Train 2017-21 | OT | 8.65 | -3.06 | 3.59 | 21.86 / -14.33 / 1.54 |
| Valid 2022-23 | OT | 6.49 | -2.02 | 2.38 | 11.99 / -8.32 / 1.18 |
| **Test 2024-26** | OT | 5.81 | -1.69 | 2.01 | 9.35 / -7.30 / 0.92 |
| Post-2022 | OT | 6.08 | -2.02 | 2.16 | 10.41 / -8.32 / 1.03 |
| Full | OT | 7.34 | -3.06 | 2.79 | 15.93 / -14.33 / 1.30 |
Walk-forward 2020-26 (yearly re-pick of ST period/mult from a 9-cell grid, trailing 3y Sharpe): OT 6.6% / -3.9% / Sharpe 2.37 vs baseline 16.2% / -14.5% / 1.22. WF 2024-26: OT Sharpe 1.86 vs 0.62.
Trade stats (full): 1,276 trades (~133/yr), win rate 66%, avg +0.053%/trade, worst -0.94%, 0 trades lose >1%. Test: worst -0.92% (2 Mar 2026).
Correlation of daily returns OT vs baseline: 0.60.

Risk dial (k): k=3 CAGR 5.7/4.3/3.8 (train/valid/test), worst -0.63%; k=2 (chosen) 8.6/6.5/5.8, worst -0.94%; k=1.5 11.7/8.7/7.8, worst -1.25% (8 trades >1%); k=1 16.8/11.4/11.3, worst -1.88% (12 trades >1%). Sharpe is unchanged by k.

## 3. Sensitivity (Supertrend period x multiplier, OT sizing k=2), Sharpe train / valid / test
All 9 cells in n{10,14,20} x m{2.5,3,3.5}: train 3.21-3.59, valid 1.78-2.38, test 1.62-2.01. Drawdown test -1.5% to -2.7%. No single-cell peak.

## 4. Weaknesses (read before trusting it)
- **Open-print dependence.** The first 15-min bar averages -6.6bp (train) while the overnight bar averages +16bp. If the exit is one bar later (09:30 open), OT Sharpe falls to 1.50 full / 0.55 test (baseline 1.30 / 0.92) and the 2024-26 walk-forward Sharpe is 0.25. The edge only holds if you can really fill near the 09:15 open print. Spot-index "open" is not a tradable price; verify with futures tick/1-min data.
- **Cost sensitivity.** 133 round trips a year. At 2x costs OT Sharpe 1.58 (baseline 0.93); at 3x costs 0.36 (baseline 0.56).
- **Low return at the mandate's risk cap.** CAGR is about half the baseline. Capital is idle ~96% of the time. If Sharpe is measured over a 6% risk-free rate, OT does not beat the baseline (test 0.44-vs-0.35 only at k=1.5; ~0 at k=2). I used zero risk-free because the brief's convention already adds carry to futures P&L.
- **Gap risk.** A sizing rule cannot stop a halt/limit move. Worst planned-vs-actual loss in the data: -0.94% (k=2). With a 09:30 exit, 2024-06-03 (election-result gap) lost -1.78%.
- **Baseline mismatch.** My replication of the baseline shows CAGR 15.9 / DD -14.3 / Sharpe 1.30 (full) vs the brief's 17.1 / -12.8 / 0.94; the Sharpe definition or carry handling probably differs. Comparisons here are like-for-like in my engine only.
- My earlier global-factor study (S&P, VIX, crude) looked at full-period data including 2024+. The OT idea itself came from a train-only decomposition and uses none of those factors.

## 5. Failed / rejected ideas log (train Sharpe / valid Sharpe unless stated)
| Idea | Result | Verdict |
|---|---|---|
| Baseline ST(14,3) long-only, continuous | 1.54 / 1.17, DD -14.3 / -8.1 | reference |
| + risk sizing 0.75% via ST-line distance | 1.68 / 1.23, CAGR 15.8 / 10.9 | modest gain; fallback |
| + long only above 200DMA | 1.48 / 0.94 | worse; cuts winners |
| Symmetric shorts (no filter) | 1.10 / 0.53, valid DD -19% | fail |
| Shorts only below 200DMA | 1.14 / 0.54 | fail; shorts pay 4.7% carry |
| + ADX(14) >= 20 / >= 25 | 0.86 / 0.79 ; 0.85 / 0.70 | fail |
| + VIX > 22 halves size | 1.31 / 0.96 | no gain |
| Supertrend intraday holding | -8% summed return vs +115% overnight (train) | intraday drift is negative |
| Overnight long every night | 2.77 / 1.08, DD -27% | fails validation; needs trend filter |
| Intraday short when prior-day ST red | 0.48 / -0.38 | fail |
| Overnight long + intraday short | 1.76 / 1.04 | worse than overnight alone |
| Mean reversion RSI(2)<10 above 200DMA, overnight | 0.45 / -0.23 | fail |
| Add MR trigger to OT | 3.21 / 2.06 (vs 3.59 / 2.38) | worse |
| OT + ADX>=20 / >200DMA / VIX<25 | 2.23/2.17, 3.71/2.14, 3.59/2.32 | no gain, adds params |
| Fixed 1.0 exposure overnight | worst trade -9.08%, 25 trades >1% | breaches mandate |
| ST-line-distance sizing for OT | 3.03 / 2.24, worst -3.94%, 19 trades >1% | breaches mandate |
| Exit 1/2/4 bars later | Sharpe 2.07 / 1.83 / 1.63 (train) | confirms open-print dependence |
| Enter at 15:00 open instead of 15:15 | 3.71 / 3.23 (train / valid) | not adopted (tuned after seeing results); worth a proper test |

## 6. Next steps
1. Check fills against real Nifty futures 1-min data (open and 15:15), not spot. This decides whether the strategy is real.
2. Paper trade 2-3 months with actual 09:15 fills before sizing up.
3. Decide the risk dial (k=2 is mandate-compliant; k=1.5 is a reasonable compromise).
4. Pair OT with a second, uncorrelated sleeve to use the idle risk budget (none found so far).

---
# 7. Factor layer (from "Nifty 50 What Moves It" document): added 3 Nov 2026

**What was built.** `scripts/factors.py` (flags, no lookahead: each day uses only data dated before it) and `scripts/monitor.py` (live panel). Flags use the document's thresholds unchanged: rupee -2%/month, dollar +1.5%/month, US10Y +25bp/month, S&P -2%/month, Brent 21d avg >$100, Brent +10% in 5d above $90, FII >Rs 2 lakh cr sold in 12 months, P/E >23. Reaction = size multiplier (-25% per flag, no trade at 3+ fast flags).

**Data limits.** Daily FII flows, FII index-futures positions and market breadth have no free 10-year history; monthly FII (NSE provisional) ends Dec 2025 and P/E ends 1 Jul 2026 (carried forward after). The document's own 2026 FII/P/E figures are entered by hand in the live monitor.

**Contamination.** The document's thresholds were fitted on the full 2016-2026 sample, so no period (including 2024-26) is clean out-of-sample for these rules. Treat results as best case.

## 7.1 Do the factors predict the overnight return OT trades? (1,277 green nights)
No. Difference in mean overnight return, flag ON minus OFF (train / valid / test): rupee_month -0.12 / +0.26 / +0.34; spx_month -0.15 / +0.09 / +0.18; dollar_month -0.06 / +0.06 / -0.03; us10y_month -0.02 / -0.13 / -0.03; crude_regime n/a / +0.08 / -0.01; fii_12m_sell n/a / +0.02 / -0.02; pe_high +0.05 / -0.13 / -0.06. Signs flip across periods and almost every |t| < 2. The factors explain same-day and monthly Nifty moves, not the overnight gap.

## 7.2 Backtest with the reaction layer (Sharpe train / valid / test / full; CAGR full; MaxDD full)
| Variant | Sharpe tr/va/te/full | CAGR full | MaxDD full |
|---|---|---|---|
| OT, no factors | 3.59 / 2.38 / 2.01 / 2.79 | 7.3 | -3.1 |
| OT + 6 fast flags | 3.79 / 2.14 / 1.83 / 2.80 | 6.1 | -1.4 |
| OT + all 8 flags | 3.64 / 2.25 / 1.69 / 2.65 | 4.5 | -1.3 |
| OT + crude only (half size) | 3.59 / 2.24 / 2.01 / 2.79 | 7.1 | -3.1 |
| OT + US10Y only (picked on train/valid) | 3.66 / 2.80 / 1.93 / 2.88 | 7.1 | -3.1 |
| OT + rupee/dollar/S&P/US10Y, veto at 2 | 3.59 / 2.49 / 1.90 / 2.75 | 6.5 | -1.8 |
| Baseline, no factors | 1.54 / 1.18 / 0.92 / 1.30 | 15.9 | -14.3 |
| Baseline + 6 fast flags | 1.55 / 1.03 / 0.83 / 1.26 | 11.7 | -10.5 |
| Baseline + all 8 flags | 1.51 / 1.35 / 0.67 / 1.23 | 9.1 | -6.4 |
2026 (war year) net: OT 4.2%, OT + fast flags 2.0%, baseline 5.8%, baseline + fast flags 0.5%.
Verdict: the layer cuts drawdown mostly by cutting exposure; it does not raise Sharpe on the test period and it costs return. Not adopted for OT. For the baseline it trades most of the return for lower drawdown.

## 7.3 Intraday test (could the factors time an intraday short?)
Flagged days have mean intraday return (09:15 -> 15:15 open) of about -0.05% to -0.15%, vs unconditional -0.10 / -0.03 / -0.04 (train / valid / test). Round-trip cost is 0.05%. No tradable edge. us10y_month is the only consistently negative flag (-0.26 / -0.07 / -0.11) but the gain over baseline drift is under cost.

## 7.4 Failed-idea log additions
| Idea | Result |
|---|---|
| Rupee, dollar, S&P, US10Y, crude, FII, P/E flags as overnight vetoes | no consistent effect on overnight returns |
| Equal-weight "score" of all 8 flags | Sharpe 1.69 on test (vs 2.01), CAGR 3.3% |
| Crude regime half-size | no change in Sharpe; only touches 8.5% of nights |
| Factor-flagged intraday short | edge below cost |
| Korean won / Taiwan dollar / yen / VIX jump flags | too rare or inconsistent (yen and VIX jump fire on ~1-2% of nights) |
| Seasonality (Jan/Feb weak, Apr/Jul strong) | +0.01 / -0.08 / +0.09 diff on Jan-Feb; no effect |

## 7.5 Live reading (data through 2 Nov 2026)
Caution: S&P 500 -2.35% over 21 days; Brent 21d average $108.7; FII 12-month selling (per document). OK: rupee (-1.4% over 21d), dollar, US10Y (-0.38pt), VIX 15.3, won/Taiwan dollar, P/E ~19. Two of six fast flags on, so the layer would run at 0.50x. OT signal: Supertrend GREEN at the 2 Nov close (23,440.8; line 23,250.6).
