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
| 2026-06-11 | BBAJIOO.MX | BUY | 149 | 52.74 | -7,858.26 | Market | FILLED | V3 Dynamic Rebalance (Target Weight: 40.0%, DCS: 1.00) |
| 2026-06-11 | AAPL | SELL | 1 | 5150.20 | +5,150.20 | Market | FILLED | V3 Dynamic Rebalance |
| 2026-06-11 | GRUMAB.MX | BUY | 26 | 293.50 | -7,631.00 | Market | FILLED | V3 Dynamic Rebalance (Target Weight: 40.0%, DCS: 0.99) |
| 2026-06-11 | NVDA | SELL | 2 | 3569.06 | +7,138.12 | Market | FILLED | V3 Dynamic Rebalance |
| 2026-06-11 | BONDIA | INTEREST | 1 | 0.0215 | +0.0215 | Market | FILLED | Bondia overnight yield on cash reserves for 0.0171 days. |
| 2026-06-11 | BONDIA | INTEREST | 1 | 0.0034 | +0.0034 | Market | FILLED | Bondia overnight yield on cash reserves for 0.0027 days. |
---

## Portfolio Capital Reconciliation

* **Initial Starting Capital (2026-06-03)**: 20,000.00 MXN
* **Total Deployed Capital**: 15,489.26 MXN (79.0% invested)
* **Unallocated Cash Reserves**: 4,106.83 MXN (21.0% cash)
* **Current Portfolio Market Value**: 19,596.09 MXN (including cash)
