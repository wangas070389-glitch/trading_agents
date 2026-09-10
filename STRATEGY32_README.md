# S32 experiment: rejected for promotion

The frozen diversified-trend challenger did not beat its passive diversified benchmark on the predeclared 2020–2025 retrospective holdout screen. Its net MXN CAGR was 5.48% versus 10.07%, its Sharpe was 0.56 versus 0.65, and maximum drawdown was -22.26% versus -25.78%. Doubling modeled trading/FX costs reduced its CAGR to 4.75%.

This is useful negative evidence: the trend filter modestly reduced the worst drawdown but sacrificed too much return and incurred substantially more turnover. No parameter tuning followed this result. These historical results are not evidence of future returns, and they do not establish superiority over the unreconciled existing strategies.

## Reproduce

```powershell
python strategy32.py --data research/strategy32/prices.csv
python paper_strategy32.py --data research/strategy32/prices.csv --inception 2020-01-01
python -m pytest -q tests/test_strategy32.py
```

Running strategy32.py without --data fetches a new Yahoo snapshot; historical adjustments can change, so use the retained snapshot and its results.json SHA256 for exact reproduction. Prices are USD adjusted total-return closes plus USD/MXN, on complete shared dates. Output ledgers use synthetic fractional total-return units. They cannot be submitted to a broker as actual shares.

The paper runner reconciles its entire transaction ledger to cash, units and ending NAV and atomically writes one isolated state file. Replaying the same snapshot and inception is idempotent. For a prospective paper experiment, supply a new complete snapshot with at least 200 sessions before the explicitly chosen inception and only completed session closes. This runner is not scheduled and S32 is not registered for trading or graduation.

The specification in CHALLENGER_DESIGN.md predates this evaluation within the experiment, but the 2020–2025 period is retrospective, not truly unseen prospective data. Cash earns zero in the primary simulation; the fixed 6.53% scenario is not historical Bondia. Taxes and broker-specific minimum fees are not modeled. Daily risk estimates assume 252 shared observations per year; missing observations are excluded and counted in results.json.

Next research priority: reconstruct existing strategy histories and evaluate the equal-weight passive baseline on the same accounting assumptions. Do not introduce a more complicated S32 variant merely to improve these holdout numbers.
