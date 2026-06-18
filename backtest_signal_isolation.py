"""
Signal Isolation Backtest — Phase 3

Tests 6 strategy variants on the same data to identify which signals
carry alpha on the BMV + US universe:

  1. Equal-weight (benchmark)
  2. DCS momentum (current strategy — buy high DCS)
  3. DCS mean-reversion (inverted — buy LOW DCS, avoid high)
  4. HMM risk filter (equal-weight, exit Bear-state tickers)
  5. GARCH vol-target (all tickers, inverse-vol sizing)
  6. 12-1 month momentum (classic Jegadeesh-Titman)

All variants use:
  - Same universe, same 5y data, same 0.29% cost
  - 5% dead-zone, 20% concentration cap
  - 21-day rebalance frequency

Run:  python backtest_signal_isolation.py
Out:  signal_isolation_report.md
"""

import os
import sys
import time
import datetime
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Stub NLP before importing agents
import skills.nlp_sentiment as _nlp_module


class _StubNLPEngine:
    def get_black_litterman_adjustments(self, tickers):
        return {t: 0.0 for t in tickers}


_nlp_module.NLPSentimentEngine = _StubNLPEngine

from agents.agents import FundamentalScreener, MacroRiskAnalyst
from ingest_live_bmv import BMV_TICKERS, US_TICKERS

# ---------- Config ----------
LOOKBACK_PERIOD = "5y"
REBALANCE_FREQ_DAYS = 21
MIN_HISTORY_DAYS = 252
TRANSACTION_COST = 0.0029
CONCENTRATION_CAP = 0.20
DEAD_ZONE = 0.05
INITIAL_CAPITAL = 20_000.0
TOP_N_MOMENTUM = 8  # for 12-1 momentum variant
MIN_POSITIONS = 5   # minimum diversification floor
# ----------------------------


def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df.index = pd.to_datetime(df.index.date)
    return df


def download_universe():
    """Download 5y data for all tickers + SPY + USD/MXN."""
    print("Downloading SPY and USD/MXN...")
    spy = _strip_tz(yf.Ticker("SPY").history(period=LOOKBACK_PERIOD))
    usdmxn = _strip_tz(yf.Ticker("MXN=X").history(period=LOOKBACK_PERIOD))
    if spy.empty or usdmxn.empty:
        raise RuntimeError("Failed to fetch SPY or USD/MXN")

    spy_ret = np.log(spy["Close"] / spy["Close"].shift(1))
    usdmxn_ret = np.log(usdmxn["Close"] / usdmxn["Close"].shift(1))
    exog = pd.DataFrame({"SPY_Ret": spy_ret, "USDMXN_Ret": usdmxn_ret}).dropna()
    fx_rate = usdmxn["Close"].rename("USDMXN_Rate")

    asset_data = {}
    for ticker in BMV_TICKERS + US_TICKERS:
        print(f"  {ticker}...", end=" ", flush=True)
        try:
            hist = _strip_tz(yf.Ticker(ticker).history(period=LOOKBACK_PERIOD))
            if hist.empty or len(hist) < MIN_HISTORY_DAYS:
                print(f"skip ({len(hist)} days)")
                continue
            if ticker in US_TICKERS:
                df = pd.DataFrame({"Close": hist["Close"], "Volume": hist["Volume"]}).join(fx_rate, how="inner")
                if df.empty:
                    print("skip (no FX)")
                    continue
                df["Close"] = df["Close"] * df["USDMXN_Rate"]
                hist = df[["Close", "Volume"]]
            asset_data[ticker] = hist
            print(f"OK ({len(hist)}d)")
        except Exception as exc:
            print(f"FAIL ({exc})")

    return asset_data, exog, fx_rate


