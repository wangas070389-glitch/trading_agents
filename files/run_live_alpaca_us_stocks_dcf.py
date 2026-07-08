import os
import sys
import json
import argparse
import datetime
import yfinance as yf
import numpy as np
import pandas as pd

# local import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from connectors.alpaca_connector import AlpacaConnector
from skills.us_dcf_valuation import calculate_us_dcs
from backtest_us_stocks_dcf import solve_weights

# Strategy Constants
US_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX", "AMD", "JPM"]
PORTFOLIO_FILE = "portfolio_us_dcs.json"
TRANSACTIONS_FILE = "transactions_us_dcs.md"
REPORT_FILE = "us_stocks_dcf_report_live.md"

TRANSACTION_FEE_RATE = 0.0029
DCS_ENTRY_THRESHOLD = 0.15
CONCENTRATION_CAP = 0.25
MAX_CONCURRENT_POSITIONS = 5
MONTHLY_CONTRIBUTION = 1000.0  # USD

def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if not os.path.exists(p_path):
        return {
            "total_capital": 100000.0,
            "cash_balance": 100000.0,
            "holdings": [],
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_rebalance_date": "2000-01-01"
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
            f.write("# Transaction Log (US Stock DCS Strategy)\n\n| Date | Ticker | Action | Shares | Price | Fee | Net Amount | Note |\n| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |\n---\n")
            
    net_amount = shares * price
    if action in ["BUY", "DCA_BUY", "DEPOSIT"]:
        net_amount = -(net_amount + fee)
    else:
        net_amount = net_amount - fee
        
    lines = []
    with open(t_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split("\n")
    row = f"| {date_str} | {ticker} | {action} | {shares:.2f} | ${price:.2f} | ${fee:.2f} | ${net_amount:,.2f} | {note} |"
    
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebalance", action="store_true", help="Force a quarterly rebalance run.")
    args = parser.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    from halt_gate import halted
    if halted(dir_path, "us_dcs"):
        return
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    print("=" * 80)
    print(f"LIVE EXECUTION: US STOCK DCS VALUE-GROWTH STRATEGY ({today_str})")
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

    # 4. Fetch dynamic risk-free rate & stock price indicators
    print("\nFetching Treasury Yield and universe price details...")
    try:
        tnx = yf.download("^TNX", period="5d", progress=False)
        tnx.columns = [c if isinstance(c, str) else c[0] for c in tnx.columns]
        rf_rate = float(tnx["Close"].iloc[-1]) / 100.0
    except Exception as e:
        print(f"  [WARN] Failed to fetch US 10Y Yield: {e}. Using fallback 4.5%.")
        rf_rate = 0.045
    print(f"  US 10-Year Treasury Yield (Risk-Free Rate): {rf_rate*100:.2f}%")

    # Download recent stock history
    ticker_history = {}
    current_prices = {}
    sma_20_values = {}
    sma_100_values = {}

    try:
        data = yf.download(US_UNIVERSE, period="1y", interval="1d", group_by='ticker', progress=False)
    except Exception as e:
        print(f"Batch fetch failed: {e}")
        data = pd.DataFrame()

    for ticker in US_UNIVERSE:
        try:
            if not data.empty and isinstance(data.columns, pd.MultiIndex) and ticker in data.columns.levels[0]:
                hist = data[ticker].dropna(how='all')
            else:
                hist = yf.Ticker(ticker).history(period="1y", interval="1d")

            if hist.empty or len(hist) < 100:
                continue
                
            hist.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in hist.columns]
            ticker_history[ticker] = hist
            
            closes = hist["close"].values
            current_prices[ticker] = float(closes[-1])
            
            # SMA 20
            sma_20_values[ticker] = float(hist["close"].rolling(window=20).mean().iloc[-1])
            # SMA 100
            sma_100_values[ticker] = float(hist["close"].rolling(window=100).mean().iloc[-1])
        except Exception as e:
            print(f"  Ticker {ticker:6} | Failed loading data: {e}")

    # 5. Check if rebalancing is due
    last_rebalance_str = portfolio.get("last_rebalance_date", "2000-01-01")
    last_rebalance_date = datetime.datetime.strptime(last_rebalance_str, "%Y-%m-%d").date()
    days_since_rebalance = (today - last_rebalance_date).days
    should_rebalance = args.rebalance or (days_since_rebalance >= 90)
    print(f"Days since last rebalance: {days_since_rebalance} days.")

    # Calculate DCS for all assets
    adjusted_metrics = {}
    for ticker in US_UNIVERSE:
        if ticker in current_prices:
            try:
                dcf_res = calculate_us_dcs(ticker, current_prices[ticker], rf_rate)
                adjusted_metrics[ticker] = {
                    "current_price": current_prices[ticker],
                    "dcs_adjusted": float(dcf_res["margin_of_safety"]),
                    "intrinsic_value": float(dcf_res["intrinsic_value"]),
                    "wacc": float(dcf_res["wacc"])
                }
            except Exception as e:
                print(f"  [WARN] Failed to compute DCS for {ticker}: {e}")

    # 6. Process Active DCA monthly savings allocation
    dca_trades = []
    if is_new_month and portfolio["holdings"]:
        eligible_dca = []
        for h in portfolio["holdings"]:
            ticker = h["ticker"]
            if ticker in current_prices:
                price = current_prices[ticker]
                sma_20 = sma_20_values.get(ticker, price)
                # Lookup DCS
                dcs = adjusted_metrics.get(ticker, {}).get("dcs_adjusted", h["dcs"])
                
                if price > sma_20 and dcs >= DCS_ENTRY_THRESHOLD:
                    eligible_dca.append((ticker, dcs, price))
                    
        if eligible_dca:
            eligible_dca.sort(key=lambda x: x[1], reverse=True)
            top_dca = eligible_dca[:3]
            dca_alloc = MONTHLY_CONTRIBUTION / len(top_dca)
            
            print("\n[Active DCA Inflow] Deploying monthly savings into undervalued uptrending holdings:")
            for ticker, dcs_val, price in top_dca:
                shares = int(dca_alloc // price)
                if shares > 0:
                    cost = shares * price
                    fee = cost * TRANSACTION_FEE_RATE
                    total_cost = cost + fee
                    
                    if total_cost <= current_cash:
                        current_cash -= total_cost
                        
                        # Submit trade
                        if alpaca_client:
                            res = alpaca_client.submit_and_confirm(ticker=ticker, qty=shares, side="buy")
                            if not res["filled"]:
                                print(f"  [Alpaca BUY NOT FILLED] {ticker}: {res['status']}. Ledger NO modificado.")
                                current_cash += total_cost
                                log_transaction(dir_path, today_str, ticker, "BUY-REJECTED", shares, price, f"Alpaca {res['status']}", fee=0.0)
                                continue
                                
                        # Update local state
                        for h in portfolio["holdings"]:
                            if h["ticker"] == ticker:
                                old_cost = h["shares"] * h["buy_price"]
                                h["shares"] += shares
                                h["buy_price"] = round((old_cost + cost) / h["shares"], 2)
                                h["last_price"] = price
                                break
                                
                        log_transaction(dir_path, today_str, ticker, "DCA_BUY", shares, price, f"Active DCA (DCS={dcs_val:.3f})", fee=fee)
                        dca_trades.append(f"DCA BUY {shares} shares of {ticker} at ${price:.2f}")

    # 7. Execute quarterly rebalancing
    rebalance_trades = []
    if should_rebalance:
        print("\n[Quarterly Rebalance] Running portfolio rebalancing...")
        candidates = []
        for t, m in adjusted_metrics.items():
            dcs = m["dcs_adjusted"]
            price = current_prices[t]
            sma_100 = sma_100_values.get(t, price)
            
            if dcs >= DCS_ENTRY_THRESHOLD and price > sma_100:
                candidates.append((t, dcs))
                
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:MAX_CONCURRENT_POSITIONS]
        
        target_dcs = {t: dcs for t, dcs in top_candidates}
        target_weights = solve_weights(target_dcs, max_weight=CONCENTRATION_CAP)
        
        full_target_weights = {t: 0.0 for t in US_UNIVERSE}
        for t, w in target_weights.items():
            full_target_weights[t] = w
            
        # Re-calculate total portfolio value
        holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}
        current_equity = sum(h["shares"] * current_prices.get(h["ticker"], h["last_price"]) for h in portfolio["holdings"])
        portfolio_value = current_cash + current_equity
        
        # Sells first to raise cash
        for h in list(portfolio["holdings"]):
            ticker = h["ticker"]
            target_w = full_target_weights.get(ticker, 0.0)
            close_price = current_prices[ticker]
            curr_val = h["shares"] * close_price
            target_val = portfolio_value * target_w
            
            if target_w == 0.0:
                # Liquidate
                shares_to_sell = h["shares"]
                sell_val = shares_to_sell * close_price
                fee = sell_val * TRANSACTION_FEE_RATE
                current_cash += (sell_val - fee)
                
                if alpaca_client:
                    res = alpaca_client.submit_and_confirm(ticker=ticker, qty=int(shares_to_sell), side="sell")
                    if not res["filled"]:
                        print(f"  [Alpaca SELL NOT FILLED] {ticker}: {res['status']}. Ledger NO modificado.")
                        current_cash -= (sell_val - fee)
                        log_transaction(dir_path, today_str, ticker, "SELL-REJECTED", shares_to_sell, close_price, f"Alpaca {res['status']}", fee=0.0)
                        continue
                        
                log_transaction(dir_path, today_str, ticker, "SELL", shares_to_sell, close_price, "Quarterly exit (DCS suppressed)", fee=fee)
                rebalance_trades.append(f"SOLD {shares_to_sell:.2f} shares of {ticker} (Exit)")
                h["shares"] = 0
            elif (curr_val - target_val) > (portfolio_value * 0.05):
                # Sell down
                shares_to_sell = int((curr_val - target_val) / close_price)
                if shares_to_sell > 0:
                    sell_val = shares_to_sell * close_price
                    fee = sell_val * TRANSACTION_FEE_RATE
                    current_cash += (sell_val - fee)
                    
                    if alpaca_client:
                        try:
                            alpaca_client.submit_order(ticker=ticker, qty=shares_to_sell, side="sell")
                        except Exception as e:
                            print(f"  [Alpaca SELL FAILED] Scale-down {ticker}: {e}")
                            
                    log_transaction(dir_path, today_str, ticker, "SELL", shares_to_sell, close_price, f"Quarterly scale-down to {target_w*100:.1f}%", fee=fee)
                    rebalance_trades.append(f"SOLD {shares_to_sell} shares of {ticker} (Scale-down)")
                    h["shares"] -= shares_to_sell

        # Remove empty positions
        portfolio["holdings"] = [h for h in portfolio["holdings"] if h["shares"] > 0]
        holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}

        # Buys second
        for t, w in target_weights.items():
            h = holdings_dict.get(t)
            curr_shares = h["shares"] if h else 0.0
            close_price = current_prices[t]
            curr_val = curr_shares * close_price
            target_val = portfolio_value * w
            
            if (target_val - curr_val) > (portfolio_value * 0.05):
                alloc = target_val - curr_val
                shares_to_buy = int(alloc / close_price)
                
                cost = shares_to_buy * close_price
                fee = cost * TRANSACTION_FEE_RATE
                total_cost = cost + fee
                
                if total_cost > current_cash:
                    shares_to_buy = int(current_cash / (close_price * (1.0 + TRANSACTION_FEE_RATE)))
                    cost = shares_to_buy * close_price
                    fee = cost * TRANSACTION_FEE_RATE
                    total_cost = cost + fee
                    
                if shares_to_buy > 0:
                    current_cash -= total_cost
                    
                    if alpaca_client:
                        try:
                            alpaca_client.submit_order(ticker=t, qty=shares_to_buy, side="buy")
                        except Exception as e:
                            print(f"  [Alpaca BUY FAILED] Buy {t}: {e}")
                            
                    if h:
                        old_cost = h["shares"] * h["buy_price"]
                        h["shares"] += shares_to_buy
                        h["buy_price"] = round((old_cost + cost) / h["shares"], 2)
                        h["last_price"] = close_price
                        h["target_weight"] = w
                        h["dcs"] = adjusted_metrics[t]["dcs_adjusted"]
                    else:
                        portfolio["holdings"].append({
                            "ticker": t,
                            "shares": shares_to_buy,
                            "buy_price": close_price,
                            "last_price": close_price,
                            "target_weight": w,
                            "dcs": adjusted_metrics[t]["dcs_adjusted"]
                        })
                    log_transaction(dir_path, today_str, t, "BUY", shares_to_buy, close_price, f"Quarterly Rebalance (Target weight {w*100:.1f}%)", fee=fee)
                    rebalance_trades.append(f"BOUGHT {shares_to_buy} shares of {t}")

        portfolio["last_rebalance_date"] = today_str

    # 8. Update positions' last prices
    for h in portfolio["holdings"]:
        t = h["ticker"]
        if t in current_prices:
            h["last_price"] = current_prices[t]
            if t in adjusted_metrics and should_rebalance:
                h["dcs"] = adjusted_metrics[t]["dcs_adjusted"]

    # 9. Save portfolio
    portfolio["cash_balance"] = round(current_cash, 2)
    save_portfolio(dir_path, portfolio)
    update_capital_reconciliation(dir_path, portfolio)

    # 10. Generate markdown report
    current_equity = sum(h["shares"] * current_prices.get(h["ticker"], h["last_price"]) for h in portfolio["holdings"])
    portfolio_value = current_cash + current_equity
    
    report_markdown = f"""# Isolated US Stock DCS Value-Growth Execution Report
**Execution Date:** {today_str} | **Strategy Version:** DCS Value-Growth Isolated V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} USD
* **Total Cash Balance:** ${current_cash:,.2f} USD
* **Equity Exposure:** {((portfolio_value - current_cash)/portfolio_value * 100):.1f}%
* **Days Since Last Rebalance:** {(today - datetime.datetime.strptime(portfolio["last_rebalance_date"], "%Y-%m-%d").date()).days} days

## 2. Current Holdings
| Ticker | Shares Held | Last Price | Market Value | Target Weight | DCS Conviction |
| :--- | :---: | :---: | ---: | :---: | :---: |
"""
    for h in portfolio["holdings"]:
        mkt_val = h["shares"] * h["last_price"]
        report_markdown += f"| **{h['ticker']}** | {h['shares']:.2f} | ${h['last_price']:.2f} | ${mkt_val:,.2f} | {h['target_weight']*100:.1f}% | {h['dcs']:.3f} |\n"

    report_markdown += "\n## 3. Today's Execution Logs\n"
    if is_new_month:
        report_markdown += f"* **[SAVINGS DEPOSIT]** Detected month transition. Credited $1,000.00 USD cash inflow.\n"
    if dca_trades:
        report_markdown += "### Active DCA Allocations:\n"
        for trade in dca_trades:
            report_markdown += f"* {trade}\n"
    if should_rebalance:
        report_markdown += "### Quarterly Rebalancing Executed:\n"
        for trade in rebalance_trades:
            report_markdown += f"* {trade}\n"
    if not dca_trades and not rebalance_trades and not is_new_month:
        report_markdown += "* No actions required today. Portfolio matches target weights.\n"

    # 4. Diagnostics Table
    report_markdown += "\n## 4. Asset Evaluation Diagnostics (Signals Checked)\n"
    report_markdown += "| Ticker | Signal | Price | DCS Conviction | Intrinsic Value | SMA 100 Trend | SMA 20 Trend (DCA) | Evaluation Reason |\n"
    report_markdown += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |\n"
    
    for t in sorted(US_UNIVERSE):
        price = current_prices.get(t, 0.0)
        sma20 = sma_20_values.get(t, 0.0)
        sma100 = sma_100_values.get(t, 0.0)
        
        dcs = 0.0
        intrinsic = 0.0
        if t in adjusted_metrics:
            dcs = adjusted_metrics[t]["dcs_adjusted"]
            intrinsic = adjusted_metrics[t]["intrinsic_value"]
        else:
            for h in portfolio["holdings"]:
                if h["ticker"] == t:
                    dcs = h["dcs"]
                    
        sma100_status = "BULL" if price > sma100 else "BEAR"
        sma20_status = "BULL" if price > sma20 else "BEAR"
        
        is_held = any(h["ticker"] == t for h in portfolio["holdings"])
        
        if dcs >= DCS_ENTRY_THRESHOLD and price > sma100:
            sig = "BUY / HOLD"
            reason = f"Strong conviction (DCS={dcs:.3f}) and bull trend (Close > SMA 100)"
        else:
            sig = "SELL / AVOID"
            reasons = []
            if dcs < DCS_ENTRY_THRESHOLD:
                reasons.append(f"Low conviction (DCS={dcs:.3f} < {DCS_ENTRY_THRESHOLD})")
            if price <= sma100:
                reasons.append(f"Bear trend (Close <= SMA 100)")
            reason = " and ".join(reasons)
            
        if is_held and sig == "BUY / HOLD":
            if price > sma20:
                reason += " | Eligible for active DCA"
            else:
                reason += f" | DCA restricted (Close <= SMA 20)"
                
        report_markdown += f"| **{t}** | {sig} | ${price:,.2f} | {dcs:.3f} | ${intrinsic:,.2f} | {sma100_status} | {sma20_status} | {reason} |\n"

    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report_markdown)

    print("\nUS Stocks DCS portfolio execution completed!")
    print("=" * 80)

if __name__ == "__main__":
    main()
