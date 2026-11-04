# Failure log (every idea gets a row the day it is tested; train = 2017-04..2021-12, baseline train Sharpe 1.15 / MaxDD -13.4%, validation baseline 0.73 / -7.7%)

| ID | Date | Idea | Hypothesis (expected sign written before running) | Params tried | Train Sharpe / DD (chosen cell) | Validation Sharpe / DD | Verdict | Why it failed or passed |
|---|---|---|---|---|---|---|---|---|
| F-001 | 2026-11-03 | A1 (trend) | Shorts pay in 2022 and 2024-25 sell-offs; short futures also earn the basis (expected +) | 1 cell(s): {} | 1.20 / -10.8% at {} | look 1: 0.44 / -16.2% | fail validation | Symmetric shorts doubled turnover (174 trades/yr) and lost in the 2022-23 chop; validation drawdown -16%. |
| F-002 | 2026-11-03 | A2 (trend) | Index drift makes shorts lose in bull phases; allow them only below the daily average (expected +) | 5 cell(s): {"L": [50, 100, 150, 200, 250]} | 1.28 / -10.8% at {"L": 100} | look 1: 0.57 / -7.2%; look 2 ({'L': 100}): 0.47 / -11.7% | fail validation | Shorting below the 200-DMA-style filter did not pay in 2022-23; Sharpe below baseline at both L=50 and L=100. |
| F-003 | 2026-11-03 | A3 (trend) | Higher-timeframe agreement cuts counter-trend whipsaws (expected +) | 16 cell(s): {"n": [7, 10, 14, 20], "m": [2.0, 2.5, 3.0, 3.5]} | 1.25 / -8.9% at {"n": 14, "m": 3.0} | look 1: 0.63 / -7.7% | fail validation | Daily Supertrend agreement: after the plateau-rule correction only 38% of neighbours beat baseline on train, so the idea fails train (a lone peak). |
| F-004 | 2026-11-03 | B1e (trend) | Standing aside when daily efficiency ratio is low removes 2022-23 whipsaw (expected +) | 15 cell(s): {"n": [10, 20, 30], "thr": [0.15, 0.2, 0.25, 0.3, 0.35]} | 0.42 / -13.2% at {"n": 20, "thr": 0.15} | - | fail train | Efficiency-ratio chop filter removed profitable trend days; train Sharpe far below baseline for every cell. |
| F-005 | 2026-11-03 | B1a (trend) | Standing aside when daily ADX is low removes whipsaw (expected +) | 12 cell(s): {"n": [10, 14, 20], "thr": [15, 20, 25, 30]} | 0.91 / -13.4% at {"n": 10, "thr": 15} | - | fail train | ADX chop filter: same, 0 of neighbours beat baseline. |
| F-006 | 2026-11-03 | B2h (trend) | Trend signals fail in high-vol regimes: stand aside when prior-day VIX percentile is high (expected +) | 4 cell(s): {"p": [60, 70, 80, 90]} | 1.58 / -5.6% at {"p": 80} | look 1: 0.24 / -8.9%; look 2 ({'p': 80}): 0.78 / -6.8% | PASS validation (then FAILED the locked test) | PASSED: standing aside when prior-day VIX percentile > 80 cut train drawdown from -13.4% to -5.6% and validated (second look). Failed the final test: Sharpe -0.09 vs 0.46. |
| F-007 | 2026-11-03 | B2l (trend) | Trend signals fail in low-vol regimes: stand aside when prior-day VIX percentile is low (expected +) | 4 cell(s): {"p": [10, 20, 30, 40]} | 1.07 / -13.2% at {"p": 10} | - | fail train | Standing aside in low-vol regimes did not help. |
| F-008 | 2026-11-03 | C1 (trend) | Confirmation bars on flips cut turnover; each skipped round trip saves >=0.05% (expected +) | 5 cell(s): {"n": [1, 2, 3, 4, 6]} | 1.15 / -13.4% at {"n": 1} | - | fail train | Confirmation bars only delayed entries; best cell is n=1 = the baseline itself. |
| F-009 | 2026-11-03 | D1 (time) | Intraday-only removes gap risk but may lose the overnight drift (expected -) | 1 cell(s): {} | -0.71 / -15.4% at {} | - | fail train | Intraday-only lost the overnight return (night leg Sharpe ~2 vs day leg ~-1.4 on the synthetic series). |
| F-010 | 2026-11-03 | D2 (time) | Early range sets the day direction on trend days (expected +) | 16 cell(s): {"orm": [15, 30, 45, 60], "L": [20, 50, 100, 200]} | 0.52 / -5.1% at {"orm": 60, "L": 100} | - | fail train | Opening-range breakout: train Sharpe 0.52 at best, no plateau. |
| F-011 | 2026-11-03 | D3 (time) | Opening and closing bars are noisy and gap-driven; skip new entries there (expected +) | 9 cell(s): {"first": [0, 1, 2], "last": [0, 2, 4]} | 1.15 / -13.4% at {"first": 0, "last": 0} | - | fail train | Skipping entries in the first/last bars changed almost nothing; best cell is no skipping. |
| F-012 | 2026-11-03 | E1 (gap) | Small gaps fill (fade), large gaps continue (follow) (expected +) | 8 cell(s): {"small": [0.2, 0.4], "large": [0.6, 0.8, 1.0, 1.2]} | -0.47 / -26.7% at {"small": 0.2, "large": 1.2} | - | fail train | Gap fade/follow lost money (train Sharpe -0.47, drawdown -27%). |
| F-013 | 2026-11-03 | F1 (meanrev) | Short-term mean reversion pays in range regimes when trend signals lose (expected +) | 12 cell(s): {"lo": [5, 10, 15, 20], "ert": [0.2, 0.3, 0.4]} | 0.08 / -17.8% at {"lo": 20, "ert": 0.2} | - | fail train | Daily RSI(2) mean reversion in range regimes: only ~26 trades/yr, train Sharpe 0.08. |
| F-014 | 2026-11-03 | G1 (diag) | Diagnostic: long exposure held only overnight (night leg) (expected ?) | 1 cell(s): {} | 1.98 / -26.4% at {} | - | diagnostic | Diagnostic only. Overnight-only has Sharpe 1.98 on the synthetic series but 252 trades/yr and -26% drawdown; real futures nights earn far less (report section 8). |
| F-015 | 2026-11-03 | G1b (diag) | Diagnostic: long exposure held only intraday (day leg) (expected ?) | 1 cell(s): {} | -1.41 / -53.6% at {} | - | diagnostic | Diagnostic only. Day-leg-only loses money on the synthetic series. |
| F-016 | 2026-11-03 | H1 (flow) | Futures OI x price change quadrants add information (expected +) | 4 cell(s): {"n": [1, 2, 3, 5]} | 0.19 / -22.9% at {"n": 1} | - | fail train | OI x price quadrants (prior-day data): train Sharpe 0.19. |
| F-017 | 2026-11-03 | H2 (flow) | US overnight return predicts the gap but is priced into the open (expected to fail) (expected -) | 4 cell(s): {"thr": [0.0, 0.0025, 0.005, 0.01]} | -0.54 / -19.6% at {"thr": 0.01} | - | fail train | US overnight return as gap predictor: priced into the open, as expected (train Sharpe negative). |

## Risk-layer components (Phase 4, on the surviving signal B2h; each must raise train Sharpe by >= 0.02 AND improve MaxDD by >= 0.25 pt)

| Component | Result on train | Kept? |
|---|---|---|
| stop + risk sizing k in {2,2.5,3} | k=2.0: Sharpe 1.53; k=2.5: 1.68; k=3.0: 1.55 (centre k=2.5 chosen) | mandatory |
| vol targeting 12/15/18% | best 15%: Sharpe 1.60 vs 1.68 without | no |
| overnight cap 8 lots | Sharpe collapsed to ~0.1 (the overnight leg carries the return) | no |
| drawdown brake (halve at -10%) | never triggered, no change | no |
| daily loss limit 1.5% | never triggered, no change | no |

## Final frozen strategy (B2h p=80 + k=2.5 stop sizing)

Train Sharpe 1.68 / -6.2%; validation 0.60 / -5.5% (baseline 0.73 / -7.7%); **locked test -0.09 / -8.7% vs baseline 0.46 / -6.6%: NO-GO.**