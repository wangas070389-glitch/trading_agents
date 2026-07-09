import os
import json
import math
import datetime
import yfinance as yf

def is_valid_price(p):
    """True if p is a usable price (finite float > 0). Guards against NaN
    closes returned by yfinance when the market is closed or data is missing."""
    try:
        return p is not None and math.isfinite(float(p)) and float(p) > 0.0
    except (TypeError, ValueError):
        return False

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
    elif action == "INTEREST":
        cash_flow_str = f"+{cash_flow:,.4f}"
    else:
        cash_flow_str = f"+{cash_flow:,.2f}"

    row = f"| {date_str} | {ticker} | {action} | {shares} | {price:.4f} | {cash_flow_str} | Market | FILLED | {note} |"

    if os.path.exists(transactions_path):
        with open(transactions_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# Transaction Ledger\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"

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

def update_capital_reconciliation(transactions_path, portfolio):
    """Update the capital reconciliation section at the bottom of transactions.md."""
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
        f"* **Initial Starting Capital (2026-06-03)**: {total_capital:,.2f} MXN",
        f"* **Total Deployed Capital**: {invested:,.2f} MXN ({invested/total_value*100:.1f}% invested)",
        f"* **Unallocated Cash Reserves**: {cash:,.2f} MXN ({cash/total_value*100:.1f}% cash)",
        f"* **Current Portfolio Market Value**: {total_value:,.2f} MXN (including cash)",
        ""
    ]

    if recon_start is not None:
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
    print("PORTFOLIO MONITORING ENGINE | ACCRUING BONDIA INTEREST & FETCHING LIVE PRICES")
    print("=" * 80)

    # 1. Accrue Bondia Yield (11% APR, 360-day convention)
    last_updated_str = portfolio.get("last_updated")
    accrued_interest = 0.0
    days_elapsed = 0.0
    
    if last_updated_str:
        try:
            last_updated = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            time_diff = now - last_updated
            days_elapsed = time_diff.total_seconds() / 86400.0
            
            if days_elapsed > 0.001 and cash > 0:
                daily_rate = 0.0653 / 360.0
                accrued_interest = cash * daily_rate * days_elapsed
                cash = round(cash + accrued_interest, 2)
                portfolio["cash_balance"] = cash
                
                # Log interest credit to transactions ledger
                note = f"Bondia overnight yield on cash reserves for {days_elapsed:.4f} days."
                log_transaction(transactions_path, today_str, "BONDIA", "INTEREST", 1, accrued_interest, note)
                print(f"  +-- [INTEREST ACCRUED] Cash Reserves: +{accrued_interest:,.4f} MXN for {days_elapsed:.4f} days elapsed.")
        except Exception as e:
            print(f"  |-- [WARNING] Failed to accrue Bondia interest: {e}")

    # 2. Fetch live prices for stock holdings
    # Fetch current USD/MXN rate once in case we have U.S. holdings
    try:
        fx = yf.Ticker("MXN=X").history(period="1d")
        if not fx.empty:
            current_usd_mxn = float(fx["Close"].iloc[-1])
        else:
            current_usd_mxn = float(yf.Ticker("MXN=X").info.get("regularMarketPrice", 20.0))
    except Exception:
        current_usd_mxn = 20.0
        
    updated_holdings = []
    total_market_value = 0.0

    report_lines = []
    report_lines.append("# PORTFOLIO PERFORMANCE MONITOR")
    report_lines.append(f"**Status Check Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append("## 1. Current Holdings Value")
    report_lines.append("| Ticker | Shares Held | Buy Price (MXN) | Current Price (MXN) | Market Value (MXN) | Unrealized P/L | P/L % | DCS | HMM State | Target Weight |")
    report_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for h in holdings:
        ticker = h["ticker"]
        shares = h["shares"]
        buy_price = h["buy_price"]
        target_weight = h.get("target_weight", 0.0)
        dcs = h.get("dcs", 0.0)
        hmm_state = h.get("hmm_state", 0)

        # Fetch current price from yfinance (fresh_price is in the asset's
        # native currency; the cached last_price is already in MXN)
        fresh_price = None
        try:
            t_obj = yf.Ticker(ticker)
            hist = t_obj.history(period="1d")
            if not hist.empty:
                fresh_price = hist["Close"].iloc[-1]
            else:
                fresh_price = t_obj.info.get("currentPrice")
        except Exception as e:
            print(f"Warning: Failed to fetch live price for {ticker}: {e}. Using last cached price.")

        if is_valid_price(fresh_price):
            current_price = float(fresh_price)
            # Convert to MXN if it is a U.S. stock (doesn't end in .MX)
            if not ticker.endswith(".MX"):
                current_price = current_price * current_usd_mxn
        else:
            print(f"Warning: No valid price for {ticker} (market closed or empty feed). Keeping last cached price.")
            current_price = h["last_price"]

        current_price = round(current_price, 2)
        market_value = shares * current_price
        total_market_value += market_value

        pl_mxn = market_value - (shares * buy_price)
        pl_pct = ((current_price / buy_price) - 1.0) * 100.0 if buy_price > 0 else 0.0

        pl_sign = "+" if pl_mxn >= 0 else ""
        pl_style = f"**{pl_sign}{pl_mxn:,.2f}**"
        pl_pct_style = f"**{pl_sign}{pl_pct:.2f}%**"
        
        state_str = "Bull" if hmm_state == 1 else ("Bear" if hmm_state == -1 else "Sideways")

        report_lines.append(f"| {ticker} | {shares:,} | {buy_price:.2f} | {current_price:.2f} | {market_value:,.2f} | {pl_style} | {pl_pct_style} | {dcs:.4f} | {state_str} | {target_weight:.1%} |")

        h_updated = h.copy()
        h_updated["last_price"] = current_price
        updated_holdings.append(h_updated)

    # 3. Calculate portfolio aggregates
    total_market_value = sum(h["shares"] * h["last_price"] for h in updated_holdings)
    total_value = total_market_value + cash
    original_capital = portfolio["total_capital"]
    total_pl_mxn = total_value - original_capital
    total_pl_pct = (total_value / original_capital - 1.0) * 100.0

    pl_sign = "+" if total_pl_mxn >= 0 else ""

    report_lines.append(f"\n* **Current Market Value of Shares**: {total_market_value:,.2f} MXN ({total_market_value/total_value*100:.1f}% allocation)")
    report_lines.append(f"* **Bondia Cash Routing Reserves (6.53% APR)**: {cash:,.2f} MXN ({cash/total_value*100:.1f}% cash reserve)")
    report_lines.append(f"* **Total Portfolio Value**: **{total_value:,.2f} MXN**")
    report_lines.append(f"* **Total Unrealized Profit/Loss**: **{pl_sign}{total_pl_mxn:,.2f} MXN ({pl_sign}{total_pl_pct:.2f}%)**")

    # Add Cash management detail
    report_lines.append("\n## 2. Active Cash Routing & Yield Generation")
    if accrued_interest > 0.0:
        report_lines.append(f"* Overnight interest accrued in this step: **+{accrued_interest:,.4f} MXN** (for {days_elapsed:.4f} days elapsed)")
    else:
        report_lines.append(f"* No overnight interest accrued in this check (last checked {days_elapsed*24.0*60.0:.1f} minutes ago)")
    report_lines.append(f"* Expected daily interest accrual at 6.53% APR: **+{cash * (0.0653 / 360):,.4f} MXN**")

    # Save back to portfolio.json
    portfolio["holdings"] = updated_holdings
    portfolio["cash_balance"] = round(cash, 2)
    portfolio["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_portfolio(portfolio_path, portfolio)
    update_capital_reconciliation(transactions_path, portfolio)

    # Save markdown report
    with open(status_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\n[Monitor] Performance log written to: {status_path}")
    print(f"[Monitor] Cached prices and interest updated in: {portfolio_path}")

    # Display the table on stdout
    print("\n--- PORTFOLIO V3 MONITORING SUMMARY ---")
    print(f"Total Portfolio Value: {total_value:,.2f} MXN (Cash in Bondia: {cash:,.2f} MXN, Stocks: {total_market_value:,.2f} MXN)")
    print(f"Total Unrealized P/L: {pl_sign}{total_pl_mxn:,.2f} MXN ({pl_sign}{total_pl_pct:.2f}%)")
    print("=" * 80)

if __name__ == "__main__":
    monitor_portfolio()
