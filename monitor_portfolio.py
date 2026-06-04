import os
import json
import datetime
import yfinance as yf

def monitor_portfolio():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    portfolio_path = os.path.join(dir_path, "portfolio.json")
    status_path = os.path.join(dir_path, "portfolio_status.md")
    
    if not os.path.exists(portfolio_path):
        print(f"Error: portfolio.json not found at {portfolio_path}")
        return
        
    with open(portfolio_path, "r", encoding="utf-8") as f:
        portfolio = json.load(f)
        
    cash = portfolio["cash_balance"]
    holdings = portfolio["holdings"]
    
    print("=" * 80)
    print("PORTFOLIO MONITORING ENGINE | RETRIEVING LIVE PRICES")
    print("=" * 80)
    
    updated_holdings = []
    total_market_value = 0.0
    
    report_lines = []
    report_lines.append("# PORTFOLIO PERFORMANCE MONITOR")
    report_lines.append(f"**Status Check Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append("## 1. Current Holdings Value")
    report_lines.append("| Ticker | Shares Held | Buy Price (MXN) | Current Price (MXN) | Market Value (MXN) | Unrealized P/L | P/L % |")
    report_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    alert_lines = []
    
    for h in holdings:
        ticker = h["ticker"]
        shares = h["shares"]
        buy_price = h["buy_price"]
        target_exit = h["intrinsic_value"]
        scale_out = h["scale_out_price"]
        
        # Fetch current price from yfinance
        try:
            t_obj = yf.Ticker(ticker)
            hist = t_obj.history(period="1d")
            if not hist.empty:
                current_price = hist["Close"].iloc[-1]
            else:
                info = t_obj.info
                current_price = info.get("currentPrice", h["last_price"])
        except Exception as e:
            print(f"Warning: Failed to fetch live price for {ticker}: {e}. Using last cached price.")
            current_price = h["last_price"]
            
        current_price = round(current_price, 2)
        market_value = shares * current_price
        total_market_value += market_value
        
        pl_mxn = market_value - (shares * buy_price)
        pl_pct = ((current_price / buy_price) - 1.0) * 100.0 if buy_price > 0 else 0.0
        
        pl_sign = "+" if pl_mxn >= 0 else ""
        pl_style = f"**{pl_sign}{pl_mxn:,.2f}**"
        pl_pct_style = f"**{pl_sign}{pl_pct:.2f}%**"
        
        report_lines.append(f"| {ticker} | {shares:,} | {buy_price:.2f} | {current_price:.2f} | {market_value:,.2f} | {pl_style} | {pl_pct_style} |")
        
        # Check sell triggers
        if current_price >= target_exit:
            alert = f"🚨 **[SELL TRIGGER: TAKE PROFIT]** {ticker} has hit or exceeded the target exit price of {target_exit:.2f} MXN (Current: {current_price:.2f} MXN). Capitalize 100% of the position!"
            alert_lines.append(alert)
        elif current_price >= scale_out:
            alert = f"⚠️ **[SELL TRIGGER: SCALE OUT]** {ticker} has reached the 90% target scale-out price of {scale_out:.2f} MXN (Current: {current_price:.2f} MXN). Sell 50% to lock in profit!"
            alert_lines.append(alert)
            
        h_updated = h.copy()
        h_updated["last_price"] = current_price
        updated_holdings.append(h_updated)
        
    total_value = total_market_value + cash
    original_capital = portfolio["total_capital"]
    total_pl_mxn = total_value - original_capital
    total_pl_pct = (total_value / original_capital - 1.0) * 100.0
    
    pl_sign = "+" if total_pl_mxn >= 0 else ""
    
    report_lines.append(f"\n* **Current Market Value of Shares**: {total_market_value:,.2f} MXN ({total_market_value/total_value*100:.1f}% allocation)")
    report_lines.append(f"* **Cash Balance**: {cash:,.2f} MXN ({cash/total_value*100:.1f}% cash reserve)")
    report_lines.append(f"* **Total Portfolio Value**: **{total_value:,.2f} MXN**")
    report_lines.append(f"* **Total Unrealized Profit/Loss**: **{pl_sign}{total_pl_mxn:,.2f} MXN ({pl_sign}{total_pl_pct:.2f}%)**")
    
    if alert_lines:
        report_lines.append("\n## 2. Active Trading Triggers")
        for alert in alert_lines:
            report_lines.append(alert)
            print(alert)
    else:
        report_lines.append("\n## 2. Active Trading Triggers")
        report_lines.append("* No trade triggers hit. All holdings are moving within target boundaries.")
        print("Status: No sell triggers hit. Positions are moving as intended.")
        
    # Add rebalancing rules
    report_lines.append("\n## 3. Position Sizing & Rebalancing Bounds")
    report_lines.append(f"* **Total Invested Ratio**: {total_market_value/original_capital*100:.1f}% (Initial target was at least 30%, currently at {total_market_value/original_capital*100:.1f}%)")
    report_lines.append("* **Cash Cover**: Liquid cash buffer protects portfolio volatility.")
    
    # Save back to portfolio.json
    portfolio["holdings"] = updated_holdings
    with open(portfolio_path, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)
        
    # Save markdown report
    with open(status_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"\n[Monitor] Dashboard successfully written to: {status_path}")
    print(f"[Monitor] Cached prices updated in: {portfolio_path}")
    
    # Display the table on stdout
    print("\n--- PORTFOLIO SUMMARY ---")
    print(f"Total Portfolio Value: {total_value:,.2f} MXN (Cash: {cash:,.2f} MXN, Shares: {total_market_value:,.2f} MXN)")
    print(f"Total Unrealized P/L: {pl_sign}{total_pl_mxn:,.2f} MXN ({pl_sign}{total_pl_pct:.2f}%)")
    print("=" * 80)

if __name__ == "__main__":
    monitor_portfolio()
