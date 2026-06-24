import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

from skills.us_dcf_valuation import calculate_us_dcs

# US Stocks Universe
US_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX", "AMD", "JPM"]

# Strategy params
START_DATE = "2021-06-20"
END_DATE = "2026-06-20"
INITIAL_CAPITAL = 100000.0        # USD
MONTHLY_CONTRIBUTION = 1000.0     # USD monthly savings inflow
TRANSACTION_FEE_RATE = 0.0029     # 0.29% brokerage fee
CONCENTRATION_CAP = 0.25          # Max 25% weight per position
MAX_CONCURRENT_POSITIONS = 5
DCS_ENTRY_THRESHOLD = 0.15

def solve_weights(dcs_scores, max_weight=0.25):
    if not dcs_scores:
        return {}
    tickers = list(dcs_scores.keys())
    scores = np.array([dcs_scores[t] for t in tickers])
    
    # Cap negative/low scores at a small positive value to avoid division by zero or negative weights
    scores = np.clip(scores, 0.01, 1.0)
    raw_weights = scores / np.sum(scores)
    
    weights = {t: raw_weights[i] for i, t in enumerate(tickers)}
    while True:
        capped = False
        excess = 0.0
        uncapped_sum = 0.0
        
        for t, w in weights.items():
            if w > max_weight:
                excess += (w - max_weight)
                weights[t] = max_weight
                capped = True
            else:
                uncapped_sum += w
                
        if not capped or excess <= 1e-6 or uncapped_sum <= 1e-6:
            break
            
        for t, w in weights.items():
            if w < max_weight:
                weights[t] += excess * (w / uncapped_sum)
    return weights

def download_data(tickers, start_date, end_date):
    print(f"Downloading daily data for {len(tickers)} US tickers from {start_date} to {end_date}...")
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
            if ticker in data.columns:
                ticker_df = data.dropna(how='all')
                universe_data[ticker] = ticker_df
                
    # Download US 10Y yield for dynamic risk free rate
    print("Downloading US 10Y Treasury yield (^TNX)...")
    tnx = yf.download("^TNX", start=warmup_start, end=end_date, progress=False)
    tnx.columns = [c if isinstance(c, str) else c[0] for c in tnx.columns]
    rf_series = tnx["Close"] / 100.0  # convert e.g. 4.5 to 0.045
    rf_series = rf_series.ffill().bfill()
    
    return universe_data, rf_series

