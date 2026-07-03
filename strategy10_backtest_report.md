# Strategy 10: Intraday VWAP Leveraged Breakout & Reversion Report
**Simulation Period:** 2026-04-08 to 2026-07-02 (85.0 Days)
**Assets Traded:** TQQQ (3x Long QQQ) & SQQQ (3x Short QQQ) based on QQQ indicators.

## 1. Upgraded Performance Summary
* **Final Portfolio NAV**: $212,933.11 MXN
* **Total Return**: 6.47%
* **Time-Weighted CAGR**: **30.90%**
* **Annualized Volatility**: 10.66%
* **Sharpe Ratio**: **2.01**
* **Maximum Drawdown**: **-4.95%**

## 2. Updated Settings
* **Conditional Overnight Holds:** ACTIVE (Evaluates day-end trend strength)
* **Entry Band Threshold:** 1.5 * ATR (Tightened)
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-04-16 | 14:00 | SETTLE_LONG_VWAP | $55.59 | +$2,842.36 |
| 2026-04-30 | 19:30 | EXIT_SHORT_EOD_CLOSE | $51.67 | $-791.91 |
| 2026-05-06 | 19:30 | EXIT_SHORT_EOD_CLOSE | $45.60 | $-1,678.32 |
| 2026-05-07 | 15:30 | EXIT_LONG_TRAILING_STOP | $72.11 | $-2,686.66 |
| 2026-05-12 | 15:30 | EXIT_LONG_EOD_CLOSE | $72.33 | $-677.51 |
| 2026-05-12 | 18:00 | SETTLE_LONG_VWAP | $73.52 | +$2,990.89 |
| 2026-05-14 | 14:00 | SETTLE_LONG_VWAP | $78.44 | +$3,494.88 |
| 2026-05-18 | 15:30 | EXIT_LONG_EOD_CLOSE | $73.50 | +$717.78 |
| 2026-05-18 | 19:30 | EXIT_LONG_EOD_CLOSE | $74.28 | +$4,403.32 |
| 2026-05-21 | 19:30 | EXIT_LONG_EOD_CLOSE | $76.93 | $-981.26 |
| 2026-05-29 | 13:30 | SETTLE_LONG_VWAP | $85.57 | +$4,939.69 |
| 2026-06-01 | 19:30 | EXIT_LONG_EOD_CLOSE | $86.05 | $-249.78 |
| 2026-06-04 | 19:30 | EXIT_SHORT_EOD_CLOSE | $37.78 | +$674.80 |
| 2026-06-12 | 14:00 | SETTLE_LONG_VWAP | $76.46 | +$1,863.91 |
| 2026-06-16 | 15:30 | EXIT_LONG_EOD_CLOSE | $81.33 | $-2,603.55 |
| 2026-06-16 | 19:30 | EXIT_LONG_EOD_CLOSE | $79.92 | $-3,128.10 |
| 2026-06-29 | 19:30 | EXIT_SHORT_EOD_CLOSE | $38.18 | $-852.98 |
| 2026-06-30 | 19:30 | EXIT_LONG_EOD_CLOSE | $80.96 | $-11.84 |
| 2026-07-02 | 15:30 | EXIT_LONG_EOD_CLOSE | $74.32 | $-12.92 |
| 2026-07-02 | 19:30 | EXIT_LONG_EOD_CLOSE | $73.34 | $-261.28 |
