# Isolated Alternative Assets Strategy (Strategy 5) Backtest Report
**Assets Covered:** Crypto (BTC, ETH), Commodities (GLD, SLV, USO, DBA), Forex (EURUSD, GBPUSD, USDMXN, USDJPY)
**Simulation Period:** 2022-01-06 to 2026-06-19

## 1. Executive Performance Summary

| Metric | Alternatives Strategy (Crypto/Forex/Commodities) | SPY Benchmark (Excluding DCA) |
| :--- | :---: | :---: |
| **Total Return (ROI)** | **24.22%** | **75.41%** |
| **CAGR (TWR)** | **3.42%** | **9.10%** |
| **Sharpe Ratio** | **0.61** | -- |
| **Max Drawdown** | **-12.10%** | -- |
| **Total Trades Executed** | **121** | -- |
| **Win Rate** | **38.8%** | -- |
| **Total Invested (DCA)** | **$154,000.00 USD** | -- |
| **Final Portfolio NAV** | **$191,292.87 USD** | -- |

## 2. Strategy Rules and Parameters
- **Crypto Engine:** Trend-Following using SMA 200 and MACD crossover. Trades closed if MACD crosses down or trailing stop hits 5% below peak (armed at +10% return). Max 20% weight.
- **Commodities Engine:** Momentum Breakout using SMA 100 and Donchian Channels (20-day high for buy entry, 10-day low for sell exit). Max 20% weight.
- **Forex Engine:** Mean-Reversion using Bollinger Bands (20 periods, 2 std dev) and RSI (14 periods). Buy when RSI < 35 at lower band, sell when RSI > 65 at upper band. Max 15% weight.
- **General Constraints:** Maximum of 5 concurrent open positions. Friction model: 0.29% round-trip fee.

