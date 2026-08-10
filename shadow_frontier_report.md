# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-08-10 16:00:30 | Inception: 2026-07-14 (27 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $232,620.51 USD |
| Return since inception | -- | +132.62% |
| Ann. return | +14.67% | -- (<30d) |
| Ann. volatility | 6.66% | 120.71% |
| Sharpe (Rf 6.53%) | +1.22 | +7.09 |
| Max drawdown | -4.10% | -5.29% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 4.7% | +1.93% | 2026-08-10 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 4.3% | -0.65% | 2026-08-10 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 4.0% | +1.77% | 2026-08-10 | multi-strategy USD |
| S5 Alternatives | 25.0% | 15.6% | +269.13% | 2026-08-10 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 12.0% | +1.22% | 2026-08-10 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 10.4% | +4.11% | 2026-08-10 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 7.6% | -3.94% | 2026-08-10 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 4.9% | +2.15% | 2026-08-10 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 9.6% | +76.98% | 2026-08-10 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 13.3% | +101.95% | 2026-08-10 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 13.7% | +101.96% | 2026-08-10 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +0.87% | 2026-08-10 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -10.01% | 2026-08-10 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | +1.34% | 2026-08-10 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | +1.31% | 2026-08-10 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | +1.00% | 2026-08-10 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | +8.17% | 2026-08-10 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -20.80% | 2026-08-10 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | +0.89% | 2026-08-10 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +2.10% | 2026-08-10 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +2.10% | 2026-08-10 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | +1.68% | 2026-08-10 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1019596.14% | 2026-08-10 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
Largest divergences from the backtest correlation matrix (the frontier's key input):

| Pair | Backtest | Realized | Divergence |
| :--- | ---: | ---: | ---: |
| S27-S29 | 0.00 | 1.00 | 1.00 |
| S20-S21 | 0.00 | 1.00 | 1.00 |
| S25-S29 | 0.00 | 0.94 | 0.94 |
| S25-S27 | 0.00 | 0.94 | 0.94 |
| S20-S22 | 0.00 | 0.92 | 0.92 |
| S21-S22 | 0.00 | 0.92 | 0.92 |
| S1-S29 | 0.00 | 0.87 | 0.87 |
| S1-S27 | 0.00 | 0.87 | 0.87 |
| S12-S29 | 0.00 | 0.86 | 0.86 |
| S12-S27 | 0.00 | 0.86 | 0.86 |

## 4. Rebalances
| Date | NAV | Max weight drift |
| :--- | ---: | ---: |
| 2026-08-01 | $202,870.65 | 38.4pp |

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.1276), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
