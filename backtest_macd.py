import os
import argparse
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

from skills.macd_trend import calculate_all_indicators

# Define Default Systematic Parameters matching Pine Script
DEFAULT_PARAMS = {
    "longTermMALength": 200,
    "maType": "SMA",
    "fastLength": 12,
    "slowLength": 26,
    "signalLength": 9,
    "profitTriggerPercent": 5.0,
    "trailingStopPercent": 2.0,
    "defaultQtyValue": 10.0,
    "pyramiding": 1,
    "commission": 0.0010,
    "slippage_cents": 3,
}

def download_data(tickers, start_date, end_date):
    """Downloads daily OHLCV data for specified tickers."""
    print(f"Downloading daily data for {len(tickers)} tickers from {start_date} to {end_date}...")
    # Add a warmup buffer to calculate 200 MA on day 1 of backtest
    warmup_start = (datetime.datetime.strptime(start_date, "%Y-%m-%d") - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    
    if len(tickers) == 1:
        data = yf.download(tickers[0], start=warmup_start, end=end_date, progress=False)
        if data.empty:
            return {}
        # Format columns properly (yf return format can vary)
        data.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in data.columns]
        return {tickers[0]: data}
    else:
        # Batch download for universe
        data = yf.download(tickers, start=warmup_start, end=end_date, group_by='ticker', progress=False)
        universe_data = {}
        for ticker in tickers:
            try:
                if ticker in data.columns.levels[0]:
                    ticker_df = data[ticker].dropna(how='all')
                    if len(ticker_df) > 100:
                        ticker_df.columns = [c.lower() for c in ticker_df.columns]
                        universe_data[ticker] = ticker_df
            except Exception:
                continue
        return universe_data

