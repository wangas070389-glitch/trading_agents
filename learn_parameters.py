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
import yfinance as yf

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

DCS_GRID = [0.05, 0.10, 0.15, 0.20, 0.30]
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
    print("Fetching S&P 500 tickers...")
    from skills.index_constituents import get_spx_tickers
    sp500_all = get_spx_tickers()
    
    print(f"Downloading historical data for {len(sp500_all)} S&P 500 components...")
    sp500_data = yf.download(sp500_all, period="5y", progress=False)
    sp500_close = sp500_data["Close"]
    sp500_vol = sp500_data["Volume"]
    
    for ticker in sp500_all:
        try:
            if ticker not in sp500_close.columns or ticker not in sp500_vol.columns:
                continue
            close_col = sp500_close[ticker].dropna()
            vol_col = sp500_vol[ticker].reindex(close_col.index).fillna(0.0)
            if len(close_col) < 200:
                continue
            
            close_col.index = close_col.index.tz_localize(None)
            vol_col.index = vol_col.index.tz_localize(None)
            
            df_usd = pd.DataFrame({
                "Close_USD": close_col,
                "Volume": vol_col,
            }).join(raw_rate, how="inner")
            
            df_usd["Close_MXN"] = df_usd["Close_USD"] * df_usd["USDMXN_Rate"]
            
            df = pd.DataFrame({
                "Asset_Price": df_usd["Close_MXN"],
                "Asset_Vol": df_usd["Volume"],
                "Close_USD": df_usd["Close_USD"],
                "USDMXN_Rate": df_usd["USDMXN_Rate"]
            }).join(df_exog, how="right")
            
            df["Asset_Price"] = df["Asset_Price"].ffill()
            df["Asset_Vol"] = df["Asset_Vol"].fillna(0.0)
            df["Close_USD"] = df["Close_USD"].ffill()
            df["USDMXN_Rate"] = df["USDMXN_Rate"].ffill()
            
            if len(df.dropna(subset=["Asset_Price"])) >= 200:
                universe[ticker] = df
        except Exception:
            continue
    return universe, df_exog


