# Strategy 10: Intraday VWAP Leveraged Breakout & Reversion Report
**Simulation Period:** 2026-04-09 to 2026-07-06 (88.0 Days)
**Assets Traded:** TQQQ (3x Long QQQ) & SQQQ (3x Short QQQ) based on QQQ indicators.

## 1. Upgraded Performance Summary
* **Final Portfolio NAV**: $221,664.31 MXN
* **Total Return**: 10.83%
* **Time-Weighted CAGR**: **53.25%**
* **Annualized Volatility**: 16.05%
* **Sharpe Ratio**: **2.73**
* **Maximum Drawdown**: **-4.14%**

## 2. Updated Settings
* **Conditional Overnight Holds:** ACTIVE (Evaluates day-end trend strength)
* **Entry Band Threshold:** 1.5 * ATR (Tightened)
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-04-21 | 15:00 | SETTLE_LONG_VWAP | $58.27 | +$2,094.60 |
| 2026-04-23 | 15:30 | EXIT_LONG_EOD_CLOSE | $59.21 | +$1,119.17 |
| 2026-05-01 | 09:30 | SETTLE_LONG_VWAP | $65.54 | +$6,488.03 |
| 2026-05-07 | 09:30 | SETTLE_LONG_VWAP | $72.08 | +$2,838.31 |
| 2026-05-07 | 11:30 | SETTLE_SHORT_VWAP | $45.27 | +$2,943.18 |
| 2026-05-07 | 15:30 | EXIT_LONG_EOD_CLOSE | $71.34 | +$1,503.82 |
| 2026-05-13 | 15:30 | EXIT_SHORT_EOD_CLOSE | $41.99 | $-749.89 |
| 2026-05-18 | 15:30 | EXIT_LONG_EOD_CLOSE | $74.28 | +$2,761.28 |
| 2026-05-21 | 15:30 | EXIT_LONG_EOD_CLOSE | $76.93 | $-987.59 |
| 2026-05-29 | 09:30 | SETTLE_LONG_VWAP | $85.57 | +$4,971.54 |
| 2026-06-01 | 15:30 | EXIT_LONG_EOD_CLOSE | $86.05 | $-251.39 |
| 2026-06-04 | 15:30 | EXIT_SHORT_EOD_CLOSE | $37.78 | +$679.15 |
| 2026-06-12 | 10:00 | SETTLE_LONG_VWAP | $76.46 | +$1,875.92 |
| 2026-06-16 | 14:30 | EXIT_LONG_TRAILING_STOP | $81.06 | $-3,284.48 |
| 2026-06-16 | 15:30 | EXIT_LONG_EOD_CLOSE | $79.92 | $-2,745.69 |
| 2026-06-24 | 15:30 | EXIT_LONG_EOD_CLOSE | $73.27 | +$2,137.57 |
| 2026-06-30 | 09:30 | SETTLE_LONG_VWAP | $79.72 | +$7,175.51 |
| 2026-06-30 | 15:30 | EXIT_SHORT_EOD_CLOSE | $36.29 | $-166.87 |
| 2026-07-02 | 13:30 | EXIT_LONG_TRAILING_STOP | $71.78 | $-6,926.44 |
| 2026-07-02 | 15:30 | EXIT_LONG_EOD_CLOSE | $73.34 | +$4,252.39 |
