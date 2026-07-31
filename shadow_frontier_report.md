# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-07-31 20:50:38 | Inception: 2026-07-14 (17 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $202,953.47 USD |
| Return since inception | -- | +102.95% |
| Ann. return | +14.67% | -- (<30d) |
| Ann. volatility | 6.66% | 144.03% |
| Sharpe (Rf 6.53%) | +1.22 | +7.99 |
| Max drawdown | -4.10% | -1.22% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 2.7% | +1.66% | 2026-07-31 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 2.4% | -0.42% | 2026-07-31 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 2.2% | -0.26% | 2026-07-31 | multi-strategy USD |
| S5 Alternatives | 25.0% | 63.4% | +415.05% | 2026-07-31 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 6.6% | -0.79% | 2026-07-31 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 6.0% | +3.36% | 2026-07-31 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 4.0% | -4.99% | 2026-07-31 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 2.5% | -3.13% | 2026-07-31 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 2.8% | -3.97% | 2026-07-31 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 3.6% | -2.16% | 2026-07-31 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 3.7% | -2.16% | 2026-07-31 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +3.42% | 2026-07-31 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -14.53% | 2026-07-31 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | -12.52% | 2026-07-31 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | -12.54% | 2026-07-31 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | -12.54% | 2026-07-31 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | -4.62% | 2026-07-31 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -15.32% | 2026-07-31 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | -0.34% | 2026-07-31 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +0.86% | 2026-07-31 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +0.86% | 2026-07-31 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | +0.20% | 2026-07-31 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1009007.92% | 2026-07-31 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
Largest divergences from the backtest correlation matrix (the frontier's key input):

| Pair | Backtest | Realized | Divergence |
| :--- | ---: | ---: | ---: |
| S27-S29 | 0.00 | 1.00 | 1.00 |
| S20-S21 | 0.00 | 1.00 | 1.00 |
| S14-S29 | 0.00 | 0.97 | 0.97 |
| S14-S27 | 0.00 | 0.97 | 0.97 |
| S15-S29 | 0.00 | 0.97 | 0.97 |
| S15-S27 | 0.00 | 0.97 | 0.97 |
| S12-S29 | 0.00 | 0.97 | 0.97 |
| S12-S27 | 0.00 | 0.97 | 0.97 |
| S1-S29 | 0.00 | 0.96 | 0.96 |
| S1-S27 | 0.00 | 0.96 | 0.96 |

## 4. Rebalances
*None yet (monthly, first mark of each month).*

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.3120), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
