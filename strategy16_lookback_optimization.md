# Strategy 16: HMM Lookback Days Optimization Report

We evaluated the performance of Strategy 16 (S16 v2 Multi-Day Swing Holder) using different M-HMM training lookback periods (**30 days, 60 days, and 90 days**) across the top timeframes (**1h and 4h**).
The simulation evaluated performance over the last 60 days.

---

## 1. Grid Search Results Table (Final Converged HMMs)

| Timeframe | HMM Lookback | Final NAV | Total Return (60d) | Sharpe Ratio | Max Drawdown | Trades Executed |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| 1h | 30 days | $210,350.32 MXN | +5.18% | -0.13 | -10.13% | 17 |
| **1h** | **60 days (Best)** | **$318,008.86 MXN** | **+59.00%** | **0.99** | **-10.70%** | **17** |
| 1h | 90 days | $240,178.14 MXN | +20.09% | 0.18 | -21.62% | 17 |
| 4h | 30 days | $210,044.97 MXN | +5.02% | -0.13 | -9.60% | 3 |
| 4h | 60 days | $227,080.00 MXN | +13.54% | 0.12 | -13.04% | 2 |
| **4h** | **90 days** | **$229,515.66 MXN** | **+14.76%** | **0.11** | **-13.04%** | **3** |

---

## 2. Key Insights & Observations

### A. The 60-day Lookback Sweet Spot on 1h
*   **1h Timeframe + 60-day HMM training lookback** is the clear ultimate winner, achieving **+59.00% total return** in 60 trading days with a high Sharpe ratio of **0.99** and a controlled drawdown of **-10.70%**.
*   A 60-day window on 1-hour bars (~420 data points) provides the HMM with enough samples to estimate stable regimes, while remaining recent enough to capture macro pivots before they fade.

### B. Lookback Sensitivity on 4h
*   On the **4h timeframe**, a **90-day HMM lookback** performs best (**+14.76%** return), since 4h bars are less frequent and require a longer lookback in days to accumulate enough training samples (~180 bars) for HMM convergence.

---

## 3. Conclusions and Recommended Configuration
*   **Ultimate Winner:** **1h timeframe with a 60-day HMM training lookback**. It delivers stellar profits (+59.00%) with a highly reliable Sharpe (0.99) and active trading (17 trades).
