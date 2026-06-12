"""
Walk-forward backtest of the live trading_agents strategy.

Pulls 5y of daily data for the BMV + US universe, then walks forward in
monthly rebalance steps. At each rebalance date the screener and macro
analyst run on data available up to that point, target weights are computed
with the 20% concentration cap, and trades are applied with a 0.29%
round-trip transaction cost. Daily NAV is tracked and compared against an
equal-weight buy-and-hold benchmark of the same universe.

Honest caveats baked in:
  * NLP sentiment is stubbed to zero — pulling live news in a backtest is
    forward-looking and would bias results. The macro registry (static)
    is still applied, which is itself a look-ahead since it was authored
    after-the-fact, but at least it doesn't move per run.
  * Statistical arbitrage regime adjustments are disabled (universe_prices_dict
    not passed). They depend on full-period cointegration estimates.
  * No survivorship adjustment — universe is the current IPC. Bias is
    toward overstating returns.
  * Slippage and bid-ask spread are folded into the 0.29% transaction cost.
    That is generous for liquid names, tight for the thinner ones.

Run:  python backtest_walkforward.py
Out:  backtest_report.md, backtest_nav.csv
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

# Stub out NLPSentimentEngine BEFORE importing agents to prevent live news fetch
import skills.nlp_sentiment as _nlp_module


class _StubNLPEngine:
    def get_black_litterman_adjustments(self, tickers):
        return {t: 0.0 for t in tickers}


_nlp_module.NLPSentimentEngine = _StubNLPEngine

from agents.agents import FundamentalScreener, MacroRiskAnalyst
from ingest_live_bmv import BMV_TICKERS, US_TICKERS


# ---------- Config ----------
LOOKBACK_PERIOD = "5y"
REBALANCE_FREQ_DAYS = 21         # monthly
MIN_HISTORY_DAYS = 252           # 1y warmup before backtest begins
TRANSACTION_COST = 0.0029        # 0.29% per side (matches live code)
CONCENTRATION_CAP = 0.20
INITIAL_CAPITAL = 20_000.0       # MXN
DCS_ENTRY_THRESHOLD = 0.25
RELVOL_ENTRY_THRESHOLD = 1.2
# ----------------------------


def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df


def download_universe() -> tuple[dict, pd.DataFrame, pd.Series]:
    """Pull 5y daily history for all tickers, plus SPY and USD/MXN exogenous.
    Returns (asset_data, exog_returns, usdmxn_rate). All US tickers converted to MXN."""
    print("Downloading SPY and USD/MXN exogenous regressors...")
    spy = _strip_tz(yf.Ticker("SPY").history(period=LOOKBACK_PERIOD))
    usdmxn = _strip_tz(yf.Ticker("MXN=X").history(period=LOOKBACK_PERIOD))
    if spy.empty or usdmxn.empty:
        raise RuntimeError("Failed to fetch SPY or USD/MXN. Network issue?")

    spy_ret = np.log(spy["Close"] / spy["Close"].shift(1))
    usdmxn_ret = np.log(usdmxn["Close"] / usdmxn["Close"].shift(1))
    exog = pd.DataFrame({"SPY_Ret": spy_ret, "USDMXN_Ret": usdmxn_ret}).dropna()
    fx_rate = usdmxn["Close"].rename("USDMXN_Rate")

    asset_data = {}
    for ticker in BMV_TICKERS + US_TICKERS:
        print(f"  Fetching {ticker}...", end=" ", flush=True)
        try:
            hist = _strip_tz(yf.Ticker(ticker).history(period=LOOKBACK_PERIOD))
            if hist.empty or len(hist) < MIN_HISTORY_DAYS:
                print(f"skip (only {len(hist)} days)")
                continue

            if ticker in US_TICKERS:
                # Convert to MXN
                df = pd.DataFrame({"Close": hist["Close"], "Volume": hist["Volume"]}).join(fx_rate, how="inner")
                if df.empty:
                    print("skip (no FX overlap)")
                    continue
                df["Close"] = df["Close"] * df["USDMXN_Rate"]
                hist = df[["Close", "Volume"]]

            asset_data[ticker] = hist
            print(f"OK ({len(hist)} days)")
        except Exception as exc:
            print(f"FAIL ({exc})")

    return asset_data, exog, fx_rate


def build_universe_data(asset_data: dict, exog: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """Build the {ticker: {prices, volumes, exogenous}} dict the screener expects,
    sliced to ≤ as_of."""
    universe = {}
    for ticker, hist in asset_data.items():
        sliced = hist.loc[hist.index <= as_of]
        if len(sliced) < MIN_HISTORY_DAYS:
            continue
        df = pd.DataFrame({
            "Price": sliced["Close"],
            "Volume": sliced["Volume"],
        })
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


def compute_target_weights(adjusted_metrics: dict) -> dict:
    """Replicates PortfolioReconciler weighting logic without the trade simulation."""
    eligible = [
        t for t, m in adjusted_metrics.items()
        if m["dcs_adjusted"] >= DCS_ENTRY_THRESHOLD and m["relative_vol"] >= RELVOL_ENTRY_THRESHOLD
    ]
    weights = {t: 0.0 for t in adjusted_metrics}
    if not eligible:
        return weights

    # Inverse-volatility weighting scaled by DCS
    inv_vol = {t: 1.0 / max(adjusted_metrics[t]["garch_vol_adjusted"], 1e-4) for t in eligible}
    inv_vol_sum = sum(inv_vol.values())
    raw = {t: (inv_vol[t] / inv_vol_sum) * adjusted_metrics[t]["dcs_adjusted"] for t in eligible}

    # Apply concentration cap with excess redistribution
    capped = {}
    excess = 0.0
    under_cap_sum = 0.0
    for t, w in raw.items():
        if w > CONCENTRATION_CAP:
            capped[t] = CONCENTRATION_CAP
            excess += (w - CONCENTRATION_CAP)
        else:
            capped[t] = w
            under_cap_sum += w
    if excess > 0 and under_cap_sum > 0:
        for t in list(capped.keys()):
            if capped[t] < CONCENTRATION_CAP:
                share = raw[t] / under_cap_sum
                capped[t] = min(CONCENTRATION_CAP, capped[t] + excess * share)

    # Normalize so total ≤ 1 (raw weights can be < 1 if DCS values are < 1)
    total = sum(capped.values())
    if total > 1.0:
        capped = {t: w / total for t, w in capped.items()}

    for t, w in capped.items():
        weights[t] = w
    return weights


def get_rebalance_dates(asset_data: dict) -> list:
    """Pick rebalance dates at fixed intervals from the first day all tickers have MIN_HISTORY_DAYS."""
    all_dates = sorted(set().union(*(set(df.index) for df in asset_data.values())))
    all_dates = [d for d in all_dates if d.weekday() < 5]
    start_idx = MIN_HISTORY_DAYS
    return all_dates[start_idx::REBALANCE_FREQ_DAYS]


def compute_metrics(nav_series: pd.Series, label: str) -> dict:
    """Compute total return, CAGR, Sharpe, max drawdown."""
    returns = nav_series.pct_change().dropna()
    total_return = nav_series.iloc[-1] / nav_series.iloc[0] - 1
    days = (nav_series.index[-1] - nav_series.index[0]).days
    years = max(days / 365.25, 0.01)
    cagr = (1 + total_return) ** (1 / years) - 1
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0
    cumulative = (1 + returns).cumprod()
    drawdown = (cumulative / cumulative.cummax() - 1).min()
    return {
        "label": label,
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "n_obs": len(returns),
    }


def main():
    print("=" * 80)
    print("WALK-FORWARD BACKTEST")
    print("=" * 80)

    asset_data, exog, _ = download_universe()
    if not asset_data:
        print("No data downloaded. Aborting.")
        return
    print(f"\nUniverse: {len(asset_data)} tickers with sufficient history\n")

    rebalance_dates = get_rebalance_dates(asset_data)
    print(f"Rebalance dates: {len(rebalance_dates)} (from {rebalance_dates[0].date()} to {rebalance_dates[-1].date()})\n")

    # Pre-build a price matrix for daily NAV tracking
    all_dates = sorted(set().union(*(set(df.index) for df in asset_data.values())))
    price_matrix = pd.DataFrame(index=all_dates)
    for ticker, hist in asset_data.items():
        price_matrix[ticker] = hist["Close"]
    price_matrix = price_matrix.ffill().bfill()

    backtest_start = rebalance_dates[0]
    price_matrix = price_matrix.loc[price_matrix.index >= backtest_start]

    # State
    cash = INITIAL_CAPITAL
    shares_held = {t: 0.0 for t in asset_data}
    strategy_nav = {}
    benchmark_nav = {}
    trade_log = []
    total_traded_value = 0.0
    rebalance_idx = 0

    # Equal-weight benchmark — buy at start with full capital, hold
    bench_per_ticker = INITIAL_CAPITAL / len(asset_data)
    bench_shares = {t: bench_per_ticker / price_matrix[t].iloc[0] for t in asset_data}

    screener = FundamentalScreener()
    analyst = MacroRiskAnalyst()

    t_start = time.time()
    for i, current_date in enumerate(price_matrix.index):
        # Rebalance if this is a rebalance date
        if rebalance_idx < len(rebalance_dates) and current_date >= rebalance_dates[rebalance_idx]:
            print(f"  [{current_date.date()}] Rebalancing... (step {rebalance_idx+1}/{len(rebalance_dates)})")
            try:
                universe = build_universe_data(asset_data, exog, current_date)
                if universe:
                    raw_metrics = screener.screen(universe)
                    if raw_metrics:
                        adjusted = analyst.stress_test(raw_metrics, {})
                        target_weights = compute_target_weights(adjusted)

                        # Compute portfolio value at today's prices
                        portfolio_value = cash + sum(
                            shares_held[t] * price_matrix[t].iloc[i] for t in shares_held
                        )

                        # Compute trades
                        for ticker in asset_data:
                            target_value = portfolio_value * target_weights.get(ticker, 0.0)
                            current_value = shares_held[ticker] * price_matrix[ticker].iloc[i]
                            delta_value = target_value - current_value
                            if abs(delta_value) < 50.0:  # ignore sub-50 MXN moves
                                continue
                            delta_shares = delta_value / price_matrix[ticker].iloc[i]
                            cost = abs(delta_value) * TRANSACTION_COST
                            cash -= (delta_value + cost)
                            shares_held[ticker] += delta_shares
                            total_traded_value += abs(delta_value)
                            trade_log.append({
                                "date": current_date,
                                "ticker": ticker,
                                "delta_value": delta_value,
                                "cost": cost,
                            })
            except Exception as exc:
                print(f"    [WARN] rebalance failed: {exc}")
            rebalance_idx += 1

        # Track daily NAV
        equity_value = sum(shares_held[t] * price_matrix[t].iloc[i] for t in shares_held)
        strategy_nav[current_date] = cash + equity_value
        benchmark_nav[current_date] = sum(bench_shares[t] * price_matrix[t].iloc[i] for t in bench_shares)

    elapsed = time.time() - t_start
    print(f"\nBacktest completed in {elapsed:.1f}s")

    strategy_series = pd.Series(strategy_nav, name="strategy")
    benchmark_series = pd.Series(benchmark_nav, name="benchmark")
    nav_df = pd.DataFrame({"strategy": strategy_series, "benchmark": benchmark_series})

    strategy_metrics = compute_metrics(strategy_series, "Strategy")
    benchmark_metrics = compute_metrics(benchmark_series, "Equal-weight buy-and-hold")

    # Save outputs
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nav_df.to_csv(os.path.join(base_dir, "backtest_nav.csv"))
    print(f"  NAV series saved: backtest_nav.csv")

    # Write report
    report_path = os.path.join(base_dir, "backtest_walkforward_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Walk-Forward Backtest Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Setup\n\n")
        f.write(f"- Universe: {len(asset_data)} tickers (BMV + US, US converted to MXN)\n")
        f.write(f"- Backtest period: {strategy_series.index[0].date()} to {strategy_series.index[-1].date()}\n")
        f.write(f"- Rebalance frequency: every {REBALANCE_FREQ_DAYS} trading days ({len(rebalance_dates)} rebalances)\n")
        f.write(f"- Transaction cost: {TRANSACTION_COST*100:.2f}% per trade\n")
        f.write(f"- Concentration cap: {CONCENTRATION_CAP*100:.0f}% per ticker\n")
        f.write(f"- Initial capital: ${INITIAL_CAPITAL:,.2f} MXN\n")
        f.write(f"- NLP sentiment: **disabled** (live news in backtest = look-ahead bias)\n")
        f.write(f"- Statistical arbitrage: **disabled** (cointegration uses full-sample data)\n\n")

        f.write("## Results\n\n")
        f.write("| Metric | Strategy | Equal-weight Benchmark |\n")
        f.write("| :--- | ---: | ---: |\n")
        f.write(f"| Total return | {strategy_metrics['total_return']*100:+.2f}% | {benchmark_metrics['total_return']*100:+.2f}% |\n")
        f.write(f"| CAGR | {strategy_metrics['cagr']*100:+.2f}% | {benchmark_metrics['cagr']*100:+.2f}% |\n")
        f.write(f"| Sharpe (annualized) | {strategy_metrics['sharpe']:.2f} | {benchmark_metrics['sharpe']:.2f} |\n")
        f.write(f"| Max drawdown | {strategy_metrics['max_drawdown']*100:.2f}% | {benchmark_metrics['max_drawdown']*100:.2f}% |\n")
        f.write(f"| Final NAV | ${strategy_series.iloc[-1]:,.2f} | ${benchmark_series.iloc[-1]:,.2f} |\n\n")

        # Activity
        f.write("## Trading Activity\n\n")
        f.write(f"- Total trades: {len(trade_log)}\n")
        f.write(f"- Total dollar volume traded: ${total_traded_value:,.2f} MXN\n")
        f.write(f"- Total transaction costs paid: ${sum(t['cost'] for t in trade_log):,.2f} MXN\n")
        if total_traded_value > 0:
            turnover = total_traded_value / INITIAL_CAPITAL
            f.write(f"- Turnover (volume / initial capital): {turnover:.2f}x\n\n")

        # Verdict
        f.write("## Verdict\n\n")
        excess = strategy_metrics["total_return"] - benchmark_metrics["total_return"]
        excess_cagr = strategy_metrics["cagr"] - benchmark_metrics["cagr"]
        if excess_cagr > 0.02:
            f.write(f"**Strategy outperformed** equal-weight by {excess_cagr*100:+.2f}% CAGR. ")
        elif excess_cagr < -0.02:
            f.write(f"**Strategy underperformed** equal-weight by {abs(excess_cagr)*100:.2f}% CAGR. ")
        else:
            f.write(f"**Roughly tied** with equal-weight ({excess_cagr*100:+.2f}% CAGR difference). ")

        if strategy_metrics["sharpe"] > benchmark_metrics["sharpe"] + 0.2:
            f.write("Risk-adjusted return is meaningfully better.\n\n")
        elif strategy_metrics["sharpe"] < benchmark_metrics["sharpe"] - 0.2:
            f.write("Risk-adjusted return is worse, so the active trading isn't earning its costs.\n\n")
        else:
            f.write("Risk-adjusted return is comparable, meaning the complexity isn't paying off.\n\n")

        f.write("**Reading the result honestly:** in-sample backtests on a 27-ticker universe over 5 years ")
        f.write("with a strategy this complex have very wide confidence intervals. A 2-3% CAGR edge here ")
        f.write("is well within noise. Repeat on a held-out period and a wider universe (full BMV + S&P) ")
        f.write("before concluding anything.\n")

    print(f"  Report saved: {report_path}\n")

    # Stdout summary
    print("=" * 80)
    print("BACKTEST SUMMARY")
    print("=" * 80)
    print(f"  Period:    {strategy_series.index[0].date()} → {strategy_series.index[-1].date()}")
    print(f"  Strategy:  CAGR={strategy_metrics['cagr']*100:+.2f}%  Sharpe={strategy_metrics['sharpe']:.2f}  MaxDD={strategy_metrics['max_drawdown']*100:.2f}%")
    print(f"  Benchmark: CAGR={benchmark_metrics['cagr']*100:+.2f}%  Sharpe={benchmark_metrics['sharpe']:.2f}  MaxDD={benchmark_metrics['max_drawdown']*100:.2f}%")
    print(f"  Excess CAGR: {(strategy_metrics['cagr']-benchmark_metrics['cagr'])*100:+.2f}%")
    print(f"  Trades: {len(trade_log)} | Turnover: {total_traded_value/INITIAL_CAPITAL:.2f}x | Costs paid: ${sum(t['cost'] for t in trade_log):,.2f} MXN")


if __name__ == "__main__":
    main()
