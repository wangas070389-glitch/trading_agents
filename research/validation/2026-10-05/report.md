# Reproducible strategy validation

Committed accounting evidence: `fd7461011259e175777f7c21695e5abfc696f829`.
Current implementation fingerprints and runtime versions are in results.json.

**Deployment remains BLOCKED.** Code-test success is not investment-performance validation.

## Ledger reconciliation (offline, immutable source copies)

MISMATCH: 23, VERIFIED: 1, UNRESOLVED: 4.
See ledger_audit.md/json for per-symbol quantities, cash gaps and parsing errors.
No broker was contacted and no opening balances or corrections were invented.

## Corrected Golden MACD engines versus matched baskets

Adjusted closes; native currencies; no contributions or taxes; next-close fills.
Each stock has an independent equal-sized sleeve. This is NOT a full reproduction
of the paper runner's shared cash and 18% allocation limit. Universe selection is retrospective.
Base cash yields are fixed sensitivities, not historical rates. Benchmark entry pays the same cost.
Sharpe uses zero risk-free return and 252 observations/year; CAGR uses calendar years.

| Strategy/scenario | Currency | CAGR | Sharpe (0% Rf) | Max DD | Matched buy/hold CAGR | Buy/hold Sharpe | Buy/hold DD |
|---|---|---:|---:|---:|---:|---:|---:|
| S25 base | MXN | 1.71% | 0.27 | -14.93% | 10.88% | 0.67 | -28.24% |
| S25 zero_cash_carry | MXN | -3.31% | -0.44 | -45.77% | 10.88% | 0.67 | -28.24% |
| S25 double_cost | MXN | -1.76% | -0.21 | -33.57% | 10.86% | 0.67 | -28.24% |
| S30 base | USD | 10.51% | 1.02 | -24.22% | 35.22% | 1.16 | -48.14% |
| S30 zero_cash_carry | USD | 7.01% | 0.71 | -29.22% | 35.22% | 1.16 | -48.14% |
| S30 double_cost | USD | 10.34% | 1.00 | -24.43% | 35.22% | 1.16 | -48.14% |

## Remaining evidence gaps

- S1/S8: point-in-time fundamental inputs are unavailable; refreshing current fundamentals cannot validate history.
- S2: the scheduled HMM-filtered runner is not the legacy portfolio backtester. Canonical engine/live parity is not established.
- S24: the source provider's rolling 60-day window is not a preserved independent test set. No new profitability claim is made.
- S3: broker fills, statements and strategy ownership allocations are required; do not overwrite shared-account books from aggregate positions.
- S12 and one S14/S15 representative remain research priorities, not approved allocations.
- S32's frozen experiment remains rejected. Its existing snapshot is retained, not tuned to change that result.

Passing tests and rerunning curves do not clear backtest_review.py blocks or the 90-day verified paper-history requirement.
