# Ledger-first NAV Reconciliation

Audit-only: no portfolio JSON was changed. `Cash delta` is the sum recorded by each ledger; position differences must be resolved before using a ledger as authoritative.

| Strategy | Ledger rows | Ledger positions | Portfolio positions | Position status | Cash delta |
| :--- | ---: | ---: | ---: | :--- | ---: |
| S1 Adaptive Value | 287 | 2 | 5 | MISMATCH | 93,331.99 MXN |
| ↳ difference |  |  |  | AC.MX: ledger 19, portfolio 0, ASURB.MX: ledger 7, portfolio 0, BBAJIOO.MX: ledger 0, portfolio 634.686, BIMBOA.MX: ledger 0, portfolio 372.276, CUERVO.MX: ledger 0, portfolio 1650.22, GRUMAB.MX: ledger 0, portfolio 1, ORBIA.MX: ledger 0, portfolio 1538.87 |  |
| ↳ cash/evidence |  |  |  | Line 2: data before header; cash discrepancy -113331.99 |  |
| S2 1d MACD Systematic | 498 | 7 | 9 | MISMATCH | 19,117.52 MXN |
| ↳ difference |  |  |  | AMZN: ledger 0, portfolio 2, GOOGL: ledger 0, portfolio 2 |  |
| ↳ cash/evidence |  |  |  | Line 251: column count does not match header; Line 252: column count does not match header; Line 271: column count does not match header; Line 300: column count does not match header; Line 384: column count does not match header; cash discrepancy -16740.29 |  |
| S3 US Stock Momentum | 26 | 9 | 4 | MISMATCH | -63,620.29 USD |
| ↳ difference |  |  |  | AAPL: ledger 83, portfolio 0, AMD: ledger 0, portfolio 31, AMZN: ledger -149, portfolio 0, AVGO: ledger -45, portfolio 0, COST: ledger -23, portfolio 0, GOOGL: ledger -35, portfolio 0, JPM: ledger -115, portfolio 0, MSFT: ledger -87, portfolio 31, NVDA: ledger 0, portfolio 94, TSLA: ledger -105, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: column count does not match header; Line 7: column count does not match header; Line 8: column count does not match header; Line 9: column count does not match header; cash discrepancy -129590.91 |  |
| S4 US DCF Value-Growth | 8 | 1 | 0 | MISMATCH | -27,461.24 USD |
| ↳ difference |  |  |  | AVGO: ledger 65, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 7: funding sign contradicts action; Line 8: funding sign contradicts action; Line 11: funding sign contradicts action; Line 12: funding sign contradicts action; Line 13: funding sign contradicts action; cash discrepancy 35459.96 |  |
| S5 Alternative Assets | 14 | 3 | 5 | MISMATCH | -332,738.91 USD |
| ↳ difference |  |  |  | DBA: ledger 0, portfolio 733, USO: ledger 0, portfolio 164 |  |
| ↳ cash/evidence |  |  |  | Line 7: funding sign contradicts action; Line 8: column count does not match header; Line 10: column count does not match header; Line 11: column count does not match header; Line 12: column count does not match header; cash discrepancy 1099032.59 |  |
| S6 High-Beta Momentum | 9 | 0 | 0 | MISMATCH | -5,474.07 USD |
| ↳ cash/evidence |  |  |  | Line 5: funding sign contradicts action; Line 9: funding sign contradicts action; Line 11: funding sign contradicts action; Line 12: funding sign contradicts action; Line 13: funding sign contradicts action; cash discrepancy 9511.47 |  |
| S8 Dividend Quality | 447 | 4 | 4 | VERIFIED | -149,738.14 MXN |
| S9 AI Regime Stat-Arb | 513 | 0 | 0 | MISMATCH | -36,150.58 MXN |
| ↳ cash/evidence |  |  |  | Line 232: funding sign contradicts action; Line 351: funding sign contradicts action; Line 444: funding sign contradicts action; Line 517: funding sign contradicts action; cash discrepancy 18083.98 |  |
| S10 Intraday VWAP | 229 | 0 | 0 | MISMATCH | -1,504.44 MXN |
| ↳ cash/evidence |  |  |  | Line 57: unsupported action BUY_TQQQ; Line 60: unsupported action SETTLE_LONG_VWAP; Line 111: funding sign contradicts action; Line 116: unsupported action BUY_TQQQ; Line 121: unsupported action SETTLE_LONG_VWAP; cash discrepancy 12177.86 |  |
| S11 Intraday CCI-ADX | 432 | 0 | 0 | MISMATCH | -3,414.11 MXN |
| ↳ cash/evidence |  |  |  | Line 30: unsupported action BUY_SQQQ; Line 32: unsupported action SETTLE_SHORT_CCI_ZERO; Line 53: unsupported action BUY_TQQQ; Line 55: unsupported action SETTLE_LONG_CCI_ZERO; Line 57: unsupported action BUY_TQQQ; cash discrepancy 19504.01 |  |
| S12 VTTL Trend+Vol | 426 | 1 | 1 | MISMATCH | -65,809.91 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -0.07 |  |
| S13 CARA Cross-Asset | 445 | 1 | 0 | UNRESOLVED | 11,982.88 MXN |
| ↳ cash/evidence |  |  |  | Line 413: unsupported action BUY_USD; Line 423: unsupported action SELL_USD; Line 435: unsupported action BUY_USD; Line 445: unsupported action SELL_USD; Currency-specific balances require an FX ledger reconciliation; cash discrepancy None |  |
| S14 HEDGE Aggregator | 845 | 1 | 1 | UNRESOLVED | -30,479.54 MXN |
| ↳ cash/evidence |  |  |  | Line 7: unsupported action BUY_USD; Line 400: unsupported action BUY_USD; Line 585: unsupported action SELL_USD; Line 790: unsupported action BUY_USD; Line 803: unsupported action BUY_USD; cash discrepancy None |  |
| S15 TRACK Tracker | 845 | 1 | 1 | UNRESOLVED | -30,492.98 MXN |
| ↳ cash/evidence |  |  |  | Line 7: unsupported action BUY_USD; Line 400: unsupported action BUY_USD; Line 585: unsupported action SELL_USD; Line 790: unsupported action BUY_USD; Line 803: unsupported action BUY_USD; cash discrepancy None |  |
| S16 HMM Intraday Router | 396 | 0 | 0 | MISMATCH | -4,155.86 MXN |
| ↳ cash/evidence |  |  |  | Line 65: unsupported action BUY_SOXL; Line 76: unsupported action SELL_SOXL; Line 78: unsupported action BUY_URTY; Line 88: unsupported action SELL_URTY; Line 112: unsupported action BUY_URTY; cash discrepancy 18452.37 |  |
| S17 FIBRAs Dynamic | 263 | 2 | 2 | MISMATCH | 54,455.88 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -101553.43 |  |
| S18 Efficient Frontier | 0 | 0 | 0 | UNRESOLVED | 0.00 USD |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: unsupported action REBALANCE; Line 7: unsupported action REBALANCE; Line 8: unsupported action REBALANCE; Line 9: unsupported action REBALANCE; cash discrepancy 0.0 |  |
| S19 Particle Filter QQQ | 54 | 0 | 0 | MISMATCH | -64,386.95 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S20 Hurst Exponent Dynamic | 95 | 0 | 0 | MISMATCH | -22,330.60 MXN |
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
| S25 Golden MACD BMV | 352 | 0 | 0 | MISMATCH | 588.77 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S27 Golden Hurst | 337 | 0 | 0 | MISMATCH | 4,006.64 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S29 Golden Stat-Arb | 340 | 0 | 0 | MISMATCH | 5,347.36 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200588.67 |  |
| S30 Golden MACD US | 356 | 0 | 0 | MISMATCH | -1,186.74 USD |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 100000.0 |  |
| S31 Fibonacci S&R | 55 | 1 | 1 | UNRESOLVED | 0.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: missing cash amount; Line 7: missing cash amount; Line 8: missing cash amount; Line 9: missing cash amount; cash discrepancy 0.0 |  |
