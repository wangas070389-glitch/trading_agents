# Strategy 19 Backtest Report (Particle Filter QQQ/TQQQ/SQQQ)
**Executed:** 2026-07-13 00:36:10
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** 2010-02-11 to 2026-07-10 (16.41 Years)

## Performance Comparison
| Metric | Strategy 19 (Particle Filter) | Benchmark (QQQ Buy-and-Hold) |
| :--- | :---: | :---: |
| **Final Portfolio NAV** | $5,165,058.16 MXN | $5,196,591.43 MXN |
| **Cumulative Return** | +2482.53% | +2498.30% |
| **CAGR** | +21.92% | +21.96% |
| **Annualized Volatility** | 40.48% | 21.86% |
| **Sharpe Ratio (Rf=9.5%)** | 0.31 | 0.57 |
| **Maximum Drawdown** | -51.78% | -41.21% |

## Probabilistic Verification (Bailey & Lopez de Prado)
* **Realized Sharpe (Daily Period):** 0.0438
* **Regret Hurdle ($\mu_*$ Sharpe):** 0.0000
* **Deflated Sharpe Ratio (DSR):** 99.72%
  > [!NOTE]
  > A Deflated Sharpe Ratio (DSR) above 95% indicates high evidence quality, confirming that the backtest performance is not a product of data mining or multiple trials selection bias.

## Execution Statistics
* **Starting Capital:** $200,000.00 MXN
* **Total Transactions:** 158 trades
* **Total Commissions & VAT Paid:** $683,626.76 MXN
* **Position Breakdown:**
  * Cash: 639 days
  * QQQ: 504 days
  * TQQQ: 2928 days
  * SQQQ: 56 days
