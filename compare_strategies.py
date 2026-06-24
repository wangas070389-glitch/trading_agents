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
    portfolio_us_path = os.path.join(dir_path, "portfolio_us_stocks.json")
    portfolio_us_dcs_path = os.path.join(dir_path, "portfolio_us_dcs.json")
    portfolio_alternatives_path = os.path.join(dir_path, "portfolio_alternatives.json")
    comparison_report_path = os.path.join(dir_path, "comparison_report.md")
    
    port_val = load_json(portfolio_val_path)
    port_macd = load_json(portfolio_macd_path)
    port_us = load_json(portfolio_us_path)
    port_us_dcs = load_json(portfolio_us_dcs_path)
    port_alternatives = load_json(portfolio_alternatives_path)
    
    if not port_val and not port_macd and not port_us and not port_us_dcs and not port_alternatives:
        print("Error: No portfolio files found. Cannot generate comparison.")
        return
        
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = []
    report.append("# Daily Strategy Performance Comparison Report")
    report.append(f"**Report Generated At:** {now_str}\n")
    
    # 1. Summary Comparison Table
    report.append("## 1. Executive Performance Summary")
    report.append("| Strategy | Total Portfolio Value | Cash Balance | Capital Invested | Allocation % | Total Profit/Loss | ROI % | Inception Date | Currency |")
    report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
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
        report.append(f"| **Adaptive Dynamic Value (V4)** | ${v_market_val:,.2f} | ${v_cash:,.2f} | ${v_invested:,.2f} | {v_alloc:.1f}% | {v_sign}${v_profit:,.2f} | {v_sign}{v_roi:.2f}% | 2026-06-03 | MXN |")
    else:
        report.append("| **Adaptive Dynamic Value (V4)** | *Not Initialized* | - | - | - | - | - | - | MXN |")
        
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
        report.append(f"| **1d MACD + SMA + HMM** | ${m_market_val:,.2f} | ${m_cash:,.2f} | ${m_invested:,.2f} | {m_alloc:.1f}% | {m_sign}${m_profit:,.2f} | {m_sign}{m_roi:.2f}% | 2026-06-03 | MXN |")
    else:
        report.append("| **1d MACD + SMA + HMM** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse Strategy 3 (US Stock Momentum - Isolated)
    if port_us:
        u_total_cap = port_us.get("total_capital", 100000.0)
        u_cash = port_us.get("cash_balance", 100000.0)
        u_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_us.get("holdings", []))
        u_market_val = u_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_us.get("holdings", []))
        u_profit = u_market_val - u_total_cap
        u_roi = (u_profit / u_total_cap) * 100.0
        u_alloc = (u_invested / u_market_val) * 100.0 if u_market_val > 0 else 0.0
        u_sign = "+" if u_profit >= 0 else ""
        report.append(f"| **US Stock Momentum (Isolated)** | ${u_market_val:,.2f} | ${u_cash:,.2f} | ${u_invested:,.2f} | {u_alloc:.1f}% | {u_sign}${u_profit:,.2f} | {u_sign}{u_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **US Stock Momentum (Isolated)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    # Parse Strategy 4 (US Stock DCS Value-Growth - Isolated)
    if port_us_dcs:
        ud_total_cap = port_us_dcs.get("total_capital", 100000.0)
        ud_cash = port_us_dcs.get("cash_balance", 100000.0)
        ud_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_us_dcs.get("holdings", []))
        ud_market_val = ud_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_us_dcs.get("holdings", []))
        ud_profit = ud_market_val - ud_total_cap
        ud_roi = (ud_profit / ud_total_cap) * 100.0
        ud_alloc = (ud_invested / ud_market_val) * 100.0 if ud_market_val > 0 else 0.0
        ud_sign = "+" if ud_profit >= 0 else ""
        report.append(f"| **US Stock DCS Value-Growth (Isolated)** | ${ud_market_val:,.2f} | ${ud_cash:,.2f} | ${ud_invested:,.2f} | {ud_alloc:.1f}% | {ud_sign}${ud_profit:,.2f} | {ud_sign}{ud_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **US Stock DCS Value-Growth (Isolated)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    # Parse Strategy 5 (Alternative Assets - Isolated)
    if port_alternatives:
        a_total_cap = port_alternatives.get("total_capital", 100000.0)
        a_cash = port_alternatives.get("cash_balance", 100000.0)
        a_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_alternatives.get("holdings", []))
        a_market_val = a_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_alternatives.get("holdings", []))
        a_profit = a_market_val - a_total_cap
        a_roi = (a_profit / a_total_cap) * 100.0
        a_alloc = (a_invested / a_market_val) * 100.0 if a_market_val > 0 else 0.0
        a_sign = "+" if a_profit >= 0 else ""
        report.append(f"| **Alternative Assets (Isolated)** | ${a_market_val:,.2f} | ${a_cash:,.2f} | ${a_invested:,.2f} | {a_alloc:.1f}% | {a_sign}${a_profit:,.2f} | {a_sign}{a_roi:.2f}% | 2026-06-24 | USD |")
    else:
        report.append("| **Alternative Assets (Isolated)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    report.append("\n" + "-" * 80 + "\n")
    
    # 2. Holdings Breakdown
    report.append("## 2. Strategy Holdings Details")
    
    # Strategy 1 Holdings
    report.append("### A. Adaptive Dynamic Value (V4) Holdings (MXN)")
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
    report.append("### B. 1d MACD + SMA + HMM Holdings (MXN)")
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
        
    report.append("\n")

    # Strategy 3 Holdings
    report.append("### C. US Stock Momentum (Isolated) Holdings (USD)")
    if port_us and port_us.get("holdings"):
        report.append("| Ticker | Shares Held | Average Cost (USD) | Current Price (USD) | Market Value (USD) | Target Weight | Unrealized P/L | P/L % |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for h in port_us["holdings"]:
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
        report.append("*No open stock positions currently held. Portfolio is 100% Cash.*")
        
    report.append("\n")

    # Strategy 4 Holdings
    report.append("### D. US Stock DCS Value-Growth (Isolated) Holdings (USD)")
    if port_us_dcs and port_us_dcs.get("holdings"):
        report.append("| Ticker | Shares Held | Average Cost (USD) | Current Price (USD) | Market Value (USD) | Target Weight | DCS Conviction | Unrealized P/L | P/L % |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for h in port_us_dcs["holdings"]:
            ticker = h["ticker"]
            shares = h["shares"]
            buy_price = h["buy_price"]
            last_price = h.get("last_price", buy_price)
            target_w = h.get("target_weight", 0.0)
            dcs = h.get("dcs", 0.0)
            mval = shares * last_price
            pl = mval - (shares * buy_price)
            pl_pct = ((last_price / buy_price) - 1.0) * 100.0 if buy_price > 0 else 0.0
            sign = "+" if pl >= 0 else ""
            report.append(f"| {ticker} | {shares:,} | ${buy_price:,.2f} | ${last_price:,.2f} | ${mval:,.2f} | {target_w:.1%} | {dcs:.3f} | {sign}${pl:,.2f} | {sign}{pl_pct:.2f}% |")
    else:
        report.append("*No open stock positions currently held. Portfolio is 100% Cash.*")
        
    report.append("\n")

    # Strategy 5 Holdings
    report.append("### E. Alternative Assets (Isolated) Holdings (USD)")
    if port_alternatives and port_alternatives.get("holdings"):
        report.append("| Ticker | Asset Type | Shares Held | Average Cost (USD) | Current Price (USD) | Market Value (USD) | Target Weight | Unrealized P/L | P/L % |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for h in port_alternatives["holdings"]:
            ticker = h["ticker"]
            asset_type = h.get("asset_type", "N/A").upper()
            shares = h["shares"]
            buy_price = h["buy_price"]
            last_price = h.get("last_price", buy_price)
            target_w = h.get("target_weight", 0.0)
            mval = shares * last_price
            pl = mval - (shares * buy_price)
            pl_pct = ((last_price / buy_price) - 1.0) * 100.0 if buy_price > 0 else 0.0
            sign = "+" if pl >= 0 else ""
            report.append(f"| {ticker} | {asset_type} | {shares:.4f} | ${buy_price:,.2f} | ${last_price:,.2f} | ${mval:,.2f} | {target_w:.1%} | {sign}${pl:,.2f} | {sign}{pl_pct:.2f}% |")
    else:
        report.append("*No alternative asset positions currently held. Portfolio is 100% Cash.*")
        
    report.append("\n" + "-" * 80 + "\n")
    
    # 3. Dynamic Yield & Reserves Details
    report.append("## 3. Cash Sweeps & Yield Settings")
    report.append("* **Bondia Overnight Cash Sweep Yield:** **6.53% APR** (accrued on unallocated MXN cash balance daily).")
    if port_val:
        report.append(f"* **Adaptive Value Current Cash Reserves:** ${port_val.get('cash_balance', 0.0):,.2f} MXN")
    if port_macd:
        report.append(f"* **1D MACD Current Cash Reserves:** ${port_macd.get('cash_balance', 0.0):,.2f} MXN")
    if port_us:
        report.append(f"* **US Stock Momentum Current Cash Reserves:** ${port_us.get('cash_balance', 0.0):,.2f} USD")
    if port_us_dcs:
        report.append(f"* **US Stock DCS Value-Growth Current Cash Reserves:** ${port_us_dcs.get('cash_balance', 0.0):,.2f} USD")
    if port_alternatives:
        report.append(f"* **Alternative Assets Current Cash Reserves:** ${port_alternatives.get('cash_balance', 0.0):,.2f} USD")
        
    # Write to comparison_report.md
    with open(comparison_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Comparison report generated successfully: {comparison_report_path}")

if __name__ == "__main__":
    main()
