# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-07-30 20:48:20 | Inception: 2026-07-14 (16 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $183,052.01 USD |
| Return since inception | -- | +83.05% |
| Ann. return | +14.67% | -- (<30d) |
| Ann. volatility | 6.66% | 146.37% |
| Sharpe (Rf 6.53%) | +1.22 | +7.19 |
| Max drawdown | -4.10% | -1.22% |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 3.0% | +1.67% | 2026-07-30 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 2.6% | -1.26% | 2026-07-30 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 2.5% | -0.15% | 2026-07-30 | multi-strategy USD |
| S5 Alternatives | 25.0% | 59.5% | +335.77% | 2026-07-30 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 7.3% | -0.70% | 2026-07-30 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 6.7% | +3.71% | 2026-07-30 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 4.5% | -4.87% | 2026-07-30 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 2.8% | -3.63% | 2026-07-30 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 3.1% | -4.40% | 2026-07-30 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 3.9% | -2.54% | 2026-07-30 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 4.0% | -2.54% | 2026-07-30 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +3.54% | 2026-07-30 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -14.57% | 2026-07-30 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | -13.87% | 2026-07-30 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | -13.89% | 2026-07-30 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | -13.91% | 2026-07-30 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | -6.09% | 2026-07-30 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -13.85% | 2026-07-30 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | -0.47% | 2026-07-30 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | +0.73% | 2026-07-30 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | +0.73% | 2026-07-30 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | +0.19% | 2026-07-30 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1007878.63% | 2026-07-30 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
Largest divergences from the backtest correlation matrix (the frontier's key input):

| Pair | Backtest | Realized | Divergence |
| :--- | ---: | ---: | ---: |
| S27-S29 | 0.00 | 1.00 | 1.00 |
| S20-S21 | 0.00 | 1.00 | 1.00 |
| S14-S29 | 0.00 | 0.98 | 0.98 |
| S14-S27 | 0.00 | 0.98 | 0.98 |
| S15-S29 | 0.00 | 0.98 | 0.98 |
| S15-S27 | 0.00 | 0.98 | 0.98 |
| S12-S29 | 0.00 | 0.97 | 0.97 |
| S12-S27 | 0.00 | 0.97 | 0.97 |
| S1-S29 | 0.00 | 0.97 | 0.97 |
| S1-S27 | 0.00 | 0.97 | 0.97 |

## 4. Rebalances
*None yet (monthly, first mark of each month).*

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.3360), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
