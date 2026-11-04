# Paper-trading plan (deliverable; G5 verdict was NO-GO, so this is the plan for the BASELINE as comparator, not the researched strategy)

- **What to paper trade**: nothing new is authorised by this research. Keep running the Supertrend(14,3) baseline in paper trading as before; the frozen candidate (baseline + VIX-percentile filter + k=2.5 stop sizing) may run beside it as a shadow book for >= 3 months for information only.
- **Order handling**: signal on the 15-min bar close, order at the next bar open (market-on-open for the 09:15 bar, limit with 1-tick tolerance otherwise); log fill price vs the next-bar open for slippage.
- **Roll**: close the near contract and open the next at the close two trading days before expiry (last Thursday monthly until Aug 2025, last Tuesday from Sep 2025; shift to the prior trading day on holidays). Record the actual calendar spread paid.
- **Kill switches**: stop paper run and review if (a) rolling 60-day Sharpe < -1 vs the baseline running beside it, (b) any single trade loses more than 1% of capital including gap, (c) fill-vs-model slippage averages more than 3 bp per side over 20 trades, (d) paper drawdown exceeds 12% (the roadmap's limit).
- **Comparison rule**: the strategy has to beat BOTH the baseline and simply holding Nifty futures after costs over the paper period before any real money.
- **Data to log**: signal time, order time, fill, costs (brokerage, STT, exchange, GST, stamp), roll spread, daily equity; reconcile weekly against the contract note.
