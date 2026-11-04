# Research protocol (Phase 2) — written 2026-11-03, before any idea was run

Fixes how ideas are judged so the test result cannot be talked into a pass. Its sha256 is stored in `protocol.lock`
and checked by every research script; a change needs a logged reason in `PROTOCOL_CHANGES.md`.

## Yardstick (settled in week 1 — the three open questions)
- **Baseline**: Supertrend(14,3), Wilder ATR, 15-min *spot* signal, long-only, flat when red, fills at next bar open, synthetic futures P&L.
- **Reproduction**: the engine reproduces the paper numbers (17.1% / -12.8% / 0.94, recent Sharpe 0.56) only with: mandate-floor costs
  (0.025%/side, 0.05%/roll) + 6% p.a. interest on idle collateral in CAGR/DD + Sharpe taken on the excess return (futures P&L after costs).
  So: **official yardstick = floor cost model**; CAGR / MaxDD / Calmar on total return (interest included); Sharpe/Sortino on excess return.
  The realistic model (dated STT, brokerage, exchange, SEBI, stamp, GST, 1 tick; roll = two legs + 0.5pt spread) is reported alongside
  and must also be beaten in the final pass criteria. Carry convention: long loses basis, short earns it, interest reported with and without.
- Capital Rs 2 crore fixed; position = lots of 65 with full size = floor(capital / (price*65)) (1x notional, ~12-13 lots today), 0 to full.

## Splits
Train 2017-04..2021-12 (build/tune, unlimited). Validate 2022-01..2023-12 (pass/fail only; **at most 2 looks per idea**, each logged
in `validation_looks.json`; never used to re-tune). Test 2024-01..2026-10 (locked: opened once, after the spec is frozen, via `rm_final.py`).
Walk-forward: 3y train, 6m OOS, 6m step, OOS stitched; development folds only inside 2017-04..2023-12 (OOS from 2020-04);
the full walk-forward to Oct 2026 runs once at the final test, for strategy and baseline. Inside each fold parameters are re-picked
by the plateau rule, never by the single best cell.

## Parameter budget & grids
<=3 tunable parameters per signal, <=6 for the final combined system; everything else fixed convention (session times, roll 2 trading
days before expiry, Wilder ATR). Round-value grids only (grids listed in `rm_ideas.py`). **Every configuration run is counted** in `trials.json`;
the count feeds the Deflated Sharpe Ratio.

## Sensitivity / plateau rule
For each idea, report train Sharpe and max drawdown for the full grid. Neighbours = cells differing by one grid step in any parameter
(including diagonals). Chosen cell = the cell with the highest mean train Sharpe over itself + neighbours, among cells whose own
Sharpe beats the baseline's train Sharpe. An idea **passes train** only if: (a) >=70% of the chosen cell's neighbours beat the baseline's
train Sharpe (zero-parameter ideas: the single cell must beat it); (b) chosen train Sharpe > baseline train Sharpe; (c) train MaxDD not worse
than the baseline's by more than 2 points; (d) turnover not above 2x the baseline's trades/yr. A lone peak is logged as a failure.
Compared on train: Sharpe, MaxDD, trades/yr, cost drag, 2018 and 2020 sub-periods (reported, not gating).

## Validation pass (one look = one pass/fail)
Validation Sharpe > baseline's validation Sharpe AND validation MaxDD no worse than the baseline's by more than 2 points AND
positive total return in the validation window. Not used to re-tune.

## Gate G3
2-3 ideas pass validation from >=2 families: trend refinement (A/B/C), mean reversion (F), time-of-day (D), gap (E), flow/positioning (H/G).

## Combination (Phase 4)
Combine only signals whose train daily-return correlation < 0.5; weights = inverse train volatility, rounded, fixed; net into one position
before trading; round to whole lots; ignore changes < 2 lots. Risk: initial stop k*ATR(15-min), k in {2,2.5,3}, lots = min(full, floor(0.0075*capital/(k*ATR*65))).
Vol targeting 12/15/18% (scale = min(1, target/20d realised vol)) kept only if it improves train Sharpe AND drawdown. Drawdown brake (halve at -10%)
and daily loss limit (1.5%) each must earn a place on train.

## Statistics reported
20-day block bootstrap CI on the Sharpe difference vs baseline; PBO (CSCV) on the final candidate set; Deflated Sharpe with the trial count;
per-calendar-year table. Lookahead tests (truncation, extra delay, shuffled future) on every strategy.

## Final pass criteria (all must hold; test window, floor AND realistic costs)
Sharpe > baseline on test and on 2022-01..2026-10; MaxDD better than -15% on every window and better than the baseline's; walk-forward Sharpe > baseline's
and drawdown better than -15%; no calendar year worse than -10%; still beats the baseline with doubled costs; no trade loses >1% of capital at its stop
(gaps reported separately). Targets table of the roadmap (Sharpe >= 1.0, recent >= 0.8, MaxDD better than -12%, WF CAGR >= 15%) is reported against too.

## Known limits (stated up front)
Earlier exploratory work in this repo already looked at 2024-26 data for other strategies, so the test window is not perfectly virgin for *the researcher*;
no idea in this roadmap was tuned on it. Intraday futures bars do not exist in the data: futures = synthetic series from spot (tracking error in G0 report).
