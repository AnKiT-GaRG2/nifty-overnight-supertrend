# Nifty 50 overnight Supertrend: backtests and a real-futures check

Research code for a Nifty 50 index-futures strategy project (Supertrend(14,3) baseline, factor filters, and an overnight variant).
Author: Ankit Garg (GitHub: AnKiT-GaRG2). Research only, not investment advice.

## Current best system (v2-FE, read this first)

Leveraged long/short Supertrend on real Nifty futures at a -17.7% drawdown cap: **45.9% CAGR with realistic costs** at scale 1.20 (38.3% / Sharpe 1.21 with floor costs, floor drawdown -18.6%; the scale was raised from 1.142, which gave 43.8% / 36.7%, by owner decision on 2026-11-05: leverage only, Sharpe unchanged), full period 2017-04 to 2026-10. This is v2-FEG: the earlier v2-FE (41.2% realistic / 34.4% floor) plus a long boost of 1.25x when the previous day's opening gap was in its top 20% of the prior year (adopted by the owner on 2026-11-05 after it passed the declared FACT3 rules; see the caveats in `results/rm/V2FE_SPEC.md`: the gain is concentrated in 2020, 2022-23 is slightly worse and nearby cut-offs are not a plateau, so treat it as a weak, possibly regime-specific add-on). The 2024-26 test window gave about 22% at floor costs (25% realistic) at scale 1.20, unchanged by the boost, which is the more likely live level. Details in "Roadmap implementation and later rounds" below and `results/rm/V2FE_SPEC.md`. The spot-index table that follows is the early overnight study and does not survive real futures prices.

## Early spot-index results (read the caveat first)

Strategy: buy Nifty at 15:15 when Supertrend(14,3) on 15-min bars is green and India VIX did not jump more than 8% the previous day; sell at the next 09:15 open. Costs 0.025%/side, 0.05% roll, carry 4.7% p.a. as in the brief.

| Period | Overnight Supertrend + VIX filter (CAGR / MaxDD / Sharpe) | Plain Supertrend(14,3) |
|---|---|---|
| 2017-21 | 23.4% / -3.7% / 3.21 | 21.9% / -14.3% / 1.54 |
| 2022-23 | 15.3% / -3.1% / 2.48 | 12.0% / -8.3% / 1.18 |
| 2024-26 | 11.8% / -5.8% / 1.79 | 9.3% / -7.3% / 0.92 |
| Full 2017-26 | 18.2% / -5.8% / 2.65 | 15.9% / -14.3% / 1.30 |

**Caveat: these numbers are on the spot index and do not survive real futures prices.** The spot file's 09:15 "open" is about 10bp above where futures first trade, and the overnight edge comes almost entirely from that gap. Replayed on real NSE Nifty futures (daily bhavcopy, 2,367 days), the same nights return 2.2% CAGR / -10.1% MaxDD / 0.40 Sharpe on price alone (8.5% with 6% interest on idle capital). Mean overnight return per held night: about 21bp on spot, 6.9bp on futures. Unconditionally: spot night +11.3bp / day -6.8bp; futures night +1.9bp / day +0.6bp. The brief's "+4.7% carry for longs" also has the wrong sign for real futures (they trade at a premium, so longs pay it).

Other findings:
- Searching about 800 factor gates (long and short) with six techniques (greedy, beam, pairs/triples, stability-screened, factor-score voting, random) looked great in-sample (25-33% CAGR) but did not generalise in walk-forward (2021-26 OOS 10.8-16.1% vs 14.8% for the baseline, with worse drawdown).
- A gap-reversal day sleeve and factor-timed shorts had no edge after costs.
- Repo-data-only version (price-derived ATR-jump filter instead of VIX): 15.7% / -5.1% / 2.58 over 2017-26; 7.9% / -5.1% / 1.45 over 2024-26.

## Layout
- `scripts/btlib.py` data loading (1-min -> 15-min), Supertrend, ADX/RSI, reference backtest engine
- `scripts/fast.py` fast vectorised engine (day/night legs, same accounting as btlib)
- `scripts/gates.py`, `scripts/factors.py` factor gates and the factor monitor (no lookahead)
- `scripts/finalbest.py` the overnight Supertrend + VIX filter strategy, with sensitivity and stress tests
- `scripts/pxfinal.py` repo-data-only (price-derived) version
- `scripts/psearch.py`, `scripts/techniques.py` the search techniques with walk-forward scoring
- `scripts/analyze_fut.py`, `fut_diag.py`, `fut_daily.py`, `dl_fut.py` the real NSE futures test
- `scripts/monitor.py` live factor panel
- `scripts/dl_*.py` data downloaders; `results/` saved outputs and `STRATEGY_REPORT.md`