def run_single_asset_simulation(df, ticker, params):
    """Runs systematic daily strategy simulation on a single asset dataframe.
    Ensures precise replication of TradingView bar-by-bar stop and entry mechanics
    for the Pyramided MACD + Trailing Stop Exit Strategy.
    """
    commission_rate = params.get("commission", 0.0010)
    slippage = params.get("slippage_cents", 3) / 100.0  # convert cents to dollars
    initial_capital = 10000.0
    
    # Calculate indicators
    df_ind = calculate_all_indicators(df, params)
    
    # Find start index after warmup (exclude rows where 200 MA is NaN)
    start_loc = df_ind["ma_long"].first_valid_index()
    if start_loc is None:
        raise ValueError("Not enough warmup history to calculate 200 MA.")
        
    df_bt = df_ind.loc[df_ind.index >= start_loc].copy()
    
    # Simulation State variables
    cash = initial_capital
    position = 0.0             # Total shares held
    position_avg_price = 0.0   # Average price of position
    highest_since_entry = 0.0  # Highest high achieved since position opened
    trailing_stop_price = None # Active trailing stop price
    entry_date = None
    active_entries = []        # Tracks info about individual entry fills
    
    # Log tracking
    trades = []
    daily_nav = []
    
    dates = df_bt.index
    opens = df_bt["open"].values
    highs = df_bt["high"].values
    lows = df_bt["low"].values
    closes = df_bt["close"].values
    
    macd_vals = df_bt["macd"].values
    signal_vals = df_bt["signal"].values
    ma_long_vals = df_bt["ma_long"].values
    
    for t in range(len(df_bt)):
        current_date = dates[t]
        o_t = opens[t]
        h_t = highs[t]
        l_t = lows[t]
        c_t = closes[t]
        
        # 1. Update/check open position during the day
        if position > 0:
            # Check trailing stop hit
            if trailing_stop_price is not None and l_t <= trailing_stop_price:
                # Position is stopped out
                fill_price = max(o_t, trailing_stop_price) - slippage
                gross_proceeds = position * fill_price
                cost = position * position_avg_price
                commission_total = (cost + gross_proceeds) * commission_rate
                profit = gross_proceeds - cost - commission_total
                
                trades.append({
                    "ticker": ticker,
                    "entry_date": entry_date.strftime("%Y-%m-%d") if isinstance(entry_date, (datetime.datetime, pd.Timestamp)) else str(entry_date),
                    "exit_date": current_date.strftime("%Y-%m-%d"),
                    "entry_price": position_avg_price,
                    "exit_price": fill_price,
                    "shares": position,
                    "reason": "Trailing Stop Exit",
                    "profit": profit
                })
                
                cash += gross_proceeds * (1.0 - commission_rate)
                position = 0.0
                position_avg_price = 0.0
                highest_since_entry = 0.0
                trailing_stop_price = None
                active_entries = []
                entry_date = None
                
            # If still open, update trailing stop parameters
            if position > 0:
                highest_since_entry = max(highest_since_entry, h_t)
                current_profit_pct = (c_t - position_avg_price) / position_avg_price * 100.0
                
                if current_profit_pct >= params["profitTriggerPercent"]:
                    potential_stop = highest_since_entry * (1.0 - params["trailingStopPercent"] / 100.0)
                    trailing_stop_price = potential_stop if trailing_stop_price is None else max(trailing_stop_price, potential_stop)
                    
        # 2. Check for entry signal on close of bar t (to enter at open of bar t+1)
        if t > 0 and t < len(df_bt) - 1:
            macd_curr, macd_prev = macd_vals[t], macd_vals[t-1]
            sig_curr, sig_prev = signal_vals[t], signal_vals[t-1]
            
            # ta.crossover(macdLine, signalLine)
            macd_buy = (macd_prev <= sig_prev) and (macd_curr > sig_curr)
            is_bull = c_t > ma_long_vals[t]
            
            if macd_buy and is_bull:
                # Check if we can enter based on pyramiding rules
                pyramiding_limit = params.get("pyramiding", 1)
                if len(active_entries) < pyramiding_limit + 1:
                    # Trigger entry at open of bar t+1
                    entry_o = opens[t+1]
                    entry_price = entry_o + slippage
                    
                    # Size based on percent of current equity
                    current_equity = cash + (position * closes[t] if position > 0 else 0.0)
                    qty_pct = params.get("defaultQtyValue", 10.0)
                    target_val = current_equity * (qty_pct / 100.0)
                    shares_to_buy = target_val / entry_price
                    
                    # Cap by available cash
                    cost_per_share = entry_price * (1.0 + commission_rate)
                    max_shares = cash / cost_per_share
                    shares_to_buy = min(shares_to_buy, max_shares)
                    
                    if shares_to_buy > 0:
                        cash -= shares_to_buy * cost_per_share
                        
                        # Add entry detail
                        active_entries.append({
                            "shares": shares_to_buy,
                            "price": entry_price,
                            "date": dates[t+1]
                        })
                        
                        if position == 0.0:
                            # Initial position
                            position = shares_to_buy
                            position_avg_price = entry_price
                            entry_date = dates[t+1]
                            highest_since_entry = max(opens[t+1], highs[t+1])
                            trailing_stop_price = None
                        else:
                            # Pyramided position update
                            new_total_shares = position + shares_to_buy
                            position_avg_price = (position * position_avg_price + shares_to_buy * entry_price) / new_total_shares
                            position = new_total_shares
                            highest_since_entry = max(highest_since_entry, highs[t+1])
        
        # Track daily equity
        current_equity = cash + (position * c_t if position > 0 else 0.0)
        daily_nav.append({
            "Date": current_date.strftime("%Y-%m-%d"),
            "NAV": current_equity,
            "Close": c_t,
            "Position": position,
        })
        
    nav_df = pd.DataFrame(daily_nav).set_index("Date")
    return nav_df, trades

def calculate_metrics(nav_series, label):
    """Calculates standard performance metrics."""
    returns = nav_series.pct_change().dropna()
    total_ret = nav_series.iloc[-1] / nav_series.iloc[0] - 1
    
    # CAGR
    days = (pd.to_datetime(nav_series.index[-1]) - pd.to_datetime(nav_series.index[0])).days
    years = max(days / 365.25, 0.01)
    cagr = (1.0 + total_ret) ** (1.0 / years) - 1.0
    
    # Sharpe
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0
    
    # Max Drawdown
    cum = (1.0 + returns).cumprod()
    drawdown = (cum / cum.cummax() - 1.0).min()
    
    return {
        "label": label,
        "total_return": total_ret,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "final_nav": nav_series.iloc[-1]
    }

