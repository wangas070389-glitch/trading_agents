"""
S9 + S2/MACD Full Grid Search
==============================
Tests all combinations of:
  Timeframes:  30m, 1h, 2h (resampled), 4h (resampled), 1d
  Lookbacks:   30d, 60d, 90d, ALL (max available)

For each combo:
  - Downloads SPY at the given timeframe
  - Trains a 3-state GaussianHMM on the given lookback window
  - Classifies the FINAL regime (what the strategy sees right now)
  - Runs a simplified backtest to measure regime quality + portfolio returns

Key design:
  - HMM is trained ONCE on the lookback window (not re-trained daily).
    This is fast and measures the model quality at each config.
  - S9 simulation: routes capital Bull/Bear/Chop (simplified, no pairs trade)
  - S2/MACD simulation: uses HMM as allocation gate on SPY MACD signals

Output: formatted comparison table for all 20 combinations per strategy.

yfinance data limits (confirmed empirically):
  30m  -> max ~60 calendar days (~520 bars)
  1h   -> max ~730 calendar days (~5082 bars)
  2h   -> resampled from 1h (same limit)
  4h   -> resampled from 1h (same limit)
  1d   -> ~33 years (8416 bars from 1993)
"""
import os
import sys
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
INITIAL_NAV   = 200_000.0
MONTHLY_CONT  = 2_000.0
COMMISSION    = 0.0029
RF_DAILY_MXN  = 0.095 / 252.0   # 9.5% MXN cash yield
RF_DAILY_USD  = 0.045 / 252.0

TIMEFRAMES = {
    "30m":  {"yf_interval": "30m",  "period": "60d",  "bars_per_day": 13,  "resample": None},
    "1h":   {"yf_interval": "60m",  "period": "730d", "bars_per_day": 6.5, "resample": None},
    "2h":   {"yf_interval": "60m",  "period": "730d", "bars_per_day": 3.25,"resample": "2h"},
    "4h":   {"yf_interval": "60m",  "period": "730d", "bars_per_day": 1.5, "resample": "4h"},
    "1d":   {"yf_interval": "1d",   "period": "5y",   "bars_per_day": 1,   "resample": None},
}

# Lookback in TRADING DAYS (will be converted to bars per timeframe)
LOOKBACK_DAYS = {
    "30d":  30,
    "60d":  60,
    "90d":  90,
    "ALL":  None,   # use all available data
}

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def strip_tz(df):
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df

def resample_ohlcv(df, rule):
    """Resample 1h OHLCV bars to 2h or 4h."""
    return df.resample(rule, closed="left", label="left").agg(
        {"Open": "first", "High": "max", "Low": "min",
         "Close": "last", "Volume": "sum"}
    ).dropna()

def download_spy(tf_cfg):
    raw = yf.download("SPY", period=tf_cfg["period"],
                      interval=tf_cfg["yf_interval"], progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0] for c in raw.columns]
    raw = strip_tz(raw)
    if tf_cfg["resample"]:
        raw = resample_ohlcv(raw, tf_cfg["resample"])
    return raw

def fit_hmm(returns_arr):
    """Fit 3-state GaussianHMM. Returns model + (bull_state, bear_state, chop_state)."""
    arr = returns_arr.reshape(-1, 1)
    model = GaussianHMM(n_components=3, covariance_type="diag",
                        n_iter=200, random_state=42)
    model.fit(arr)
    states = model.predict(arr)
    # Label by volatility (bear=highest vol) and mean (bull=highest mean)
    means = [np.mean(arr[states == i]) if np.any(states == i) else 0.0  for i in range(3)]
    vols  = [np.std(arr[states == i])  if np.any(states == i) else 1e9  for i in range(3)]
    bear  = int(np.argmax(vols))
    rem   = [i for i in range(3) if i != bear]
    bull  = rem[0] if means[rem[0]] >= means[rem[1]] else rem[1]
    chop  = [i for i in range(3) if i != bear and i != bull][0]
    return model, states, bull, bear, chop

def regime_metrics(states, bull, bear, chop, returns_arr):
    """Compute regime quality diagnostics."""
    n = len(states)
    pct_bull = np.mean(states == bull) * 100
    pct_bear = np.mean(states == bear) * 100
    pct_chop = np.mean(states == chop) * 100
    # Transition rate (fraction of bars where state changes)
    transitions = np.sum(np.diff(states) != 0) / max(n - 1, 1) * 100
    # State separation: ratio of between-state variance to within-state variance
    group_means = [np.mean(returns_arr[states == i]) for i in range(3) if np.any(states == i)]
    overall_mean = np.mean(returns_arr)
    between_var = np.var(group_means) if len(group_means) > 1 else 0.0
    within_var  = np.mean([np.var(returns_arr[states == i]) for i in range(3) if np.any(states == i)])
    separation = between_var / max(within_var, 1e-12)
    return pct_bull, pct_bear, pct_chop, transitions, separation

