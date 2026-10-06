# S33 aggressive growth challenger

**Predeclared screen: PASS — research only.** No deployment approval.

**Not an unambiguous improvement:** the prespecified higher-risk S12-style control has both higher CAGR and less drawdown in 2019–2025. Passing the narrower screen does not beat this control or prove alpha.

All figures are after modeled costs in MXN. Signals use completed closes and fill at a later close; old holdings earn the interval return.
No margin, deposits, synthetic pre-inception TQQQ or taxes. Adjusted prices include distributions and embedded fund drag.
Primary cash earns zero. Fixed 6.53% carry is a sensitivity, not historical Bondia. FX is marked at same-date daily observations, not synchronized executable quotes.
All windows are retrospective; none is a newly untouched holdout. More leverage is not evidence of alpha.

## Primary evaluation: 2019–2025

| Model | CAGR | Sharpe (0% Rf) | Max drawdown | Annual turnover | Sharpe × years |
|---|---:|---:|---:|---:|---:|
| challenger | 25.29% | 0.90 | -34.25% | 4.87 | 6.30 |
| qqq | 21.05% | 0.84 | -41.21% | 0.00 | 5.88 |
| tqqq | 40.67% | 0.84 | -82.97% | 0.00 | 5.86 |
| s12_reference | 18.10% | 1.00 | -22.91% | 2.17 | 6.97 |
| s12_scaled_control | 25.85% | 0.94 | -29.76% | 2.04 | 6.55 |

## Full common history: 2011-03-01 through 2026-10-05

| Model | CAGR | Sharpe (0% Rf) | Max drawdown | Peak effective exposure |
|---|---:|---:|---:|---:|
| challenger | 22.95% | 0.89 | -34.25% | 2.12x |
| qqq | 22.18% | 1.01 | -41.21% | 1.00x |
| tqqq | 44.25% | 0.91 | -82.97% | 3.00x |
| s12_reference | 15.49% | 0.90 | -27.51% | 1.80x |
| s12_scaled_control | 21.69% | 0.86 | -36.22% | 2.17x |

S12_reference preserves its original target/risk settings and relative daily rebalance band, but uses this common funded next-close engine, costs and cash assumptions. It is NOT the old published S12 backtest.
S12_scaled_control uses the challenger's exposure target and rebalance rule with TQQQ plus MXN cash, isolating allocation/currency differences. Neither is full live parity.

## Challenger across time and execution sensitivities

| Scenario | Window | CAGR | Total return | Max drawdown |
|---|---|---:|---:|---:|
| base | reference | 18.93% | 289.09% | -33.58% |
| base | evaluation | 25.29% | 384.78% | -34.25% |
| base | recent | 45.40% | 32.96% | -16.93% |
| base | full | 22.95% | 2407.96% | -34.25% |
| double_cost | reference | 16.89% | 239.77% | -36.08% |
| double_cost | evaluation | 23.48% | 337.64% | -35.78% |
| double_cost | recent | 42.35% | 30.83% | -17.32% |
| double_cost | full | 20.96% | 1845.45% | -36.08% |
| two_session_fill | reference | 18.02% | 266.28% | -36.56% |
| two_session_fill | evaluation | 25.62% | 393.75% | -28.32% |
| two_session_fill | recent | 42.96% | 31.26% | -16.51% |
| two_session_fill | full | 22.51% | 2273.81% | -36.56% |
| cash_carry_sensitivity | reference | 20.13% | 320.92% | -32.12% |
| cash_carry_sensitivity | evaluation | 27.13% | 436.65% | -29.54% |
| cash_carry_sensitivity | recent | 46.12% | 33.46% | -16.93% |
| cash_carry_sensitivity | full | 24.41% | 2914.79% | -32.12% |

## All prespecified neighbors (no winner selected)

| Change | Evaluation CAGR | Max drawdown |
|---|---:|---:|
| {'trend': 150} | 27.28% | -28.00% |
| {'trend': 250} | 25.16% | -32.83% |
| {'vol_target': 0.3} | 23.68% | -32.96% |
| {'vol_target': 0.4} | 26.51% | -36.09% |
| {'max_exposure': 1.5} | 22.63% | -31.37% |
| {'max_exposure': 2.5} | 26.80% | -36.25% |

## Screen checks

- base_beats_qqq_and_s12_cagr: True
- double_cost_beats_qqq_and_s12_cagr: True
- two_session_fill_beats_qqq_and_s12_cagr: True
- base_drawdown_better_than_minus_60_percent: True
- positive_recent_return: True

## Limits

- All windows are retrospective; repository history and market outcomes have already been seen
- 2008 is absent because actual TQQQ did not exist
- 35% realized QQQ volatility sizing does not guarantee portfolio volatility, drawdown or exposure limits between trades
- Nasdaq concentration and leveraged ETF daily reset/path dependence remain
- Zero MXN cash primary; fixed cash yield is a sensitivity, never historical Bondia
- No claim to beat all repository strategies, including S14 without canonical comparable histories
- S32 rejection and all existing safety/graduation blocks remain unchanged

The 2x exposure is a target at fills, not a guaranteed cap between rebalances. A 60% drawdown threshold is a research screen, not a stop-loss promise.
The recent window is less than a year: use its total return, not its annualized CAGR as a forecast. Differences between periods are evidence of regime dependence, not permission to select a convenient window.
Ledger quantities use total-return-adjusted prices: they are synthetic accounting units, not broker-reconcilable historical share counts. The simulator assumes fractional fills and reinvested distributions; it does not model taxes or distribution payment-date cash constraints.
Performance is not comparable with mismatched archived S14/S25/S30 results. Do not claim superiority over all strategies.
Reproduce with `python -B strategy33.py`. Only explicit `--download` contacts a public price feed. No broker runner is registered.
