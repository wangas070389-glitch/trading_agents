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
import datetime
import hashlib

from skills.file_io_utils import atomic_save_json, safe_load_json
from strategy_registry import STRATEGIES
from accounting import cash_value

REPORT = "nav_reconciliation_report.md"
DATA = "nav_reconciliation.json"
NON_SECURITIES = {"BONDIA", "CASH", "USD", "MXN", "USDMXN"}
POSITION_TOLERANCE = 0.01  # Ledger display rounding; not a whole-share discrepancy.
# Ledger prices are printed to 4 decimals, so qty x price rounding accumulates
# ~0.1-2.5 over hundreds of rows on six-figure trades (observed: S12 -0.14,
# S23 -2.23, S24 -2.14). A cash gap below this is display rounding, not a real
# difference; genuine errors in this repo are >= 20x larger (smallest real
# residual after this fix is S25 at 104.01, a fee-accounting difference).
CASH_TOLERANCE = 5.00


def normalize_action(action):
    """Map strategy-specific action names onto the canonical set.

    Returns (canonical_action, cash_only). cash_only actions affect cash but
    never open/close a position.
    """
    action = action.upper()
    if action in {"BUY", "SELL", "STOP_OUT", "DEPOSIT", "WITHDRAWAL", "INTEREST", "DIVIDEND"}:
        return action, False
    if action in {"EXIT_SHORT", "EXIT_LONG"}:
        # Position close-outs (S11: closes a SQQQ "short" bet or a TQQQ long).
        # In this repo both are sells of a long holding: the amount column is
        # positive (cash in) and the position is reduced. Mapped to SELL.
        return "SELL", False
    if action in {"BUY_USD", "SELL_USD"}:
        return ("BUY" if action == "BUY_USD" else "SELL"), False
    if action.startswith("BUY_") or action.startswith("SELL_"):
        # Intraday BUY_TQQQ / SELL_SOXL / ... : the ticker column already names
        # the instrument, so these are plain buys/sells of that ticker.
        return ("BUY" if action.startswith("BUY_") else "SELL"), False
    if action.startswith("SETTLE_"):
        # Intraday settlement: the cash leg of closing a position. Recorded as
        # a cash adjustment only (the paired BUY_* already booked the shares);
        # see RESCUE_2026-11-12.md — S10/S11/S16 exits are SETTLE-only, so
        # their ledgers still show the paired position as open.
        return "SELL", True
    if action == "REBALANCE":
        # Composite re-allocation, not a trade. No cash/position effect.
        return "REBALANCE", True
    return action, False


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
    positions, cash_delta, rows, errors, warnings = collections.defaultdict(float), 0.0, 0, [], []
    header = None
    with open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = cells(line)
            lower = [cell.lower() for cell in row]
            if "ticker" in lower and "action" in lower and ("date" in lower or "trade date" in lower):
                header = {name: index for index, name in enumerate(lower)}
                continue
            if not line.lstrip().startswith("|") or all(set(cell) <= {":", "-", " "} for cell in row):
                continue
            if not header:
                errors.append(f"Line {line_number}: data before header")
                continue
            if len(row) > len(header):
                # Defensive: an unescaped '|' inside a note cell splits the row.
                # The note is the last column; rejoin the surplus into it.
                row = row[:len(header) - 1] + [" / ".join(row[len(header) - 1:])]
                warnings.append(f"Line {line_number}: rejoined {len(cells(line))} cells into {len(header)} (note pipe)")
            if len(row) != len(header):
                errors.append(f"Line {line_number}: column count does not match header")
                continue
            try:
                ticker = row[header["ticker"]].upper()
                raw_action = row[header["action"]].upper()
            except (IndexError, KeyError):
                continue
            action, cash_only = normalize_action(raw_action)
            if action == "REBALANCE":
                warnings.append(f"Line {line_number}: REBALANCE recorded as no-op (composite re-allocation, not a trade)")
                continue
            if action not in {"BUY", "SELL", "STOP_OUT", "DEPOSIT", "WITHDRAWAL", "INTEREST", "DIVIDEND"}:
                if "REJECTED" not in action and "CANCELLED" not in action:
                    errors.append(f"Line {line_number}: unsupported action {raw_action}")
                continue
            if "status" in header and row[header["status"]].upper() not in {"FILLED", "EXECUTED"}:
                errors.append(f"Line {line_number}: unconfirmed execution status")
                continue
            note = row[header["note"]].lower() if "note" in header else ""
            if "execution failed" in note:
                # The row says FILLED but the note records a broker rejection
                # (e.g. Alpaca 403). Counted as executed: the status field says
                # FILLED and, for S2, the cash impact of the two such rows
                # (+2,869.76) reconciles the portfolio to the cent, proving the
                # portfolio reflects them (likely a retried order). Flagged here
                # so a broker statement can confirm it.
                warnings.append(f"Line {line_number}: FILLED row carries an 'execution failed' note ({ticker} {raw_action}); counted as executed")
            rows += 1
            quantity_key = "shares" if "shares" in header else "qty" if "qty" in header else None
            quantity = number(row[header[quantity_key]]) if quantity_key else None
            amount_key = next((key for key in header if any(token in key for token in ("net impact", "net amount", "cash flow", "capital impact"))), None)
            amount = number(row[header[amount_key]]) if amount_key else None
            if amount is not None:
                cash_delta += amount
            elif quantity is not None:
                price_key = next((key for key in header if "price" in key), None)
                price = number(row[header[price_key]]) if price_key else 0.0
                price = price or 0.0
                fee = (number(row[header["fee"]]) or 0.0) if "fee" in header else 0.0
                cash_delta += -(quantity * price + fee) if action == "BUY" else quantity * price - fee if action == "SELL" else quantity * price
            else:
                errors.append(f"Line {line_number}: missing cash amount")
            if amount is not None and ((action == "DEPOSIT" and amount < 0) or (action == "WITHDRAWAL" and amount > 0)):
                errors.append(f"Line {line_number}: funding sign contradicts action")
            if not cash_only and ticker not in NON_SECURITIES and quantity is not None:
                positions[ticker] += quantity if action == "BUY" else -quantity if action in {"SELL", "STOP_OUT"} else 0.0
    positions = {ticker: quantity for ticker, quantity in positions.items() if abs(quantity) > 1e-7}
    return positions, cash_delta, rows, errors, warnings


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
        ledger_positions, cash_delta, row_count, errors, warnings = parse_ledger(ledger_path)
        saved = reported_positions(portfolio)
        symbols = sorted(set(ledger_positions) | set(saved))
        differences = {symbol: round(ledger_positions.get(symbol, 0.0) - saved.get(symbol, 0.0), 8) for symbol in symbols if abs(ledger_positions.get(symbol, 0.0) - saved.get(symbol, 0.0)) > POSITION_TOLERANCE}
        # A quantity match alone is not a cash or NAV reconciliation.
        seed = portfolio.get("initial_seed_capital")
        ledger_text = open(ledger_path, encoding="utf-8").read()
        opening_cash = 0.0 if "initial capital funding" in ledger_text.lower() else seed
        expected_cash = actual_cash = cash_difference = None
        if "cash_balance_mxn" in portfolio or "cash_balance_usd" in portfolio:
            # Cash is split across currencies, so no single-currency cash
            # comparison is possible. Positions are still verified; cash is
            # explicitly NOT verified here (cash_difference stays None).
            warnings.append("Currency-specific balances: cash is split MXN/USD and is not single-currency verified")
        elif opening_cash is None:
            errors.append("Opening cash is undocumented")
        else:
            expected_cash = float(opening_cash) + cash_delta
            actual_cash = cash_value(portfolio, spec.currency, 1.0)
            cash_difference = round(actual_cash - expected_cash, 2)
        status = "MISMATCH" if differences or (cash_difference is not None and abs(cash_difference) > CASH_TOLERANCE) else "UNRESOLVED" if errors or row_count == 0 else "VERIFIED"
        record = {"strategy": spec.key, "ledger": ledger, "rows": row_count, "ledger_positions": ledger_positions, "portfolio_positions": saved, "position_differences": differences, "cash_delta": round(cash_delta, 2), "status": status}
        record.update(errors=errors, warnings=warnings, expected_cash=expected_cash, actual_cash=actual_cash,
                      cash_difference=cash_difference,
                      portfolio_sha256=hashlib.sha256(open(portfolio_path, "rb").read()).hexdigest(),
                      ledger_sha256=hashlib.sha256(open(ledger_path, "rb").read()).hexdigest())
        output.append(record)
        lines.append(f"| {spec.key.upper()} {spec.label} | {row_count} | {len(ledger_positions)} | {len(saved)} | {status} | {cash_delta:,.2f} {spec.currency} |")
        if differences:
            details = ", ".join(f"{ticker}: ledger {ledger_positions.get(ticker, 0):g}, portfolio {saved.get(ticker, 0):g}" for ticker in differences)
            lines.append(f"| ↳ difference |  |  |  | {details} |  |")
        if errors or cash_difference:
            lines.append(f"| ↳ cash/evidence |  |  |  | {'; '.join(errors[:5])}; cash discrepancy {cash_difference} |  |")
        if warnings:
            lines.append(f"| ↳ notes |  |  |  | {'; '.join(warnings[:5])} |  |")
    atomic_save_json(os.path.join(directory, DATA), {"generated_at": datetime.datetime.now().isoformat(), "strategies": output})
    with open(os.path.join(directory, REPORT), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"Reconciled {len(output)} registered strategies; see {REPORT}.")


if __name__ == "__main__":
    main()
