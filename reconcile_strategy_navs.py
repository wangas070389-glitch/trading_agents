"""Ledger-first NAV reconciliation for every registered paper strategy.

This tool is deliberately audit-only: a malformed or incomplete ledger must
not overwrite a portfolio.  It produces the exact discrepancies that require
an approved correction.
"""
from __future__ import annotations

import collections
import json
import math
import os
import re

from skills.file_io_utils import atomic_save_json, safe_load_json
from strategy_registry import STRATEGIES

REPORT = "nav_reconciliation_report.md"
DATA = "nav_reconciliation.json"
NON_SECURITIES = {"BONDIA", "CASH", "USD", "MXN"}
POSITION_TOLERANCE = 0.01  # Ledger display rounding; not a whole-share discrepancy.


def number(value):
    if value is None:
        return None
    cleaned = str(value).replace("$", "").replace(",", "").replace("+", "").strip()
    try:
        result = float(cleaned)
        return result if math.isfinite(result) else None
    except ValueError:
        return None


def ledger_name(spec):
    if spec.key == "s1":
        return "transactions.md"
    if spec.key == "s2":
        return "transactions_macd.md"
    if spec.key == "s3":
        return "transactions_us_stocks.md"
    if spec.key == "s4":
        return "transactions_us_dcs.md"
    if spec.key == "s5":
        return "transactions_alternatives.md"
    if spec.key == "s6":
        return "transactions_high_beta.md"
    if spec.key == "s8":
        return "transactions_dividends.md"
    return f"transactions_strategy{spec.key[1:]}.md"


def cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_ledger(path):
    """Extract filled trade quantities and recorded cash flow from any ledger table."""
    positions, cash_delta, rows, errors = collections.defaultdict(float), 0.0, 0, []
    header = None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            row = cells(line)
            lower = [cell.lower() for cell in row]
            if "ticker" in lower and "action" in lower and ("date" in lower or "trade date" in lower):
                header = {name: index for index, name in enumerate(lower)}
                continue
            if not header or not line.lstrip().startswith("|") or all(set(cell) <= {":", "-", " "} for cell in row):
                continue
            try:
                ticker = row[header["ticker"]].upper()
                action = row[header["action"]].upper()
            except (IndexError, KeyError):
                continue
            if action not in {"BUY", "SELL", "STOP_OUT", "DEPOSIT", "WITHDRAWAL", "INTEREST", "DIVIDEND"}:
                continue
            rows += 1
            quantity_key = "shares" if "shares" in header else "qty" if "qty" in header else None
            quantity = number(row[header[quantity_key]]) if quantity_key else None
            amount_key = next((key for key in header if any(token in key for token in ("net impact", "net amount", "cash flow", "capital impact"))), None)
            amount = number(row[header[amount_key]]) if amount_key else None
            if amount is not None:
                cash_delta += amount
            elif quantity is not None and "price" in header:
                price = number(row[header["price"]]) or 0.0
                fee = number(row[header.get("fee", -1)]) or 0.0
                cash_delta += -(quantity * price + fee) if action == "BUY" else quantity * price - fee if action == "SELL" else quantity * price
            if ticker not in NON_SECURITIES and quantity is not None:
                positions[ticker] += quantity if action == "BUY" else -quantity if action in {"SELL", "STOP_OUT"} else 0.0
    positions = {ticker: quantity for ticker, quantity in positions.items() if abs(quantity) > 1e-7}
    return positions, cash_delta, rows, errors


def reported_positions(portfolio):
    return {str(h.get("ticker", "")).upper(): float(h.get("shares", 0.0)) for h in portfolio.get("holdings", []) if h.get("ticker")}


def main():
    directory = os.path.dirname(os.path.abspath(__file__))
    output, lines = [], ["# Ledger-first NAV Reconciliation", "", "Audit-only: no portfolio JSON was changed. `Cash delta` is the sum recorded by each ledger; position differences must be resolved before using a ledger as authoritative.", "", "| Strategy | Ledger rows | Ledger positions | Portfolio positions | Position status | Cash delta |", "| :--- | ---: | ---: | ---: | :--- | ---: |"]
    for spec in STRATEGIES:
        ledger = ledger_name(spec)
        ledger_path, portfolio_path = os.path.join(directory, ledger), os.path.join(directory, spec.portfolio_file)
        portfolio = safe_load_json(portfolio_path, default={}) or {}
        if not os.path.exists(ledger_path):
            record = {"strategy": spec.key, "ledger": ledger, "status": "MISSING LEDGER"}
            output.append(record)
            lines.append(f"| {spec.key.upper()} {spec.label} | — | — | {len(reported_positions(portfolio))} | MISSING LEDGER | — |")
            continue
        ledger_positions, cash_delta, row_count, errors = parse_ledger(ledger_path)
        saved = reported_positions(portfolio)
        symbols = sorted(set(ledger_positions) | set(saved))
        differences = {symbol: round(ledger_positions.get(symbol, 0.0) - saved.get(symbol, 0.0), 8) for symbol in symbols if abs(ledger_positions.get(symbol, 0.0) - saved.get(symbol, 0.0)) > POSITION_TOLERANCE}
        status = "MATCH" if not differences else "MISMATCH"
        record = {"strategy": spec.key, "ledger": ledger, "rows": row_count, "ledger_positions": ledger_positions, "portfolio_positions": saved, "position_differences": differences, "cash_delta": round(cash_delta, 2), "status": status}
        output.append(record)
        lines.append(f"| {spec.key.upper()} {spec.label} | {row_count} | {len(ledger_positions)} | {len(saved)} | {status} | {cash_delta:,.2f} {spec.currency} |")
        if differences:
            details = ", ".join(f"{ticker}: ledger {ledger_positions.get(ticker, 0):g}, portfolio {saved.get(ticker, 0):g}" for ticker in differences)
            lines.append(f"| ↳ difference |  |  |  | {details} |  |")
    atomic_save_json(os.path.join(directory, DATA), {"strategies": output})
    with open(os.path.join(directory, REPORT), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"Reconciled {len(output)} registered strategies; see {REPORT}.")


if __name__ == "__main__":
    main()
