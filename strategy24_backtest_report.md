# Strategy 24 Backtest Report (30-Minute Random Forest Classifier - Golden Ratio Optimized)
**Executed:** 2026-07-14 22:07:08
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** 2026-04-17 09:30 to 2026-07-14 15:30 (780 bars, 0.24 Years equivalent)

## Optimal Hyperparameters
* **Feature Scale:** Single 35-bar Savitzky-Golay and SRP
* **Number of Estimators:** 30
* **Maximum Depth:** 4
* **Confidence Gate Threshold:** 0.35
* **Minimum Holding Period:** 26 bars (13.0 trading hours equivalent)
* **Trailing Stop-Loss Percentage:** None
* **Retraining Frequency:** Every 50 bars
* **Training Window:** 450 bars

## Full Period Performance Comparison
| Metric | Strategy 24 (30m RF - Golden Ratio) | Benchmark (QQQ Buy-and-Hold) |
| :--- | :---: | :---: |
| **Final Portfolio NAV** | $215,707.19 MXN | $223,657.32 MXN |
| **Cumulative Return** | +7.85% | +11.83% |
| **CAGR (Ann. Eq.)** | +37.37% | +59.93% |
| **Annualized Volatility** | 47.08% | 18.85% |
| **Sharpe Ratio (Rf=9.5%)** | 0.59 | 2.68 |
| **Maximum Drawdown** | -11.92% | -6.64% |

## Out-Of-Sample Validation Performance (Last 15 days)
| Metric | Strategy 24 (Out-of-Sample) | Benchmark (Out-of-Sample) |
| :--- | :---: | :---: |
| **OOS Cumulative Return** | +6.85% | +10.79% |
| **OOS CAGR (Ann. Eq.)** | +93.13% | +176.63% |
| **OOS Sharpe Ratio** | 1.15 | 7.16 |
| **OOS Maximum Drawdown** | -11.92% | -4.34% |

## Execution Statistics
* **Starting Capital:** $200,000.00 MXN
* **Total Transactions:** 15 trades
* **Total Commissions & VAT Paid:** $8,860.79 MXN
* **Position Breakdown:**
  * Cash: 471 bars
  * TQQQ: 254 bars
  * SQQQ: 55 bars
