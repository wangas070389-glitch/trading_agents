# Walk-Forward Backtest Report

**Generated:** 2026-06-19 11:56:51

## Setup

- Strategy profile: **STANDARD**
- Universe: 26 tickers (BMV + US, US converted to MXN)
- Backtest period: 2022-06-09 to 2026-06-19
- Rebalance frequency: every 21 trading days (50 rebalances)
- Transaction cost: 0.29% per trade
- Concentration cap: 20% per ticker
- Max positions: 6
- Dead-zone threshold: 5%
- Initial capital: $20,000.00 MXN
- NLP sentiment: **disabled** (live news in backtest = look-ahead bias)
- Statistical arbitrage: **disabled** (cointegration uses full-sample data)

## Results

| Metric | Strategy | Equal-weight Benchmark |
| :--- | ---: | ---: |
| Total return | +22.38% | +114.85% |
| CAGR | +5.14% | +20.91% |
| Sharpe (annualized) | 0.49 | 1.19 |
| Max drawdown | -12.21% | -13.57% |
| Final NAV | $24,475.33 | $42,969.18 |

## Trading Activity

- Total trades: 146
- Total dollar volume traded: $472,727.54 MXN
- Total transaction costs paid: $1,370.91 MXN
- Turnover (volume / initial capital): 23.64x

## Verdict

**Strategy underperformed** equal-weight by 15.77% CAGR. Risk-adjusted return is worse, so the active trading isn't earning its costs.

**Reading the result honestly:** in-sample backtests on a 27-ticker universe over 5 years with a strategy this complex have very wide confidence intervals. A 2-3% CAGR edge here is well within noise. Repeat on a held-out period and a wider universe (full BMV + S&P) before concluding anything.
