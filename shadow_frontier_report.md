# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-11-06 20:32:38 | Inception: 2026-07-14 (115 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $291,175.54 USD |
| Return since inception | -- | +191.18% |
| Ann. return | +14.67% | +606.77% |
| Ann. volatility | 6.66% | 74.73% |
| Sharpe (Rf 6.53%) | +1.22 | +4.46 |
| Max drawdown | -4.10% | -10.68% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 5.3% | -1.68% | 2026-11-06 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 4.8% | +7.66% | 2026-11-05 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 4.3% | +1.77% | 2026-11-06 | multi-strategy USD |
| S5 Alternatives | 25.0% | 28.0% | +1309.37% | 2026-11-06 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 13.0% | -0.09% | 2026-11-06 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 11.7% | +15.11% | 2026-11-06 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 7.9% | -14.85% | 2026-11-06 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 4.9% | -5.06% | 2026-11-06 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 5.7% | +0.28% | 2026-11-06 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 7.0% | +13.90% | 2026-11-06 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 7.2% | +13.91% | 2026-11-06 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +6.85% | 2026-11-06 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -31.25% | 2026-11-06 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | -5.44% | 2026-11-06 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | -27.81% | 2026-11-06 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | +0.33% | 2026-11-06 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | -15.36% | 2026-11-06 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -37.84% | 2026-11-06 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | +0.32% | 2026-11-06 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +1.97% | 2026-11-06 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +2.94% | 2026-11-06 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | -1.50% | 2026-11-06 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1062429.03% | 2026-11-06 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
Largest divergences from the backtest correlation matrix (the frontier's key input):

| Pair | Backtest | Realized | Divergence |
| :--- | ---: | ---: | ---: |
| S27-S29 | 0.00 | 0.97 | 0.97 |
| S25-S27 | 0.00 | 0.88 | 0.88 |
| S21-S22 | 0.00 | 0.86 | 0.86 |
| S25-S29 | 0.00 | 0.85 | 0.85 |
| S20-S21 | 0.00 | 0.81 | 0.81 |
| S12-S14 | 0.93 | 0.20 | 0.73 |
| S12-S15 | 0.93 | 0.20 | 0.73 |
| S12-S23 | 0.00 | 0.69 | 0.69 |
| S12-S19 | 0.00 | 0.69 | 0.69 |
| S20-S22 | 0.00 | 0.68 | 0.68 |

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
