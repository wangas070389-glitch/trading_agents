# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-07-13 18:57:13 | Inception: 2026-07-11 (2 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $100,046.01 USD |
| Return since inception | -- | +0.05% |
| Ann. return | +14.67% | -- (<30d) |
| Ann. volatility | 6.66% | -- (<10 marks) |
| Sharpe (Rf 6.53%) | +1.22 | -- |
| Max drawdown | -4.10% | -- |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 5.5% | +1.83% | 2026-07-13 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 4.9% | -0.15% | 2026-07-13 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 4.5% | +0.00% | 2026-07-13 | multi-strategy USD |
| S5 Alternatives | 25.0% | 25.0% | -0.04% | 2026-07-13 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 13.5% | +0.01% | 2026-07-13 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 11.8% | +0.47% | 2026-07-13 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 8.6% | -0.51% | 2026-07-13 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 5.3% | -0.20% | 2026-07-13 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 6.0% | -0.19% | 2026-07-13 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 7.4% | -0.17% | 2026-07-13 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 7.6% | -0.17% | 2026-07-13 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
*Needs >= 15 daily return observations; have 3.*

## 4. Rebalances
*None yet (monthly, first mark of each month).*

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.5140), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
