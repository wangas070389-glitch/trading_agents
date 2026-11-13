"""
Strategy 30 LIVE Runner: Golden MACD US Stocks
=============================================
Runs daily to rebalance a 5-ticker US tech portfolio in USD using Golden parameters.
"""
import os
import sys
import json
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

PORTFOLIO_FILE = "portfolio_strategy30.json"
TRANSACTIONS_FILE = "transactions_strategy30.md"
REPORT_FILE = "strategy30_report_live.md"

TRADING_DAYS = 252
TRANSACTION_COST = 0.0001
RF_USD = 0.045

def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if not os.path.exists(p_path):
        return {"total_capital": 100000.0, "cash_balance": 100000.0, "holdings": [],
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    with open(p_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_portfolio(dir_path, portfolio):
    portfolio["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(dir_path, PORTFOLIO_FILE), "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(t_path):
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("# Strategy 30 Transaction Ledger (Golden MACD US Stocks)\n\n"
                    "| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n"
                    "| :--- | :--- | :--- | ---: | ---: | ---: | :--- | :--- | :--- |\n---\n")
    with open(t_path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    gross = shares * price
    impact = f"-{gross + fee:,.2f}" if action in ["BUY", "DEPOSIT"] else f"+{gross - fee:,.2f}" if action != "INTEREST" else f"+{gross:,.2f}"
    row = f"| {date_str} | {ticker} | {action} | {shares:.4f} | ${price:.4f} | ${impact} | Market | FILLED | {note} |"
    idx = next((i for i, l in enumerate(lines) if l.strip() == "---"), None)
    lines.insert(idx, row) if idx is not None else lines.append(row)
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().isoformat()
    now_local = datetime.datetime.now()
    
    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 30 GOLDEN MACD US STOCKS ({today_str} USD)")
    print("=" * 80)
    
    portfolio = load_portfolio(dir_path)
    cash = portfolio["cash_balance"]
    
    # Calculate daily cash sweep yield on USD
    last_str = portfolio.get("last_updated", today_str + " 00:00:00")
    fmt = "%Y-%m-%d %H:%M:%S" if " " in last_str else "%Y-%m-%d"
    last_dt = datetime.datetime.strptime(last_str, fmt)
    days = max((now_local - last_dt).total_seconds() / 86400.0, 0.0)
    
    if days > 0:
        interest = cash * (RF_USD / 365.25) * days
        cash = round(cash + interest, 2)
        portfolio["cash_balance"] = cash
        log_transaction(dir_path, today_str, "CASH_SWEEP", "INTEREST", 1, interest, "USD Sweep interest", 0.0)
        print(f"[USD Sweep] +${interest:,.4f} USD")
        
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    
    print("Downloading US stock prices...")
    try:
        data = yf.download(tickers, period="200d", group_by="ticker", progress=False)
        if data.empty:
            print("CRITICAL: pricing data feed empty. Exit.")
            save_portfolio(dir_path, portfolio)
            return
    except Exception as e:
        print(f"CRITICAL: data ingest failed ({e}). Exit.")
        save_portfolio(dir_path, portfolio)
        return
        
    active_holdings = {h["ticker"]: h for h in portfolio.get("holdings", [])}
    new_holdings = []
    
    for ticker in tickers:
        df = data[ticker].dropna(subset=["Close"])
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
            
        prices = df["Close"].values
        ma_long = df["Close"].ewm(span=55, adjust=False).mean().values
        ema_fast = df["Close"].ewm(span=13, adjust=False).mean()
        ema_slow = df["Close"].ewm(span=34, adjust=False).mean()
        macd = (ema_fast - ema_slow).values
        signal = (ema_fast - ema_slow).ewm(span=8, adjust=False).mean().values
        
        close_t = prices[-1]
        ma_t = ma_long[-1]
        
        crossover_bull = macd[-1] > signal[-1] and macd[-2] <= signal[-2]
        crossover_bear = macd[-1] < signal[-1] and macd[-2] >= signal[-2]
        
        holding = active_holdings.get(ticker)
        
        if holding is None:
            if close_t > ma_t and crossover_bull:
                target_alloc = portfolio["total_capital"] * 0.18
                if cash >= target_alloc:
                    shares = target_alloc / close_t
                    fee = target_alloc * TRANSACTION_COST
                    cash = round(cash - (target_alloc + fee), 2)
                    holding = {
                        "ticker": ticker,
                        "shares": shares,
                        "buy_price": close_t,
                        "last_price": close_t,
                        "peak_price": close_t,
                        "trailing_armed": False
                    }
                    log_transaction(dir_path, today_str, ticker, "BUY", shares, close_t, "Golden MACD US entry", fee)
                    print(f"[{ticker}] BUY {shares:.4f} shares @ ${close_t:.2f} USD")
        else:
            peak_price = max(holding.get("peak_price", holding["buy_price"]), close_t)
            holding["peak_price"] = peak_price
            holding["last_price"] = close_t
            perf_from_peak = close_t / peak_price - 1.0
            
            is_armed = holding.get("trailing_armed", False)
            if not is_armed and (close_t / holding["buy_price"] - 1.0) >= 0.15:
                is_armed = True
                holding["trailing_armed"] = True
                
            sell = False
            note = ""
            if is_armed and perf_from_peak < -0.02:
                sell = True
                note = "Trailing stop triggered"
            elif crossover_bear or close_t < ma_t:
                sell = True
                note = "MACD crossover or Trend break exit"
                
            if sell:
                shares = holding["shares"]
                val = shares * close_t
                fee = val * TRANSACTION_COST
                cash = round(cash + (val - fee), 2)
                log_transaction(dir_path, today_str, ticker, "SELL", shares, close_t, note, fee)
                print(f"[{ticker}] SELL {shares:.4f} shares @ ${close_t:.2f} USD due to: {note}")
                holding = None
                
        if holding is not None:
            new_holdings.append(holding)
            
    portfolio["cash_balance"] = cash
    portfolio["holdings"] = new_holdings
    
    total_val = cash
    for h in new_holdings:
        total_val += h["shares"] * h["last_price"]
    portfolio["total_capital"] = total_val
    
    save_portfolio(dir_path, portfolio)
    
    # Generate live report
    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(f"# Strategy 30 Live Status Report\n\n")
        f.write(f"**Last Run:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Capital:** ${total_val:,.2f} USD\n")
        f.write(f"**Cash Balance:** ${cash:,.2f} USD\n\n")
        f.write(f"## Current Holdings\n\n")
        if new_holdings:
            f.write(f"| Ticker | Shares | Buy Price | Current Price | Return | Peak Price |\n")
            f.write(f"| :--- | ---: | ---: | ---: | ---: | ---: |\n")
            for h in new_holdings:
                ret = (h['last_price'] / h['buy_price'] - 1.0) * 100
                f.write(f"| {h['ticker']} | {h['shares']:.4f} | ${h['buy_price']:.2f} | ${h['last_price']:.2f} | {ret:+.2f}% | ${h['peak_price']:.2f} |\n")
        else:
            f.write(f"No active US stock positions.\n")
            
    print(f"Strategy 30 Live Update Completed. Portfolio NAV: ${total_val:,.2f} USD")

if __name__ == "__main__":
    main()
