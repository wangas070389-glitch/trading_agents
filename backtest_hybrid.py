"""
MACD + DCF Momentum-Value Hybrid Backtest Runner

Combines:
  - Fundamental undervalued screening (adjusted DCS >= 0.05) updated monthly.
  - Daily MACD crossover trend-following triggers.
  - Pyramiding (up to 3 tranches of 10% equity per asset).
  - Wider trailing stop exit (+20% trigger, 7.5% trail).
  - Overvaluation exit (DCS < -0.10).
  - Active DCA deployment of monthly $2,000 MXN inflows directly into winning positions.
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

# Stub out NLPSentimentEngine before importing agents to prevent live news fetch
import skills.nlp_sentiment as _nlp_module


class _StubNLPEngine:
    def get_black_litterman_adjustments(self, tickers):
        return {t: 0.0 for t in tickers}


_nlp_module.NLPSentimentEngine = _StubNLPEngine

from agents.agents import FundamentalScreener, MacroRiskAnalyst
from ingest_live_bmv import BMV_TICKERS, US_TICKERS
from skills.hybrid_momentum_value import HybridPositionState, _ema, _sma

# ---------- Config ----------
LOOKBACK_PERIOD = "5y"
REBALANCE_FREQ_DAYS = 21         # monthly
MIN_HISTORY_DAYS = 252           # 1y warmup
TRANSACTION_COST = 0.0029        # 0.29% per side (matches live code)
INITIAL_CAPITAL = 20_000.0       # MXN
MONTHLY_CONTRIBUTION = 2_000.0   # MXN

# Strategy params
STRATEGY_PARAMS = {
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "profit_trigger_pct": 20.0,      # arm trailing stop at +20%
    "trailing_stop_pct": 7.5,        # 7.5% trail below peak
    "position_pct": 0.10,            # 10% of equity per tranche
    "max_positions": 10,             # Max open positions
    "overvaluation_exit_dcs": -0.10, # Force exit if DCS drops below -0.10
    "undervaluation_enter_dcs": 0.05, # Require DCS >= 0.05 to buy
}
# ----------------------------


def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df.index = pd.to_datetime(df.index.date)
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
    """Build the {ticker: {prices, volumes, exogenous}} dict the screener expects, sliced to <= as_of."""
    universe = {}
    for ticker, hist in asset_data.items():
        sliced = hist.loc[hist.index <= as_of]
        if len(sliced) < 200:
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


def get_rebalance_dates(asset_data: dict) -> list[pd.Timestamp]:
    all_dates = sorted(set().union(*(set(df.index) for df in asset_data.values())))
    all_dates = [d for d in all_dates if d.weekday() < 5]
    start_idx = MIN_HISTORY_DAYS
    return all_dates[start_idx::REBALANCE_FREQ_DAYS]


def compute_metrics(nav_series: pd.Series, label: str) -> dict:
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
    print("HYBRID MACD-DCF MOMENTUM-VALUE BACKTEST")
    print("=" * 80)

    asset_data, exog, _ = download_universe()
    if not asset_data:
        print("No data downloaded. Aborting.")
        return
    tickers = list(asset_data.keys())

    rebalance_dates = get_rebalance_dates(asset_data)
    all_dates = sorted(set().union(*(set(df.index) for df in asset_data.values())))
    price_matrix = pd.DataFrame(index=all_dates)
    for ticker, hist in asset_data.items():
        price_matrix[ticker] = hist["Close"]
    price_matrix = price_matrix.ffill().bfill()

    # Slice to backtest period
    backtest_start = rebalance_dates[0]
    price_matrix = price_matrix.loc[price_matrix.index >= backtest_start]
    dates = price_matrix.index
    n_days = len(dates)

    # Pre-compute indicators for daily MACD and trend filters
    indicators = {}
    for ticker in tickers:
        prices = price_matrix[ticker].values.astype(np.float64)
        ema_fast = _ema(prices, STRATEGY_PARAMS["macd_fast"])
        ema_slow = _ema(prices, STRATEGY_PARAMS["macd_slow"])
        macd_line = ema_fast - ema_slow
        signal_line = _ema(macd_line, STRATEGY_PARAMS["macd_signal"])
        sma_200 = _sma(prices, 200)
        sma_20 = _sma(prices, 20)
        
        indicators[ticker] = {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "sma_200": sma_200,
            "sma_20": sma_20,
        }

    # State
    cash = INITIAL_CAPITAL
    positions = {}  # ticker -> HybridPositionState
    trade_log = []
    nav_history = []
    
    # Equal-weight stock benchmark
    bench_per_ticker = INITIAL_CAPITAL / len(tickers)
    bench_shares = {t: bench_per_ticker / price_matrix[t].iloc[0] for t in tickers}
    bench_nav_history = []

    # TWR Tracking
    last_nav = INITIAL_CAPITAL
    last_bench_nav = INITIAL_CAPITAL
    twr = 1.0
    bench_twr = 1.0
    twr_history = []
    bench_twr_history = []

    screener = FundamentalScreener()
    analyst = MacroRiskAnalyst()
    
    # Store latest monthly DCS scores (ticker -> float)
    latest_dcs = {}
    rebalance_idx = 0
    prev_month = dates[0].month

    print(f"\nBacktest period: {dates[0].date()} to {dates[-1].date()}")
    print("Starting simulation loop...")

    for i in range(n_days):
        current_date = dates[i]
        current_month = current_date.month

        # --- 0. Accrue daily interest on cash balance (11% APR) ---
        if i > 0:
            date_prev = dates[i - 1]
            calendar_days = (current_date - date_prev).days
            daily_rate = 0.11 / 360.0
            interest = cash * daily_rate * calendar_days
            cash += interest

        # --- 1. Compute today's NAV before any rebalance or cash additions ---
        equity_val = sum(pos.total_shares * price_matrix[t].iloc[i] for t, pos in positions.items())
        nav_before = cash + equity_val
        bench_val = sum(bench_shares[t] * price_matrix[t].iloc[i] for t in tickers)

        # --- 2. Update TWR series ---
        if i > 0:
            r = (nav_before / last_nav) - 1.0 if last_nav > 0 else 0.0
            r_b = (bench_val / last_bench_nav) - 1.0 if last_bench_nav > 0 else 0.0
            twr *= (1.0 + r)
            bench_twr *= (1.0 + r_b)

        # --- 3. Monthly savings cash injection & Active DCA ---
        is_contribution_day = (i == 0 or current_month != prev_month)
        if is_contribution_day:
            cash += MONTHLY_CONTRIBUTION
            nav_before += MONTHLY_CONTRIBUTION
            
            # Passive Benchmark: allocate savings equally to all tickers
            bench_contrib_per = MONTHLY_CONTRIBUTION / len(tickers)
            for t in tickers:
                bench_shares[t] += bench_contrib_per / price_matrix[t].iloc[i]
            bench_val = sum(bench_shares[t] * price_matrix[t].iloc[i] for t in tickers)
            
            # Active DCA: Deploy $2,000 MXN immediately into top performing undervalued holdings
            if i > 0 and positions:
                eligible_dca = []
                for ticker, pos in positions.items():
                    # Criteria: Close > SMA 20 (uptrend) AND latest_dcs >= 0.05
                    curr_price = price_matrix[ticker].iloc[i]
                    sma_20_val = indicators[ticker]["sma_20"][i]
                    dcs_val = latest_dcs.get(ticker, 0.0)
                    
                    if curr_price > sma_20_val and dcs_val >= STRATEGY_PARAMS["undervaluation_enter_dcs"]:
                        eligible_dca.append((ticker, dcs_val, pos))
                
                if eligible_dca:
                    # Sort by DCS descending, take top 3
                    eligible_dca.sort(key=lambda x: x[1], reverse=True)
                    top_dca = eligible_dca[:3]
                    
                    dca_alloc = MONTHLY_CONTRIBUTION / len(top_dca)
                    print(f"  [{current_date.date()}] Active DCA: Deploying ${MONTHLY_CONTRIBUTION:.2f} across {len(top_dca)} positions:")
                    
                    for ticker, dcs_val, pos in top_dca:
                        curr_price = price_matrix[ticker].iloc[i]
                        shares_to_buy = int(dca_alloc // curr_price)
                        if shares_to_buy > 0:
                            cost = shares_to_buy * curr_price
                            fee = cost * TRANSACTION_COST
                            total_cost = cost + fee
                            if total_cost <= cash:
                                cash -= total_cost
                                pos.add_tranche(curr_price, shares_to_buy, i)
                                trade_log.append({
                                    "date": str(current_date.date()),
                                    "ticker": ticker,
                                    "action": "DCA_BUY",
                                    "shares": shares_to_buy,
                                    "price": curr_price,
                                    "fee": fee,
                                    "pnl": 0.0,
                                    "reason": f"Active DCA inflow (DCS={dcs_val:.3f}, Price>SMA20)",
                                })
                                print(f"    |-- DCA BUY {ticker}: {shares_to_buy} shares at ${curr_price:.2f} MXN")

            prev_month = current_month

        # --- 4. Monthly/Periodic Fundamental Screener Runs ---
        if rebalance_idx < len(rebalance_dates) and current_date >= rebalance_dates[rebalance_idx]:
            try:
                universe = build_universe_data(asset_data, exog, current_date)
                if universe:
                    raw_metrics = screener.screen(universe, execution_date=current_date)
                    if raw_metrics:
                        adjusted = analyst.stress_test(raw_metrics, {})
                        # Update latest_dcs store
                        for t in tickers:
                            if t in adjusted:
                                latest_dcs[t] = adjusted[t]["dcs_adjusted"]
                            else:
                                latest_dcs[t] = 0.0
            except Exception as e:
                print(f"  [ERROR] Fundamental screening failed on {current_date.date()}: {e}")
            rebalance_idx += 1

        # --- 5. Process Exits (Trailing stops and Overvaluation checks) ---
        tickers_to_close = []
        for ticker, pos in positions.items():
            current_price = price_matrix[ticker].iloc[i]
            if not np.isfinite(current_price) or current_price <= 0:
                continue

            # Check 1: Trailing stop trigger
            triggered = pos.update(current_price, STRATEGY_PARAMS["profit_trigger_pct"], STRATEGY_PARAMS["trailing_stop_pct"])
            if triggered:
                tickers_to_close.append((ticker, "stop", pos.stop_level, pos.highest_since_entry))
                continue

            # Check 2: Overvaluation exit (DCS < -0.10)
            curr_dcs = latest_dcs.get(ticker, 0.0)
            if curr_dcs < STRATEGY_PARAMS["overvaluation_exit_dcs"]:
                tickers_to_close.append((ticker, "overvalued", curr_dcs, 0.0))

        for ticker, reason, val1, val2 in tickers_to_close:
            pos = positions[ticker]
            sell_price = price_matrix[ticker].iloc[i]
            revenue = pos.total_shares * sell_price
            fee = revenue * TRANSACTION_COST
            cash += (revenue - fee)
            
            pnl = sum((sell_price - t.entry_price) * t.shares for t in pos.tranches) - fee
            
            reason_str = ""
            if reason == "stop":
                reason_str = f"Trailing stop at {val1:.2f} (peak {val2:.2f})"
            else:
                reason_str = f"Forced overvaluation exit (DCS={val1:.3f} < {STRATEGY_PARAMS['overvaluation_exit_dcs']})"
                
            trade_log.append({
                "date": str(current_date.date()),
                "ticker": ticker,
                "action": "SELL_ALL",
                "shares": pos.total_shares,
                "price": sell_price,
                "fee": fee,
                "pnl": pnl,
                "reason": reason_str,
            })
            del positions[ticker]

        # --- 6. Process Entries (MACD crossover + Bull trend + DCF Undervalued) ---
        # Allow entries only if we have sufficient history for indicators
        if i >= 200:
            for ticker in tickers:
                curr_price = price_matrix[ticker].iloc[i]
                if not np.isfinite(curr_price) or curr_price <= 0:
                    continue

                # Crossover check
                ind = indicators[ticker]
                macd_today = ind["macd_line"][i]
                signal_today = ind["signal_line"][i]
                macd_yesterday = ind["macd_line"][i - 1]
                signal_yesterday = ind["signal_line"][i - 1]
                crossover = (macd_yesterday <= signal_yesterday) and (macd_today > signal_today)

                # SMA 200 bull market filter
                sma_200_val = ind["sma_200"][i]
                is_bull = curr_price > sma_200_val

                # DCS undervaluation filter
                curr_dcs = latest_dcs.get(ticker, 0.0)
                is_undervalued = curr_dcs >= STRATEGY_PARAMS["undervaluation_enter_dcs"]

                if crossover and is_bull and is_undervalued:
                    pos = positions.get(ticker)
                    
                    # If we don't hold the stock, open first tranche
                    if pos is None:
                        if len(positions) < STRATEGY_PARAMS["max_positions"]:
                            # Size = 10% of current equity
                            current_equity = cash + sum(p.total_shares * price_matrix[t].iloc[i] for t, p in positions.items())
                            alloc = current_equity * STRATEGY_PARAMS["position_pct"]
                            shares_to_buy = int(alloc // curr_price)
                            
                            if shares_to_buy > 0:
                                cost = shares_to_buy * curr_price
                                fee = cost * TRANSACTION_COST
                                total_cost = cost + fee
                                if total_cost <= cash:
                                    cash -= total_cost
                                    positions[ticker] = HybridPositionState(ticker)
                                    positions[ticker].add_tranche(curr_price, shares_to_buy, i)
                                    trade_log.append({
                                        "date": str(current_date.date()),
                                        "ticker": ticker,
                                        "action": "BUY_T1",
                                        "shares": shares_to_buy,
                                        "price": curr_price,
                                        "fee": fee,
                                        "pnl": 0.0,
                                        "reason": f"MACD crossover + Bull trend + DCF Undervalued (DCS={curr_dcs:.3f})",
                                    })
                    # If we already hold it, check if we can pyramid (up to 3 tranches)
                    elif len(pos.tranches) < 3:
                        # Add a new tranche (10% of current equity)
                        current_equity = cash + sum(p.total_shares * price_matrix[t].iloc[i] for t, p in positions.items())
                        alloc = current_equity * STRATEGY_PARAMS["position_pct"]
                        shares_to_buy = int(alloc // curr_price)
                        
                        if shares_to_buy > 0:
                            cost = shares_to_buy * curr_price
                            fee = cost * TRANSACTION_COST
                            total_cost = cost + fee
                            if total_cost <= cash:
                                cash -= total_cost
                                pos.add_tranche(curr_price, shares_to_buy, i)
                                trade_log.append({
                                    "date": str(current_date.date()),
                                    "ticker": ticker,
                                    "action": f"BUY_T{len(pos.tranches)}",
                                    "shares": shares_to_buy,
                                    "price": curr_price,
                                    "fee": fee,
                                    "pnl": 0.0,
                                    "reason": f"Pyramiding entry (crossover, DCS={curr_dcs:.3f})",
                                })

        # --- 7. Record daily NAV ---
        equity_val = sum(pos.total_shares * price_matrix[t].iloc[i] for t, pos in positions.items())
        final_nav = cash + equity_val
        last_nav = final_nav
        last_bench_nav = sum(bench_shares[t] * price_matrix[t].iloc[i] for t in tickers)

        nav_history.append(final_nav)
        bench_nav_history.append(last_bench_nav)
        twr_history.append(twr)
        bench_twr_history.append(bench_twr)

    # --- Build final results ---
    strategy_series = pd.Series(nav_history, index=dates, name="strategy")
    benchmark_series = pd.Series(bench_nav_history, index=dates, name="benchmark")
    strategy_twr_pd = pd.Series(twr_history, index=dates, name="strategy_twr")
    benchmark_twr_pd = pd.Series(bench_twr_history, index=dates, name="benchmark_twr")

    strategy_metrics = compute_metrics(strategy_twr_pd, "Hybrid Strategy")
    benchmark_metrics = compute_metrics(benchmark_twr_pd, "Equal-weight buy-and-hold")

    # Save CSV
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nav_df = pd.DataFrame({"strategy": strategy_series, "benchmark": benchmark_series})
    nav_df.to_csv(os.path.join(base_dir, "backtest_hybrid_nav.csv"))
    print(f"\n  NAV series saved: backtest_hybrid_nav.csv")

    # Write report
    report_path = os.path.join(base_dir, "backtest_hybrid_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Hybrid MACD-DCF Momentum-Value Backtest Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Setup\n\n")
        f.write(f"- Universe: {len(tickers)} tickers (BMV + US, US converted to MXN)\n")
        f.write(f"- Backtest period: {strategy_series.index[0].date()} to {strategy_series.index[-1].date()}\n")
        f.write(f"- Strategy: MACD + DCF Undervalued (DCS >= {STRATEGY_PARAMS['undervaluation_enter_dcs']})\n")
        f.write(f"- Trailing stop: arms at +{STRATEGY_PARAMS['profit_trigger_pct']}%, trails at {STRATEGY_PARAMS['trailing_stop_pct']}% below peak\n")
        f.write(f"- Pyramiding: enabled (max 3 tranches, {STRATEGY_PARAMS['position_pct']*100:.0f}% equity each)\n")
        f.write(f"- Active DCA Deployment: enabled (deposits routed immediately into top performing undervalued holdings)\n")
        f.write(f"- Transaction cost: {TRANSACTION_COST*100:.2f}% per side\n")
        f.write(f"- Initial capital: ${INITIAL_CAPITAL:,.2f} MXN\n")
        f.write(f"- Monthly contribution: ${MONTHLY_CONTRIBUTION:,.2f} MXN\n\n")

        f.write("## Results\n\n")
        f.write("| Metric | Hybrid Strategy | Equal-weight Benchmark |\n")
        f.write("| :--- | ---: | ---: |\n")
        f.write(f"| Total return | {strategy_metrics['total_return']*100:+.2f}% | {benchmark_metrics['total_return']*100:+.2f}% |\n")
        f.write(f"| CAGR | {strategy_metrics['cagr']*100:+.2f}% | {benchmark_metrics['cagr']*100:+.2f}% |\n")
        f.write(f"| Sharpe (annualized) | {strategy_metrics['sharpe']:.2f} | {benchmark_metrics['sharpe']:.2f} |\n")
        f.write(f"| Max drawdown | {strategy_metrics['max_drawdown']*100:.2f}% | {benchmark_metrics['max_drawdown']*100:.2f}% |\n")
        f.write(f"| Final NAV | ${strategy_series.iloc[-1]:,.2f} | ${benchmark_series.iloc[-1]:,.2f} |\n\n")

        # Trading Activity
        sells = [t for t in trade_log if t["action"] == "SELL_ALL"]
        wins = [t for t in sells if t["pnl"] > 0]
        win_rate = len(wins) / len(sells) if sells else 0.0
        total_fees = sum(t["fee"] for t in trade_log)
        
        f.write("## Trading Activity\n\n")
        f.write(f"- Total closed trades (SELL_ALL): {len(sells)}\n")
        f.write(f"- Win rate: {win_rate*100:.1f}%\n")
        f.write(f"- Total transaction costs paid: ${total_fees:,.2f} MXN\n")
        f.write(f"- Total trades executed (BUYs + SELLs): {len(trade_log)}\n\n")

        # Recent trade log
        if trade_log:
            f.write("## Recent Trade Log (last 30)\n\n")
            f.write("| Date | Ticker | Action | Shares | Price | Fee | P&L | Reason |\n")
            f.write("| :--- | :--- | :---: | ---: | ---: | ---: | ---: | :--- |\n")
            for t in trade_log[-30:]:
                pnl_str = f"${t['pnl']:,.2f}" if t['action'] == 'SELL_ALL' else "--"
                f.write(f"| {t['date']} | {t['ticker']} | {t['action']} | {t['shares']} | ${t['price']:.2f} | ${t['fee']:.2f} | {pnl_str} | {t['reason']} |\n")

    print(f"  Report saved: {report_path}")
    print("=" * 80)
    print("HYBRID BACKTEST SUMMARY")
    print("=" * 80)
    print(f"  Period:    {strategy_series.index[0].date()} -> {strategy_series.index[-1].date()}")
    print(f"  Strategy:  CAGR={strategy_metrics['cagr']*100:+.2f}%  Sharpe={strategy_metrics['sharpe']:.2f}  MaxDD={strategy_metrics['max_drawdown']*100:.2f}%")
    print(f"  Benchmark: CAGR={benchmark_metrics['cagr']*100:+.2f}%  Sharpe={benchmark_metrics['sharpe']:.2f}  MaxDD={benchmark_metrics['max_drawdown']*100:.2f}%")
    print(f"  Excess CAGR: {(strategy_metrics['cagr']-benchmark_metrics['cagr'])*100:+.2f}%")
    print(f"  Total Trades: {len(trade_log)} | Win Rate: {win_rate*100:.1f}% | Fees: ${total_fees:,.2f} MXN")


if __name__ == "__main__":
    main()