def build_universe_data(asset_data, exog, as_of):
    """Build screener-compatible dict sliced to as_of."""
    universe = {}
    for ticker, hist in asset_data.items():
        sliced = hist.loc[hist.index <= as_of]
        if len(sliced) < 200:
            continue
        df = pd.DataFrame({"Price": sliced["Close"], "Volume": sliced["Volume"]})
        ret = np.log(df["Price"] / df["Price"].shift(1)).fillna(0.0)
        df["Ret"] = ret
        df_aligned = df.join(exog, how="inner").fillna(0.0)
        if len(df_aligned) < MIN_HISTORY_DAYS:
            continue
        universe[ticker] = {
            "prices": df_aligned["Price"].values,
            "volumes": df_aligned["Volume"].values,
            "exogenous": df_aligned[["SPY_Ret", "USDMXN_Ret"]].values,
        }
    return universe


def apply_cap(weights):
    """Enforce 20% cap on all weights."""
    capped = {}
    for t, w in weights.items():
        capped[t] = min(w, CONCENTRATION_CAP)
    total = sum(capped.values())
    if total > 1.0:
        capped = {t: w / total for t, w in capped.items()}
    return capped


# ─────────────────────────────────────────────────────────
# STRATEGY VARIANTS
# ─────────────────────────────────────────────────────────

def strategy_equal_weight(adjusted_metrics, asset_data_keys, price_matrix, as_of):
    """Variant 1: Equal-weight across all tickers."""
    tickers = list(asset_data_keys)
    n = len(tickers)
    if n == 0:
        return {}
    w = 1.0 / n
    weights = {t: w for t in tickers}
    return apply_cap(weights)


def strategy_dcs_momentum(adjusted_metrics, asset_data_keys, price_matrix, as_of):
    """Variant 2: Current strategy — buy high DCS ≥ 0.25 with relative_vol ≥ 1.2."""
    eligible = [
        t for t, m in adjusted_metrics.items()
        if m["dcs_adjusted"] >= 0.25 and m["relative_vol"] >= 1.2
    ]
    weights = {t: 0.0 for t in adjusted_metrics}
    if not eligible:
        return weights
    inv_vol = {t: 1.0 / max(adjusted_metrics[t]["garch_vol_adjusted"], 1e-4) for t in eligible}
    inv_sum = sum(inv_vol.values())
    raw = {t: (inv_vol[t] / inv_sum) * adjusted_metrics[t]["dcs_adjusted"] for t in eligible}
    for t, w in raw.items():
        weights[t] = w
    return apply_cap(weights)


