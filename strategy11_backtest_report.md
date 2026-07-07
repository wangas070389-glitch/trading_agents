# Strategy 11: Intraday Direct Asset CCI-ADX Leveraged Report
**Simulation Period:** 2026-04-09 to 2026-07-06 (88.0 Days)
**Assets Traded:** TQQQ & SQQQ based on direct asset indicators.

## 1. Performance Summary
* **Final Portfolio NAV**: $205,481.30 MXN
* **Total Return**: 2.74%
* **Time-Weighted CAGR**: **11.88%**
* **Annualized Volatility**: 24.32%
* **Sharpe Ratio**: **0.10**
* **Maximum Drawdown**: **-16.31%**

## 2. Dynamic Settings
* **CCI Channels (10-period):** Breakout $\pm 100$, Reversion $\pm 150$ (Direct traded assets)
* **ADX Trend strength (7-period):** Threshold 22.0
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-06-24 | 10:00 | EXIT_SHORT_TRAILING_STOP | $39.70 | $-2,798.76 |
| 2026-06-24 | 13:30 | SETTLE_SHORT_CCI_ZERO | $40.99 | +$410.89 |
| 2026-06-24 | 15:00 | SETTLE_SHORT_CCI_ZERO | $41.01 | $-646.65 |
| 2026-06-25 | 11:00 | SETTLE_LONG_CCI_ZERO | $73.98 | $-324.29 |
| 2026-06-25 | 12:00 | SETTLE_LONG_CCI_ZERO | $75.09 | +$1,853.37 |
| 2026-06-25 | 14:30 | SETTLE_LONG_CCI_ZERO | $75.13 | $-1,831.46 |
| 2026-06-26 | 10:00 | SETTLE_SHORT_CCI_ZERO | $40.16 | $-2,471.79 |
| 2026-06-26 | 15:00 | SETTLE_SHORT_CCI_ZERO | $40.72 | $-593.18 |
| 2026-06-29 | 10:30 | SETTLE_LONG_CCI_ZERO | $74.72 | +$1,762.84 |
| 2026-06-29 | 12:00 | SETTLE_LONG_CCI_ZERO | $75.86 | +$510.20 |
| 2026-06-29 | 14:00 | SETTLE_LONG_CCI_ZERO | $76.75 | $-228.87 |
| 2026-06-30 | 10:00 | SETTLE_LONG_CCI_ZERO | $80.07 | +$771.32 |
| 2026-06-30 | 11:00 | SETTLE_LONG_CCI_ZERO | $80.08 | +$1,847.26 |
| 2026-06-30 | 12:00 | SETTLE_LONG_CCI_ZERO | $80.72 | +$586.43 |
| 2026-07-02 | 10:30 | SETTLE_SHORT_CCI_ZERO | $38.79 | +$1,626.46 |
| 2026-07-02 | 11:30 | SETTLE_SHORT_CCI_ZERO | $39.44 | +$0.00 |
| 2026-07-02 | 12:30 | SETTLE_SHORT_CCI_ZERO | $40.22 | +$1,557.29 |
| 2026-07-02 | 13:30 | SETTLE_SHORT_CCI_ZERO | $40.69 | +$1,853.42 |
| 2026-07-06 | 10:00 | SETTLE_LONG_CCI_ZERO | $76.86 | +$1,416.56 |
| 2026-07-06 | 11:00 | SETTLE_LONG_CCI_ZERO | $77.20 | +$599.33 |
