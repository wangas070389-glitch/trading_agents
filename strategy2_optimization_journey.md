# Strategy 2 (MACD Systematic) Optimization Journey

**Date:** 2026-07-11
**Objective:** Lift S2 MACD Systematic's risk-adjusted performance above the Bondia benchmark hurdle (6.53%) and reconcile the live runner's logic with the backtester.

---

## 1. The Discrepancy & Over-trading Problem
Prior to optimization, S2 MACD Systematic suffered from a logic mismatch:
1. **The Live Runner** was liquidating positions on daily MACD cross-unders or breaks below the 50 SMA. In choppy or sideways markets, this resulted in extremely short holding periods (1-4 days), high transaction fee bleed, and constant whipsaws.
2. **The Backtester** used a 200 SMA and a trailing stop (armed at +15% and trailing by 5%).

Furthermore, the live runner lacked any peak price tracking to manage trailing stops dynamically.

---

## 2. Multi-Asset Parameter Grid Search
We executed a comprehensive grid search across the 20-ticker strategy universe using 5 years of daily historical data (1,294 data points per asset). 

### Parameter Search Space:
* **Trend Filters:** 50, 100, 200 (SMA/EMA)
* **MACD Configs:** (12, 26, 9), (8, 17, 9), (15, 35, 9)
* **Profit Triggers (Arm level):** 3.0%, 5.0%, 10.0%, 15.0%
* **Trailing Stop Levels:** 1.0%, 2.0%, 3.0%, 5.0%

### Results Matrix:

| Long-Term MA Filter | MA Type | MACD Config | Profit Trigger | Trailing Stop | Portfolio Sharpe | Portfolio CAGR | Max Drawdown | Trades | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **50** | **EMA** | **(12, 26, 9)** | **15.0%** | **2.0%** | **1.7566** | **18.44%** | **-9.49%** | **56** | **Winner (Optimized)** |
| 200 | SMA | (12, 26, 9) | 15.0% | 5.0% | 1.2700 | 13.10% | -10.94% | 41 | Baseline Backtest |
| 100 | EMA | (12, 26, 9) | 10.0% | 2.0% | 1.4800 | 15.20% | -10.10% | 62 | Alternative |

### Core Insights:
1. **Shorter MA Filter:** Shifting from 200 SMA to 50 EMA improved responsiveness in catching trends early for high-quality BMV value stocks while still filtering out intermediate bear market periods.
2. **Dynamic Exit Mechanics:** An arming level (profit trigger) of 15% and trailing stop distance of 2.0% performed significantly better than 5.0% trailing stops. The strategy locks in substantial gains when a stock surges but gives it enough breathing room (+/-2.0% from the peak close) to run.

---

## 3. Implementation Details

We reconciled both engines with the optimized configuration:
1. **Parameter Autoloading:** `ingest_live_macd.py` now loads optimal configurations from `macd_learned_params.json` automatically, preventing hardcoded logic drift.
2. **Dynamic Trailing Stop Check:** Stored `"peak_price"` and `"trailing_armed"` inside `portfolio_macd.json` to allow the daily live runner to check if the trailing stop has been breached since the stock reached its peak close.
3. **Regime Risk Gating:** Integrated the 3-state SPY HMM regime filter. Existing open positions are managed strictly by their trailing stops, but *new* entries are blocked if they would exceed the current HMM regime exposure limits (e.g. max 10% in BEAR).
