"""Authoritative catalogue for scheduled strategies and portfolio files.

Rescue 2026-11-12: only the 6 strategies that passed the honest-evidence
review still run. The other 22 were archived to _archive/ (see
RESCUE_2026-11-12.md); their runners, ledgers and portfolios no longer exist
at the repo root, so they are not listed here. Do not re-add a strategy
without a verified ledger reconciliation (criterion C5) and a graduation
report entry.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategySpec:
    key: str
    label: str
    runner: str
    portfolio_file: str
    currency: str  # Currency of cash_balance and holding prices.
    active: bool = True
    composite: bool = False  # Derived from other books; exclude from deployable NAV.


STRATEGIES = (
    StrategySpec("s2", "1d MACD Systematic", "ingest_live_macd.py", "portfolio_macd.json", "MXN"),
    StrategySpec("s4", "US DCF Value-Growth", "run_live_alpaca_us_stocks_dcf.py", "portfolio_us_dcs.json", "USD"),
    StrategySpec("s8", "Dividend Quality", "run_live_dividends.py", "portfolio_dividends.json", "MXN"),
    StrategySpec("s12", "VTTL Trend+Vol", "run_live_strategy12.py", "portfolio_strategy12.json", "MXN"),
    StrategySpec("s14", "HEDGE Aggregator", "run_live_strategy14.py", "portfolio_strategy14.json", "MXN"),
    StrategySpec("s15", "TRACK Tracker", "run_live_strategy15.py", "portfolio_strategy15.json", "MXN"),
)

STRATEGY_SCRIPTS = (
    "monitor_portfolio.py",
    *(spec.runner for spec in STRATEGIES),
    "reconcile_strategy_navs.py", "graduation_report.py", "watchdog.py",
)
BY_PORTFOLIO_FILE = {spec.portfolio_file: spec for spec in STRATEGIES}
BY_RUNNER = {spec.runner: spec for spec in STRATEGIES}
