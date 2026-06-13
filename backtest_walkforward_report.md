# Walk-Forward Backtest Report

**Generated:** 2026-06-11 23:29:00

## Setup

- Universe: 26 tickers (BMV + US, US converted to MXN)
- Backtest period: 2022-06-01 to 2026-06-11
- Rebalance frequency: every 21 trading days (50 rebalances)
- Transaction cost: 0.29% per trade
- Concentration cap: 20% per ticker
- Initial capital: $20,000.00 MXN
- NLP sentiment: **disabled** (live news in backtest = look-ahead bias)
- Statistical arbitrage: **disabled** (cointegration uses full-sample data)

## Results

| Metric | Strategy | Equal-weight Benchmark |
| :--- | ---: | ---: |
| Total return | +0.72% | +106.60% |
| CAGR | +0.18% | +19.74% |
| Sharpe (annualized) | 0.06 | 1.13 |
| Max drawdown | -15.88% | -13.48% |
| Final NAV | $20,144.11 | $41,319.03 |

## Trading Activity

- Total trades: 156
- Total dollar volume traded: $507,401.37 MXN
- Total transaction costs paid: $1,471.46 MXN
- Turnover (volume / initial capital): 25.37x

## Verdict

**Strategy underperformed** equal-weight by 19.56% CAGR. Risk-adjusted return is worse, so the active trading isn't earning its costs.

**Reading the result honestly:** in-sample backtests on a 27-ticker universe over 5 years with a strategy this complex have very wide confidence intervals. A 2-3% CAGR edge here is well within noise. Repeat on a held-out period and a wider universe (full BMV + S&P) before concluding anything.
