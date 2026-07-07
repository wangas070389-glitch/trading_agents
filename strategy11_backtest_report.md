# Strategy 11: Intraday Direct Asset CCI-ADX Leveraged Report
**Simulation Period:** 2026-04-09 to 2026-07-06 (88.0 Days)
**Assets Traded:** TQQQ & SQQQ based on direct asset indicators.

## 1. Performance Summary
* **Final Portfolio NAV**: $182,968.81 MXN
* **Total Return**: -8.52%
* **Time-Weighted CAGR**: **-30.89%**
* **Annualized Volatility**: 21.00%
* **Sharpe Ratio**: **-1.92**
* **Maximum Drawdown**: **-20.90%**

## 2. Dynamic Settings
* **CCI Channels (10-period):** Breakout $\pm 100$, Reversion $\pm 150$ (Direct traded assets)
* **ADX Trend strength (7-period):** Threshold 22.0
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-06-18 | 09:30 | EXIT_SHORT_TRAILING_STOP | $37.66 | $-6,023.19 |
| 2026-06-22 | 10:00 | EXIT_LONG_TRAILING_STOP | $83.43 | $-2,842.54 |
| 2026-06-22 | 11:30 | EXIT_LONG_TRAILING_STOP | $81.83 | $-3,185.71 |
| 2026-06-22 | 12:30 | SETTLE_SHORT_CCI_ZERO | $37.14 | +$43.96 |
| 2026-06-22 | 15:30 | EXIT_SHORT_EOD_CLOSE | $36.86 | $-1,818.08 |
| 2026-06-24 | 13:30 | SETTLE_SHORT_CCI_ZERO | $40.99 | +$375.16 |
| 2026-06-24 | 15:00 | SETTLE_SHORT_CCI_ZERO | $41.01 | $-590.42 |
| 2026-06-25 | 11:00 | SETTLE_LONG_CCI_ZERO | $73.98 | $-296.09 |
| 2026-06-25 | 12:00 | SETTLE_LONG_CCI_ZERO | $75.09 | +$1,692.21 |
| 2026-06-25 | 14:30 | SETTLE_LONG_CCI_ZERO | $75.13 | $-1,672.20 |
| 2026-06-26 | 10:00 | SETTLE_SHORT_CCI_ZERO | $40.16 | $-2,256.85 |
| 2026-06-26 | 15:00 | SETTLE_SHORT_CCI_ZERO | $40.72 | $-541.60 |
| 2026-06-29 | 10:30 | SETTLE_LONG_CCI_ZERO | $74.72 | +$1,609.56 |
| 2026-06-29 | 12:00 | SETTLE_LONG_CCI_ZERO | $75.86 | +$465.84 |
| 2026-06-29 | 14:00 | SETTLE_LONG_CCI_ZERO | $76.75 | $-208.96 |
| 2026-06-30 | 10:00 | SETTLE_LONG_CCI_ZERO | $80.07 | +$704.25 |
| 2026-06-30 | 11:00 | SETTLE_LONG_CCI_ZERO | $80.08 | +$1,686.63 |
| 2026-06-30 | 12:00 | SETTLE_LONG_CCI_ZERO | $80.72 | +$535.43 |
| 2026-07-06 | 10:00 | SETTLE_LONG_CCI_ZERO | $76.86 | +$1,261.36 |
| 2026-07-06 | 11:00 | SETTLE_LONG_CCI_ZERO | $77.20 | +$533.66 |
