"""Reproducible research validation. Never imports or executes live runners.

Only --download contacts a public price provider. The default run reads frozen
CSVs and Git objects and writes exclusively below the chosen research output.
No broker APIs, credential access, portfolio changes, or graduation approval.
"""
from __future__ import annotations
import argparse
import collections
import contextlib
import datetime as dt
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import platform
import subprocess
import tempfile
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
UNIVERSES = {
    "s25": ["AMXB.MX", "WALMEX.MX", "GMEXICOB.MX", "FEMSAUBD.MX", "CEMEXCPO.MX"],
    "s30": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
}
SOURCE_FILES = [
    "validate_strategies.py", "skills/golden_macd_backtest.py", "backtest_strategy25.py",
    "backtest_strategy30.py", "reconcile_strategy_navs.py", "accounting.py",
    "strategy_registry.py", "strategy32.py", "paper_strategy32.py",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def validate_prices(frame, expected_columns):
    if (not isinstance(frame.index, pd.DatetimeIndex) or frame.index.has_duplicates
            or not frame.index.is_monotonic_increasing or len(frame) < 252):
        raise ValueError("A year or more of unique, sorted, dated prices is required")
    if list(frame.columns) != list(expected_columns):
        raise ValueError("Frozen universe differs from the reviewed configuration")
    if not np.isfinite(frame.to_numpy()).all() or (frame <= 0).any().any():
        raise ValueError("Prices must be finite, positive and complete")


def freeze_prices(output, start, end):
    """Explicit acquisition step; existing snapshots are never overwritten."""
    import yfinance as yf
    manifest_path = output / "prices_manifest.json"
    if manifest_path.exists() or any((output / f"{key}_prices.csv").exists() for key in UNIVERSES):
        raise FileExistsError("Use a new output directory for a new price snapshot")
    records, failures = {}, {}
    for key, tickers in UNIVERSES.items():
        try:
            raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                              progress=False, threads=False)
            prices = raw["Close"].reindex(columns=tickers)
            prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
            common = prices.dropna()
            validate_prices(common, tickers)
            path = output / f"{key}_prices.csv"
            common.to_csv(path, index_label="date", lineterminator="\n")
            records[key] = dict(file=path.name, sha256=digest(path.read_bytes()),
                                rows=len(common), dropped_rows=len(prices) - len(common),
                                first=str(common.index[0].date()), last=str(common.index[-1].date()),
                                tickers=tickers)
        except Exception as exc:
            failures[key] = str(exc)
    manifest = dict(provider="Yahoo Finance via yfinance", adjusted_total_return_prices=True,
                    requested_start=start, requested_end_exclusive=end,
                    fetched_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                    yfinance_version=importlib.metadata.version("yfinance"), datasets=records, failures=failures)
    write_json(manifest_path, manifest)
    return manifest


def read_frozen(output, key, record):
    path = output / f"{key}_prices.csv"
    if record["file"] != path.name or digest(path.read_bytes()) != record["sha256"]:
        raise ValueError(f"{key}: frozen snapshot hash mismatch")
    data = pd.read_csv(path, index_col="date", parse_dates=True)
    validate_prices(data, UNIVERSES[key])
    return data


def metrics(nav, initial):
    if len(nav) < 2 or not isinstance(nav.index, pd.DatetimeIndex):
        raise ValueError("Dated portfolio curve required")
    values = np.r_[initial, nav.to_numpy(dtype=float)]
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Invalid NAV curve")
    returns = values[1:] / values[:-1] - 1
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    if years <= 0:
        raise ValueError("Positive evaluation window required")
    volatility = float(returns.std(ddof=1) * np.sqrt(252))
    sharpe = float(returns.mean() * 252 / volatility) if volatility > 1e-12 else 0.
    return dict(cagr=float((values[-1] / initial) ** (1 / years) - 1),
                sharpe_zero_rf=sharpe, max_dd=float((values / np.maximum.accumulate(values) - 1).min()),
                years=years, evidence_score=sharpe * years, annual_volatility=volatility,
                end_nav=float(values[-1]))


