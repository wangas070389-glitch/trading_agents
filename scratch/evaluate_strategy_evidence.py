"""Read-only audit of saved strategy evidence at a pinned Git revision.

Never imports strategy runners, refreshes market data, or contacts a broker.
Printed NAV statistics describe the stored curves; they do not certify returns.
"""
import argparse
import ast
import csv
import datetime as dt
import hashlib
import io
import json
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path


def git(*args):
    return subprocess.check_output(["git", *args]).decode("utf-8-sig")


def summarize(text):
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames
    if not fields:
        return None
    column = next((x for x in ("NAV", "strategy", "Portfolio Value", "nav") if x in fields), fields[1] if len(fields) > 1 else None)
    if column is None:
        return {"headers": fields}
    points, invalid = [], 0
    for row in reader:
        try:
            value = float(row[column])
            day = dt.date.fromisoformat(row[fields[0]][:10])
            if not math.isfinite(value) or value <= 0:
                raise ValueError("unusable NAV")
            points.append((day, value))
        except (ValueError, TypeError):
            invalid += 1
    if not points:
        return {"headers": fields, "invalid": invalid}
    years = (points[-1][0] - points[0][0]).days / 365.25
    peak, drawdown = points[0][1], 0.0
    for _, value in points:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1)
    daily = dict(points)
    returns = {day: value / daily[previous] - 1 for previous, (day, value) in zip(list(daily), list(daily.items())[1:])}
    summary = {"column": column, "rows": len(points), "invalid": invalid,
               "first": str(points[0][0]), "last": str(points[-1][0]),
               "years": round(years, 3), "start_nav": points[0][1], "end_nav": points[-1][1],
               "curve_cagr_pct": round(100 * ((points[-1][1] / points[0][1]) ** (1 / years) - 1), 3) if years else None,
               "curve_max_dd_pct": round(drawdown * 100, 3)}
    return summary, returns


