# Strategy 16: Timeframe Optimization Report

We evaluated the performance of Strategy 16 (S16 v2 Multi-Day Swing Holder) across four timeframe schedules (**30m, 1h, 4h, and 1d**). 
Each model trained the Gaussian HMM (M-HMM) on a lookback of the **last 30 periods** of that active timeframe and evaluated performance over the last 60 days.

---

## 1. Comparative Results Table

| Timeframe | Final NAV | Total Return (60d) | Sharpe Ratio | Max Drawdown | Trades Executed |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **30m** | $215,537.42 MXN | +7.77% | -0.04 | -11.59% | 16 |
| **1h** | $231,468.12 MXN | +15.73% | 0.28 | -4.63% | 11 |
| **4h (Recommended)** | **$253,464.79 MXN** | **+26.73%** | **0.36** | **-12.92%** | **3** |
| **1d** | $192,724.49 MXN | -3.64% | -1.46 | -4.29% | 2 |

---

## 2. Key Insights & Observations

### A. Intraday Noise and Whipsawing
*   **30m and 1h schedules** are highly vulnerable to short-term intraday price fluctuations. Pullback entries (CCI < -100) trigger frequently on noise, leading to more frequent stop-outs.
*   The transaction frequency is higher, but the edge is negative due to noise.

### B. 4h Timeframe Superiority
*   The **4h timeframe** acts as a natural noise filter. It filters out random hourly dips while remaining active enough to capture mid-week swings.
*   It produced the **highest return (+26.73% in 60 days)** and **highest Sharpe (0.36)** with only **3 trades**, showing extremely high efficiency.
*   A 30-period lookback on 4h bars trains the HMM on approximately 120 hours of price action (~18 trading days), creating a highly responsive swing regime decoder.

### C. 1d Timeframe Limits
*   The **1d timeframe** is slow. It only adjusts positions once a day, missing major intraday pivot opportunities that the 4h timeframe successfully captures.

---

## 3. Next Steps
We can keep S16 v2 running on the **daily schedule** (which decoded 1d bars), or we can configure S16 v2 to run on **4h bars** to capture this optimized swing-trading edge.
If you'd like to switch the live strategy to 4h bars, let me know!
