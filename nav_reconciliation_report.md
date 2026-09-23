# Ledger-first NAV Reconciliation

Audit-only: no portfolio JSON was changed. `Cash delta` is the sum recorded by each ledger; position differences must be resolved before using a ledger as authoritative.

| Strategy | Ledger rows | Ledger positions | Portfolio positions | Position status | Cash delta |
| :--- | ---: | ---: | ---: | :--- | ---: |
| S1 Adaptive Value | 287 | 2 | 5 | MISMATCH | 93,331.99 MXN |
| ↳ difference |  |  |  | AC.MX: ledger 19, portfolio 0, ASURB.MX: ledger 7, portfolio 0, BBAJIOO.MX: ledger 0, portfolio 634.686, BIMBOA.MX: ledger 0, portfolio 372.276, CUERVO.MX: ledger 0, portfolio 1650.22, GRUMAB.MX: ledger 0, portfolio 1, ORBIA.MX: ledger 0, portfolio 1538.87 |  |
| ↳ cash/evidence |  |  |  | Line 2: data before header; cash discrepancy -113331.99 |  |
| S2 1d MACD Systematic | 419 | 5 | 9 | MISMATCH | 42,728.31 MXN |
| ↳ difference |  |  |  | AMZN: ledger 0, portfolio 2, GOOGL: ledger 0, portfolio 2, META: ledger 0, portfolio 1, NVDA: ledger 0, portfolio 3 |  |
| ↳ cash/evidence |  |  |  | Line 251: column count does not match header; Line 252: column count does not match header; Line 271: column count does not match header; Line 300: column count does not match header; Line 384: column count does not match header; cash discrepancy -42623.33 |  |
| S3 US Stock Momentum | 26 | 9 | 5 | MISMATCH | -63,620.29 USD |
| ↳ difference |  |  |  | AAPL: ledger 83, portfolio 52, AMD: ledger 0, portfolio 31, AMZN: ledger -149, portfolio 0, AVGO: ledger -45, portfolio 0, COST: ledger -23, portfolio 0, GOOGL: ledger -35, portfolio 53, JPM: ledger -115, portfolio 0, MSFT: ledger -87, portfolio 0, NVDA: ledger 0, portfolio 94, TSLA: ledger -105, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: column count does not match header; Line 7: column count does not match header; Line 8: column count does not match header; Line 9: column count does not match header; cash discrepancy -155693.3 |  |
| S4 US DCF Value-Growth | 6 | 1 | 0 | MISMATCH | -25,461.24 USD |
| ↳ difference |  |  |  | AVGO: ledger 65, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 7: funding sign contradicts action; Line 8: funding sign contradicts action; Line 11: funding sign contradicts action; cash discrepancy 31459.96 |  |
| S5 Alternative Assets | 12 | 3 | 5 | MISMATCH | -330,738.91 USD |
| ↳ difference |  |  |  | DBA: ledger 0, portfolio 733, USO: ledger 0, portfolio 164 |  |
| ↳ cash/evidence |  |  |  | Line 7: funding sign contradicts action; Line 8: column count does not match header; Line 10: column count does not match header; Line 11: column count does not match header; Line 12: column count does not match header; cash discrepancy 794951.24 |  |
| S6 High-Beta Momentum | 7 | 0 | 0 | MISMATCH | -3,474.07 USD |
| ↳ cash/evidence |  |  |  | Line 5: funding sign contradicts action; Line 9: funding sign contradicts action; Line 11: funding sign contradicts action; cash discrepancy 5306.77 |  |
| S8 Dividend Quality | 368 | 4 | 4 | VERIFIED | -154,921.15 MXN |
| S9 AI Regime Stat-Arb | 415 | 1 | 1 | MISMATCH | -189,951.17 MXN |
| ↳ cash/evidence |  |  |  | Line 232: funding sign contradicts action; Line 351: funding sign contradicts action; cash discrepancy 10083.98 |  |
| S10 Intraday VWAP | 195 | 0 | 0 | MISMATCH | -892.13 MXN |
| ↳ cash/evidence |  |  |  | Line 57: unsupported action BUY_TQQQ; Line 60: unsupported action SETTLE_LONG_VWAP; Line 111: funding sign contradicts action; Line 116: unsupported action BUY_TQQQ; Line 121: unsupported action SETTLE_LONG_VWAP; cash discrepancy 8177.86 |  |
| S11 Intraday CCI-ADX | 355 | 0 | 0 | MISMATCH | -944.10 MXN |
| ↳ cash/evidence |  |  |  | Line 30: unsupported action BUY_SQQQ; Line 32: unsupported action SETTLE_SHORT_CCI_ZERO; Line 53: unsupported action BUY_TQQQ; Line 55: unsupported action SETTLE_LONG_CCI_ZERO; Line 57: unsupported action BUY_TQQQ; cash discrepancy 11504.01 |  |
| S12 VTTL Trend+Vol | 349 | 1 | 1 | MISMATCH | -70,753.03 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -0.08 |  |
| S13 CARA Cross-Asset | 354 | 1 | 1 | UNRESOLVED | -73,084.15 MXN |
| ↳ cash/evidence |  |  |  | Currency-specific balances require an FX ledger reconciliation; cash discrepancy None |  |
| S14 HEDGE Aggregator | 689 | 1 | 1 | UNRESOLVED | -58,401.68 MXN |
| ↳ cash/evidence |  |  |  | Line 7: unsupported action BUY_USD; Line 400: unsupported action BUY_USD; Line 585: unsupported action SELL_USD; Currency-specific balances require an FX ledger reconciliation; cash discrepancy None |  |
| S15 TRACK Tracker | 689 | 1 | 1 | UNRESOLVED | -58,420.34 MXN |
| ↳ cash/evidence |  |  |  | Line 7: unsupported action BUY_USD; Line 400: unsupported action BUY_USD; Line 585: unsupported action SELL_USD; Currency-specific balances require an FX ledger reconciliation; cash discrepancy None |  |
| S16 HMM Intraday Router | 319 | 0 | 0 | MISMATCH | -1,559.16 MXN |
| ↳ cash/evidence |  |  |  | Line 65: unsupported action BUY_SOXL; Line 76: unsupported action SELL_SOXL; Line 78: unsupported action BUY_URTY; Line 88: unsupported action SELL_URTY; Line 112: unsupported action BUY_URTY; cash discrepancy 8308.38 |  |
| S17 FIBRAs Dynamic | 186 | 2 | 2 | MISMATCH | 52,079.82 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -101553.43 |  |
| S18 Efficient Frontier | 0 | 0 | 0 | UNRESOLVED | 0.00 USD |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: unsupported action REBALANCE; Line 7: unsupported action REBALANCE; Line 8: unsupported action REBALANCE; Line 9: unsupported action REBALANCE; cash discrepancy 0.0 |  |
| S19 Particle Filter QQQ | 30 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S20 Hurst Exponent Dynamic | 20 | 0 | 0 | MISMATCH | -23,602.10 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S21 Shannon Entropy Dynamic | 49 | 1 | 0 | MISMATCH | -20,665.55 MXN |
| ↳ difference |  |  |  | TQQQ: ledger 59.4709, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S22 Walk-Forward ML | 132 | 0 | 0 | MISMATCH | 7,869.73 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S23 Calculus S&R | 146 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S24 30m Random Forest | 72 | 1 | 1 | MISMATCH | -200,000.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S25 Golden MACD BMV | 275 | 0 | 0 | MISMATCH | -1,640.72 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S27 Golden Hurst | 262 | 0 | 0 | MISMATCH | 2,546.70 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S29 Golden Stat-Arb | 261 | 0 | 0 | MISMATCH | 2,546.68 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 200000.0 |  |
| S30 Golden MACD US | 272 | 1 | 1 | MISMATCH | -18,607.91 USD |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; cash discrepancy 100000.0 |  |
| S31 Fibonacci S&R | 40 | 0 | 0 | MISMATCH | 0.00 MXN |
| ↳ cash/evidence |  |  |  | Line 5: column count does not match header; Line 6: missing cash amount; Line 7: missing cash amount; Line 8: missing cash amount; Line 9: missing cash amount; cash discrepancy 209970.88 |  |
