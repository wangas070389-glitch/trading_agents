# Isolated US Stock DCS Value-Growth Strategy Backtest Report

**Period:** 2020-11-10 to 2026-06-18 | **Starting Capital:** $100,000.00 USD

## 1. Executive Performance Summary

| Metric | US Stock DCS Value-Growth | SPY DCA Benchmark |
| :--- | :---: | :---: |
| **CAGR (Time-Weighted Return)** | **31.32%** | **15.66%** |
| **Sharpe Ratio** | **1.19** | **0.69** |
| **Max Drawdown** | **-32.04%** | **-24.50%** |
| **Final Portfolio Value** | **$619,047.43** | **$333,329.81** |
| **Total Deployed Capital (DCA)** | **$167,000.00** | **$167,000.00** |

## 2. Strategy Parameters

- **Universe**: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, AVGO, COST, NFLX, AMD, JPM
- **Screening Criteria**: `DCS (Margin of Safety) >= 0.15` and `Close > SMA 100`
- **Sizing Allocation**: Proportional conviction weighting, capped at `25%` per position, max 5 holdings
- **Monthly Inflow (DCA)**: $1,000.00 USD on month start, deployed to holdings where `Close > SMA 20` and `DCS >= 0.15`
- **Transaction Friction**: 0.29% flat broker fee per transaction

## 3. Trade Log

* **Total Trades Executed**: 20
* **Win Rate**: 75.0%

| Ticker | Entry Date | Exit Date | Entry Price | Exit Price | Shares | Net Profit | Profit % | Reason |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| COST | 2020-11-10 | 2021-02-11 | $337.41 | $332.96 | 60.3 | $-326.45 | -1.32% | Exited Rebalance |
| NVDA | 2020-11-10 | 2021-05-13 | $12.73 | $13.62 | 1597.1 | +$1,349.24 | +6.95% | Exited Rebalance |
| AVGO | 2020-11-10 | 2021-05-13 | $32.99 | $38.90 | 676.8 | +$3,923.31 | +17.91% | Exited Rebalance |
| NFLX | 2021-02-11 | 2021-05-13 | $55.72 | $48.67 | 375.9 | $-2,704.02 | -12.66% | Exited Rebalance |
| MSFT | 2021-05-13 | 2021-08-12 | $233.82 | $278.13 | 44.1 | +$1,918.62 | +18.95% | Exited Rebalance |
| GOOGL | 2021-05-13 | 2021-08-12 | $110.92 | $135.99 | 176.7 | +$4,361.08 | +22.60% | Exited Rebalance |
| META | 2021-05-13 | 2021-11-10 | $279.84 | $324.79 | 60.8 | +$2,674.44 | +16.06% | Exited Rebalance |
| NVDA | 2021-08-12 | 2022-02-10 | $20.20 | $25.74 | 1114.5 | +$6,089.71 | +27.41% | Exited Rebalance |
| NFLX | 2021-11-10 | 2022-02-10 | $64.69 | $40.63 | 569.2 | $-13,764.66 | -37.20% | Exited Rebalance |
| JPM | 2020-11-10 | 2022-02-10 | $105.94 | $139.90 | 228.0 | +$7,650.50 | +32.06% | Exited Rebalance |
| AVGO | 2021-08-12 | 2022-05-12 | $44.74 | $53.11 | 711.8 | +$5,843.79 | +18.69% | Exited Rebalance |
| COST | 2022-02-10 | 2022-05-12 | $409.14 | $463.67 | 76.2 | +$4,051.73 | +13.33% | Exited Rebalance |
| GOOGL | 2022-08-12 | 2022-11-10 | $120.61 | $93.11 | 304.4 | $-8,451.72 | -22.80% | Exited Rebalance |
| JPM | 2022-08-12 | 2023-05-15 | $112.05 | $126.30 | 349.3 | +$4,846.51 | +12.71% | Exited Rebalance |
| NVDA | 2023-05-15 | 2023-08-15 | $18.56 | $43.85 | 1773.6 | +$44,639.12 | +136.30% | Exited Rebalance |
| META | 2023-05-15 | 2023-11-13 | $197.44 | $326.32 | 223.7 | +$28,616.50 | +65.28% | Exited Rebalance |
| JPM | 2023-08-15 | 2023-11-13 | $141.83 | $138.10 | 486.7 | $-2,013.76 | -2.63% | Exited Rebalance |
| JPM | 2024-02-14 | 2024-11-13 | $168.47 | $233.90 | 526.1 | +$34,065.50 | +38.84% | Exited Rebalance |
| NFLX | 2023-05-15 | 2025-11-17 | $31.92 | $110.29 | 1311.5 | +$102,362.91 | +245.52% | Exited Rebalance |
| AVGO | 2022-08-12 | 2026-02-19 | $62.83 | $332.76 | 523.8 | +$140,879.27 | +429.61% | Exited Rebalance |
