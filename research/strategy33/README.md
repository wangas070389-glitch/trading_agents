# Growth research handoff

The user prioritized highest growth and accepted large drawdowns. One challenger
was specified before its first market-data run; the design was committed as
`88276912`. No winning neighbor was selected afterwards. The frozen design and
data hashes are in `manifest.json`; the implementation hash is in `results.json`.

## Outcome

Read [report.md](report.md) for all periods, controls, sensitivities and limits.
The primary 2019–2025 MXN comparison, after 30 bps one-way costs and with zero
interest on MXN cash, is:

| Model | Annualized return | Worst drawdown |
|---|---:|---:|
| S33 QQQ/TQQQ growth challenger | 25.29% | -34.25% |
| S12-style, original risk targets | 18.10% | -22.91% |
| S12-style, challenger risk targets/control | 25.85% | -29.76% |
| QQQ buy-and-hold | 21.05% | -41.21% |
| TQQQ buy-and-hold | 40.67% | -82.97% |

The challenger passes its predeclared comparison against QQQ and original-risk
S12-style under base costs, doubled costs, and two-session fills. **It does not
prove that a new strategy is necessary:** the simpler higher-risk S12-style
control outperforms it in the primary evaluation. Across the full 2011–2026
window S33 instead has somewhat higher CAGR and less drawdown than that control.
It only narrowly beats QQQ's full-window CAGR and has lower full-window Sharpe.
This is mixed, regime-dependent evidence, not a universal winner.

S12 comparisons preserve the target rules but use this simulator's funded,
next-close execution and common costs/carry. They do not reproduce the archived
S12 headline numbers or certify the broker runner. The scaled control additionally
uses the challenger's weekly/band rebalancing to isolate allocation differences.

The six prespecified neighbors are published without selecting a replacement.
No claim of an untouched holdout or statistical confidence is made. The observed
history excludes 2000–2002 and 2008. TQQQ buy-and-hold's much higher return came
with a near-83% drawdown; that return is not a reasonable guaranteed-growth target.

## Implementation

The primary rule uses QQQ's 200-session trend and 20-session realized volatility.
When trend-positive, target Nasdaq exposure is the lesser of 2x and 35% divided
by realized QQQ volatility. QQQ provides exposure up to 1x; QQQ/TQQQ combinations
provide the additional exposure without borrowing portfolio cash. Risk is
rebalanced weekly with a five-percentage-point band; risk-off exits can occur
daily. Targets observed at a completed close fill at the next close. Previously
held positions, not newly purchased ones, earn the intervening return.

Targets are not guaranteed bounds: exposure drifts between trades, and FX affects
MXN risk. S33 reached about 2.12x effective exposure in this simulation. A
volatility estimate cannot prevent gaps or guarantee any maximum drawdown.
Adjusted prices create synthetic accounting units, not broker share-lot records.

Trend and volatility sizing are research hypotheses motivated by
[Moskowitz, Ooi and Pedersen](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum)
and [Moreira and Muir](https://www.nber.org/papers/w22208), not endorsements of
these parameters or expected returns. TQQQ targets 3x **daily** Nasdaq-100
performance before fees; longer-period compounding differs and leverage adds
risk, as the [issuer explains](https://www.proshares.com/our-etfs/leveraged-and-inverse/tqqq).

## Reproduce

Use the project's isolated Python environment/dependencies. From the repo root:

```powershell
python -B -m pytest -q tests --junitxml=research/strategy33/pytest.xml
python -B strategy33.py
```

Ordinary replay is offline and checks the immutable data/design hashes. The
explicit acquisition command `python -B strategy33.py --download` refuses to
overwrite this snapshot. All generated files stay in this research directory.
No registry, schedule, broker connector or existing strategy parameter was changed.
The repair PR and S3 halt remain intact.

Verification: **223 tests and six subtests pass, with no failures or skips.**
Sixteen S33 tests cover funded two-sided fees, causal targets/fills, risk-off
exits, delayed execution, ledger/NAV reconciliation, frozen hashes, allocation
constraints and unregistered research status. `pytest.xml` records the full suite.

## What next would establish useful evidence

Keep the primary and scaled-control rules frozen. Compare them on a prospective
paper record beginning after this research date, with actual quotes, cash carry,
tradable share sizing, slippage and operational reconciliation. Do not switch to
whichever neighbor performed best retrospectively. Historical broker/accounting
blocks still apply, and passing this growth screen does not waive the 90-day
verified paper-history requirement or authorize real-money deployment.
