# Transaction Log (Alternative Assets Strategy) — RESTART v2

> **RESTART 2026-11-13 (Rescue 2026-11-12).** The prior ledger
> (`_archive/transactions_alternatives.md`) and portfolio
> (`_archive/portfolio_alternatives.json`) are **uncertifiable**: cash
> disagrees by 1,466,254.95 USD (the portfolio shows cash 1,202,026.36 USD
> against NAV 105,171.66 USD — an accounting artifact, not a real balance),
> and DEPOSIT rows were recorded with negative amounts. Per
> ACCOUNTING_REVIEW_FOLLOWUP.md the prior history cannot be certified, so this
> ledger starts from zero.
>
> This is a **dormant clean start**: S5 is NOT in the strategy registry or the
> daily pipeline after the rescue. No positions, no carried-forward balance.
> The single DEPOSIT below is the restart's starting capital (99,321.45 USD,
> the portfolio's declared initial seed). No actual funds moved on 2026-11-13
> — this is a paper restart; fund it before reactivating.

| Date | Ticker | Action | Shares | Price | Fee | Net Amount | Note |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 2026-11-13 | CASH | DEPOSIT | 1.0000 | $99,321.45 | $0.00 | $99,321.45 | Restart 2026-11-13: initial capital funding (clean start; prior history uncertifiable, see note above) |
