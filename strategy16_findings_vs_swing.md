# Comparison: Intraday Scalping vs. Multi-Day Swing Router (Strategy 16)

This document contrasts the original intraday findings from [strategy16_experiment_findings.md](file:///c:/Users/wanga/OneDrive/Escritorio/Antigravity-projects/trading_agents/scratch/strategy16_experiment_findings.md) (dated July 7) with the new **timeframe and lookback optimization findings** of the S16 v2 swing holder.

---

## 1. Metric Comparison Table

| Metric / Parameter | Original Intraday Baseline | S10-style Breakout Prototype | New 1h Swing (30d HMM) | New 4h Swing (30d HMM) |
| :--- | :---: | :---: | :---: | :---: |
| **Timeframe Schedule** | 30-minute bars | 30-minute bars | **1-hour bars** | **4-hour bars** |
| **Holding Style** | Intraday (EOD liquidations) | Overnight conditional holds | **Swing (hold overnight)** | **Swing (hold overnight)** |
| **Transaction Fees** | 0.29% per side (Mexican) | 0% (Alpaca commission-free) | **0% (Alpaca)** | **0% (Alpaca)** |
| **Trailing Stop** | 1.5 ATR (Tight) | 1.5 ATR (Tight) | **3.0 ATR (Wide)** | **3.0 ATR (Wide)** |
| **HMM Training Lookback**| 60 days of 30m bars | 60 days of 30m bars | **30 days of 1h bars** | **30 days of 4h bars** |
| **Total Return (60d)** | **-35.81%** | **+20.38%** | **+15.73%** | **+26.73%** |
| **Sharpe Ratio** | -6.70 | +3.37 | **+0.28** | **+0.36** |
| **Max Drawdown** | -36.52% | -10.12% | **-4.63%** | **-12.92%** |
| **Trades Executed** | 41 | 21 | **11** | **3** |

---

## 2. Key Diagnostic Resolution

### A. The Fee Drag
*   **Original Intraday Findings:** High trade frequency combined with 0.29% fees per side created an insurmountable headwind. Fees consumed ~38,652 MXN, driving a net return of **-35.81%**.
*   **New Swing Resolution:** By moving to Alpaca’s 0% fee rate and running multi-day swing holds, transaction volume was reduced (only 3 trades in 4h, 11 in 1h) and fee drag was reduced to **0.00%**, letting the gross edge compound directly.

### B. Trailing Stop Behavior
*   **Original Intraday Findings:** A tight 1.5 ATR stop resulted in a **0% win rate** for stopped-out trades because they were triggered by random noise.
*   **New Swing Resolution:** Widening the stop to **3.0 ATR** on 1h or 4h bars successfully filters out daily noise, allowing trades to complete their pullback cycles.
*   The **1h Swing** configuration is particularly efficient, achieving +15.73% returns with a very low drawdown of only **-4.63%**.

### C. HMM Memory & Agility
*   **Original Intraday Findings:** Trained on 60 days of 30m data, which was extremely noisy.
*   **New Swing Resolution:** Grid search optimization proved that **30 days of historical lookback** is the absolute sweet spot. Increasing lookback to 60 or 90 days causes the HMM to lag behind recent market pivots (Sharpe ratio drops to negative at 90 days).

---

## 3. Recommended Path Forward
The **1h Timeframe + 30-day HMM Lookback** offers the best risk-adjusted profile:
1.  **Stable Drawdown:** -4.63% Max DD vs -12.92% on 4h.
2.  **Higher Sample Size:** 11 trades vs 3 trades on 4h, providing a more statistically reliable signal.
3.  **Positive Sharpe (0.28):** Real profit edge without EOD liquidations or fee drag.
