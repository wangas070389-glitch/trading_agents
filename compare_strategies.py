import os
import json
import datetime

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    
    portfolio_val_path = os.path.join(dir_path, "portfolio.json")
    portfolio_macd_path = os.path.join(dir_path, "portfolio_macd.json")
    comparison_report_path = os.path.join(dir_path, "comparison_report.md")
    
    port_val = load_json(portfolio_val_path)
    port_macd = load_json(portfolio_macd_path)
    
    if not port_val and not port_macd:
        print("Error: Neither portfolio.json nor portfolio_macd.json was found. Cannot generate comparison.")
        return
        
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = []
    report.append("# Daily Strategy Performance Comparison Report")
    report.append(f"**Report Generated At:** {now_str}\n")
    
    # 1. Summary Comparison Table
    report.append("## 1. Executive Performance Summary")
    report.append("| Strategy | Total Portfolio Value (MXN) | Cash Balance (MXN) | Capital Invested (MXN) | Allocation % | Total Profit/Loss | ROI % | Inception Date |")
    report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    # Parse Strategy 1 (Adaptive Value)
    if port_val:
        v_total_cap = port_val.get("total_capital", 20000.0)
        v_cash = port_val.get("cash_balance", 20000.0)
        v_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_val.get("holdings", []))
        v_market_val = v_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_val.get("holdings", []))
        v_profit = v_market_val - v_total_cap
        v_roi = (v_profit / v_total_cap) * 100.0
        v_alloc = (v_invested / v_market_val) * 100.0 if v_market_val > 0 else 0.0
        v_sign = "+" if v_profit >= 0 else ""
        report.append(f"| **Adaptive Dynamic Value (V4)** | ${v_market_val:,.2f} | ${v_cash:,.2f} | ${v_invested:,.2f} | {v_alloc:.1f}% | {v_sign}${v_profit:,.2f} | {v_sign}{v_roi:.2f}% | 2026-06-03 |")
    else:
        report.append("| **Adaptive Dynamic Value (V4)** | *Not Initialized* | - | - | - | - | - | - |")
        
    # Parse Strategy 2 (1d MACD)
    if port_macd:
        m_total_cap = port_macd.get("total_capital", 20000.0)
        m_cash = port_macd.get("cash_balance", 20000.0)
        m_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_macd.get("holdings", []))
        m_market_val = m_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_macd.get("holdings", []))
        m_profit = m_market_val - m_total_cap
        m_roi = (m_profit / m_total_cap) * 100.0
        m_alloc = (m_invested / m_market_val) * 100.0 if m_market_val > 0 else 0.0
        m_sign = "+" if m_profit >= 0 else ""
        report.append(f"| **1d MACD + SMA + HMM** | ${m_market_val:,.2f} | ${m_cash:,.2f} | ${m_invested:,.2f} | {m_alloc:.1f}% | {m_sign}${m_profit:,.2f} | {m_sign}{m_roi:.2f}% | 2026-06-03 |")
    else:
        report.append("| **1d MACD + SMA + HMM** | *Not Initialized* | - | - | - | - | - | - |")
        
    report.append("\n" + "-" * 80 + "\n")
    
    # 2. Holdings Breakdown
    report.append("## 2. Strategy Holdings Details")
    
    # Strategy 1 Holdings
    report.append("### A. Adaptive Dynamic Value (V4) Holdings")
    if port_val and port_val.get("holdings"):
        report.append("| Ticker | Shares Held | Average Cost (MXN) | Current Price (MXN) | Market Value (MXN) | Target Weight | Unrealized P/L | P/L % |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for h in port_val["holdings"]:
            ticker = h["ticker"]
            shares = h["shares"]
            buy_price = h["buy_price"]
            last_price = h.get("last_price", buy_price)
            target_w = h.get("target_weight", 0.0)
            mval = shares * last_price
            pl = mval - (shares * buy_price)
            pl_pct = ((last_price / buy_price) - 1.0) * 100.0 if buy_price > 0 else 0.0
            sign = "+" if pl >= 0 else ""
            report.append(f"| {ticker} | {shares:,} | ${buy_price:,.2f} | ${last_price:,.2f} | ${mval:,.2f} | {target_w:.1%} | {sign}${pl:,.2f} | {sign}{pl_pct:.2f}% |")
    else:
        report.append("*No open stock positions currently held. Portfolio is 100% Cash / Bondia sweep.*")
        
    report.append("\n")
    
    # Strategy 2 Holdings
    report.append("### B. 1d MACD + SMA + HMM Holdings")
    if port_macd and port_macd.get("holdings"):
        report.append("| Ticker | Shares Held | Average Cost (MXN) | Current Price (MXN) | Market Value (MXN) | Target Weight | Unrealized P/L | P/L % |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for h in port_macd["holdings"]:
            ticker = h["ticker"]
            shares = h["shares"]
            buy_price = h["buy_price"]
            last_price = h.get("last_price", buy_price)
            target_w = h.get("target_weight", 0.0)
            mval = shares * last_price
            pl = mval - (shares * buy_price)
            pl_pct = ((last_price / buy_price) - 1.0) * 100.0 if buy_price > 0 else 0.0
            sign = "+" if pl >= 0 else ""
            report.append(f"| {ticker} | {shares:,} | ${buy_price:,.2f} | ${last_price:,.2f} | ${mval:,.2f} | {target_w:.1%} | {sign}${pl:,.2f} | {sign}{pl_pct:.2f}% |")
    else:
        report.append("*No open stock positions currently held. Portfolio is 100% Cash / Bondia sweep.*")
        
    report.append("\n" + "-" * 80 + "\n")
    
    # 3. Dynamic Yield & Reserves Details
    report.append("## 3. Cash Sweeps & Yield Settings")
    report.append("* **Bondia Overnight Cash Sweep Yield:** **6.53% APR** (accrued on unallocated cash balance daily).")
    if port_val:
        report.append(f"* **Adaptive Value Current Cash Reserves:** ${port_val.get('cash_balance', 0.0):,.2f} MXN")
    if port_macd:
        report.append(f"* **1D MACD Current Cash Reserves:** ${port_macd.get('cash_balance', 0.0):,.2f} MXN")
        
    # Write to comparison_report.md
    with open(comparison_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Comparison report generated successfully: {comparison_report_path}")

if __name__ == "__main__":
    main()
