import os
import sys
import json
import argparse
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# Local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from skills.fibra_screener import evaluate_and_rank_fibras, get_fibra_metrics, FIBRA_TICKERS

PORTFOLIO_FILE = "portfolio_strategy17.json"
TRANSACTIONS_FILE = "transactions_strategy17.md"
REPORT_FILE = "strategy17_report_live.md"
TRANSACTION_COST = 0.0029  # 0.29% GBM broker fee
MIN_YIELD = 0.04
MAX_STOCK_WEIGHT = 0.25
MAX_CONCURRENT_POSITIONS = 4

def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if os.path.exists(p_path):
        with open(p_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Default initialization with 100K MXN
        return {
            "total_capital": 100000.0,
            "cash_balance": 100000.0,
            "holdings": [],
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_rebalance_date": "2000-01-01"
        }

def save_portfolio(dir_path, portfolio):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    with open(p_path, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    gross = shares * price
    if action == "BUY":
        cash_flow_str = f"-{gross + fee:,.2f}"
    elif action in ["INTEREST", "DIVIDEND", "CASH", "DEPOSIT"]:
        cash_flow_str = f"+{gross:,.2f}"
    else:
        cash_flow_str = f"+{gross - fee:,.2f}"
        
    row = f"| {date_str} | {ticker} | {action} | {shares:.2f} | ${price:.2f} | ${cash_flow_str} | Market | FILLED | {note} |"
    
    if os.path.exists(t_path):
        with open(t_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = f"# Strategy 17: FIBRAs Dynamic Income Transaction Ledger\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"
        
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
        
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebalance", action="store_true", help="Force a rebalancing screener run.")
    args = parser.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 17 FIBRAS DYNAMIC INCOME ({today_str})")
    print("=" * 80)

    # 1. Load portfolio state
    portfolio = load_portfolio(dir_path)
    current_cash = portfolio["cash_balance"]
    last_updated_str = portfolio.get("last_updated", today_str + " 00:00:00")
    
    if " " in last_updated_str:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
    else:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d")
        
    is_new_month = now.year > last_dt.year or (now.year == last_dt.year and now.month > last_dt.month)
    
    # 2. Check for monthly savings contribution (similar to S8 but 1000 MXN due to lower cap)
    if is_new_month:
        inflow = 1000.0
        portfolio["cash_balance"] += inflow
        current_cash += inflow
        portfolio["total_capital"] = portfolio.get("total_capital", 100000.0) + inflow
        log_transaction(dir_path, today_str, "CASH", "DEPOSIT", 1, inflow, "Monthly savings contribution", fee=0.0)
        print(f"  +-- [SAVINGS INFLOW] Deposited ${inflow:,.2f} MXN monthly savings.")

    # 3. Accrue Bondia interest on cash reserve
    time_diff = now - last_dt
    days_elapsed = time_diff.total_seconds() / 86400.0
    accrued_interest = 0.0
    if days_elapsed > 0.001 and current_cash > 0:
        daily_rate = 0.0653 / 360.0
        accrued_interest = current_cash * daily_rate * days_elapsed
        current_cash = round(current_cash + accrued_interest, 2)
        portfolio["cash_balance"] = current_cash
        log_transaction(dir_path, today_str, "BONDIA", "INTEREST", 1, accrued_interest, f"Yield on cash for {days_elapsed:.4f} days.")
        print(f"  +-- [BONDIA YIELD] Earned +${accrued_interest:,.4f} MXN interest over {days_elapsed:.4f} days.")

    # 4. Fetch current prices & process dividend payouts since last_dt
    print("Downloading current FIBRA prices & checking ex-dividend dates...")
    current_prices = {}
    dividend_credits = []
    
    for h in portfolio["holdings"]:
        ticker_symbol = h["ticker"]
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")
            if not hist.empty and hist["Close"].notna().any():
                current_price = float(hist["Close"].dropna().squeeze().iloc[-1]) if hasattr(hist["Close"], "iloc") else float(hist["Close"].dropna().squeeze())
                if np.isfinite(current_price) and current_price > 0:
                    current_prices[ticker_symbol] = current_price
                else:
                    print(f"  [WARN] No valid close for {ticker_symbol}. Keeping cached price.")
                
                # Check for dividends paid
                divs = ticker.dividends
                if not divs.empty:
                    if divs.index.tz is not None:
                        divs.index = divs.index.tz_convert("UTC").tz_localize(None)
                    recent_divs = divs[(divs.index.date > last_dt.date()) & (divs.index.date <= now.date())]
                    for pay_date, amt in recent_divs.items():
                        payout = h["shares"] * amt
                        current_cash = round(current_cash + payout, 2)
                        portfolio["cash_balance"] = current_cash
                        log_transaction(dir_path, today_str, ticker_symbol, "DIVIDEND", h["shares"], amt, f"Reinvested distribution paid on {pay_date.strftime('%Y-%m-%d')}")
                        dividend_credits.append(f"  |-- Distribution from {ticker_symbol}: +${payout:,.2f} MXN")
                        print(dividend_credits[-1])
        except Exception as e:
            print(f"  [WARN] Failed to check status for {ticker_symbol}: {e}")
            if np.isfinite(h.get("last_price", float("nan"))) and h.get("last_price", 0) > 0:
                current_prices[ticker_symbol] = h["last_price"]

    # 5. Check if rebalancing is due (quarterly = 90 days)
    last_rebalance_str = portfolio.get("last_rebalance_date", "2000-01-01")
    last_rebalance_date = datetime.datetime.strptime(last_rebalance_str, "%Y-%m-%d").date()
    days_since_rebalance = (now.date() - last_rebalance_date).days
    
    should_rebalance = args.rebalance or (days_since_rebalance >= 90)
    print(f"Days since last rebalance: {days_since_rebalance} days.")

    rebalance_trades = []
    
    if should_rebalance:
        print("\nExecuting FIBRAs screening and portfolio rebalancing...")
        ranked = evaluate_and_rank_fibras(min_yield=MIN_YIELD)
        top_candidates = ranked[:MAX_CONCURRENT_POSITIONS]
        
        target_holdings = {}
        if top_candidates:
            target_weight = min(MAX_STOCK_WEIGHT, 1.0 / len(top_candidates))
            for s in top_candidates:
                ticker_symbol = s["ticker"]
                target_holdings[ticker_symbol] = {
                    "price": s["current_price"],
                    "weight": target_weight,
                    "yield": s["dividend_yield"]
                }
                
        # Calculate current total portfolio value
        assets_val = sum(h["shares"] * current_prices.get(h["ticker"], h["last_price"]) for h in portfolio["holdings"])
        portfolio_value = current_cash + assets_val
        
        # 5a. Liquidate positions not in target
        updated_holdings = []
        for h in portfolio["holdings"]:
            ticker = h["ticker"]
            if ticker not in target_holdings:
                price = current_prices.get(ticker, h["last_price"])
                gross = h["shares"] * price
                fee = gross * TRANSACTION_COST
                current_cash = round(current_cash + (gross - fee), 2)
                portfolio["cash_balance"] = current_cash
                log_transaction(dir_path, today_str, ticker, "SELL", h["shares"], price, "Screener liquidation", fee=fee)
                rebalance_trades.append(f"  |-- LIQUIDATED {h['shares']:.2f} shares of {ticker} at ${price:.2f} MXN")
                print(rebalance_trades[-1])
            else:
                updated_holdings.append(h)
                
        portfolio["holdings"] = updated_holdings
        
        # 5b. Rebalance existing and buy new targets
        holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}
        
        for ticker, info in target_holdings.items():
            price = info["price"]
            target_val = portfolio_value * info["weight"]
            
            h = holdings_dict.get(ticker)
            curr_shares = h["shares"] if h else 0.0
            curr_val = curr_shares * price
            
            deviation = target_val - curr_val
            if abs(deviation) > (portfolio_value * 0.01):
                if deviation > 0:
                     shares_to_buy = deviation / price
                     cost = shares_to_buy * price
                     fee = cost * TRANSACTION_COST
                     if current_cash < (cost + fee):
                         # Adjust to fit available cash
                         cost = current_cash / (1.0 + TRANSACTION_COST)
                         fee = cost * TRANSACTION_COST
                         shares_to_buy = cost / price
                         
                     if shares_to_buy > 0.01:
                         current_cash = round(current_cash - (cost + fee), 2)
                         portfolio["cash_balance"] = current_cash
                         if h:
                             h["shares"] += shares_to_buy
                             h["last_price"] = price
                         else:
                             portfolio["holdings"].append({
                                 "ticker": ticker,
                                 "shares": shares_to_buy,
                                 "buy_price": price,
                                 "last_price": price,
                                 "target_weight": info["weight"]
                             })
                         log_transaction(dir_path, today_str, ticker, "BUY", shares_to_buy, price, f"Target weight allocation ({info['weight']*100:.1f}%)", fee=fee)
                         rebalance_trades.append(f"  |-- BOUGHT {shares_to_buy:.2f} shares of {ticker} at ${price:.2f} MXN")
                         print(rebalance_trades[-1])
                else:
                    shares_to_sell = abs(deviation) / price
                    if curr_shares > 0 and shares_to_sell > 0.01:
                        shares_to_sell = min(shares_to_sell, curr_shares)
                        gross = shares_to_sell * price
                        fee = gross * TRANSACTION_COST
                        current_cash = round(current_cash + (gross - fee), 2)
                        portfolio["cash_balance"] = current_cash
                        h["shares"] -= shares_to_sell
                        h["last_price"] = price
                        log_transaction(dir_path, today_str, ticker, "SELL", shares_to_sell, price, f"Trimmed to target weight ({info['weight']*100:.1f}%)", fee=fee)
                        rebalance_trades.append(f"  |-- TRIMMED {shares_to_sell:.2f} shares of {ticker} at ${price:.2f} MXN")
                        print(rebalance_trades[-1])
                        
        portfolio["last_rebalance_date"] = today_str
        print("Rebalancing completed.")

    # 6. Update prices of holdings & ensure dividend metadata is cached
    for h in portfolio["holdings"]:
        ticker = h["ticker"]
        if ticker not in current_prices or "dividend_rate" not in h:
            try:
                ticker_obj = yf.Ticker(ticker)
                if ticker not in current_prices:
                    hist = ticker_obj.history(period="1d")
                    if not hist.empty:
                        px = float(hist["Close"].iloc[-1])
                        if np.isfinite(px) and px > 0:
                            current_prices[ticker] = px
                
                if "dividend_rate" not in h:
                    info = ticker_obj.info
                    def format_epoch_date(val):
                        if not val:
                            return "N/A"
                        try:
                            return datetime.datetime.utcfromtimestamp(int(val)).strftime('%Y-%m-%d')
                        except Exception:
                            return "N/A"
                    h["dividend_rate"] = info.get("dividendRate") or info.get("trailingAnnualDividendRate") or 0.0
                    h["last_dividend"] = info.get("lastDividendValue") or 0.0
                    h["ex_dividend_date"] = format_epoch_date(info.get("exDividendDate"))
                    h["payment_date"] = format_epoch_date(info.get("dividendDate"))
            except Exception as e:
                print(f"  [WARN] Failed to fetch dividend metadata for {ticker}: {e}")
        
        if ticker in current_prices and np.isfinite(current_prices[ticker]) and current_prices[ticker] > 0:
            h["last_price"] = current_prices[ticker]

    # Calculate final stats
    assets_val = sum(h["shares"] * h["last_price"] for h in portfolio["holdings"])
    portfolio_value = current_cash + assets_val

    # Run Screener for all tickers to generate diagnostics report
    print("\nEvaluating all FIBRAs universe metrics for diagnostics...")
    diagnostics_metrics = {}
    for t in FIBRA_TICKERS:
        try:
            metrics = get_fibra_metrics(t)
            if metrics:
                diagnostics_metrics[t] = metrics
        except Exception as e:
            print(f"  [WARN] Failed to get diagnostics metrics for {t}: {e}")
            
    portfolio["last_updated"] = now_str
    save_portfolio(dir_path, portfolio)

    # 7. Generate Markdown Report
    print(f"\nWriting execution report to: {REPORT_FILE}...")
    report_markdown = f"""# Strategy 17: FIBRAs Dynamic Income Execution Report
**Execution Date:** {now_str} | **Strategy Version:** Live V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} MXN
* **Total Cash Balance:** ${current_cash:,.2f} MXN (Parked in Bondia Compound at 6.53% APR)
* **FIBRA Equity Exposure:** {((portfolio_value - current_cash)/portfolio_value * 100):.1f}%
* **Days Since Last Rebalance:** {(now.date() - last_rebalance_date).days} days

## 2. Current Holdings
| Ticker | Shares Held | Buy Price | Last Price | Market Value | Expected Yield (Annual) | Next Ex-Div / Pay Date | Target Weight |
| :--- | :---: | :---: | :---: | ---: | :--- | :--- | :---: |
"""
    for h in portfolio["holdings"]:
        mkt_val = h["shares"] * h["last_price"]
        rate = h.get("dividend_rate", 0.0)
        ann_div = h["shares"] * rate
        div_str = f"${rate:.2f} MXN/sh (Annual: ${ann_div:,.2f} MXN)"
        date_str = f"Ex: {h.get('ex_dividend_date', 'N/A')} / Pay: {h.get('payment_date', 'N/A')}"
        report_markdown += f"| **{h['ticker']}** | {h['shares']:.2f} | ${h['buy_price']:.2f} | ${h['last_price']:.2f} | ${mkt_val:,.2f} | {div_str} | {date_str} | {h.get('target_weight', 0.25)*100:.1f}% |\n"

    report_markdown += "\n## 3. Today's Execution Logs\n"
    if is_new_month:
        report_markdown += f"* **[SAVINGS DEPOSIT]** Detected calendar month transition. Injected $1,000.00 MXN savings contribution.\n"
    if accrued_interest > 0:
        report_markdown += f"* **[INTEREST ACCRUED]** Cash accrued interest of ${accrued_interest:,.4f} MXN over {days_elapsed:.4f} days.\n"
    if dividend_credits:
        report_markdown += "### Distributions Credited (DRIP):\n"
        for credit in dividend_credits:
            report_markdown += f"* {credit.strip()}\n"
    if should_rebalance:
        report_markdown += "### Quarterly Rebalancing Executed:\n"
        for trade in rebalance_trades:
            report_markdown += f"* {trade.strip()}\n"
    if not dividend_credits and not rebalance_trades and not is_new_month:
        report_markdown += "* No actions required today. Portfolio matches target weights and cash remains compounding.\n"

    # 4. Diagnostics Table
    report_markdown += "\n## 4. FIBRA Evaluation Diagnostics (Signals Checked)\n"
    report_markdown += "| Ticker | Signal | Yield | Debt / Equity | Close vs SMA 200 | Evaluation Reason |\n"
    report_markdown += "| :--- | :---: | :---: | :---: | :---: | :--- |\n"
    
    for t in sorted(FIBRA_TICKERS):
        metrics = diagnostics_metrics.get(t)
        if metrics is None:
            report_markdown += f"| **{t}** | - | - | - | - | Data failed | \n"
            continue
            
        dy = metrics["dividend_yield"]
        de = metrics["debt_to_equity"]
        price = metrics["current_price"]
        sma200 = metrics["sma200"]
        
        trend_bull = price > sma200
        
        reasons = []
        if dy < MIN_YIELD:
            reasons.append(f"Yield below {MIN_YIELD*100:.1f}%")
        if de > 1.5:
            reasons.append(f"Debt/Equity ({de:.2f}) exceeds 1.5")
        if not trend_bull:
            reasons.append("Bear trend (Close <= SMA 200)")
            
        if reasons:
            sig = "SELL / AVOID"
            reason = " and ".join(reasons)
        else:
            sig = "BUY / HOLD"
            reason = f"Passed quality screens. Score: {metrics.get('dividend_score', 0.0):.4f}"
            
        trend_str = f"${price:,.2f} > SMA ${sma200:,.2f}" if trend_bull else f"${price:,.2f} <= SMA ${sma200:,.2f}"
        report_markdown += f"| **{t}** | {sig} | {dy*100:.2f}% | {de*100:.1f}% | {trend_str} | {reason} |\n"

    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report_markdown)

    print("=" * 80)
    print("LIVE PAPER TRADING SUMMARY - STRATEGY 17")
    print("=" * 80)
    print(f"  Date:            {today_str}")
    print(f"  Portfolio NAV:   ${portfolio_value:,.2f} MXN")
    print(f"  Cash Reserve:    ${current_cash:,.2f} MXN")
    print(f"  Holdings Count:  {len(portfolio['holdings'])}")
    print(f"  Rebalanced:      {'YES (Quarterly)' if should_rebalance else 'NO (Normal Hold)'}")
    print(f"  Report Saved:    {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
