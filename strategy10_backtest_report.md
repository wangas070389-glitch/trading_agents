# Strategy 10: Intraday VWAP Breakout & Reversion Backtest Report
**Simulation Period:** 2026-04-08 to 2026-07-02 (85.0 Days)
**Core Asset traded:** QQQ 30-Minute Bars

## 1. Performance Summary
* **Final Portfolio NAV**: $200,227.12 MXN
* **Total Return**: 0.11%
* **Time-Weighted CAGR**: **0.49%**
* **Annualized Volatility**: 4.05%
* **Sharpe Ratio**: **-2.23**
* **Maximum Drawdown**: **-2.60%**

## 2. Dynamic Settings
* **Intraday Square-off Time:** 15:30 EST (Force close to sweeps)
* **Regime Switching Active:** YES (HMM on SPY returns)
* **Broker Commission Rate:** 0.29%

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-04-15 | 19:30 | CLOSE_LONG | $637.36 | +$440.30 |
| 2026-04-30 | 19:30 | CLOSE_SHORT | $667.57 | +$86.48 |
| 2026-05-12 | 15:30 | CLOSE_LONG | $699.03 | $-233.15 |
| 2026-05-12 | 18:00 | SETTLE_LONG_VWAP | $702.75 | +$1,540.40 |
| 2026-05-13 | 19:30 | CLOSE_LONG | $714.48 | $-456.84 |
| 2026-05-28 | 19:30 | CLOSE_LONG | $735.57 | $-161.40 |
| 2026-06-01 | 19:30 | CLOSE_LONG | $742.69 | $-583.97 |
| 2026-06-04 | 19:30 | CLOSE_SHORT | $740.50 | +$647.07 |
| 2026-06-05 | 19:30 | CLOSE_SHORT | $705.21 | +$1,428.90 |
| 2026-06-09 | 15:30 | CLOSE_SHORT | $697.71 | +$1,046.44 |
| 2026-06-09 | 19:30 | CLOSE_SHORT | $707.96 | $-3,808.13 |
| 2026-07-02 | 19:30 | CLOSE_LONG | $712.74 | $-68.27 |
