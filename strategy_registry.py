"""Authoritative catalogue for scheduled strategies and portfolio files."""

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
    StrategySpec("s1", "Adaptive Value", "run_live_alpha_growth.py", "portfolio.json", "MXN"),
    StrategySpec("s2", "1d MACD Systematic", "ingest_live_macd.py", "portfolio_macd.json", "MXN"),
    StrategySpec("s3", "US Stock Momentum", "run_live_alpaca_us_stocks.py", "portfolio_us_stocks.json", "USD"),
    StrategySpec("s4", "US DCF Value-Growth", "run_live_alpaca_us_stocks_dcf.py", "portfolio_us_dcs.json", "USD"),
    StrategySpec("s5", "Alternative Assets", "run_live_alternatives.py", "portfolio_alternatives.json", "USD"),
    StrategySpec("s6", "High-Beta Momentum", "run_live_high_beta.py", "portfolio_high_beta.json", "USD"),
    StrategySpec("s8", "Dividend Quality", "run_live_dividends.py", "portfolio_dividends.json", "MXN"),
    StrategySpec("s9", "AI Regime Stat-Arb", "run_live_strategy9.py", "portfolio_strategy9.json", "MXN"),
    StrategySpec("s10", "Intraday VWAP", "run_live_strategy10.py", "portfolio_strategy10.json", "MXN"),
    StrategySpec("s11", "Intraday CCI-ADX", "run_live_strategy11.py", "portfolio_strategy11.json", "MXN"),
    StrategySpec("s12", "VTTL Trend+Vol", "run_live_strategy12.py", "portfolio_strategy12.json", "MXN"),
    StrategySpec("s13", "CARA Cross-Asset", "run_live_strategy13.py", "portfolio_strategy13.json", "MXN"),
    StrategySpec("s14", "HEDGE Aggregator", "run_live_strategy14.py", "portfolio_strategy14.json", "MXN"),
    StrategySpec("s15", "TRACK Tracker", "run_live_strategy15.py", "portfolio_strategy15.json", "MXN"),
    StrategySpec("s16", "HMM Intraday Router", "run_live_strategy16.py", "portfolio_strategy16.json", "MXN"),
    StrategySpec("s17", "FIBRAs Dynamic", "run_live_strategy17.py", "portfolio_strategy17.json", "MXN"),
    StrategySpec("s18", "Efficient Frontier", "run_live_strategy18.py", "portfolio_strategy18.json", "USD", composite=True),
    StrategySpec("s19", "Particle Filter QQQ", "run_live_strategy19.py", "portfolio_strategy19.json", "MXN"),
    StrategySpec("s20", "Hurst Exponent Dynamic", "run_live_strategy20.py", "portfolio_strategy20.json", "MXN"),
    StrategySpec("s21", "Shannon Entropy Dynamic", "run_live_strategy21.py", "portfolio_strategy21.json", "MXN"),
    StrategySpec("s22", "Walk-Forward ML", "run_live_strategy22.py", "portfolio_strategy22.json", "MXN"),
    StrategySpec("s23", "Calculus S&R", "run_live_strategy23.py", "portfolio_strategy23.json", "MXN"),
    StrategySpec("s24", "30m Random Forest", "run_live_strategy24.py", "portfolio_strategy24.json", "MXN"),
    StrategySpec("s25", "Golden MACD BMV", "run_live_strategy25.py", "portfolio_strategy25.json", "MXN"),
    StrategySpec("s27", "Golden Hurst", "run_live_strategy27.py", "portfolio_strategy27.json", "MXN"),
    StrategySpec("s29", "Golden Stat-Arb", "run_live_strategy29.py", "portfolio_strategy29.json", "MXN"),
    StrategySpec("s30", "Golden MACD US", "run_live_strategy30.py", "portfolio_strategy30.json", "USD"),
    StrategySpec("s31", "Fibonacci S&R", "run_live_strategy31.py", "portfolio_strategy31.json", "MXN"),
)

STRATEGY_SCRIPTS = (
    "monitor_portfolio.py",
    *(spec.runner for spec in STRATEGIES),
    "reconcile_strategy_navs.py", "run_live_multi_strategy.py", "shadow_frontier.py", "compare_strategies.py",
    "generate_clean_report.py", "graduation_report.py", "watchdog.py",
)
BY_PORTFOLIO_FILE = {spec.portfolio_file: spec for spec in STRATEGIES}
BY_RUNNER = {spec.runner: spec for spec in STRATEGIES}
