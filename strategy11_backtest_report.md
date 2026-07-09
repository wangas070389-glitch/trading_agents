# Strategy 11: Intraday Direct Asset CCI-ADX Leveraged Report
**Simulation Period:** 2026-04-13 to 2026-07-08 (86.0 Days)
**Assets Traded:** TQQQ & SQQQ based on direct asset indicators.
 
## 1. Performance Summary
* **Final Portfolio NAV**: $232,698.93 MXN
* **Total Return**: 16.35%
* **Time-Weighted CAGR**: **90.24%**
* **Annualized Volatility**: 20.19%
* **Sharpe Ratio**: **4.00**
* **Maximum Drawdown**: **-6.76%**
 
## 2. Dynamic Settings
* **CCI Channels (10-period):** Breakout $\pm 100$, Reversion $\pm 150$ (Direct traded assets)
* **ADX Trend strength (7-period):** Threshold 22.0
* **Trailing Stop-Loss:** Hybrid ATR trailing stop (3.0 to 1.5)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-06-12 | 11:30 | SETTLE_LONG_CCI_ZERO | $77.08 | $-3,008.94 |
| 2026-06-15 | 10:30 | SETTLE_LONG_CCI_ZERO | $84.51 | +$1,616.89 |
| 2026-06-15 | 12:30 | SETTLE_LONG_CCI_ZERO | $84.79 | $-331.05 |
| 2026-06-16 | 12:30 | SETTLE_SHORT_CCI_ZERO | $37.81 | +$1,580.77 |
| 2026-06-16 | 14:30 | SETTLE_SHORT_CCI_ZERO | $37.89 | +$591.88 |
| 2026-06-18 | 11:30 | SETTLE_LONG_CCI_ZERO | $82.79 | +$1,801.46 |
| 2026-06-18 | 13:30 | SETTLE_LONG_CCI_ZERO | $82.91 | $-295.02 |
| 2026-06-22 | 10:30 | SETTLE_LONG_CCI_ZERO | $82.16 | $-3,103.51 |
| 2026-06-23 | 15:30 | EXIT_LONG_EOD_CLOSE | $74.42 | $-7,291.60 |
| 2026-06-25 | 14:30 | SETTLE_LONG_CCI_ZERO | $74.46 | $-3,713.73 |
| 2026-06-29 | 11:30 | SETTLE_LONG_CCI_ZERO | $75.86 | +$1,870.61 |
| 2026-06-29 | 13:30 | SETTLE_LONG_CCI_ZERO | $76.75 | $-372.99 |
| 2026-06-30 | 09:30 | SETTLE_LONG_CCI_ZERO | $80.07 | +$7,573.05 |
| 2026-06-30 | 11:30 | SETTLE_LONG_CCI_ZERO | $80.72 | +$1,593.39 |
| 2026-06-30 | 13:30 | SETTLE_LONG_CCI_ZERO | $81.02 | +$74.38 |
| 2026-07-01 | 13:30 | SETTLE_SHORT_CCI_ZERO | $37.60 | +$925.84 |
| 2026-07-02 | 10:30 | SETTLE_SHORT_CCI_ZERO | $39.44 | +$5,247.64 |
| 2026-07-02 | 12:30 | SETTLE_SHORT_CCI_ZERO | $40.28 | +$2,070.90 |
| 2026-07-02 | 14:30 | SETTLE_SHORT_CCI_ZERO | $40.37 | +$1,331.44 |
| 2026-07-07 | 10:30 | SETTLE_SHORT_CCI_ZERO | $40.72 | $-103.90 |
