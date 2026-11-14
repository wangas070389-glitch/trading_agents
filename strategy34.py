"""Audit and run S34 research from reviewed historical data. Never contacts APIs.

Default audit writes only a data-readiness status, not invented performance.
Market data and derived performance must remain in the ignored private folder.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import datetime as dt

import numpy as np
import pandas as pd

from skills.earnings_momentum import Dataset, DataError, PARAMS, MODELS, simulate, metrics, timestamp

ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT / "research/strategy34"
PRIVATE = RESEARCH / "private"
REVIEW_CHECKS = (
    "license_allows_local_research", "stable_identifiers_and_links_verified",
    "historical_universe_includes_delisted", "announcement_and_availability_times_verified",
    "original_actuals_not_restatements", "preannouncement_consensus_vintages_verified",
    "forward_revision_same_period_and_basis_verified", "price_and_delisting_returns_verified",
    "market_calendar_and_missing_data_reviewed",
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def audit(bundle_path, review_path=None):
    errors, warnings, data, digest, exported_at = [], [], None, None, None
    counts = {}
    if not bundle_path.is_file():
        errors.append("DATA_MISSING: supply the point-in-time bundle described in DATA_REQUIREMENTS.md")
    else:
        try:
            raw = bundle_path.read_bytes()
            digest = sha(raw)
            bundle = json.loads(raw)
            if not isinstance(bundle, dict):
                raise DataError("Dataset must be a JSON object")
            if bundle.get("dataset_kind") != "market":
                errors.append("MARKET_DATA_REQUIRED: synthetic fixtures are tests, not performance evidence")
            meta = bundle.get("provenance", {})
            if not isinstance(meta, dict):
                raise DataError("Provenance must be a JSON object")
            for field in ("provider", "exported_at", "universe_definition", "calendar_source", "price_adjustment_method", "eps_basis_method", "availability_method"):
                if not isinstance(meta.get(field), str) or not meta[field].strip():
                    errors.append(f"PROVENANCE_MISSING: {field}")
            if meta.get("exported_at"):
                exported_at = timestamp(meta["exported_at"])
                if exported_at > pd.Timestamp.now(tz="UTC"):
                    errors.append("EXPORT_TIMESTAMP_IN_FUTURE")
            data = Dataset(bundle)
            if exported_at is not None:
                latest = max(timestamp(r["available_at"]) for table in ("prices", "universes", "actuals", "estimates") for r in bundle[table])
                if latest > exported_at:
                    errors.append("RECORD_AFTER_EXPORT: a vintage was unavailable when the snapshot was exported")
            counts = dict(sessions=len(data.sessions), securities=len(data.securities),
                          prices=len(data.prices), actual_versions=len(bundle["actuals"]),
                          estimate_vintages=len(bundle["estimates"]), universe_vintages=len(data.universes),
                          terminal_settlements=len(data.terminals))
            # Fail closed rather than silently dropping unavailable/delisted names.
            gaps = []
            for session in data.sessions[PARAMS["momentum_sessions"]:]:
                for member in data.universe(session["decision_at"]):
                    sid = member["sid"]
                    quote = data.prices.get((session["date"], sid))
                    if quote is None:
                        terminal_date = data.terminals.get(sid)
                        terminal = data.prices.get((terminal_date, sid))
                        if terminal and terminal_date < session["date"] and terminal["available_at"] <= session["decision_at"]:
                            continue
                    if quote is None or quote["available_at"] > session["decision_at"]:
                        gaps.append(f"{sid} {session['date']}")
            if gaps:
                errors.append(f"UNIVERSE_PRICE_GAPS: {len(gaps)} member/session marks missing or late; examples: {', '.join(gaps[:5])}")
            if len(data.sessions) < 1000:
                errors.append("INSUFFICIENT_HISTORY: at least 1000 sessions required for market research output")
            initial_sids = {sid for sid, rows in data.actuals.items() if any(r["version"] == 0 for r in rows)}
            quarterly = {sid for sid, rows in data.estimates.items() if any(r["period_type"] == "quarter" for r in rows)}
            annual = {sid for sid, rows in data.estimates.items() if any(r["period_type"] == "annual" for r in rows)}
            members = {m["sid"] for universe in data.universes for m in universe["members"]}
            missing = sorted(members - (initial_sids & quarterly & annual))
            if missing:
                errors.append(f"EARNINGS_COVERAGE_GAPS: {len(missing)} universe members lack original actuals, quarter consensus or annual estimates")
            if not data.terminals:
                warnings.append("No terminal settlements in bundle; reviewer must explain delisting coverage, not assume survivorship-free data")
        except (ValueError, TypeError, KeyError, OSError) as exc:
            errors.append(f"INVALID_DATA: {exc}")
    if review_path is None or not review_path.is_file():
        errors.append("REVIEW_REQUIRED: explicit human provenance review tied to the dataset SHA256")
    else:
        try:
            review = json.loads(review_path.read_text(encoding="utf-8"))
            if not isinstance(review, dict) or not isinstance(review.get("checks"), dict):
                raise DataError("Review and checks must be JSON objects")
            if digest is None or review.get("dataset_sha256") != digest:
                errors.append("REVIEW_HASH_MISMATCH")
            if not review.get("reviewer") or not review.get("coverage_notes"):
                errors.append("REVIEW_IDENTITY_AND_COVERAGE_NOTES_REQUIRED")
            reviewed_at = timestamp(review.get("reviewed_at"))
            if reviewed_at > pd.Timestamp.now(tz="UTC"):
                errors.append("REVIEW_TIMESTAMP_IN_FUTURE")
            if exported_at is not None and reviewed_at < exported_at:
                errors.append("REVIEW_PREDATES_EXPORT")
            for check in REVIEW_CHECKS:
                if review.get("checks", {}).get(check) is not True:
                    errors.append(f"REVIEW_INCOMPLETE: {check}")
        except (ValueError, TypeError, KeyError, OSError) as exc:
            errors.append(f"INVALID_REVIEW: {exc}")
    status = dict(status="INPUTS_REVIEWED_RESEARCH_ONLY" if not errors else "BLOCKED_DATA_REQUIRED",
                  performance_available=False, deployment_approved=False,
                  dataset_sha256=digest, counts=counts, errors=errors, warnings=warnings,
                  note="Metadata assertions and reviewer attestation are not independent proof of data quality or a trading edge")
    return status, data


def run(bundle_path, review_path, output):
    # Prevent publication of licensed inputs, identifiers or derived results.
    output = output.resolve()
    if not output.is_relative_to(PRIVATE.resolve()) or output == PRIVATE.resolve():
        raise DataError("Run output must be a new directory below research/strategy34/private")
    if output.exists():
        raise DataError("Output already exists; preserve the previous research record")
    status, data = audit(bundle_path, review_path)
    if status["errors"]:
        return status
    design_raw = (RESEARCH / "design.json").read_bytes()
    design = json.loads(design_raw)
    if design["params"] != PARAMS or tuple(design["models"]) != MODELS:
        raise DataError("Implementation differs from fixed research design")
    results, frames = {}, {}
    # Build entirely in memory first. Missing held prices abort without a
    # partial success report or an old result masquerading as a fresh run.
    for scenario, assumptions in (("base", {}), ("double_cost", {"cost": .006}), ("two_session_fill", {"lag": 2})):
        for mode in MODELS:
            frame, ledger, signals, rejected = simulate(data, mode, **assumptions)
            key = f"{scenario}_{mode}"
            frames[key] = (frame, ledger, signals, rejected)
            results[key] = dict(full=metrics(frame), windows={label: metrics(frame, *dates) for label, dates in design["windows"].items()},
                                filled_legs=sum(r["action"] in {"BUY", "SELL"} for r in ledger),
                                terminal_settlements=sum(r["action"] == "TERMINAL" for r in ledger),
                                rejected_batches=len(rejected), signal_rows=len(signals))
    output.mkdir(parents=True)
    for key, (frame, ledger, signals, rejected) in frames.items():
        frame.to_csv(output / f"{key}_nav.csv", index_label="date", lineterminator="\n")
        write_json(output / f"{key}_audit.json", dict(ledger=ledger, signals=signals, rejected_batches=rejected))
    summary = dict(status="RETROSPECTIVE_RESEARCH_ONLY_NO_PROMOTION", dataset_sha256=status["dataset_sha256"],
                   review_sha256=sha(review_path.read_bytes()), design_sha256=sha(design_raw),
                   code_sha256={p: sha((ROOT / p).read_bytes().replace(b"\r\n", b"\n")) for p in ("strategy34.py", "skills/earnings_momentum.py")},
                   runtime=dict(python=platform.python_version(), pandas=pd.__version__, numpy=np.__version__),
                   generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(), results=results,
                   deployment_approved=False)
    write_json(output / "results.json", summary)
    write_json(output / "data_audit.json", status)
    lines = ["# S34 retrospective research — not deployment approval", "",
             "USD, zero cash yield, no contributions/taxes/leverage. All models use trailing volatility ceilings, not ex-post risk matching.",
             "Actual volatility/exposure can differ. No alpha claim, parameter search, hypothesis significance or unseen holdout is implied.",
             "Adjusted-index units, fractional fills and terminal cash settlements are research abstractions, not broker share lots.",
             "Any unfillable leg cancels the entire modeled rebalance. Missing held marks abort; rejected orders never finance new buys.", "",
             "| Model/scenario | CAGR | Sharpe (0% Rf) | Sharpe × years | Drawdown | Volatility | Mean exposure | Rejected batches |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for key, value in results.items():
        m = value["full"]
        lines.append(f"| {key} | {m['cagr']:.2%} | {m['sharpe_zero_rf']:.2f} | {m['evidence_score']:.2f} | {m['max_dd']:.2%} | {m['volatility']:.2%} | {m['average_exposure']:.2%} | {value['rejected_batches']} |")
    lines += ["", "No automatic pass/fail profitability screen: review time-window, exposure and coverage differences before drawing an investment conclusion.",
              "This output can contain licensed derived data. Keep it private. Existing accounting, halt and graduation blocks remain."]
    (output / "report.md").write_text("\n".join(lines)+"\n", encoding="utf-8", newline="\n")
    return dict(status=summary["status"], output=str(output), errors=[], deployment_approved=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "run"), nargs="?", default="audit")
    parser.add_argument("--bundle", type=Path, default=PRIVATE / "bundle.json")
    parser.add_argument("--review", type=Path, default=PRIVATE / "review.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "audit":
            status, _ = audit(args.bundle, args.review)
            # No licensed rows/identifiers or private filenames in public status.
            if args.bundle == PRIVATE / "bundle.json" and not args.bundle.exists():
                write_json(RESEARCH / "status.json", status)
        else:
            if args.output is None:
                parser.error("run requires --output below research/strategy34/private")
            status = run(args.bundle, args.review, args.output)
        print(json.dumps(status, indent=2, allow_nan=False))
        return 2 if status["errors"] else 0
    except (DataError, OSError, ValueError, KeyError) as exc:
        print(json.dumps(dict(status="BLOCKED", error=str(exc), deployment_approved=False)))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
