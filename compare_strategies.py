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
    portfolio_high_beta_path = os.path.join(dir_path, "portfolio_high_beta.json")
    portfolio_multi_strategy_path = os.path.join(dir_path, "portfolio_multi_strategy.json")
    comparison_report_path = os.path.join(dir_path, "comparison_report.md")
    
    port_val = load_json(portfolio_val_path)
    port_macd = load_json(portfolio_macd_path)
    port_us = load_json(portfolio_us_path)
    port_us_dcs = load_json(portfolio_us_dcs_path)
    port_alternatives = load_json(portfolio_alternatives_path)
    port_high_beta = load_json(portfolio_high_beta_path)
    port_multi_strategy = load_json(portfolio_multi_strategy_path)
    
    if not port_val and not port_macd and not port_us and not port_us_dcs and not port_alternatives and not port_high_beta and not port_multi_strategy:
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
        
    # Parse Strategy 6 (High-Beta Value-Momentum - Isolated)
    if port_high_beta:
        hb_total_cap = port_high_beta.get("total_capital", 100000.0)
        hb_cash = port_high_beta.get("cash_balance", 100000.0)
        hb_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_high_beta.get("holdings", []))
        hb_market_val = hb_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_high_beta.get("holdings", []))
        hb_profit = hb_market_val - hb_total_cap
        hb_roi = (hb_profit / hb_total_cap) * 100.0
        hb_alloc = (hb_invested / hb_market_val) * 100.0 if hb_market_val > 0 else 0.0
        hb_sign = "+" if hb_profit >= 0 else ""
        report.append(f"| **High-Beta Value-Momentum (Isolated)** | ${hb_market_val:,.2f} | ${hb_cash:,.2f} | ${hb_invested:,.2f} | {hb_alloc:.1f}% | {hb_sign}${hb_profit:,.2f} | {hb_sign}{hb_roi:.2f}% | 2026-06-24 | USD |")
    else:
        report.append("| **High-Beta Value-Momentum (Isolated)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    # Parse Strategy 7 (Consolidated Multi-Strategy)
    if port_multi_strategy:
        usd_mxn_rate = port_multi_strategy.get("usd_mxn_rate", 18.0)
        s1_cap_usd = port_val.get("total_capital", 20000.0) / usd_mxn_rate if port_val else 1139.0
        s4_cap = port_us_dcs.get("total_capital", 100000.0) if port_us_dcs else 100000.0
        s5_cap = port_alternatives.get("total_capital", 100000.0) if port_alternatives else 100000.0
        s6_cap = port_high_beta.get("total_capital", 100000.0) if port_high_beta else 100000.0
        ms_total_cap = s1_cap_usd + s4_cap + s5_cap + s6_cap
        
        ms_market_val = port_multi_strategy.get("total_portfolio_value_usd", 0.0)
        ms_cash = port_multi_strategy.get("total_cash_balance_usd", 0.0)
        ms_invested = ms_market_val - ms_cash
        ms_profit = ms_market_val - ms_total_cap
        ms_roi = (ms_profit / ms_total_cap) * 100.0 if ms_total_cap > 0 else 0.0
        ms_alloc = (ms_invested / ms_market_val) * 100.0 if ms_market_val > 0 else 0.0
        ms_sign = "+" if ms_profit >= 0 else ""
        report.append(f"| **Consolidated Multi-Strategy (S7)** | ${ms_market_val:,.2f} | ${ms_cash:,.2f} | ${ms_invested:,.2f} | {ms_alloc:.1f}% | {ms_sign}${ms_profit:,.2f} | {ms_sign}{ms_roi:.2f}% | 2026-06-24 | USD |")
    else:
        report.append("| **Consolidated Multi-Strategy (S7)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
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
        
    report.append("\n")

    # Strategy 6 Holdings
    report.append("### F. High-Beta Value-Momentum (Isolated) Holdings (USD)")
    if port_high_beta and port_high_beta.get("holdings"):
        report.append("| Ticker | Shares Held | Average Cost (USD) | Current Price (USD) | Market Value (USD) | Target Weight | DCS Conviction | Beta | Unrealized P/L | P/L % |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for h in port_high_beta["holdings"]:
            ticker = h["ticker"]
            shares = h["shares"]
            buy_price = h["buy_price"]
            last_price = h.get("last_price", buy_price)
            target_w = h.get("target_weight", 0.33)
            dcs = h.get("dcs", 0.0)
            beta = h.get("beta", 0.0)
            mval = shares * last_price
            pl = mval - (shares * buy_price)
            pl_pct = ((last_price / buy_price) - 1.0) * 100.0 if buy_price > 0 else 0.0
            sign = "+" if pl >= 0 else ""
            report.append(f"| {ticker} | {shares:.4f} | ${buy_price:,.2f} | ${last_price:,.2f} | ${mval:,.2f} | {target_w:.1%} | {dcs:.3f} | {beta:.2f} | {sign}${pl:,.2f} | {sign}{pl_pct:.2f}% |")
    else:
        report.append("*No open stock positions currently held. Portfolio is 100% Cash.*")
        
    report.append("\n")

    # Strategy 7 Holdings (Allocations)
    report.append("### G. Consolidated Multi-Strategy Portfolio (Strategy 7) Allocations (USD)")
    if port_multi_strategy and port_multi_strategy.get("allocations"):
        report.append("| Strategy Component | Target Allocation % | Current Weight % | Deviation % | Current Value (USD) |")
        report.append("| :--- | :---: | :---: | :---: | :---: |")
        allocs = port_multi_strategy["allocations"]
        for key, val in allocs.items():
            name = key.replace("_", " ").title()
            target_w = val.get("target_weight", 0.0)
            curr_w = val.get("current_weight", 0.0)
            dev = val.get("deviation", 0.0)
            nav = val.get("nav_usd", 0.0)
            sign = "+" if dev >= 0 else ""
            report.append(f"| {name} | {target_w:.1%} | {curr_w:.1%} | {sign}{dev:.1%} | ${nav:,.2f} |")
    else:
        report.append("*Multi-strategy allocation tracking is not active.*")

    report.append("\n" + "-" * 80 + "\n")
    
    # 3. Dynamic Yield & Reserves Details
    report.append("## 3. Cash Sweeps & Yield Settings")
    report.append("* **Bondia Overnight Cash Sweep Yield:** **6.53% APR** (accrued on unallocated MXN cash balance daily).")
    report.append("* **USD Sweep Cash Yield:** **4.50% APR** (accrued on unallocated USD cash reserves daily).")
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
    if port_high_beta:
        report.append(f"* **High-Beta Momentum Current Cash Reserves:** ${port_high_beta.get('cash_balance', 0.0):,.2f} USD")
    if port_multi_strategy:
        report.append(f"* **Consolidated Portfolio Current Cash Reserves:** ${port_multi_strategy.get('total_cash_balance_usd', 0.0):,.2f} USD")
        
    # Write to comparison_report.md
    with open(comparison_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Comparison report generated successfully: {comparison_report_path}")

    # 4. Generate all strategies allocation history
    usd_mxn = port_multi_strategy.get("usd_mxn_rate", 17.5) if port_multi_strategy else 17.5
    
    # Helper to compute local NAV
    def get_portfolio_nav(port):
        if not port:
            return 0.0
        cash = float(port.get("cash_balance", 0.0))
        holdings_val = sum(float(h.get("shares", 0.0)) * float(h.get("last_price", h.get("buy_price", 0.0))) for h in port.get("holdings", []))
        return cash + holdings_val

    s1_nav_mxn = get_portfolio_nav(port_val)
    s2_nav_mxn = get_portfolio_nav(port_macd)
    s3_nav_usd = get_portfolio_nav(port_us)
    s4_nav_usd = get_portfolio_nav(port_us_dcs)
    s5_nav_usd = get_portfolio_nav(port_alternatives)
    s6_nav_usd = get_portfolio_nav(port_high_beta)

    s1_nav_usd = s1_nav_mxn / usd_mxn
    s2_nav_usd = s2_nav_mxn / usd_mxn
    
    total_nav_usd = s1_nav_usd + s2_nav_usd + s3_nav_usd + s4_nav_usd + s5_nav_usd + s6_nav_usd

    history_json_path = os.path.join(dir_path, "all_strategies_history.json")
    all_history = []
    if os.path.exists(history_json_path):
        try:
            with open(history_json_path, 'r', encoding='utf-8') as f:
                all_history = json.load(f)
        except Exception:
            all_history = []

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    exists_idx = -1
    for idx, entry in enumerate(all_history):
        if entry["date"] == today_str:
            exists_idx = idx
            break
            
    new_entry = {
        "date": today_str,
        "s1_nav_usd": s1_nav_usd,
        "s2_nav_usd": s2_nav_usd,
        "s3_nav_usd": s3_nav_usd,
        "s4_nav_usd": s4_nav_usd,
        "s5_nav_usd": s5_nav_usd,
        "s6_nav_usd": s6_nav_usd,
        "total_nav_usd": total_nav_usd
    }
    
    if exists_idx != -1:
        all_history[exists_idx] = new_entry
    else:
        all_history.append(new_entry)
        
    try:
        with open(history_json_path, 'w', encoding='utf-8') as f:
            json.dump(all_history, f, indent=2)
    except Exception as e:
        print(f"Error saving all strategies history: {e}")

    history_md_path = os.path.join(dir_path, "all_strategies_allocation_history.md")
    md_lines = [
        "# All Strategies Allocation History\n",
        "| Date | Strategy 1 (MXN Value) | Strategy 2 (1d MACD) | Strategy 3 (US Momentum) | Strategy 4 (US DCS) | Strategy 5 (Alternatives) | Strategy 6 (High-Beta) | Total Combined NAV (USD) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    sorted_all_history = sorted(all_history, key=lambda x: x["date"], reverse=True)
    for entry in sorted_all_history:
        date = entry["date"]
        nav = entry["total_nav_usd"]
        if nav > 0:
            pct1 = (entry["s1_nav_usd"] / nav) * 100.0
            pct2 = (entry["s2_nav_usd"] / nav) * 100.0
            pct3 = (entry["s3_nav_usd"] / nav) * 100.0
            pct4 = (entry["s4_nav_usd"] / nav) * 100.0
            pct5 = (entry["s5_nav_usd"] / nav) * 100.0
            pct6 = (entry["s6_nav_usd"] / nav) * 100.0
        else:
            pct1 = pct2 = pct3 = pct4 = pct5 = pct6 = 0.0
            
        md_lines.append(f"| {date} | {pct1:.1f}% | {pct2:.1f}% | {pct3:.1f}% | {pct4:.1f}% | {pct5:.1f}% | {pct6:.1f}% | ${nav:,.2f} |")
        
    try:
        with open(history_md_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(md_lines) + "\n")
        print(f"All strategies allocation history saved to {history_md_path}")
    except Exception as e:
        print(f"Error saving all strategies allocation history: {e}")

if __name__ == "__main__":
    main()
