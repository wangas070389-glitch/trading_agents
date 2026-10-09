# Ledger-first NAV Reconciliation

Audit-only: no portfolio JSON was changed. `Cash delta` is the sum recorded by each ledger; position differences must be resolved before using a ledger as authoritative.

| Strategy | Ledger rows | Ledger positions | Portfolio positions | Position status | Cash delta |
| :--- | ---: | ---: | ---: | :--- | ---: |
| S1 Adaptive Value | 287 | 2 | 5 | MISMATCH | 93,331.99 MXN |
| ↳ difference |  |  |  | AC.MX: ledger 19, portfolio 0, ASURB.MX: ledger 7, portfolio 0, BBAJIOO.MX: ledger 0, portfolio 634.686, BIMBOA.MX: ledger 0, portfolio 372.276, CUERVO.MX: ledger 0, portfolio 1650.22, GRUMAB.MX: ledger 0, portfolio 1, ORBIA.MX: ledger 0, portfolio 1538.87 |  |
| ↳ cash/evidence |  |  |  | Line 2: data before header; cash discrepancy -113331.99 |  |
| S2 1d MACD Systematic | 452 | 7 | 9 | MISMATCH | 17,555.71 MXN |
| ↳ difference |  |  |  | AMZN: ledger 0, portfolio 2, GOOGL: ledger 0, portfolio 2 |  |
| ↳ cash/evidence |  |  |  | Line 251: column count does not match header; Line 252: column count does not match header; Line 271: column count does not match header; Line 300: column count does not match header; Line 384: column count does not match header; cash discrepancy -16740.31 |  |
| S3 US Stock Momentum | 26 | 9 | 5 | MISMATCH | -63,620.29 USD |
| ↳ difference |  |  |  | AAPL: ledger 83, portfolio 0, AMD: ledger 0, portfolio 31, AMZN: ledger -149, portfolio 62, AVGO: ledger -45, portfolio 0, COST: ledger -23, portfolio 0, GOOGL: ledger -35, portfolio 0, JPM: ledger -115, portfolio 0, MSFT: ledger -87, portfolio 31, NVDA: ledger 0, portfolio 94, TSLA: ledger -105, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: column count does not match header; Line 7: column count does not match header; Line 8: column count does not match header; Line 9: column count does not match header; cash discrepancy -161154.67 |  |
| S4 US DCF Value-Growth | 7 | 1 | 0 | MISMATCH | -26,461.24 USD |
| ↳ difference |  |  |  | AVGO: ledger 65, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 7: funding sign contradicts action; Line 8: funding sign contradicts action; Line 11: funding sign contradicts action; Line 12: funding sign contradicts action; cash discrepancy 33459.96 |  |
| S5 Alternative Assets | 13 | 3 | 5 | MISMATCH | -331,738.91 USD |
| ↳ difference |  |  |  | DBA: ledger 0, portfolio 733, USO: ledger 0, portfolio 164 |  |
| ↳ cash/evidence |  |  |  | Line 7: funding sign contradicts action; Line 8: column count does not match header; Line 10: column count does not match header; Line 11: column count does not match header; Line 12: column count does not match header; cash discrepancy 796951.24 |  |
| S6 High-Beta Momentum | 8 | 0 | 0 | MISMATCH | -4,474.07 USD |
| ↳ cash/evidence |  |  |  | Line 5: funding sign contradicts action; Line 9: funding sign contradicts action; Line 11: funding sign contradicts action; Line 12: funding sign contradicts action; cash discrepancy 7383.33 |  |
| S8 Dividend Quality | 399 | 4 | 4 | VERIFIED | -152,786.41 MXN |
| S9 AI Regime Stat-Arb | 457 | 0 | 0 | MISMATCH | -29,554.20 MXN |
| ↳ cash/evidence |  |  |  | Line 232: funding sign contradicts action; Line 351: funding sign contradicts action; Line 444: funding sign contradicts action; cash discrepancy 14083.98 |  |
| S10 Intraday VWAP | 209 | 0 | 0 | MISMATCH | -2,294.00 MXN |
| ↳ cash/evidence |  |  |  | Line 57: unsupported action BUY_TQQQ; Line 60: unsupported action SETTLE_LONG_VWAP; Line 111: funding sign contradicts action; Line 116: unsupported action BUY_TQQQ; Line 121: unsupported action SETTLE_LONG_VWAP; cash discrepancy 12177.86 |  |
| S11 Intraday CCI-ADX | 386 | 0 | 0 | MISMATCH | -2,335.59 MXN |
| ↳ cash/evidence |  |  |  | Line 30: unsupported action BUY_SQQQ; Line 32: unsupported action SETTLE_SHORT_CCI_ZERO; Line 53: unsupported action BUY_TQQQ; Line 55: unsupported action SETTLE_LONG_CCI_ZERO; Line 57: unsupported action BUY_TQQQ; cash discrepancy 15504.01 |  |
| S12 VTTL Trend+Vol | 380 | 1 | 1 | MISMATCH | -68,378.59 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -0.09 |  |
| S13 CARA Cross-Asset | 385 | 1 | 1 | UNRESOLVED | -70,716.41 MXN |
| ↳ cash/evidence |  |  |  | Currency-specific balances require an FX ledger reconciliation; cash discrepancy None |  |
| S14 HEDGE Aggregator | 751 | 1 | 1 | UNRESOLVED | -46,009.96 MXN |
| ↳ cash/evidence |  |  |  | Line 7: unsupported action BUY_USD; Line 400: unsupported action BUY_USD; Line 585: unsupported action SELL_USD; Currency-specific balances require an FX ledger reconciliation; cash discrepancy None |  |
| S15 TRACK Tracker | 751 | 1 | 1 | UNRESOLVED | -46,041.15 MXN |
| ↳ cash/evidence |  |  |  | Line 7: unsupported action BUY_USD; Line 400: unsupported action BUY_USD; Line 585: unsupported action SELL_USD; Currency-specific balances require an FX ledger reconciliation; cash discrepancy None |  |
| S16 HMM Intraday Router | 350 | 0 | 0 | MISMATCH | -2,961.83 MXN |
| ↳ cash/evidence |  |  |  | Line 65: unsupported action BUY_SOXL; Line 76: unsupported action SELL_SOXL; Line 78: unsupported action BUY_URTY; Line 88: unsupported action SELL_URTY; Line 112: unsupported action BUY_URTY; cash discrepancy 12308.38 |  |
| S17 FIBRAs Dynamic | 217 | 2 | 2 | MISMATCH | 53,228.79 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -101553.43 |  |
| S18 Efficient Frontier | 0 | 0 | 0 | UNRESOLVED | 0.00 USD |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: unsupported action REBALANCE; Line 7: unsupported action REBALANCE; Line 8: unsupported action REBALANCE; Line 9: unsupported action REBALANCE; cash discrepancy 0.0 |  |
| S19 Particle Filter QQQ | 30 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S20 Hurst Exponent Dynamic | 50 | 0 | 0 | MISMATCH | -23,094.95 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S21 Shannon Entropy Dynamic | 79 | 1 | 0 | MISMATCH | -20,150.00 MXN |
| ↳ difference |  |  |  | TQQQ: ledger 59.4709, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S22 Walk-Forward ML | 162 | 0 | 0 | MISMATCH | 8,467.34 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S23 Calculus S&R | 146 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S24 30m Random Forest | 78 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S25 Golden MACD BMV | 306 | 1 | 1 | MISMATCH | -36,962.91 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S27 Golden Hurst | 292 | 0 | 0 | MISMATCH | 3,128.99 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S29 Golden Stat-Arb | 295 | 0 | 0 | MISMATCH | 4,461.44 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200588.67 |  |
| S30 Golden MACD US | 303 | 2 | 2 | MISMATCH | -36,447.10 USD |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 100000.0 |  |
| S31 Fibonacci S&R | 40 | 0 | 0 | MISMATCH | 0.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: missing cash amount; Line 7: missing cash amount; Line 8: missing cash amount; Line 9: missing cash amount; cash discrepancy 209970.88 |  |
