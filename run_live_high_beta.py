import os
import sys
import json
import datetime
import argparse
import yfinance as yf
import numpy as np
import pandas as pd

# local import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from connectors.alpaca_connector import AlpacaConnector
from skills.us_dcf_valuation import calculate_us_dcs

# Strategy Constants
US_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX", "AMD", "JPM"]
ALL_TICKERS = US_TICKERS + ["SPY"]

PORTFOLIO_FILE = "portfolio_high_beta.json"
TRANSACTIONS_FILE = "transactions_high_beta.md"
REPORT_FILE = "high_beta_report_live.md"

TRANSACTION_FEE_RATE = 0.0029
MAX_CONCURRENT_POSITIONS = 3
MAX_POSITION_WEIGHT = 0.33
MONTHLY_CONTRIBUTION = 1000.0  # USD
USD_CASH_YIELD = 0.045         # 4.5% annual sweep yield

def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if not os.path.exists(p_path):
        return {
            "total_capital": 100000.0,
            "cash_balance": 100000.0,
            "holdings": [],
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    with open(p_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_portfolio(dir_path, portfolio):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    portfolio["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(p_path, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(t_path):
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("# Transaction Log (High-Beta Value-Momentum Strategy)\n\n| Date | Ticker | Action | Shares | Price | Fee | Net Amount | Note |\n| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |\n---\n")
            
    net_amount = shares * price
    if action in ["BUY", "DEPOSIT"]:
        net_amount = -(net_amount + fee)
    else:
        net_amount = net_amount - fee
        
    lines = []
    with open(t_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split("\n")
    row = f"| {date_str} | {ticker} | {action} | {shares:.4f} | ${price:.4f} | ${fee:.2f} | ${net_amount:,.2f} | {note} |"
    
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            insert_idx = i
            break
            
    if insert_idx is not None:
        lines.insert(insert_idx, row)
    else:
        lines.append(row)
        
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def update_capital_reconciliation(dir_path, portfolio):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(t_path):
        return
        
    with open(t_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split("\n")
    recon_start = None
    for i, line in enumerate(lines):
        if "## Portfolio Capital Reconciliation" in line:
            recon_start = i
            break
            
    total_capital = portfolio["total_capital"]
    cash = portfolio["cash_balance"]
    invested = sum(h["shares"] * h.get("last_price", h["buy_price"]) for h in portfolio["holdings"])
    total_value = cash + invested
    
    recon_lines = [
        "## Portfolio Capital Reconciliation",
        "",
        f"* **Initial + Inflow Capital**: ${total_capital:,.2f} USD",
        f"* **Total Deployed Capital**: ${invested:,.2f} USD ({invested/total_value*100:.1f}% invested)",
        f"* **Unallocated Cash Reserves**: ${cash:,.2f} USD ({cash/total_value*100:.1f}% cash)",
        f"* **Current Portfolio Market Value**: ${total_value:,.2f} USD (including cash)",
        ""
    ]
    
    if recon_start is not None:
        lines = lines[:recon_start] + recon_lines
    else:
        lines.extend(["", "---", ""] + recon_lines)
        
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    df["sma100"] = close.rolling(window=100).mean()
    
    # ATR 14
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()
    
    # MACD (12, 26, 9)
    fast_ema = close.ewm(span=12, adjust=False).mean()
    slow_ema = close.ewm(span=26, adjust=False).mean()
    df["macd"] = fast_ema - slow_ema
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    return df

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    print("=" * 80)
    print(f"LIVE EXECUTION: HIGH-BETA VALUE-MOMENTUM STRATEGY ({today_str})")
    print("=" * 80)

    # 1. Connect to Alpaca
    alpaca_client = None
    try:
        alpaca_client = AlpacaConnector()
        account_info = alpaca_client.get_account_info()
        print(f"Connected to Alpaca Paper Account (ID: {account_info.get('id')})")
        account_equity = float(account_info.get("equity", 100000.0))
        account_cash = float(account_info.get("cash", 100000.0))
        print(f"Alpaca Account Equity: ${account_equity:,.2f} USD | Cash: ${account_cash:,.2f} USD")
    except Exception as e:
        print(f"Alpaca connection failed or credentials missing: {e}. US trades will run in mock mode.")
        alpaca_client = None
        account_equity = 100000.0
        account_cash = 100000.0

    # 2. Load portfolio tracking state
    portfolio = load_portfolio(dir_path)
    
    # Accrue daily cash yield (since last run)
    last_updated_str = portfolio.get("last_updated", today_str + " 00:00:00")
    if " " in last_updated_str:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
    else:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d")
        
    days_elapsed = max((datetime.datetime.now() - last_dt).days, 0)
    if days_elapsed > 0:
        yield_accrued = portfolio["cash_balance"] * ((USD_CASH_YIELD / 365.25) * days_elapsed)
        portfolio["cash_balance"] += yield_accrued
        portfolio["total_capital"] += yield_accrued
        print(f"[Sweep Yield] Accrued ${yield_accrued:,.2f} USD on cash reserves over {days_elapsed} days.")

    # 3. Detect monthly savings inflow
    today = datetime.date.today()
    is_new_month = today.year > last_dt.year or (today.year == last_dt.year and today.month > last_dt.month)

    if is_new_month:
        portfolio["cash_balance"] += MONTHLY_CONTRIBUTION
        portfolio["total_capital"] += MONTHLY_CONTRIBUTION
        print(f"[Savings Ingestion] New calendar month transition. Injected ${MONTHLY_CONTRIBUTION:,.2f} USD.")
        log_transaction(dir_path, today_str, "CASH", "DEPOSIT", 1, MONTHLY_CONTRIBUTION, "Monthly savings contribution", fee=0.0)

    # 4. Fetch dynamic risk-free rate & stock prices
    print("\nFetching Treasury Yield and stock history (2 years for beta calculation)...")
    try:
        tnx = yf.download("^TNX", period="5d", progress=False)
        tnx.columns = [c if isinstance(c, str) else c[0] for c in tnx.columns]
        rf_rate = float(tnx["Close"].iloc[-1]) / 100.0
    except Exception as e:
        print(f"  [WARN] Failed to fetch US 10Y Yield: {e}. Using fallback 4.5%.")
        rf_rate = 0.045
    print(f"  US 10-Year Treasury Yield (Risk-Free Rate): {rf_rate*100:.2f}%")

    try:
        # Fetch 2 years to calculate 252-day beta properly
        data = yf.download(ALL_TICKERS, period="2y", interval="1d", group_by='ticker', progress=False)
    except Exception as e:
        print(f"Batch download failed: {e}")
        data = pd.DataFrame()

    # Process prices and calculate rolling beta
    daily_returns = pd.DataFrame()
    price_data = {}
    current_prices = {}

    for ticker in ALL_TICKERS:
        try:
            if not data.empty and isinstance(data.columns, pd.MultiIndex) and ticker in data.columns.levels[0]:
                hist = data[ticker].dropna(how='all')
            else:
                hist = yf.Ticker(ticker).history(period="2y")
                
            if hist.empty or len(hist) < 252:
                print(f"  [WARN] Insufficient history for {ticker}")
                continue
                
            price_data[ticker] = hist
            current_prices[ticker] = float(hist["Close"].iloc[-1])
            daily_returns[ticker] = hist["Close"].pct_change()
        except Exception as e:
            print(f"  [WARN] Error processing {ticker}: {e}")

    # Calculate current betas relative to SPY
    active_betas = {}
    if "SPY" in daily_returns.columns:
        spy_var = daily_returns["SPY"].iloc[-252:].var()
        for ticker in US_TICKERS:
            if ticker in daily_returns.columns and ticker != "SPY":
                cov = daily_returns[ticker].iloc[-252:].cov(daily_returns["SPY"].iloc[-252:])
                active_betas[ticker] = cov / spy_var
                print(f"  Beta for {ticker}: {active_betas[ticker]:.2f}")

    # Calculate indicators for each stock
    indicators_dict = {}
    for ticker in US_TICKERS:
        if ticker in price_data:
            indicators_dict[ticker] = calculate_indicators(price_data[ticker])

    # 5. Evaluate exits
    print("\nEvaluating exits for current holdings...")
    action_logs = []
    
    current_holdings = portfolio.get("holdings", [])
    updated_holdings = []
    
    for h in current_holdings:
        ticker = h["ticker"]
        if ticker not in current_prices:
            updated_holdings.append(h)
            continue
            
        close_price = current_prices[ticker]
        low_price = float(price_data[ticker]["Low"].iloc[-1])
        
        # Update peak price & arming
        h["last_price"] = close_price
        if close_price > h.get("peak_price", h["buy_price"]):
            h["peak_price"] = close_price
            unrealized_ret = (close_price / h["buy_price"]) - 1.0
            if unrealized_ret >= 0.15:
                if not h.get("armed", False):
                    h["armed"] = True
                    print(f"  Armed trailing stop for {ticker} (Unrealized return: {unrealized_ret*100:.1f}%)")
                    
        # Check exits
        exit_triggered = False
        exit_reason = ""
        
        # A. Trailing Stop (5% below peak close once armed)
        peak = h.get("peak_price", h["buy_price"])
        if h.get("armed", False) and low_price < peak * 0.95:
            exit_triggered = True
            close_price = peak * 0.95  # Simulated exit price
            exit_reason = f"Trailing Stop (5% below Peak ${peak:.2f})"
            
        # B. Indicator exits
        if not exit_triggered and ticker in indicators_dict:
            ind_df = indicators_dict[ticker]
            curr_macd = float(ind_df["macd"].iloc[-1])
            curr_signal = float(ind_df["signal"].iloc[-1])
            curr_sma = float(ind_df["sma100"].iloc[-1])
            
            prev_macd = float(ind_df["macd"].iloc[-2])
            prev_signal = float(ind_df["signal"].iloc[-2])
            
            macd_cross_down = (prev_macd >= prev_signal) and (curr_macd < curr_signal)
            below_trend = close_price < curr_sma
            
            if macd_cross_down:
                exit_triggered = True
                exit_reason = "MACD Cross Down"
            elif below_trend:
                exit_triggered = True
                exit_reason = "SMA 100 Trend Break"
                
        if exit_triggered:
            shares_to_sell = h["shares"]
            proceeds = shares_to_sell * close_price
            fee = proceeds * TRANSACTION_FEE_RATE
            net_proceeds = proceeds - fee
            
            portfolio["cash_balance"] += net_proceeds
            
            if alpaca_client:
                try:
                    alpaca_client.submit_order(ticker=ticker, qty=int(shares_to_sell), side="sell")
                except Exception as e:
                    print(f"  [Alpaca SELL FAILED] Exit {ticker}: {e}")
                    
            realized_pnl = net_proceeds - (shares_to_sell * h["buy_price"])
            pnl_pct = (close_price / h["buy_price"] - 1.0) * 100.0
            
            log_transaction(dir_path, today_str, ticker, "SELL", shares_to_sell, close_price, f"Exit: {exit_reason}", fee=fee)
            action_logs.append(f"SOLD {shares_to_sell:.4f} shares of {ticker} at ${close_price:.2f} due to {exit_reason} (P/L: ${realized_pnl:,.2f}, {pnl_pct:.1f}%)")
            print(f"  Exited {ticker}: {exit_reason}")
        else:
            updated_holdings.append(h)
            
    portfolio["holdings"] = updated_holdings

    # 6. Evaluate entries
    holdings_count = len(portfolio["holdings"])
    if holdings_count < MAX_CONCURRENT_POSITIONS:
        print(f"\nCurrent holdings: {holdings_count}/{MAX_CONCURRENT_POSITIONS}. Evaluating new entries...")
        
        # Calculate current portfolio value to size positions
        invested_value = sum(h["shares"] * current_prices.get(h["ticker"], h["last_price"]) for h in portfolio["holdings"])
        portfolio_value = portfolio["cash_balance"] + invested_value
        
        candidates = []
        for ticker in US_TICKERS:
            # Skip existing holdings
            if any(h["ticker"] == ticker for h in portfolio["holdings"]):
                continue
                
            if ticker not in indicators_dict or ticker not in active_betas:
                continue
                
            ind_df = indicators_dict[ticker]
            curr_close = current_prices[ticker]
            curr_sma = float(ind_df["sma100"].iloc[-1])
            curr_macd = float(ind_df["macd"].iloc[-1])
            curr_signal = float(ind_df["signal"].iloc[-1])
            
            prev_macd = float(ind_df["macd"].iloc[-2])
            prev_signal = float(ind_df["signal"].iloc[-2])
            
            macd_cross_up = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
            trend_bull = curr_close > curr_sma
            
            if trend_bull and macd_cross_up:
                # Calculate DCS margin of safety
                try:
                    dcf_res = calculate_us_dcs(ticker, curr_close, rf_rate)
                    dcs = float(dcf_res["margin_of_safety"])
                except Exception as e:
                    print(f"  DCS valuation failed for {ticker}: {e}")
                    dcs = 0.0
                    
                if dcs >= 0.15:
                    candidates.append((ticker, active_betas[ticker], curr_close, dcs, float(ind_df["atr"].iloc[-1])))
                    print(f"  Candidate: {ticker} (Beta: {active_betas[ticker]:.2f}, DCS MOS: {dcs:.2%}) - VALID")
                else:
                    print(f"  Candidate: {ticker} (Beta: {active_betas[ticker]:.2f}, DCS MOS: {dcs:.2%}) - EXCLUDED (DCS below 15%)")

        # Sort by beta descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        for ticker, beta_val, close_price, dcs_val, atr_val in candidates:
            if len(portfolio["holdings"]) >= MAX_CONCURRENT_POSITIONS:
                break
                
            # Sizing (2% ATR Risk Parity)
            risk_amt = portfolio_value * 0.02
            stop_dist = 2.5 * atr_val
            
            if stop_dist > 0:
                target_shares = risk_amt / stop_dist
                target_val = target_shares * close_price
            else:
                target_val = portfolio_value * MAX_POSITION_WEIGHT
                
            target_val = min(target_val, portfolio_value * MAX_POSITION_WEIGHT)
            
            if target_val > portfolio["cash_balance"]:
                target_val = portfolio["cash_balance"] * 0.98
                
            shares = target_val / (close_price * (1.0 + TRANSACTION_FEE_RATE))
            if shares > 0.0001:
                cost = shares * close_price
                fee = cost * TRANSACTION_FEE_RATE
                total_cost = cost + fee
                
                portfolio["cash_balance"] -= total_cost
                portfolio["holdings"].append({
                    "ticker": ticker,
                    "shares": shares,
                    "buy_price": close_price,
                    "last_price": close_price,
                    "peak_price": close_price,
                    "armed": False,
                    "entry_date": today_str,
                    "beta": beta_val,
                    "dcs": dcs_val
                })
                
                if alpaca_client:
                    try:
                        alpaca_client.submit_order(ticker=ticker, qty=int(shares), side="buy")
                    except Exception as e:
                        print(f"  [Alpaca BUY FAILED] Entry {ticker}: {e}")
                        
                log_transaction(dir_path, today_str, ticker, "BUY", shares, close_price, f"Entry (Beta: {beta_val:.2f}, DCS MOS: {dcs_val:.2%})", fee=fee)
                action_logs.append(f"BOUGHT {shares:.4f} shares of {ticker} at ${close_price:.2f} (Beta: {beta_val:.2f}, DCS MOS: {dcs_val:.2%})")
                print(f"  Entered {ticker} with weight {target_val/portfolio_value*100:.1f}%")
    else:
        print("Portfolio is already at max concurrent positions cap (3).")

    # Update total portfolio value and holdings details
    invested_value = sum(h["shares"] * current_prices.get(h["ticker"], h["last_price"]) for h in portfolio["holdings"])
    portfolio_value = portfolio["cash_balance"] + invested_value
    portfolio["total_capital"] = portfolio_value  # Update current capital
    
    # Save the updated portfolio tracking state
    save_portfolio(dir_path, portfolio)
    update_capital_reconciliation(dir_path, portfolio)

    # 7. Write live execution report
    report_md = f"""# Isolated High-Beta Value-Momentum Execution Report
**Execution Date:** {today_str} | **Strategy Version:** Upgraded High-Beta V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} USD
* **Total Cash Balance:** ${portfolio["cash_balance"]:,.2f} USD
* **Equity Exposure:** {(invested_value / portfolio_value * 100):.1f}%
* **Number of Positions:** {len(portfolio["holdings"])}/3

## 2. Current Holdings
| Ticker | Shares Held | Buy Price | Last Price | Market Value | Peak Price | Armed | Beta | DCS MOS |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for h in portfolio["holdings"]:
        mkt_val = h["shares"] * h["last_price"]
        report_md += f"| **{h['ticker']}** | {h['shares']:.4f} | ${h['buy_price']:.2f} | ${h['last_price']:.2f} | ${mkt_val:,.2f} | ${h.get('peak_price', h['buy_price']):.2f} | {h.get('armed', False)} | {h.get('beta', 0.0):.2f} | {h.get('dcs', 0.0):.2%} |\n"

    report_md += "\n## 3. Today's Execution Logs\n"
    if is_new_month:
        report_md += f"* **[SAVINGS DEPOSIT]** Detected month transition. Credited $1,000.00 USD cash inflow.\n"
    if action_logs:
        for log in action_logs:
            report_md += f"* {log}\n"
    else:
        report_md += "* No rebalancing or trades required today.\n"

    report_path = os.path.join(dir_path, REPORT_FILE)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print(f"\nExecution complete. Saved report to {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