def strategy_dcs_mean_reversion(adjusted_metrics, asset_data_keys, price_matrix, as_of):
    """Variant 3: DCS INVERTED — buy the LOWEST DCS (oversold), avoid highest."""
    all_tickers = list(adjusted_metrics.keys())
    if not all_tickers:
        return {}

    # Invert DCS: oversold names (low/negative DCS) get the highest score
    inverted_scores = {}
    for t, m in adjusted_metrics.items():
        inverted_scores[t] = -m["dcs_adjusted"]  # flip the sign

    # Rank and pick top N (most oversold)
    ranked = sorted(inverted_scores.keys(), key=lambda t: inverted_scores[t], reverse=True)
    n_pick = max(MIN_POSITIONS, len(ranked) // 4)  # top quartile, min 5
    selected = ranked[:n_pick]

    # Inverse-vol sizing
    inv_vol = {t: 1.0 / max(adjusted_metrics[t]["garch_vol_adjusted"], 1e-4) for t in selected}
    inv_sum = sum(inv_vol.values())
    weights = {t: 0.0 for t in adjusted_metrics}
    for t in selected:
        weights[t] = inv_vol[t] / inv_sum
    return apply_cap(weights)


def strategy_hmm_filter(adjusted_metrics, asset_data_keys, price_matrix, as_of):
    """Variant 4: Equal-weight, but EXIT any ticker in Bear state (HMM=-1)."""
    tickers = list(adjusted_metrics.keys())
    survivors = [t for t in tickers if adjusted_metrics[t].get("hmm_state", 0) != -1]
    if not survivors:
        survivors = tickers  # fallback: don't go 100% cash
    n = len(survivors)
    weights = {t: 0.0 for t in adjusted_metrics}
    for t in survivors:
        weights[t] = 1.0 / n
    return apply_cap(weights)


def strategy_garch_vol_target(adjusted_metrics, asset_data_keys, price_matrix, as_of):
    """Variant 5: All tickers, sized by inverse GARCH vol (risk parity)."""
    tickers = list(adjusted_metrics.keys())
    if not tickers:
        return {}
    inv_vol = {t: 1.0 / max(adjusted_metrics[t]["garch_vol_adjusted"], 1e-4) for t in tickers}
    inv_sum = sum(inv_vol.values())
    weights = {t: inv_vol[t] / inv_sum for t in tickers}
    return apply_cap(weights)


def strategy_momentum_12_1(adjusted_metrics, asset_data_keys, price_matrix, as_of):
    """Variant 6: 12-1 month momentum (Jegadeesh-Titman).
    Long top N by 12-month return, skipping the most recent month."""
    weights = {t: 0.0 for t in asset_data_keys}

    # Compute 12-1 momentum for each ticker
    momentum_scores = {}
    for ticker in asset_data_keys:
        if ticker not in price_matrix.columns:
            continue
        prices = price_matrix[ticker].loc[price_matrix[ticker].index <= as_of].dropna()
        if len(prices) < 252:
            continue
        # 12-month return minus last 1 month
        price_12m_ago = prices.iloc[-252]
        price_1m_ago = prices.iloc[-21]
        if price_12m_ago > 0:
            mom = (price_1m_ago / price_12m_ago) - 1.0
            momentum_scores[ticker] = mom

    if not momentum_scores:
        return weights

    # Rank and pick top N
    ranked = sorted(momentum_scores.keys(), key=lambda t: momentum_scores[t], reverse=True)
    n_pick = min(TOP_N_MOMENTUM, len(ranked))
    selected = ranked[:n_pick]

    # Equal-weight among selected
    w = 1.0 / n_pick
    for t in selected:
        weights[t] = w
    return apply_cap(weights)


# ─────────────────────────────────────────────────────────
# BACKTEST ENGINE
# ─────────────────────────────────────────────────────────

def run_single_backtest(strategy_fn, name, asset_data, exog, price_matrix, rebalance_dates,
                        needs_metrics=True):
    """Run a single strategy variant and return NAV series + trade stats."""
    print(f"\n{'='*60}")
    print(f"  RUNNING: {name}")
    print(f"{'='*60}")

    cash = INITIAL_CAPITAL
    shares_held = {t: 0.0 for t in asset_data}
    nav_series = {}
    trade_count = 0
    total_traded_value = 0.0
    total_fees = 0.0
    rebalance_idx = 0

    screener = FundamentalScreener()
    analyst = MacroRiskAnalyst()

    for i, current_date in enumerate(price_matrix.index):
        if rebalance_idx < len(rebalance_dates) and current_date >= rebalance_dates[rebalance_idx]:
            try:
                if needs_metrics:
                    universe = build_universe_data(asset_data, exog, current_date)
                    if universe:
                        raw_metrics = screener.screen(universe)
                        if raw_metrics:
                            adjusted = analyst.stress_test(raw_metrics, {})
                            target_weights = strategy_fn(adjusted, asset_data.keys(), price_matrix, current_date)
                        else:
                            target_weights = strategy_fn({}, asset_data.keys(), price_matrix, current_date)
                    else:
                        target_weights = strategy_fn({}, asset_data.keys(), price_matrix, current_date)
                else:
                    target_weights = strategy_fn({}, asset_data.keys(), price_matrix, current_date)

                # Compute portfolio value
                portfolio_value = cash + sum(
                    shares_held[t] * price_matrix[t].iloc[i] for t in shares_held
                )

                # Execute trades with dead-zone
                for ticker in asset_data:
                    target_value = portfolio_value * target_weights.get(ticker, 0.0)
                    current_value = shares_held[ticker] * price_matrix[ticker].iloc[i]
                    delta_value = target_value - current_value

                    # Dead-zone check
                    current_weight = current_value / portfolio_value if portfolio_value > 0 else 0.0
                    target_w = target_weights.get(ticker, 0.0)
                    w_delta = abs(target_w - current_weight)
                    if w_delta < DEAD_ZONE and shares_held[ticker] > 0:
                        continue

                    if abs(delta_value) < 50:
                        continue

                    delta_shares = delta_value / price_matrix[ticker].iloc[i]
                    cost = abs(delta_value) * TRANSACTION_COST
                    cash -= (delta_value + cost)
                    shares_held[ticker] += delta_shares
                    total_traded_value += abs(delta_value)
                    total_fees += cost
                    trade_count += 1

            except Exception as exc:
                pass  # silently skip failed rebalances (same as main backtest)
            rebalance_idx += 1

        # Track daily NAV
        equity = sum(shares_held[t] * price_matrix[t].iloc[i] for t in shares_held)
        nav_series[current_date] = cash + equity

    return pd.Series(nav_series, name=name), trade_count, total_traded_value, total_fees


def compute_metrics(nav_series):
    """Compute CAGR, Sharpe, max drawdown from NAV series."""
    returns = nav_series.pct_change().dropna()
    if len(returns) < 2:
        return {"cagr": 0, "sharpe": 0, "max_dd": 0, "total_return": 0, "final_nav": nav_series.iloc[-1]}

    total_return = (nav_series.iloc[-1] / nav_series.iloc[0]) - 1.0
    n_years = len(returns) / 252.0
    cagr = (1 + total_return) ** (1 / max(n_years, 0.01)) - 1.0
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0
    cumulative = (1 + returns).cumprod()
    max_dd = (cumulative / cumulative.cummax() - 1).min()

    return {
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "total_return": total_return,
        "final_nav": nav_series.iloc[-1],
    }


def main():
    print("=" * 80)
    print("SIGNAL ISOLATION BACKTEST - PHASE 3")
    print("=" * 80)

    asset_data, exog, fx_rate = download_universe()
    if not asset_data:
        print("No data. Aborting.")
        return
    print(f"\nUniverse: {len(asset_data)} tickers\n")

    # Build common infrastructure
    all_dates = sorted(set().union(*(set(df.index) for df in asset_data.values())))
    price_matrix = pd.DataFrame(index=all_dates)
    for ticker, hist in asset_data.items():
        price_matrix[ticker] = hist["Close"]
    price_matrix = price_matrix.ffill().bfill()

    # Rebalance dates
    start_idx = MIN_HISTORY_DAYS
    trading_days = [d for d in all_dates if d.weekday() < 5]
    rebalance_dates = trading_days[start_idx::REBALANCE_FREQ_DAYS]
    backtest_start = rebalance_dates[0]
    price_matrix = price_matrix.loc[price_matrix.index >= backtest_start]

    print(f"Backtest: {price_matrix.index[0].date()} to {price_matrix.index[-1].date()}")
    print(f"Rebalance dates: {len(rebalance_dates)}\n")

    # Define strategy variants
    strategies = [
        ("1. Equal-Weight", strategy_equal_weight, False),
        ("2. DCS Momentum (current)", strategy_dcs_momentum, True),
        ("3. DCS Mean-Reversion (Best-of)", strategy_dcs_mean_reversion, True),
        ("4. HMM Risk Filter", strategy_hmm_filter, True),
        ("5. GARCH Vol-Target", strategy_garch_vol_target, True),
        ("6. 12-1 Momentum (Classic)", strategy_momentum_12_1, False),
    ]

    results = []
    t_start = time.time()

    for name, fn, needs_metrics in strategies:
        nav, trades, traded_val, fees = run_single_backtest(
            fn, name, asset_data, exog, price_matrix, rebalance_dates,
            needs_metrics=needs_metrics
        )
        metrics = compute_metrics(nav)
        results.append({
            "name": name,
            "nav": nav,
            "trades": trades,
            "traded_value": traded_val,
            "fees": fees,
            **metrics,
        })
        print(f"  -> {name}: CAGR={metrics['cagr']:.2%}, Sharpe={metrics['sharpe']:.2f}, MaxDD={metrics['max_dd']:.2%}, Trades={trades}")

    elapsed = time.time() - t_start
    print(f"\nAll variants completed in {elapsed:.0f}s")

    # Sort by CAGR descending
    results.sort(key=lambda r: r["cagr"], reverse=True)

    # Write report
    base_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(base_dir, "signal_isolation_report.md")

    ew_cagr = next(r["cagr"] for r in results if "Equal-Weight" in r["name"])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Signal Isolation Backtest Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Universe:** {len(asset_data)} tickers | ")
        f.write(f"**Period:** {price_matrix.index[0].date()} to {price_matrix.index[-1].date()} | ")
        f.write(f"**Cost:** {TRANSACTION_COST:.2%} per trade | ")
        f.write(f"**Dead-zone:** {DEAD_ZONE:.0%} | ")
        f.write(f"**Cap:** {CONCENTRATION_CAP:.0%}\n\n")

        f.write("## Results (Ranked by CAGR)\n\n")
        f.write("| Rank | Strategy | CAGR | Sharpe | Max DD | Trades | Fees | vs EW |\n")
        f.write("| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |\n")

        for i, r in enumerate(results):
            vs_ew = r["cagr"] - ew_cagr
            vs_str = f"+{vs_ew:.2%}" if vs_ew >= 0 else f"{vs_ew:.2%}"
            medal = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else f"{i+1}"))
            f.write(f"| {medal} | {r['name']} | {r['cagr']:.2%} | {r['sharpe']:.2f} | "
                    f"{r['max_dd']:.2%} | {r['trades']} | ${r['fees']:,.0f} | {vs_str} |\n")

        f.write("\n## Interpretation\n\n")

        # Find winners (beat equal-weight)
        winners = [r for r in results if r["cagr"] > ew_cagr and "Equal-Weight" not in r["name"]]
        losers = [r for r in results if r["cagr"] <= ew_cagr and "Equal-Weight" not in r["name"]]

        if winners:
            f.write("### Signals With Alpha\n\n")
            for r in winners:
                vs_ew = r["cagr"] - ew_cagr
                f.write(f"- **{r['name']}**: +{vs_ew:.2%} CAGR over equal-weight, "
                        f"Sharpe {r['sharpe']:.2f}\n")
            f.write("\n")

        if losers:
            f.write("### Signals Without Alpha (noise)\n\n")
            for r in losers:
                vs_ew = r["cagr"] - ew_cagr
                f.write(f"- **{r['name']}**: {vs_ew:.2%} CAGR vs equal-weight\n")
            f.write("\n")

        # Recommendation
        f.write("## Recommended Architecture\n\n")
        if winners:
            best = winners[0]
            f.write(f"**Use {best['name']}** as the primary signal, combined with:\n")
            for w in winners[1:]:
                f.write(f"- {w['name']} as a secondary factor\n")
            f.write(f"\nTarget: Multi-factor composite of winning signals.\n")
        else:
            f.write("**No single signal beat equal-weight.** Recommended: equal-weight base "
                    "with risk overlay (HMM veto on worst drawdowns).\n")

        # Final NAV comparison
        f.write("\n## Final NAV Comparison\n\n")
        f.write("| Strategy | Initial | Final | Total Return |\n")
        f.write("| :--- | ---: | ---: | ---: |\n")
        for r in results:
            f.write(f"| {r['name']} | $20,000 | ${r['final_nav']:,.0f} | {r['total_return']:.2%} |\n")

    print(f"\nReport saved: {report_path}")

    # Save NAV curves for plotting
    nav_df = pd.DataFrame({r["name"]: r["nav"] for r in results})
    nav_path = os.path.join(base_dir, "signal_isolation_nav.csv")
    nav_df.to_csv(nav_path)
    print(f"NAV curves saved: {nav_path}")


if __name__ == "__main__":
    main()
