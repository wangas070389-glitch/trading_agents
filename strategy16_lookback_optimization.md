# Strategy 16: HMM Lookback Days Optimization Report

We evaluated the performance of Strategy 16 (S16 v2 Multi-Day Swing Holder) using different M-HMM training lookback periods (**30 days, 60 days, and 90 days**) across the top timeframes (**1h and 4h**).
The simulation evaluated performance over the last 60 days.

---

## 1. Grid Search Results Table

| Timeframe | HMM Lookback | Final NAV | Total Return (60d) | Sharpe Ratio | Max Drawdown | Trades Executed |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **1h** | **30 days** | **$231,468.12 MXN** | **+15.73%** | **0.28** | **-4.63%** | **11** |
| 1h | 60 days | $217,665.41 MXN | +8.83% | 0.03 | -5.32% | 18 |
| 1h | 90 days | $208,610.12 MXN | +4.31% | -0.19 | -5.32% | 15 |
| **4h** | **30 days (Best)** | **$253,464.79 MXN** | **+26.73%** | **0.36** | **-12.92%** | **3** |
| 4h | 60 days | $222,084.73 MXN | +11.04% | 0.05 | -4.94% | 13 |
| 4h | 90 days | $208,733.64 MXN | +4.37% | -0.18 | -24.55% | 23 |

---

## 2. Key Insights & Observations

### A. The Power of Recency (Short HMM Memory)
*   **30-day HMM lookback** is the clear winner for both timeframes.
    *   **4h TF + 30-day lookback:** Achieved the highest return (**+26.73%**) and Sharpe (**0.36**).
    *   **1h TF + 30-day lookback:** Achieved a stellar **+15.73%** return with **0.28 Sharpe** and a very small Max Drawdown (**-4.63%**).
*   Regimes in modern markets shift quickly. Longer training windows (60 and 90 days) carry too much stale memory of past trends, delaying the HMM's ability to decode recent momentum pivots. A shorter 30-day training lookback makes the model much more agile and adaptive.

### B. Trailing Stop Dynamics on 4h
*   While the 4h + 30-day lookback achieved the highest returns (+26.73%), it had a higher drawdown (-12.92%) over only 3 trades. 
*   In comparison, the **1h + 30-day lookback** executed 11 trades and maintained a much smoother equity curve with a **Max Drawdown of only -4.63%**, which is extremely stable.

---

## 3. Conclusions and Recommended Configuration
*   **Optimal Lookback:** Use **30 days** of training lookback for the HMM model.
*   **Optimal Schedule:** 
    *   If you prefer **maximum return and low trade frequency**, choose the **4h timeframe**.
    *   If you prefer **lower drawdown and a smoother equity curve**, choose the **1h timeframe**.

I have saved this report and pushed the updates to your repository. Let me know if you would like me to implement one of these specific timeframe/lookback configurations in your live production script!
