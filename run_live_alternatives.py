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
from skills.alternative_indicators import evaluate_signals

# Strategy Universe
CRYPTO = ["BTC-USD", "ETH-USD"]
COMMODITIES = ["GLD", "SLV", "USO", "DBA"]
FOREX = ["EURUSD=X", "GBPUSD=X", "USDMXN=X", "USDJPY=X"]
ALL_TICKERS = CRYPTO + COMMODITIES + FOREX

PORTFOLIO_FILE = "portfolio_alternatives.json"
TRANSACTIONS_FILE = "transactions_alternatives.md"
REPORT_FILE = "alternatives_report_live.md"

MAX_CRYPTO_WEIGHT = 0.20
MAX_COMMODITY_WEIGHT = 0.20
MAX_FOREX_WEIGHT = 0.15
MAX_CONCURRENT_POSITIONS = 5
MONTHLY_CONTRIBUTION = 1000.0  # USD
TRANSACTION_FEE_RATE = 0.0029

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
            f.write("# Transaction Log (Alternative Assets Strategy)\n\n| Date | Ticker | Action | Shares | Price | Fee | Net Amount | Note |\n| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |\n---\n")
            
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
    invested = sum(h["shares"] * h["buy_price"] for h in portfolio["holdings"])
    total_value = cash + sum(h["shares"] * h.get("last_price", h["buy_price"]) for h in portfolio["holdings"])
    
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

