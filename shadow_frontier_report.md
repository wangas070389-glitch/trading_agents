# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-11-12 21:34:42 | Inception: 2026-07-14 (121 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $298,550.02 USD |
| Return since inception | -- | +198.55% |
| Ann. return | +14.67% | +598.93% |
| Ann. volatility | 6.66% | 73.46% |
| Sharpe (Rf 6.53%) | +1.22 | +4.48 |
| Max drawdown | -4.10% | -10.68% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 5.2% | -1.63% | 2026-11-12 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 4.8% | +8.90% | 2026-11-11 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 4.2% | +1.77% | 2026-11-12 | multi-strategy USD |
| S5 Alternatives | 25.0% | 29.5% | +1420.85% | 2026-11-12 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 12.7% | -0.02% | 2026-11-12 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 11.7% | +17.18% | 2026-11-12 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 7.6% | -16.39% | 2026-11-12 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 4.8% | -5.13% | 2026-11-12 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 5.5% | +0.38% | 2026-11-12 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 6.9% | +15.33% | 2026-11-12 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 7.1% | +15.33% | 2026-11-12 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +8.72% | 2026-11-12 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -30.54% | 2026-11-12 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | -5.34% | 2026-11-12 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | -18.26% | 2026-11-12 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | +13.60% | 2026-11-12 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | -4.19% | 2026-11-12 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -29.64% | 2026-11-12 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | +0.42% | 2026-11-12 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +2.08% | 2026-11-12 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +3.05% | 2026-11-12 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | -1.04% | 2026-11-12 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1055203.64% | 2026-11-12 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
Largest divergences from the backtest correlation matrix (the frontier's key input):

| Pair | Backtest | Realized | Divergence |
| :--- | ---: | ---: | ---: |
| S27-S29 | 0.00 | 0.97 | 0.97 |
| S25-S27 | 0.00 | 0.88 | 0.88 |
| S21-S22 | 0.00 | 0.87 | 0.87 |
| S25-S29 | 0.00 | 0.85 | 0.85 |
| S20-S21 | 0.00 | 0.79 | 0.79 |
| S12-S14 | 0.93 | 0.20 | 0.73 |
| S12-S15 | 0.93 | 0.20 | 0.73 |
| S22-S23 | 0.00 | 0.69 | 0.69 |
| S12-S19 | 0.00 | 0.69 | 0.69 |
| S8-S17 | 0.00 | 0.68 | 0.68 |

## 4. Rebalances
| Date | NAV | Max weight drift |
| :--- | ---: | ---: |
| 2026-08-01 | $202,870.65 | 38.4pp |
| 2026-09-01 | $273,466.52 | 4.0pp |
| 2026-10-01 | $260,481.80 | 5.1pp |
| 2026-11-02 | $281,224.64 | 5.6pp |

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.4300), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
