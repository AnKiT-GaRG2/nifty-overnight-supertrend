# Leveraged long/short combo + factors (floor costs; each cell: CAGR / MaxDD / Sharpe)

Base combo (2x baseline long + 1x A2 short): train 45.5% / -19.0% / 1.28 | valid 18.0% / -21.2% / 0.62 | test(desc.) 21.3% / -16.0% / 0.77 | full 32.0% / -21.2% / 1.02

## Factor V (tau) - train | valid | test(desc.) | full
   tau=0.12: 28.2% / -13.4% / 1.23 | 15.4% / -19.2% / 0.59 | 16.9% / -15.3% / 0.67 | 22.1% / -19.2% / 0.93
   tau=0.15: 32.5% / -15.5% / 1.27 | 15.5% / -20.0% / 0.56 | 17.6% / -16.0% / 0.66 | 24.3% / -20.0% / 0.95
   tau=0.18: 35.1% / -17.8% / 1.28 | 16.5% / -19.9% / 0.58 | 18.8% / -16.0% / 0.69 | 26.1% / -19.9% / 0.97
   tau=0.21: 36.8% / -19.0% / 1.27 | 17.8% / -20.6% / 0.62 | 19.9% / -16.0% / 0.73 | 27.5% / -20.6% / 0.99
   -> no interior cell keeps train and valid drawdown within the buffer (with neighbours): factor fails alone
## Factor R (q) - train | valid | test(desc.) | full
   q=60: 36.0% / -13.4% / 1.44 | 13.6% / -20.2% / 0.50 | 17.5% / -8.2% / 0.84 | 25.5% / -20.2% / 1.10
   q=70: 37.5% / -13.9% / 1.44 | 17.6% / -20.0% / 0.68 | 15.6% / -11.2% / 0.69 | 26.4% / -20.0% / 1.09
   q=80: 42.1% / -13.9% / 1.56 | 15.8% / -20.2% / 0.57 | 17.5% / -12.8% / 0.75 | 28.7% / -20.2% / 1.14
   q=90: 44.7% / -13.9% / 1.57 | 15.2% / -21.2% / 0.53 | 14.8% / -16.6% / 0.55 | 28.8% / -21.2% / 1.09
   -> no interior cell keeps train and valid drawdown within the buffer (with neighbours): factor fails alone
## Factor B (d) - train | valid | test(desc.) | full
   d=0.05: 26.7% / -17.1% / 0.98 | 16.6% / -13.1% / 0.71 | 8.3% / -11.5% / 0.20 | 18.9% / -17.1% / 0.72
   d=0.075: 32.6% / -17.4% / 1.12 | 12.0% / -15.7% / 0.41 | 18.9% / -11.7% / 0.70 | 23.9% / -17.4% / 0.87
   d=0.1: 32.6% / -19.4% / 1.08 | 15.3% / -17.3% / 0.58 | 19.0% / -14.4% / 0.69 | 24.7% / -19.4% / 0.88
   d=0.125: 28.5% / -23.0% / 0.95 | 16.8% / -18.0% / 0.61 | 20.9% / -14.4% / 0.77 | 23.7% / -23.0% / 0.83
   -> no interior cell keeps train and valid drawdown within the buffer (with neighbours): factor fails alone

## Pairs (different factors; each factor at its own chosen cell; also neighbour-robustness shown)

## Summary (CAGR / MaxDD / Sharpe)

| Stack | Train | Valid | Test (desc.) | Full |
|---|---|---|---|---|
| Combo 2x long + 1x short (no factors) | 45.5% / -19.0% / 1.28 | 18.0% / -21.2% / 0.62 | 21.3% / -16.0% / 0.77 | 32.0% / -21.2% / 1.02 |
| Reference: baseline long-only | 22.8% / -13.4% / 1.15 | 13.3% / -7.7% / 0.73 | 10.4% / -6.6% / 0.46 | 17.0% / -13.4% / 0.90 |
| Reference: plain A2 (1x long + 1x short) | 28.0% / -10.8% / 1.28 | 11.7% / -11.7% / 0.47 | 17.8% / -9.7% / 0.96 | 21.4% / -11.7% / 1.04 |