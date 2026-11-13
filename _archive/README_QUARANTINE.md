# Quarantined: reconcile_all_transactions.py

Moved here 2026-11-12 (Rescue). DO NOT RUN.

Why: this script fabricates accounting evidence. It overwrites portfolio
JSONs with NAV taken from watchdog history, hardcodes NAV values, invents
an initial-deposit row when none exists (`ensure_initial_deposit_entry`),
and stamps results `[TRUE_PROFIT_VERIFIED]`.

ACCOUNTING_REVIEW_FOLLOWUP.md forbids inventing transactions: "A missing
fill, opening balance, or FX transfer cannot be repaired by inventing a
transaction."

Status: dead code. It is not in STRATEGY_SCRIPTS (strategy_registry.py)
and the pipeline only runs reconcile_strategy_navs.py (monitor.yml).
It was quarantined so nobody runs it by hand. The audit-only reconciler
(reconcile_strategy_navs.py) is the only reconciliation tool.