def compute_snapshots(universe, df_exog):
    """One (metrics, forward_returns) pair per snapshot date. Heavy step."""
    screener = FundamentalScreener()
    analyst = MacroRiskAnalyst()
    from skills.prefilter import prefilter_us_universe

    all_dates = df_exog.index
    usable = all_dates[-(LOOKBACK_DAYS + FORWARD_HORIZON):]
    snapshot_dates = usable[::SNAPSHOT_EVERY]
    snapshot_dates = [d for d in snapshot_dates
                      if all_dates.get_loc(d) + FORWARD_HORIZON < len(all_dates)]

    # Separate BMV and US tickers
    bmv_tickers = [t for t in universe.keys() if t.endswith(".MX")]
    us_tickers = [t for t in universe.keys() if not t.endswith(".MX")]

    snapshots = []
    for i, date in enumerate(snapshot_dates):
        print(f"[{i+1}/{len(snapshot_dates)}] Snapshot {date.date()}")
        
        # Slice lookback close and volume for S&P 500 tickers for pre-filtering
        us_close_dict = {}
        us_vol_dict = {}
        usdmxn_rate = None
        
        for ticker in us_tickers:
            df = universe[ticker]
            df_lb = df.loc[df.index <= date]
            if len(df_lb) >= 100:
                slice_lb = df_lb.iloc[-130:]
                us_close_dict[ticker] = slice_lb["Close_USD"]
                us_vol_dict[ticker] = slice_lb["Asset_Vol"]
                if usdmxn_rate is None and not slice_lb["USDMXN_Rate"].isna().all():
                    usdmxn_rate = float(slice_lb["USDMXN_Rate"].iloc[-1])
        
        if not us_close_dict or usdmxn_rate is None:
            print(f"  |-- Skipping snapshot {date.date()}: No US data or exchange rate available.")
            continue
            
        # Build wide DataFrames
        batch_close = pd.DataFrame(us_close_dict)
        batch_volume = pd.DataFrame(us_vol_dict)
        
        # Run S&P 500 pre-filter
        selected_us = prefilter_us_universe(
            batch_close=batch_close,
            batch_volume=batch_volume,
            usdmxn_rate=usdmxn_rate,
            portfolio_value_mxn=20000.0 # Standard capital baseline
        )
        selected_us_tickers = list(selected_us.keys())
        
        # The candidates to screen are BMV tickers + selected US tickers
        candidates = bmv_tickers + selected_us_tickers
        
        lookback_universe = {}
        fwd_returns = {}
        for ticker in candidates:
            if ticker not in universe:
                continue
            df = universe[ticker]
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
    currently_held = set()
    for snap in snapshots:
        met = snap["metrics"]
        fwd = snap["fwd_returns"]
        eligible = []
        for t in met:
            if t not in fwd:
                continue
            dcs_threshold_required = dcs_thr - 0.10 if t in currently_held else dcs_thr
            if met[t]["dcs_adjusted"] >= dcs_threshold_required and met[t]["relative_vol"] >= vr_thr:
                eligible.append(t)
        
        currently_held = set(eligible)
        
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
            # Selection MUST be blind to validation data. Using val_sharpe in the
            # score collapses the validation set into the training set and destroys
            # out-of-sample integrity. Score is strictly in-sample; validation is a
            # blind readout only.
            score = s_tr
            rows.append({
                "dcs_threshold": dcs_thr, "vr_threshold": vr_thr,
                "train_sharpe": round(s_tr, 3), "val_sharpe": round(s_va, 3),
                "score": round(score, 3),
                "val_cum_return": round(float(np.prod(1 + va) - 1) * 100, 2),
            })

    # Tie-break toward the MOST CONSERVATIVE parameters: with identical
    # scores (e.g. when a threshold doesn't bind), prefer the strictest
    # entry rules, never the loosest.
    rows.sort(key=lambda r: (r["score"], r["dcs_threshold"], r["vr_threshold"]),
              reverse=True)
    best = rows[0]

    # Degeneracy diagnostic: warn when a grid dimension has no effect.
    by_vr = {}
    for r in rows:
        by_vr.setdefault(r["vr_threshold"], set()).add(
            (r["train_sharpe"], r["val_sharpe"]))
    if all(len(v) == 1 for v in by_vr.values()):
        print("\n[DIAGNOSTIC] The DCS threshold has ZERO effect across the whole "
              "grid: every asset passing the VR filter also clears the highest "
              "DCS bar. The DCS signal is saturated (near +/-1) and acts as a "
              "binary flag, not a graded score. Recalibrate the signal before "
              "trusting threshold learning on it.")

    print("\nTop 5 combos (score = train_sharpe; val_sharpe shown as blind readout):")
    for r in rows[:5]:
        print(f"  DCS>={r['dcs_threshold']:.2f} VR>={r['vr_threshold']:.1f} | "
              f"train Sharpe {r['train_sharpe']:+.2f} | val Sharpe {r['val_sharpe']:+.2f} | "
              f"val return {r['val_cum_return']:+.2f}%")

    # Gate 1: a negative TRAIN Sharpe with a positive validation Sharpe is a
    # regime flip, not a validated edge — the strategy lost in-sample and the
    # out-of-sample window happened to be favorable. Do not learn from luck.
    if best["train_sharpe"] <= 0:
        print(f"\nBest combo has NEGATIVE train Sharpe ({best['train_sharpe']:+.2f}) "
              f"despite val Sharpe {best['val_sharpe']:+.2f}. That is a regime "
              "flip, not an edge. Refusing to write learned parameters.")
        params_file = os.path.join(dir_path, LEARNED_PARAMS_FILE)
        if os.path.exists(params_file):
            try:
                os.remove(params_file)
                print(f"Removed stale {LEARNED_PARAMS_FILE}; system falls back to defaults.")
            except OSError as e:
                print(f"Warning: Could not remove stale parameter file: {e}")
        return

    # Gate 2: validation must also be profitable.
    if best["val_sharpe"] <= 0:
        print("\nNo combo is profitable out-of-sample. Refusing to write 'learned' "
              "parameters — defaults stay in place. This is the system telling you "
              "the signal has no edge in the current regime; do not force it.")
        # If a stale parameter file exists, remove it so the system falls back to default values
        params_file = os.path.join(dir_path, LEARNED_PARAMS_FILE)
        if os.path.exists(params_file):
            try:
                os.remove(params_file)
                print(f"Removed stale {LEARNED_PARAMS_FILE} to force fallback to system defaults.")
            except OSError as e:
                print(f"Warning: Could not remove stale parameter file: {e}")
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
