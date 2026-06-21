# MACD + Trailing Stop Backtest Report

**Generated:** 2026-06-21 00:34:13

## Setup

- Universe: 26 tickers (BMV + US, US converted to MXN)
- Backtest period: 2021-06-21 to 2026-06-19
- Strategy: MACD(12, 26, 9) + 200 SMA trend filter
- Trailing stop: arms at +15.0%, trails at 5.0% below peak
- Position sizing: 10% of equity per trade
- Max concurrent positions: 10
- Transaction cost: 0.29% per side
- Initial capital: $20,000.00 MXN
- Monthly contribution: $2,000.00 MXN

## Results

| Metric | MACD Strategy | Equal-weight Benchmark |
| :--- | ---: | ---: |
| Total return (TWR) | +84.89% | +117.96% |
| CAGR | +13.10% | +16.88% |
| Sharpe (annualized) | 1.27 | -- |
| Max drawdown | -10.94% | -16.15% |
| Final NAV | $203,098.80 | $240,486.16 |

## Trading Activity

- Total buy signals: 51
- Total closed trades: 41
- Win rate: 100.0%
- Total realized P&L: $57,242.36 MXN
- Average P&L per trade: $1,396.16 MXN
- Total transaction fees: $2,822.17 MXN

## Recent Trade Log (last 20)

| Date | Ticker | Action | Shares | Price | Fee | P&L | Reason |
| :--- | :--- | :---: | ---: | ---: | ---: | ---: | :--- |
| 2025-10-13 | CEMEXCPO.MX | BUY | 999 | $17.06 | $49.42 | -- | MACD crossover + bull trend (MA200=13.58) |
| 2025-10-20 | GOOGL | BUY | 3 | $4702.26 | $40.91 | -- | MACD crossover + bull trend (MA200=3644.70) |
| 2025-12-01 | AMXB.MX | SELL | 245 | $20.34 | $14.45 | $510.29 | Trailing stop at 20.43 (peak 21.51) |
| 2025-12-02 | GFNORTEO.MX | BUY | 114 | $161.58 | $53.42 | -- | MACD crossover + bull trend (MA200=150.15) |
| 2025-12-11 | GOOGL | SELL | 3 | $5665.54 | $49.29 | $2,840.55 | Trailing stop at 5671.39 (peak 5969.89) |
| 2025-12-17 | KIMBERA.MX | SELL | 271 | $36.02 | $28.31 | $574.85 | Trailing stop at 37.00 (peak 38.95) |
| 2025-12-19 | GENTERA.MX | BUY | 414 | $44.72 | $53.69 | -- | MACD crossover + bull trend (MA200=39.32) |
| 2025-12-22 | NVDA | BUY | 5 | $3305.25 | $47.93 | -- | MACD crossover + bull trend (MA200=2986.37) |
| 2026-02-04 | CEMEXCPO.MX | SELL | 999 | $20.88 | $60.48 | $3,752.98 | Trailing stop at 21.40 (peak 22.53) |
| 2026-02-04 | BIMBOA.MX | BUY | 316 | $61.94 | $56.76 | -- | MACD crossover + bull trend (MA200=57.36) |
| 2026-02-25 | OMAB.MX | SELL | 68 | $263.60 | $51.98 | $1,597.22 | Trailing stop at 265.05 (peak 279.00) |
| 2026-02-26 | GENTERA.MX | SELL | 414 | $49.14 | $59.00 | $1,770.97 | Trailing stop at 50.58 (peak 53.24) |
| 2026-02-26 | GMEXICOB.MX | BUY | 93 | $213.49 | $57.58 | -- | MACD crossover + bull trend (MA200=144.44) |
| 2026-02-26 | CEMEXCPO.MX | BUY | 913 | $21.85 | $57.86 | -- | MACD crossover + bull trend (MA200=17.53) |
| 2026-02-27 | GFNORTEO.MX | SELL | 114 | $185.60 | $61.36 | $2,676.86 | Trailing stop at 187.72 (peak 197.60) |
| 2026-02-27 | PE&OLES.MX | BUY | 18 | $1095.90 | $57.21 | -- | MACD crossover + bull trend (MA200=735.31) |
| 2026-05-19 | NVDA | SELL | 5 | $3806.08 | $55.19 | $2,448.96 | Trailing stop at 3840.22 (peak 4042.33) |
| 2026-05-21 | AC.MX | BUY | 92 | $221.25 | $59.03 | -- | MACD crossover + bull trend (MA200=192.98) |
| 2026-06-01 | FEMSAUBD.MX | SELL | 82 | $204.01 | $48.51 | $2,325.12 | Trailing stop at 204.24 (peak 214.99) |
| 2026-06-10 | FEMSAUBD.MX | BUY | 92 | $215.58 | $57.52 | -- | MACD crossover + bull trend (MA200=182.93) |

## Verdict

**MACD strategy underperformed** equal-weight by 3.79% CAGR. Win rate of 100.0% across 41 completed trades.