## Run
Run everything from the repo root. Data is not committed (third-party, large); download it first:
```
pip install -r requirements.txt
python3 scripts/dl_intraday.py          # 1-min Nifty spot: github.com/technovusin/nifty50-historical-data
python3 scripts/dl.py data              # daily Yahoo series (VIX, USDINR, S&P, Brent, ...)
python3 scripts/dl2.py data             # more Yahoo series
mkdir -p data/x && python3 scripts/dl3.py data/x
python3 scripts/dl_flows.py             # FII/DII monthly flows, Nifty P/E
python3 scripts/explore0.py             # builds the 15-min cache (data/bars15.pkl), prints the baseline
python3 scripts/finalbest.py            # the strategy
python3 scripts/dl_fut.py               # real NSE futures bhavcopy (~1-2 GB of downloads, keeps only Nifty rows)
python3 scripts/analyze_fut.py          # real-futures replay
```
Set `NIFTY_DATA_DIR` to use a different data folder.

## Method rules
Signal on bar close, fill at the next bar open; costs 0.025% per side plus 0.05% per roll; train 2017-21, validate 2022-23, test 2024-Oct 2026; every searched strategy is scored by yearly walk-forward.

## Data sources
1-min Nifty spot (technovusin/nifty50-historical-data), Yahoo Finance daily series, NSE F&O bhavcopy (nsearchives.nseindia.com), HARI-KIRAN-REDDY/FIIDIIData, MrChartist/fii-dii-data. Respect each source's terms; none of it is redistributed here.

## Rebuild on real futures (rf_*.py)
After the real-futures replay showed the overnight edge was a spot-open artifact, the search was redone with P&L taken from actual NSE Nifty futures prices (daily open/close per contract, premium and open interest included). Signals are decided at 15:00 and filled at the last-30-minute VWAP; no spot-open fills.

- `scripts/rf.py` framework (real futures legs, costs, roll), `rf_check.py` sanity check, `rf_search.py` 378-variant search + yearly walk-forward, `rf_round2.py` stability, sleeves, shorts, cost stress. Output: `results/rf_round2_output.txt`.
- Best family: trend filter AND rising futures open interest, long-only (e.g. close above 50-day average and 5-day OI change > 0).
- Total-return view (futures P&L + 6% interest on capital), full period 2017-26: 9.4% CAGR / -8.2% MaxDD / Sharpe 1.38 vs buy-and-hold futures 10.6% / -38.3% / 0.71. 2024-26: 4.2% / -7.1% vs 0.4% / -18.6%. Pure futures price P&L: 3.1% / -10.9% / 0.48.
- Yearly walk-forward of the whole 378-variant selection (2021-26): 7.2% / -12.4% / Sharpe 0.96 vs buy-and-hold 8.1% / -18.6% / 0.63.
- Stable across 24 neighbouring settings (CAGR 5.9-9.8%); at 3x costs still 6.8%. Shorts reduced Sharpe. Equal-weight blend of three sleeves: 9.1% / -6.2% / 1.40.
- This is risk-managed long exposure: it cuts drawdown by about 80% for a similar return, it does not produce high CAGR. Daily data only; intraday futures data is still needed for anything faster.

## Roadmap implementation and later rounds (rm_*.py, results/rm/)
Research roadmap ("Nifty 50 Futures Strategy - Research Roadmap"): data pipeline and synthetic futures anchored to real NSE futures opens/closes (`rm_data.py`), numba engine with 1-minute stop fills and two cost models, "floor" (0.025% per side, 0.05% per roll) and "realistic" (`rm_engine.py`), signals (`rm_signals.py`), protocol-locked idea runner (`rm_ideas.py`), one-shot locked test (`rm_final.py`). Needs `numba`, `scipy`, `pandas`. The `data/` folder (NSE, Yahoo and other raw inputs) is not committed; the `dl_*.py` scripts and `results/rm/PROTOCOL_CHANGES.md` describe how each input was obtained.

- The first frozen strategy failed its locked test (NO-GO, `results/rm/FINAL_ROADMAP_REPORT.md`, `FAILURE_LOG.md`).
- Later rounds, each declared in writing before it ran (`results/rm/PROTOCOL_CHANGES.md`, 706 variants logged in `trials.json`), produced "v2-FE": a leveraged long/short Supertrend system on Nifty futures (long leg Supertrend(14,3) held overnight, short leg only below the 100-day mean, a Nasdaq/US10Y long-leg cut, and a cap of 1x on election-result and Union Budget days). Spec and risk notes: `results/rm/V2FE_SPEC.md`, `PAPER_TRADING_SPEC.md`, event dates and sources: `EVENT_LISTS.md`.
- At a -17.7% drawdown cap (owner-chosen, scale 1.163, long 2.22x / short 1.11x): full period 2017-04 to 2026-10 **41.2% CAGR with realistic costs**, 34.4% / Sharpe 1.20 with floor costs (train 40.5%, test 2024-26 20.9% at floor costs). The 2024-26 figure is the more likely live level: the train and validate windows were used for tuning and the test window has been looked at many times.
- 17 further ideas on the long side, short side, filters, sleeves and timing failed pre-declared tests; the one addition that beat a noise benchmark is the scheduled-event cap. The 2012-16 holdout has been kept sealed.
- `scripts/paper_compare.py` compares a paper-trading fill log with the model month by month.
- Not investment advice. Backtests on this data include selection effects; read the caveats in the spec files.
