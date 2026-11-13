# DCF Alpha-Momentum Concentrated Backtest Report

**Generated:** 2026-06-21 00:48:28

## Setup

- Universe: 26 tickers (BMV + US, US converted to MXN)
- Backtest period: 2022-06-09 to 2026-06-19
- Strategy: DCF Valuation (DCS >= 0.15) + Momentum Filter (Close > 100 SMA)
- Rebalancing frequency: every 63 trading days (quarterly)
- Position Sizing: Conviction-based allocation, capped at 30% weight per stock (Max 5 positions)
- Active DCA Deployment: enabled (deposits routed immediately into top performing undervalued holdings)
- Transaction cost: 0.29% per side
- Initial capital: $20,000.00 MXN
- Monthly contribution: $2,000.00 MXN

## Results

| Metric | Alpha Strategy | Equal-weight Benchmark |
| :--- | ---: | ---: |
| Total return | +122.25% | +114.29% |
| CAGR | +21.93% | +20.83% |
| Sharpe (annualized) | 1.14 | 1.21 |
| Max drawdown | -12.19% | -12.80% |
| Final NAV | $194,902.06 | $192,599.14 |

## Trading Activity

- Total transaction costs paid: $4,082.01 MXN
- Total trades executed: 168

## Recent Trade Log (last 30)

| Date | Ticker | Action | Shares | Price | Fee | Cost | Reason |
| :--- | :--- | :---: | ---: | ---: | ---: | ---: | :--- |
| 2025-11-03 | FEMSAUBD.MX | DCA_BUY | 3.00 | $167.92 | $1.46 | $505.23 | Active DCA (DCS=0.686, Close>SMA20) |
| 2025-11-03 | VESTA.MX | DCA_BUY | 12.00 | $55.11 | $1.92 | $663.25 | Active DCA (DCS=0.473, Close>SMA20) |
| 2025-11-05 | GFNORTEO.MX | SELL | 181.35 | $161.01 | $84.68 | $29199.42 | Quarterly Rebalance (Target weight: 10.0%) |
| 2025-11-05 | PINFRA.MX | SELL | 177.19 | $253.65 | $130.34 | $44944.39 | Quarterly Rebalance (Target weight: 0.0%) |
| 2025-11-05 | VESTA.MX | SELL | 442.35 | $56.39 | $72.34 | $24944.02 | Quarterly Rebalance (Target weight: 12.8%) |
| 2025-11-05 | FEMSAUBD.MX | BUY | 142.75 | $168.58 | $69.79 | $24134.72 | Quarterly Rebalance (Target weight: 17.2%) |
| 2025-11-05 | ORBIA.MX | BUY | 2699.77 | $16.77 | $131.30 | $45406.42 | Quarterly Rebalance (Target weight: 30.0%) |
| 2025-11-05 | BBAJIOO.MX | BUY | 969.90 | $44.89 | $126.25 | $43661.84 | Quarterly Rebalance (Target weight: 30.0%) |
| 2025-12-01 | BBAJIOO.MX | DCA_BUY | 21.00 | $45.71 | $2.78 | $962.72 | Active DCA (DCS=0.993, Close>SMA20) |
| 2025-12-01 | FEMSAUBD.MX | DCA_BUY | 5.00 | $169.47 | $2.46 | $849.79 | Active DCA (DCS=0.489, Close>SMA20) |
| 2026-01-02 | GFNORTEO.MX | DCA_BUY | 12.00 | $162.10 | $5.64 | $1950.86 | Active DCA (DCS=0.286, Close>SMA20) |
| 2026-02-02 | BBAJIOO.MX | DCA_BUY | 13.00 | $49.38 | $1.86 | $643.79 | Active DCA (DCS=0.993, Close>SMA20) |
| 2026-02-02 | ORBIA.MX | DCA_BUY | 35.00 | $18.54 | $1.88 | $650.78 | Active DCA (DCS=0.962, Close>SMA20) |
| 2026-02-02 | FEMSAUBD.MX | DCA_BUY | 3.00 | $179.45 | $1.56 | $539.92 | Active DCA (DCS=0.489, Close>SMA20) |
| 2026-02-04 | GFNORTEO.MX | SELL | 106.16 | $189.97 | $58.48 | $20166.95 | Quarterly Rebalance (Target weight: 0.0%) |
| 2026-02-04 | GRUMAB.MX | BUY | 62.97 | $324.87 | $59.32 | $20514.96 | Quarterly Rebalance (Target weight: 14.2%) |
| 2026-03-02 | BBAJIOO.MX | DCA_BUY | 12.00 | $54.27 | $1.89 | $653.08 | Active DCA (DCS=1.000, Close>SMA20) |
| 2026-03-02 | VESTA.MX | DCA_BUY | 11.00 | $60.57 | $1.93 | $668.19 | Active DCA (DCS=0.448, Close>SMA20) |
| 2026-03-02 | FEMSAUBD.MX | DCA_BUY | 3.00 | $191.64 | $1.67 | $576.60 | Active DCA (DCS=0.390, Close>SMA20) |
| 2026-04-01 | ORBIA.MX | DCA_BUY | 30.00 | $21.68 | $1.89 | $652.29 | Active DCA (DCS=1.000, Close>SMA20) |
| 2026-04-01 | BBAJIOO.MX | DCA_BUY | 12.00 | $54.96 | $1.91 | $661.45 | Active DCA (DCS=1.000, Close>SMA20) |
| 2026-04-01 | GRUMAB.MX | DCA_BUY | 2.00 | $321.47 | $1.86 | $644.81 | Active DCA (DCS=0.458, Close>SMA20) |
| 2026-05-01 | GRUMAB.MX | DCA_BUY | 2.00 | $303.69 | $1.76 | $609.14 | Active DCA (DCS=0.458, Close>SMA20) |
| 2026-05-01 | VESTA.MX | DCA_BUY | 10.00 | $62.32 | $1.81 | $624.99 | Active DCA (DCS=0.448, Close>SMA20) |
| 2026-05-01 | FEMSAUBD.MX | DCA_BUY | 3.00 | $206.33 | $1.80 | $620.79 | Active DCA (DCS=0.390, Close>SMA20) |
| 2026-05-05 | GRUMAB.MX | SELL | 66.97 | $303.19 | $58.88 | $20303.40 | Quarterly Rebalance (Target weight: 0.0%) |
| 2026-05-05 | VESTA.MX | SELL | 364.18 | $62.12 | $65.61 | $22622.97 | Quarterly Rebalance (Target weight: 0.0%) |
| 2026-05-05 | PINFRA.MX | BUY | 145.77 | $293.64 | $124.13 | $42927.96 | Quarterly Rebalance (Target weight: 21.9%) |
| 2026-06-01 | ORBIA.MX | DCA_BUY | 42.00 | $23.34 | $2.84 | $983.12 | Active DCA (DCS=1.000, Close>SMA20) |
| 2026-06-01 | BBAJIOO.MX | DCA_BUY | 17.00 | $56.46 | $2.78 | $962.60 | Active DCA (DCS=0.907, Close>SMA20) |
