import os
import json
import datetime
import yfinance as yf

def load_portfolio(portfolio_path):
    """Load portfolio.json and return the dict."""
    with open(portfolio_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_portfolio(portfolio_path, portfolio):
    """Save portfolio dict back to portfolio.json."""
    with open(portfolio_path, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(transactions_path, date_str, ticker, action, shares, price, note):
    """Append a transaction row to transactions.md."""
    cash_flow = shares * price
    if action == "BUY":
        cash_flow_str = f"-{cash_flow:,.2f}"
    else:
        cash_flow_str = f"+{cash_flow:,.2f}"

    row = f"| {date_str} | {ticker} | {action} | {shares} | {price:.2f} | {cash_flow_str} | Market | FILLED | {note} |"

    with open(transactions_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the last transaction row (before the --- separator)
    lines = content.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            insert_idx = i
            break

    if insert_idx is not None:
        lines.insert(insert_idx, row)
    else:
        # Fallback: append before the end
        lines.append(row)

    with open(transactions_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def update_capital_reconciliation(transactions_path, portfolio):
    """Update the capital reconciliation section at the bottom of transactions.md."""
    with open(transactions_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")

    # Find the reconciliation section and replace it
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
        f"* **Initial Starting Capital (2026-06-03)**: {total_capital:,.2f} MXN",
        f"* **Total Deployed Capital**: -{invested:,.2f} MXN ({invested/total_capital*100:.1f}% invested)",
        f"* **Unallocated Cash Reserves**: {cash:,.2f} MXN ({cash/total_capital*100:.1f}% cash)",
        f"* **Current Portfolio Market Value**: {total_value:,.2f} MXN (including cash)",
        ""
    ]

    if recon_start is not None:
        # Replace from recon_start to end of file
        lines = lines[:recon_start] + recon_lines
    else:
        lines.extend(["", "---", ""] + recon_lines)

    with open(transactions_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def monitor_portfolio():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    portfolio_path = os.path.join(dir_path, "portfolio.json")
    status_path = os.path.join(dir_path, "portfolio_status.md")
    transactions_path = os.path.join(dir_path, "transactions.md")
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    if not os.path.exists(portfolio_path):
        print(f"Error: portfolio.json not found at {portfolio_path}")
        return

    portfolio = load_portfolio(portfolio_path)

    cash = portfolio["cash_balance"]
    holdings = portfolio["holdings"]

    print("=" * 80)
    print("PORTFOLIO MONITORING ENGINE | RETRIEVING LIVE PRICES")
    print("=" * 80)

    updated_holdings = []
    removed_holdings = []
    total_market_value = 0.0

    report_lines = []
    report_lines.append("# PORTFOLIO PERFORMANCE MONITOR")
    report_lines.append(f"**Status Check Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append("## 1. Current Holdings Value")
    report_lines.append("| Ticker | Shares Held | Buy Price (MXN) | Current Price (MXN) | Market Value (MXN) | Unrealized P/L | P/L % |")
    report_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    alert_lines = []
    trade_actions = []  # Track auto-executed trades

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

        # ===== AUTO-EXECUTE SELL TRIGGERS =====
        if current_price >= target_exit:
            # TAKE PROFIT: Sell 100% of position
            sell_value = shares * current_price
            cash += sell_value

            alert = f"🚨 **[AUTO-SELL: TAKE PROFIT]** {ticker} hit target exit {target_exit:.2f} MXN (Current: {current_price:.2f} MXN). Sold ALL {shares} shares for {sell_value:,.2f} MXN."
            alert_lines.append(alert)
            trade_actions.append(("SELL", ticker, shares, current_price, f"Take-profit exit. Target: {target_exit:.2f}, Actual: {current_price:.2f}"))
            removed_holdings.append(h)
            print(alert)
            # Don't add to updated_holdings (position closed)
            continue

        elif current_price >= scale_out:
            # SCALE-OUT: Sell 50% of position
            sell_shares = shares // 2
            if sell_shares > 0:
                keep_shares = shares - sell_shares
                sell_value = sell_shares * current_price
                cash += sell_value

                alert = f"⚠️ **[AUTO-SELL: SCALE OUT]** {ticker} hit 90% target {scale_out:.2f} MXN (Current: {current_price:.2f} MXN). Sold {sell_shares} of {shares} shares for {sell_value:,.2f} MXN. Keeping {keep_shares} shares."
                alert_lines.append(alert)
                trade_actions.append(("SELL", ticker, sell_shares, current_price, f"Scale-out 50%. Target: {scale_out:.2f}, Actual: {current_price:.2f}"))
                print(alert)

                # Update holding with remaining shares
                h_updated = h.copy()
                h_updated["shares"] = keep_shares
                h_updated["last_price"] = current_price
                updated_holdings.append(h_updated)
                continue

        # ===== STOP-LOSS CHECK =====
        # If intrinsic value drops below buy price, the thesis is broken
        # (This would be triggered if a future re-evaluation updates intrinsic_value)

        h_updated = h.copy()
        h_updated["last_price"] = current_price
        updated_holdings.append(h_updated)

    # Recalculate totals after trades
    total_market_value = sum(h["shares"] * h["last_price"] for h in updated_holdings)
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
        report_lines.append("\n## 2. Active Trading Triggers & Executed Trades")
        for alert in alert_lines:
            report_lines.append(alert)
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
    portfolio["cash_balance"] = round(cash, 2)
    save_portfolio(portfolio_path, portfolio)

    # Log any executed trades to transactions.md
    if trade_actions and os.path.exists(transactions_path):
        for action, ticker, shares, price, note in trade_actions:
            log_transaction(transactions_path, today_str, ticker, action, shares, price, note)
        update_capital_reconciliation(transactions_path, portfolio)

    # Save markdown report
    with open(status_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\n[Monitor] Dashboard successfully written to: {status_path}")
    print(f"[Monitor] Cached prices updated in: {portfolio_path}")
    if trade_actions:
        print(f"[Monitor] {len(trade_actions)} trade(s) auto-executed and logged to transactions.md")

    # Display the table on stdout
    print("\n--- PORTFOLIO SUMMARY ---")
    print(f"Total Portfolio Value: {total_value:,.2f} MXN (Cash: {cash:,.2f} MXN, Shares: {total_market_value:,.2f} MXN)")
    print(f"Total Unrealized P/L: {pl_sign}{total_pl_mxn:,.2f} MXN ({pl_sign}{total_pl_pct:.2f}%)")
    print("=" * 80)

if __name__ == "__main__":
    monitor_portfolio()
