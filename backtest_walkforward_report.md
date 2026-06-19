# Walk-Forward Backtest Report

**Generated:** 2026-06-19 14:13:49

## Setup

- Strategy profile: **ADAPTIVE**
- Universe: 26 tickers (BMV + US, US converted to MXN)
- Backtest period: 2022-06-09 to 2026-06-19
- Rebalance frequency: **Regime-Switching (Bull=63, Sideways=42, Bear=21)**
- Transaction cost: 0.29% per trade
- Concentration cap: **Asymmetric (50% / 30% / 20%)**
- Max positions: 3
- Dead-zone threshold: 5%
- Initial capital: $20,000.00 MXN
- NLP sentiment: **disabled** (live news in backtest = look-ahead bias)
- Statistical arbitrage: **disabled** (cointegration uses full-sample data)

## Results

| Metric | Strategy | Equal-weight Benchmark |
| :--- | ---: | ---: |
| Total return | +70.04% | +115.47% |
| CAGR | +14.09% | +21.00% |
| Sharpe (annualized) | 0.89 | 1.19 |
| Max drawdown | -12.78% | -13.57% |
| Final NAV | $34,007.27 | $43,094.49 |

## Trading Activity

- Total trades: 43
- Total dollar volume traded: $388,975.22 MXN
- Total transaction costs paid: $1,128.03 MXN
- Turnover (volume / initial capital): 19.45x

## Verdict

**Strategy underperformed** equal-weight by 6.91% CAGR. Risk-adjusted return is worse, so the active trading isn't earning its costs.

**Reading the result honestly:** in-sample backtests on a 27-ticker universe over 5 years with a strategy this complex have very wide confidence intervals. A 2-3% CAGR edge here is well within noise. Repeat on a held-out period and a wider universe (full BMV + S&P) before concluding anything.
