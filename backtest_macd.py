"""
MACD + Trailing Stop Backtest Runner

Runs the MACDTrailingStopStrategy on the BMV + US universe over 5 years
of daily data.  Produces:
  - backtest_macd_report.md
  - backtest_macd_nav.csv

Parallel structure to backtest_walkforward.py but uses pure technical
analysis signals (MACD crossover + 200 SMA trend filter + trailing stop)
instead of DCF/GARCH/Macro fundamental pipeline.

Run:  python backtest_macd.py
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

from ingest_live_bmv import BMV_TICKERS, US_TICKERS
from skills.macd_trailing_strategy import MACDTrailingStopStrategy


# ---------- Config ----------
LOOKBACK_PERIOD = "5y"
MIN_HISTORY_DAYS = 252           # 1y warmup before backtest begins (200 SMA needs this)
INITIAL_CAPITAL = 20_000.0       # MXN
MONTHLY_CONTRIBUTION = 2_000.0   # MXN
TRANSACTION_COST = 0.0029        # 0.29% per side (matches live broker)
# ----------------------------

# Strategy params (matching Pine Script defaults)
STRATEGY_PARAMS = {
    "long_term_ma_length": 200,
    "ma_type": "SMA",
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "profit_trigger_pct": 15.0,
    "trailing_stop_pct": 5.0,
    "position_pct": 0.10,
    "commission_pct": TRANSACTION_COST,
    "max_positions": 10,
}


def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df.index = pd.to_datetime(df.index.date)
    return df


def download_universe() -> tuple:
    """Pull 5y daily history for all tickers, convert US tickers to MXN.
    Returns (price_matrix: pd.DataFrame, fx_rate: pd.Series)."""
    print("Downloading USD/MXN exchange rate...")
    usdmxn = _strip_tz(yf.Ticker("MXN=X").history(period=LOOKBACK_PERIOD))
    if usdmxn.empty:
        raise RuntimeError("Failed to fetch USD/MXN. Network issue?")
    fx_rate = usdmxn["Close"].rename("USDMXN_Rate")

    all_tickers = BMV_TICKERS + US_TICKERS
    price_data = {}

    for ticker in all_tickers:
        print(f"  Fetching {ticker}...", end=" ", flush=True)
        try:
            hist = _strip_tz(yf.Ticker(ticker).history(period=LOOKBACK_PERIOD))
            if hist.empty or len(hist) < MIN_HISTORY_DAYS:
                print(f"skip (only {len(hist)} days)")
                continue

            if ticker in US_TICKERS:
                # Convert to MXN
                df = pd.DataFrame({"Close": hist["Close"]}).join(fx_rate, how="inner")
                if df.empty:
                    print("skip (no FX overlap)")
                    continue
                price_data[ticker] = df["Close"] * df["USDMXN_Rate"]
            else:
                price_data[ticker] = hist["Close"]

            print(f"OK ({len(hist)} days)")
        except Exception as exc:
            print(f"FAIL ({exc})")

    if not price_data:
        raise RuntimeError("No ticker data downloaded.")

    # Build a clean price matrix (forward-fill gaps, drop tickers with too many NaNs)
    price_matrix = pd.DataFrame(price_data)
    price_matrix = price_matrix.ffill().bfill()

    # Only keep tickers with at least MIN_HISTORY_DAYS of valid data
    valid_cols = [c for c in price_matrix.columns if price_matrix[c].notna().sum() >= MIN_HISTORY_DAYS]
    price_matrix = price_matrix[valid_cols]

    print(f"\nUniverse: {len(price_matrix.columns)} tickers with sufficient history")
    return price_matrix, fx_rate


def main():
    print("=" * 80)
    print("MACD + TRAILING STOP BACKTEST")
    print("=" * 80)

    t_start = time.time()

    price_matrix, _ = download_universe()
    if price_matrix.empty:
        print("No data downloaded. Aborting.")
        return

    # Slice to start after warmup period (200 SMA needs data)
    backtest_start_idx = MIN_HISTORY_DAYS
    if backtest_start_idx >= len(price_matrix):
        print("Not enough data for warmup period. Aborting.")
        return

    print(f"\nBacktest period: {price_matrix.index[backtest_start_idx].date()} to {price_matrix.index[-1].date()}")
    print(f"Strategy: MACD({STRATEGY_PARAMS['macd_fast']}, {STRATEGY_PARAMS['macd_slow']}, {STRATEGY_PARAMS['macd_signal']}) "
          f"+ {STRATEGY_PARAMS['long_term_ma_length']} {STRATEGY_PARAMS['ma_type']} trend filter")
    print(f"Trailing stop: arms at +{STRATEGY_PARAMS['profit_trigger_pct']}%, trails at {STRATEGY_PARAMS['trailing_stop_pct']}% below peak")
    print(f"Position sizing: {STRATEGY_PARAMS['position_pct']*100:.0f}% of equity | Max positions: {STRATEGY_PARAMS['max_positions']}")
    print(f"Commission: {STRATEGY_PARAMS['commission_pct']*100:.2f}% per side")
    print()

    # Run strategy
    strategy = MACDTrailingStopStrategy(**STRATEGY_PARAMS)
    results = strategy.run_portfolio_backtest(
        price_matrix=price_matrix,
        initial_capital=INITIAL_CAPITAL,
        monthly_contribution=MONTHLY_CONTRIBUTION,
    )

    elapsed = time.time() - t_start
    print(f"\nBacktest completed in {elapsed:.1f}s")

    # Extract results
    nav_series = results["nav_series"]
    bench_series = results["benchmark_nav"]
    trade_log = results["trade_log"]
    metrics = results["metrics"]

    # Save NAV CSV
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nav_df = pd.DataFrame({"strategy": nav_series, "benchmark": bench_series})
    nav_csv_path = os.path.join(base_dir, "backtest_macd_nav.csv")
    nav_df.to_csv(nav_csv_path)
    print(f"  NAV series saved: {nav_csv_path}")

    # Write report
    report_path = os.path.join(base_dir, "backtest_macd_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# MACD + Trailing Stop Backtest Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Setup\n\n")
        f.write(f"- Universe: {len(price_matrix.columns)} tickers (BMV + US, US converted to MXN)\n")
        f.write(f"- Backtest period: {nav_series.index[0].date()} to {nav_series.index[-1].date()}\n")
        f.write(f"- Strategy: MACD({STRATEGY_PARAMS['macd_fast']}, {STRATEGY_PARAMS['macd_slow']}, {STRATEGY_PARAMS['macd_signal']}) "
                f"+ {STRATEGY_PARAMS['long_term_ma_length']} {STRATEGY_PARAMS['ma_type']} trend filter\n")
        f.write(f"- Trailing stop: arms at +{STRATEGY_PARAMS['profit_trigger_pct']}%, trails at {STRATEGY_PARAMS['trailing_stop_pct']}% below peak\n")
        f.write(f"- Position sizing: {STRATEGY_PARAMS['position_pct']*100:.0f}% of equity per trade\n")
        f.write(f"- Max concurrent positions: {STRATEGY_PARAMS['max_positions']}\n")
        f.write(f"- Transaction cost: {STRATEGY_PARAMS['commission_pct']*100:.2f}% per side\n")
        f.write(f"- Initial capital: ${INITIAL_CAPITAL:,.2f} MXN\n")
        f.write(f"- Monthly contribution: ${MONTHLY_CONTRIBUTION:,.2f} MXN\n\n")

        f.write("## Results\n\n")
        f.write("| Metric | MACD Strategy | Equal-weight Benchmark |\n")
        f.write("| :--- | ---: | ---: |\n")
        f.write(f"| Total return (TWR) | {metrics['strategy_total_return']*100:+.2f}% | {metrics['benchmark_total_return']*100:+.2f}% |\n")
        f.write(f"| CAGR | {metrics['strategy_cagr']*100:+.2f}% | {metrics['benchmark_cagr']*100:+.2f}% |\n")
        f.write(f"| Sharpe (annualized) | {metrics['strategy_sharpe']:.2f} | -- |\n")
        f.write(f"| Max drawdown | {metrics['strategy_max_dd']*100:.2f}% | {metrics['benchmark_max_dd']*100:.2f}% |\n")
        f.write(f"| Final NAV | ${nav_series.iloc[-1]:,.2f} | ${bench_series.iloc[-1]:,.2f} |\n\n")

        f.write("## Trading Activity\n\n")
        f.write(f"- Total buy signals: {metrics['n_buys']}\n")
        f.write(f"- Total closed trades: {metrics['n_trades']}\n")
        f.write(f"- Win rate: {metrics['win_rate']*100:.1f}%\n")
        f.write(f"- Total realized P&L: ${metrics['total_pnl']:,.2f} MXN\n")
        f.write(f"- Average P&L per trade: ${metrics['avg_pnl']:,.2f} MXN\n")
        f.write(f"- Total transaction fees: ${metrics['total_fees']:,.2f} MXN\n\n")

        # Last 20 trades
        if trade_log:
            f.write("## Recent Trade Log (last 20)\n\n")
            f.write("| Date | Ticker | Action | Shares | Price | Fee | P&L | Reason |\n")
            f.write("| :--- | :--- | :---: | ---: | ---: | ---: | ---: | :--- |\n")
            for t in trade_log[-20:]:
                pnl_str = f"${t['pnl']:,.2f}" if t['action'] == 'SELL' else "--"
                f.write(f"| {t['date']} | {t['ticker']} | {t['action']} | {t['shares']} | ${t['price']:.2f} | ${t['fee']:.2f} | {pnl_str} | {t['reason']} |\n")

        # Verdict
        f.write("\n## Verdict\n\n")
        excess_cagr = metrics["strategy_cagr"] - metrics["benchmark_cagr"]
        if excess_cagr > 0.02:
            f.write(f"**MACD strategy outperformed** equal-weight by {excess_cagr*100:+.2f}% CAGR. ")
        elif excess_cagr < -0.02:
            f.write(f"**MACD strategy underperformed** equal-weight by {abs(excess_cagr)*100:.2f}% CAGR. ")
        else:
            f.write(f"**Roughly tied** with equal-weight ({excess_cagr*100:+.2f}% CAGR difference). ")

        f.write(f"Win rate of {metrics['win_rate']*100:.1f}% across {metrics['n_trades']} completed trades.\n")

    print(f"  Report saved: {report_path}\n")

    # Console summary
    print("=" * 80)
    print("MACD BACKTEST SUMMARY")
    print("=" * 80)
    print(f"  Period:    {nav_series.index[0].date()} -> {nav_series.index[-1].date()}")
    print(f"  Strategy:  CAGR={metrics['strategy_cagr']*100:+.2f}%  Sharpe={metrics['strategy_sharpe']:.2f}  MaxDD={metrics['strategy_max_dd']*100:.2f}%")
    print(f"  Benchmark: CAGR={metrics['benchmark_cagr']*100:+.2f}%  MaxDD={metrics['benchmark_max_dd']*100:.2f}%")
    print(f"  Excess CAGR: {(metrics['strategy_cagr']-metrics['benchmark_cagr'])*100:+.2f}%")
    print(f"  Trades: {metrics['n_trades']} closed | Win rate: {metrics['win_rate']*100:.1f}% | Fees: ${metrics['total_fees']:,.2f} MXN")

    return results


def run_macd_backtest_for_api():
    """Entry point for the dashboard API. Returns JSON-serializable results."""
    price_matrix, _ = download_universe()
    strategy = MACDTrailingStopStrategy(**STRATEGY_PARAMS)
    results = strategy.run_portfolio_backtest(
        price_matrix=price_matrix,
        initial_capital=INITIAL_CAPITAL,
        monthly_contribution=MONTHLY_CONTRIBUTION,
    )

    nav_series = results["nav_series"]
    bench_series = results["benchmark_nav"]
    metrics = results["metrics"]
    trade_log = results["trade_log"]

    return {
        "dates": [str(d.date()) for d in nav_series.index],
        "strategy": [float(x) for x in nav_series.values],
        "benchmark": [float(x) for x in bench_series.values],
        "trade_log": trade_log[-30:],  # Last 30 trades for display
        "metrics": {
            "strategy_return": float(metrics["strategy_total_return"] * 100),
            "strategy_cagr": float(metrics["strategy_cagr"] * 100),
            "benchmark_return": float(metrics["benchmark_total_return"] * 100),
            "benchmark_cagr": float(metrics["benchmark_cagr"] * 100),
            "sharpe": float(metrics["strategy_sharpe"]),
            "drawdown": float(metrics["strategy_max_dd"] * 100),
            "n_trades": int(metrics["n_trades"]),
            "win_rate": float(metrics["win_rate"] * 100),
            "total_fees": float(metrics["total_fees"]),
            "total_pnl": float(metrics["total_pnl"]),
        },
    }


if __name__ == "__main__":
    main()
