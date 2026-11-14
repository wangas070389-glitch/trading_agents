# S34 data request and provider-neutral contract

No subscription has been purchased, no credentials are required by this code,
and no historical performance has been calculated. Supply a licensed export;
the system does not turn present-day fundamentals into historical observations.

## What to request from a provider

Ask for historical US-listed common stocks, including securities that later
delisted, changed tickers, merged or went bankrupt. Prefer 2000 onward to include
the technology crash and 2008; the importer requires at least 1,000 market
sessions, but that minimum alone is not sufficient validation. Include:

1. Original quarterly EPS actuals, exact public announcement timestamps, the
   vendor's historical availability timestamps, and separately versioned
   corrections. Distinguish GAAP/adjusted EPS, basic/diluted EPS and currencies.
2. Historical quarterly consensus **snapshots known before each announcement**,
   not today's estimate history reconstructed using revised values.
3. Historical annual forward-consensus snapshots, with exact fiscal-period end
   dates. At least daily/weekly vintages are preferable. A revision compares the
   same fiscal year and EPS/share basis, never FY1 versus the following FY1 year.
4. Stable security IDs and dated identifier links, historical common-stock
   eligibility and sectors, and daily exchange-session timestamps. Current index
   constituents or current ticker lists are not a valid historical universe.
5. Daily unadjusted close and USD traded volume, plus a total-return index that
   includes distributions, corporate actions and terminal/delisting outcomes
   exactly once. Include nontradability, suspensions and settlement records.

