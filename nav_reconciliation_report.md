# Ledger-first NAV Reconciliation

Audit-only: no portfolio JSON was changed. `Cash delta` is the sum recorded by each ledger; position differences must be resolved before using a ledger as authoritative.

| Strategy | Ledger rows | Ledger positions | Portfolio positions | Position status | Cash delta |
| :--- | ---: | ---: | ---: | :--- | ---: |
| S1 Adaptive Value | 287 | 2 | 5 | MISMATCH | 93,331.99 MXN |
| ↳ difference |  |  |  | AC.MX: ledger 19, portfolio 0, ASURB.MX: ledger 7, portfolio 0, BBAJIOO.MX: ledger 0, portfolio 634.686, BIMBOA.MX: ledger 0, portfolio 372.276, CUERVO.MX: ledger 0, portfolio 1650.22, GRUMAB.MX: ledger 0, portfolio 1, ORBIA.MX: ledger 0, portfolio 1538.87 |  |
| S2 1d MACD Systematic | 399 | 9 | 9 | MATCH | 1,191.95 MXN |
| S3 US Stock Momentum | 76 | 4 | 3 | MISMATCH | -328,383.50 USD |
| ↳ difference |  |  |  | JPM: ledger 75, portfolio 0 |  |
| S4 US DCF Value-Growth | 6 | 1 | 0 | MISMATCH | -25,461.24 USD |
| ↳ difference |  |  |  | AVGO: ledger 65, portfolio 0 |  |
| S5 Alternative Assets | 13 | 4 | 4 | MATCH | -130,227.01 USD |
| S6 High-Beta Momentum | 7 | 0 | 0 | MATCH | -3,474.07 USD |
| S8 Dividend Quality | 344 | 4 | 4 | MATCH | -155,034.49 MXN |
| S9 AI Regime Stat-Arb | 388 | 0 | 0 | MATCH | -30,797.78 MXN |
| S10 Intraday VWAP | 183 | 0 | 0 | MATCH | -1,415.37 MXN |
| S11 Intraday CCI-ADX | 331 | 0 | 0 | MATCH | -1,466.15 MXN |
| S12 VTTL Trend+Vol | 324 | 1 | 1 | MATCH | -98,875.87 MXN |
| S13 CARA Cross-Asset | 326 | 1 | 1 | MATCH | -99,838.62 MXN |
| S14 HEDGE Aggregator | 638 | 1 | 1 | MATCH | -68,947.93 MXN |
| S15 TRACK Tracker | 638 | 1 | 1 | MATCH | -68,953.03 MXN |
| S16 HMM Intraday Router | 295 | 0 | 0 | MATCH | -2,070.74 MXN |
| S17 FIBRAs Dynamic | 162 | 2 | 2 | MATCH | 51,952.99 MXN |
| S18 Efficient Frontier | 1 | 0 | 0 | MATCH | 0.00 USD |
| S19 Particle Filter QQQ | 31 | 1 | 1 | MATCH | -200,000.00 MXN |
| S20 Hurst Exponent Dynamic | 3 | 1 | 1 | MATCH | -200,000.00 MXN |
| S21 Shannon Entropy Dynamic | 26 | 1 | 0 | MISMATCH | -21,109.24 MXN |
| ↳ difference |  |  |  | TQQQ: ledger 59.4709, portfolio 0 |  |
| S22 Walk-Forward ML | 109 | 0 | 0 | MATCH | 7,355.44 MXN |
| S23 Calculus S&R | 129 | 0 | 0 | MATCH | 6,123.57 MXN |
| S24 30m Random Forest | 68 | 0 | 0 | MATCH | -34,519.98 MXN |
| S25 Golden MACD BMV | 252 | 0 | 0 | MATCH | -2,131.50 MXN |
| S27 Golden Hurst | 239 | 0 | 0 | MATCH | 2,045.59 MXN |
| S29 Golden Stat-Arb | 238 | 0 | 0 | MATCH | 2,045.57 MXN |
| S30 Golden MACD US | 245 | 1 | 1 | MATCH | -17,766.82 USD |
| S31 Fibonacci S&R | 41 | 0 | 0 | MATCH | 0.00 MXN |
