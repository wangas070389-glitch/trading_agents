# Transaction Ledger (Isolated US Stock Momentum) — RESTART v2

> **RESTART 2026-11-13 (Rescue 2026-11-12).** The prior ledger
> (`_archive/transactions_us_stocks.md`) and portfolio
> (`_archive/portfolio_us_stocks.json`) are **uncertifiable**: negative
> positions (AMZN −149, JPM −115, TSLA −105), de-leverage sells queued
> 2026-07-11 never filled/recorded, cash disagrees by −59,837.33 USD, and the
> AVGO claim is split unresolved with S4 (shared Alpaca account). Per
> ACCOUNTING_REVIEW_FOLLOWUP.md the prior history cannot be certified, so this
> ledger starts from zero.
>
> **Alpaca paper account state:** no local Alpaca account statement exists in
> this repo; the only local record is the old portfolio JSON, which shows
> **cash −193,211.20 USD (negative)** and NAV 59,846.31 USD with 4 holdings.
> That negative cash is **NOT carried forward** — this ledger starts at zero
> cash with no positions. Before reactivating S3, reconcile the live Alpaca
> paper account (positions and cash) against a broker statement; do not assume
> the old −193,211.20 USD cash or the old holdings.
>
> This is a **dormant clean start**: S3 is NOT in the strategy registry or the
> daily pipeline after the rescue. The single DEPOSIT below is the restart's
> starting capital (199,203.11 USD, the original funded amount). No actual
> funds moved on 2026-11-13 — this is a paper restart; fund it and reconcile
> the Alpaca account before reactivating.

| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| 2026-11-13 | CASH | DEPOSIT | 1.00 | $199,203.11 | +$199,203.11 | Market | FILLED | Restart 2026-11-13: initial capital funding (clean start; prior history uncertifiable, see note above) |
