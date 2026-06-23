"""
Walk-forward learning of entry thresholds (DCS, relative volume).

Why this design
---------------
The expensive part of the pipeline (GARCH + HMM + Markov matrix per ticker)
does NOT depend on the thresholds — only eligibility and sizing do. So we:

  1. Compute one metric snapshot per rebalance date (heavy, done once).
  2. Grid-search threshold combos over the cached snapshots (cheap).
  3. Split snapshot dates 60/40 into train/validation. Score each combo on
     BOTH windows. Select by validation Sharpe MINUS an instability penalty
     |train_sharpe - val_sharpe|, so we prefer parameters that behave the
     same out-of-sample over parameters that merely got lucky in-sample.
  4. Write the winner to learned_params.json, which ingest_live_bmv.py
     loads on every run (with safe fallbacks).

Run weekly (or via the GitHub Action) — NOT on every daily run; relearning
thresholds daily on overlapping data is how you overfit.

Usage:  python learn_parameters.py
"""

import os
import json
import datetime
import numpy as np

from skills.liquidity_gatekeeper import calculate_adtv, passes_liquidity_gate
from skills.adaptive_learning import LEARNED_PARAMS_FILE
from agents.agents import FundamentalScreener, MacroRiskAnalyst
from ingest_live_bmv import (
    BMV_TICKERS, US_TICKERS,
    fetch_historical_exogenous, fetch_historical_asset,
)

import pandas as pd

LOOKBACK_DAYS = 250          # how far back snapshots go (~1 trading year)
SNAPSHOT_EVERY = 10          # business days between snapshots
FORWARD_HORIZON = 15         # business days a decision is held / scored
FEE = 0.0029
TRAIN_FRACTION = 0.6

DCS_GRID = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40]
VR_GRID = [1.0, 1.1, 1.2, 1.4]


def build_universe_history():
    df_exog, raw_rate = fetch_historical_exogenous()
    universe = {}
    for ticker in BMV_TICKERS:
        try:
            hist = fetch_historical_asset(ticker)
            if len(hist) < 200:
                continue
            hist.index = hist.index.tz_localize(None)
            df = pd.DataFrame({
                "Asset_Price": hist["Close"],
                "Asset_Vol": hist["Volume"],
            }).join(df_exog, how="right")
            df["Asset_Price"] = df["Asset_Price"].ffill()  # no bfill: no look-ahead
            df["Asset_Vol"] = df["Asset_Vol"].fillna(0.0)
            universe[ticker] = df
        except Exception:
            continue
    for ticker in US_TICKERS:
        try:
            hist = fetch_historical_asset(ticker)
            if len(hist) < 200:
                continue
            hist.index = hist.index.tz_localize(None)
            df_usd = pd.DataFrame({
                "Close_USD": hist["Close"],
                "Volume": hist["Volume"],
            }).join(raw_rate, how="inner")
            df_usd["Close_MXN"] = df_usd["Close_USD"] * df_usd["USDMXN_Rate"]
            df = pd.DataFrame({
                "Asset_Price": df_usd["Close_MXN"],
                "Asset_Vol": df_usd["Volume"],
            }).join(df_exog, how="right")
            df["Asset_Price"] = df["Asset_Price"].ffill()
            df["Asset_Vol"] = df["Asset_Vol"].fillna(0.0)
            universe[ticker] = df
        except Exception:
            continue
    return universe, df_exog


def compute_snapshots(universe, df_exog):
    """One (metrics, forward_returns) pair per snapshot date. Heavy step."""
    screener = FundamentalScreener()
    analyst = MacroRiskAnalyst()

    all_dates = df_exog.index
    usable = all_dates[-(LOOKBACK_DAYS + FORWARD_HORIZON):]
    snapshot_dates = usable[::SNAPSHOT_EVERY]
    # Need FORWARD_HORIZON days after each snapshot to score it
    snapshot_dates = [d for d in snapshot_dates
                      if all_dates.get_loc(d) + FORWARD_HORIZON < len(all_dates)]

    snapshots = []
    for i, date in enumerate(snapshot_dates):
        print(f"[{i+1}/{len(snapshot_dates)}] Snapshot {date.date()}")
        lookback_universe = {}
        fwd_returns = {}
        for ticker, df in universe.items():
            df_lb = df.loc[df.index <= date].dropna(subset=["Asset_Price"])
            if len(df_lb) < 120:
                continue
            prices_30 = df_lb["Asset_Price"].iloc[-30:].tolist()
            vols_30 = df_lb["Asset_Vol"].iloc[-30:].tolist()
            if not passes_liquidity_gate(calculate_adtv(prices_30, vols_30)):
                continue
            lookback_universe[ticker] = {
                "prices": df_lb["Asset_Price"].values,
                "volumes": df_lb["Asset_Vol"].values,
                "exogenous": df_lb[["SPY_Ret", "USDMXN_Ret"]].values,
            }
            # Forward return over the holding horizon (uses only future data
            # for SCORING, never for signal computation)
            loc = all_dates.get_loc(date)
            future_date = all_dates[loc + FORWARD_HORIZON]
            p_now = df["Asset_Price"].asof(date)
            p_fut = df["Asset_Price"].asof(future_date)
            if p_now and p_fut and p_now > 0:
                fwd_returns[ticker] = p_fut / p_now - 1.0

        if not lookback_universe:
            continue
        raw = screener.screen(lookback_universe)
        adjusted = analyst.stress_test(raw, {})
        snapshots.append({
            "date": str(date.date()),
            "metrics": adjusted,
            "fwd_returns": fwd_returns,
        })
    return snapshots