def offline_checks(ref):
    """Replay frozen data and small synthetic cases; no downloads or file writes."""
    root = Path(__file__).resolve().parents[1]
    for path in ("strategy32.py", "paper_strategy32.py", "skills/file_io_utils.py"):
        local = (root / path).read_text(encoding="utf-8-sig")
        if local != git("show", f"{ref}:{path}").replace("\r\n", "\n"):
            raise ValueError(f"Local implementation differs from reviewed revision: {path}")
    sys.path.insert(0, str(root))
    import numpy as np
    import pandas as pd
    from strategy32 import ASSETS, targets, simulate, metrics
    from paper_strategy32 import replay
    # Inspect the baseline even after its working-copy repair. The reviewed
    # module only imports numpy/pandas and defines offline calculations.
    baseline_macd = {"__name__": "reviewed_macd_baseline"}
    exec(compile(git("show", f"{ref}:skills/macd_trailing_strategy.py"),
                 f"{ref}:skills/macd_trailing_strategy.py", "exec"), baseline_macd)
    MACDTrailingStopStrategy = baseline_macd["MACDTrailingStopStrategy"]

    raw = subprocess.check_output(["git", "show", f"{ref}:research/strategy32/prices.csv"])
    saved = json.loads(git("show", f"{ref}:research/strategy32/results.json"))
    fingerprint = hashlib.sha256(raw).hexdigest()
    lf = raw.replace(b"\r\n", b"\n")
    variants = {"git_bytes": fingerprint, "lf": hashlib.sha256(lf).hexdigest(),
                "crlf": hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest()}
    matching_endings = [name for name, digest in variants.items() if digest == saved["sha256"]]
    assert matching_endings, "Frozen price snapshot fingerprint changed beyond line endings"
    data = pd.read_csv(io.BytesIO(raw), index_col="date", parse_dates=True)
    results = {}
    for mode, cost in (("trend", 0.003), ("equal", 0.003), ("spy", 0.003),
                       ("cash", 0.003), ("trend", 0.006)):
        frame, events = simulate(data, mode=mode, cost=cost)
        key = "trend_double_cost_holdout" if cost == 0.006 else f"{mode}_holdout"
        result = metrics(frame, "2020", "2025")
        for name, value in result.items():
            assert math.isclose(value, saved["metrics"][key][name], rel_tol=1e-8, abs_tol=1e-8), (key, name)
        results[key] = result
    state = replay(data, "2006-01-01")
    assert state["accounting_reconciled"]

    dates = pd.bdate_range("2005-01-01", "2007-12-31")
    rng = np.random.default_rng(32)
    sample = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, (len(dates), 4)), axis=0)), index=dates, columns=ASSETS)
    sample["FX"] = 20.0
    weights = targets(sample)
    assert (weights.sum(axis=1) <= 1 + 1e-10).all() and (weights <= 0.35).all().all()
    altered = sample.copy()
    altered.iloc[400:, :4] *= 2
    pd.testing.assert_frame_equal(weights.iloc[:400], targets(altered).iloc[:400])
    frame, events = simulate(sample)
    allowed = set(frame.groupby(frame.index.to_period("M")).head(1).index.strftime("%Y-%m-%d"))
    assert all(event["date"] in allowed for event in events)
    assert frame.cash_mxn.min() >= -1e-7
    assert replay(sample, "2006-01-01") == replay(sample, "2006-01-01")
    flat = sample.copy()
    flat[ASSETS] = 100.0
    free, _ = simulate(flat, "equal", cost=0)
    paid, _ = simulate(flat, "equal", cost=0.003)
    assert math.isclose(free.nav_mxn.iloc[-1], 200000.0)
    assert math.isclose(paid.nav_mxn.iloc[-1], 200000.0 / 1.003)
    invalid = sample.copy()
    invalid.iloc[300, 0] = np.nan
    try:
        simulate(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid price observation was accepted")
    altered = sample.copy()
    altered.iloc[500:, :4] *= 1.5
    changed, changed_events = simulate(altered)
    pd.testing.assert_frame_equal(frame.loc[:sample.index[499]], changed.loc[:sample.index[499]])
    cutoff = str(sample.index[500].date())
    assert [e for e in events if e["date"] < cutoff] == [e for e in changed_events if e["date"] < cutoff]

    class FixedEntry(MACDTrailingStopStrategy):
        def compute_indicators(self, prices):
            return {"macd_line": np.r_[0., 0., np.ones(len(prices) - 2)],
                    "signal_line": np.zeros(len(prices)), "long_term_ma": np.full(len(prices), 99.)}

    # One artificial entry on a flat price, zero external flows. This isolates the
    # production engine's performance-accounting behavior from signal quality.
    simple = pd.DataFrame({"TEST": 100.0}, index=pd.bdate_range("2026-01-05", periods=8))
    case = FixedEntry(long_term_ma_length=2, position_pct=0.5, commission_pct=0.01).run_portfolio_backtest(simple, initial_capital=100000.0, monthly_contribution=0)
    actual_return = float(case["nav_series"].iloc[-1] / case["nav_series"].iloc[0] - 1)
    claimed_return = float(case["twr_series"].iloc[-1] - 1)
    assert len(case["trade_log"]) == 1 and case["trade_log"][0]["fee"] > 0
    assert claimed_return > actual_return + 0.004
    return {"s32_git_sha256": fingerprint, "s32_recorded_sha256_line_endings": matching_endings,
            "s32_holdout_metrics_reproduced": results,
            "s32_paper_ledger_reconciled": state["accounting_reconciled"],
            "s32_synthetic_invariant_groups_passed": 6,
            "s2_synthetic_fee_regression": {"actual_nav_return_pct": actual_return * 100,
                                            "reported_twr_return_pct": claimed_return * 100,
                                            "fee": case["trade_log"][0]["fee"]}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", required=True)
    parser.add_argument("--offline-checks", action="store_true")
    args = parser.parse_args()
    ref = git("rev-parse", args.ref).strip()
    paths = git("ls-tree", "-r", "--name-only", ref).splitlines()
    curves, returns = {}, {}
    for path in paths:
        if "/" not in path and path.endswith("nav.csv") and "consolidated" not in path:
            result = summarize(git("show", f"{ref}:{path}"))
            if isinstance(result, tuple):
                curves[path], returns[path] = result
            else:
                curves[path] = result
    pairs = [("strategy14_backtest_nav.csv", "strategy15_backtest_nav.csv"),
             ("strategy12_backtest_nav.csv", "strategy14_backtest_nav.csv"),
             ("strategy19_backtest_nav.csv", "strategy23_backtest_nav.csv")]
    correlations = []
    for a, b in pairs:
        shared = sorted(set(returns[a]) & set(returns[b]))
        correlations.append({"a": a, "b": b, "overlap": len(shared), "correlation": round(statistics.correlation([returns[a][k] for k in shared], [returns[b][k] for k in shared]), 5)})
    audit = json.loads(git("show", f"{ref}:nav_reconciliation.json"))
    statuses = {}
    for item in audit["strategies"]:
        statuses[item["status"]] = statuses.get(item["status"], 0) + 1
    watchdog = git("show", f"{ref}:watchdog.py")
    scheduler = git("show", f"{ref}:scheduler.py")
    source = ast.parse(watchdog)
    # Match the expression used by the live watchdog, without importing it.
    pattern = next(n.value for n in ast.walk(source) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith("STRATEGY_SCRIPTS"))
    output = {"revision": ref, "curves": curves, "daily_curve_correlations": correlations,
                      "reconciliation_counts": statuses,
                      "watchdog_scheduler_regex_matches": bool(re.search(pattern, scheduler, re.DOTALL))}
    if args.offline_checks:
        output["offline_checks"] = offline_checks(ref)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
