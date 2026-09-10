"""Isolated paper replay. No broker connection, no legacy ledger mutation.

Supply a complete adjusted-close snapshot with 200 warmup sessions and an
explicit inception date. Repeated identical inputs produce identical state.
Adjusted total-return units include reinvested distributions, not broker shares.
"""
import argparse
import hashlib
from pathlib import Path
import pandas as pd
from strategy32 import ASSETS, simulate
from skills.file_io_utils import atomic_save_json


def replay(data, inception):
    nav, trades = simulate(data, start=inception)
    cash = 200000 + sum(event["cash_delta"] for event in trades)
    final = nav.iloc[-1]
    if abs(cash - final.cash_mxn) > 1e-6:
        raise AssertionError("Ledger cash does not reconcile")
    quantities = {a: sum(e["quantity"] for e in trades if e["ticker"] == a) for a in ASSETS}
    for asset in ASSETS:
        if abs(quantities[asset] - final[f"units_{asset}"]) > 1e-8:
            raise AssertionError("Ledger units do not reconcile")
    marked = sum(quantities[a] * data[a].iloc[-1] * data.FX.iloc[-1] for a in ASSETS)
    if abs(cash + marked - final.nav_mxn) > 1e-6:
        raise AssertionError("NAV does not reconcile")
    return dict(strategy="S32", inception=inception, as_of=str(nav.index[-1].date()),
                mode="research paper; adjusted total-return units", cash_mxn=cash,
                units=quantities, nav_mxn=float(final.nav_mxn),
                accounting_reconciled=True, graduation="RESEARCH_ONLY",
                transactions=[dict(date=inception, action="DEPOSIT", cash_delta=200000)] + trades)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--inception", required=True)
    parser.add_argument("--output", type=Path, default=Path("research/strategy32/paper_replay.json"))
    args = parser.parse_args()
    data = pd.read_csv(args.data, index_col="date", parse_dates=True)
    state = replay(data, args.inception)
    state["source_sha256"] = hashlib.sha256(args.data.read_bytes()).hexdigest()
    atomic_save_json(str(args.output), state)
    print(f"Paper ledger reconciled through {state['as_of']}: MXN {state['nav_mxn']:,.2f}")


if __name__ == "__main__":
    main()
