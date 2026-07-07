# Strategy 10: Intraday VWAP Leveraged Breakout & Reversion Report
**Simulation Period:** 2026-04-09 to 2026-07-06 (88.0 Days)
**Assets Traded:** TQQQ (3x Long QQQ) & SQQQ (3x Short QQQ) based on QQQ indicators.

## 1. Upgraded Performance Summary
* **Final Portfolio NAV**: $203,147.96 MXN
* **Total Return**: 1.57%
* **Time-Weighted CAGR**: **6.70%**
* **Annualized Volatility**: 19.08%
* **Sharpe Ratio**: **-0.15**
* **Maximum Drawdown**: **-13.20%**

## 2. Updated Settings
* **Conditional Overnight Holds:** ACTIVE (Evaluates day-end trend strength)
* **Entry Band Threshold:** 1.5 * ATR (Tightened)
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-04-23 | 15:30 | EXIT_LONG_EOD_CLOSE | $59.21 | +$1,107.74 |
| 2026-05-01 | 09:30 | SETTLE_LONG_VWAP | $65.54 | +$6,421.77 |
| 2026-05-07 | 09:30 | SETTLE_LONG_VWAP | $72.08 | +$2,809.32 |
| 2026-05-07 | 11:30 | SETTLE_SHORT_VWAP | $45.27 | +$2,913.12 |
| 2026-05-07 | 15:30 | EXIT_LONG_EOD_CLOSE | $71.34 | +$1,488.46 |
| 2026-05-13 | 15:30 | EXIT_SHORT_EOD_CLOSE | $41.99 | $-742.23 |
| 2026-05-21 | 15:30 | EXIT_SHORT_EOD_CLOSE | $41.97 | +$1,019.16 |
| 2026-05-28 | 15:30 | EXIT_SHORT_EOD_CLOSE | $38.46 | $-688.38 |
| 2026-06-01 | 15:30 | EXIT_SHORT_EOD_CLOSE | $37.41 | +$177.17 |
| 2026-06-04 | 15:30 | EXIT_LONG_EOD_CLOSE | $85.21 | $-708.52 |
| 2026-06-05 | 14:00 | EXIT_LONG_TRAILING_STOP | $74.92 | $-6,093.22 |
| 2026-06-05 | 15:30 | EXIT_LONG_EOD_CLOSE | $73.02 | $-4,641.04 |
| 2026-06-09 | 11:00 | EXIT_LONG_TRAILING_STOP | $71.69 | $-7,089.35 |
| 2026-06-09 | 12:00 | EXIT_LONG_TRAILING_STOP | $69.11 | $-6,225.82 |
| 2026-06-09 | 14:00 | SETTLE_LONG_VWAP | $72.57 | +$8,389.03 |
| 2026-06-11 | 15:30 | EXIT_SHORT_EOD_CLOSE | $40.80 | $-872.77 |
| 2026-06-22 | 15:30 | EXIT_LONG_EOD_CLOSE | $82.58 | +$1,593.67 |
| 2026-06-24 | 15:30 | EXIT_LONG_EOD_CLOSE | $73.27 | +$1,935.66 |
| 2026-06-30 | 09:30 | SETTLE_LONG_VWAP | $79.72 | +$6,497.72 |
| 2026-06-30 | 15:30 | EXIT_SHORT_EOD_CLOSE | $36.29 | $-151.11 |
