# S34: earnings-driven stock-momentum research pipeline

**Implemented and tested; historical performance is unavailable because the
required point-in-time data has not been supplied. Not registered for trading.**

The user explicitly requested building the pipeline and specifying the missing
data. No paid account was opened, no subscription purchased, no credentials
accessed, and no current fundamentals were used as historical estimates.

## What is built

- Provider-neutral historical-data validation and an explicit provenance-review
  gate, tied to the exact dataset hash.
- Original quarterly EPS surprises using consensus available strictly before
  announcement; later restatements cannot improve earlier signals.
- Forward EPS revision comparisons across the same fiscal period and share/
  accounting basis, with separate as-of and availability times.
- Historical universe membership/sectors, stable security IDs, contiguous
  price history, liquidity/price screens and terminal/delisting treatment.
- Fixed combined earnings/price-momentum ranking plus earnings-only,
  broad momentum-only, coverage-matched momentum and trailing-volatility-managed
  QQQ controls.
- Funded next-close fills, two-sided transaction costs, a two-session-delay
  stress, a doubled-cost stress, NAV/cash/trade audits and explicit rejected
  batches. A required failed sell cannot finance fresh buys.
- Private, reproducible result output with code/design/data/review hashes.
  A data failure produces **no profitability result**, not a fabricated pass.

## Fixed primary hypothesis

The design in `design.json` is frozen before any empirical S34 results. It tests
whether earnings information adds value beyond price momentum, not whether
more leverage increases a favorable historical return.

At the first observed session of a week, after the close:

1. Use historical common stocks with raw price at least USD 5 and average
   20-session traded notional at least USD 5 million.
2. Require an initial earnings announcement within 45 calendar days, an EPS
   surprise of at least 5%, and a positive forward annual EPS revision versus
   the matching-period estimate available 21 sessions earlier.
3. Require positive 126-session momentum excluding the latest five sessions,
   and positive return over those five confirmation sessions.
4. Rank by equal-weight cross-sectional percentiles of surprise, revision and
   momentum. The EPS normalization denominator is floored at USD 0.25, and the
   two normalized EPS signals are clipped to [-2, 2]; these are fixed research
   choices, not optimized values.
5. Select up to 20 names at 5% target weights, at most 25% per historical sector.
   Reduce all weights proportionally if the selected portfolio's trailing
   20-session estimated volatility exceeds 20% annualized. Never lever up.
6. Fill no earlier than the next session's close. Existing holdings earn the
   intervening return; newly bought holdings do not receive a pre-fill return.

Unallocated USD cash earns zero in the primary test. Targets and volatility
ceilings are not guaranteed realized limits; weights drift between trades.
The earnings-only ablation omits the price-momentum/confirmation gates. The
momentum-only control omits earnings information. The additional
`momentum_covered` control requires the same usable earnings-event/estimate
coverage but ignores the signs and values of earnings surprises/revisions in
selection. This helps separate a new signal from nonrandom data availability.
QQQ uses the same trailing
volatility ceiling without pretending the realized risk is identical. Reports
include actual volatility and mean exposure so risk differences remain visible.

## Execution abstractions and limits

The engine uses total-return-index units, fractional allocations, no taxes,
no margin and no shorting. These are research units, not broker-reconcilable
share lots. At 30 bps one-way cost, a full switch pays both sale and purchase
costs. Trades exceeding 1% of prior observable average daily traded notional,
untradable legs or missing fill quotes reject the whole modeled batch. This
conservative all-or-nothing assumption is not a realistic partial-fill/order
router. Missing held marks abort the run; terminal losses are never erased.

The implementation is a research prototype, not a production data adapter or
live broker system. Data-provider schema mapping, sample verification and
large-scale storage need review when an actual export is available. No
statistical significance or market edge follows from passing software tests.

## Use

```powershell
# Safe now: reports missing data and exits 2, with no performance output.
python -B strategy34.py audit

# Once a licensed export and an independent review have been supplied:
python -B strategy34.py audit --bundle research/strategy34/private/bundle.json --review research/strategy34/private/review.json
python -B strategy34.py run --bundle research/strategy34/private/bundle.json --review research/strategy34/private/review.json --output research/strategy34/private/run-001

# Offline software verification; fixtures are explicitly synthetic.
python -B -m pytest -q tests
```

See [DATA_REQUIREMENTS.md](DATA_REQUIREMENTS.md) for exact fields, semantics and
source options. `review_template.json` is deliberately incomplete and must not
be presented as an approval. Actual inputs and derived outputs stay in the
Git-ignored `private/` directory; existing run directories cannot be overwritten.
Do not commit licensed data or private provider credentials to a pull request.

## Current evidence status

`status.json` records **BLOCKED_DATA_REQUIRED**, `performance_available: false`
and `deployment_approved: false`. This is the expected result in this repository.
The tests exercise selection chronology, fiscal-period joins, restatements,
historical membership, fees, ledger reconciliation, failed sells, terminal losses,
hash reviews, output isolation and all 15 model/scenario combinations. Their
synthetic returns are not published as investment evidence.

Local verification: **251 tests and 6 subtests passed**, including 28 S34 tests.
The full-suite JUnit record is saved in `pytest.xml`.

The statistical hypothesis is motivated by research on
[price and earnings momentum](https://www.nber.org/papers/w5375) and
[earnings-news underreaction](https://www.nber.org/papers/w11683). Those findings
do not establish that this implementation works today, after costs, or at the
chosen parameters. Reference/evaluation windows are explicitly retrospective;
the design never claims a newly untouched holdout.

No existing strategy, schedule, S3 safety hold, or graduation gate was modified.
A future performance comparison still needs exposure-aware interpretation,
selection-adjusted uncertainty, independent periods and prospective paper
execution. There is no automatic promotion or claimed return target.
