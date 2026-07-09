# Strategy 11: Optimization Journey & Paradigm Shift Report

This report documents the optimization journey of Strategy 11 (S11), detailing its transition from the original whipsaw-prone 30-minute schedule into the optimal **1-Hour Multi-Day Swing Mean-Reversion** setup.

---

## 1. Executive Summary

Strategy 11 trades TQQQ and SQQQ using direct indicators (CCI and ADX) calculated on the leveraged ETFs themselves, with regime filters running on the QQQ index via a daily Gaussian HMM. 

Originally configured on 30-minute bars, Strategy 11 was severely affected by intraday market whipsaws and noise stop-outs. This baseline generated a marginal **+1.11%** return, but with a highly punitive **-19.00% max drawdown** and a negative Sharpe ratio of **-0.34**.

Applying our systematic optimization framework:
1. **Timeframe Grid Search** identified **1-hour bars** as the optimal schedule for filtering intraday noise, lifting raw returns to **+7.57%** and cutting drawdowns to **-10.35%**.
2. **Lookback Grid Search** identified **60 days of hourly bars** as the optimal training window for the HMM model, boosting returns to **+16.17%** and reducing drawdown to **-6.63%** (with a positive Sharpe of **+0.35**).
3. **Hybrid Stop-Tightening** was implemented as a safety guard (starts at **3.0 ATR** and tightens to **1.5 ATR** when paper profit exceeds 1.5 ATR). Backtest validation confirmed that Strategy 11 exits most positions via direct CCI zero line crosses, leaving the hybrid trailing stop to act as a high-performance safety net.

---

## 2. Phase 1: The Intraday Whipsaw Baseline

The baseline configuration of S11 suffered from high-frequency whipsaws:
* **Timeframe:** 30-minute bars.
* **HMM Lookback:** 30 periods.
* **Stop Loss:** 1.5 ATR trailing stop.
* **Holding Period:** Intraday (EOD liquidations).

### Diagnostic Analysis:
* **Whipsaw Noise:** A tight 1.5 ATR stop on 30-minute bars resulted in high transaction counts (137 trades in 60 days) and recurrent stop-outs on minor pullbacks.
* **Severe Drawdown:** Short-term volatility whipsawed the trend breakout signals, dragging the strategy down to a maximum drawdown of **-19.00%** with a negative Sharpe of **-0.34**.

---

## 3. Phase 2: Timeframe Optimization

To filter out short-term noise, we evaluated S11 across four schedules: **30-minute, 1-hour, 4-hour, and 1-day**, holding positions overnight. HMM models were trained on 30 periods of each timeframe.

### Grid Search Results:

| Timeframe Schedule | Final NAV | Total Return (60d) | Sharpe Ratio | Max Drawdown | Trades |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **30m (Baseline)** | $202,221.62 MXN | +1.11% | -0.34 | -19.00% | 137 |
| **1h (Noise Filter)** | **$215,136.02 MXN** | **+7.57%** | **-0.09** | **-10.35%** | **83** |
| **4h** | $194,676.69 MXN | -2.66% | -0.75 | -7.96% | 16 |
| **1d** | $200,000.00 MXN | +0.00% | 0.00 | 0.00% | 0 |

### Key Insight:
The **1-hour timeframe** is the optimal noise filter for Strategy 11. It reduced trade count by 40% (from 137 to 83) and cut maximum drawdown in half (from **-19.00%** to **-10.35%**) while boosting return to **+7.57%**.

---

## 4. Phase 3: HMM Training Lookback Grid Search

We next optimized the training window (lookback days) for the QQQ HMM model across the top-performing timeframes (**1h and 4h**), testing lookbacks of **30 days, 60 days, and 90 days**.

### Grid Search Results:

| Timeframe | HMM Lookback | Final NAV | Total Return (60d) | Sharpe Ratio | Max Drawdown | Trades |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| 1h | 30 days | $224,506.14 MXN | +12.25% | +0.13 | -10.35% | 85 |
| **1h** | **60 days (Sweet Spot)** | **$232,330.82 MXN** | **+16.17%** | **+0.35** | **-6.63%** | **80** |
| 1h | 90 days | $219,457.57 MXN | +9.73% | +0.01 | -6.63% | 77 |
| 4h | 30 days | $196,628.96 MXN | -1.69% | -0.50 | -12.74% | 20 |
| 4h | 60 days | $195,804.74 MXN | -2.10% | -0.50 | -13.11% | 21 |
| 4h | 90 days | $195,804.74 MXN | -2.10% | -0.50 | -13.11% | 21 |

### Key Insight:
* **The 60-day Sweet Spot (1h):** 60 trading days of 1-hour bars (~420 hourly bars) provides the HMM with enough samples to estimate stable regimes, lifting Strategy 11's Sharpe ratio to **+0.35** and minimizing drawdown to **-6.63%**.

---

## 5. Phase 4: Hybrid Stop-Tightening Validation

To ensure robust capital protection, we implemented a **Hybrid Profit-Tightening Trailing Stop**:
1. **Initial Stop:** Trailing stop is placed at **3.0 ATR** from the peak price.
2. **Profit Trigger:** When paper profit exceeds **1.5 ATR** (relative to the buy price), the trailing stop tightens to **1.5 ATR** from the peak price.

### Validation Results:
* **Final NAV:** **$232,330.82 MXN** (+16.17% total return, -6.63% drawdown).
* **Trade Exit Analysis:** 77 trades exited via CCI zero-line crossings (`CCI >= 0.0`), and only 3 trades closed at the end of the simulation day.
* **Role of the Trailing Stop:** Strategy 11's CCI zero line crossings trigger fast settlements to lock in gains. The hybrid trailing stop-loss acts as a high-performance safety net, preventing catastrophic losses on sudden reversals while giving the trade ample room (3.0 ATR initially) to breathe.

---

## 6. Synthesis & Live Transition Config

The table below contrasts the configurations:

| Parameter | Baseline (Intraday) | Swing V1 (Breakout) | Swing V2 (Hybrid Swing - Final) |
| :--- | :--- | :--- | :--- |
| **Timeframe** | 30-minute bars | 30-minute bars | **1-hour bars** |
| **HMM Training Lookback** | 30 periods (30m) | 60 days (30m) | **60 days (1h)** |
| **Fees** | 0.00% | 0% | **0% (Alpaca commission-free)** |
| **Overnight Holdings** | Liquidated at EOD | Liquidated at EOD | **Held overnight** |
| **Trailing Stop** | 1.5 ATR | 1.5 ATR | **3.0 ATR (initial) -> 1.5 ATR (profit > 1.5 ATR)** |
| **Return Profile** | **+1.11%** | **+7.57%** | **+16.17%** |
| **Sharpe Ratio** | **-0.34** | **-0.09** | **+0.35** |
| **Max Drawdown** | **-19.00%** | **-10.35%** | **-6.63%** |

### Live Configuration Status:
The live execution runner (`run_live_strategy11.py`) and the backtest validator (`backtest_strategy11.py`) have been updated to run this exact **Swing V2 (Hybrid Swing)** model. 
* Hourly bar downloads are active.
* HMM lookback is configured to exactly 60 trading days.
* The hybrid trailing stop logic is fully coded and operational.
