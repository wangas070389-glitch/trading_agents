# S32 Diversified Trend — frozen research specification v1

Declared before fetching/evaluating this experiment's data. No parameter selection from results.

- Universe: SPY, EFA, IEF, GLD. This universe was chosen today; survivorship and retrospective design bias remain.
- Signals: adjusted USD close above its 200-session average. Trailing 60-session annualized volatility, floored at 5%.
- Sizing: inverse volatility across all four assets; each allocation capped at 35%. Ineligible assets' allocations stay in MXN cash, without redistribution. Gross allocation at most 100%, no borrowing or shorts.
- Decisions: final observed session of each month. Execute at the NEXT session's close after that session's return. No same-close signal fills.
- Trade threshold: 2 percentage points of portfolio NAV; if the largest deviation exceeds it, rebalance the portfolio to target. Otherwise retain existing units.
- Friction: 10 bps asset execution plus 20 bps FX per traded notional, one-way. Stress at 60 bps total. Fractional total-return units are a research abstraction.
- Base cash: zero nominal MXN interest; a separate fixed 6.53% cash scenario is NOT historical Bondia. Taxes excluded. Adjusted prices include distributions and fund expenses; FX converts USD exposures into MXN daily.
- Data: Yahoo adjusted closes, 2005-01-01 through 2025-12-31, with no forward filling. Reject incomplete, duplicate, nonpositive or nonfinite inputs. Snapshot and SHA256 retained.
- Evaluation: 2006-2019 development reference; 2020-2025 retrospective holdout. This is not truly prospective evidence: those market events were known when choosing the design. No tuning after evaluation.
- Benchmarks: equal-weight four-asset portfolio with the same monthly schedule and trade threshold; SPY buy-and-hold; MXN cash. Same data and friction assumptions.
- Acceptance on holdout: net CAGR above zero-interest cash, Sharpe above equal-weight, and shallower maximum drawdown than equal-weight. Otherwise do not promote. Also publish 2020-2022 and 2023-2025 independently and doubled-cost stress without selecting parameters.
- S8/S11/S12 comparison withheld until their histories are reconstructed on equivalent dates/capital/costs. Their existing summary statistics are not comparable evidence.

S32 stays outside the production strategy registry and scheduled trading workflow during research. Its paper runner is an isolated, repeatable replay of a data snapshot with exact units, cash and transaction events; it makes no brokerage calls and grants no graduation status.
