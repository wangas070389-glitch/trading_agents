# Strategy 11: Intraday Direct Asset CCI-ADX Leveraged Report
**Simulation Period:** 2026-04-10 to 2026-07-07 (88.0 Days)
**Assets Traded:** TQQQ & SQQQ based on direct asset indicators.

## 1. Performance Summary
* **Final Portfolio NAV**: $208,531.33 MXN
* **Total Return**: 4.27%
* **Time-Weighted CAGR**: **18.93%**
* **Annualized Volatility**: 24.50%
* **Sharpe Ratio**: **0.39**
* **Maximum Drawdown**: **-16.31%**

## 2. Dynamic Settings
* **CCI Channels (10-period):** Breakout $\pm 100$, Reversion $\pm 150$ (Direct traded assets)
* **ADX Trend strength (7-period):** Threshold 22.0
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-06-24 | 15:00 | SETTLE_SHORT_CCI_ZERO | $41.01 | $-647.58 |
| 2026-06-25 | 11:00 | SETTLE_LONG_CCI_ZERO | $73.98 | $-324.75 |
| 2026-06-25 | 12:00 | SETTLE_LONG_CCI_ZERO | $75.09 | +$1,856.04 |
| 2026-06-25 | 14:30 | SETTLE_LONG_CCI_ZERO | $75.13 | $-1,834.10 |
| 2026-06-26 | 10:00 | SETTLE_SHORT_CCI_ZERO | $40.16 | $-2,475.36 |
| 2026-06-26 | 15:00 | SETTLE_SHORT_CCI_ZERO | $40.72 | $-594.04 |
| 2026-06-29 | 10:30 | SETTLE_LONG_CCI_ZERO | $74.72 | +$1,765.39 |
| 2026-06-29 | 12:00 | SETTLE_LONG_CCI_ZERO | $75.86 | +$510.94 |
| 2026-06-29 | 14:00 | SETTLE_LONG_CCI_ZERO | $76.75 | $-229.20 |
| 2026-06-30 | 10:00 | SETTLE_LONG_CCI_ZERO | $80.07 | +$772.43 |
| 2026-06-30 | 11:00 | SETTLE_LONG_CCI_ZERO | $80.08 | +$1,849.93 |
| 2026-06-30 | 12:00 | SETTLE_LONG_CCI_ZERO | $80.72 | +$587.27 |
| 2026-07-02 | 10:30 | SETTLE_SHORT_CCI_ZERO | $38.79 | +$1,628.81 |
| 2026-07-02 | 11:30 | SETTLE_SHORT_CCI_ZERO | $39.44 | $-0.00 |
| 2026-07-02 | 12:30 | SETTLE_SHORT_CCI_ZERO | $40.22 | +$1,559.54 |
| 2026-07-02 | 13:30 | SETTLE_SHORT_CCI_ZERO | $40.69 | +$1,856.10 |
| 2026-07-06 | 10:00 | SETTLE_LONG_CCI_ZERO | $76.86 | +$1,418.61 |
| 2026-07-06 | 11:00 | SETTLE_LONG_CCI_ZERO | $77.20 | +$600.19 |
| 2026-07-07 | 10:00 | SETTLE_SHORT_CCI_ZERO | $40.74 | +$2,886.00 |
| 2026-07-07 | 11:00 | SETTLE_SHORT_CCI_ZERO | $40.72 | $-138.73 |
