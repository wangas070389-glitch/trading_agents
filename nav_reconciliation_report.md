# Ledger-first NAV Reconciliation

Audit-only: no portfolio JSON was changed. `Cash delta` is the sum recorded by each ledger; position differences must be resolved before using a ledger as authoritative.

| Strategy | Ledger rows | Ledger positions | Portfolio positions | Position status | Cash delta |
| :--- | ---: | ---: | ---: | :--- | ---: |
| S1 Adaptive Value | 227 | 2 | 4 | MISMATCH | 93,185.70 MXN |
| ↳ difference |  |  |  | AC.MX: ledger 19, portfolio 0, ASURB.MX: ledger 7, portfolio 0, BBAJIOO.MX: ledger 0, portfolio 111.394, GFNORTEO.MX: ledger 0, portfolio 32.2636, GRUMAB.MX: ledger 0, portfolio 1, ORBIA.MX: ledger 0, portfolio 288.364 |  |
| S2 1d MACD Systematic | 207 | 5 | 5 | MATCH | 45,805.73 MXN |
| S3 US Stock Momentum | 44 | 1 | 0 | MISMATCH | -224,112.57 USD |
| ↳ difference |  |  |  | JPM: ledger 75, portfolio 0 |  |
| S4 US DCF Value-Growth | 2 | 1 | 1 | MATCH | -25,781.41 USD |
| S5 Alternative Assets | 8 | 3 | 3 | MATCH | -56,467.45 USD |
| S6 High-Beta Momentum | 3 | 0 | 0 | MATCH | -1,546.34 USD |
| S8 Dividend Quality | 154 | 4 | 4 | MATCH | -159,973.84 MXN |
| S9 AI Regime Stat-Arb | 173 | 0 | 0 | MATCH | -15,093.42 MXN |
| S10 Intraday VWAP | 82 | 0 | 0 | MATCH | 1,299.00 MXN |
| S11 Intraday CCI-ADX | 146 | 0 | 0 | MATCH | 945.62 MXN |
| S12 VTTL Trend+Vol | 135 | 1 | 1 | MATCH | -50,027.67 MXN |
| S13 CARA Cross-Asset | 135 | 1 | 1 | MATCH | -50,029.58 MXN |
| S14 HEDGE Aggregator | 267 | 1 | 1 | MATCH | -35,750.06 MXN |
| S15 TRACK Tracker | 267 | 1 | 1 | MATCH | -35,752.72 MXN |
| S16 HMM Intraday Router | 110 | 0 | 0 | MATCH | 602.41 MXN |
| S17 FIBRAs Dynamic | 5 | 4 | 4 | MATCH | 0.00 MXN |
| S18 Efficient Frontier | 0 | 0 | 0 | MATCH | 0.00 USD |
| S19 Particle Filter QQQ | 2 | 1 | 1 | MATCH | -200,000.00 MXN |
| S20 Hurst Exponent Dynamic | 2 | 1 | 1 | MATCH | -200,000.00 MXN |
| S21 Shannon Entropy Dynamic | 5 | 1 | 1 | MATCH | -200,000.00 MXN |
| S22 Walk-Forward ML | 1 | 1 | 1 | MATCH | -200,000.00 MXN |
| S23 Calculus S&R | 55 | 1 | 1 | MATCH | -200,000.00 MXN |
| S24 30m Random Forest | 9 | 1 | 1 | MATCH | -200,000.00 MXN |
| S25 Golden MACD BMV | 66 | 0 | 0 | MATCH | -1,987.72 MXN |
| S27 Golden Hurst | 55 | 0 | 0 | MATCH | 501.31 MXN |
| S29 Golden Stat-Arb | 54 | 0 | 0 | MATCH | 501.30 MXN |
| S30 Golden MACD US | 54 | 0 | 0 | MATCH | 172.67 USD |
| S31 Fibonacci S&R | 8 | 0 | 0 | MATCH | 0.00 MXN |