def run_simulation(data_dict, rf_series, tickers):
    # Compute basic indicators (SMA 20, SMA 100) for each stock
    processed_data = {}
    for t in tickers:
        if t in data_dict:
            df = data_dict[t].copy()
            df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
            df["sma20"] = df["close"].rolling(window=20).mean()
            df["sma100"] = df["close"].rolling(window=100).mean()
            processed_data[t] = df
            
    # Find common timeline
    common_dates = None
    for t, df in processed_data.items():
        valid_idx = df["sma100"].dropna().index
        if common_dates is None:
            common_dates = set(valid_idx)
        else:
            common_dates = common_dates.intersection(set(valid_idx))
            
    sim_dates = sorted(list(common_dates))
    if not sim_dates:
        raise ValueError("Not enough history to align SMA 100 data.")
        
    print(f"Running DCS Value-Growth simulation over {len(sim_dates)} trading days...")
    
    # Align datasets
    for t in list(processed_data.keys()):
        processed_data[t] = processed_data[t].reindex(sim_dates).ffill()
        
    rf_series = rf_series.reindex(sim_dates).ffill().fillna(0.04)
    
    # State variables
    cash = INITIAL_CAPITAL
    shares_held = {t: 0.0 for t in processed_data}
    buy_prices = {t: 0.0 for t in processed_data}
    buy_dates = {t: None for t in processed_data}
    
    trades = []
    daily_nav = []
    
    last_rebalance_idx = -999
    last_month_val = -1
    total_capital = INITIAL_CAPITAL
    
    for day_idx, current_date in enumerate(sim_dates):
        # 1. Update prices & check monthly savings DCA inflow
        current_rf = float(rf_series.iloc[day_idx])
        
        # Monthly cash injection on transition of calendar month
        if last_month_val == -1:
            last_month_val = current_date.month
        elif current_date.month != last_month_val:
            last_month_val = current_date.month
            # Inject inflow
            cash += MONTHLY_CONTRIBUTION
            total_capital += MONTHLY_CONTRIBUTION
            
            # Active DCA Step
            # Find eligible holdings (Close > SMA 20 and DCS >= 0.15)
            active_holdings = [t for t, sh in shares_held.items() if sh > 0.0]
            if active_holdings:
                eligible_dca = []
                for t in active_holdings:
                    row = processed_data[t].iloc[day_idx]
                    close = float(row["close"])
                    sma20 = float(row["sma20"])
                    
                    # Calculate today's DCS
                    try:
                        dcf_res = calculate_us_dcs(t, close, current_rf)
                        dcs = float(dcf_res["margin_of_safety"])
                        if close > sma20 and dcs >= DCS_ENTRY_THRESHOLD:
                            eligible_dca.append((t, dcs, close))
                    except Exception:
                        pass
                
                # Split monthly cash inflow equally among top 3
                if eligible_dca:
                    eligible_dca.sort(key=lambda x: x[1], reverse=True)
                    top_dca = eligible_dca[:3]
                    alloc_per_stock = MONTHLY_CONTRIBUTION / len(top_dca)
                    
                    for t, dcs_val, close_price in top_dca:
                        fee = alloc_per_stock * TRANSACTION_FEE_RATE
                        cost_before_fee = alloc_per_stock - fee
                        shares_to_buy = cost_before_fee / close_price
                        
                        if cash >= alloc_per_stock:
                            cash -= alloc_per_stock
                            old_shares = shares_held[t]
                            old_cost = old_shares * buy_prices[t]
                            
                            shares_held[t] += shares_to_buy
                            buy_prices[t] = (old_cost + cost_before_fee) / shares_held[t]
                            
        # 2. Quarterly Rebalance (every 63 business days)
        if day_idx == 0 or (day_idx - last_rebalance_idx) >= 63:
            last_rebalance_idx = day_idx
            
            # Run screener
            candidates = []
            for t, df in processed_data.items():
                row = df.iloc[day_idx]
                close = float(row["close"])
                sma100 = float(row["sma100"])
                
                if close > sma100:
                    try:
                        dcf_res = calculate_us_dcs(t, close, current_rf)
                        dcs = float(dcf_res["margin_of_safety"])
                        if dcs >= DCS_ENTRY_THRESHOLD:
                            candidates.append((t, dcs, close))
                    except Exception:
                        pass
                        
            # Sort candidates by DCS and take top 5
            candidates.sort(key=lambda x: x[1], reverse=True)
            top_candidates = candidates[:MAX_CONCURRENT_POSITIONS]
            
            # Sizing weights
            target_dcs = {t: dcs for t, dcs, _ in top_candidates}
            target_weights = solve_weights(target_dcs, max_weight=CONCENTRATION_CAP)
            
            # Compute portfolio value for target allocation
            curr_value = sum(shares_held[tk] * float(processed_data[tk].iloc[day_idx]["close"]) for tk in processed_data)
            portfolio_equity = cash + curr_value
            
            # Sells First
            for t in list(shares_held.keys()):
                shares = shares_held[t]
                if shares > 0.0:
                    target_w = target_weights.get(t, 0.0)
                    close_price = float(processed_data[t].iloc[day_idx]["close"])
                    curr_w = (shares * close_price) / portfolio_equity if portfolio_equity > 0 else 0.0
                    
                    # Exit if no longer a candidate or sell down if overweighted by more than 5%
                    if target_w == 0.0:
                        sell_proceeds = shares * close_price
                        fee = sell_proceeds * TRANSACTION_FEE_RATE
                        cash += (sell_proceeds - fee)
                        
                        trades.append({
                            "ticker": t,
                            "entry_date": buy_dates.get(t, str(current_date)),
                            "exit_date": current_date.strftime("%Y-%m-%d"),
                            "entry_price": buy_prices[t],
                            "exit_price": close_price,
                            "shares": shares,
                            "profit": (sell_proceeds - fee) - (shares * buy_prices[t]),
                            "reason": "Exited Rebalance"
                        })
                        shares_held[t] = 0.0
                        buy_prices[t] = 0.0
                    elif (curr_w - target_w) > 0.05:
                        target_val = portfolio_equity * target_w
                        shares_to_sell = shares - (target_val / close_price)
                        if shares_to_sell > 0.01:
                            sell_proceeds = shares_to_sell * close_price
                            fee = sell_proceeds * TRANSACTION_FEE_RATE
                            cash += (sell_proceeds - fee)
                            
                            shares_held[t] -= shares_to_sell
                            
            # Buys Second
            for t, w in target_weights.items():
                close_price = float(processed_data[t].iloc[day_idx]["close"])
                curr_w = (shares_held[t] * close_price) / portfolio_equity if portfolio_equity > 0 else 0.0
                
                if (w - curr_w) > 0.05:
                    target_val = portfolio_equity * w
                    buy_val = target_val - (shares_held[t] * close_price)
                    
                    fee = buy_val * TRANSACTION_FEE_RATE
                    total_cost = buy_val + fee
                    
                    if total_cost > cash:
                        buy_val = cash / (1.0 + TRANSACTION_FEE_RATE)
                        fee = buy_val * TRANSACTION_FEE_RATE
                        total_cost = buy_val + fee
                        
                    shares_to_buy = buy_val / close_price
                    if shares_to_buy > 0.01:
                        cash -= total_cost
                        old_shares = shares_held[t]
                        old_cost = old_shares * buy_prices[t]
                        
                        shares_held[t] += shares_to_buy
                        buy_prices[t] = (old_cost + buy_val) / shares_held[t]
                        buy_dates[t] = current_date.strftime("%Y-%m-%d")
                        
        # Track daily NAV
        curr_val = sum(shares_held[tk] * float(processed_data[tk].iloc[day_idx]["close"]) for tk in processed_data)
        portfolio_equity = cash + curr_val
        daily_nav.append({
            "Date": current_date.strftime("%Y-%m-%d"),
            "NAV": portfolio_equity,
            "Capital": total_capital
        })
        
    nav_df = pd.DataFrame(daily_nav).set_index("Date")
    return nav_df, trades

