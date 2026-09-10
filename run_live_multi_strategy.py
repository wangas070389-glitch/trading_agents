"""Consolidate every registered paper portfolio into an auditable NAV view.

Reporting only: this never moves capital, rebalances, or submits orders.
"""
from __future__ import annotations

import datetime as dt
import math
import os

import pandas as pd
import yfinance as yf

from skills.file_io_utils import atomic_save_json, safe_load_json
from strategy_registry import STRATEGIES
from accounting import nav_value, valuation_price

PORTFOLIO_FILE = "portfolio_multi_strategy.json"
REPORT_FILE = "multi_strategy_report_live.md"
CSV_FILE = "consolidated_portfolio_nav.csv"
FALLBACK_USD_MXN = 17.43


def get_nav(portfolio):
    """Legacy interface: native MXN valuation, plus a separate USD cash leg."""
    native = dict(portfolio)
    usd = _finite(native.get("cash_balance_usd"))
    if "cash_balance_usd" in native:
        native["cash_balance_usd"] = 0.0
    total, cash = nav_value(native, "MXN", 1.0)
    return total, cash, usd


def _finite(value, default=0.0):
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _price(holding):
    for field in ("last_price", "current_price", "buy_price"):
        value = _finite(holding.get(field), 0.0)
        if value > 0:
            return value
    return 0.0


def _native_nav(portfolio, currency):
    if currency == "USD" and _finite(portfolio.get("total_portfolio_value_usd")) > 0:
        return _finite(portfolio["total_portfolio_value_usd"]), _finite(portfolio.get("total_cash_balance_usd"))
    cash = _finite(portfolio.get("cash_balance")) + _finite(portfolio.get("cash_balance_mxn"))
    holdings = sum(_finite(h.get("shares")) * _price(h) for h in portfolio.get("holdings", []) if isinstance(h, dict))
    return cash + holdings, cash


def _fx_rate():
    try:
        data = yf.download("USDMXN=X", period="5d", progress=False, auto_adjust=False)
        value = _finite(data["Close"].dropna().iloc[-1])
        if value > 0:
            return value, False
    except Exception:
        pass
    return FALLBACK_USD_MXN, True


def _load_rows(directory, rate):
    rows = []
    reconciliation = safe_load_json(os.path.join(directory, "nav_reconciliation.json"), default={}) or {}
    statuses = {r["strategy"]: r["status"] for r in reconciliation.get("strategies", [])}
    for spec in STRATEGIES:
        portfolio = safe_load_json(os.path.join(directory, spec.portfolio_file))
        if not isinstance(portfolio, dict):
            rows.append({"key": spec.key, "label": spec.label, "currency": spec.currency, "status": "missing/unreadable", "nav_usd": 0.0, "cash_usd": 0.0})
            continue
        native_nav, native_cash = nav_value(portfolio, spec.currency, rate)
        if spec.composite:
            native_nav, native_cash = _native_nav(portfolio, spec.currency)
        multiplier = 1.0 if spec.currency == "USD" else 1.0 / rate
        usd_cash_extra = 0.0  # Already included by the shared valuation function.
        rows.append({"key": spec.key, "label": spec.label, "currency": spec.currency, "composite": spec.composite, "status": statuses.get(spec.key, "UNRESOLVED") + "; marks unverified", "nav_usd": native_nav * multiplier + usd_cash_extra, "cash_usd": native_cash * multiplier + usd_cash_extra})
    return rows


def _performance(history):
    values = [entry.get("nav_usd", 0.0) for entry in history if _finite(entry.get("nav_usd")) > 0]
    if len(values) < 2:
        return {"return_pct": 0.0, "max_drawdown_pct": 0.0}
    series = pd.Series(values, dtype=float)
    return {"return_pct": (series.iloc[-1] / series.iloc[0] - 1.0) * 100.0, "max_drawdown_pct": ((series / series.cummax() - 1.0).min()) * 100.0}