Examples to investigate are I/B/E/S historical estimates/actuals paired with CRSP
security/return/delisting histories, subject to access, licensing, link quality
and available timestamp vintages. These are examples, not an assertion that a
subscription automatically supplies every required field. WRDS describes its
[estimate datasets](https://wrds-www.wharton.upenn.edu/pages/video-support/),
[identifier linking](https://wrds-www.wharton.upenn.edu/pages/wrds-research/database-linking-matrix/linking-ibes-with-crsp/),
and [CRSP histories including delistings](https://wrds-www.wharton.upenn.edu/demo/crsp/form/).

The [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
provide submissions and XBRL disclosures, not a historical analyst-consensus
feed. They can support an actuals/timestamp audit. Current aggregated company
facts or calendar frames must not be treated as pre-announcement expectations.

## Export format accepted by this implementation

Place `bundle.json` and its independently completed `review.json` below
`research/strategy34/private/` (Git-ignored). A licensed provider's CSV/Parquet
export will need a documented adapter into this contract. No provider-specific
column mapping is guessed. JSON is the initial research interchange format;
large full-universe datasets may need a partitioned adapter before loading.

Top-level object:

```json
{
  "schema_version": 1,
  "dataset_kind": "market",
  "provenance": {
    "provider": "Actual licensed source and dataset version",
    "exported_at": "2026-11-14T12:00:00Z",
    "universe_definition": "Historical selection rule, coverage and exclusions",
    "calendar_source": "Exchange-session source including holidays/early closes",
    "price_adjustment_method": "Distribution/split/terminal-return treatment",
    "eps_basis_method": "Currency, GAAP/adjusted, share basis and vintage treatment",
    "availability_method": "Meaning and source of historical availability timestamps"
  },
  "sessions": [],
  "securities": [],
  "prices": [],
  "universes": [],
  "actuals": [],
  "estimates": []
}
```

This is a schema illustration, **not usable data**. Empty tables are rejected.
An export timestamp must be real, cannot precede its records' availability, and
cannot be in the future. All timestamps require explicit UTC offsets; dates
without release times are not silently assumed to be available before trading.
Unknown/missing economic values must not be filled with zero or passing defaults.

### sessions

Required fields per row: `date` (YYYY-MM-DD), `close_at`, `decision_at` (timestamps).
Rows are unique and sorted. Decision must be after close and before the next
session. Include actual US exchange hours, daylight saving and early closes;
synthetic weekday calendars are suitable for unit tests only.

### securities

Required: `sid`, `kind`, `currency`, `label`. `sid` is a permanent security-level
identifier, not a reusable ticker. `kind` is `common_stock` or `benchmark`;
currency is `USD`. The QQQ benchmark must have the reserved ID `QQQ` and kind
`benchmark`; its display ticker is not used for stock-universe linking.

### prices

Required: `sid`, `date`, `available_at`, `tr_index`, `raw_close`, `dollar_volume`,
`tradable`, `terminal`. One row per security/session; the session must exist.

- `tr_index`: positive total-return index in consistent synthetic units. It
  must already include distributions/fees embedded in fund prices and corporate
  actions. No extra dividends are credited by the engine.
- `raw_close`: actual historical unadjusted USD close, used for the minimum-price
  eligibility screen, not a modern split-adjusted substitute.
- `dollar_volume`: historical USD traded notional, not volume multiplied by a
  mismatched modern adjusted close. Liquidity uses the prior 20 observed sessions.
- `available_at`: when the closing observation could be used, no earlier than
  that session's close. Late records cannot inform earlier decisions.
- `tradable`: explicit boolean for the modeled close. A suspended security can
  have a valuation mark while being unavailable for fills.
- `terminal`: explicit boolean for the **final settlement** record. It must be
  nontradable and the last row for that stable ID. Its `tr_index` is the final
  cash-settlement value per synthetic index unit; zero is permitted for total
  loss. Do not replace a missing delisting outcome with zero without evidence.

Terminal payoff is marked into NAV and transferred to cash. This assumes the
provided settlement session is the actual cash-availability session. Prior
nontradable sessions still require defensible marks. Missing held marks abort
the simulation rather than dropping a holding or inventing a fill. Do not
double-count a delisting return already embedded in another vendor return field.

QQQ must have a timely nonterminal quote on every session. All historical
universe members require timely marks during evaluation, except after a known
terminal settlement. Stock signals additionally require contiguous history;
new listings remain ineligible until their warmup is available.

### universes

Required: `asof_at`, `available_at`, `source_ref`, `members`.
Each member is `{ "sid": "stable-id", "sector": "historical-sector" }`.
Use historical common-stock membership, including later failures, with unique
IDs and sector classifications known then. Supply at least monthly snapshots:
the latest usable `asof_at` cannot be more than 35 calendar days old. Corrections
need their own availability timestamp; do not overwrite the original vintage.

### actuals

Required: `sid`, `event_id`, `period_end`, `announced_at`, `available_at`, `eps`,
`basis_id`, `currency`, `version`, `source_ref`.

`period_end` identifies the exact fiscal quarter, not a calendar-quarter guess.
`version=0` is the original reported actual. Later corrections have greater
versions under the same event identity and are never substituted into the
original earnings-surprise signal. Exactly one initial event per security/fiscal
period is permitted. EPS can be negative; it cannot be null/NaN/infinite.

### estimates

Required: `sid`, `period_end`, `period_type`, `asof_at`, `available_at`, `eps`,
`basis_id`, `currency`, `source_ref`.

`period_type` is `quarter` or `annual`. Both snapshot/as-of and actual historical
availability timestamps are needed; `asof_at <= available_at`. A forecast that
arrived after the earnings release is not eligible consensus even if backdated.
EPS must be USD and the compared records must have identical `basis_id` values.
The basis must encode compatible accounting and per-share treatment; copying a
generic label onto incompatible series does not make them comparable.

For revisions, the engine selects the nearest future annual fiscal period among
available estimates and compares it with the latest available snapshot of that
**same period and basis** at least 21 sessions earlier. Current and baseline
snapshots have 45-calendar-day freshness limits relative to their respective
cutoffs. A missing match excludes the signal; no year-roll substitution occurs.

## Human review is a separate requirement

Copy `review_template.json` into the private directory and complete it only
after checking the actual export. Hash the exact input bytes with:

```powershell
(Get-FileHash research/strategy34/private/bundle.json -Algorithm SHA256).Hash.ToLower()
```

The review must match that SHA256, identify its reviewer/date, include coverage
notes, and explicitly affirm every listed check. Changing even one byte of the
bundle invalidates the old review. Review time must follow the export. Do not
check boxes merely to get a green result: these attestations cannot independently
prove source quality. Provider methodology, record samples and historical joins
still need inspection. Fees/licensing and any needed purchase require a separate
user decision; none has been authorized or performed here.
