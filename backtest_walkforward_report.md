# Walk-Forward Backtest Report

**Generated:** 2026-06-15 15:52:50

## Setup

- Universe: 26 tickers (BMV + US, US converted to MXN)
- Backtest period: 2022-06-03 to 2026-06-15
- Rebalance frequency: every 21 trading days (50 rebalances)
- Transaction cost: 0.29% per trade
- Concentration cap: 20% per ticker
- Initial capital: $20,000.00 MXN
- NLP sentiment: **disabled** (live news in backtest = look-ahead bias)
- Statistical arbitrage: **disabled** (cointegration uses full-sample data)

## Results

| Metric | Strategy | Equal-weight Benchmark |
| :--- | ---: | ---: |
| Total return | +8.55% | +110.95% |
| CAGR | +2.05% | +20.33% |
| Sharpe (annualized) | 0.43 | 1.17 |
| Max drawdown | -4.93% | -13.50% |
| Final NAV | $21,709.12 | $42,189.04 |

## Trading Activity

- Total trades: 1247
- Total dollar volume traded: $144,898.31 MXN
- Total transaction costs paid: $420.21 MXN
- Turnover (volume / initial capital): 7.24x

## Verdict

**Strategy underperformed** equal-weight by 18.28% CAGR. Risk-adjusted return is worse, so the active trading isn't earning its costs.

**Reading the result honestly:** in-sample backtests on a 27-ticker universe over 5 years with a strategy this complex have very wide confidence intervals. A 2-3% CAGR edge here is well within noise. Repeat on a held-out period and a wider universe (full BMV + S&P) before concluding anything.
