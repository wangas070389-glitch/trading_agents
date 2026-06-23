import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

from skills.us_stock_momentum import calculate_us_momentum_indicators, check_trailing_stop

# US Stocks Universe
US_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX", "AMD", "JPM"]

# Strategy params
START_DATE = "2021-06-20"
END_DATE = "2026-06-20"
INITIAL_CAPITAL = 100000.0  # USD
SLIPPAGE_PCT = 0.0002       # 0.02% slippage to account for bid-ask spread
TRAILING_ARM_PCT = 0.10     # Arm trailing stop at +10%
TRAILING_STOP_PCT = 0.05    # Trail 5% below peak

def download_us_data(tickers, start_date, end_date):
    print(f"Downloading daily data for {len(tickers)} US tickers from {start_date} to {end_date}...")
    # Add warmup buffer for 200 SMA calculation
    warmup_start = (datetime.datetime.strptime(start_date, "%Y-%m-%d") - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    
    data = yf.download(tickers, start=warmup_start, end=end_date, group_by='ticker', progress=False)
    universe_data = {}
    for ticker in tickers:
        try:
            if ticker in data.columns.levels[0]:
                ticker_df = data[ticker].dropna(how='all')
                if len(ticker_df) > 100:
                    universe_data[ticker] = ticker_df
        except Exception:
            # Fallback if yfinance formats output as a single level DataFrame (when only one ticker succeeds)
            if ticker in data.columns:
                ticker_df = data.dropna(how='all')
                universe_data[ticker] = ticker_df
    return universe_data

def run_simulation(data_dict, tickers):
    # Calculate indicators for each stock
    processed_data = {}
    for t in tickers:
        if t in data_dict:
            try:
                processed_data[t] = calculate_us_momentum_indicators(data_dict[t])
            except Exception as e:
                print(f"Error calculating indicators for {t}: {e}")
                
    if not processed_data:
        raise ValueError("No valid US stock data found.")
        
    # Get common timeline after warmup
    common_dates = None
    for t, df in processed_data.items():
        valid_idx = df["sma200"].dropna().index
        if common_dates is None:
            common_dates = set(valid_idx)
        else:
            common_dates = common_dates.intersection(set(valid_idx))
            
    sim_dates = sorted(list(common_dates))
    if not sim_dates:
        raise ValueError("Not enough history to align 200 SMA data.")
        
    print(f"Running simulation over {len(sim_dates)} trading days...")
    
    # Align dataframes
    for t in list(processed_data.keys()):
        processed_data[t] = processed_data[t].reindex(sim_dates).ffill()
        
    # Simulation State
    cash = INITIAL_CAPITAL
    shares_held = {t: 0.0 for t in processed_data}
    buy_prices = {t: 0.0 for t in processed_data}
    peak_prices = {t: 0.0 for t in processed_data}
    
    trades = []
    daily_nav = []
    
    for day_idx, current_date in enumerate(sim_dates):
        # 1. Update prices & check Trailing Stops for currently held positions
        for t in list(processed_data.keys()):
            shares = shares_held[t]
            if shares > 0.0:
                row = processed_data[t].iloc[day_idx]
                c_price = float(row["Close"])
                low_price = float(row["Low"])
                high_price = float(row["High"])
                
                # Check trailing stop using Low price for stop-out trigger
                should_exit, updated_peak = check_trailing_stop(
                    buy_price=buy_prices[t],
                    current_price=low_price,
                    peak_price=peak_prices[t],
                    arm_pct=TRAILING_ARM_PCT,
                    trail_pct=TRAILING_STOP_PCT
                )
                
                # Keep tracking high price for peak
                peak_prices[t] = max(peak_prices[t], high_price)
                
                if should_exit:
                    # Execute sell at stop price or open
                    exit_price = max(row["Open"], peak_prices[t] * (1.0 - TRAILING_STOP_PCT)) * (1.0 - SLIPPAGE_PCT)
                    gross = shares * exit_price
                    profit = gross - (shares * buy_prices[t])
                    trades.append({
                        "ticker": t,
                        "entry_date": buy_prices.get(f"{t}_date", str(current_date)),
                        "exit_date": current_date.strftime("%Y-%m-%d"),
                        "entry_price": buy_prices[t],
                        "exit_price": exit_price,
                        "shares": shares,
                        "profit": profit,
                        "reason": "Trailing Stop"
                    })
                    cash += gross
                    shares_held[t] = 0.0
                    buy_prices[t] = 0.0
                    peak_prices[t] = 0.0
                    
        # 2. Check Signals on Close to trade at the Close/Next Open
        # Find which assets are bullish today
        bullish_tickers = []
        for t, df in processed_data.items():
            row = df.iloc[day_idx]
            close = float(row["Close"])
            sma = float(row["sma200"])
            macd = float(row["macd"])
            sig = float(row["signal"])
            
            # Bullish: Close > SMA 200 AND MACD > Signal
            if close > sma and macd > sig:
                bullish_tickers.append(t)
                
        # Calculate Current NAV
        curr_value = sum(shares_held[tk] * float(processed_data[tk].iloc[day_idx]["Close"]) for tk in processed_data)
        portfolio_equity = cash + curr_value
        
        # Determine Target Weights
        target_weights = {t: 0.0 for t in processed_data}
        if bullish_tickers:
            weight_per_stock = 1.0 / len(bullish_tickers)
            for t in bullish_tickers:
                target_weights[t] = weight_per_stock
                
        # Execute Rebalancing to reach target weights
        # Sell down / exit non-bullish or over-weighted assets first
        for t in processed_data:
            shares = shares_held[t]
            c_price = float(processed_data[t].iloc[day_idx]["Close"])
            target_w = target_weights[t]
            current_w = (shares * c_price) / portfolio_equity if portfolio_equity > 0 else 0.0
            
            # Exit if no longer bullish
            if target_w == 0.0 and shares > 0.0:
                exit_price = c_price * (1.0 - SLIPPAGE_PCT)
                gross = shares * exit_price
                profit = gross - (shares * buy_prices[t])
                trades.append({
                    "ticker": t,
                    "entry_date": buy_prices.get(f"{t}_date", str(current_date)),
                    "exit_date": current_date.strftime("%Y-%m-%d"),
                    "entry_price": buy_prices[t],
                    "exit_price": exit_price,
                    "shares": shares,
                    "profit": profit,
                    "reason": "Bearish Signal"
                })
                cash += gross
                shares_held[t] = 0.0
                buy_prices[t] = 0.0
                peak_prices[t] = 0.0
                
        # Calculate available cash for buys after exits
        curr_value = sum(shares_held[tk] * float(processed_data[tk].iloc[day_idx]["Close"]) for tk in processed_data)
        portfolio_equity = cash + curr_value
        
        # Deploy remaining cash to buy bullish targets
        for t in bullish_tickers:
            shares = shares_held[t]
            c_price = float(processed_data[t].iloc[day_idx]["Close"])
            target_val = portfolio_equity * target_weights[t]
            current_val = shares * c_price
            
            if target_val > current_val:
                cash_to_spend = target_val - current_val
                # Check cash limit
                if cash_to_spend > cash:
                    cash_to_spend = cash
                    
                exec_price = c_price * (1.0 + SLIPPAGE_PCT)
                shares_to_buy = cash_to_spend / exec_price
                if shares_to_buy > 0.001:
                    cash -= (shares_to_buy * exec_price)
                    old_shares = shares_held[t]
                    old_price = buy_prices[t]
                    
                    shares_held[t] += shares_to_buy
                    buy_prices[t] = ((old_shares * old_price) + (shares_to_buy * exec_price)) / shares_held[t]
                    buy_prices[f"{t}_date"] = current_date.strftime("%Y-%m-%d")
                    peak_prices[t] = max(peak_prices[t], float(processed_data[t].iloc[day_idx]["High"]))
                    
        # Record NAV
        final_day_value = sum(shares_held[tk] * float(processed_data[tk].iloc[day_idx]["Close"]) for tk in processed_data)
        portfolio_equity = cash + final_day_value
        daily_nav.append({
            "Date": current_date.strftime("%Y-%m-%d"),
            "NAV": portfolio_equity
        })
        
    nav_df = pd.DataFrame(daily_nav).set_index("Date")
    return nav_df, trades

def calculate_metrics(nav_series):
    returns = nav_series.pct_change().dropna()
    total_ret = nav_series.iloc[-1] / nav_series.iloc[0] - 1.0
    
    days = (pd.to_datetime(nav_series.index[-1]) - pd.to_datetime(nav_series.index[0])).days
    years = max(days / 365.25, 0.01)
    cagr = (1.0 + total_ret) ** (1.0 / years) - 1.0
    
    # Sharpe ratio (assume risk-free rate of 4.5% USD)
    excess_returns = returns - (0.045 / 252.0)
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0.0
    
    cum = (1.0 + returns).cumprod()
    max_dd = (cum / cum.cummax() - 1.0).min()
    
    return {
        "total_return": total_ret,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "final_nav": nav_series.iloc[-1]
    }

def main():
    print("=" * 80)
    print("STARTING ISOLATED US STOCK MOMENTUM STRATEGY BACKTEST")
    print("=" * 80)
    
    data_dict = download_us_data(US_UNIVERSE, START_DATE, END_DATE)
    nav_df, trades = run_simulation(data_dict, US_UNIVERSE)
    
    metrics = calculate_metrics(nav_df["NAV"])
    
    # Download SPY benchmark
    spy_data = yf.download("SPY", start=nav_df.index[0], end=nav_df.index[-1], progress=False)
    spy_data.columns = [c if isinstance(c, str) else c[0] for c in spy_data.columns]
    spy_shares = INITIAL_CAPITAL / spy_data["Close"].iloc[0]
    spy_nav = spy_data["Close"] * spy_shares
    spy_nav.index = [d.strftime("%Y-%m-%d") for d in spy_nav.index]
    
    # Sync benchmarks
    common_idx = nav_df.index.intersection(spy_nav.index)
    nav_df = nav_df.loc[common_idx]
    spy_nav = spy_nav.loc[common_idx]
    
    bench_metrics = calculate_metrics(spy_nav)
    
    # Win rate
    wins = [t for t in trades if t["profit"] > 0]
    win_rate = len(wins) / len(trades) if trades else 0.0
    
    print("\n" + "=" * 80)
    print("PERFORMANCE RESULTS")
    print("=" * 80)
    print(f"Strategy CAGR:     {metrics['cagr']*100:.2f}% (vs. SPY: {bench_metrics['cagr']*100:.2f}%)")
    print(f"Strategy Sharpe:   {metrics['sharpe']:.2f} (vs. SPY: {bench_metrics['sharpe']:.2f})")
    print(f"Strategy Max DD:   {metrics['max_drawdown']*100:.2f}% (vs. SPY: {bench_metrics['max_drawdown']*100:.2f}%")
    print(f"Total Trades:      {len(trades)} (Win Rate: {win_rate*100:.1f}%)")
    print(f"Final NAV:         ${metrics['final_nav']:,.2f} USD")
    print("=" * 80)
    
    # Write Report
    report_path = "us_stocks_backtest_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Isolated US Stock Momentum Strategy Backtest Report\n\n")
        f.write(f"**Period:** {nav_df.index[0]} to {nav_df.index[-1]} | **Initial Capital:** $100,000.00 USD\n\n")
        f.write("## 1. Executive Performance Summary\n\n")
        f.write("| Metric | US Stock Momentum Strategy | SPY Buy & Hold Benchmark |\n")
        f.write("| :--- | :---: | :---: |\n")
        f.write(f"| **Total Return** | **{metrics['total_return']*100:.2f}%** | **{bench_metrics['total_return']*100:.2f}%** |\n")
        f.write(f"| **CAGR** | **{metrics['cagr']*100:.2f}%** | **{bench_metrics['cagr']*100:.2f}%** |\n")
        f.write(f"| **Sharpe Ratio** | **{metrics['sharpe']:.2f}** | **{bench_metrics['sharpe']:.2f}** |\n")
        f.write(f"| **Max Drawdown** | **{metrics['max_drawdown']*100:.2f}%** | **{bench_metrics['max_drawdown']*100:.2f}%** |\n")
        f.write(f"| **Final Portfolio Value** | **${metrics['final_nav']:,.2f}** | **${bench_metrics['final_nav']:,.2f}** |\n\n")
        
        f.write("## 2. Strategy Parameters\n\n")
        f.write(f"- **Universe**: {', '.join(US_UNIVERSE)}\n")
        f.write("- **Trend Filter**: 200-day Simple Moving Average (SMA 200)\n")
        f.write("- **Indicators**: MACD (12, 26, 9) crossing Signal Line\n")
        f.write(f"- **Trailing Stop**: Armed at +{TRAILING_ARM_PCT*100:.1f}%, trailing {TRAILING_STOP_PCT*100:.1f}% below peak\n")
        f.write(f"- **Sizing**: Equal-weight (100% exposure distributed equally across bullish assets)\n")
        f.write(f"- **Slippage Model**: {SLIPPAGE_PCT*100:.2f}% flat transaction cost per order\n\n")
        
        f.write("## 3. Trade Log\n\n")
        f.write(f"* **Total Trades Executed**: {len(trades)}\n")
        f.write(f"* **Win Rate**: {win_rate*100:.1f}%\n\n")
        f.write("| Ticker | Entry Date | Exit Date | Entry Price | Exit Price | Shares | Net Profit | Profit % | Reason |\n")
        f.write("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |\n")
        for t in trades:
            prof_pct = (t["exit_price"] / t["entry_price"] - 1.0) * 100.0
            prof_sign = "+" if t["profit"] >= 0 else ""
            f.write(f"| {t['ticker']} | {t['entry_date']} | {t['exit_date']} | ${t['entry_price']:.2f} | ${t['exit_price']:.2f} | {t['shares']:.1f} | {prof_sign}${t['profit']:,.2f} | {prof_sign}{prof_pct:.2f}% | {t['reason']} |\n")
            
    # Save CSV
    nav_df.to_csv("us_stocks_backtest_nav.csv")
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    main()
