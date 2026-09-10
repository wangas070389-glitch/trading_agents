# S32 frozen challenger evaluation

Retrospective holdout; research simulation, not demonstrated live alpha. All results in MXN, distributions included; taxes excluded.

30 bps one-way trading/FX costs; no interest on MXN cash. Annualization uses 252 observations. Observations with missing inputs are dropped, never forward-filled.

**Predeclared screen: FAIL — do not promote**

| Model / period | CAGR | Sharpe (0% cash) | Max drawdown | Annual traded/NAV | Fees MXN |
|---|---:|---:|---:|---:|---:|
| trend_reference | 6.65% | 0.85 | -11.23% | 1.80 | 26,157.23 |
| trend_holdout | 5.48% | 0.56 | -22.26% | 2.30 | 23,099.04 |
| trend_early_holdout | 3.23% | 0.37 | -11.78% | 2.23 | 11,413.43 |
| trend_late_holdout | 7.79% | 0.72 | -13.46% | 2.37 | 11,685.61 |
| equal_reference | 11.67% | 1.02 | -14.47% | 0.28 | 4,311.44 |
| equal_holdout | 10.07% | 0.65 | -25.78% | 0.14 | 2,944.84 |
| equal_early_holdout | 4.45% | 0.32 | -24.52% | 0.17 | 1,802.74 |
| equal_late_holdout | 16.04% | 1.10 | -11.23% | 0.10 | 1,142.09 |
| spy_reference | 13.69% | 0.88 | -36.52% | 0.07 | 598.21 |
| spy_holdout | 14.07% | 0.67 | -28.92% | 0.00 | 0.00 |
| spy_early_holdout | 8.63% | 0.43 | -28.27% | 0.00 | 0.00 |
| spy_late_holdout | 19.82% | 1.05 | -20.17% | 0.00 | 0.00 |
| cash_reference | 0.00% | 0.00 | 0.00% | 0.00 | 0.00 |
| cash_holdout | 0.00% | 0.00 | 0.00% | 0.00 | 0.00 |
| cash_early_holdout | 0.00% | 0.00 | 0.00% | 0.00 | 0.00 |
| cash_late_holdout | 0.00% | 0.00 | 0.00% | 0.00 | 0.00 |
| trend_double_cost_holdout | 4.75% | 0.49 | -24.57% | 2.30 | 41,974.83 |

Fixed 6.53% cash sensitivity: CAGR 6.53%, drawdown 0% by construction; this is not historical Bondia and is not used to invent historical income.

S8/S11/S12 comparisons remain unavailable because their reconstructed, equivalent histories are missing. This experiment cannot establish superiority over them.
