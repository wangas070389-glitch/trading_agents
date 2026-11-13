# Transaction Ledger — Strategy 1: Adaptive Value (BMV) — RESTART v2

> **RESTART 2026-11-13 (Rescue 2026-11-12).** The prior ledger
> (`_archive/transactions.md`) and portfolio (`_archive/portfolio.json`) are
> **uncertifiable**: the ledger holds AC.MX 19 / ASURB.MX 7 while the portfolio
> holds GRUMAB.MX / ORBIA.MX / WALMEX.MX, cash disagrees by −66,683.45 MXN, and
> the funding history is contradictory (portfolio seed 20,000 MXN vs a 100,000
> MXN manual injection in the old ledger). Per ACCOUNTING_REVIEW_FOLLOWUP.md
> the prior history cannot be certified, so this ledger starts from zero.
> This is a **dormant clean start**: S1 is NOT in the strategy registry or the
> daily pipeline after the rescue. No positions, no carried-forward balance.
> The single DEPOSIT below is the restart's starting capital (the portfolio's
> declared initial seed, 20,000 MXN). No actual funds moved on 2026-11-13 —
> this is a paper restart; fund it before reactivating.

## Chronological Transaction Log

| Trade Date | Ticker | Action | Shares | Execution Price (MXN) | Total Cash Flow (MXN) | Order Type | Status | Note |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| 2026-11-13 | CASH | DEPOSIT | 1 | 20000.00 | +20000.00 | Manual | FILLED | Restart 2026-11-13: initial capital funding (clean start; prior history uncertifiable, see note above) |