def calculate_twr_metrics(nav_df):
    """Calculate GIPS-compliant Time-Weighted Return metrics to isolate strategy return from DCA inflows."""
    nav_df = nav_df.copy()
    nav_df["Return"] = nav_df["NAV"].pct_change()
    
    # Isolate returns from cash flow injections:
    # Daily returns = (NAV_t - Flow_t) / NAV_t-1 - 1
    # For simplicity, since inflows occur monthly, we can adjust daily returns on month start days:
    # We detect when "Capital" changes and adjust that day's return:
    capital_diff = nav_df["Capital"].diff().fillna(0.0)
    adjusted_returns = []
    
    for i in range(len(nav_df)):
        if i == 0:
            adjusted_returns.append(0.0)
            continue
            
        nav_prev = nav_df["NAV"].iloc[i-1]
        nav_curr = nav_df["NAV"].iloc[i]
        flow = capital_diff.iloc[i]
        
        # Adjust daily return: isolate the deposit
        ret = (nav_curr - flow) / nav_prev - 1.0
        adjusted_returns.append(ret)
        
    nav_df["Adj_Return"] = adjusted_returns
    
    # Calculate cumulative TWR CAGR
    cum_twr = (1.0 + nav_df["Adj_Return"]).cumprod()
    total_twr_ret = cum_twr.iloc[-1] - 1.0
    
    days = (pd.to_datetime(nav_df.index[-1]) - pd.to_datetime(nav_df.index[0])).days
    years = max(days / 365.25, 0.01)
    cagr = (1.0 + total_twr_ret) ** (1.0 / years) - 1.0
    
    # Sharpe (using Adj_Return and assume risk-free rate of 4.5% USD)
    excess_returns = nav_df["Adj_Return"].dropna() - (0.045 / 252.0)
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0.0
    
    # Max Drawdown based on cumulative TWR curve
    max_dd = (cum_twr / cum_twr.cummax() - 1.0).min()
    
    return {
        "total_return": total_twr_ret,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "final_nav": nav_df["NAV"].iloc[-1],
        "total_capital": nav_df["Capital"].iloc[-1],
        "cum_twr": cum_twr
    }

