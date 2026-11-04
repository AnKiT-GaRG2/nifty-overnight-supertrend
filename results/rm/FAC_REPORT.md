# FAC: catalogue factors on the two reference bases (floor costs; CAGR / MaxDD / Sharpe)

NB1 (2.0 / 1.0): train 45.5% / -19.0% / 1.28 | valid 18.0% / -21.2% / 0.62 | test(desc.) 21.3% / -16.0% / 0.77 | full 32.0% / -21.2% / 1.02
NB2 (1.5 / 0.75): train 35.4% / -14.3% / 1.28 | valid 15.4% / -14.9% / 0.62 | test(desc.) 17.8% / -12.1% / 0.77 | full 25.7% / -14.9% / 1.02

## MC1  (cell: train CAGR/DD/Sharpe for NB1 | NB2; uplift vs base in Sharpe)
   1: 39.4% / -12.8% / 1.38 (+0.10) | 30.8% / -9.6% / 1.38 (+0.10)
   2: 45.6% / -14.3% / 1.53 (+0.25) | 35.2% / -10.8% / 1.53 (+0.25)
   3: 47.8% / -15.0% / 1.55 (+0.27) | 36.8% / -11.2% / 1.55 (+0.27)
   -> PASS train, chosen 2

## MC2  (cell: train CAGR/DD/Sharpe for NB1 | NB2; uplift vs base in Sharpe)
   10: 39.3% / -20.0% / 1.16 (-0.12) | 31.0% / -15.0% / 1.16 (-0.12)
   15: 42.2% / -19.0% / 1.22 (-0.06) | 33.1% / -14.3% / 1.22 (-0.06)
   20: 42.7% / -19.0% / 1.22 (-0.06) | 33.4% / -14.3% / 1.22 (-0.06)
   -> fail train (needs +0.05 Sharpe, no worse DD on both bases, >=70% neighbours lift)

## MC3  (cell: train CAGR/DD/Sharpe for NB1 | NB2; uplift vs base in Sharpe)
   10: 46.1% / -16.6% / 1.35 (+0.07) | 35.8% / -12.6% / 1.35 (+0.07)
   15: 47.8% / -18.1% / 1.38 (+0.10) | 37.0% / -13.6% / 1.38 (+0.10)
   20: 47.0% / -19.0% / 1.35 (+0.07) | 36.4% / -14.3% / 1.35 (+0.07)
   25: 44.4% / -19.0% / 1.27 (-0.01) | 34.7% / -14.3% / 1.27 (-0.01)
   -> PASS train, chosen 15

## DXY  (cell: train CAGR/DD/Sharpe for NB1 | NB2; uplift vs base in Sharpe)
   1: 38.5% / -16.3% / 1.20 (-0.08) | 30.3% / -12.1% / 1.20 (-0.08)
   1.5: 42.5% / -16.3% / 1.29 (+0.01) | 33.2% / -12.1% / 1.29 (+0.01)
   2: 42.2% / -18.1% / 1.27 (-0.01) | 33.0% / -13.6% / 1.27 (-0.01)
   -> fail train (needs +0.05 Sharpe, no worse DD on both bases, >=70% neighbours lift)

## S1  (cell: train CAGR/DD/Sharpe for NB1 | NB2; uplift vs base in Sharpe)
   10: 37.0% / -16.7% / 1.37 (+0.09) | 29.0% / -12.6% / 1.37 (+0.09)
   20: 36.4% / -14.4% / 1.37 (+0.09) | 28.6% / -10.8% / 1.37 (+0.09)
   40: 35.4% / -12.7% / 1.37 (+0.09) | 27.9% / -9.5% / 1.37 (+0.09)
   -> PASS train, chosen 20

## O3  (cell: train CAGR/DD/Sharpe for NB1 | NB2; uplift vs base in Sharpe)
   10: 43.9% / -16.6% / 1.30 (+0.02) | 34.2% / -12.6% / 1.30 (+0.02)
   20: 42.8% / -16.6% / 1.30 (+0.02) | 33.4% / -12.6% / 1.30 (+0.02)
   30: 40.6% / -16.6% / 1.27 (-0.01) | 31.8% / -12.6% / 1.27 (-0.01)
   -> fail train (needs +0.05 Sharpe, no worse DD on both bases, >=70% neighbours lift)

## T2L  (cell: train CAGR/DD/Sharpe for NB1 | NB2; uplift vs base in Sharpe)
   100: 39.1% / -13.2% / 1.40 (+0.13) | 30.6% / -9.9% / 1.40 (+0.13)
   150: 39.2% / -13.3% / 1.41 (+0.13) | 30.7% / -9.9% / 1.41 (+0.13)
   200: 39.6% / -13.3% / 1.41 (+0.14) | 30.9% / -9.9% / 1.41 (+0.14)
   250: 40.3% / -13.3% / 1.44 (+0.16) | 31.4% / -9.9% / 1.44 (+0.16)
   -> PASS train, chosen 200

## Pair check (different factors, chosen cells, train)
   MC1+MC3: NB1 (2.0 / 1.0): pair 1.60 vs 1.53/1.38; NB2 (1.5 / 0.75): pair 1.60 vs 1.53/1.38 -> KEEP
   MC1+S1: NB1 (2.0 / 1.0): pair 1.48 vs 1.53/1.37; NB2 (1.5 / 0.75): pair 1.48 vs 1.53/1.37 -> single only
   MC1+T2L: NB1 (2.0 / 1.0): pair 1.52 vs 1.53/1.41; NB2 (1.5 / 0.75): pair 1.52 vs 1.53/1.41 -> single only
   MC3+S1: NB1 (2.0 / 1.0): pair 1.45 vs 1.38/1.37; NB2 (1.5 / 0.75): pair 1.45 vs 1.38/1.37 -> KEEP
   MC3+T2L: NB1 (2.0 / 1.0): pair 1.49 vs 1.38/1.41; NB2 (1.5 / 0.75): pair 1.49 vs 1.38/1.41 -> KEEP
   S1+T2L: NB1 (2.0 / 1.0): pair 1.41 vs 1.37/1.41; NB2 (1.5 / 0.75): pair 1.41 vs 1.37/1.41 -> single only

## Validation look (one) for stack [('MC1', 2), ('MC3', 15)]: CAGR / MaxDD / Sharpe

| Base | Window | Reference | With factors |
|---|---|---|---|
| NB1 (2.0 / 1.0) | train | 45.5% / -19.0% / 1.28 | 47.1% / -13.7% / 1.60 |
| NB1 (2.0 / 1.0) | valid | 18.0% / -21.2% / 0.62 | 16.1% / -20.6% / 0.58 |
| NB1 (2.0 / 1.0) | test (desc.) | 21.3% / -16.0% / 0.77 | 23.8% / -14.8% / 0.91 |
| NB1 (2.0 / 1.0) | full (desc.) | 32.0% / -21.2% / 1.02 | 33.1% / -20.6% / 1.21 |
| NB2 (1.5 / 0.75) | train | 35.4% / -14.3% / 1.28 | 36.2% / -10.2% / 1.60 |
| NB2 (1.5 / 0.75) | valid | 15.4% / -14.9% / 0.62 | 13.9% / -14.6% / 0.58 |
| NB2 (1.5 / 0.75) | test (desc.) | 17.8% / -12.1% / 0.77 | 19.6% / -11.1% / 0.91 |
| NB2 (1.5 / 0.75) | full (desc.) | 25.7% / -14.9% / 1.02 | 26.3% / -14.6% / 1.21 |

Validation rule (Sharpe up AND MaxDD no worse on both bases): FAIL