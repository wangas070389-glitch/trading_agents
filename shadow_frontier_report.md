# Shadow Frontier — Live Track Record of the Allocation Layer
**Generated:** 2026-07-17 15:13:39 | Inception: 2026-07-14 (3 calendar days) | Virtual capital: $100,000 USD
**Weights (frozen):** efficient_frontier_report.md 2026-07-11 -- Risk Parity, hurdle-filtered (RECOMMENDED)

This book paper-trades the recommended frontier allocation itself, marked
from the same NAVs the pipeline already collects. It answers: does the
*blend* behave as the backtest covariances promised? Sleeve returns are
chain-linked **net of deposits**; stale/NaN marks freeze a sleeve rather
than corrupt it; rebalanced to targets on the first mark of each month.

## 1. Promise vs. Realized
| Metric | Backtest promise | Realized (live) |
| :--- | ---: | ---: |
| NAV | -- | $99,151.67 USD |
| Return since inception | -- | -0.85% |
| Ann. return | +14.67% | -- (<30d) |
| Ann. volatility | 6.66% | -- (<10 marks) |
| Sharpe (Rf 6.53%) | +1.22 | -- |
| Max drawdown | -4.10% | -- |

## 2. Sleeves
| Sleeve | Target w | Current w | TR since inception | Last mark | Source |
| :--- | ---: | ---: | ---: | :--- | :--- |
| S1 Adaptive Value (BMV) | 5.4% | 5.4% | -0.72% | 2026-07-17 | multi-strategy USD |
| S2 MACD Systematic | 4.9% | 4.9% | -0.28% | 2026-07-17 | watchdog MXN/USD |
| S4 US DCF Value-Growth | 4.5% | 4.5% | -1.09% | 2026-07-17 | multi-strategy USD |
| S5 Alternatives | 25.0% | 25.3% | +0.18% | 2026-07-17 | multi-strategy USD |
| S6 High-Beta Momentum | 13.5% | 13.5% | -0.67% | 2026-07-17 | multi-strategy USD |
| S8 Dividend Quality | 11.8% | 11.9% | -0.01% | 2026-07-17 | multi-strategy USD |
| S9 AI Regime Stat-Arb | 8.6% | 8.6% | -1.17% | 2026-07-17 | multi-strategy USD |
| S12 VTTL Trend+Vol | 5.3% | 5.2% | -2.65% | 2026-07-17 | multi-strategy USD |
| S13 CARA Cross-Asset | 6.0% | 5.9% | -2.66% | 2026-07-17 | multi-strategy USD |
| S14 HEDGE Aggregator | 7.4% | 7.3% | -2.00% | 2026-07-17 | multi-strategy USD |
| S15 TRACK Tracker | 7.6% | 7.5% | -2.01% | 2026-07-17 | multi-strategy USD |
| S17 FIBRAs Dynamic | 0.0% | 0.0% | +0.94% | 2026-07-17 | multi-strategy USD |
| S19 Particle Filter QQQ | 0.0% | 0.0% | -2.53% | 2026-07-17 | multi-strategy USD |
| S20 Hurst Exponent Dynamic | 0.0% | 0.0% | -6.80% | 2026-07-17 | multi-strategy USD |
| S21 Golden Entropy | 0.0% | 0.0% | -6.71% | 2026-07-17 | multi-strategy USD |
| S22 Walk-Forward ML | 0.0% | 0.0% | -6.68% | 2026-07-17 | multi-strategy USD |
| S23 Calculus S&R | 0.0% | 0.0% | -0.48% | 2026-07-17 | multi-strategy USD |
| S24 ML Classifier | 0.0% | 0.0% | -6.40% | 2026-07-17 | multi-strategy USD |
| S25 Golden MACD BMV | 0.0% | 0.0% | -1.03% | 2026-07-17 | multi-strategy USD |
| S27 Golden Hurst | 0.0% | 0.0% | -0.48% | 2026-07-17 | multi-strategy USD |
| S29 Golden Stat-Arb | 0.0% | 0.0% | -0.48% | 2026-07-17 | multi-strategy USD |
| S30 Golden MACD US | 0.0% | 0.0% | +0.03% | 2026-07-17 | multi-strategy USD |
| S31 Fibonacci S&R | 0.0% | 0.0% | +1142391.55% | 2026-07-17 | multi-strategy USD |

## 3. Correlation check (realized vs. backtest)
*Needs >= 15 daily return observations; have 3.*

## 4. Rebalances
*None yet (monthly, first mark of each month).*

## 5. Warnings
*None this cycle.*

## 6. Method notes
- USD-denominated; MXN sleeves converted at usd_mxn_rate (17.5310), so they carry FX exposure — same caveat as the frontier report.
- S2 is marked from watchdog snapshots (it has no multi-strategy NAV column), so its marks can lag the others by one cycle.
- A weight change is a new allocation config (KILL_CRITERIA P3): delete portfolio_shadow_frontier.json to restart the clock, and say so here.
- This is evidence for the ALLOCATION layer only; individual strategies still graduate (or die) via graduation_report.md / KILL_CRITERIA.md.
