# Strategy 31 Backtest Report (Fibonacci S&R Reversal)
**Executed:** 2026-07-15 23:58:00
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** 2010-01-04 to 2026-07-09 (16.51 Years)

## Performance Comparison of Strategy 31 Variants

We backtested three structural configurations for Strategy 31 to optimize the synergy between short-term Savitzky-Golay support/resistance and macro Fibonacci retracements:

| Metric | Variant A: Long-Short (TQQQ/SQQQ) | Variant B: Long-Only (TQQQ) | Variant C: Long-Only (QQQ - Low Drawdown) | Benchmark (QQQ Buy-and-Hold) |
| :--- | :---: | :---: | :---: | :---: |
| **Final NAV** | $463,099.13 MXN | $1,632,349.47 MXN | $756,037.67 MXN | $4,905,584.00 MXN |
| **Cumulative Return** | +131.55% | +716.17% | +278.02% | +2352.79% |
| **CAGR** | +5.22% | +13.56% | +8.39% | +21.39% |
| **Annualized Volatility** | 27.86% | 26.89% | 9.76% | 21.47% |
| **Sharpe Ratio (Rf=9.5%)** | -0.15 | 0.15 | -0.11 | 0.55 |
| **Maximum Drawdown** | -68.97% | -49.60% | -18.13% | -41.21% |
| **Total Trades** | 184 | 106 | 106 | - |

### 🔍 Key Findings
1. **Leverage/Shorting Drag (Variant A)**: Shorting QQQ via SQQQ during a structural decade-long bull run leads to significant capital erosion and high drawdowns (-68.97%).
2. **Long-Only Outperformance (Variant B)**: Restricting trades only to TQQQ entries when price hits confluence support and exiting to cash on resistance improves CAGR to **13.56%** and reduces maximum drawdown to **-49.60%**.
3. **Volatility Shield (Variant C)**: Removing leverage entirely (trading QQQ instead of TQQQ) cuts the maximum drawdown to just **-18.13%** (more than halving the benchmark's drawdown of -41.21%), albeit with lower raw returns.

