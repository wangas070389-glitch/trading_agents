# Strategy 11: Intraday Direct Asset CCI-ADX Leveraged Report
**Simulation Period:** 2026-04-08 to 2026-07-02 (85.0 Days)
**Assets Traded:** TQQQ & SQQQ based on direct asset indicators.

## 1. Performance Summary
* **Final Portfolio NAV**: $213,537.77 MXN
* **Total Return**: 6.77%
* **Time-Weighted CAGR**: **32.50%**
* **Annualized Volatility**: 22.38%
* **Sharpe Ratio**: **1.03**
* **Maximum Drawdown**: **-11.02%**

## 2. Dynamic Settings
* **CCI Channels (10-period):** Breakout $\pm 100$, Reversion $\pm 150$ (Direct traded assets)
* **ADX Trend strength (7-period):** Threshold 22.0
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-06-22 | 14:00 | EXIT_LONG_TRAILING_STOP | $83.43 | $-3,287.15 |
| 2026-06-22 | 15:30 | EXIT_LONG_TRAILING_STOP | $81.83 | $-3,684.00 |
| 2026-06-23 | 14:00 | SETTLE_SHORT_CCI_ZERO | $39.31 | $-955.22 |
| 2026-06-23 | 15:00 | SETTLE_SHORT_CCI_ZERO | $40.26 | +$2,220.23 |
| 2026-06-23 | 18:30 | SETTLE_SHORT_CCI_ZERO | $40.61 | +$1,769.80 |
| 2026-06-24 | 14:00 | EXIT_SHORT_TRAILING_STOP | $39.70 | $-2,984.90 |
| 2026-06-25 | 15:00 | SETTLE_LONG_CCI_ZERO | $73.98 | $-346.27 |
| 2026-06-25 | 16:30 | SETTLE_LONG_CCI_ZERO | $74.49 | $-1,506.75 |
| 2026-06-25 | 18:30 | SETTLE_LONG_CCI_ZERO | $75.13 | $-1,923.38 |
| 2026-06-29 | 14:30 | SETTLE_LONG_CCI_ZERO | $74.72 | +$1,880.70 |
| 2026-06-29 | 18:00 | SETTLE_LONG_CCI_ZERO | $76.75 | $-243.53 |
| 2026-06-30 | 14:00 | SETTLE_LONG_CCI_ZERO | $80.07 | +$820.74 |
| 2026-06-30 | 15:00 | SETTLE_LONG_CCI_ZERO | $80.08 | +$1,965.61 |
| 2026-07-01 | 14:00 | SETTLE_SHORT_CCI_ZERO | $37.14 | $-101.97 |
| 2026-07-01 | 15:00 | SETTLE_SHORT_CCI_ZERO | $36.94 | $-2,679.47 |
| 2026-07-01 | 18:30 | SETTLE_SHORT_CCI_ZERO | $37.71 | +$521.57 |
| 2026-07-02 | 14:30 | SETTLE_SHORT_CCI_ZERO | $38.79 | +$1,707.03 |
| 2026-07-02 | 15:30 | EXIT_SHORT_EOD_CLOSE | $39.44 | +$0.00 |
| 2026-07-02 | 16:30 | SETTLE_SHORT_CCI_ZERO | $40.22 | +$1,634.43 |
| 2026-07-02 | 17:30 | SETTLE_SHORT_CCI_ZERO | $40.69 | +$1,945.23 |
