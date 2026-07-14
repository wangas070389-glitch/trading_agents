# Strategy 20 Backtest Report (Hurst Exponent Dynamic Allocation)
**Executed:** 2026-07-13 00:44:48
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** 2010-02-11 to 2026-07-10 (16.41 Years)

## Performance Comparison
| Metric | Strategy 20 (Hurst Exponent) | Benchmark (QQQ Buy-and-Hold) |
| :--- | :---: | :---: |
| **Final Portfolio NAV** | $7,090,194.43 MXN | $5,196,595.09 MXN |
| **Cumulative Return** | +3445.10% | +2498.30% |
| **CAGR** | +24.29% | +21.96% |
| **Annualized Volatility** | 44.05% | 21.86% |
| **Sharpe Ratio (Rf=9.5%)** | 0.34 | 0.57 |
| **Maximum Drawdown** | -63.71% | -41.21% |

## Probabilistic Verification (Bailey & Lopez de Prado)
* **Realized Sharpe (Daily Period):** 0.0452
* **Regret Hurdle ($\mu_*$ Sharpe):** 0.0000
* **Deflated Sharpe Ratio (DSR):** 99.80%

## Execution Statistics
* **Starting Capital:** $200,000.00 MXN
* **Total Transactions:** 72 trades
* **Total Commissions & VAT Paid:** $367,232.47 MXN
* **Position Breakdown:**
  * Cash: 2233 days
  * QQQ: 0 days
  * TQQQ: 1433 days
  * SQQQ: 461 days
