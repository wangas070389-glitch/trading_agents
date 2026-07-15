# Strategy 23 Backtest Report (Calculus Support/Resistance & RSI Momentum - Optimized)
**Executed:** 2026-07-14 22:03:29
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** 2010-02-11 to 2026-07-13 (16.42 Years)

## Optimal Strategy Parameters
* **Savitzky-Golay Window Length:** 35 days
* **Savitzky-Golay Polynomial Order:** 3
* **RSI Period:** 14 days
* **SRP Buy Threshold:** 0.20
* **SRP Sell Threshold:** 0.70
* **RSI Buy Threshold:** 45
* **RSI Sell Threshold:** 65
* **RSI Breakout Up:** 55
* **RSI Breakout Down:** 45
* **Trailing Stop-Loss Percentage:** None

## Full Period Performance Comparison (2010 - 2026)
| Metric | Strategy 23 (Calculus S&R + RSI) | Benchmark (QQQ Buy-and-Hold) |
| :--- | :---: | :---: |
| **Final Portfolio NAV** | $16,450,929.15 MXN | $5,087,008.64 MXN |
| **Cumulative Return** | +8125.46% | +2443.50% |
| **CAGR** | +30.82% | +21.79% |
| **Annualized Volatility** | 50.61% | 21.87% |
| **Sharpe Ratio (Rf=9.5%)** | 0.42 | 0.56 |
| **Maximum Drawdown** | -70.53% | -41.21% |

## Out-Of-Sample Validation Performance (2022 - 2026)
| Metric | Strategy 23 (Out-of-Sample) | Benchmark (Out-of-Sample) |
| :--- | :---: | :---: |
| **OOS Cumulative Return** | +86.42% | -42.35% |
| **OOS CAGR** | +14.76% | -11.47% |
| **OOS Sharpe Ratio** | 0.09 | -0.82 |
| **OOS Maximum Drawdown** | -69.09% | -38.02% |

## Probabilistic Verification (Bailey & Lopez de Prado)
* **Realized Sharpe (Daily Period):** 0.0495
* **Regret Hurdle ($\mu_*$ Sharpe):** 0.0000
* **Deflated Sharpe Ratio (DSR):** 99.93%

## Execution Statistics
* **Starting Capital:** $200,000.00 MXN
* **Total Transactions:** 384 trades
* **Total Commissions & VAT Paid:** $4,227,798.49 MXN
* **Position Breakdown:**
  * Cash: 1523 days
  * TQQQ: 2520 days
  * SQQQ: 85 days