# ─────────────────────────────────────────
# S9 SIMPLIFIED BACKTEST
#   Bull  -> 80% equity (S1+S4 proxy = SPY×1.0), 20% cash
#   Bear  -> 50% GLD,  50% cash
#   Chop  -> 100% cash (stat-arb modeled as 0 contribution for simplicity)
# ─────────────────────────────────────────
def s9_backtest(spy_df, gld_daily, lookback_bars, tf_bars_per_day):
    """
    Walk-forward S9 simulation:
    - Retrain HMM every 21 bars (approx monthly) on trailing `lookback_bars`
    - Route allocation: Bull=SPY, Bear=GLD, Chop=Cash
    """
    spy_ret = spy_df["Close"].pct_change().fillna(0.0)
    # For non-daily timeframes, aggregate daily GLD to match frequency
    # We compare by date; for sub-daily we use the last intrabar return for that day
    nav = INITIAL_NAV
    nav_list = []
    retrain_every = max(1, int(21 * tf_bars_per_day))  # ~monthly
    min_bars = max(50, lookback_bars if lookback_bars else 50)

    regime = 2   # start neutral
    bull_s, bear_s, chop_s = 1, 0, 2   # defaults until first HMM

    for i, (date, ret) in enumerate(spy_ret.items()):
        if i < min_bars:
            nav_list.append(nav)
            continue

        # Retrain periodically
        if i % retrain_every == 0:
            window = spy_ret.iloc[max(0, i - (lookback_bars or i)):i]
            if len(window) >= 30:
                try:
                    model, states, bull_s, bear_s, chop_s = fit_hmm(window.values)
                    cur_raw = model.predict(window.values.reshape(-1, 1))[-1]
                    if cur_raw == bull_s:
                        regime = 0
                    elif cur_raw == bear_s:
                        regime = 1
                    else:
                        regime = 2
                except Exception:
                    regime = 2

        # Get GLD return for this bar (approximate as daily for all timeframes)
        date_key = pd.Timestamp(date).normalize()
        gld_ret = gld_daily.get(date_key, 0.0) if isinstance(gld_daily, dict) else 0.0

        if regime == 0:   # Bull: ride SPY
            nav *= (1.0 + ret * 0.80)
            nav *= (1.0 + RF_DAILY_MXN * 0.20)
        elif regime == 1: # Bear: GLD + cash
            nav *= (1.0 + gld_ret * 0.50)
            nav *= (1.0 + RF_DAILY_MXN * 0.50)
        else:             # Chop: full cash
            nav *= (1.0 + RF_DAILY_MXN)

        nav_list.append(nav)

    nav_series = pd.Series(nav_list, index=spy_ret.index[:len(nav_list)])
    if len(nav_series) < 10:
        return None
    rets = nav_series.pct_change().dropna()
    total_return = (nav_series.iloc[-1] / nav_series.iloc[0] - 1.0) * 100.0
    # Annualize based on bars per day
    sharpe = rets.mean() / rets.std() * np.sqrt(252 * tf_bars_per_day) if rets.std() > 0 else 0.0
    rolling_max = nav_series.cummax()
    max_dd = ((nav_series - rolling_max) / rolling_max).min() * 100.0
    return total_return, sharpe, max_dd, nav_series.iloc[-1]

# ─────────────────────────────────────────
# S2/MACD SIMPLIFIED BACKTEST
#   MACD crossover on SPY at the given timeframe
#   HMM gates max equity exposure: Bull=95%, Sideways=50%, Bear=10%
#   Position size = max_exposure on each MACD buy; exit on MACD sell
# ─────────────────────────────────────────
def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig  = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig

