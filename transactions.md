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
| 2026-06-06 | BONDIA | INTEREST | 1 | 0.0066 | +0.0066 | Market | FILLED | Bondia overnight yield on cash reserves for 0.0011 days. |
| 2026-06-06 | NVDA | BUY | 2 | 3543.66 | -7,087.31 | Market | FILLED | V3 Dynamic Rebalance (Target Weight: 40.0%, DCS: 0.96) |
| 2026-06-06 | AAPL | BUY | 1 | 5310.13 | -5,310.13 | Market | FILLED | V3 Dynamic Rebalance (Target Weight: 40.0%, DCS: 0.95) |
| 2026-06-08 | BONDIA | INTEREST | 1 | 6.1904 | +6.1904 | Market | FILLED | Bondia overnight yield on cash reserves for 2.7421 days. |
| 2026-06-08 | NVDA | SELL | 2 | 3649.11 | +7,298.23 | Market | FILLED | V3 Dynamic Rebalance |
| 2026-06-08 | AAPL | SELL | 1 | 5322.59 | +5,322.59 | Market | FILLED | V3 Dynamic Rebalance |
---

## Portfolio Capital Reconciliation

* **Initial Starting Capital (2026-06-03)**: 20,000.00 MXN
* **Total Deployed Capital**: 0.00 MXN (0.0% invested)
* **Unallocated Cash Reserves**: 19,978.71 MXN (100.0% cash)
* **Current Portfolio Market Value**: 19,978.71 MXN (including cash)
