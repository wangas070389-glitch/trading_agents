# Validation handoff — 2026-10-05

This is a research-only record, not permission to trade. Read [report.md](report.md)
for corrected results and [ledger_audit.md](ledger_audit.md) for unresolved books.
The original operating portfolios, ledgers and archived backtest reports were not
rewritten by this validation.

Verification: **207 tests and six subtests passed, no failures or skips**, in
28.42 seconds. `pytest.xml` contains the full run. The separate pinned-evidence
replay also reproduced S32's frozen metrics, reconciled its paper ledger and
passed six synthetic invariant groups. `git diff --check` was clean.

## Reproduce without market or broker access

Use Python 3.12 with `requirements.txt` and CPU PyTorch installed. Exact observed
package versions are recorded in `results.json` under `runtime`. From the repo root:

```powershell
python -B -m pytest -q tests --junitxml=research/validation/2026-10-05/pytest.xml
python -B validate_strategies.py --ref fd7461011259e175777f7c21695e5abfc696f829
python -B scratch/evaluate_strategy_evidence.py --ref fd7461011259e175777f7c21695e5abfc696f829 --offline-checks
```

Tests deny external HTTP/socket access; provider behavior uses fixtures. Report
and cache tests write to temporary directories. The validator reads committed
books into temporary copies, checks frozen price SHA256 values, and writes only
inside `research/validation`. It never imports or executes broker runners.

The quoted Git revision pins the accounting inputs, not the repaired source.
`results.json` separately fingerprints the implementation with LF-normalized
SHA256 values. `.gitattributes` preserves LF bytes for the frozen price files on
Windows and Linux. CI checks snapshot hashes and the declared dates/universes.

## Data and experiment boundaries

- `prices_manifest.json` records the provider, acquisition time, universe, requested
  window, dropped incomplete dates and exact file hashes. Acquisition used an
  explicit `--download`; ordinary reruns do not refresh data. A new acquisition
  must use a new `--output research/validation/<name>` directory.
- S25 and S30 cover 2010-02-11 through 2026-10-05, using adjusted closes and their
  native currencies. Five equal initial sleeves are compared with the same
  buy-and-hold basket, with funded entry fees. No parameters were optimized here.
- Each strategy is rerun with base costs/carry, zero cash carry, and doubled costs.
  These are retrospective fixed-universe sensitivity tests, not independent
  holdouts or exact reproductions of shared-cash paper allocation.
- S25 underperforms its basket in all scenarios. S30 reduces drawdown but trails
  its selected-stock basket in both CAGR and zero-risk-free Sharpe. Neither
  establishes a deployable edge. Historical carry, universe selection, live
  execution parity, and complete accounting remain open.
- S32's existing frozen rejection is preserved. No tuning was done to reverse it.

## What still needs outside evidence

The ledger audit found 23 mismatches, four unresolved books and one matching S8
snapshot. These are not all evidence of lost money: for example S12 differs by
only MXN 0.09, while several books have unresolved opening-funding conventions.
S8 snapshot agreement does not validate its complete performance history.

S3 requires dated broker statements/fills and explicit allocation of shared-account
positions to strategies. Do not copy aggregate broker positions into a single
strategy, invent cash adjustments, run `reconcile_s3.py`, remove a halt, or close
positions just to make the audit pass. Manual broker reconciliation is a separate
controlled step. `HALT_us_stocks.flag` is included in this repair branch because
the workspace safety rules require a hold for negative cash. It only affects
S3 runners using this checkout (or deployments that adopt this branch), not
the separate online main branch or other strategies. It does not cancel orders
or close positions. A regression checks that S3 returns before broker access
when a temporary halt flag exists. No broker endpoint was invoked.

S1/S8 need point-in-time fundamental inputs; S2 needs one canonical signal and
accounting engine; S24 needs a preserved independent market sample. Its actual
Random Forest is tested for future-data invariance on synthetic prices, not for
profitability. S12 and one S14/S15 representative remain research priorities.
All invalidated-backtest blocks and the existing 90-day graduation gate remain.