def main():
    print("=" * 80)
    print("STARTING US STOCK DCS VALUE-GROWTH STRATEGY BACKTEST")
    print("=" * 80)
    
    data_dict, rf_series = download_data(US_UNIVERSE, START_DATE, END_DATE)
    nav_df, trades = run_simulation(data_dict, rf_series, US_UNIVERSE)
    
    metrics = calculate_twr_metrics(nav_df)
    
    # Benchmark SPY Buy & Hold with identical DCA monthly contributions
    print("Simulating Buy & Hold SPY benchmark with DCA inflows...")
    spy_data = yf.download("SPY", start=nav_df.index[0], end=nav_df.index[-1], progress=False)
    spy_data.columns = [c if isinstance(c, str) else c[0] for c in spy_data.columns]
    
    spy_cash = INITIAL_CAPITAL
    spy_shares = 0.0
    spy_dates = [d.strftime("%Y-%m-%d") for d in spy_data.index]
    spy_nav_list = []
    
    last_month = -1
    for d_idx, d_str in enumerate(spy_dates):
        dt = pd.to_datetime(d_str)
        close = float(spy_data["Close"].iloc[d_idx])
        
        # Monthly contribution
        if last_month == -1:
            last_month = dt.month
        elif dt.month != last_month:
            last_month = dt.month
            spy_cash += MONTHLY_CONTRIBUTION
            
        # Buy SPY
        if spy_cash > 0:
            shares_bought = spy_cash / close
            spy_shares += shares_bought
            spy_cash = 0.0
            
        spy_nav_list.append({
            "Date": d_str,
            "NAV": spy_shares * close + spy_cash,
            "Capital": INITIAL_CAPITAL + (spy_dates[:d_idx+1].count(d_str) * 0.0) # calculate capital manually
        })
        
    spy_nav_df = pd.DataFrame(spy_nav_list).set_index("Date")
    # Align capital
    spy_nav_df["Capital"] = nav_df["Capital"]
    
    bench_metrics = calculate_twr_metrics(spy_nav_df)
    
    # Win rate
    wins = [t for t in trades if t["profit"] > 0]
    win_rate = len(wins) / len(trades) if trades else 0.0
    
    print("\n" + "=" * 80)
    print("PERFORMANCE RESULTS")
    print("=" * 80)
    print(f"Strategy CAGR (TWR):  {metrics['cagr']*100:.2f}% (vs. SPY: {bench_metrics['cagr']*100:.2f}%)")
    print(f"Strategy Sharpe:      {metrics['sharpe']:.2f} (vs. SPY: {bench_metrics['sharpe']:.2f})")
    print(f"Strategy Max DD:      {metrics['max_drawdown']*100:.2f}% (vs. SPY: {bench_metrics['max_drawdown']*100:.2f}%)")
    print(f"Total Trades:         {len(trades)} (Win Rate: {win_rate*100:.1f}%)")
    print(f"Final Portfolio NAV:  ${metrics['final_nav']:,.2f} USD")
    print(f"Total Invested (DCA): ${metrics['total_capital']:,.2f} USD")
    print("=" * 80)
    
    # Save CSV
    nav_df.to_csv("us_stocks_dcf_backtest_nav.csv")
    
    # Write Report
    report_path = "us_stocks_dcf_backtest_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Isolated US Stock DCS Value-Growth Strategy Backtest Report\n\n")
        f.write(f"**Period:** {nav_df.index[0]} to {nav_df.index[-1]} | **Starting Capital:** $100,000.00 USD\n\n")
        f.write("## 1. Executive Performance Summary\n\n")
        f.write("| Metric | US Stock DCS Value-Growth | SPY DCA Benchmark |\n")
        f.write("| :--- | :---: | :---: |\n")
        f.write(f"| **CAGR (Time-Weighted Return)** | **{metrics['cagr']*100:.2f}%** | **{bench_metrics['cagr']*100:.2f}%** |\n")
        f.write(f"| **Sharpe Ratio** | **{metrics['sharpe']:.2f}** | **{bench_metrics['sharpe']:.2f}** |\n")
        f.write(f"| **Max Drawdown** | **{metrics['max_drawdown']*100:.2f}%** | **{bench_metrics['max_drawdown']*100:.2f}%** |\n")
        f.write(f"| **Final Portfolio Value** | **${metrics['final_nav']:,.2f}** | **${bench_metrics['final_nav']:,.2f}** |\n")
        f.write(f"| **Total Deployed Capital (DCA)** | **${metrics['total_capital']:,.2f}** | **${bench_metrics['total_capital']:,.2f}** |\n\n")
        
        f.write("## 2. Strategy Parameters\n\n")
        f.write(f"- **Universe**: {', '.join(US_UNIVERSE)}\n")
        f.write("- **Screening Criteria**: `DCS (Margin of Safety) >= 0.15` and `Close > SMA 100`\n")
        f.write(f"- **Sizing Allocation**: Proportional conviction weighting, capped at `{CONCENTRATION_CAP*100:.0f}%` per position, max {MAX_CONCURRENT_POSITIONS} holdings\n")
        f.write(f"- **Monthly Inflow (DCA)**: ${MONTHLY_CONTRIBUTION:,.2f} USD on month start, deployed to holdings where `Close > SMA 20` and `DCS >= 0.15`\n")
        f.write("- **Transaction Friction**: 0.29% flat broker fee per transaction\n\n")
        
        f.write("## 3. Trade Log\n\n")
        f.write(f"* **Total Trades Executed**: {len(trades)}\n")
        f.write(f"* **Win Rate**: {win_rate*100:.1f}%\n\n")
        f.write("| Ticker | Entry Date | Exit Date | Entry Price | Exit Price | Shares | Net Profit | Profit % | Reason |\n")
        f.write("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |\n")
        for t in trades:
            prof_pct = (t["exit_price"] / t["entry_price"] - 1.0) * 100.0
            prof_sign = "+" if t["profit"] >= 0 else ""
            f.write(f"| {t['ticker']} | {t['entry_date']} | {t['exit_date']} | ${t['entry_price']:.2f} | ${t['exit_price']:.2f} | {t['shares']:.1f} | {prof_sign}${t['profit']:,.2f} | {prof_sign}{prof_pct:.2f}% | {t['reason']} |\n")
            
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    main()
