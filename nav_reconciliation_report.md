# Ledger-first NAV Reconciliation

Audit-only: no portfolio JSON was changed. `Cash delta` is the sum recorded by each ledger; position differences must be resolved before using a ledger as authoritative.

| Strategy | Ledger rows | Ledger positions | Portfolio positions | Position status | Cash delta |
| :--- | ---: | ---: | ---: | :--- | ---: |
| S1 Adaptive Value | 293 | 2 | 3 | MISMATCH | 93,357.34 MXN |
| ↳ difference |  |  |  | AC.MX: ledger 19, portfolio 0, ASURB.MX: ledger 7, portfolio 0, GRUMAB.MX: ledger 0, portfolio 1, ORBIA.MX: ledger 0, portfolio 1538.87, WALMEX.MX: ledger 0, portfolio 696.031 |  |
| ↳ cash/evidence |  |  |  | Line 2: data before header; cash discrepancy -66683.45 |  |
| S2 1d MACD Systematic | 509 | 6 | 8 | MISMATCH | 31,662.00 MXN |
| ↳ difference |  |  |  | AMZN: ledger 0, portfolio 2, GOOGL: ledger 0, portfolio 2 |  |
| ↳ cash/evidence |  |  |  | Line 251: column count does not match header; Line 252: column count does not match header; Line 271: column count does not match header; Line 300: column count does not match header; Line 384: column count does not match header; cash discrepancy -16740.3 |  |
| S3 US Stock Momentum | 26 | 9 | 4 | MISMATCH | -63,620.29 USD |
| ↳ difference |  |  |  | AAPL: ledger 83, portfolio 0, AMD: ledger 0, portfolio 31, AMZN: ledger -149, portfolio 0, AVGO: ledger -45, portfolio 0, COST: ledger -23, portfolio 0, GOOGL: ledger -35, portfolio 0, JPM: ledger -115, portfolio 0, MSFT: ledger -87, portfolio 31, NVDA: ledger 0, portfolio 94, TSLA: ledger -105, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: column count does not match header; Line 7: column count does not match header; Line 8: column count does not match header; Line 9: column count does not match header; cash discrepancy -129590.91 |  |
| S4 US DCF Value-Growth | 8 | 1 | 0 | MISMATCH | -27,461.24 USD |
| ↳ difference |  |  |  | AVGO: ledger 65, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 7: funding sign contradicts action; Line 8: funding sign contradicts action; Line 11: funding sign contradicts action; Line 12: funding sign contradicts action; Line 13: funding sign contradicts action; cash discrepancy 35459.96 |  |
| S5 Alternative Assets | 14 | 3 | 5 | MISMATCH | -332,738.91 USD |
| ↳ difference |  |  |  | DBA: ledger 0, portfolio 733, USO: ledger 0, portfolio 164 |  |
| ↳ cash/evidence |  |  |  | Line 7: funding sign contradicts action; Line 8: column count does not match header; Line 10: column count does not match header; Line 11: column count does not match header; Line 12: column count does not match header; cash discrepancy 1300962.95 |  |
| S6 High-Beta Momentum | 9 | 0 | 0 | MISMATCH | -5,474.07 USD |
| ↳ cash/evidence |  |  |  | Line 5: funding sign contradicts action; Line 9: funding sign contradicts action; Line 11: funding sign contradicts action; Line 12: funding sign contradicts action; Line 13: funding sign contradicts action; cash discrepancy 9537.36 |  |
| S8 Dividend Quality | 459 | 4 | 4 | VERIFIED | -155,002.13 MXN |
| S9 AI Regime Stat-Arb | 524 | 1 | 1 | MISMATCH | -197,887.06 MXN |
| ↳ cash/evidence |  |  |  | Line 232: funding sign contradicts action; Line 351: funding sign contradicts action; Line 444: funding sign contradicts action; Line 517: funding sign contradicts action; cash discrepancy 18083.99 |  |
| S10 Intraday VWAP | 234 | 0 | 0 | MISMATCH | -3,238.59 MXN |
| ↳ cash/evidence |  |  |  | Line 57: unsupported action BUY_TQQQ; Line 60: unsupported action SETTLE_LONG_VWAP; Line 111: funding sign contradicts action; Line 116: unsupported action BUY_TQQQ; Line 121: unsupported action SETTLE_LONG_VWAP; cash discrepancy 16177.86 |  |
| S11 Intraday CCI-ADX | 440 | 0 | 0 | MISMATCH | -3,263.26 MXN |
| ↳ cash/evidence |  |  |  | Line 30: unsupported action BUY_SQQQ; Line 32: unsupported action SETTLE_SHORT_CCI_ZERO; Line 53: unsupported action BUY_TQQQ; Line 55: unsupported action SETTLE_LONG_CCI_ZERO; Line 57: unsupported action BUY_TQQQ; cash discrepancy 19504.01 |  |
| S12 VTTL Trend+Vol | 436 | 1 | 0 | MISMATCH | -1,386.81 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -0.14 |  |
| S13 CARA Cross-Asset | 457 | 1 | 0 | UNRESOLVED | 12,106.28 MXN |
| ↳ cash/evidence |  |  |  | Line 413: unsupported action BUY_USD; Line 423: unsupported action SELL_USD; Line 435: unsupported action BUY_USD; Line 445: unsupported action SELL_USD; Line 458: unsupported action BUY_USD; cash discrepancy None |  |
| S14 HEDGE Aggregator | 862 | 1 | 1 | UNRESOLVED | -19,135.31 MXN |
| ↳ cash/evidence |  |  |  | Line 7: unsupported action BUY_USD; Line 400: unsupported action BUY_USD; Line 585: unsupported action SELL_USD; Line 790: unsupported action BUY_USD; Line 803: unsupported action BUY_USD; cash discrepancy None |  |
| S15 TRACK Tracker | 862 | 1 | 1 | UNRESOLVED | -19,149.85 MXN |
| ↳ cash/evidence |  |  |  | Line 7: unsupported action BUY_USD; Line 400: unsupported action BUY_USD; Line 585: unsupported action SELL_USD; Line 790: unsupported action BUY_USD; Line 803: unsupported action BUY_USD; cash discrepancy None |  |
| S16 HMM Intraday Router | 404 | 0 | 0 | MISMATCH | -4,006.31 MXN |
| ↳ cash/evidence |  |  |  | Line 65: unsupported action BUY_SOXL; Line 76: unsupported action SELL_SOXL; Line 78: unsupported action BUY_URTY; Line 88: unsupported action SELL_URTY; Line 112: unsupported action BUY_URTY; cash discrepancy 18452.37 |  |
| S17 FIBRAs Dynamic | 277 | 4 | 4 | MISMATCH | 5,049.45 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -101553.43 |  |
| S18 Efficient Frontier | 0 | 0 | 0 | UNRESOLVED | 0.00 USD |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: unsupported action REBALANCE; Line 7: unsupported action REBALANCE; Line 8: unsupported action REBALANCE; Line 9: unsupported action REBALANCE; cash discrepancy 0.0 |  |
| S19 Particle Filter QQQ | 63 | 0 | 0 | MISMATCH | -65,513.12 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S20 Hurst Exponent Dynamic | 103 | 0 | 0 | MISMATCH | -22,206.64 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S21 Shannon Entropy Dynamic | 97 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ difference |  |  |  | TQQQ: ledger 197.464, portfolio 137.993 |  |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S22 Walk-Forward ML | 194 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S23 Calculus S&R | 160 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S24 30m Random Forest | 111 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S25 Golden MACD BMV | 360 | 0 | 0 | MISMATCH | 728.73 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S27 Golden Hurst | 345 | 0 | 0 | MISMATCH | 4,149.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S29 Golden Stat-Arb | 348 | 0 | 0 | MISMATCH | 5,491.07 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200588.67 |  |
| S30 Golden MACD US | 365 | 1 | 1 | MISMATCH | -18,933.74 USD |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 100000.0 |  |
| S31 Fibonacci S&R | 63 | 1 | 1 | UNRESOLVED | 0.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: missing cash amount; Line 7: missing cash amount; Line 8: missing cash amount; Line 9: missing cash amount; cash discrepancy 0.0 |  |