def passive_basket(prices, capital, cost):
    """Equal initial allocations, funded entry fees, then hold without rebalancing."""
    quantities = (capital / len(prices.columns)) / (1 + cost) / prices.iloc[0]
    return prices.mul(quantities).sum(axis=1)


def compare_golden(output, key, record):
    import backtest_strategy25 as s25
    import backtest_strategy30 as s30
    module = s25 if key == "s25" else s30
    capital = 200000. if key == "s25" else 100000.
    cash_name = "BONDIA_YIELD" if key == "s25" else "RF_USD"
    base_carry, base_cost = getattr(module, cash_name), module.TRANSACTION_COST
    prices = read_frozen(output, key, record)
    results = {}
    for label, carry, cost in (("base", base_carry, base_cost),
                               ("zero_cash_carry", 0., base_cost),
                               ("double_cost", base_carry, base_cost * 2)):
        with patch.object(module, cash_name, carry), patch.object(module, "TRANSACTION_COST", cost):
            curves = [module.run_single_asset_simulation(pd.DataFrame({"close": prices[ticker]}), ticker,
                                                        initial_capital=capital / len(prices.columns))
                      for ticker in prices.columns]
        strategy = pd.Series(np.sum(curves, axis=0), index=prices.index)
        benchmark = passive_basket(prices, capital, cost)
        pd.DataFrame({"strategy": strategy, "equal_weight_buy_hold": benchmark}).to_csv(
            output / f"{key}_{label}_nav.csv", index_label="date", lineterminator="\n")
        results[label] = dict(currency="MXN" if key == "s25" else "USD", fixed_cash_apr=carry,
                              one_way_cost=cost, strategy=metrics(strategy, capital),
                              equal_weight_buy_hold=metrics(benchmark, capital))
    return results


def ledger_audit(output, revision):
    """Audit copies of committed evidence, never the working portfolios."""
    import reconcile_strategy_navs as reconcile
    from strategy_registry import STRATEGIES
    hashes = {}
    with tempfile.TemporaryDirectory(prefix="strategy-ledger-audit-") as folder:
        location = Path(folder)
        for spec in STRATEGIES:
            for filename in (spec.portfolio_file, reconcile.ledger_name(spec)):
                raw = git("show", f"{revision}:{filename}")
                hashes[filename] = digest(raw)
                (location / filename).write_bytes(raw)
        with patch.object(reconcile, "__file__", str(location / "reconcile_strategy_navs.py")), contextlib.redirect_stdout(io.StringIO()):
            reconcile.main()
        result = json.loads((location / reconcile.DATA).read_text(encoding="utf-8"))
        (output / "ledger_audit.md").write_bytes((location / reconcile.REPORT).read_bytes())
    result["source_revision"] = revision
    result["input_sha256"] = hashes
    write_json(output / "ledger_audit.json", result)
    return result


