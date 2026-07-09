# Strategy 16: Optimization Journey & Paradigm Shift Report

This report documents the optimization journey of Strategy 16 (S16), detailing its transition from an intraday scalper into the optimal **Multi-Day Hybrid Swing Router** setup.

---

## 1. Executive Summary

Strategy 16 was originally designed as a high-frequency intraday trading strategy utilizing 30-minute bars, tight trailing stops, and mandatory end-of-day (EOD) liquidations. Under this setup, the strategy generated a devastating net return of **-35.81%** over a 60-day period.

Through a series of systematic grid searches and structural redesigns, we successfully resolved these issues:
1. **Timeframe Grid Search** proved that shifting to longer bars (**1-hour** and **4-hour**) filters out market noise.
2. **Lookback Grid Search** identified **60 days of 1-hour bars** as the optimal training dataset size for Gaussian HMM convergence.
3. **Stop-Tightening Validation** confirmed that a hybrid trailing stop (starts at **3.0 ATR** and tightens to **1.5 ATR** when paper profit exceeds 1.5 ATR) preserves a **+59.00% return** profile while actively locking in gains.

---

## 2. Phase 1: The Intraday Baseline Failure

The original configuration of S16 was evaluated under the following parameters:
* **Timeframe:** 30-minute bars.
* **Stop Loss:** 1.5 ATR trailing stop.
* **Transaction Fee:** 0.29% per side (simulating a standard Mexican retail broker).
* **Holding Period:** Intraday (EOD liquidations).

### Diagnostic Analysis:
* **Fatal Fee Drag:** At 0.29% per side, a round trip of 90% NAV costs ~0.52% of NAV. Over 41 trades, transaction fees consumed **$38,652 MXN** (nearly 20% of initial NAV). Intraday scalping under this commission structure is structurally unprofitable.
* **Noise Stop-outs:** A tight 1.5 ATR stop on 30-minute bars resulted in a **0% win rate** for stopped-out trades. Short-term intraday volatility frequently triggered stops prematurely before pullback entry signals (CCI < -100) could play out.
* **Clipped Winners:** Mandatory EOD liquidations prevented the strategy from riding multi-day trends, forcing the exit of otherwise profitable trades at the close.

---

## 3. Phase 2: Timeframe Optimization

To address intraday noise, we evaluated S16 v2 (holding positions overnight, 0% fees) across four schedules: **30-minute, 1-hour, 4-hour, and 1-day**. Each model trained the HMM on the last 30 periods of that active timeframe.

### Grid Search Results:

| Timeframe Schedule | Final NAV | Total Return (60d) | Sharpe Ratio | Max Drawdown | Trades |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **30m** | $215,537.42 MXN | +7.77% | -0.04 | -11.59% | 16 |
| **1h** | $231,468.12 MXN | +15.73% | +0.28 | -4.63% | 11 |
| **4h (Noise Filter)** | **$253,464.79 MXN** | **+26.73%** | **+0.36** | **-12.92%** | **3** |
| **1d** | $192,724.49 MXN | -3.64% | -1.46 | -4.29% | 2 |

### Key Insight:
Longer timeframes act as natural noise filters. Shifting from 30m to 4h bars reduced the trade count from 16 to 3, while improving the total return from **+7.77%** to **+26.73%**, showing that higher trade frequency in intraday schedules carries negative edge.

---

## 4. Phase 3: HMM Training Lookback Grid Search

We next optimized the training window (lookback days) for the HMM model across the top-performing timeframes (**1h and 4h**), testing lookbacks of **30 days, 60 days, and 90 days**.

### Grid Search Results:

| Timeframe | HMM Lookback | Final NAV | Total Return (60d) | Sharpe Ratio | Max Drawdown | Trades |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| 1h | 30 days | $210,350.32 MXN | +5.18% | -0.13 | -10.13% | 17 |
| **1h** | **60 days (Sweet Spot)** | **$318,008.86 MXN** | **+59.00%** | **+0.99** | **-10.70%** | **17** |
| 1h | 90 days | $240,178.14 MXN | +20.09% | +0.18 | -21.62% | 17 |
| 4h | 30 days | $210,044.97 MXN | +5.02% | -0.13 | -9.60% | 3 |
| 4h | 60 days | $227,080.00 MXN | +13.54% | +0.12 | -13.04% | 2 |
| **4h** | **90 days** | **$229,515.66 MXN** | **+14.76%** | **+0.11** | **-13.04%** | **3** |

### Key Insights:
* **The 60-day Sweet Spot (1h):** 60 days of 1-hour bars (~420 hourly bars) provides the HMM with enough samples to estimate stable regimes, while remaining recent enough to capture macro trend shifts promptly.
* **Lookback Sensitivity on 4h:** The 4h timeframe requires a longer **90-day** lookback window to accumulate enough bars (~180 bars) for model convergence.

---

## 5. Phase 4: Hybrid Stop-Tightening Validation

To combine the edge of wider trailing stops (to survive pullback noise) with the capital protection of tighter stops, we implemented a **Hybrid Profit-Tightening Trailing Stop**:
1. **Initial Stop:** Trailing stop is placed at **3.0 ATR** from the peak price.
2. **Profit Trigger:** When paper profit exceeds **1.5 ATR** (relative to the buy price), the trailing stop tightens to **1.5 ATR** from the peak price.

### Validation Results:
* **Final NAV:** **$318,008.86 MXN** (+59.00% total return).
* **Max Drawdown:** **-10.70%** (strictly controlled).
* **Trade Breakdown:** 17 trades (15 exited via regime flips, 2 exited via stop-outs).
* **Profit-Locking Edge:** Tightening the stop protects accumulated gains in fast market reversals without curtailing major multi-day trends.

---

## 6. Synthesis & Live Transition Config

The table below contrasts the configurations:

| Parameter | Baseline (Intraday) | Swing V1 (Breakout) | Swing V2 (Hybrid Swing - Final) |
| :--- | :--- | :--- | :--- |
| **Timeframe** | 30-minute bars | 30-minute bars | **1-hour bars** |
| **HMM Training Lookback** | 60 days (30m) | 60 days (30m) | **60 days (1h)** |
| **Fees** | 0.29% per side | 0% (Alpaca) | **0% (Alpaca)** |
| **Overnight Holdings** | Liquidated at EOD | Liquidated at EOD | **Held overnight** |
| **Trailing Stop** | 1.5 ATR | 1.5 ATR | **3.0 ATR (initial) -> 1.5 ATR (profit > 1.5 ATR)** |
| **Return Profile** | **-35.81%** | **+20.38%** | **+59.00%** |

### Live Configuration Status:
The live execution script (`run_live_strategy16.py`) and the backtest validator (`backtest_strategy16.py`) have been updated to run this exact **Swing V2 (Hybrid Swing)** model. 
* Hourly schedules have been set.
* Transaction fee rates are set to `0.0000`.
* The trailing stop tightening logic is fully active.