def s2_macd_backtest(spy_df, lookback_bars, tf_bars_per_day):
    """MACD trend on SPY at the given timeframe, gated by HMM regime."""
    close = spy_df["Close"]
    ret   = close.pct_change().fillna(0.0)
    macd, sig = calc_macd(close)

    nav  = INITIAL_NAV
    nav_list = []
    in_position = False
    max_exposure = 0.50
    retrain_every = max(1, int(21 * tf_bars_per_day))
    min_bars = max(50, lookback_bars if lookback_bars else 50)
    regime = 0
    bull_s, bear_s, chop_s = 0, 2, 1

    for i in range(len(ret)):
        if i < min_bars:
            nav_list.append(nav)
            continue

        # Periodic HMM retrain
        if i % retrain_every == 0:
            window = ret.iloc[max(0, i - (lookback_bars or i)):i]
            if len(window) >= 30:
                try:
                    model, states, bull_s, bear_s, chop_s = fit_hmm(window.values)
                    cur_raw = model.predict(window.values.reshape(-1, 1))[-1]
                    if cur_raw == bull_s:
                        regime = 0
                        max_exposure = 0.95
                    elif cur_raw == bear_s:
                        regime = -1
                        max_exposure = 0.10
                    else:
                        regime = 1
                        max_exposure = 0.50
                except Exception:
                    pass

        # MACD crossover signals (previous bar → current bar)
        if i > 0:
            prev_cross = macd.iloc[i-1] - sig.iloc[i-1]
            curr_cross = macd.iloc[i]   - sig.iloc[i]
            if prev_cross <= 0 and curr_cross > 0:   # bullish crossover
                in_position = True
            elif prev_cross >= 0 and curr_cross < 0: # bearish crossover
                in_position = False

        # P&L
        bar_ret = ret.iloc[i]
        if in_position:
            nav *= (1.0 + bar_ret * max_exposure)
            nav *= (1.0 + RF_DAILY_MXN * (1.0 - max_exposure))
        else:
            nav *= (1.0 + RF_DAILY_MXN)

        nav_list.append(nav)

    nav_series = pd.Series(nav_list, index=ret.index[:len(nav_list)])
    if len(nav_series) < 10:
        return None
    rets = nav_series.pct_change().dropna()
    total_return = (nav_series.iloc[-1] / nav_series.iloc[0] - 1.0) * 100.0
    sharpe = rets.mean() / rets.std() * np.sqrt(252 * tf_bars_per_day) if rets.std() > 0 else 0.0
    rolling_max = nav_series.cummax()
    max_dd = ((nav_series - rolling_max) / rolling_max).min() * 100.0
    return total_return, sharpe, max_dd, nav_series.iloc[-1]