def simulate_combo(snapshots, dcs_thr, vr_thr):
    """Per-period portfolio returns for one threshold combo. Cheap step."""
    period_returns = []
    for snap in snapshots:
        met = snap["metrics"]
        fwd = snap["fwd_returns"]
        eligible = [t for t in met
                    if met[t]["dcs_adjusted"] >= dcs_thr
                    and met[t]["relative_vol"] >= vr_thr
                    and t in fwd]
        if not eligible:
            period_returns.append(0.0)  # cash (ignore Bondia for comparison)
            continue
        inv_vol = {t: 1.0 / met[t]["garch_vol_adjusted"] for t in eligible}
        s = sum(inv_vol.values())
        weights = {t: (inv_vol[t] / s) * met[t]["dcs_adjusted"] for t in eligible}
        weights = {t: min(w, 0.40) for t, w in weights.items()}
        gross = sum(weights.values())
        port_ret = sum(weights[t] * fwd[t] for t in eligible)
        turnover_cost = 2 * FEE * gross  # round-trip approximation
        period_returns.append(port_ret - turnover_cost)
    return np.array(period_returns)


def sharpe(returns, periods_per_year):
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0
    return float(np.sqrt(periods_per_year) * np.mean(returns) / np.std(returns))


def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("Building universe history...")
    universe, df_exog = build_universe_history()
    print(f"Universe: {len(universe)} tickers. Computing snapshots...")
    snapshots = compute_snapshots(universe, df_exog)
    if len(snapshots) < 8:
        print("Not enough snapshots to learn anything robust. Keeping current params.")
        return

    split = int(len(snapshots) * TRAIN_FRACTION)
    train, val = snapshots[:split], snapshots[split:]
    ppy = 252 / (SNAPSHOT_EVERY)

    rows = []
    for dcs_thr in DCS_GRID:
        for vr_thr in VR_GRID:
            tr = simulate_combo(train, dcs_thr, vr_thr)
            va = simulate_combo(val, dcs_thr, vr_thr)
            s_tr, s_va = sharpe(tr, ppy), sharpe(va, ppy)
            score = s_va - 0.5 * abs(s_tr - s_va)  # instability penalty
            rows.append({
                "dcs_threshold": dcs_thr, "vr_threshold": vr_thr,
                "train_sharpe": round(s_tr, 3), "val_sharpe": round(s_va, 3),
                "score": round(score, 3),
                "val_cum_return": round(float(np.prod(1 + va) - 1) * 100, 2),
            })

    rows.sort(key=lambda r: r["score"], reverse=True)
    best = rows[0]

    print("\nTop 5 combos (score = val_sharpe - 0.5*|train-val|):")
    for r in rows[:5]:
        print(f"  DCS>={r['dcs_threshold']:.2f} VR>={r['vr_threshold']:.1f} | "
              f"train Sharpe {r['train_sharpe']:+.2f} | val Sharpe {r['val_sharpe']:+.2f} | "
              f"val return {r['val_cum_return']:+.2f}%")

    if best["val_sharpe"] <= 0:
        print("\nNo combo is profitable out-of-sample. Refusing to write 'learned' "
              "parameters — defaults stay in place. This is the system telling you "
              "the signal has no edge in the current regime; do not force it.")
        return

    params = {
        "dcs_threshold": best["dcs_threshold"],
        "vr_threshold": best["vr_threshold"],
        "trained_on": datetime.date.today().isoformat(),
        "train_sharpe": best["train_sharpe"],
        "validation_sharpe": best["val_sharpe"],
        "grid_results": rows,
    }
    with open(os.path.join(dir_path, LEARNED_PARAMS_FILE), "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
    print(f"\nWrote {LEARNED_PARAMS_FILE}: DCS>={best['dcs_threshold']}, "
          f"VR>={best['vr_threshold']} (val Sharpe {best['val_sharpe']:+.2f})")


if __name__ == "__main__":
    main()