## 3. Trade Log Summary (Last 30 Completed Trades)
| Asset | Type | Entry Date | Exit Date | Entry Price | Exit Price | P&L | Return % | Reason |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **GBPUSD=X** | FOREX | 2026-06-19 | 2026-06-19 | $1.32 | $1.32 | $+0.00 | +0.00% | Simulation End Forced Exit |
| **EURUSD=X** | FOREX | 2026-03-09 | 2026-06-19 | $1.15 | $1.15 | $-165.83 | -0.56% | Simulation End Forced Exit |
| **USDJPY=X** | FOREX | 2026-01-28 | 2026-06-19 | $152.45 | $161.29 | $+1,714.18 | +5.80% | Overbought (RSI=70.6) at upper Bollinger Band |
| **USO** | COMMODITY | 2026-04-29 | 2026-05-27 | $150.63 | $131.03 | $-5,194.00 | -13.01% | Breakout below 10-day low or bearish trend break |
| **DBA** | COMMODITY | 2026-02-20 | 2026-05-26 | $26.03 | $27.47 | $+2,005.92 | +5.53% | Breakout below 10-day low or bearish trend break |
| **SLV** | COMMODITY | 2026-05-11 | 2026-05-15 | $78.00 | $69.04 | $-4,533.76 | -11.49% | Breakout below 10-day low or bearish trend break |
| **SLV** | COMMODITY | 2026-04-17 | 2026-04-21 | $73.63 | $68.49 | $-2,832.14 | -6.98% | Breakout below 10-day low or bearish trend break |
| **GLD** | COMMODITY | 2026-04-17 | 2026-04-21 | $445.93 | $429.57 | $-1,488.76 | -3.67% | Breakout below 10-day low or bearish trend break |
| **USO** | COMMODITY | 2026-01-27 | 2026-04-17 | $75.66 | $116.04 | $+20,674.56 | +53.37% | Breakout below 10-day low or bearish trend break |
| **GLD** | COMMODITY | 2025-12-01 | 2026-03-18 | $389.75 | $444.74 | $+4,454.19 | +14.11% | Breakout below 10-day low or bearish trend break |
| **USDMXN=X** | FOREX | 2025-05-21 | 2026-03-09 | $19.27 | $17.99 | $-1,569.46 | -6.63% | Overbought (RSI=70.2) at upper Bollinger Band |
| **SLV** | COMMODITY | 2025-11-28 | 2026-01-30 | $51.21 | $75.44 | $+14,780.30 | +47.31% | Breakout below 10-day low or bearish trend break |
| **USO** | COMMODITY | 2026-01-13 | 2026-01-15 | $73.48 | $71.13 | $-1,132.70 | -3.20% | Breakout below 10-day low or bearish trend break |
| **DBA** | COMMODITY | 2026-01-05 | 2026-01-12 | $25.82 | $25.63 | $-251.56 | -0.74% | Breakout below 10-day low or bearish trend break |
| **GBPUSD=X** | FOREX | 2025-07-31 | 2025-12-24 | $1.33 | $1.35 | $+456.14 | +1.93% | Overbought (RSI=70.3) at upper Bollinger Band |
| **EURUSD=X** | FOREX | 2025-11-05 | 2025-12-12 | $1.15 | $1.17 | $+516.77 | +2.21% | Overbought (RSI=68.6) at upper Bollinger Band |
| **ETH-USD** | CRYPTO | 2025-10-26 | 2025-11-03 | $4,157.99 | $3,602.31 | $-3,889.77 | -13.36% | MACD cross down or bearish trend break |
| **SLV** | COMMODITY | 2025-09-19 | 2025-10-27 | $39.04 | $42.40 | $+2,738.40 | +8.61% | Breakout below 10-day low or bearish trend break |
| **GLD** | COMMODITY | 2025-08-28 | 2025-10-27 | $315.03 | $367.01 | $+5,146.02 | +16.50% | Breakout below 10-day low or bearish trend break |
| **ETH-USD** | CRYPTO | 2025-10-02 | 2025-10-10 | $4,487.92 | $3,843.01 | $-4,514.41 | -14.37% | MACD cross down or bearish trend break |
| **USO** | COMMODITY | 2025-09-25 | 2025-09-30 | $76.99 | $73.75 | $-1,354.32 | -4.21% | Breakout below 10-day low or bearish trend break |
| **DBA** | COMMODITY | 2025-08-11 | 2025-09-18 | $25.70 | $26.14 | $+527.28 | +1.69% | Breakout below 10-day low or bearish trend break |
| **EURUSD=X** | FOREX | 2025-07-31 | 2025-09-17 | $1.14 | $1.19 | $+913.90 | +3.87% | Overbought (RSI=65.9) at upper Bollinger Band |
| **ETH-USD** | CRYPTO | 2025-08-23 | 2025-08-25 | $4,776.09 | $4,372.99 | $-2,418.62 | -8.44% | MACD cross down or bearish trend break |
| **ETH-USD** | CRYPTO | 2025-08-09 | 2025-08-15 | $4,263.60 | $4,439.99 | $+1,234.73 | +4.14% | Trailing Stop Triggered (Peak: $4756.28, Trigger: $4518.46) |
| **USO** | COMMODITY | 2025-06-11 | 2025-08-06 | $74.82 | $73.79 | $-437.75 | -1.38% | Breakout below 10-day low or bearish trend break |
| **GLD** | COMMODITY | 2025-07-21 | 2025-07-30 | $313.13 | $300.96 | $-1,229.17 | -3.89% | Breakout below 10-day low or bearish trend break |
| **SLV** | COMMODITY | 2025-06-02 | 2025-07-30 | $31.59 | $33.51 | $+1,918.08 | +6.08% | Breakout below 10-day low or bearish trend break |
| **USDJPY=X** | FOREX | 2025-04-04 | 2025-07-16 | $146.23 | $148.76 | $+407.33 | +1.73% | Overbought (RSI=68.0) at upper Bollinger Band |
| **ETH-USD** | CRYPTO | 2025-07-02 | 2025-07-04 | $2,571.34 | $2,508.52 | $-753.81 | -2.44% | MACD cross down or bearish trend break |
