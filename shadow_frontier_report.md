# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-08-12 17:02:33 | Inception: 2026-07-14 (29 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $252,823.45 USD |
| Return since inception | -- | +152.82% |
| Ann. return | +14.67% | -- (<30d) |
| Ann. volatility | 6.66% | 117.24% |
| Sharpe (Rf 6.53%) | +1.22 | +7.43 |
| Max drawdown | -4.10% | -5.29% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 4.3% | +0.82% | 2026-08-12 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 3.9% | -1.40% | 2026-08-11 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 3.7% | +1.77% | 2026-08-12 | multi-strategy USD |
| S5 Alternatives | 25.0% | 22.3% | +472.26% | 2026-08-12 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 11.0% | +0.96% | 2026-08-12 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 9.5% | +3.40% | 2026-08-12 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 7.0% | -3.72% | 2026-08-12 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 4.5% | +2.91% | 2026-08-12 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 8.9% | +78.09% | 2026-08-12 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 12.3% | +103.05% | 2026-08-12 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 12.6% | +103.05% | 2026-08-12 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +0.59% | 2026-08-12 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -9.55% | 2026-08-12 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | +2.84% | 2026-08-12 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | +2.86% | 2026-08-12 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | +1.50% | 2026-08-12 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | +9.08% | 2026-08-12 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -22.03% | 2026-08-12 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | +1.38% | 2026-08-12 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +2.60% | 2026-08-12 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +2.60% | 2026-08-12 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | +1.30% | 2026-08-12 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1024192.76% | 2026-08-12 | multi-strategy USD |

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
| S12-S29 | 0.00 | 0.86 | 0.86 |
| S12-S27 | 0.00 | 0.86 | 0.86 |
| S12-S25 | 0.00 | 0.85 | 0.85 |
| S12-S14 | 0.93 | 0.13 | 0.80 |

## 4. Rebalances
| Date | NAV | Max weight drift |
| :--- | ---: | ---: |
| 2026-08-01 | $202,870.65 | 38.4pp |

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.0589), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
