# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-09-04 21:53:20 | Inception: 2026-07-14 (52 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $275,263.01 USD |
| Return since inception | -- | +175.26% |
| Ann. return | +14.67% | +1230.21% |
| Ann. volatility | 6.66% | 99.58% |
| Sharpe (Rf 6.53%) | +1.22 | +6.54 |
| Max drawdown | -4.10% | -5.29% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 5.4% | -3.36% | 2026-09-04 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 4.9% | -1.99% | 2026-09-04 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 4.5% | +1.77% | 2026-09-04 | multi-strategy USD |
| S5 Alternatives | 25.0% | 24.8% | +698.13% | 2026-09-04 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 13.4% | -0.42% | 2026-09-04 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 11.9% | +5.96% | 2026-09-04 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 8.6% | -4.89% | 2026-09-04 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 5.4% | +3.31% | 2026-09-04 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 6.1% | +79.36% | 2026-09-04 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 7.4% | +104.78% | 2026-09-04 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 7.6% | +104.76% | 2026-09-04 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +3.15% | 2026-09-04 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -15.92% | 2026-09-04 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | -1.49% | 2026-09-04 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | -1.75% | 2026-09-04 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | +7.28% | 2026-09-04 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | +6.32% | 2026-09-04 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -14.64% | 2026-09-04 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | +2.12% | 2026-09-04 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +4.22% | 2026-09-04 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +4.22% | 2026-09-04 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | +0.78% | 2026-09-04 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1245057.28% | 2026-09-04 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
Largest divergences from the backtest correlation matrix (the frontier's key input):

| Pair | Backtest | Realized | Divergence |
| :--- | ---: | ---: | ---: |
| S27-S29 | 0.00 | 1.00 | 1.00 |
| S20-S21 | 0.00 | 1.00 | 1.00 |
| S20-S22 | 0.00 | 0.89 | 0.89 |
| S21-S22 | 0.00 | 0.88 | 0.88 |
| S25-S29 | 0.00 | 0.84 | 0.84 |
| S25-S27 | 0.00 | 0.84 | 0.84 |
| S12-S14 | 0.93 | 0.13 | 0.80 |
| S12-S15 | 0.93 | 0.13 | 0.80 |
| S12-S29 | 0.00 | 0.74 | 0.74 |
| S12-S27 | 0.00 | 0.74 | 0.74 |

## 4. Rebalances
| Date | NAV | Max weight drift |
| :--- | ---: | ---: |
| 2026-08-01 | $202,870.65 | 38.4pp |
| 2026-09-01 | $273,466.52 | 4.0pp |

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (16.8990), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