def main():
    directory = os.path.dirname(os.path.abspath(__file__))
    today = dt.date.today().isoformat()
    rate, used_fallback = _fx_rate()
    rows = _load_rows(directory, rate)
    # Composite strategies are valuable research benchmarks but own sleeves
    # already represented by standalone books.  Including them as capital
    # would double-count exposure.
    deployable_rows = [r for r in rows if not r.get("composite")]
    total_nav, total_cash = sum(r["nav_usd"] for r in deployable_rows), sum(r["cash_usd"] for r in deployable_rows)
    gross_research_nav = sum(r["nav_usd"] for r in rows)
    state = safe_load_json(os.path.join(directory, PORTFOLIO_FILE), default={}) or {}
    history = state.get("history", [])
    entry = {"date": today, "nav_usd": total_nav, "cash_usd": total_cash, "accounting_version": 2, "verified": False}
    entry.update({f"{r['key']}_nav_usd": r["nav_usd"] for r in rows})
    if history and history[-1].get("date") == today:
        history[-1] = entry
    else:
        history.append(entry)
    history = history[-500:]
    state = {"total_portfolio_value_usd": total_nav, "total_cash_balance_usd": total_cash, "gross_research_nav_usd": gross_research_nav, "last_updated": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "usd_mxn_rate": rate, "reporting_scope": "independent paper books; composite strategies excluded to avoid double-counting", "history": history, "allocations": {r["key"]: {"nav_usd": r["nav_usd"], "cash_usd": r["cash_usd"], "current_weight": r["nav_usd"] / total_nav if total_nav and not r.get("composite") else 0.0, "composite": r.get("composite", False)} for r in rows}, "performance": _performance(history)}
    state["performance"] = {"return_pct": None, "max_drawdown_pct": None,
                            "status": "Unavailable: historical accounting and cash flows need validation"}
    state["valuation_status"] = "UNVERIFIED; arithmetic estimates only"
    atomic_save_json(os.path.join(directory, PORTFOLIO_FILE), state)
    lines = [f"# Consolidated Paper-Portfolio NAV — {today}", "", "The total below excludes composite strategies so it does not double-count their underlying sleeves. This remains paper-trading reporting, not a brokerage NAV.", "", f"USD/MXN: {rate:.4f}" + (" (fallback; market-data fetch failed)" if used_fallback else ""), "", "| Strategy | Currency | NAV (USD) | Cash (USD) | Weight | Status |", "| :--- | :---: | ---: | ---: | ---: | :--- |"]
    for row in rows:
        weight = row["nav_usd"] / total_nav * 100 if total_nav and not row.get("composite") else 0.0
        status = "composite — excluded from total" if row.get("composite") else row["status"]
        lines.append(f"| {row['key'].upper()} {row['label']} | {row['currency']} | ${row['nav_usd']:,.2f} | ${row['cash_usd']:,.2f} | {weight:.2f}% | {status} |")
    lines.extend(["", "**UNVERIFIED ESTIMATES:** these balances are not ledger-certified NAV or investment profits. Historical returns are withheld pending reconstruction.", "", f"**Independent-book NAV estimate:** ${total_nav:,.2f}", f"**Independent-book cash estimate:** ${total_cash:,.2f}", f"**Gross research NAV estimate (includes composites):** ${gross_research_nav:,.2f}"])
    with open(os.path.join(directory, REPORT_FILE), "w", encoding="utf-8") as report:
        report.write("\n".join(lines) + "\n")
    pd.DataFrame(history)[["date", "nav_usd", "cash_usd"]].rename(columns={"date": "Date", "nav_usd": "NAV_USD", "cash_usd": "Cash_USD"}).to_csv(os.path.join(directory, CSV_FILE), index=False)
    print(f"Consolidated {len(rows)} registered strategies: NAV ${total_nav:,.2f} USD")


if __name__ == "__main__":
    main()
