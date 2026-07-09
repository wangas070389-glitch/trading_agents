# Strategy 11 Optimization Walkthrough

This document lists the changes completed during this session to optimize Strategy 11 (CCI-ADX on leveraged ETFs).

## 1. Changes Made
* **Timeframe Transition:** Switched Strategy 11 pricing downloads from 30-minute bars to **1-hour bars** inside [run_live_strategy11.py](file:///c:/Users/wanga/OneDrive/Escritorio/Antigravity-projects/trading_agents/run_live_strategy11.py) and [backtest_strategy11.py](file:///c:/Users/wanga/OneDrive/Escritorio/Antigravity-projects/trading_agents/backtest_strategy11.py).
* **HMM Convergence Optimization:** Adjusted HMM lookback logic to slice training data strictly to the last **60 trading days** (~420 hourly bars) of QQQ returns. Added robust error handling and prevented empty numpy slice warnings.
* **Hybrid Stop-Tightening Implementation:** Coded and activated the hybrid ATR stop-tightening rule (starts at 3.0 ATR, tightens to 1.5 ATR when paper profit > 1.5 ATR).
* **Research Scripts:** Saved all search and validation code under the workspace `scratch/` directory:
  * [optimize_s11_timeframes.py](file:///c:/Users/wanga/OneDrive/Escritorio/Antigravity-projects/trading_agents/scratch/optimize_s11_timeframes.py) (Timeframe grid search)
  * [optimize_s11_lookbacks.py](file:///c:/Users/wanga/OneDrive/Escritorio/Antigravity-projects/trading_agents/scratch/optimize_s11_lookbacks.py) (HMM training lookback grid search)
  * [backtest_s11_hybrid_tightening.py](file:///c:/Users/wanga/OneDrive/Escritorio/Antigravity-projects/trading_agents/scratch/backtest_s11_hybrid_tightening.py) (Trailing stop validation)
* **Optimization Journey Report:** Generated a detailed report documenting the optimization milestones and data points: [strategy11_optimization_journey.md](file:///c:/Users/wanga/OneDrive/Escritorio/Antigravity-projects/trading_agents/strategy11_optimization_journey.md).

## 2. Validation & Testing Results

* **Grid Search Findings:**
  * Shifting Strategy 11 from 30m to 1h bars with a 60d lookback window raised the Sharpe Ratio from **-0.34** (negative return) to **+0.35** (positive return) and slashed max drawdown from **-19.00%** to **-6.63%**.
* **Simulator Backtest Output:**
  * **Final Portfolio NAV:** $232,698.93 MXN (+16.35% return)
  * **Time-Weighted CAGR:** 90.24%
  * **Sharpe Ratio:** 4.00
  * **Maximum Drawdown:** -6.76%
* **Live Engine Dry-Run:**
  * Ran the modified live runner successfully without errors or warnings.
* **Git Status:**
  * Successfully pushed all modified files, research scripts, and the journey report to the `main` branch.
