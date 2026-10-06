"""Research-only Nasdaq challenger; no brokerage, scheduler or operating-book I/O."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import datetime as dt

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "research/strategy33"
ASSETS = ["QQQ", "TQQQ"]
PRIMARY = dict(trend=200, volatility=20, vol_target=.35, max_exposure=2., band=.05)
MODES = ("challenger", "qqq", "tqqq", "s12_reference", "s12_scaled_control")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def validate(data):
    if list(data.columns) != ASSETS + ["FX"] or not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("QQQ, TQQQ, FX with dated observations required")
    if data.index.has_duplicates or not data.index.is_monotonic_increasing or len(data) < 260:
        raise ValueError("At least 260 unique sorted observations required")
    if not np.isfinite(data.to_numpy()).all() or (data <= 0).any().any():
        raise ValueError("Finite positive complete observations required")


def targets(data, mode="challenger", params=None):
    validate(data)
    if mode not in MODES:
        raise ValueError("Unknown mode")
    p = PRIMARY | (params or {})
    if (p["trend"] < 2 or p["volatility"] < 2 or not 0 < p["vol_target"] <= 1
            or not 0 < p["max_exposure"] <= 3 or not 0 <= p["band"] < 1):
        raise ValueError("Invalid research parameters")
    result = pd.DataFrame(0., index=data.index, columns=ASSETS)
    if mode in {"qqq", "tqqq"}:
        result[mode.upper()] = 1.
        return result
    if mode == "s12_reference":
        p = p | dict(trend=200, volatility=20, vol_target=.20, max_exposure=1.5)
    vol = data.QQQ.pct_change(fill_method=None).rolling(p["volatility"]).std() * np.sqrt(252)
    # A flat, adequately observed history uses the cap; absent history is cash.
    exposure = (p["vol_target"] / vol.clip(lower=.0001)).clip(upper=p["max_exposure"])
    exposure = exposure.where(data.QQQ > data.QQQ.rolling(p["trend"]).mean(), 0.).fillna(0.)
    if mode.startswith("s12"):
        result.TQQQ = exposure / 3.
    else:
        result.TQQQ = ((exposure - 1.) / 2.).clip(lower=0.)
        result.QQQ = exposure.clip(upper=1.) - result.TQQQ
    return result


def funded_rebalance(holdings, desired, nav, cost):
    """Solve post-cost NAV without borrowing; all amounts in the book currency."""
    if (not 0 <= cost < 1 or not np.isfinite(nav) or nav <= 0
            or not np.isfinite(desired).all() or (desired < 0).any()
            or desired.sum() > 1 + 1e-10):
        raise ValueError("Invalid funded allocation")
    low, high = 0., nav
    for _ in range(55):
        mid = (low + high) / 2
        if mid + cost * np.abs(mid * desired - holdings).sum() > nav:
            high = mid
        else:
            low = mid
    trade = low * desired - holdings
    fees = float(cost * np.abs(trade).sum())
    after = holdings + trade
    return after, float(nav - fees - after.sum()), fees, trade


def simulate(data, mode="challenger", params=None, cost=.003, cash_apr=0., lag=1,
             start="2011-03-01", seed=200000.):
    desired = targets(data, mode, params)
    p = PRIMARY | (params or {})
    if (lag not in (1, 2) or not np.isfinite(seed) or seed <= 0
            or not np.isfinite(cash_apr) or not 0 <= cash_apr < 1 or not 0 <= cost < 1):
        raise ValueError("Invalid execution assumptions")
    indices = np.flatnonzero(data.index >= pd.Timestamp(start))
    if not len(indices) or indices[0] < max(250, p["trend"]) + lag:
        raise ValueError("Insufficient pre-evaluation warmup")
    prices = data[ASSETS].mul(data.FX, axis=0).to_numpy()
    weights = desired.to_numpy()
    units, cash = np.zeros(2), float(seed)
    rows, ledger = [], []
    previous_date = data.index[indices[0] - 1]
    for count, i in enumerate(indices):
        date = data.index[i]
        # Carry belongs to the interval's old cash, before this close's fills.
        interest = cash * cash_apr / 365.25 * (date - previous_date).days
        cash += interest
        old_value = units * prices[i]
        before = float(cash + old_value.sum())
        target = weights[i - lag]
        current = old_value / before
        new_week = date.to_period("W-SUN") != previous_date.to_period("W-SUN")
        risk_off = target.sum() == 0 and old_value.sum() > 1e-8
        if mode == "s12_reference":
            # Preserve the original daily relative 20% rebalance rule, but
            # use this engine's funded next-close fills and common costs.
            needed = (target[1] == 0 and current[1] > 0) or (target[1] > 0 and
                      (current[1] == 0 or abs(current[1] / target[1] - 1) > .20))
            rebalance = count == 0 or needed
        elif mode in {"qqq", "tqqq"}:
            rebalance = count == 0  # Buy-and-hold, no free daily rebalancing.
        else:
            rebalance = count == 0 or risk_off or (new_week and np.max(np.abs(target - current)) >= p["band"])
        fees, turnover = 0., 0.
        if rebalance:
            held, cash, fees, trade = funded_rebalance(old_value, target, before, cost)
            units = held / prices[i]
            turnover = float(np.abs(trade).sum())
            for j, ticker in enumerate(ASSETS):
                if abs(trade[j]) > 1e-8:
                    ledger.append(dict(date=str(date.date()), signal_date=str(data.index[i-lag].date()),
                                       ticker=ticker, quantity=float(trade[j] / prices[i, j]),
                                       price_mxn=float(prices[i, j]), fee_mxn=float(abs(trade[j]) * cost),
                                       cash_delta=float(-trade[j] - abs(trade[j]) * cost)))
        nav = float(cash + units @ prices[i])
        if cash < -1e-7 or (units < -1e-9).any() or not np.isfinite(nav) or nav <= 0:
            raise AssertionError("Unfunded or invalid portfolio")
        effective = float((units * prices[i]) @ np.array([1., 3.]) / nav)
        rows.append(dict(date=date, nav_mxn=nav, cash_mxn=cash, interest_mxn=interest,
                         fees_mxn=fees, traded_mxn=turnover, units_QQQ=float(units[0]),
                         units_TQQQ=float(units[1]), effective_exposure=effective))
        previous_date = date
    frame = pd.DataFrame(rows).set_index("date")
    frame.attrs["seed"] = seed
    return frame, ledger


def metrics(frame, start, end):
    part = frame.loc[start:end]
    if len(part) < 2:
        raise ValueError("Insufficient evaluation observations")
    before = frame.loc[frame.index < part.index[0]]
    initial = float(before.nav_mxn.iloc[-1]) if len(before) else frame.attrs["seed"]
    initial_date = before.index[-1] if len(before) else part.index[0]
    values = np.r_[initial, part.nav_mxn.to_numpy()]
    returns = values[1:] / values[:-1] - 1
    years = (part.index[-1] - initial_date).days / 365.25
    volatility = float(returns.std(ddof=1) * np.sqrt(252))
    sharpe = float(returns.mean() * 252 / volatility) if volatility > 1e-12 else 0.
    drawdown = values / np.maximum.accumulate(values) - 1
    return dict(total_return=float(values[-1] / initial - 1),
                cagr=float((values[-1] / initial) ** (1/years) - 1),
                sharpe_zero_rf=sharpe, evidence_score=sharpe * years, years=years,
                annual_volatility=volatility, max_dd=float(drawdown.min()),
                worst_day=float(returns.min()), fees_mxn=float(part.fees_mxn.sum()),
                annual_turnover=float((part.traded_mxn / part.nav_mxn).sum() / years),
                peak_effective_exposure=float(part.effective_exposure.max()))


def acquire(output, design):
    import yfinance as yf
    if (output / "prices.csv").exists() or (output / "manifest.json").exists():
        raise FileExistsError("Frozen acquisition cannot be overwritten")
    spec = design["data"]
    raw = yf.download(spec["tickers"], start=spec["start"], end=spec["end_exclusive"],
                      auto_adjust=True, threads=False, progress=False)["Close"]
    raw = raw.reindex(columns=spec["tickers"]).rename(columns={"MXN=X": "FX"})
    raw.index = pd.to_datetime(raw.index).tz_localize(None).normalize()
    data = raw.dropna()
    validate(data)
    if data.index[0] > pd.Timestamp("2010-02-12") or data.index[-1] < pd.Timestamp("2026-10-05"):
        raise ValueError("Requested data coverage missing")
    data.to_csv(output / "prices.csv", index_label="date", lineterminator="\n")
    write_json(output / "manifest.json", dict(provider="Yahoo Finance via yfinance", version=yf.__version__,
               fetched_utc=dt.datetime.now(dt.timezone.utc).isoformat(), adjusted=True,
               rows=len(data), dropped=len(raw)-len(data), first=str(data.index[0].date()),
               last=str(data.index[-1].date()), sha256=sha((output / "prices.csv").read_bytes()),
               design_sha256=sha((output / "design.json").read_bytes())))


def run(output):
    design = json.loads((output / "design.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if (sha((output / "prices.csv").read_bytes()) != manifest["sha256"] or
            sha((output / "design.json").read_bytes()) != manifest["design_sha256"]):
        raise ValueError("Frozen data or predeclared design has changed")
    if design["primary"] != PRIMARY:
        raise ValueError("Implementation differs from predeclared primary")
    data = pd.read_csv(output / "prices.csv", index_col="date", parse_dates=True)
    validate(data)
    scenarios = {"base": {}, "double_cost": {"cost": .006}, "two_session_fill": {"lag": 2},
                 "cash_carry_sensitivity": {"cash_apr": .0653}}
    results = {}
    for scenario, assumptions in scenarios.items():
        for mode in MODES:
            frame, ledger = simulate(data, mode=mode, **assumptions)
            key = f"{scenario}_{mode}"
            frame.to_csv(output / f"{key}_nav.csv", index_label="date", lineterminator="\n")
            if scenario == "base":
                write_json(output / f"{key}_ledger.json", ledger)
            results[key] = {name: metrics(frame, *window) for name, window in design["windows"].items()}
            results[key]["full"] = metrics(frame, "2011", "2026")
            results[key]["years"] = {str(year): metrics(frame, str(year), str(year)) for year in range(2011, 2027)}
    neighbors = []
    for changes in design["neighbors"]:
        frame, _ = simulate(data, params=changes)
        neighbors.append(dict(changes=changes, evaluation=metrics(frame, *design["windows"]["evaluation"])))
    checks = {}
    for scenario in ("base", "double_cost", "two_session_fill"):
        candidate = results[f"{scenario}_challenger"]["evaluation"]
        checks[f"{scenario}_beats_qqq_and_s12_cagr"] = all(candidate["cagr"] > results[f"{scenario}_{mode}"]["evaluation"]["cagr"] for mode in ("qqq", "s12_reference"))
    checks["base_drawdown_better_than_minus_60_percent"] = results["base_challenger"]["evaluation"]["max_dd"] > -.60
    checks["positive_recent_return"] = results["base_challenger"]["recent"]["total_return"] > 0
    accepted = all(checks.values())
    candidate = results["base_challenger"]["evaluation"]
    control = results["base_s12_scaled_control"]["evaluation"]
    control_dominates = (control["cagr"] > candidate["cagr"] and
                         control["max_dd"] > candidate["max_dd"])
    result = dict(status="RESEARCH_ONLY", screen_passed=accepted, checks=checks, results=results,
                  higher_risk_s12_control_dominates_evaluation=control_dominates,
                  neighbors=neighbors, design_sha256=manifest["design_sha256"], data_sha256=manifest["sha256"],
                  code_sha256=sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
                  runtime=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__))
    write_json(output / "results.json", result)
    lines = ["# S33 aggressive growth challenger", "",
             f"**Predeclared screen: {'PASS — research only' if accepted else 'FAIL — do not promote'}.** No deployment approval.", "",
             ("**Not an unambiguous improvement:** the prespecified higher-risk S12-style control has both higher CAGR and less drawdown in 2019–2025. Passing the narrower screen does not beat this control or prove alpha." if control_dominates else "Passing a historical screen does not establish future superiority or alpha."), "",
             "All figures are after modeled costs in MXN. Signals use completed closes and fill at a later close; old holdings earn the interval return.",
             "No margin, deposits, synthetic pre-inception TQQQ or taxes. Adjusted prices include distributions and embedded fund drag.",
             "Primary cash earns zero. Fixed 6.53% carry is a sensitivity, not historical Bondia. FX is marked at same-date daily observations, not synchronized executable quotes.",
             "All windows are retrospective; none is a newly untouched holdout. More leverage is not evidence of alpha.", "",
             "## Primary evaluation: 2019–2025", "",
             "| Model | CAGR | Sharpe (0% Rf) | Max drawdown | Annual turnover | Sharpe × years |", "|---|---:|---:|---:|---:|---:|"]
    for mode in MODES:
        m = results[f"base_{mode}"]["evaluation"]
        lines.append(f"| {mode} | {m['cagr']:.2%} | {m['sharpe_zero_rf']:.2f} | {m['max_dd']:.2%} | {m['annual_turnover']:.2f} | {m['evidence_score']:.2f} |")
    lines += ["", "## Full common history: 2011-03-01 through 2026-10-05", "",
              "| Model | CAGR | Sharpe (0% Rf) | Max drawdown | Peak effective exposure |", "|---|---:|---:|---:|---:|"]
    for mode in MODES:
        m = results[f"base_{mode}"]["full"]
        lines.append(f"| {mode} | {m['cagr']:.2%} | {m['sharpe_zero_rf']:.2f} | {m['max_dd']:.2%} | {m['peak_effective_exposure']:.2f}x |")
    lines += ["", "S12_reference preserves its original target/risk settings and relative daily rebalance band, but uses this common funded next-close engine, costs and cash assumptions. It is NOT the old published S12 backtest.",
              "S12_scaled_control uses the challenger's exposure target and rebalance rule with TQQQ plus MXN cash, isolating allocation/currency differences. Neither is full live parity.", "",
              "## Challenger across time and execution sensitivities", "",
              "| Scenario | Window | CAGR | Total return | Max drawdown |", "|---|---|---:|---:|---:|"]
    for scenario in scenarios:
        for window in ["reference", "evaluation", "recent", "full"]:
            m = results[f"{scenario}_challenger"][window]
            lines.append(f"| {scenario} | {window} | {m['cagr']:.2%} | {m['total_return']:.2%} | {m['max_dd']:.2%} |")
    lines += ["", "## All prespecified neighbors (no winner selected)", "",
              "| Change | Evaluation CAGR | Max drawdown |", "|---|---:|---:|"]
    for item in neighbors:
        m = item["evaluation"]
        lines.append(f"| {item['changes']} | {m['cagr']:.2%} | {m['max_dd']:.2%} |")
    lines += ["", "## Screen checks", ""] + [f"- {key}: {value}" for key, value in checks.items()]
    lines += ["", "## Limits", ""] + [f"- {item}" for item in design["limitations"]]
    lines += ["", "The 2x exposure is a target at fills, not a guaranteed cap between rebalances. A 60% drawdown threshold is a research screen, not a stop-loss promise.",
              "The recent window is less than a year: use its total return, not its annualized CAGR as a forecast. Differences between periods are evidence of regime dependence, not permission to select a convenient window.",
              "Ledger quantities use total-return-adjusted prices: they are synthetic accounting units, not broker-reconcilable historical share counts. The simulator assumes fractional fills and reinvested distributions; it does not model taxes or distribution payment-date cash constraints.",
              "Performance is not comparable with mismatched archived S14/S25/S30 results. Do not claim superiority over all strategies.",
              "Reproduce with `python -B strategy33.py`. Only explicit `--download` contacts a public price feed. No broker runner is registered."]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    design = json.loads((OUTPUT / "design.json").read_text(encoding="utf-8"))
    if args.download:
        acquire(OUTPUT, design)
    run(OUTPUT)


if __name__ == "__main__":
    main()