def runtime_versions():
    result = {"python": platform.python_version(), "platform": platform.platform()}
    result["installed_distributions"] = dict(sorted((dist.metadata["Name"], dist.version)
                                                   for dist in importlib.metadata.distributions()))
    for name in ("numpy", "pandas", "scipy", "scikit-learn", "yfinance", "pytest", "hmmlearn", "arch", "torch"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = "not installed"
    return result


def run(output, ref):
    revision = git("rev-parse", ref).decode().strip()
    audit = ledger_audit(output, revision)
    counts = dict(collections.Counter(item["status"] for item in audit["strategies"]))
    manifest_file = output / "prices_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {"datasets": {}}
    comparisons, unavailable = {}, {}
    for key in UNIVERSES:
        record = manifest.get("datasets", {}).get(key)
        if not record:
            unavailable[key] = manifest.get("failures", {}).get(key, "No frozen market-price snapshot supplied")
            continue
        # Hash/price violations fail the run; never silently accept altered data.
        comparisons[key] = compare_golden(output, key, record)
    results = dict(source_revision=revision, generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   implementation_sha256={name: digest((ROOT / name).read_bytes().replace(b"\r\n", b"\n")) for name in SOURCE_FILES},
                   runtime=runtime_versions(), reconciliation_counts=counts, comparisons=comparisons,
                   unavailable=unavailable, deployment="BLOCKED — research validation only")
    write_json(output / "results.json", results)
    lines = ["# Reproducible strategy validation", "", f"Committed accounting evidence: `{revision}`.",
             "Current implementation fingerprints and runtime versions are in results.json.", "",
             "**Deployment remains BLOCKED.** Code-test success is not investment-performance validation.", "",
             "## Ledger reconciliation (offline, immutable source copies)", "",
             ", ".join(f"{name}: {count}" for name, count in counts.items()) + ".",
             "See ledger_audit.md/json for per-symbol quantities, cash gaps and parsing errors.",
             "No broker was contacted and no opening balances or corrections were invented.", "",
             "## Corrected Golden MACD engines versus matched baskets", "",
             "Adjusted closes; native currencies; no contributions or taxes; next-close fills.",
             "Each stock has an independent equal-sized sleeve. This is NOT a full reproduction",
             "of the paper runner's shared cash and 18% allocation limit. Universe selection is retrospective.",
             "Base cash yields are fixed sensitivities, not historical rates. Benchmark entry pays the same cost.",
             "Sharpe uses zero risk-free return and 252 observations/year; CAGR uses calendar years.", "",
             "| Strategy/scenario | Currency | CAGR | Sharpe (0% Rf) | Max DD | Matched buy/hold CAGR | Buy/hold Sharpe | Buy/hold DD |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for key, scenarios in comparisons.items():
        for label, item in scenarios.items():
            s, b = item["strategy"], item["equal_weight_buy_hold"]
            lines.append(f"| {key.upper()} {label} | {item['currency']} | {s['cagr']:.2%} | {s['sharpe_zero_rf']:.2f} | {s['max_dd']:.2%} | {b['cagr']:.2%} | {b['sharpe_zero_rf']:.2f} | {b['max_dd']:.2%} |")
    for key, reason in unavailable.items():
        lines.append(f"\n{key.upper()} unavailable: {reason}")
    lines += ["", "## Remaining evidence gaps", "",
              "- S1/S8: point-in-time fundamental inputs are unavailable; refreshing current fundamentals cannot validate history.",
              "- S2: the scheduled HMM-filtered runner is not the legacy portfolio backtester. Canonical engine/live parity is not established.",
              "- S24: the source provider's rolling 60-day window is not a preserved independent test set. No new profitability claim is made.",
              "- S3: broker fills, statements and strategy ownership allocations are required; do not overwrite shared-account books from aggregate positions.",
              "- S12 and one S14/S15 representative remain research priorities, not approved allocations.",
              "- S32's frozen experiment remains rejected. Its existing snapshot is retained, not tuned to change that result.", "",
              "Passing tests and rerunning curves do not clear backtest_review.py blocks or the 90-day verified paper-history requirement."]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(output / "report.md"), "reconciliation": counts,
                      "comparisons": list(comparisons), "unavailable": unavailable}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("research/validation/2026-10-05"))
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--download", action="store_true", help="Explicitly acquire a new frozen public-price snapshot first")
    parser.add_argument("--start", default="2010-02-11")
    parser.add_argument("--end", default="2026-10-06", help="Exclusive end date")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "research" / "validation"):
        parser.error("Output must be inside research/validation; production artifact paths are forbidden")
    output.mkdir(parents=True, exist_ok=True)
    if args.download:
        freeze_prices(output, args.start, args.end)
    run(output, args.ref)


if __name__ == "__main__":
    main()
