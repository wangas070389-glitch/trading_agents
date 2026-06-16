# Walk-Forward Backtest Report

**Generated:** 2026-06-16 13:42:33

## Setup

- Universe: 26 tickers (BMV + US, US converted to MXN)
- Backtest period: 2022-06-06 to 2026-06-16
- Rebalance frequency: every 21 trading days (50 rebalances)
- Transaction cost: 0.29% per trade
- Concentration cap: 20% per ticker
- Initial capital: $20,000.00 MXN
- NLP sentiment: **disabled** (live news in backtest = look-ahead bias)
- Statistical arbitrage: **disabled** (cointegration uses full-sample data)

## Results

| Metric | Strategy | Equal-weight Benchmark |
| :--- | ---: | ---: |
| Total return | +40.50% | +112.17% |
| CAGR | +8.81% | +20.54% |
| Sharpe (annualized) | 0.74 | 1.18 |
| Max drawdown | -11.22% | -13.42% |
| Final NAV | $28,100.52 | $42,433.96 |

## Trading Activity

- Total trades: 146
- Total dollar volume traded: $520,136.91 MXN
- Total transaction costs paid: $1,508.40 MXN
- Turnover (volume / initial capital): 26.01x

## Verdict

**Strategy underperformed** equal-weight by 11.73% CAGR. Risk-adjusted return is worse, so the active trading isn't earning its costs.

**Reading the result honestly:** in-sample backtests on a 27-ticker universe over 5 years with a strategy this complex have very wide confidence intervals. A 2-3% CAGR edge here is well within noise. Repeat on a held-out period and a wider universe (full BMV + S&P) before concluding anything.
