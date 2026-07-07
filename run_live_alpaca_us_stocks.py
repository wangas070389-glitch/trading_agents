import os
import sys
import json
import datetime
import yfinance as yf
import numpy as np
import pandas as pd

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from connectors.alpaca_connector import AlpacaConnector
from skills.us_stock_momentum import calculate_us_momentum_indicators, check_trailing_stop

# US Stocks Universe
US_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX", "AMD", "JPM"]

PORTFOLIO_FILE = "portfolio_us_stocks.json"
TRANSACTIONS_FILE = "transactions_us_stocks.md"
REBALANCE_TOLERANCE = 0.05  # 5% rebalance dead-zone
TRAILING_ARM_PCT = 0.10     # Arm at +10% profit
TRAILING_STOP_PCT = 0.05    # Exit if falls 5% below peak

def load_portfolio(dir_path):
    portfolio_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if os.path.exists(portfolio_path):
        try:
            with open(portfolio_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "total_capital": 100000.0,
        "cash_balance": 100000.0,
        "holdings": [],
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def save_portfolio(dir_path, portfolio):
    portfolio_path = os.path.join(dir_path, PORTFOLIO_FILE)
    with open(portfolio_path, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    transactions_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    gross = shares * price
    if action == "BUY":
        cash_flow_str = f"-{gross + fee:,.2f}"
    else:
        cash_flow_str = f"+{gross - fee:,.2f}"

    row = f"| {date_str} | {ticker} | {action} | {shares} | {price:.2f} | {cash_flow_str} | Market | FILLED | {note} |"

    if os.path.exists(transactions_path):
        with open(transactions_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# Transaction Ledger (Isolated US Stock Momentum)\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"

    lines = content.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            insert_idx = i
            break

    if insert_idx is not None:
        lines.insert(insert_idx, row)
    else:
        lines.append(row)

    with open(transactions_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def update_capital_reconciliation(dir_path, portfolio):
    transactions_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(transactions_path):
        return
        
    with open(transactions_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    recon_start = None
    for i, line in enumerate(lines):
        if "## Portfolio Capital Reconciliation" in line:
            recon_start = i
            break

    total_capital = portfolio["total_capital"]
    cash = portfolio["cash_balance"]
    invested = sum(h["shares"] * h["buy_price"] for h in portfolio["holdings"])
    total_value = cash + sum(h["shares"] * h.get("last_price", h["buy_price"]) for h in portfolio["holdings"])

    recon_lines = [
        "## Portfolio Capital Reconciliation",
        "",
        f"* **Initial Starting Capital**: ${total_capital:,.2f} USD",
        f"* **Total Deployed Capital**: ${invested:,.2f} USD ({invested/total_value*100:.1f}% invested)",
        f"* **Unallocated Cash Reserves**: ${cash:,.2f} USD ({cash/total_value*100:.1f}% cash)",
        f"* **Current Portfolio Market Value**: ${total_value:,.2f} USD (including cash)",
        ""
    ]

    if recon_start is not None:
        lines = lines[:recon_start] + recon_lines
    else:
        lines.extend(["", "---", ""] + recon_lines)

    with open(transactions_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    from halt_gate import halted
    if halted(dir_path, "us_stocks"):
        return
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    print("=" * 80)
    print("RUNNING LIVE INGESTION & EXECUTION: ISOLATED US STOCK MOMENTUM STRATEGY")
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
        print(f"Alpaca credentials missing or error connecting: {e}")
        print("US trades will run in mock/dry-run mode.")
        alpaca_client = None
        account_equity = 100000.0
        account_cash = 100000.0

    # 2. Load local tracking portfolio
    portfolio = load_portfolio(dir_path)
    portfolio["total_capital"] = account_equity
    
    # Map currently held items
    current_holdings = {h["ticker"]: h for h in portfolio["holdings"]}
    
    # 3. Download data & compute signals
    print("\nFetching daily bars & computing signals...")
    bullish_assets = []
    current_prices = {}
    current_highs = {}
    
    # Download in batch for speed
    try:
        data = yf.download(US_UNIVERSE, period="1y", interval="1d", group_by='ticker', progress=False)
    except Exception as e:
        print(f"Batch fetch failed: {e}")
        data = pd.DataFrame()

    for ticker in US_UNIVERSE:
        try:
            # Extract ticker history from batch or single fetch
            if not data.empty and isinstance(data.columns, pd.MultiIndex) and ticker in data.columns.levels[0]:
                hist = data[ticker].dropna(how='all')
            else:
                hist = yf.Ticker(ticker).history(period="1y", interval="1d")
                
            if hist.empty or len(hist) < 200:
                print(f"  Ticker {ticker:6} | Insufficient history")
                continue
                
            hist.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in hist.columns]
            
            # Calculate Indicators
            hist_ind = calculate_us_momentum_indicators(hist)
            row = hist_ind.iloc[-1]
            
            close = float(row["close"])
            high = float(row["high"])
            sma = float(row["sma200"])
            macd_val = float(row["macd"])
            sig_val = float(row["signal"])
            
            current_prices[ticker] = close
            current_highs[ticker] = high
            
            is_bullish = close > sma and macd_val > sig_val
            status_str = "BULLISH" if is_bullish else "BEARISH/NEUTRAL"
            print(f"  Ticker {ticker:6} | Close: ${close:7.2f} | SMA200: ${sma:7.2f} | Signal: {status_str}")
            
            if is_bullish:
                bullish_assets.append(ticker)
        except Exception as e:
            print(f"  Ticker {ticker:6} | Failed to fetch/calculate: {e}")

    # 4. Check exit rules & trailing stops for held assets
    active_bullish_assets = []
    
    for ticker in bullish_assets:
        if ticker in current_holdings:
            h = current_holdings[ticker]
            # Update peak price
            current_high = current_highs.get(ticker, current_prices[ticker])
            h["peak_price"] = max(h.get("peak_price", h["buy_price"]), current_high)
            
            # Check trailing stop
            should_exit, updated_peak = check_trailing_stop(
                buy_price=h["buy_price"],
                current_price=current_prices[ticker],
                peak_price=h["peak_price"],
                arm_pct=TRAILING_ARM_PCT,
                trail_pct=TRAILING_STOP_PCT
            )
            h["peak_price"] = updated_peak
            
            if should_exit:
                print(f"  |-- [EXIT TRIGGERED] Trailing stop hit for {ticker}. Forcing liquidation.")
                # We do NOT add to active bullish assets (this will trigger a sell order)
            else:
                active_bullish_assets.append(ticker)
        else:
            active_bullish_assets.append(ticker)

    # 5. Calculate target weights
    target_weights = {t: 0.0 for t in US_UNIVERSE}
    if active_bullish_assets:
        weight_per_asset = min(0.25, 1.0 / len(active_bullish_assets))
        for ticker in active_bullish_assets:
            target_weights[ticker] = weight_per_asset

    # 6. Calculate rebalancing trade sizes
    print("\nCalculating rebalancing trades...")
    rebalancing_trades = []
    
    for ticker in US_UNIVERSE:
        if ticker not in current_prices:
            continue
            
        close_price = current_prices[ticker]
        target_w = target_weights[ticker]
        
        # Get current shares from local tracking
        shares_held = current_holdings.get(ticker, {}).get("shares", 0.0)
        current_w = (shares_held * close_price) / account_equity if account_equity > 0 else 0.0
        
        # Calculate target value and trade value
        target_val = account_equity * target_w
        current_val = shares_held * close_price
        trade_val = target_val - current_val
        
        # Rebalance if weight difference is larger than tolerance or we want to exit completely
        if target_w == 0.0 and shares_held > 0.0:
            # Liquidate
            rebalancing_trades.append({
                "ticker": ticker,
                "action": "SELL",
                "shares": int(shares_held),
                "price": close_price,
                "reason": "Exit/Bearish Signal"
            })
        elif abs(target_w - current_w) > REBALANCE_TOLERANCE:
            if trade_val > 0.0:
                shares_to_buy = int(trade_val / close_price)
                if shares_to_buy > 0:
                    rebalancing_trades.append({
                        "ticker": ticker,
                        "action": "BUY",
                        "shares": shares_to_buy,
                        "price": close_price,
                        "reason": f"Buy Rebalance to {target_w:.1%}"
                    })
            elif trade_val < 0.0 and shares_held > 0.0:
                shares_to_sell = int(abs(trade_val) / close_price)
                shares_to_sell = min(shares_to_sell, int(shares_held))
                if shares_to_sell > 0:
                    rebalancing_trades.append({
                        "ticker": ticker,
                        "action": "SELL",
                        "shares": shares_to_sell,
                        "price": close_price,
                        "reason": f"Sell Rebalance to {target_w:.1%}"
                    })

    # 7. Execute trades on Alpaca
    updated_holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}
    
    # Sells first to raise cash
    sells = [t for t in rebalancing_trades if t["action"] == "SELL"]
    buys = [t for t in rebalancing_trades if t["action"] == "BUY"]
    
    for trade in (sells + buys):
        ticker = trade["ticker"]
        action = trade["action"]
        shares = trade["shares"]
        price = trade["price"]
        reason = trade["reason"]
        
        note = f"Isolated US Stock Momentum strategy: {reason}"
        
        executed = True
        if alpaca_client:
            print(f"  |-- [Alpaca Order] Submitting {action} order for {shares} shares of {ticker}...")
            res = alpaca_client.submit_and_confirm(ticker=ticker, qty=shares, side=action)
            executed = res["filled"]
            if executed:
                shares = res["filled_qty"] or shares
                price = res["filled_avg_price"] or price
                note = f"Alpaca Order {res['id']} FILLED | {note}"
                print(f"  +-- [Alpaca FILLED] {shares} @ ${price:.2f}")
            else:
                print(f"  +-- [Alpaca NOT FILLED] status={res['status']}. Ledger NO modificado.")
                log_transaction(dir_path, today_str, ticker, f"{action}-REJECTED", shares, price, f"Alpaca {res['status']} | {note}")
        else:
            print(f"  |-- [Mock Order] {action} {shares} shares of {ticker} @ ${price:.2f} ({reason})")
        if not executed:
            continue
            
        # Update capital ledger
        net_impact = shares * price
        if action == "BUY":
            account_cash -= net_impact
            if ticker in updated_holdings_dict:
                h = updated_holdings_dict[ticker]
                old_cost = h["shares"] * h["buy_price"]
                new_cost = old_cost + net_impact
                h["shares"] += shares
                h["buy_price"] = round(new_cost / h["shares"], 2)
                h["last_price"] = price
                h["peak_price"] = max(h.get("peak_price", price), current_highs.get(ticker, price))
                h["target_weight"] = target_weights[ticker]
            else:
                updated_holdings_dict[ticker] = {
                    "ticker": ticker,
                    "shares": shares,
                    "buy_price": price,
                    "last_price": price,
                    "peak_price": current_highs.get(ticker, price),
                    "target_weight": target_weights[ticker]
                }
        else:
            account_cash += net_impact
            if ticker in updated_holdings_dict:
                h = updated_holdings_dict[ticker]
                h["shares"] -= shares
                h["last_price"] = price
                h["target_weight"] = target_weights[ticker]
                if h["shares"] <= 0:
                    del updated_holdings_dict[ticker]
                    
        log_transaction(dir_path, today_str, ticker, action, shares, price, note)

    # 8. Update portfolio file
    portfolio["holdings"] = list(updated_holdings_dict.values())
    portfolio["cash_balance"] = round(account_cash, 2)
    portfolio["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    save_portfolio(dir_path, portfolio)
    update_capital_reconciliation(dir_path, portfolio)
    
    print("\nUS Stocks portfolio execution finished!")
    print("=" * 80)

if __name__ == "__main__":
    main()
