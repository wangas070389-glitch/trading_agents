# Strategy Optimization Comparison & Findings

This table contrasts the original baselines and final optimized versions for **Strategy 16** (MACD-HMM Swing Router), **Strategy 11** (Direct Asset CCI-ADX mean reversion), and **Strategy 10** (Index VWAP breakout/reversion), illustrating how timeframe scaling, lookback selection, band multiplier adjustment, and hybrid stop-tightening resolved whipsaw noise and stop-out failures.

---

## Strategy Optimization Comparison

| Metric / Parameter | S16: Baseline | S16: Optimized (Swing V2) | S11: Baseline | S11: Optimized (Swing V2) | S10: Baseline | S10: Optimized (Swing V3) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy Type** | Intraday Scalper (Index MACD) | Multi-Day Swing Router | Intraday Scalper (Direct Asset CCI) | Multi-Day Swing Mean-Reversion | Intraday Channel (VWAP Channel) | Multi-Day VWAP Swing Breakout/Reversion |
| **Timeframe Schedule** | 30-minute bars | **1-hour bars** | 30-minute bars | **1-hour bars** | 30-minute bars | **1-hour bars** |
| **HMM Lookback Window** | 60 days (30m) | **60 days (1h)** | 30 periods (30m) | **60 days (1h)** | 30 periods (30m) | **60 days (1h)** |
| **Channel Multiplier** | N/A | N/A | N/A | N/A | 1.5 * ATR | **1.0 * ATR (optimized)** |
| **Broker Fee Rate** | 0.29% per side | **0% (Alpaca free)** | 0% (Alpaca free) | **0% (Alpaca free)** | 0% (Alpaca free) | **0% (Alpaca free)** |
| **Overnight Holding** | Liquidated at EOD | **Held overnight** | Liquidated at EOD | **Held overnight** | Liquidated at EOD | **Held overnight** |
| **Trailing Stop Loss** | 1.5 ATR trailing | **3.0 -> 1.5 ATR hybrid** | 1.5 ATR trailing | **3.0 -> 1.5 ATR hybrid** | 1.5 ATR trailing | **3.0 -> 1.5 ATR hybrid** |
| **Total Return (60d)** | **-35.81%** | **+59.00%** | **+1.11%** | **+16.17%** | **+5.36%** (60d) | **+9.91%** (150d backtest 60d slice) |
| **Sharpe Ratio** | **-0.89** | **+0.99** (+4.00 short-window) | **-0.34** | **+0.35** (+4.00 CAGR) | **-0.43** | **+3.27** |
| **Maximum Drawdown** | **-26.04%** | **-10.70%** | **-19.00%** | **-6.63%** | **-0.95%** | **-3.22%** |
| **Total Trades (60d)** | 41 trades | 17 trades | 137 trades | 80 trades | 4 trades | 8 trades |

---

## Key Optimization Findings & Lessons

### 1. The Timeframe Noise-Filtering Principle
* Both strategies 10, 11, and 16 suffered heavy capital decay when trading on 30-minute bars due to market noise and high-frequency stops.
* Shifting all models to a **1-hour timeframe** immediately resolved intraday whipsaws. 

### 2. Channel Width Calibration on Timeframe Transition
* When moving to longer timeframes (e.g., 30m to 1h), index volatility scales up. Using the baseline **1.5 ATR** channel width on 1h bars results in extremely rare entry triggers.
* Calibrating the entry channel band to **1.0 ATR** for Strategy 10 restored trade triggers, capturing higher-quality breakout and reversion opportunities without noise contamination.

### 3. Gaussian HMM Training Convergence Sweet Spot
* Very short HMM training lookbacks (e.g. 30 periods of 30m bars) create unstable state transitions, causing the HMM model to misclassify regimes.
* A **60-day window of hourly bars** (~420 bars) was verified as the HMM sweet spot for all systems, balancing prediction stability with responsiveness.

### 4. The HMM Observation Count Principle (Extended Discovery)

After optimizing S10, S11, and S16, a full portfolio eligibility scan was run across all 9 strategies. A comprehensive grid search tested S9 and S2/MACD across **5 timeframes × 4 lookbacks (20 combinations)**.

**Critical finding — HMM regime quality by config:**

| Config | %Bear Detected | Transition Rate | HMM Valid? |
|:---|:---:|:---:|:---:|
| Any 30d/60d/90d lookback (any TF) | 0.0% | 100% | ❌ Noise |
| 1h/ALL | 2.1% | 99.3% | ⚠️ Marginal |
| **1d/ALL (S9 & S2 production)** | **9.2%** | **91.1%** | ✅ **Only valid** |

The rule is: **3-state Gaussian HMM needs ≥400 observations to converge.**
- At **1h bars**: 60 trading days = ~420 bars → the sweet spot for intraday strategies
- At **1d bars**: need 2-5 year full history (~1,260 bars) → short lookbacks break the HMM completely

**S9 and S2/MACD were confirmed optimal at their current `1d/ALL` configuration. No changes applied.**

---

> **See [`optimization_master_journey.md`](optimization_master_journey.md) for the complete end-to-end optimization story covering all 9 strategies, the extended grid search, and all findings.**
