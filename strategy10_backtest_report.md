# Strategy 10: Intraday VWAP Leveraged Breakout & Reversion Report
**Simulation Period:** 2026-04-13 to 2026-07-08 (86.0 Days)
**Assets Traded:** TQQQ (3x Long QQQ) & SQQQ (3x Short QQQ) based on QQQ indicators.

## 1. Upgraded Performance Summary
* **Final Portfolio NAV**: $219,821.87 MXN
* **Total Return**: 9.91%
* **Time-Weighted CAGR**: **49.38%**
* **Annualized Volatility**: 12.20%
* **Sharpe Ratio**: **3.27**
* **Maximum Drawdown**: **-3.22%**

## 2. Updated Settings
* **Conditional Overnight Holds:** ACTIVE (Evaluates day-end trend strength)
* **Entry Band Threshold:** 1.0 * ATR (Optimized for 1h Timeframe)
* **Trailing Stop-Loss:** Hybrid 3.0 / 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-04-14 | 09:30 | SETTLE_LONG_VWAP | $52.25 | +$8,988.15 |
| 2026-04-14 | 15:30 | EXIT_SHORT_EOD_CLOSE | $62.03 | $-1,742.46 |
| 2026-04-16 | 10:30 | SETTLE_LONG_VWAP | $56.28 | +$2,687.33 |
| 2026-04-16 | 13:30 | SETTLE_SHORT_VWAP | $59.40 | +$3,197.63 |
| 2026-04-30 | 15:30 | EXIT_SHORT_EOD_CLOSE | $51.67 | $-2,508.77 |
| 2026-05-06 | 15:30 | EXIT_SHORT_EOD_CLOSE | $45.60 | $-2,885.02 |
| 2026-05-08 | 15:30 | EXIT_SHORT_EOD_CLOSE | $42.59 | $-819.93 |
| 2026-05-12 | 13:30 | SETTLE_LONG_VWAP | $73.52 | +$2,348.27 |
| 2026-05-14 | 09:30 | SETTLE_LONG_VWAP | $78.44 | +$3,574.23 |
| 2026-05-18 | 15:30 | EXIT_LONG_EOD_CLOSE | $74.28 | +$2,774.22 |
| 2026-05-19 | 15:30 | EXIT_LONG_EOD_CLOSE | $72.94 | $-3,220.28 |
| 2026-05-22 | 10:30 | SETTLE_LONG_VWAP | $79.00 | +$5,787.86 |
| 2026-05-29 | 11:30 | SETTLE_LONG_VWAP | $84.63 | +$2,874.71 |
| 2026-06-01 | 15:30 | EXIT_LONG_EOD_CLOSE | $86.05 | $-599.81 |
| 2026-06-04 | 15:30 | EXIT_SHORT_EOD_CLOSE | $37.78 | +$685.71 |
| 2026-06-12 | 09:30 | SETTLE_LONG_VWAP | $76.46 | +$1,894.04 |
| 2026-06-29 | 15:30 | EXIT_SHORT_EOD_CLOSE | $38.18 | $-889.99 |
| 2026-07-02 | 15:30 | EXIT_LONG_EOD_CLOSE | $73.34 | $-2,666.78 |
