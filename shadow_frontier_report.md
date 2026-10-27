# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-10-27 19:37:16 | Inception: 2026-07-14 (105 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $272,072.85 USD |
| Return since inception | -- | +172.07% |
| Ann. return | +14.67% | +598.16% |
| Ann. volatility | 6.66% | 78.45% |
| Sharpe (Rf 6.53%) | +1.22 | +4.41 |
| Max drawdown | -4.10% | -10.68% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 5.7% | +0.76% | 2026-10-27 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 5.0% | +5.13% | 2026-10-26 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 4.3% | +1.77% | 2026-10-27 | multi-strategy USD |
| S5 Alternatives | 25.0% | 27.6% | +958.06% | 2026-10-27 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 12.9% | -0.15% | 2026-10-27 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 12.1% | +10.00% | 2026-10-27 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 8.1% | -10.18% | 2026-10-27 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 4.9% | +5.85% | 2026-10-27 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 5.4% | +0.48% | 2026-10-27 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 6.9% | +19.83% | 2026-10-27 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 7.1% | +19.83% | 2026-10-27 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +2.01% | 2026-10-27 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -19.18% | 2026-10-27 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | -5.61% | 2026-10-27 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | -2.19% | 2026-10-27 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | +16.76% | 2026-10-27 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | +14.64% | 2026-10-27 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -15.78% | 2026-10-27 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | +0.14% | 2026-10-27 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +1.79% | 2026-10-27 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +2.75% | 2026-10-27 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | -0.80% | 2026-10-27 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1083424.05% | 2026-10-27 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
Largest divergences from the backtest correlation matrix (the frontier's key input):

| Pair | Backtest | Realized | Divergence |
| :--- | ---: | ---: | ---: |
| S27-S29 | 0.00 | 0.97 | 0.97 |
| S20-S21 | 0.00 | 0.95 | 0.95 |
| S25-S27 | 0.00 | 0.88 | 0.88 |
| S21-S22 | 0.00 | 0.87 | 0.87 |
| S25-S29 | 0.00 | 0.86 | 0.86 |
| S20-S22 | 0.00 | 0.85 | 0.85 |
| S9-S25 | 0.00 | 0.75 | 0.75 |
| S12-S14 | 0.93 | 0.21 | 0.72 |
| S12-S15 | 0.93 | 0.21 | 0.72 |
| S9-S27 | 0.00 | 0.71 | 0.71 |

## 4. Rebalances
| Date | NAV | Max weight drift |
| :--- | ---: | ---: |
| 2026-08-01 | $202,870.65 | 38.4pp |
| 2026-09-01 | $273,466.52 | 4.0pp |
| 2026-10-01 | $260,481.80 | 5.1pp |

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.4300), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
