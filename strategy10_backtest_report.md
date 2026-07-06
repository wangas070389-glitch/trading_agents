# Strategy 10: Intraday VWAP Leveraged Breakout & Reversion Report
**Simulation Period:** 2026-04-08 to 2026-07-02 (85.0 Days)
**Assets Traded:** TQQQ (3x Long QQQ) & SQQQ (3x Short QQQ) based on QQQ indicators.

## 1. Upgraded Performance Summary
* **Final Portfolio NAV**: $211,948.91 MXN
* **Total Return**: 5.97%
* **Time-Weighted CAGR**: **28.32%**
* **Annualized Volatility**: 11.90%
* **Sharpe Ratio**: **1.58**
* **Maximum Drawdown**: **-6.08%**

## 2. Updated Settings
* **Conditional Overnight Holds:** ACTIVE (Evaluates day-end trend strength)
* **Entry Band Threshold:** 1.5 * ATR (Tightened)
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-04-14 | 15:30 | EXIT_SHORT_EOD_CLOSE | $62.03 | $-1,719.57 |
| 2026-04-16 | 10:00 | SETTLE_LONG_VWAP | $55.59 | +$3,337.77 |
| 2026-04-16 | 14:00 | SETTLE_SHORT_VWAP | $59.40 | +$3,522.74 |
| 2026-04-30 | 15:30 | EXIT_SHORT_EOD_CLOSE | $51.67 | $-806.88 |
| 2026-05-06 | 15:30 | EXIT_SHORT_EOD_CLOSE | $45.60 | $-1,710.04 |
| 2026-05-07 | 11:30 | EXIT_LONG_TRAILING_STOP | $72.11 | $-2,737.44 |
| 2026-05-12 | 14:00 | SETTLE_LONG_VWAP | $73.52 | +$2,339.34 |
| 2026-05-14 | 10:00 | SETTLE_LONG_VWAP | $78.44 | +$3,560.63 |
| 2026-05-18 | 15:30 | EXIT_LONG_EOD_CLOSE | $74.28 | +$2,763.66 |
| 2026-05-21 | 15:30 | EXIT_LONG_EOD_CLOSE | $76.93 | $-988.44 |
| 2026-05-29 | 09:30 | SETTLE_LONG_VWAP | $85.57 | +$4,975.82 |
| 2026-06-01 | 15:30 | EXIT_LONG_EOD_CLOSE | $86.05 | $-251.61 |
| 2026-06-04 | 15:30 | EXIT_SHORT_EOD_CLOSE | $37.78 | +$679.74 |
| 2026-06-12 | 10:00 | SETTLE_LONG_VWAP | $76.46 | +$1,877.54 |
| 2026-06-16 | 14:30 | EXIT_LONG_TRAILING_STOP | $81.06 | $-3,287.31 |
| 2026-06-16 | 15:30 | EXIT_LONG_EOD_CLOSE | $79.92 | $-2,748.06 |
| 2026-06-29 | 15:30 | EXIT_SHORT_EOD_CLOSE | $38.18 | $-858.18 |
| 2026-06-30 | 15:30 | EXIT_LONG_EOD_CLOSE | $80.96 | $-11.92 |
| 2026-07-02 | 13:30 | EXIT_LONG_TRAILING_STOP | $71.78 | $-6,623.05 |
| 2026-07-02 | 15:30 | EXIT_LONG_EOD_CLOSE | $73.34 | +$4,066.13 |
