import json
T = json.load(open('results/report_ext_tables.json'))
doc = f"""# Nifty Futures — Extended Backtest 2013–2026: Popular Strategies, Trend(50) + Rising OI, Re-tuning and Regimes

Research only, not investment advice. Prepared 2026-11-03. **All results are on real NSE Nifty index futures** (daily bhavcopy). Spot is not used. This report extends the earlier 2018–2026 report with **1,292 additional trading days (2012-01-02 to 2017-03-31)**, so the data now covers 2012–2026 ({T['NDAYS']}).

## 1. Verdict (short)

**Hinglish mein:** 2013–2017 ka naya data aane ke baad bhi Trend(50)+rising OI strategy buy-and-hold se behtar nahi nikli. 2013–17 mein (jo data pehle kabhi nahi dekha tha) uska result -2.2% CAGR raha, jabki buy-and-hold 4.5% tha. Pichle test period mein bhi -8.5% tha. Tune karne par bhi koi trend/OI strategy test mein paisa nahi bana payi. Ek hi family jo har period mein positive rahi: IBS mean-reversion (3 se 6% CAGR, drawdown -6% se -14%, buy-and-hold ka -41%). Ye chhota edge hai, aur trials ke hisaab se statistically proven nahi hai (Deflated Sharpe 0.10).

**In English:**
- **Trend(50) + rising OI still fails.** On the never-seen 2013–17 window it returned **-2.2% CAGR / -0.15 Sharpe / -27.0% MaxDD** against buy-and-hold's **+4.5% / 0.33 / -27.4%**. Combined with the earlier test-period loss (-8.5% vs -4.8%), it has now failed on two independent windows.
- **Fine-tuning did not rescue it.** Re-tuning on the longer 2013–21 train and checking all five parameters (N=30/40/50/60/80) gives no N that beats buy-and-hold in both the 2013–17 and the 2024–26 windows.
- **No trend-following, breakout or OI strategy was profitable in all four windows** (2013–17, 2013–21 train, 2022–23, 2024–26). Trend(50)+rising OI earned money in 2020–2023 and lost in 2013 (-11.2%), 2016 (-6.6%) and 2024 (-14.5%).
- **One family stayed positive everywhere: IBS mean-reversion** (long when the close is in the bottom of the day's range). Parameters frozen from 2018–21 earn **6.0% in 2013–17, 3.6% (2013–21), 1.1% (2022–23) and 3.1% (2024–26)**, with drawdowns of -5.6% to -13.8%, against buy-and-hold's -41%. It is a small edge. It is positive in 10 of 14 years, but it does not beat buy-and-hold in strong bull years (2014, 2017, 2020, 2021, 2023).
- **A VIX filter on IBS (hold only when India VIX is at least 15) lifts it to 7.4% / 2.8% / 2.1% / 5.5% in the four windows (full 2013–26: 4.3% CAGR, Sharpe 0.65, MaxDD -12.2% vs buy-and-hold 4.6% / 0.35 / -40.7%).** I chose the filter after seeing the regime tables, so it is partly in-sample (section 10.5).
- **It is not statistically proven.** After counting about 2,700 trials, its Deflated Sharpe probability is 0.10 (0.95+ would be strong evidence), and nearby parameters (lo=0.2 and above) fail in the test period.
- **Walk-forward re-tuning every year (2015–2026) earns 0.6% CAGR** against buy-and-hold's 3.6%, so automatic yearly re-selection from this strategy menu does not work.

## 2. Data and method

| Item | Choice |
|---|---|
| New data | NSE F&O daily bhavcopy for 2012-01-02 to 2017-03-31, fetched through your own Chrome session (NSE's archive blocks scripted clients). 1,292 trading days, 3 Nifty futures contracts per day, 78 non-trading dates returned 404 (holidays). India VIX for 2012-01-02 to 2016-12-30 from NSE's historical VIX page (1,240 rows). Quality checks: no zero prices, no duplicates, largest one-day front-month move 6.0% (24 Aug 2015). |
| Instrument | Nifty index futures, front-month contract not expiring on the entry day; rolled the day it expires |
| Signal timing | Computed from data through the close of day t, including that day's price, VIX and OI. Orders fill at the **next open**; held open-to-open on the same contract. |
| Costs | Brokerage, STT (changes by date, 0.017% to 0.02%), exchange, SEBI, GST, stamp, 0.01% slippage per side, plus a roll cost. Section 6. |
| Carry / interest | Futures prices already include the premium, so longs pay it and the buy-and-hold benchmark pays it too. No interest is added. About 6.5%/yr on idle capital would be added to every series equally. |
| Warm-up | First year (2012) is indicator warm-up. Evaluation starts 2013-01-01. |
| Windows | **Pre 2013-01 to 2017-03** (new), **Train 2013-01 to 2021-12**, **Valid 2022-01 to 2023-12**, **Test 2024-01 to 2026-11**, **Full 2013-2026**. The old train (2018-04 to 2021-12) is also kept for the frozen-parameter check. |
| Two-stage protocol | **Stage 1:** parameters frozen from the earlier report (tuned on 2018–21 only) run unchanged on 2013–17, which they had never seen. **Stage 2:** re-tune on the extended train 2013–21, shortlist on train+valid, show test once. |
| Benchmark | Always-long Nifty futures with the same costs and roll rule |

## 3. Stage 1 — frozen parameters on the never-seen 2013–17 window (CAGR% / Sharpe / MaxDD%)

These parameters were chosen on 2018–21 only. 2013–17 was not touched, so this is a clean out-of-sample test.

{T['FZ']}

Reading it: the trend and OI strategies that looked best in 2018–23 mostly **did not beat buy-and-hold in 2013–17** (Trend(50)+rising OI: -2.2% vs 4.5%). The strategies that did beat it there were mean-reversion ones (IBS, Stochastic, buy-the-dip) and some trend variants that then lost in 2024–26 (EMA, Supertrend, long build-up).

## 4. Stage 2 — re-tuned on the extended train (2013–2021)

### 4.1 Textbook parameters, no fitting

{T['A']}

### 4.2 Parameters re-tuned on train 2013–21 only

{T['B']}

**Scoreboard: does the tuned strategy beat buy-and-hold on CAGR+Sharpe+MaxDD, and is its CAGR positive, in Pre/Train/Valid/Test?**

{T['SCORE']}

- **Positive in all four windows:** {T['ALLPOS']}. (Bollinger mean-reversion has 0% exposure in later periods, so it is positive only because it barely trades.)
- **Beats buy-and-hold in Pre, Valid and Test together:** {T['ALLBEAT']}.
- **Shortlist** (Sharpe above 0.5 and CAGR above 0 in train and valid, ranked by the weaker of the two): {T['SHORT']}.

### 4.3 Frozen picks (re-tuned, chosen before looking at test) and your strategy

{T['C']}

All three re-tuned picks lose money in test (-3.3% to -9.4%), as the first report's picks did.

## 5. Trend(50) + rising OI

Strategy: long when close is above its 50-day average **and** total Nifty futures OI is higher than 5 trading days ago; flat otherwise.

### 5.1 Parameter sweep (N = 30, 40, 50, 60, 80) and three OI definitions, expiry-adjusted vs naive OI

{T['SWEEP']}

- **With the 5-day OI definition and expiry-adjusted OI, no N beats buy-and-hold in 2013–17 or in 2024–26.** The only strong window is 2022–23.
- **Adding OI to a plain trend filter did not help.** Trend(50)-only earned 0.5% in 2013–17 and the OI version -2.2%.
- **The few "Y" cells are not stable.** In 2013–17 they appear only for N=30/40 (sma20 OI, and Trend-only), and none of those hold up in the test window.

### 5.2 Year by year (net of costs)

{T['YEARS']}

The OI version has a large losing streak in 2013 (-11.2%), 2016 (-6.6%) and 2024 (-14.5%), all years in which buy-and-hold was flat (0.3%, -1.6%, -0.4%).

### 5.3 Expiry effect

{T['EXP']}

{T['EXPN']}.

- Total OI drops sharply after each monthly expiry because the expiring contract leaves the file, so a naive "OI rising" test is false almost every time on those days (1% vs 65%).
- An expiry-adjusted OI series (day-to-day change over contracts present on both days) removes the artifact. It slightly overstates "rising" right after expiry because the new far contract starts near zero (92% vs 73%).
- The handling choice changes the results (full-period CAGR 1.9% adjusted vs 0.7% naive), so both are shown everywhere.

### 5.4 Look-ahead check

{T['LOOK']}

OI for day t enters the signal at the close of t and the order is placed at the open of t+1, so the after-close publication of OI is respected.

## 6. Costs

{T['COSTUNIT']}

{T['COST']}

Trend(50)+rising OI makes 212 round trips over 13.8 years and costs roughly 0.9 points of CAGR per year. Costs are not what makes it lose; the signal does.

## 7. Overfitting accounting

{T['TRIALS']}

{T['DSR']}

All of these are far below the 0.95 that would be strong evidence. The trend/OI picks also lost money in test.

## 8. Walk-forward re-tuning (2015–2026)

Each year, pick the 5 best candidates by trailing Sharpe on data **before** that year, trade them equal-weight for the year.

{T['WF']}

{T['WFSUM']}

Automatic yearly re-selection from this menu earns less than buy-and-hold and has a -29% drawdown. The picks flip between mean-reversion (2015–2020) and trend (2021–2026), which is exactly when each fails.

## 9. Regime-wise results (annualised return, Sharpe in brackets; `*` = fewer than 30 days)

{T['REG']}

What the regimes show:
- **Trend strategies gain in "up >3%" and bull regimes in some windows and lose in the next.** The sign flips between windows, so these are not stable edges.
- **The OI strategy does not protect in high-VIX or drawdown regimes** in the windows that have enough days.
- **Supertrend (7, 2.0) long-only is positive in bear-trend regimes in all three windows** (12.5%, 23.9%, 4.1%) and loses in the test-period bull regime (-15.4%). It is a description of what happened, not a tested rule.
- High-VIX days are rare in test (20 days), so single numbers there are noisy.

## 10. The one family that stayed positive: IBS mean-reversion

Rule: long when the day's close is in the bottom 10% of the day's high-low range (IBS below 0.1); exit when IBS rises above 0.8. Parameters (0.1 / 0.8) come from the earlier 2018–21 tuning and were **not** changed after seeing 2013–17 or test.

{T['IBS']}

### 10.1 Robustness to its two parameters (CAGR% in Pre / Valid / Test)

{T['IBSGRID']}

- Around lo=0.10 to 0.15 the strategy is positive in most windows. At lo=0.20 and above it fails in test, and at lo=0.05 it hardly trades. This is a modest zone of stability, not a plateau.

### 10.2 Year by year, and combined with the panic-reversal pair

{T['IBS_YEARS']}

{T['IBS_COMBO']}

- IBS is positive in 10 of 14 years; it loses in 2018, 2020 (-0.5%), 2023 and 2026 and trails buy-and-hold in strong bull years.
- A 50/50 mix with the panic-reversal pair (VIX spike or pullback in an uptrend) smooths the path: full-period 2.4% CAGR, Sharpe 0.54, MaxDD -12.1%, and positive in all five windows.

### 10.3 Costs and significance

{T['IBS_COST']}

{T['IBS_DSR']}

### 10.4 Regime-wise

{T['IBS_REG']}

- **IBS earns in stressed markets:** high VIX (27.2%, 10.9%, 12.6%), drawdown above 10% (11.9%, 9.6%, 12.1%, 6.2%) and 20-day drop below -3% (22.9%, 11.2%, 13.6%, 6.5%) are positive in every window that has enough days.
- **It loses in calm, rising markets:** low VIX below 15 is negative in all four windows (-4.7%, -0.9%, -1.9%, -3.3%), and "up >3%" is about zero or negative.

### 10.5 Regime-conditioned IBS: hold only when VIX is at least 15

The 15 boundary is the Low/Mid VIX edge I had fixed in advance. **Caveat:** I chose to test a VIX filter after looking at the regime table above, which includes valid and test windows, so this is partly in-sample. Treat it as a hypothesis; the old-train column (2018–21) is the only fully unseen check on the rule, and the sweep shows how sensitive the threshold is.

{T['IBSVIX']}

- Thresholds from 12 to 15 improve on plain IBS in every window. From 16 upward the strategy trades rarely (9% of days or less) and the test window fades, so the benefit is concentrated near 14–15.
- Exposure falls from 17% to 11% of days, with {T['IBSVIX_RT']} round trips in 13.8 years (about 9 a year).

{T['IBSVIX_YEARS']}

{T['IBSVIX_COMBO']}

{T['IBSVIX_COST']}

{T['IBSVIX_DSR']} The probability is still far below 0.95: the filtered version is not proven either.

## 11. Post-hoc panic-reversal pair (kept for completeness)

Found earlier with knowledge of 2018–2026, so **2013–17 is genuinely out-of-sample for it**: it returned 1.3% (Sharpe 0.50, MaxDD -6.5%) there, similar to its 2018–26 results.

{T['POSTHOC']}

## 12. Can this work in real life? (honest answer)

- **Trend(50) + rising OI: no.** It failed on two independent windows after costs, and fine-tuning did not fix it.
- **IBS mean-reversion (alone, filtered by VIX, or with the pair): maybe, but small.** Expect roughly 3–5% a year on notional, with a worst historical drawdown around -12% to -14%, and long stretches behind buy-and-hold in bull markets. The VIX-filtered version had 4.3% CAGR / 0.65 Sharpe / -12.2% MaxDD over 2013–26 and 3.0% / 0.71 / -11.5% when mixed 50/50 with the pair. None of this is statistically proven after the number of trials tried (Deflated Sharpe 0.10 to 0.19).
- **Gate you set** ("beat buy-and-hold after costs"): IBS beats it on drawdown and Sharpe in the full period and wins in 2013–17 and 2024–26, but earns less than buy-and-hold in 2018–23. Whether that passes depends on whether you judge by total return or by risk-adjusted return.
- **Paper trading first** is the right next step for IBS. It trades about 11 times a year, so 2–3 months gives only a handful of trades. Use it to check fills, gaps at the open and signal timing, not to judge profits.
- **Leverage is dangerous.** The strategies are mostly flat, so their return per rupee of margin looks higher, but drawdowns scale with leverage and March 2020 is in the data.

## 13. Limitations

- Daily data only; fills at the open plus 0.01% slippage per side. Real fills at volatile opens can be worse.
- One instrument. 14 years includes the 2020 crash only once and few trending bull years after 2021.
- No margin, lot-size, funding or tax modeling. Returns are on notional exposure.
- Total OI includes calendar-spread and hedging positions, so it is not a clean directional-positioning measure.
- **Test period (2024–26) is no longer completely untouched**: earlier exploratory runs looked at it. The 2013–17 window is the clean out-of-sample check for the frozen picks.
- Regime thresholds (VIX 15/22, momentum +/-3%, drawdown 10%) were fixed once and not tuned; many small regime cells are noisy.

## 14. Files

- Code: `scripts/report_futures_ext.py` (all results), `scripts/build_report_ext.py` (this document); earlier `scripts/report_futures.py`
- Data: `data/fut/nifty_fut_2012_2017.csv` (new), `data/vix_ext.csv`; raw copy `data/fut/nifty_fut_2012_2017_raw.csv`
- Results: `results/report_ext_tables.json`, `results/report_ext_res.pkl`
"""
open('results/REPORT_FUTURES_2013_2026.md', 'w').write(doc); print(len(doc.splitlines()), 'lines')
