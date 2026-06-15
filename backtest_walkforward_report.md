# Walk-Forward Backtest Report

**Generated:** 2026-06-15 16:11:35

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
| Total return | +2.84% | +110.97% |
| CAGR | +0.70% | +20.34% |
| Sharpe (annualized) | 0.12 | 1.17 |
| Max drawdown | -18.05% | -13.50% |
| Final NAV | $20,567.30 | $42,193.51 |

## Trading Activity

- Total trades: 192
- Total dollar volume traded: $625,364.26 MXN
- Total transaction costs paid: $1,813.56 MXN
- Turnover (volume / initial capital): 31.27x

## Verdict

**Strategy underperformed** equal-weight by 19.64% CAGR. Risk-adjusted return is worse, so the active trading isn't earning its costs.

**Reading the result honestly:** in-sample backtests on a 27-ticker universe over 5 years with a strategy this complex have very wide confidence intervals. A 2-3% CAGR edge here is well within noise. Repeat on a held-out period and a wider universe (full BMV + S&P) before concluding anything.
