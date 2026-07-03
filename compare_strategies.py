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
    portfolio_dividends_path = os.path.join(dir_path, "portfolio_dividends.json")
    portfolio_strategy9_path = os.path.join(dir_path, "portfolio_strategy9.json")
    portfolio_strategy10_path = os.path.join(dir_path, "portfolio_strategy10.json")
    portfolio_strategy11_path = os.path.join(dir_path, "portfolio_strategy11.json")
    comparison_report_path = os.path.join(dir_path, "comparison_report.md")
    
    port_val = load_json(portfolio_val_path)
    port_macd = load_json(portfolio_macd_path)
    port_us = load_json(portfolio_us_path)
    port_us_dcs = load_json(portfolio_us_dcs_path)
    port_alternatives = load_json(portfolio_alternatives_path)
    port_high_beta = load_json(portfolio_high_beta_path)
    port_dividends = load_json(portfolio_dividends_path)
    port_strategy9 = load_json(portfolio_strategy9_path)
    port_strategy10 = load_json(portfolio_strategy10_path)
    port_strategy11 = load_json(portfolio_strategy11_path)
    port_multi_strategy = load_json(portfolio_multi_strategy_path)
    
    if not port_val and not port_macd and not port_us and not port_us_dcs and not port_alternatives and not port_high_beta and not port_dividends and not port_strategy9 and not port_strategy10 and not port_strategy11 and not port_multi_strategy:
        print("Error: No portfolio files found. Cannot generate comparison.")
        return
        
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    report = []
    report.append("# Daily Strategy Performance Comparison Report")
    report.append(f"**Report Generated At:** {now_str}\n")
    
    # 1. Summary Comparison Table
    report.append("## 1. Executive Performance Summary")
    report.append("| Strategy | Total Portfolio Value | Cash Balance | Capital Invested | Allocation % | Total Profit/Loss | ROI % | Inception Date | Currency |")
    report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    # Parse S1
    if port_val:
        v_total_cap = port_val.get("total_capital", 20000.0)
        v_cash = port_val.get("cash_balance", 20000.0)
        v_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_val.get("holdings", []))
        v_market_val = v_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_val.get("holdings", []))
        v_profit = v_market_val - v_total_cap
        v_roi = (v_profit / v_total_cap) * 100.0
        v_alloc = (v_invested / v_market_val) * 100.0 if v_market_val > 0 else 0.0
        v_sign = "+" if v_profit >= 0 else ""
        report.append(f"| **Adaptive Dynamic Value (S1)** | ${v_market_val:,.2f} | ${v_cash:,.2f} | ${v_invested:,.2f} | {v_alloc:.1f}% | {v_sign}${v_profit:,.2f} | {v_sign}{v_roi:.2f}% | 2026-06-03 | MXN |")
    else:
        report.append("| **Adaptive Dynamic Value (S1)** | *Not Initialized* | - | - | - | - | - | - | MXN |")
        
    # Parse S2
    if port_macd:
        m_total_cap = port_macd.get("total_capital", 20000.0)
        m_cash = port_macd.get("cash_balance", 20000.0)
        m_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_macd.get("holdings", []))
        m_market_val = m_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_macd.get("holdings", []))
        m_profit = m_market_val - m_total_cap
        m_roi = (m_profit / m_total_cap) * 100.0
        m_alloc = (m_invested / m_market_val) * 100.0 if m_market_val > 0 else 0.0
        m_sign = "+" if m_profit >= 0 else ""
        report.append(f"| **1d MACD Systematic (S2)** | ${m_market_val:,.2f} | ${m_cash:,.2f} | ${m_invested:,.2f} | {m_alloc:.1f}% | {m_sign}${m_profit:,.2f} | {m_sign}{m_roi:.2f}% | 2026-06-03 | MXN |")
    else:
        report.append("| **1d MACD Systematic (S2)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S3
    if port_us:
        u_total_cap = port_us.get("total_capital", 100000.0)
        u_cash = port_us.get("cash_balance", 100000.0)
        u_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_us.get("holdings", []))
        u_market_val = u_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_us.get("holdings", []))
        u_profit = u_market_val - u_total_cap
        u_roi = (u_profit / u_total_cap) * 100.0
        u_alloc = (u_invested / u_market_val) * 100.0 if u_market_val > 0 else 0.0
        u_sign = "+" if u_profit >= 0 else ""
        report.append(f"| **US Stock Momentum (S3)** | ${u_market_val:,.2f} | ${u_cash:,.2f} | ${u_invested:,.2f} | {u_alloc:.1f}% | {u_sign}${u_profit:,.2f} | {u_sign}{u_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **US Stock Momentum (S3)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    # Parse S4
    if port_us_dcs:
        ud_total_cap = port_us_dcs.get("total_capital", 100000.0)
        ud_cash = port_us_dcs.get("cash_balance", 100000.0)
        ud_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_us_dcs.get("holdings", []))
        ud_market_val = ud_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_us_dcs.get("holdings", []))
        ud_profit = ud_market_val - ud_total_cap
        ud_roi = (ud_profit / ud_total_cap) * 100.0
        ud_alloc = (ud_invested / ud_market_val) * 100.0 if ud_market_val > 0 else 0.0
        ud_sign = "+" if ud_profit >= 0 else ""
        report.append(f"| **US DCS Value-Growth (S4)** | ${ud_market_val:,.2f} | ${ud_cash:,.2f} | ${ud_invested:,.2f} | {ud_alloc:.1f}% | {ud_sign}${ud_profit:,.2f} | {ud_sign}{ud_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **US DCS Value-Growth (S4)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    # Parse S5
    if port_alternatives:
        a_total_cap = port_alternatives.get("total_capital", 100000.0)
        a_cash = port_alternatives.get("cash_balance", 100000.0)
        a_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_alternatives.get("holdings", []))
        a_market_val = a_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_alternatives.get("holdings", []))
        a_profit = a_market_val - a_total_cap
        a_roi = (a_profit / a_total_cap) * 100.0
        a_alloc = (a_invested / a_market_val) * 100.0 if a_market_val > 0 else 0.0
        a_sign = "+" if a_profit >= 0 else ""
        report.append(f"| **Alternative Assets (S5)** | ${a_market_val:,.2f} | ${a_cash:,.2f} | ${a_invested:,.2f} | {a_alloc:.1f}% | {a_sign}${a_profit:,.2f} | {a_sign}{a_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **Alternative Assets (S5)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    # Parse S6
    if port_high_beta:
        h_total_cap = port_high_beta.get("total_capital", 100000.0)
        h_cash = port_high_beta.get("cash_balance", 100000.0)
        h_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_high_beta.get("holdings", []))
        h_market_val = h_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_high_beta.get("holdings", []))
        h_profit = h_market_val - h_total_cap
        h_roi = (h_profit / h_total_cap) * 100.0
        h_alloc = (h_invested / h_market_val) * 100.0 if h_market_val > 0 else 0.0
        h_sign = "+" if h_profit >= 0 else ""
        report.append(f"| **High-Beta Momentum (S6)** | ${h_market_val:,.2f} | ${h_cash:,.2f} | ${h_invested:,.2f} | {h_alloc:.1f}% | {h_sign}${h_profit:,.2f} | {h_sign}{h_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **High-Beta Momentum (S6)** | *Not Initialized* | - | - | - | - | - | - | USD |")

    # Parse S8
    if port_dividends:
        div_total_cap = port_dividends.get("total_capital", 200000.0)
        div_cash = port_dividends.get("cash_balance", 200000.0)
        div_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_dividends.get("holdings", []))
        div_market_val = div_cash + sum(h["shares"] * h.get("last_price", h.get("buy_price", 0.0)) for h in port_dividends.get("holdings", []))
        div_profit = div_market_val - div_total_cap
        div_roi = (div_profit / div_total_cap) * 100.0
        div_alloc = (div_invested / div_market_val) * 100.0 if div_market_val > 0 else 0.0
        div_sign = "+" if div_profit >= 0 else ""
        report.append(f"| **Dividend Quality (S8)** | ${div_market_val:,.2f} | ${div_cash:,.2f} | ${div_invested:,.2f} | {div_alloc:.1f}% | {div_sign}${div_profit:,.2f} | {div_sign}{div_roi:.2f}% | 2026-06-25 | MXN |")
    else:
        report.append("| **Dividend Quality (S8)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S9
    if port_strategy9:
        s9_total_cap = port_strategy9.get("total_capital", 200000.0)
        s9_cash = port_strategy9.get("cash_balance", 200000.0)
        # S9 handles pairs/other lists
        s9_invested = 0.0
        for h in port_strategy9.get("holdings", []):
            if h.get("ticker", "").startswith("PAIR:"):
                s9_invested += float(h.get("allocated", 0.0))
            else:
                s9_invested += float(h.get("shares", 0.0)) * float(h.get("buy_price", 0.0))
        s9_market_val = s9_cash
        for h in port_strategy9.get("holdings", []):
            if h.get("ticker", "").startswith("PAIR:"):
                s9_market_val += float(h.get("last_price", h.get("buy_price", 0.0)))
            else:
                s9_market_val += float(h.get("shares", 0.0)) * float(h.get("last_price", h.get("buy_price", 0.0)))
                
        s9_profit = s9_market_val - s9_total_cap
        s9_roi = (s9_profit / s9_total_cap) * 100.0
        s9_alloc = (s9_invested / s9_market_val) * 100.0 if s9_market_val > 0 else 0.0
        s9_sign = "+" if s9_profit >= 0 else ""
        report.append(f"| **AI Regime Stat-Arb (S9)** | ${s9_market_val:,.2f} | ${s9_cash:,.2f} | ${s9_invested:,.2f} | {s9_alloc:.1f}% | {s9_sign}${s9_profit:,.2f} | {s9_sign}{s9_roi:.2f}% | 2026-06-30 | MXN |")
    else:
        report.append("| **AI Regime Stat-Arb (S9)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S10
    if port_strategy10:
        s10_total_cap = port_strategy10.get("total_capital", 200000.0)
        s10_cash = port_strategy10.get("cash_balance", 200000.0)
        s10_invested = sum(float(h.get("allocated", h["shares"] * h["buy_price"])) for h in port_strategy10.get("holdings", []))
        
        s10_market_val = s10_cash
        for h in port_strategy10.get("holdings", []):
            if h.get("side", "long") == "long":
                s10_market_val += h["shares"] * h.get("last_price", h["buy_price"])
            else:
                s10_market_val += h["allocated"] + (h["allocated"] - h["shares"] * h.get("last_price", h["buy_price"]))
                
        s10_profit = s10_market_val - s10_total_cap
        s10_roi = (s10_profit / s10_total_cap) * 100.0
        s10_alloc = (s10_invested / s10_market_val) * 100.0 if s10_market_val > 0 else 0.0
        s10_sign = "+" if s10_profit >= 0 else ""
        report.append(f"| **AI Intraday VWAP (S10)** | ${s10_market_val:,.2f} | ${s10_cash:,.2f} | ${s10_invested:,.2f} | {s10_alloc:.1f}% | {s10_sign}${s10_profit:,.2f} | {s10_sign}{s10_roi:.2f}% | 2026-07-02 | MXN |")
    else:
        report.append("| **AI Intraday VWAP (S10)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S11
    if port_strategy11:
        s11_total_cap = port_strategy11.get("total_capital", 200000.0)
        s11_cash = port_strategy11.get("cash_balance", 200000.0)
        s11_invested = sum(float(h.get("allocated", h["shares"] * h["buy_price"])) for h in port_strategy11.get("holdings", []))
        
        s11_market_val = s11_cash
        for h in port_strategy11.get("holdings", []):
            if h.get("side", "long") == "long":
                s11_market_val += h["shares"] * h.get("last_price", h["buy_price"])
            else:
                s11_market_val += h["allocated"] + (h["allocated"] - h["shares"] * h.get("last_price", h["buy_price"]))
                
        s11_profit = s11_market_val - s11_total_cap
        s11_roi = (s11_profit / s11_total_cap) * 100.0
        s11_alloc = (s11_invested / s11_market_val) * 100.0 if s11_market_val > 0 else 0.0
        s11_sign = "+" if s11_profit >= 0 else ""
        report.append(f"| **AI Intraday CCI-ADX (S11)** | ${s11_market_val:,.2f} | ${s11_cash:,.2f} | ${s11_invested:,.2f} | {s11_alloc:.1f}% | {s11_sign}${s11_profit:,.2f} | {s11_sign}{s11_roi:.2f}% | 2026-07-02 | MXN |")
    else:
        report.append("| **AI Intraday CCI-ADX (S11)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse Strategy 7 (Consolidated Multi-Strategy)
    if port_multi_strategy:
        ms_val = port_multi_strategy.get("total_portfolio_value_usd", 0.0)
        ms_cash = port_multi_strategy.get("total_cash_balance_usd", 0.0)
        ms_invested = ms_val - ms_cash
        
        # historical return reference
        perf = port_multi_strategy.get("performance", {})
        cagr = perf.get("cagr", 0.0)
        sharpe = perf.get("sharpe_ratio", 0.0)
        max_dd = perf.get("max_drawdown", 0.0)
        cum_twr = perf.get("cum_twr", 1.0)
        
        profit_usd = ms_val - 337495.51 # incept capital
        roi_ms = (profit_usd / 337495.51) * 100.0 if ms_val > 0 else 0.0
        ms_sign = "+" if profit_usd >= 0 else ""
        
        report.append(f"| **Strategy 7 (Consolidated Core)** | ${ms_val:,.2f} | ${ms_cash:,.2f} | ${ms_invested:,.2f} | {((ms_invested/ms_val)*100.0):.1f}% | {ms_sign}${profit_usd:,.2f} | {ms_sign}{roi_ms:.2f}% | 2026-07-02 | USD |")
    else:
        report.append("| **Strategy 7 (Consolidated Core)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    report.append("\n*Note: Strategy 7 consolidated values represent all strategies rebalanced dynamically under risk parity.*")

    # 2. Add details of active allocations
    report.append("\n## 2. Dynamic Weight Deviations (Strategy 7 Core Components)")
    report.append("| Component Strategy | Current Value (USD) | Target Weight % | Current Weight % | Deviation % |")
    report.append("| :--- | :---: | :---: | :---: | :---: |")
    
    if port_multi_strategy and "allocations" in port_multi_strategy:
        allocs = port_multi_strategy["allocations"]
        for key, val in allocs.items():
            name = key.replace("strategy_", "").replace("_", " ").title()
            v_usd = val["nav_usd"]
            t_w = val["target_weight"] * 100.0
            c_w = val["current_weight"] * 100.0
            dev = val["deviation"] * 100.0
            sign = "+" if dev >= 0 else ""
            report.append(f"| {name} | ${v_usd:,.2f} | {t_w:.1f}% | {c_w:.1f}% | {sign}{dev:.1f}% |")

    # Save to comparison_report.md
    with open(comparison_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print(f"Comparison report generated successfully: {comparison_report_path}")

    # Log historical allocations
    history_json_path = os.path.join(dir_path, "all_strategies_history.json")
    all_history = load_json(history_json_path) or []
    
    # Ingest today's rates
    usd_mxn_rate = port_multi_strategy.get("usd_mxn_rate", 17.42) if port_multi_strategy else 17.42
    
    # Calculate local conversions
    s1_nav_usd = s1_market_val / usd_mxn_rate if 's1_market_val' in locals() else (s1_nav_mxn / usd_mxn_rate if 's1_nav_mxn' in locals() else 0.0)
    s2_nav_usd = m_market_val / usd_mxn_rate if 'm_market_val' in locals() else (s2_nav_mxn / usd_mxn_rate if 's2_nav_mxn' in locals() else 0.0)
    s3_nav_usd = u_market_val if 'u_market_val' in locals() else (u_nav_usd if 'u_nav_usd' in locals() else 0.0)
    s4_nav_usd = ud_market_val if 'ud_market_val' in locals() else (s4_nav_usd if 's4_nav_usd' in locals() else 0.0)
    s5_nav_usd = a_market_val if 'a_market_val' in locals() else (s5_nav_usd if 's5_nav_usd' in locals() else 0.0)
    s6_nav_usd = h_market_val if 'h_market_val' in locals() else (s6_nav_usd if 's6_nav_usd' in locals() else 0.0)
    s8_nav_usd = div_market_val / usd_mxn_rate if 'div_market_val' in locals() else (s8_nav_mxn / usd_mxn_rate if 's8_nav_mxn' in locals() else 0.0)
    s9_nav_usd = s9_market_val / usd_mxn_rate if 's9_market_val' in locals() else (s9_nav_mxn / usd_mxn_rate if 's9_nav_mxn' in locals() else 0.0)
    s10_nav_usd = s10_market_val / usd_mxn_rate if 's10_market_val' in locals() else (s10_nav_mxn / usd_mxn_rate if 's10_nav_mxn' in locals() else 0.0)
    s11_nav_usd = s11_market_val / usd_mxn_rate if 's11_market_val' in locals() else (s11_nav_mxn / usd_mxn_rate if 's11_nav_mxn' in locals() else 0.0)
    
    total_combined_usd = s1_nav_usd + s2_nav_usd + s3_nav_usd + s4_nav_usd + s5_nav_usd + s6_nav_usd + s8_nav_usd + s9_nav_usd + s10_nav_usd + s11_nav_usd
    
    # Append entry
    if not all_history or all_history[-1]["date"] != today_str:
        all_history.append({
            "date": today_str,
            "s1_nav_usd": s1_nav_usd,
            "s2_nav_usd": s2_nav_usd,
            "s3_nav_usd": s3_nav_usd,
            "s4_nav_usd": s4_nav_usd,
            "s5_nav_usd": s5_nav_usd,
            "s6_nav_usd": s6_nav_usd,
            "s8_nav_usd": s8_nav_usd,
            "s9_nav_usd": s9_nav_usd,
            "s10_nav_usd": s10_nav_usd,
            "s11_nav_usd": s11_nav_usd,
            "total_nav_usd": total_combined_usd
        })
        
    try:
        with open(history_json_path, 'w', encoding='utf-8') as f:
            json.dump(all_history, f, indent=2)
    except Exception as e:
        print(f"Error saving all strategies history: {e}")

    history_md_path = os.path.join(dir_path, "all_strategies_allocation_history.md")
    md_lines = [
        "# All Strategies Allocation History\n",
        "| Date | Strategy 1 (MXN Value) | Strategy 2 (1d MACD) | Strategy 3 (US Momentum) | Strategy 4 (US DCS) | Strategy 5 (Alternatives) | Strategy 6 (High-Beta) | Strategy 8 (Dividends) | Strategy 9 (AI Arb) | Strategy 10 (Intraday) | Strategy 11 (CCI-ADX) | Total Combined NAV (USD) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
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
            pct8 = (entry.get("s8_nav_usd", 0.0) / nav) * 100.0
            pct9 = (entry.get("s9_nav_usd", 0.0) / nav) * 100.0
            pct10 = (entry.get("s10_nav_usd", 0.0) / nav) * 100.0
            pct11 = (entry.get("s11_nav_usd", 0.0) / nav) * 100.0
        else:
            pct1 = pct2 = pct3 = pct4 = pct5 = pct6 = pct8 = pct9 = pct10 = pct11 = 0.0
            
        md_lines.append(f"| {date} | {pct1:.1f}% | {pct2:.1f}% | {pct3:.1f}% | {pct4:.1f}% | {pct5:.1f}% | {pct6:.1f}% | {pct8:.1f}% | {pct9:.1f}% | {pct10:.1f}% | {pct11:.1f}% | ${nav:,.2f} |")
        
    try:
        with open(history_md_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(md_lines) + "\n")
        print(f"All strategies allocation history saved to {history_md_path}")
    except Exception as e:
        print(f"Error saving all strategies allocation history: {e}")

if __name__ == "__main__":
    main()
