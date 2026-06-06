# Agentic DAG Paper Trading Transaction Ledger

This file tracks all buy and sell transactions executed by the Mexican Value Stock Evaluation Agentic DAG.

## Chronological Transaction Log

| Trade Date | Ticker | Action | Shares | Execution Price (MXN) | Total Cash Flow (MXN) | Order Type | Status | Note |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 2026-06-03 | KIMBERA.MX | BUY | 62 | 38.09 | -2,361.58 | Market | FILLED | Initial value portfolio allocation (30% target) |
| 2026-06-03 | PINFRA.MX | BUY | 8 | 276.19 | -2,209.52 | Market | FILLED | Initial value portfolio allocation (30% target) |
| 2026-06-03 | CUERVO.MX | BUY | 108 | 14.07 | -1,519.56 | Market | FILLED | Initial value portfolio allocation (30% target) |

| 2026-06-06 | KIMBERA.MX | SELL | 62 | 36.92 | +2,289.04 | Market | FILLED | V3 Dynamic Rebalance |
| 2026-06-06 | PINFRA.MX | SELL | 8 | 266.06 | +2,128.48 | Market | FILLED | V3 Dynamic Rebalance |
| 2026-06-06 | CUERVO.MX | SELL | 108 | 14.00 | +1,512.00 | Market | FILLED | V3 Dynamic Rebalance |
| 2026-06-06 | BONDIA | INTEREST | 1 | 0.0227 | +0.0227 | Market | FILLED | Bondia overnight yield on cash reserves for 0.0037 days. |
---

## Portfolio Capital Reconciliation

* **Initial Starting Capital (2026-06-03)**: 20,000.00 MXN
* **Total Deployed Capital**: 0.00 MXN (0.0% invested)
* **Unallocated Cash Reserves**: 19,821.68 MXN (100.0% cash)
* **Current Portfolio Market Value**: 19,821.68 MXN (including cash)
