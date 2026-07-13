# Efficient Frontier v2 — Graduation-Day Target Allocation
**Generated:** 2026-07-12 20:34:06 | Window: 2022-06-21 → 2026-07-02 (1472 overlapping trading days) | Hurdle/Rf: Bondia 6.53% | Cap: 25%/strategy

Covariances and returns come from each strategy's own backtest NAV series over
the common window. **Intraday sleeves (S10/S11/S16) are excluded**: only ~60
in-sample days of NAV exist, and the walk-forward validation showed
near-zero/negative out-of-sample edge — see the satellite policy below.

## 1. Individual Strategy Metrics (common window)
| Strategy | Ann. return | Ann. vol | Sharpe (Rf 6.53%) | Max DD |
| :--- | ---: | ---: | ---: | ---: |
| S1 Alpha Growth | +38.62% | 24.51% | +1.31 | -22.69% |
| S2 MACD | +17.42% | 17.32% | +0.63 | -27.10% |
| S4 US DCF | +26.25% | 17.78% | +1.11 | -16.99% |
| S5 Alternatives | +9.90% | 5.78% | +0.58 | -7.12% |
| S6 High Beta | +11.10% | 8.76% | +0.52 | -5.72% |
| S8 Dividends | +17.01% | 11.53% | +0.91 | -11.39% |
| S9 Stat-Arb | +15.47% | 13.85% | +0.65 | -6.00% |
| S12 VTTL | +17.19% | 15.23% | +0.70 | -13.43% |
| S13 CARA | +10.77% | 13.32% | +0.32 | -14.00% |
| S14 HEDGE | +11.37% | 10.10% | +0.48 | -10.91% |
| S15 TRACK | +11.12% | 9.84% | +0.47 | -10.54% |
| S17 FIBRAs | +7.46% | 11.73% | +0.08 | -16.93% |

## 2. Correlation Matrix
| | S1 | S2 | S4 | S5 | S6 | S8 | S9 | S12 | S13 | S14 | S15 | S17 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | 1.00 | 0.24 | 0.23 | 0.13 | 0.08 | 0.29 | 0.15 | 0.17 | 0.15 | 0.20 | 0.20 | 0.20 |
| S2 | 0.24 | 1.00 | 0.70 | -0.01 | 0.30 | 0.23 | 0.27 | 0.59 | 0.65 | 0.74 | 0.74 | 0.16 |
| S4 | 0.23 | 0.70 | 1.00 | 0.04 | 0.55 | 0.18 | 0.38 | 0.59 | 0.64 | 0.67 | 0.67 | 0.12 |
| S5 | 0.13 | -0.01 | 0.04 | 1.00 | 0.09 | 0.10 | 0.10 | 0.04 | 0.05 | 0.03 | 0.03 | 0.06 |
| S6 | 0.08 | 0.30 | 0.55 | 0.09 | 1.00 | 0.09 | 0.19 | 0.36 | 0.37 | 0.36 | 0.36 | -0.00 |
| S8 | 0.29 | 0.23 | 0.18 | 0.10 | 0.09 | 1.00 | 0.25 | 0.09 | 0.12 | 0.20 | 0.21 | 0.27 |
| S9 | 0.15 | 0.27 | 0.38 | 0.10 | 0.19 | 0.25 | 1.00 | 0.26 | 0.26 | 0.29 | 0.29 | 0.07 |
| S12 | 0.17 | 0.59 | 0.59 | 0.04 | 0.36 | 0.09 | 0.26 | 1.00 | 0.89 | 0.93 | 0.93 | 0.11 |
| S13 | 0.15 | 0.65 | 0.64 | 0.05 | 0.37 | 0.12 | 0.26 | 0.89 | 1.00 | 0.92 | 0.92 | 0.10 |
| S14 | 0.20 | 0.74 | 0.67 | 0.03 | 0.36 | 0.20 | 0.29 | 0.93 | 0.92 | 1.00 | 1.00 | 0.14 |
| S15 | 0.20 | 0.74 | 0.67 | 0.03 | 0.36 | 0.21 | 0.29 | 0.93 | 0.92 | 1.00 | 1.00 | 0.13 |
| S17 | 0.20 | 0.16 | 0.12 | 0.06 | -0.00 | 0.27 | 0.07 | 0.11 | 0.10 | 0.14 | 0.13 | 1.00 |

## 3. Candidate Portfolios
| Portfolio | Ann. return | Ann. vol | Sharpe | Max DD |
| :--- | ---: | ---: | ---: | ---: |
| **Risk Parity, hurdle-filtered (RECOMMENDED)** | +13.66% | 6.17% | +1.16 | -3.29% |
| **Risk Parity (all)** | +13.66% | 6.17% | +1.16 | -3.29% |
| **Max Sharpe (25% cap)** | +22.32% | 9.52% | +1.66 | -5.55% |
| **Min Variance (25% cap)** | +11.11% | 5.05% | +0.91 | -2.88% |
| **Current S7 targets** | +19.24% | 9.21% | +1.38 | -5.64% |

## 4. Weights
| Strategy | **RP hurdle-filtered** | RP (all) | Max Sharpe | Min Variance | Current S7 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| S1 Alpha Growth | **4.5%** | 4.5% | 22.5% | 0.0% | 12.5% |
| S2 MACD | **4.2%** | 4.2% | 0.0% | 0.0% | 0.0% |
| S4 US DCF | **3.9%** | 3.9% | 24.5% | 0.0% | 18.7% |
| S5 Alternatives | **25.0%** | 25.0% | 25.0% | 25.0% | 6.2% |
| S6 High Beta | **11.7%** | 11.7% | 0.0% | 25.0% | 6.2% |
| S8 Dividends | **9.4%** | 9.4% | 23.3% | 11.5% | 12.5% |
| S9 Stat-Arb | **7.4%** | 7.4% | 3.4% | 5.6% | 18.7% |
| S12 VTTL | **4.7%** | 4.7% | 1.2% | 0.0% | 6.2% |
| S13 CARA | **5.2%** | 5.2% | 0.0% | 0.0% | 6.2% |
| S14 HEDGE | **6.4%** | 6.4% | 0.0% | 0.0% | 6.2% |
| S15 TRACK | **6.6%** | 6.6% | 0.0% | 16.1% | 6.2% |
| S17 FIBRAs | **11.0%** | 11.0% | 0.0% | 16.8% | 0.0% |

## 5. Satellite policy for the intraday sleeves (from walk-forward evidence)
- **S10 VWAP:** out-of-sample mean +1.2%/60d, contained drawdowns → optional
  satellite, **max 5%** of the live portfolio, and only after its 90-day live
  record confirms the walk-forward.
- **S11 CCI-ADX:** out-of-sample mean −3.2%/60d → **0%** until a live record
  contradicts the walk-forward.
- **S16 Router:** out-of-sample mean +0.9%/60d with a −48% drawdown window →
  **0%**; research project, not an allocation.

## 6. How to use this
- **Hurdle-filtered risk parity is the recommended core**: risk contributions are
  equalized (no dependence on noisy expected-return estimates) but only across
  strategies that actually beat Bondia on the common window.
- Max Sharpe shows what historical means would suggest — treat it as an upper
  bound on concentration, not a target; backtest means are noisy.
- Strategies only receive their weight once they reach **READY** in
  graduation_report.md; until then their slice stays in Bondia cash.
- Caveats: MXN and USD series are mixed (FX exposure differs by sleeve); the
  common window (2022→) is mostly one market era; S13 is retired standalone
  and its weight should be folded into S14/S15 at implementation.
