# Accounting review follow-up

The previous performance ranking is withdrawn. The legacy reports mixed initial funding with later deposits and added overlapping cash fields. Ledger position matches did not certify cash or valuation history.

## Implemented

- Pytest discovery is limited to tests/. The scheduled test step receives no Alpaca credentials.
- Currency-specific cash supersedes legacy cash in consolidated and graduation valuations.
- Initial funding is excluded from subsequent contributions; strategy resets filter earlier contributions.
- Ledger audits expose malformed records, unsupported actions, funding sign contradictions, and ending cash discrepancies. Source hashes invalidate stale audit results.
- Graduation requires explicit risk passes and verified, versioned native-currency history. Blocked strategies have their performance claims withheld.
- Historical cash-flow adjustment uses interval-end external flows, never raw deposit-driven NAV changes.

## Remaining evidence and reconstruction

The audit is deliberately non-mutating. A missing fill, opening balance, or FX transfer cannot be repaired by inventing a transaction. The JSON audit retains all parser errors and partial balance differences; these differences are not certified losses or proposed adjustment amounts.

1. Resolve ledger schema drift: initial-funding rows in several Golden ledgers have different column layouts; some order notes contain unescaped table separators.
2. Add explicit event adapters for BUY_USD/SELL_USD, intraday BUY_* and SETTLE_* actions. Reconcile each currency and instrument independently.
3. Verify opening balances, shared-account allocations, duplicate fills, and contradictory deposit signs against original execution/funding evidence. Persist corrections as traceable events.
4. Reconstruct daily quantities, cash, corporate actions and valuation marks. Only certified snapshots may carry verified=true, accounting_version=2, and their native currency. Retain provenance for each source and price.
5. Regenerate graduation after reconstructed histories pass accounting invariants. Do not promote a strategy by merely waiting for its inception date to age.
6. Run frozen baseline/challenger comparisons only after evidence is reliable; include costs, turnover, untouched evaluation periods and cash/market benchmarks. No strategy optimization or capital allocation has been approved by these reports.

S8 and S12 currently match audited cash/positions within one cent; that does not certify historical returns or current market prices. Other books remain mismatched or incomplete. The consolidation is an arithmetic estimate and is explicitly unverified.
