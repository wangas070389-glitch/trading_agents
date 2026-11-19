# Ledger-first NAV Reconciliation

Audit-only: no portfolio JSON was changed. `Cash delta` is the sum recorded by each ledger; position differences must be resolved before using a ledger as authoritative.

| Strategy | Ledger rows | Ledger positions | Portfolio positions | Position status | Cash delta |
| :--- | ---: | ---: | ---: | :--- | ---: |
| S2 1d MACD Systematic | 534 | 7 | 7 | VERIFIED | 26,609.23 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -0.02 |  |
| ↳ notes |  |  |  | Line 300: FILLED row carries an 'execution failed' note (META BUY); counted as executed; Line 438: FILLED row carries an 'execution failed' note (META SELL); counted as executed |  |
| S4 US DCF Value-Growth | 8 | 1 | 0 | MISMATCH | -17,461.24 USD |
| ↳ difference |  |  |  | AVGO: ledger 65, portfolio 0 |  |
| ↳ cash/evidence |  |  |  | ; cash discrepancy 25459.96 |  |
| S8 Dividend Quality | 473 | 4 | 4 | VERIFIED | -154,895.29 MXN |
| S12 VTTL Trend+Vol | 452 | 1 | 0 | VERIFIED | -2,766.00 MXN |
| ↳ cash/evidence |  |  |  | ; cash discrepancy -0.13 |  |
| S14 HEDGE Aggregator | 902 | 1 | 1 | VERIFIED | -87,429.96 MXN |
| ↳ notes |  |  |  | Currency-specific balances: cash is split MXN/USD and is not single-currency verified |  |
| S15 TRACK Tracker | 902 | 1 | 1 | VERIFIED | -87,434.79 MXN |
| ↳ notes |  |  |  | Currency-specific balances: cash is split MXN/USD and is not single-currency verified |  |
