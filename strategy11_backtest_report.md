# Strategy 11: Intraday Direct Asset CCI-ADX Leveraged Report
**Simulation Period:** 2026-04-08 to 2026-07-02 (85.0 Days)
**Assets Traded:** TQQQ & SQQQ based on direct asset indicators.

## 1. Performance Summary
* **Final Portfolio NAV**: $220,048.63 MXN
* **Total Return**: 10.02%
* **Time-Weighted CAGR**: **50.76%**
* **Annualized Volatility**: 21.62%
* **Sharpe Ratio**: **1.91**
* **Maximum Drawdown**: **-11.88%**

## 2. Dynamic Settings
* **CCI Channels (10-period):** Breakout $\pm 100$, Reversion $\pm 150$ (Direct traded assets)
* **ADX Trend strength (7-period):** Threshold 22.0
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-06-23 | 10:00 | SETTLE_SHORT_CCI_ZERO | $39.31 | $-962.73 |
| 2026-06-23 | 11:00 | SETTLE_SHORT_CCI_ZERO | $40.26 | +$2,237.71 |
| 2026-06-23 | 14:30 | SETTLE_SHORT_CCI_ZERO | $40.61 | +$1,783.73 |
| 2026-06-24 | 10:00 | EXIT_SHORT_TRAILING_STOP | $39.70 | $-3,008.40 |
| 2026-06-25 | 11:00 | SETTLE_LONG_CCI_ZERO | $73.98 | $-348.99 |
| 2026-06-25 | 12:00 | SETTLE_LONG_CCI_ZERO | $75.09 | +$1,994.58 |
| 2026-06-25 | 14:30 | SETTLE_LONG_CCI_ZERO | $75.13 | $-1,971.01 |
| 2026-06-29 | 10:30 | SETTLE_LONG_CCI_ZERO | $74.72 | +$1,927.27 |
| 2026-06-29 | 12:00 | SETTLE_LONG_CCI_ZERO | $75.86 | +$557.79 |
| 2026-06-29 | 14:00 | SETTLE_LONG_CCI_ZERO | $76.75 | $-250.21 |
| 2026-06-30 | 10:00 | SETTLE_LONG_CCI_ZERO | $80.07 | +$843.26 |
| 2026-06-30 | 11:00 | SETTLE_LONG_CCI_ZERO | $80.08 | +$2,019.56 |
| 2026-06-30 | 12:00 | SETTLE_LONG_CCI_ZERO | $80.72 | +$641.12 |
| 2026-07-01 | 10:00 | SETTLE_SHORT_CCI_ZERO | $37.14 | $-105.08 |
| 2026-07-01 | 11:00 | SETTLE_SHORT_CCI_ZERO | $36.94 | $-2,761.17 |
| 2026-07-01 | 14:30 | SETTLE_SHORT_CCI_ZERO | $37.71 | +$537.48 |
| 2026-07-02 | 10:30 | SETTLE_SHORT_CCI_ZERO | $38.79 | +$1,759.07 |
| 2026-07-02 | 11:30 | SETTLE_SHORT_CCI_ZERO | $39.44 | $-0.00 |
| 2026-07-02 | 12:30 | SETTLE_SHORT_CCI_ZERO | $40.22 | +$1,684.26 |
| 2026-07-02 | 13:30 | SETTLE_SHORT_CCI_ZERO | $40.69 | +$2,004.54 |
