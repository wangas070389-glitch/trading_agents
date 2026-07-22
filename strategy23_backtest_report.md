# Strategy 23 Backtest Report (Calculus Support/Resistance & RSI Momentum - Optimized)
**Executed:** 2026-07-22 00:37:14
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** 2010-02-11 to 2026-07-21 (16.44 Years)

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
| **Final Portfolio NAV** | $7,849,333.42 MXN | $5,042,448.07 MXN |
| **Cumulative Return** | +3824.67% | +2421.22% |
| **CAGR** | +25.01% | +21.69% |
| **Annualized Volatility** | 51.06% | 21.86% |
| **Sharpe Ratio (Rf=9.5%)** | 0.30 | 0.56 |
| **Maximum Drawdown** | -77.36% | -41.21% |

## Out-Of-Sample Validation Performance (2022 - 2026)
| Metric | Strategy 23 (Out-of-Sample) | Benchmark (Out-of-Sample) |
| :--- | :---: | :---: |
| **OOS Cumulative Return** | +38.67% | -10.92% |
| **OOS CAGR** | +7.46% | -2.51% |
| **OOS Sharpe Ratio** | -0.03 | -0.47 |
| **OOS Maximum Drawdown** | -72.11% | -38.02% |

## Probabilistic Verification (Bailey & Lopez de Prado)
* **Realized Sharpe (Daily Period):** 0.0438
* **Regret Hurdle ($\mu_*$ Sharpe):** 0.0000
* **Deflated Sharpe Ratio (DSR):** 99.75%

## Execution Statistics
* **Starting Capital:** $200,000.00 MXN
* **Total Transactions:** 554 trades
* **Total Commissions & VAT Paid:** $4,288,085.75 MXN
* **Position Breakdown:**
  * Cash: 1085 days
  * TQQQ: 2958 days
  * SQQQ: 91 days
