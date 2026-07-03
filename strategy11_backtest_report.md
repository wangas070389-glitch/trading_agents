# Strategy 11: Intraday CCI-ADX Leveraged Breakout & Reversion Report
**Simulation Period:** 2026-04-08 to 2026-07-02 (85.0 Days)
**Assets Traded:** TQQQ & SQQQ based on QQQ index indicators (CCI & ADX).

## 1. Performance Summary
* **Final Portfolio NAV**: $203,552.39 MXN
* **Total Return**: 1.78%
* **Time-Weighted CAGR**: **7.86%**
* **Annualized Volatility**: 18.18%
* **Sharpe Ratio**: **-0.09**
* **Maximum Drawdown**: **-8.53%**

## 2. Dynamic Settings
* **CCI Channels (20-period):** Breakout $\pm 100$, Reversion $\pm 150$
* **ADX Trend strength (14-period):** Threshold 22.0 (Active Trend / Range switch)
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
| 2026-06-15 | 14:00 | SETTLE_LONG_CCI_ZERO | $83.83 | +$968.59 |
| 2026-06-15 | 15:00 | SETTLE_LONG_CCI_ZERO | $84.51 | +$1,146.79 |
| 2026-06-16 | 14:00 | SETTLE_SHORT_CCI_ZERO | $37.00 | +$2,185.33 |
| 2026-06-16 | 15:00 | SETTLE_SHORT_CCI_ZERO | $37.53 | +$1,147.80 |
| 2026-06-17 | 13:30 | SETTLE_SHORT_CCI_ZERO | $38.21 | +$1,549.76 |
| 2026-06-22 | 14:00 | EXIT_LONG_TRAILING_STOP | $83.43 | $-3,097.28 |
| 2026-06-22 | 15:30 | EXIT_LONG_TRAILING_STOP | $81.83 | $-3,471.21 |
| 2026-06-23 | 14:00 | SETTLE_SHORT_CCI_ZERO | $39.31 | $-900.04 |
| 2026-06-23 | 15:00 | SETTLE_SHORT_CCI_ZERO | $40.26 | +$2,091.99 |
| 2026-06-23 | 18:30 | SETTLE_SHORT_CCI_ZERO | $40.61 | +$1,667.58 |
| 2026-06-24 | 13:30 | SETTLE_SHORT_CCI_ZERO | $39.76 | $-2,544.01 |
| 2026-06-30 | 14:00 | SETTLE_LONG_CCI_ZERO | $80.07 | +$782.36 |
| 2026-06-30 | 15:00 | SETTLE_LONG_CCI_ZERO | $80.08 | +$1,873.70 |
| 2026-07-01 | 14:00 | SETTLE_SHORT_CCI_ZERO | $37.14 | $-97.20 |
| 2026-07-01 | 15:00 | SETTLE_SHORT_CCI_ZERO | $36.94 | $-2,554.17 |
| 2026-07-01 | 18:30 | SETTLE_SHORT_CCI_ZERO | $37.71 | +$497.18 |
| 2026-07-02 | 14:30 | SETTLE_SHORT_CCI_ZERO | $38.79 | +$1,627.20 |
| 2026-07-02 | 15:30 | EXIT_SHORT_EOD_CLOSE | $39.44 | +$0.00 |
| 2026-07-02 | 16:30 | SETTLE_SHORT_CCI_ZERO | $40.22 | +$1,558.00 |
| 2026-07-02 | 17:30 | SETTLE_SHORT_CCI_ZERO | $40.69 | +$1,854.27 |
