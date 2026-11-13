"""Normalize trading_agents ledger Markdown (Rescue 2026-11-12).

Fixes, all traceable to the values already recorded in the ledgers
(nothing is invented):
  1. Unescaped '|' inside order-note cells: rows with MORE cells than the
     header are re-joined so the note keeps its text with ' / ' separators.
  2. Initial-funding rows (DEPOSIT + 'Initial capital funding') that were
     written one column short: the amount sat in the Order Type column and
     the note in the Status column. Rebuilt in the correct layout with the
     amount in the amount column, Order Type 'Market', Status 'FILLED'.
  3. Monthly DEPOSIT rows recorded with a negative amount (funding sign
     contradicts the action): sign flipped to positive.
  4. S1 (transactions.md): one BONDIA INTEREST row sat above the header
     ('data before header'); moved into the table in date order.

Idempotent: a second run finds nothing to change.
Backups are written to _archive/ledger_backups_2026-11-12/ before any edit.
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(ROOT, "_archive", "ledger_backups_2026-11-12")

AMOUNT_TOKENS = ("net impact", "net amount", "cash flow", "capital impact")


def split_cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def join_row(cells):
    return "| " + " | ".join(cells) + " |"


def parse_number(text):
    cleaned = str(text).replace("$", "").replace(",", "").replace("+", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def fmt_money(value, template):
    """Render a money value keeping the template's style ($ and commas)."""
    sign = "+" if value >= 0 else "-"
    body = f"{abs(value):,.2f}"
    if "$" in template:
        return f"{sign}${body}" if template.strip().startswith(("+", "-")) else f"${body}" if value >= 0 else f"-${body}"
    return f"{sign}{body}" if template.strip().startswith(("+", "-")) else body


def normalize_file(path, log):
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()

    # Locate the header row.
    header_idx = None
    header = None
    for i, line in enumerate(lines):
        row = split_cells(line)
        low = [c.lower() for c in row]
        if "ticker" in low and "action" in low and ("date" in low or "trade date" in low):
            header_idx, header = i, row
            break
    if header_idx is None:
        log.append(f"{os.path.basename(path)}: NO HEADER, skipped")
        return False

    ncols = len(header)
    lower_header = [c.lower() for c in header]
    amount_idx = next((i for i, name in enumerate(lower_header)
                       if any(tok in name for tok in AMOUNT_TOKENS)), None)
    # Rows that appear before the header (S1 stray row): collect and re-insert.
    stray_rows = []
    out = []
    changed = False

    def process_data_row(line, lineno):
        nonlocal changed
        row = split_cells(line)
        if len(row) == ncols:
            # Correct column count; only check DEPOSIT sign.
            if amount_idx is not None:
                action = row[lower_header.index("action")].upper() if "action" in lower_header else ""
                if action == "DEPOSIT":
                    amt = parse_number(row[amount_idx])
                    if amt is not None and amt < 0:
                        old = row[amount_idx]
                        row[amount_idx] = fmt_money(-amt, old)
                        log.append(f"{os.path.basename(path)}:L{lineno} DEPOSIT sign flip {old} -> {row[amount_idx]}")
                        changed = True
                        return join_row(row) + "\n"
            return line
        if len(row) > ncols:
            # Extra cells: unescaped '|' inside the note (last column).
            fixed = row[:ncols - 1] + [" / ".join(row[ncols - 1:])]
            log.append(f"{os.path.basename(path)}:L{lineno} rejoined {len(row)} cells -> {ncols} (note pipe)")
            changed = True
            return join_row(fixed) + "\n"
        # Fewer cells than the header: initial-funding row drift.
        action_idx = lower_header.index("action")
        if len(row) < ncols and row[action_idx].upper() == "DEPOSIT" and "initial capital funding" in line.lower():
            # The funding amount is the non-zero $ value that is not the price.
            price_idx = next((i for i, name in enumerate(lower_header) if "price" in name), None)
            money_cells = [(i, parse_number(c)) for i, c in enumerate(row)
                           if "$" in c and parse_number(c) not in (None, 0.0)]
            amount = None
            for i, val in money_cells:
                if i != price_idx:
                    amount = val
            if amount is None:
                amount = parse_number(row[price_idx]) if price_idx is not None else 0.0
            date = row[0]
            ticker = row[1]
            shares = row[3] if len(row) > 3 else "1.00"
            price = row[price_idx] if price_idx is not None else ""
            new = [""] * ncols
            new[0] = date
            new[1] = ticker
            new[2] = "DEPOSIT"
            new[3] = shares
            if price_idx is not None:
                new[price_idx] = price
            if amount_idx is not None:
                new[amount_idx] = fmt_money(amount, f"${amount:,.2f}")
                if new[amount_idx].startswith("$"):
                    new[amount_idx] = "+$" + new[amount_idx][1:]
            for i, name in enumerate(lower_header):
                if name == "order type":
                    new[i] = "Market"
                elif name == "status":
                    new[i] = "FILLED"
                elif name == "note":
                    new[i] = "Initial capital funding"
            log.append(f"{os.path.basename(path)}:L{lineno} funding row rebuilt (amount {amount:,.2f})")
            changed = True
            return join_row(new) + "\n"
        log.append(f"{os.path.basename(path)}:L{lineno} UNHANDLED short row ({len(row)} vs {ncols} cells): {line.strip()[:120]}")
        return line

    for i, line in enumerate(lines):
        lineno = i + 1
        if i == header_idx:
            out.append(line)
            continue
        stripped = line.strip()
        if not stripped.startswith("|"):
            out.append(line)
            continue
        # Separator row (---) passes through.
        if set(stripped.replace("|", "").strip()) <= {":", "-", " "}:
            out.append(line)
            continue
        if i < header_idx:
            # Data row before the header (S1): collect for re-insertion.
            stray_rows.append((lineno, line))
            changed = True
            continue
        out.append(process_data_row(line, lineno))

    # Re-insert stray rows in date order (after the header separator).
    if stray_rows:
        # Find the separator line index in out.
        sep_idx = None
        for j, line in enumerate(out):
            if line.strip().startswith("|") and set(line.strip().replace("|", "").strip()) <= {":", "-", " "}:
                sep_idx = j
                break
        insert_at = (sep_idx + 1) if sep_idx is not None else len(out)
        for lineno, line in stray_rows:
            fixed = process_data_row(line, lineno)
            # Insert in date order: find first data row with a later date.
            row_date = split_cells(line)[0]
            pos = insert_at
            while pos < len(out):
                other = out[pos]
                if other.strip().startswith("|") and not set(other.strip().replace("|", "").strip()) <= {":", "-", " "}:
                    other_date = split_cells(other)[0]
                    if other_date > row_date:
                        break
                pos += 1
            out.insert(pos, fixed)
            log.append(f"{os.path.basename(path)}:L{lineno} stray pre-header row moved into table (date {row_date})")

    if changed:
        with open(path, "w", encoding="utf-8") as handle:
            handle.writelines(out)
    return changed


def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    log = []
    files = sorted(glob.glob(os.path.join(ROOT, "transactions*.md")))
    for path in files:
        backup = os.path.join(BACKUP_DIR, os.path.basename(path))
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
        normalize_file(path, log)
    print(f"Processed {len(files)} ledgers; backup in _archive/ledger_backups_2026-11-12/")
    print(f"{len(log)} changes:")
    for entry in log:
        print("  " + entry)


if __name__ == "__main__":
    sys.exit(main())
