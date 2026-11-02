# Nifty 50 overnight Supertrend: backtests and a real-futures check

Research code for a Nifty 50 index-futures strategy project (Supertrend(14,3) baseline, factor filters, and an overnight variant).
Author: Ankit Garg (GitHub: AnKiT-GaRG2). Research only, not investment advice.

## Headline results (read the caveat first)

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
