# Walk-Forward Backtest Report

**Generated:** 2026-06-18 02:00:02

## Setup

- Universe: 26 tickers (BMV + US, US converted to MXN)
- Backtest period: 2022-06-07 to 2026-06-17
- Rebalance frequency: every 21 trading days (50 rebalances)
- Transaction cost: 0.29% per trade
- Concentration cap: 40% per ticker
- Initial capital: $20,000.00 MXN
- NLP sentiment: **disabled** (live news in backtest = look-ahead bias)
- Statistical arbitrage: **disabled** (cointegration uses full-sample data)

## Results

| Metric | Strategy | Equal-weight Benchmark |
| :--- | ---: | ---: |
| Total return | +108.89% | +110.09% |
| CAGR | +20.07% | +20.24% |
| Sharpe (annualized) | 0.82 | 1.19 |
| Max drawdown | -28.18% | -12.74% |
| Final NAV | $176,253.68 | $193,683.75 |

## Trading Activity

- Total trades: 250
- Total dollar volume traded: $5,731,144.21 MXN
- Total transaction costs paid: $16,620.32 MXN
- Turnover (volume / initial capital): 286.56x

## Verdict

**Roughly tied** with equal-weight (-0.17% CAGR difference). Risk-adjusted return is worse, so the active trading isn't earning its costs.

**Reading the result honestly:** in-sample backtests on a 27-ticker universe over 5 years with a strategy this complex have very wide confidence intervals. A 2-3% CAGR edge here is well within noise. Repeat on a held-out period and a wider universe (full BMV + S&P) before concluding anything.
