# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-09-24 18:52:15 | Inception: 2026-07-14 (72 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $259,727.72 USD |
| Return since inception | -- | +159.73% |
| Ann. return | +14.67% | +809.73% |
| Ann. volatility | 6.66% | 92.37% |
| Sharpe (Rf 6.53%) | +1.22 | +5.11 |
| Max drawdown | -4.10% | -10.68% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 5.4% | -8.81% | 2026-09-24 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 5.2% | -1.95% | 2026-09-24 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 4.7% | +1.77% | 2026-09-24 | multi-strategy USD |
| S5 Alternatives | 25.0% | 30.3% | +819.90% | 2026-09-24 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 14.2% | -0.31% | 2026-09-24 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 12.3% | +2.78% | 2026-09-24 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 8.7% | -8.68% | 2026-09-24 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 5.9% | +7.04% | 2026-09-24 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 3.8% | +5.54% | 2026-09-24 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 4.7% | +21.49% | 2026-09-24 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 4.8% | +21.47% | 2026-09-24 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | -0.85% | 2026-09-24 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -7.00% | 2026-09-24 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | -6.17% | 2026-09-24 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | -4.60% | 2026-09-24 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | +4.16% | 2026-09-24 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | +4.52% | 2026-09-24 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -24.55% | 2026-09-24 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | -0.85% | 2026-09-24 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +1.19% | 2026-09-24 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +1.19% | 2026-09-24 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | -0.94% | 2026-09-24 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1204552.23% | 2026-09-24 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
Largest divergences from the backtest correlation matrix (the frontier's key input):

| Pair | Backtest | Realized | Divergence |
| :--- | ---: | ---: | ---: |
| S27-S29 | 0.00 | 1.00 | 1.00 |
| S20-S21 | 0.00 | 1.00 | 1.00 |
| S25-S29 | 0.00 | 0.94 | 0.94 |
| S25-S27 | 0.00 | 0.94 | 0.94 |
| S21-S22 | 0.00 | 0.89 | 0.89 |
| S20-S22 | 0.00 | 0.88 | 0.88 |
| S9-S29 | 0.00 | 0.78 | 0.78 |
| S9-S27 | 0.00 | 0.78 | 0.78 |
| S9-S25 | 0.00 | 0.75 | 0.75 |
| S8-S25 | 0.00 | 0.70 | 0.70 |

## 4. Rebalances
| Date | NAV | Max weight drift |
| :--- | ---: | ---: |
| 2026-08-01 | $202,870.65 | 38.4pp |
| 2026-09-01 | $273,466.52 | 4.0pp |

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.4300), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