def translate_ticker_to_alpaca(ticker: str) -> str:
    """Translates yfinance symbols to Alpaca symbols (e.g. BTC-USD -> BTCUSD)."""
    if ticker in CRYPTO:
        return ticker.replace("-", "")
    return ticker

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    print("=" * 80)
    print(f"LIVE EXECUTION: ALTERNATIVE ASSETS STRATEGY ({today_str})")
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
        print(f"Alpaca connection failed or credentials missing: {e}. Live assets will run in mock mode.")
        alpaca_client = None
        account_equity = 100000.0
        account_cash = 100000.0

    # 2. Load portfolio tracking state
    portfolio = load_portfolio(dir_path)
    portfolio["total_capital"] = account_equity
    current_cash = portfolio["cash_balance"]

    # 3. Detect monthly savings inflow
    last_updated_str = portfolio.get("last_updated", "2000-01-01")
    if " " in last_updated_str:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S").date()
    else:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d").date()

    today = datetime.date.today()
    is_new_month = today.year > last_dt.year or (today.year == last_dt.year and today.month > last_dt.month)

    if is_new_month:
        portfolio["cash_balance"] += MONTHLY_CONTRIBUTION
        current_cash += MONTHLY_CONTRIBUTION
        portfolio["total_capital"] += MONTHLY_CONTRIBUTION
        print(f"[Savings Ingestion] New calendar month transition. Injected ${MONTHLY_CONTRIBUTION:,.2f} USD.")
        log_transaction(dir_path, today_str, "CASH", "DEPOSIT", 1, MONTHLY_CONTRIBUTION, "Monthly savings contribution", fee=0.0)

    # 4. Fetch dynamic data from yfinance
    print("\nFetching indicators and recent close prices...")
    ticker_history = {}
    current_prices = {}
    
    try:
        data = yf.download(ALL_TICKERS, period="1y", interval="1d", group_by='ticker', progress=False)
    except Exception as e:
        print(f"Batch fetch failed: {e}")
        data = pd.DataFrame()

    for ticker in ALL_TICKERS:
        try:
            if not data.empty and isinstance(data.columns, pd.MultiIndex) and ticker in data.columns.levels[0]:
                hist = data[ticker].dropna(how='all')
            else:
                hist = yf.Ticker(ticker).history(period="1y", interval="1d")

            if hist.empty or len(hist) < 20:
                continue
                
            hist.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in hist.columns]
            ticker_history[ticker] = hist
            current_prices[ticker] = float(hist["close"].iloc[-1])
        except Exception as e:
            print(f"  Ticker {ticker:10} | Failed loading data: {e}")

    # Re-calculate total portfolio value
    holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}
    current_equity = sum(h["shares"] * current_prices.get(h["ticker"], h["last_price"]) for h in portfolio["holdings"])
    portfolio_value = current_cash + current_equity

    # 4.5 Evaluate signals for all tickers in the universe for report logs
    all_evaluations = {}
    for ticker in ALL_TICKERS:
        if ticker not in current_prices:
            continue
        if ticker in CRYPTO:
            asset_type = "crypto"
        elif ticker in COMMODITIES:
            asset_type = "commodity"
        else:
            asset_type = "forex"
            
        hist = ticker_history[ticker]
        sig_res = evaluate_signals(ticker, asset_type, hist)
        all_evaluations[ticker] = (asset_type, sig_res)

    # 5. Process Exits
    exit_trades = []
    for ticker, h in list(holdings_dict.items()):
        if ticker not in current_prices:
            continue
            
        price = current_prices[ticker]
        asset_type = h["asset_type"]
        exit_triggered = False
        exit_reason = ""
        
        # Update peak price for Crypto trailing stops
        if asset_type == "crypto":
            h["last_price"] = price
            if price > h.get("peak_price", h["buy_price"]):
                h["peak_price"] = price
                unrealized = (price / h["buy_price"]) - 1.0
                if unrealized >= 0.10:
                    h["armed"] = True
            
            if h.get("armed", False) and price < h.get("peak_price", price) * 0.95:
                exit_triggered = True
                exit_reason = f"Trailing Stop Triggered (Peak: ${h['peak_price']:.2f})"

        # Check standard sell signals
        if not exit_triggered:
            if ticker in all_evaluations:
                _, signal_res = all_evaluations[ticker]
                if signal_res["signal"] == "sell":
                    exit_triggered = True
                    exit_reason = signal_res["reason"]

        if exit_triggered:
            # Execute Exit
            shares_to_sell = h["shares"]
            proceeds = shares_to_sell * price
            fee = proceeds * TRANSACTION_FEE_RATE
            current_cash += (proceeds - fee)
            
            note = f"Exit: {exit_reason}"
            
            # Submit to Alpaca if not mock Forex
            if asset_type != "forex" and alpaca_client:
                alpaca_sym = translate_ticker_to_alpaca(ticker)
                try:
                    alpaca_client.submit_order(ticker=alpaca_sym, qty=int(shares_to_sell) if asset_type == "commodity" else float(shares_to_sell), side="sell")
                    note = f"Alpaca Order filled | {note}"
                except Exception as e:
                    print(f"  [Alpaca Exit FAILED] {ticker}: {e}")
                    note = f"Alpaca Failed ({e}) | {note}"
                    
            log_transaction(dir_path, today_str, ticker, "SELL", shares_to_sell, price, note, fee=fee)
            exit_trades.append(f"SOLD {shares_to_sell:.4f} shares of {ticker} | {exit_reason}")
            del holdings_dict[ticker]

    # Save intermediate cash
    portfolio["holdings"] = list(holdings_dict.values())
    portfolio["cash_balance"] = round(current_cash, 2)

    # 6. Process Entries
    entry_trades = []
    num_positions = len(portfolio["holdings"])
    
    if num_positions < MAX_CONCURRENT_POSITIONS:
        candidates = []
        for ticker in ALL_TICKERS:
            if ticker in holdings_dict or ticker not in all_evaluations:
                continue
                
            asset_type, sig_res = all_evaluations[ticker]
            if sig_res["signal"] == "buy":
                candidates.append((ticker, asset_type, sig_res))
                
        # Sort candidates
        candidates.sort(key=lambda x: 0 if x[1] == "crypto" else (1 if x[1] == "commodity" else 2))
        
        for ticker, asset_type, sig_res in candidates:
            if len(portfolio["holdings"]) >= MAX_CONCURRENT_POSITIONS:
                break
                
            # Define target weight
            if asset_type == "crypto":
                target_w = MAX_CRYPTO_WEIGHT
            elif asset_type == "commodity":
                target_w = MAX_COMMODITY_WEIGHT
            else:
                target_w = MAX_FOREX_WEIGHT
                
            close_price = sig_res["price"]
            target_value = portfolio_value * target_w
            
            if target_value > current_cash:
                target_value = current_cash * 0.98  # buffer
                
            # Sizing shares
            if asset_type == "crypto":
                # Fractional shares (4 decimals)
                shares = round(target_value / (close_price * (1.0 + TRANSACTION_FEE_RATE)), 4)
            else:
                # Integer shares
                shares = int(target_value / (close_price * (1.0 + TRANSACTION_FEE_RATE)))
                
            if shares > 0.0:
                cost = shares * close_price
                fee = cost * TRANSACTION_FEE_RATE
                total_cost = cost + fee
                
                if total_cost <= current_cash:
                    current_cash -= total_cost
                    note = f"Entry: {sig_res['reason']}"
                    
                    if asset_type != "forex" and alpaca_client:
                        alpaca_sym = translate_ticker_to_alpaca(ticker)
                        try:
                            # Submit order
                            alpaca_client.submit_order(ticker=alpaca_sym, qty=shares, side="buy")
                            note = f"Alpaca Order filled | {note}"
                        except Exception as e:
                            print(f"  [Alpaca Entry FAILED] {ticker}: {e}")
                            note = f"Alpaca Failed ({e}) | {note}"
                            
                    portfolio["holdings"].append({
                        "ticker": ticker,
                        "shares": shares,
                        "buy_price": close_price,
                        "last_price": close_price,
                        "peak_price": close_price,
                        "armed": False,
                        "target_weight": target_w,
                        "asset_type": asset_type,
                        "entry_date": today_str
                    })
                    
                    log_transaction(dir_path, today_str, ticker, "BUY", shares, close_price, note, fee=fee)
                    entry_trades.append(f"BOUGHT {shares:.4f} shares of {ticker} | {sig_res['reason']}")

    # 7. Update holdings' last prices
    holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}
    for h in portfolio["holdings"]:
        t = h["ticker"]
        if t in current_prices:
            h["last_price"] = current_prices[t]

    # Save portfolio
    portfolio["cash_balance"] = round(current_cash, 2)
    save_portfolio(dir_path, portfolio)
    update_capital_reconciliation(dir_path, portfolio)

    # 8. Generate execution report
    current_equity = sum(h["shares"] * current_prices.get(h["ticker"], h["last_price"]) for h in portfolio["holdings"])
    portfolio_value = current_cash + current_equity

    report_markdown = f"""# Isolated Alternative Assets Strategy Execution Report
**Execution Date:** {today_str} | **Strategy Version:** Alternative Assets Isolated V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} USD
* **Total Cash Balance:** ${current_cash:,.2f} USD
* **Equity Exposure:** {((portfolio_value - current_cash)/portfolio_value * 100):.1f}%
* **Active Holdings Count:** {len(portfolio["holdings"])} of {MAX_CONCURRENT_POSITIONS} positions

## 2. Current Holdings
| Ticker | Type | Shares Held | Avg Cost | Last Price | Market Value | Target Weight |
| :--- | :---: | :---: | :---: | :---: | ---: | :---: |
"""
    for h in portfolio["holdings"]:
        mkt_val = h["shares"] * h["last_price"]
        report_markdown += f"| **{h['ticker']}** | {h['asset_type'].upper()} | {h['shares']:.4f} | ${h['buy_price']:,.4f} | ${h['last_price']:,.4f} | ${mkt_val:,.2f} | {h['target_weight']*100:.1f}% |\n"

    report_markdown += "\n## 3. Today's Execution Logs\n"
    if is_new_month:
        report_markdown += f"* **[SAVINGS DEPOSIT]** Detected month transition. Credited $1,000.00 USD cash inflow.\n"
    if exit_trades:
        report_markdown += "### Completed Sales:\n"
        for trade in exit_trades:
            report_markdown += f"* {trade}\n"
    if entry_trades:
        report_markdown += "### Completed Purchases:\n"
        for trade in entry_trades:
            report_markdown += f"* {trade}\n"
    if not exit_trades and not entry_trades and not is_new_month:
        report_markdown += "* No actions required today. Positions match target indicator profiles.\n"

    # 4. Evaluation Diagnostics Section
    report_markdown += "\n## 4. Asset Evaluation Diagnostics (Signals Checked)\n"
    report_markdown += "| Ticker | Asset Type | Signal | Price | Indicator Diagnostics | Evaluation Reason |\n"
    report_markdown += "| :--- | :---: | :---: | :---: | :--- | :--- |\n"
    
    for ticker in ALL_TICKERS:
        if ticker not in all_evaluations:
            report_markdown += f"| **{ticker}** | - | N/A | - | Data download failed | - |\n"
            continue
            
        asset_type, sig_res = all_evaluations[ticker]
        price = sig_res.get("price", current_prices.get(ticker, 0.0))
        sig_str = sig_res.get("signal", "hold").upper()
        reason_str = sig_res.get("reason", "No signals")
        
        ind = sig_res.get("indicators", {})
        if asset_type == "crypto":
            diag_str = f"SMA 200: ${ind.get('sma_200', 0.0):,.2f}, MACD: {ind.get('macd', 0.0):.4f}, Signal: {ind.get('signal', 0.0):.4f}"
        elif asset_type == "commodity":
            diag_str = f"SMA 100: ${ind.get('sma_100', 0.0):,.2f}, Donchian High: ${ind.get('donchian_high', 0.0):,.2f}, Donchian Low: ${ind.get('donchian_low', 0.0):,.2f}"
        else:
            diag_str = f"RSI: {ind.get('rsi', 0.0):.1f}, Lower BB: ${ind.get('lower_bb', 0.0):,.4f}, Upper BB: ${ind.get('upper_bb', 0.0):,.4f}"
            
        report_markdown += f"| **{ticker}** | {asset_type.upper()} | {sig_str} | ${price:,.4f} | {diag_str} | {reason_str} |\n"

    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report_markdown)

    print("\nAlternative Assets portfolio execution completed!")
    print("=" * 80)

if __name__ == "__main__":
    main()
