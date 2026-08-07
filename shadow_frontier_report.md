# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-08-07 18:56:24 | Inception: 2026-07-14 (24 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $211,851.46 USD |
| Return since inception | -- | +111.85% |
| Ann. return | +14.67% | -- (<30d) |
| Ann. volatility | 6.66% | 126.76% |
| Sharpe (Rf 6.53%) | +1.22 | +6.80 |
| Max drawdown | -4.10% | -5.29% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 5.2% | +2.83% | 2026-08-07 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 4.7% | -0.39% | 2026-08-07 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 4.4% | +1.77% | 2026-08-07 | multi-strategy USD |
| S5 Alternatives | 25.0% | 7.3% | +56.40% | 2026-08-07 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 13.2% | +1.25% | 2026-08-07 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 11.4% | +4.25% | 2026-08-07 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 8.4% | -3.63% | 2026-08-07 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 5.3% | +2.19% | 2026-08-07 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 10.6% | +76.97% | 2026-08-07 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 14.6% | +101.90% | 2026-08-07 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 15.0% | +101.90% | 2026-08-07 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +0.69% | 2026-08-07 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -9.88% | 2026-08-07 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | +1.94% | 2026-08-07 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | +1.93% | 2026-08-07 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | +1.94% | 2026-08-07 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | +8.82% | 2026-08-07 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -20.10% | 2026-08-07 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | +0.76% | 2026-08-07 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +1.97% | 2026-08-07 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +1.97% | 2026-08-07 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | +2.19% | 2026-08-07 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1018870.60% | 2026-08-07 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
Largest divergences from the backtest correlation matrix (the frontier's key input):

| Pair | Backtest | Realized | Divergence |
| :--- | ---: | ---: | ---: |
| S27-S29 | 0.00 | 1.00 | 1.00 |
| S20-S21 | 0.00 | 1.00 | 1.00 |
| S25-S29 | 0.00 | 0.94 | 0.94 |
| S25-S27 | 0.00 | 0.94 | 0.94 |
| S1-S29 | 0.00 | 0.94 | 0.94 |
| S1-S27 | 0.00 | 0.94 | 0.94 |
| S20-S22 | 0.00 | 0.92 | 0.92 |
| S21-S22 | 0.00 | 0.92 | 0.92 |
| S1-S25 | 0.00 | 0.88 | 0.88 |
| S12-S29 | 0.00 | 0.86 | 0.86 |

## 4. Rebalances
| Date | NAV | Max weight drift |
| :--- | ---: | ---: |
| 2026-08-01 | $202,870.65 | 38.4pp |

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.1320), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