# ─────────────────────────────────────────
# MAIN GRID SEARCH
# ─────────────────────────────────────────
def run_grid():
    print("=" * 80)
    print("S9 + S2/MACD FULL GRID SEARCH: Timeframe × Lookback")
    print("=" * 80)

    # Download GLD daily for S9 Bear-regime returns
    print("\nDownloading GLD daily for S9 Bear-regime allocation...")
    gld_raw = yf.download("GLD", period="5y", interval="1d", progress=False)
    if isinstance(gld_raw.columns, pd.MultiIndex):
        gld_raw.columns = [c[0] for c in gld_raw.columns]
    gld_raw = strip_tz(gld_raw)
    gld_daily_ret = gld_raw["Close"].pct_change().fillna(0.0)
    gld_dict = {pd.Timestamp(d).normalize(): v for d, v in gld_daily_ret.items()}

    s9_results   = {}
    s2_results   = {}
    hmm_quality  = {}

    for tf_name, tf_cfg in TIMEFRAMES.items():
        print(f"\n{'-'*60}")
        print(f"Downloading SPY @ {tf_name}  (period={tf_cfg['period']})")
        try:
            spy_df = download_spy(tf_cfg)
            if spy_df.empty or len(spy_df) < 30:
                print(f"  SKIP: insufficient data ({len(spy_df)} bars)")
                continue
            print(f"  Got {len(spy_df)} bars from {str(spy_df.index[0])[:10]}")
        except Exception as e:
            print(f"  SKIP: download failed — {e}")
            continue

        bars_per_day = tf_cfg["bars_per_day"]
        spy_ret = spy_df["Close"].pct_change().fillna(0.0)

        for lb_name, lb_days in LOOKBACK_DAYS.items():
            # Convert lookback days → bars
            if lb_days is None:
                lb_bars = None
                actual_bars = len(spy_ret)
            else:
                lb_bars = int(lb_days * bars_per_day)
                actual_bars = min(lb_bars, len(spy_ret))

            # Skip impossible combos (e.g. 90d lookback on 30m data that only has 60d)
            if lb_days and lb_bars > len(spy_ret):
                tag = f"{tf_name}/{lb_name}"
                note = f"N/A (only {len(spy_ret)} bars available, need {lb_bars})"
                s9_results[tag]  = note
                s2_results[tag]  = note
                hmm_quality[tag] = note
                print(f"  {lb_name:<6}: SKIP — {note}")
                continue

            tag = f"{tf_name}/{lb_name}"
            print(f"  {lb_name:<6}: {actual_bars} bars for HMM training...", end=" ", flush=True)

            # ── HMM quality diagnostics ──
            window_ret = spy_ret.values[-actual_bars:] if lb_bars else spy_ret.values
            try:
                model, states, bull_s, bear_s, chop_s = fit_hmm(window_ret)
                pb, pbr, pch, trans, sep = regime_metrics(
                    states, bull_s, bear_s, chop_s, window_ret)
                hmm_quality[tag] = (pb, pbr, pch, trans, sep)
                hmm_ok = True
            except Exception as e:
                hmm_quality[tag] = f"HMM FAILED: {e}"
                hmm_ok = False

            # ── S9 backtest ──
            try:
                r9 = s9_backtest(spy_df, gld_dict, lb_bars, bars_per_day)
                s9_results[tag] = r9 if r9 else "N/A"
            except Exception as e:
                s9_results[tag] = f"ERR: {e}"

            # ── S2/MACD backtest ──
            try:
                r2 = s2_macd_backtest(spy_df, lb_bars, bars_per_day)
                s2_results[tag] = r2 if r2 else "N/A"
            except Exception as e:
                s2_results[tag] = f"ERR: {e}"

            if isinstance(s9_results[tag], tuple) and isinstance(s2_results[tag], tuple):
                ret9, sh9, dd9, _ = s9_results[tag]
                ret2, sh2, dd2, _ = s2_results[tag]
                print(f"S9: {ret9:+.1f}% Sh={sh9:.2f} DD={dd9:.1f}% | "
                      f"S2: {ret2:+.1f}% Sh={sh2:.2f} DD={dd2:.1f}%")
            else:
                print()

    # ── PRINT FULL COMPARISON TABLES ──
    print("\n\n" + "=" * 90)
    print("STRATEGY 9: HMM REGIME STAT-ARB — GRID SEARCH RESULTS")
    print("=" * 90)
    print(f"{'Config':<12} {'Return':>9} {'Sharpe':>9} {'MaxDD':>9} {'Final NAV':>14}")
    print("-" * 90)
    for tf_name in TIMEFRAMES:
        for lb_name in LOOKBACK_DAYS:
            tag = f"{tf_name}/{lb_name}"
            v = s9_results.get(tag, "—")
            if isinstance(v, tuple):
                ret, sh, dd, nav = v
                print(f"{tag:<12} {ret:>+8.2f}% {sh:>9.3f} {dd:>8.2f}% ${nav:>12,.0f}")
            else:
                print(f"{tag:<12} {str(v):>50}")

    print("\n\n" + "=" * 90)
    print("STRATEGY 2/MACD: HMM-GATED MACD TREND — GRID SEARCH RESULTS")
    print("=" * 90)
    print(f"{'Config':<12} {'Return':>9} {'Sharpe':>9} {'MaxDD':>9} {'Final NAV':>14}")
    print("-" * 90)
    for tf_name in TIMEFRAMES:
        for lb_name in LOOKBACK_DAYS:
            tag = f"{tf_name}/{lb_name}"
            v = s2_results.get(tag, "—")
            if isinstance(v, tuple):
                ret, sh, dd, nav = v
                print(f"{tag:<12} {ret:>+8.2f}% {sh:>9.3f} {dd:>8.2f}% ${nav:>12,.0f}")
            else:
                print(f"{tag:<12} {str(v):>50}")

    print("\n\n" + "=" * 90)
    print("HMM REGIME QUALITY: %Bull | %Bear | %Chop | TransRate | Separation")
    print("=" * 90)
    print(f"{'Config':<12} {'%Bull':>7} {'%Bear':>7} {'%Chop':>7} {'Trans%':>8} {'Sep':>8}")
    print("-" * 90)
    for tf_name in TIMEFRAMES:
        for lb_name in LOOKBACK_DAYS:
            tag = f"{tf_name}/{lb_name}"
            q = hmm_quality.get(tag, "—")
            if isinstance(q, tuple):
                pb, pbr, pch, tr, sep = q
                print(f"{tag:<12} {pb:>6.1f}% {pbr:>6.1f}% {pch:>6.1f}% {tr:>7.1f}% {sep:>8.4f}")
            else:
                print(f"{tag:<12} {str(q):>50}")


if __name__ == "__main__":
    run_grid()
