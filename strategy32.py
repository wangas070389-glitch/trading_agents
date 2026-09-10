"""Frozen diversified trend research engine; all valuations and cash in MXN."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd

ASSETS = ["SPY", "EFA", "IEF", "GLD"]
PARAMS = dict(trend=200, volatility=60, floor=0.05, cap=0.35, band=0.02)


def validate(data):
    if not isinstance(data.index, pd.DatetimeIndex) or not data.index.is_monotonic_increasing or data.index.has_duplicates:
        raise ValueError("Unique sorted dated observations required")
    values = data[ASSETS + ["FX"]].to_numpy()
    if len(data) < 202 or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Insufficient or invalid complete price observations")


def targets(data):
    prices = data[ASSETS]
    vol = prices.pct_change(fill_method=None).rolling(PARAMS["volatility"]).std() * np.sqrt(252)
    inverse = 1 / vol.clip(lower=PARAMS["floor"])
    weights = inverse.div(inverse.sum(axis=1), axis=0).clip(upper=PARAMS["cap"])
    eligible = prices > prices.rolling(PARAMS["trend"]).mean()
    return weights.where(eligible, 0).fillna(0)


def simulate(data, mode="trend", cost=0.003, seed=200000.0, start="2006-01-01"):
    validate(data)
    if mode not in {"trend", "equal", "spy", "cash"} or not 0 <= cost < 1:
        raise ValueError("Invalid mode/cost")
    desired = targets(data)
    if mode == "equal":
        desired.loc[:, :] = 0.25
    elif mode == "spy":
        desired.loc[:, :] = 0.0
        desired.loc[:, "SPY"] = 1.0
    elif mode == "cash":
        desired.loc[:, :] = 0.0
    units = np.zeros(4)
    cash = seed
    rows, events = [], []
    active = data.loc[data.index >= start]
    if active.empty:
        raise ValueError("No evaluation observations")
    previous = data.index[data.index < active.index[0]]
    if len(previous) < 200:
        raise ValueError("200 warmup sessions required before evaluation")
    pending = desired.loc[previous[-1]].to_numpy()
    for i, (date, row) in enumerate(active.iterrows()):
        price = row[ASSETS].to_numpy(dtype=float) * float(row["FX"])
        nav = cash + units @ price
        traded, fee = 0.0, 0.0
        if pending is not None:
            current = units * price / nav
            if i == 0 or np.max(np.abs(current - pending)) >= PARAMS["band"]:
                # Solve post-fee NAV: desired holdings plus fees cannot exceed capital.
                low, high = 0.0, nav
                for _ in range(70):
                    middle = (low + high) / 2
                    charge = cost * np.abs(middle * pending - units * price).sum()
                    if middle + charge > nav:
                        high = middle
                    else:
                        low = middle
                trade = low * pending / price - units
                for ticker, qty, px in zip(ASSETS, trade, price):
                    if abs(qty) > 1e-12:
                        trade_fee = abs(qty * px) * cost
                        events.append(dict(date=date.date().isoformat(), ticker=ticker,
                                           quantity=float(qty), price_mxn=float(px), fee_mxn=float(trade_fee),
                                           cash_delta=float(-qty * px - trade_fee)))
                traded = float(np.abs(trade * price).sum())
                fee = traded * cost
                cash -= float(trade @ price) + fee
                units += trade
            pending = None
        nav = float(cash + units @ price)
        if cash < -1e-7 or (units < -1e-9).any() or not np.isfinite(nav):
            raise AssertionError("Unfunded or invalid portfolio")
        rows.append(dict(date=date, nav_mxn=nav, cash_mxn=cash, fees_mxn=fee,
                         traded_mxn=traded, **{f"units_{a}": float(q) for a, q in zip(ASSETS, units)}))
        # Only decide when a following observation confirms the month has ended.
        if i + 1 < len(active) and date.to_period("M") != active.index[i + 1].to_period("M") and mode in {"trend", "equal"}:
            pending = desired.loc[date].to_numpy()
    return pd.DataFrame(rows).set_index("date"), events


def metrics(frame, start, end):
    part = frame.loc[start:end]
    before = frame.loc[frame.index < part.index[0]]
    initial = float(before.nav_mxn.iloc[-1]) if len(before) else 200000.0
    values = np.r_[initial, part.nav_mxn.to_numpy()]
    returns = values[1:] / values[:-1] - 1
    years = len(part) / 252
    std = returns.std(ddof=1)
    return dict(cagr=float((values[-1] / initial) ** (1 / years) - 1),
                sharpe=float(returns.mean() / std * np.sqrt(252)) if std > 1e-12 else 0.0,
                max_dd=float((values / np.maximum.accumulate(values) - 1).min()),
                turnover=float((part.traded_mxn / part.nav_mxn).sum() / years),
                fees=float(part.fees_mxn.sum()))


def download(path):
    import yfinance as yf
    columns = {}
    for ticker in ASSETS + ["USDMXN=X"]:
        frame = yf.download(ticker, start="2005-01-01", end="2026-01-01", auto_adjust=True, progress=False)
        close = frame["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        columns["FX" if ticker == "USDMXN=X" else ticker] = close
    raw = pd.DataFrame(columns)
    data = raw.dropna()
    validate(data)
    if data.index[-1] < pd.Timestamp("2025-12-30") or data.index[0] > pd.Timestamp("2005-01-10"):
        raise ValueError("Requested evaluation coverage is missing")
    data.to_csv(path, index_label="date")
    return data, len(raw) - len(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path)
    parser.add_argument("--output", type=Path, default=Path("research/strategy32"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.data or args.output / "prices.csv"
    if args.data:
        data, dropped = pd.read_csv(source, index_col="date", parse_dates=True), None
    else:
        data, dropped = download(source)
    results = {}
    lines = ["# S32 frozen challenger evaluation", "", "Retrospective holdout; research simulation, not demonstrated live alpha. All results in MXN, distributions included; taxes excluded.", "", "30 bps one-way trading/FX costs; no interest on MXN cash. Annualization uses 252 observations. Observations with missing inputs are dropped, never forward-filled.", ""]
    for mode in ["trend", "equal", "spy", "cash"]:
        frame, events = simulate(data, mode)
        frame.to_csv(args.output / f"{mode}_nav.csv")
        (args.output / f"{mode}_ledger.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
        for name, start, end in [("reference", "2006", "2019"), ("holdout", "2020", "2025"), ("early_holdout", "2020", "2022"), ("late_holdout", "2023", "2025")]:
            results[f"{mode}_{name}"] = metrics(frame, start, end)
    stress, _ = simulate(data, cost=0.006)
    results["trend_double_cost_holdout"] = metrics(stress, "2020", "2025")
    trend, equal = results["trend_holdout"], results["equal_holdout"]
    accepted = trend["cagr"] > 0 and trend["sharpe"] > equal["sharpe"] and trend["max_dd"] > equal["max_dd"]
    lines += [f"**Predeclared screen: {'PASS (research only)' if accepted else 'FAIL — do not promote'}**", "", "| Model / period | CAGR | Sharpe (0% cash) | Max drawdown | Annual traded/NAV | Fees MXN |", "|---|---:|---:|---:|---:|---:|"]
    for key, result in results.items():
        lines.append(f"| {key} | {result['cagr']:.2%} | {result['sharpe']:.2f} | {result['max_dd']:.2%} | {result['turnover']:.2f} | {result['fees']:,.2f} |")
    lines += ["", "Fixed 6.53% cash sensitivity: CAGR 6.53%, drawdown 0% by construction; this is not historical Bondia and is not used to invent historical income.", "", "S8/S11/S12 comparisons remain unavailable because their reconstructed, equivalent histories are missing. This experiment cannot establish superiority over them."]
    fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()
    (args.output / "results.json").write_text(json.dumps(dict(params=PARAMS, sha256=fingerprint, dropped_rows=dropped, accepted=accepted, metrics=results), indent=2), encoding="utf-8")
    (args.output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
