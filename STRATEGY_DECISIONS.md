# Strategy decision framework — 2026-09-09

## Decision now

Keep every strategy in paper trading. Do not tune or shut down a strategy merely because a few weeks of NAV are negative: the graduation rule requires 90 live-paper days, and most histories are only 13–55 days.

| Tier | Strategies | Decision |
| :--- | :--- | :--- |
| Core candidates | S12 VTTL, S14 HEDGE, S15 TRACK, S30 Golden MACD US, S8 Dividend Quality, S4 US DCF | Primary validation set. S8 and S4 are the only candidates past 30 days with positive live return and Sharpe. |
| Promising, insufficient evidence | S29, S25, S27, S23, S19, S20, S22 | Continue unchanged until 90 days; no allocation increase. S29's 5.04 backtest Sharpe warrants scrutiny, not confidence. |
| Experimental | S9, S10, S11, S16, S24 | Paper-only. Their intraday backtests have about 60 days of in-sample history. |
| Watch / freeze changes | S6, S17, S31 | No new tuning or capital increase. S6 fails its live hurdle/Sharpe; validate S17/S31 ledgers and data before judging performance. |
| Blocked | S3 | Disabled until broker and ledger reconciliation completes. |

## Evidence-based leaders

The latest KPI report identifies S12 (22.5 years), S14/S15 (19.2 years), and S30 (16 years) as the strongest long-window research candidates. S8 and S4 have the strongest current paper evidence. High CAGRs from S29, S10, or S24 are not sufficient for allocation without independent out-of-sample validation.

## Next gates

1. Let core candidates reach 90 live-paper days without parameter changes.
2. Reconcile every paper ledger to the broker before real-money use; independent paper notional is never deployable capital.
3. Graduate at most one strategy at a time, initially with 10% of its intended allocation, only after every graduation criterion passes.
4. Retire or redesign only after a documented kill criterion fires or a completed 90-day evaluation.
