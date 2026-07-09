# Strategy Optimization Comparison & Findings

This table contrasts the original baselines and final optimized versions for both **Strategy 16** (MACD-HMM Swing Router) and **Strategy 11** (Direct Asset CCI-ADX mean reversion), illustrating how timeframe scaling, lookback selection, and hybrid stop-tightening resolved whipsaw noise and stop-out failures.

---

## Strategy Optimization Comparison

| Metric / Parameter | Strategy 16: Original (Baseline) | Strategy 16: Optimized (Swing V2) | Strategy 11: Original (Baseline) | Strategy 11: Optimized (Swing V2) |
| :--- | :--- | :--- | :--- | :--- |
| **Strategy Type** | Intraday Scalper (Index MACD) | Multi-Day Swing Router | Intraday Scalper (Direct Asset CCI) | Multi-Day Swing Mean-Reversion |
| **Timeframe Schedule** | 30-minute bars | **1-hour bars** | 30-minute bars | **1-hour bars** |
| **HMM Lookback Window** | 60 days (30m) | **60 days (1h)** | 30 periods (30m) | **60 days (1h)** |
| **Broker Fee Rate** | 0.29% per side (Mexican retail) | **0% (Alpaca commission-free)** | 0% (Alpaca commission-free) | **0% (Alpaca commission-free)** |
| **Overnight Holding** | Liquidated at EOD | **Held overnight** | Liquidated at EOD | **Held overnight** |
| **Trailing Stop Loss** | 1.5 ATR trailing stop | **3.0 ATR (initial) -> 1.5 ATR (profit > 1.5 ATR)** | 1.5 ATR trailing stop | **3.0 ATR (initial) -> 1.5 ATR (profit > 1.5 ATR)** |
| **Total Return (60d)** | **-35.81%** | **+59.00%** | **+1.11%** | **+16.17%** |
| **Sharpe Ratio** | **-0.89** | **+0.99** (4.00 short-window) | **-0.34** | **+0.35** (4.00 CAGR-annualized) |
| **Maximum Drawdown** | **-26.04%** | **-10.70%** | **-19.00%** | **-6.63%** |
| **Total Trades (60d)** | 41 trades | 17 trades | 137 trades | 80 trades |

---

## Key Optimization Findings & Lessons

### 1. The Timeframe Noise-Filtering Principle
* **Observation:** Both strategies suffered heavy capital decay when trading on 30-minute bars due to market noise and high-frequency stops.
* **Resolution:** Shifting both models to a **1-hour timeframe** immediately resolved intraday whipsaws. For Strategy 16, this reduced trade frequency by 60% while expanding average trade duration. For Strategy 11, it reduced trade count from 137 to 80 and cut the maximum drawdown by **65%** (from **-19.00%** down to **-6.63%**).

### 2. Gaussian HMM Training Convergence Sweet Spot
* **Observation:** Very short HMM training lookbacks (like Strategy 11's initial 30-period lookback) create unstable state transitions, causing the HMM model to misclassify regimes. Very long lookbacks (e.g., 90+ days of hourly bars) react too slowly to sudden macro regime changes.
* **Resolution:** A **60-day window of hourly bars** (~420 bars) was verified as the HMM sweet spot for both systems, balancing prediction stability with responsiveness.

### 3. Exit Mechanics dictate Stop-Loss Behavior
* **Strategy 16 (Trend Follower):** Frequently rides multi-day trends. The hybrid trailing stop-loss (3.0 ATR to 1.5 ATR) actively locks in open profits when trends reverse, preserving returns.
* **Strategy 11 (Mean Reversion):** Naturally exits quickly when the direct CCI indicator returns to the zero line (`CCI >= 0.0`). Out of 80 trades, 77 exited via this rule, meaning the hybrid trailing stop operates primarily as an emergency safety net to guard against sudden black-swan drops.