def main():
    parser = argparse.ArgumentParser(description=" Systematic MACD Trend Robust v3 Backtest")
    parser.add_argument("--ticker", type=str, default="SPY", help="Ticker symbol to backtest")
    parser.add_argument("--start", type=str, default="2021-06-15", help="Backtest start date")
    parser.add_argument("--end", type=str, default="2026-06-15", help="Backtest end date")
    args = parser.parse_args()
    
    ticker = args.ticker
    start_date = args.start
    end_date = args.end
    
    print(f"Loading data for {ticker}...")
    data_dict = download_data([ticker], start_date, end_date)
    if ticker not in data_dict:
        print(f"Failed to fetch data for {ticker}. Aborting.")
        return
        
    df = data_dict[ticker]
    print(f"Running simulation for {ticker}...")
    nav_df, trades = run_single_asset_simulation(df, ticker, DEFAULT_PARAMS)
    
    # Benchmark equal-weight Buy & Hold
    bench_shares = 10000.0 / df.loc[df.index >= nav_df.index[0], "close"].iloc[0]
    bench_nav = df.loc[df.index >= nav_df.index[0], "close"] * bench_shares
    bench_nav.index = [d.strftime("%Y-%m-%d") for d in bench_nav.index]
    
    # Sync Indices
    common_idx = nav_df.index.intersection(bench_nav.index)
    nav_df = nav_df.loc[common_idx]
    bench_nav = bench_nav.loc[common_idx]
    
    # Metrics
    strat_metrics = calculate_metrics(nav_df["NAV"], "MACD Trend Strategy")
    bench_metrics = calculate_metrics(bench_nav, f"Buy & Hold {ticker}")
    
    # Print results
    print("=" * 80)
    print(f"BACKTEST RESULTS FOR {ticker} ({nav_df.index[0]} to {nav_df.index[-1]})")
    print("=" * 80)
    print(f"  Strategy Return:   {strat_metrics['total_return']*100:.2f}% (CAGR: {strat_metrics['cagr']*100:.2f}%)")
    print(f"  Strategy Sharpe:   {strat_metrics['sharpe']:.2f}")
    print(f"  Strategy Max DD:   {strat_metrics['max_drawdown']*100:.2f}%")
    print(f"  Benchmark Return:  {bench_metrics['total_return']*100:.2f}% (CAGR: {bench_metrics['cagr']*100:.2f}%)")
    print(f"  Benchmark Sharpe:  {bench_metrics['sharpe']:.2f}")
    print(f"  Benchmark Max DD:  {bench_metrics['max_drawdown']*100:.2f}%")
    print(f"  Total Trades:      {len(trades)}")
    
    # Write Report
    report_path = "macd_backtest_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# MACD Trend Strategy Backtest Report ({ticker})\n\n")
        f.write(f"**Period:** {nav_df.index[0]} to {nav_df.index[-1]} | **Initial Capital:** $10,000.00 USD\n\n")
        f.write("## 1. Performance Summary\n\n")
        f.write("| Metric | MACD Trend Strategy | Buy & Hold Benchmark |\n")
        f.write("| :--- | :---: | :---: |\n")
        f.write(f"| **Total Return** | **{strat_metrics['total_return']*100:.2f}%** | **{bench_metrics['total_return']*100:.2f}%** |\n")
        f.write(f"| **CAGR** | **{strat_metrics['cagr']*100:.2f}%** | **{bench_metrics['cagr']*100:.2f}%** |\n")
        f.write(f"| **Sharpe Ratio** | **{strat_metrics['sharpe']:.2f}** | **{bench_metrics['sharpe']:.2f}** |\n")
        f.write(f"| **Max Drawdown** | **{strat_metrics['max_drawdown']*100:.2f}%** | **{bench_metrics['max_drawdown']*100:.2f}%** |\n")
        f.write(f"| **Final Portfolio Value** | **${strat_metrics['final_nav']:.2f}** | **${bench_metrics['final_nav']:.2f}** |\n\n")
        
        f.write("## 2. Trading Activity\n\n")
        f.write(f"* **Total Trades Executed**: {len(trades)}\n")
        f.write("* **Transaction Fee Rate**: 0.10% commission + 3 cents slippage\n\n")
        
        f.write("### Complete Trade Log\n\n")
        f.write("| Entry Date | Exit Date | Entry Price | Exit Price | Shares | Reason | Profit | Profit % |\n")
        f.write("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for t in trades:
            prof_pct = (t["exit_price"] / t["entry_price"] - 1.0) * 100.0
            prof_sign = "+" if t["profit"] >= 0 else ""
            f.write(f"| {t['entry_date']} | {t['exit_date']} | ${t['entry_price']:.2f} | ${t['exit_price']:.2f} | {t['shares']:.1f} | {t['reason']} | {prof_sign}${t['profit']:.2f} | {prof_sign}{prof_pct:.2f}% |\n")
            
    # Save NAV series
    nav_df.to_csv("macd_backtest_nav.csv")
    print(f"Report saved to {report_path}")
    print("NAV series saved to macd_backtest_nav.csv")

def run_macd_simulation_for_api(ticker="SPY", start_date="2021-06-15", end_date="2026-06-15"):
    import os
    import json
    import datetime
    
    # Load parameters
    params = DEFAULT_PARAMS.copy()
    dir_path = os.path.dirname(os.path.abspath(__file__))
    param_file = os.path.join(dir_path, "macd_learned_params.json")
    if os.path.exists(param_file):
        try:
            with open(param_file, "r", encoding="utf-8") as f:
                learned = json.load(f)
                params.update(learned)
                print(f"Loaded learned parameters for API: {learned}")
        except Exception as e:
            print(f"Error loading learned parameters: {e}")
            
    # Download data
    data_dict = download_data([ticker], start_date, end_date)
    if ticker not in data_dict:
        raise ValueError(f"Failed to fetch data for {ticker}")
        
    df = data_dict[ticker]
    
    # Run simulation
    nav_df, trades = run_single_asset_simulation(df, ticker, params)
    
    # Benchmark equal-weight Buy & Hold
    bench_shares = 10000.0 / df.loc[df.index >= nav_df.index[0], "close"].iloc[0]
    bench_nav = df.loc[df.index >= nav_df.index[0], "close"] * bench_shares
    bench_nav.index = [d.strftime("%Y-%m-%d") for d in bench_nav.index]
    
    # Sync Indices
    common_idx = nav_df.index.intersection(bench_nav.index)
    nav_df = nav_df.loc[common_idx]
    bench_nav = bench_nav.loc[common_idx]
    
    # Metrics
    strat_metrics = calculate_metrics(nav_df["NAV"], "MACD Trend Strategy")
    bench_metrics = calculate_metrics(bench_nav, f"Buy & Hold {ticker}")
    
    # Prepare API response matching run_backtest_simulation format
    strategy_return = strat_metrics["total_return"] * 100.0
    benchmark_return = bench_metrics["total_return"] * 100.0
    sharpe = strat_metrics["sharpe"]
    drawdown = strat_metrics["max_drawdown"] * 100.0
    
    # Simulate Bondia cash benchmark over the same period for comparison
    daily_rate = 0.11 / 360.0
    cash_history = []
    cash_val = 10000.0
    dates_list = list(nav_df.index)
    
    for t_idx, d_str in enumerate(dates_list):
        if t_idx > 0:
            date_curr = datetime.datetime.strptime(d_str, "%Y-%m-%d")
            date_prev = datetime.datetime.strptime(dates_list[t_idx - 1], "%Y-%m-%d")
            calendar_days = (date_curr - date_prev).days
        else:
            calendar_days = 1
        cash_val += cash_val * daily_rate * calendar_days
        cash_history.append(round(cash_val, 2))
        
    cash_return = (cash_val / 10000.0 - 1.0) * 100.0
    
    # Total fees paid
    total_fees = 0.0
    commission_rate = params.get("commission", 0.0010)
    slippage = params.get("slippage_cents", 3) / 100.0
    for t in trades:
        shares = t["shares"]
        p_in = t["entry_price"]
        p_out = t["exit_price"]
        total_fees += (p_in + p_out) * shares * commission_rate + 2 * shares * slippage
        
    backtest_data = {
        "dates": dates_list,
        "strategy": [round(float(x), 2) for x in nav_df["NAV"].values],
        "cash": cash_history,
        "benchmark": [round(float(x), 2) for x in bench_nav.values],
        "metrics": {
            "strategy_return": strategy_return,
            "cash_return": cash_return,
            "benchmark_return": benchmark_return,
            "sharpe": sharpe,
            "drawdown": drawdown,
            "fees": total_fees,
            "interest": 0.0
        }
    }
    return backtest_data

if __name__ == "__main__":
    main()
