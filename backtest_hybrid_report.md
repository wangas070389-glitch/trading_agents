# Hybrid MACD-DCF Momentum-Value Backtest Report

**Generated:** 2026-06-21 00:42:34

## Setup

- Universe: 26 tickers (BMV + US, US converted to MXN)
- Backtest period: 2022-06-09 to 2026-06-19
- Strategy: MACD + DCF Undervalued (DCS >= 0.05)
- Trailing stop: arms at +20.0%, trails at 7.5% below peak
- Pyramiding: enabled (max 3 tranches, 10% equity each)
- Active DCA Deployment: enabled (deposits routed immediately into top performing undervalued holdings)
- Transaction cost: 0.29% per side
- Initial capital: $20,000.00 MXN
- Monthly contribution: $2,000.00 MXN

## Results

| Metric | Hybrid Strategy | Equal-weight Benchmark |
| :--- | ---: | ---: |
| Total return | +79.50% | +114.29% |
| CAGR | +15.63% | +20.83% |
| Sharpe (annualized) | 1.07 | 1.21 |
| Max drawdown | -10.49% | -12.80% |
| Final NAV | $172,588.66 | $192,599.14 |

## Trading Activity

- Total closed trades (SELL_ALL): 21
- Win rate: 100.0%
- Total transaction costs paid: $2,125.94 MXN
- Total trades executed (BUYs + SELLs): 160

## Recent Trade Log (last 30)

| Date | Ticker | Action | Shares | Price | Fee | P&L | Reason |
| :--- | :--- | :---: | ---: | ---: | ---: | ---: | :--- |
| 2025-10-28 | BIMBOA.MX | BUY_T1 | 221 | $64.73 | $41.49 | -- | MACD crossover + Bull trend + DCF Undervalued (DCS=0.161) |
| 2025-11-03 | BBAJIOO.MX | DCA_BUY | 14 | $44.55 | $1.81 | -- | Active DCA inflow (DCS=1.000, Price>SMA20) |
| 2025-11-03 | VESTA.MX | DCA_BUY | 12 | $55.11 | $1.92 | -- | Active DCA inflow (DCS=0.697, Price>SMA20) |
| 2025-11-03 | FEMSAUBD.MX | DCA_BUY | 3 | $167.92 | $1.46 | -- | Active DCA inflow (DCS=0.535, Price>SMA20) |
| 2025-12-01 | BBAJIOO.MX | DCA_BUY | 14 | $45.71 | $1.86 | -- | Active DCA inflow (DCS=0.993, Price>SMA20) |
| 2025-12-01 | FEMSAUBD.MX | DCA_BUY | 3 | $169.47 | $1.47 | -- | Active DCA inflow (DCS=0.489, Price>SMA20) |
| 2025-12-01 | OMAB.MX | DCA_BUY | 2 | $237.37 | $1.38 | -- | Active DCA inflow (DCS=0.086, Price>SMA20) |
| 2026-01-02 | OMAB.MX | DCA_BUY | 8 | $235.40 | $5.46 | -- | Active DCA inflow (DCS=0.157, Price>SMA20) |
| 2026-01-30 | BBAJIOO.MX | SELL_ALL | 325 | $49.38 | $46.54 | $1,740.15 | Trailing stop at 50.38 (peak 54.47) |
| 2026-02-02 | ORBIA.MX | DCA_BUY | 35 | $18.54 | $1.88 | -- | Active DCA inflow (DCS=1.000, Price>SMA20) |
| 2026-02-02 | FEMSAUBD.MX | DCA_BUY | 3 | $179.45 | $1.56 | -- | Active DCA inflow (DCS=0.440, Price>SMA20) |
| 2026-02-02 | PINFRA.MX | DCA_BUY | 2 | $273.38 | $1.59 | -- | Active DCA inflow (DCS=0.179, Price>SMA20) |
| 2026-02-04 | BIMBOA.MX | BUY_T2 | 260 | $61.94 | $46.70 | -- | Pyramiding entry (crossover, DCS=0.179) |
| 2026-03-02 | VESTA.MX | DCA_BUY | 16 | $60.57 | $2.81 | -- | Active DCA inflow (DCS=0.448, Price>SMA20) |
| 2026-03-02 | FEMSAUBD.MX | DCA_BUY | 5 | $191.64 | $2.78 | -- | Active DCA inflow (DCS=0.390, Price>SMA20) |
| 2026-03-02 | ORBIA.MX | SELL_ALL | 863 | $19.64 | $49.15 | $1,489.30 | Trailing stop at 19.92 (peak 21.53) |
| 2026-03-03 | PINFRA.MX | SELL_ALL | 116 | $278.05 | $93.54 | $6,177.05 | Trailing stop at 280.23 (peak 302.95) |
| 2026-03-20 | ORBIA.MX | BUY_T1 | 818 | $19.11 | $45.33 | -- | MACD crossover + Bull trend + DCF Undervalued (DCS=0.974) |
| 2026-03-24 | BBAJIOO.MX | BUY_T1 | 307 | $51.76 | $46.08 | -- | MACD crossover + Bull trend + DCF Undervalued (DCS=0.999) |
| 2026-03-25 | GFNORTEO.MX | BUY_T1 | 87 | $185.90 | $46.90 | -- | MACD crossover + Bull trend + DCF Undervalued (DCS=0.124) |
| 2026-04-01 | BBAJIOO.MX | DCA_BUY | 12 | $54.96 | $1.91 | -- | Active DCA inflow (DCS=0.999, Price>SMA20) |
| 2026-04-01 | ORBIA.MX | DCA_BUY | 30 | $21.68 | $1.89 | -- | Active DCA inflow (DCS=0.974, Price>SMA20) |
| 2026-04-01 | CUERVO.MX | DCA_BUY | 41 | $15.87 | $1.89 | -- | Active DCA inflow (DCS=0.387, Price>SMA20) |
| 2026-05-01 | BIMBOA.MX | DCA_BUY | 11 | $58.30 | $1.86 | -- | Active DCA inflow (DCS=0.335, Price>SMA20) |
| 2026-05-01 | VESTA.MX | DCA_BUY | 10 | $62.32 | $1.81 | -- | Active DCA inflow (DCS=0.209, Price>SMA20) |
| 2026-05-01 | FEMSAUBD.MX | DCA_BUY | 3 | $206.33 | $1.80 | -- | Active DCA inflow (DCS=0.197, Price>SMA20) |
| 2026-05-25 | ORBIA.MX | SELL_ALL | 848 | $22.01 | $54.13 | $2,327.97 | Trailing stop at 22.01 (peak 23.80) |
| 2026-05-25 | GFNORTEO.MX | BUY_T2 | 92 | $179.12 | $47.79 | -- | Pyramiding entry (crossover, DCS=0.183) |
| 2026-06-01 | BBAJIOO.MX | DCA_BUY | 17 | $56.46 | $2.78 | -- | Active DCA inflow (DCS=0.907, Price>SMA20) |
| 2026-06-01 | CUERVO.MX | DCA_BUY | 70 | $14.12 | $2.87 | -- | Active DCA inflow (DCS=0.525, Price>SMA20) |
