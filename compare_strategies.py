import os
import json
import math
import datetime

def valuation_price(h):
    """Best available price for valuing a holding: last_price when it is a
    finite positive number, otherwise fall back to buy_price. Protects the
    report from NaN last_price values written while markets were closed."""
    for key in ("last_price", "buy_price"):
        try:
            px = float(h.get(key, 0.0))
            if math.isfinite(px) and px > 0:
                return px
        except (TypeError, ValueError):
            continue
    return 0.0

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
    portfolio_strategy12_path = os.path.join(dir_path, "portfolio_strategy12.json")
    portfolio_strategy13_path = os.path.join(dir_path, "portfolio_strategy13.json")
    portfolio_strategy14_path = os.path.join(dir_path, "portfolio_strategy14.json")
    portfolio_strategy15_path = os.path.join(dir_path, "portfolio_strategy15.json")
    portfolio_strategy16_path = os.path.join(dir_path, "portfolio_strategy16.json")
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
    port_strategy12 = load_json(portfolio_strategy12_path)
    port_strategy13 = load_json(portfolio_strategy13_path)
    port_strategy14 = load_json(portfolio_strategy14_path)
    port_strategy15 = load_json(portfolio_strategy15_path)
    port_strategy16 = load_json(portfolio_strategy16_path)
    port_multi_strategy = load_json(portfolio_multi_strategy_path)
    usd_mxn_rate = port_multi_strategy.get("usd_mxn_rate", 17.43) if port_multi_strategy else 17.43
    try:
        usd_mxn_rate = float(usd_mxn_rate)
        if not (math.isfinite(usd_mxn_rate) and usd_mxn_rate > 0):
            usd_mxn_rate = 17.43
    except (TypeError, ValueError):
        usd_mxn_rate = 17.43
    
    if not port_val and not port_macd and not port_us and not port_us_dcs and not port_alternatives and not port_high_beta and not port_dividends and not port_strategy9 and not port_strategy10 and not port_strategy11 and not port_strategy12 and not port_strategy13 and not port_strategy14 and not port_strategy15 and not port_strategy16 and not port_multi_strategy:
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
    s1_market_val = s1_cash = s1_invested = 0.0
    if port_val:
        v_total_cap = port_val.get("total_capital", 20000.0)
        s1_cash = port_val.get("cash_balance", 20000.0)
        s1_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_val.get("holdings", []))
        s1_market_val = s1_cash + sum(h["shares"] * valuation_price(h) for h in port_val.get("holdings", []))
        v_profit = s1_market_val - v_total_cap
        v_roi = (v_profit / v_total_cap) * 100.0
        v_alloc = (s1_invested / s1_market_val) * 100.0 if s1_market_val > 0 else 0.0
        v_sign = "+" if v_profit >= 0 else ""
        report.append(f"| **Adaptive Dynamic Value (S1)** | ${s1_market_val:,.2f} | ${s1_cash:,.2f} | ${s1_invested:,.2f} | {v_alloc:.1f}% | {v_sign}${v_profit:,.2f} | {v_sign}{v_roi:.2f}% | 2026-06-03 | MXN |")
    else:
        report.append("| **Adaptive Dynamic Value (S1)** | *Not Initialized* | - | - | - | - | - | - | MXN |")
        
    # Parse S2
    s2_market_val = s2_cash = s2_invested = 0.0
    if port_macd:
        m_total_cap = port_macd.get("total_capital", 20000.0)
        s2_cash = port_macd.get("cash_balance", 20000.0)
        s2_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_macd.get("holdings", []))
        s2_market_val = s2_cash + sum(h["shares"] * valuation_price(h) for h in port_macd.get("holdings", []))
        m_profit = s2_market_val - m_total_cap
        m_roi = (m_profit / m_total_cap) * 100.0
        m_alloc = (s2_invested / s2_market_val) * 100.0 if s2_market_val > 0 else 0.0
        m_sign = "+" if m_profit >= 0 else ""
        report.append(f"| **1d MACD Systematic (S2)** | ${s2_market_val:,.2f} | ${s2_cash:,.2f} | ${s2_invested:,.2f} | {m_alloc:.1f}% | {m_sign}${m_profit:,.2f} | {m_sign}{m_roi:.2f}% | 2026-06-03 | MXN |")
    else:
        report.append("| **1d MACD Systematic (S2)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S3
    s3_market_val = s3_cash = s3_invested = 0.0
    if port_us:
        u_total_cap = port_us.get("total_capital", 100000.0)
        s3_cash = port_us.get("cash_balance", 100000.0)
        s3_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_us.get("holdings", []))
        s3_market_val = s3_cash + sum(h["shares"] * valuation_price(h) for h in port_us.get("holdings", []))
        u_profit = s3_market_val - u_total_cap
        u_roi = (u_profit / u_total_cap) * 100.0
        u_alloc = (s3_invested / s3_market_val) * 100.0 if s3_market_val > 0 else 0.0
        u_sign = "+" if u_profit >= 0 else ""
        report.append(f"| **US Stock Momentum (S3)** | ${s3_market_val:,.2f} | ${s3_cash:,.2f} | ${s3_invested:,.2f} | {u_alloc:.1f}% | {u_sign}${u_profit:,.2f} | {u_sign}{u_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **US Stock Momentum (S3)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    # Parse S4
    s4_market_val = s4_cash = s4_invested = 0.0
    if port_us_dcs:
        ud_total_cap = port_us_dcs.get("total_capital", 100000.0)
        s4_cash = port_us_dcs.get("cash_balance", 100000.0)
        s4_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_us_dcs.get("holdings", []))
        s4_market_val = s4_cash + sum(h["shares"] * valuation_price(h) for h in port_us_dcs.get("holdings", []))
        ud_profit = s4_market_val - ud_total_cap
        ud_roi = (ud_profit / ud_total_cap) * 100.0
        ud_alloc = (s4_invested / s4_market_val) * 100.0 if s4_market_val > 0 else 0.0
        ud_sign = "+" if ud_profit >= 0 else ""
        report.append(f"| **US DCS Value-Growth (S4)** | ${s4_market_val:,.2f} | ${s4_cash:,.2f} | ${s4_invested:,.2f} | {ud_alloc:.1f}% | {ud_sign}${ud_profit:,.2f} | {ud_sign}{ud_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **US DCS Value-Growth (S4)** | *Not Initialized* | - | - | - | - | - | - | USD |")
        
    # Parse S5
    s5_market_val = s5_cash = s5_invested = 0.0
    if port_alternatives:
        a_total_cap = port_alternatives.get("total_capital", 100000.0)
        s5_cash = port_alternatives.get("cash_balance", 100000.0)
        s5_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_alternatives.get("holdings", []))
        s5_market_val = s5_cash + sum(h["shares"] * valuation_price(h) for h in port_alternatives.get("holdings", []))
        a_profit = s5_market_val - a_total_cap
        a_roi = (a_profit / a_total_cap) * 100.0
        a_alloc = (s5_invested / s5_market_val) * 100.0 if s5_market_val > 0 else 0.0
        a_sign = "+" if a_profit >= 0 else ""
        report.append(f"| **Alternative Assets (S5)** | ${s5_market_val:,.2f} | ${s5_cash:,.2f} | ${s5_invested:,.2f} | {a_alloc:.1f}% | {a_sign}${a_profit:,.2f} | {a_sign}{a_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **Alternative Assets (S5)** | *Not Initialized* | - | - | - | - | - | - | USD |")

    # Parse S6
    s6_market_val = s6_cash = s6_invested = 0.0
    if port_high_beta:
        h_total_cap = port_high_beta.get("total_capital", 100000.0)
        s6_cash = port_high_beta.get("cash_balance", 100000.0)
        s6_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_high_beta.get("holdings", []))
        s6_market_val = s6_cash + sum(h["shares"] * valuation_price(h) for h in port_high_beta.get("holdings", []))
        h_profit = s6_market_val - h_total_cap
        h_roi = (h_profit / h_total_cap) * 100.0
        h_alloc = (s6_invested / s6_market_val) * 100.0 if s6_market_val > 0 else 0.0
        h_sign = "+" if h_profit >= 0 else ""
        report.append(f"| **High-Beta Momentum (S6)** | ${s6_market_val:,.2f} | ${s6_cash:,.2f} | ${s6_invested:,.2f} | {h_alloc:.1f}% | {h_sign}${h_profit:,.2f} | {h_sign}{h_roi:.2f}% | 2026-06-23 | USD |")
    else:
        report.append("| **High-Beta Momentum (S6)** | *Not Initialized* | - | - | - | - | - | - | USD |")

    # Parse S8
    s8_market_val = s8_cash = s8_invested = 0.0
    if port_dividends:
        div_total_cap = port_dividends.get("total_capital", 200000.0)
        s8_cash = port_dividends.get("cash_balance", 200000.0)
        s8_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_dividends.get("holdings", []))
        s8_market_val = s8_cash + sum(h["shares"] * valuation_price(h) for h in port_dividends.get("holdings", []))
        div_profit = s8_market_val - div_total_cap
        div_roi = (div_profit / div_total_cap) * 100.0
        div_alloc = (s8_invested / s8_market_val) * 100.0 if s8_market_val > 0 else 0.0
        div_sign = "+" if div_profit >= 0 else ""
        report.append(f"| **Dividend Quality (S8)** | ${s8_market_val:,.2f} | ${s8_cash:,.2f} | ${s8_invested:,.2f} | {div_alloc:.1f}% | {div_sign}${div_profit:,.2f} | {div_sign}{div_roi:.2f}% | 2026-06-25 | MXN |")
    else:
        report.append("| **Dividend Quality (S8)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S9
    s9_market_val = s9_cash = s9_invested = 0.0
    if port_strategy9:
        s9_total_cap = 200000.0
        s9_cash = port_strategy9.get("cash_balance", 200000.0)
        s9_invested = sum(float(h.get("allocated", h["shares"] * h["buy_price"])) for h in port_strategy9.get("holdings", []))
        s9_market_val = s9_cash + sum(h["shares"] * valuation_price(h) for h in port_strategy9.get("holdings", []) if "shares" in h)
        s9_profit = s9_market_val - s9_total_cap
        s9_roi = (s9_profit / s9_total_cap) * 100.0
        s9_alloc = (s9_invested / s9_market_val) * 100.0 if s9_market_val > 0 else 0.0
        s9_sign = "+" if s9_profit >= 0 else ""
        report.append(f"| **AI Regime Stat-Arb (S9)** | ${s9_market_val:,.2f} | ${s9_cash:,.2f} | ${s9_invested:,.2f} | {s9_alloc:.1f}% | {s9_sign}${s9_profit:,.2f} | {s9_sign}{s9_roi:.2f}% | 2026-06-30 | MXN |")
    else:
        report.append("| **AI Regime Stat-Arb (S9)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S10
    s10_market_val = s10_cash = s10_invested = 0.0
    if port_strategy10:
        s10_total_cap = 200000.0
        s10_cash = port_strategy10.get("cash_balance", 200000.0)
        s10_invested = sum(float(h.get("allocated", h["shares"] * h["buy_price"])) for h in port_strategy10.get("holdings", []))
        s10_market_val = s10_cash
        for h in port_strategy10.get("holdings", []):
            if h.get("side", "long") == "long":
                s10_market_val += h["shares"] * valuation_price(h)
            else:
                s10_market_val += h["allocated"] + (h["allocated"] - h["shares"] * valuation_price(h))
        s10_profit = s10_market_val - s10_total_cap
        s10_roi = (s10_profit / s10_total_cap) * 100.0
        s10_alloc = (s10_invested / s10_market_val) * 100.0 if s10_market_val > 0 else 0.0
        s10_sign = "+" if s10_profit >= 0 else ""
        report.append(f"| **AI Intraday VWAP (S10)** | ${s10_market_val:,.2f} | ${s10_cash:,.2f} | ${s10_invested:,.2f} | {s10_alloc:.1f}% | {s10_sign}${s10_profit:,.2f} | {s10_sign}{s10_roi:.2f}% | 2026-07-02 | MXN |")
    else:
        report.append("| **AI Intraday VWAP (S10)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S11
    s11_market_val = s11_cash = s11_invested = 0.0
    if port_strategy11:
        s11_total_cap = 200000.0
        s11_cash = port_strategy11.get("cash_balance", 200000.0)
        s11_invested = sum(float(h.get("allocated", h["shares"] * h["buy_price"])) for h in port_strategy11.get("holdings", []))
        s11_market_val = s11_cash
        for h in port_strategy11.get("holdings", []):
            if h.get("side", "long") == "long":
                s11_market_val += h["shares"] * valuation_price(h)
            else:
                s11_market_val += h["allocated"] + (h["allocated"] - h["shares"] * valuation_price(h))
        s11_profit = s11_market_val - s11_total_cap
        s11_roi = (s11_profit / s11_total_cap) * 100.0
        s11_alloc = (s11_invested / s11_market_val) * 100.0 if s11_market_val > 0 else 0.0
        s11_sign = "+" if s11_profit >= 0 else ""
        report.append(f"| **AI Intraday CCI-ADX (S11)** | ${s11_market_val:,.2f} | ${s11_cash:,.2f} | ${s11_invested:,.2f} | {s11_alloc:.1f}% | {s11_sign}${s11_profit:,.2f} | {s11_sign}{s11_roi:.2f}% | 2026-07-02 | MXN |")
    else:
        report.append("| **AI Intraday CCI-ADX (S11)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S12
    s12_market_val = s12_cash = s12_invested = 0.0
    if port_strategy12:
        s12_total_cap = 200000.0
        s12_cash = port_strategy12.get("cash_balance", 200000.0)
        s12_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_strategy12.get("holdings", []))
        s12_market_val = s12_cash + sum(h["shares"] * valuation_price(h) for h in port_strategy12.get("holdings", []))
        s12_profit = s12_market_val - s12_total_cap
        s12_roi = (s12_profit / s12_total_cap) * 100.0
        s12_alloc = (s12_invested / s12_market_val) * 100.0 if s12_market_val > 0 else 0.0
        s12_sign = "+" if s12_profit >= 0 else ""
        report.append(f"| **VTTL Trend-Carry (S12)** | ${s12_market_val:,.2f} | ${s12_cash:,.2f} | ${s12_invested:,.2f} | {s12_alloc:.1f}% | {s12_sign}${s12_profit:,.2f} | {s12_sign}{s12_roi:.2f}% | 2026-07-06 | MXN |")
    else:
        report.append("| **VTTL Trend-Carry (S12)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S13
    s13_market_val = s13_cash = s13_invested = 0.0
    if port_strategy13:
        s13_total_cap = 200000.0
        s13_cash_mxn = port_strategy13.get("cash_balance_mxn", 200000.0)
        s13_cash_usd = port_strategy13.get("cash_balance_usd", 0.0)
        # We will parse exchange rate from multi-strategy or use default 17.43 to evaluate S13 cash_usd
        rate_temp = port_multi_strategy.get("usd_mxn_rate", 17.43) if port_multi_strategy else 17.43
        s13_cash = s13_cash_mxn + s13_cash_usd * rate_temp
        
        s13_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_strategy13.get("holdings", []))
        s13_market_val = s13_cash + sum(h["shares"] * valuation_price(h) for h in port_strategy13.get("holdings", []))
        s13_profit = s13_market_val - s13_total_cap
        s13_roi = (s13_profit / s13_total_cap) * 100.0
        s13_alloc = (s13_invested / s13_market_val) * 100.0 if s13_market_val > 0 else 0.0
        s13_sign = "+" if s13_profit >= 0 else ""
        report.append(f"| **CARA Cross-Asset (S13)** | ${s13_market_val:,.2f} | ${s13_cash:,.2f} | ${s13_invested:,.2f} | {s13_alloc:.1f}% | {s13_sign}${s13_profit:,.2f} | {s13_sign}{s13_roi:.2f}% | 2026-07-06 | MXN |")
    else:
        report.append("| **CARA Cross-Asset (S13)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S14
    s14_market_val = s14_cash = s14_invested = 0.0
    if port_strategy14:
        s14_total_cap = 200000.0
        s14_cash_mxn = port_strategy14.get("cash_balance_mxn", 200000.0)
        s14_cash_usd = port_strategy14.get("cash_balance_usd", 0.0)
        s14_cash = s14_cash_mxn + s14_cash_usd * usd_mxn_rate
        s14_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_strategy14.get("holdings", []))
        s14_market_val = s14_cash + sum(h["shares"] * valuation_price(h) for h in port_strategy14.get("holdings", []))
        s14_profit = s14_market_val - s14_total_cap
        s14_roi = (s14_profit / s14_total_cap) * 100.0
        s14_alloc = (s14_invested / s14_market_val) * 100.0 if s14_market_val > 0 else 0.0
        s14_sign = "+" if s14_profit >= 0 else ""
        report.append(f"| **HEDGE Aggregator (S14)** | ${s14_market_val:,.2f} | ${s14_cash:,.2f} | ${s14_invested:,.2f} | {s14_alloc:.1f}% | {s14_sign}${s14_profit:,.2f} | {s14_sign}{s14_roi:.2f}% | 2026-07-06 | MXN |")
    else:
        report.append("| **HEDGE Aggregator (S14)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S15
    s15_market_val = s15_cash = s15_invested = 0.0
    if port_strategy15:
        s15_total_cap = 200000.0
        s15_cash_mxn = port_strategy15.get("cash_balance_mxn", 200000.0)
        s15_cash_usd = port_strategy15.get("cash_balance_usd", 0.0)
        s15_cash = s15_cash_mxn + s15_cash_usd * usd_mxn_rate
        s15_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_strategy15.get("holdings", []))
        s15_market_val = s15_cash + sum(h["shares"] * valuation_price(h) for h in port_strategy15.get("holdings", []))
        s15_profit = s15_market_val - s15_total_cap
        s15_roi = (s15_profit / s15_total_cap) * 100.0
        s15_alloc = (s15_invested / s15_market_val) * 100.0 if s15_market_val > 0 else 0.0
        s15_sign = "+" if s15_profit >= 0 else ""
        report.append(f"| **TRACK Tracker (S15)** | ${s15_market_val:,.2f} | ${s15_cash:,.2f} | ${s15_invested:,.2f} | {s15_alloc:.1f}% | {s15_sign}${s15_profit:,.2f} | {s15_sign}{s15_roi:.2f}% | 2026-07-06 | MXN |")
    else:
        report.append("| **TRACK Tracker (S15)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse S16
    s16_market_val = s16_cash = s16_invested = 0.0
    if port_strategy16:
        s16_total_cap = 200000.0
        s16_cash = port_strategy16.get("cash_balance", 200000.0)
        s16_invested = sum(h["shares"] * h.get("buy_price", 0.0) for h in port_strategy16.get("holdings", []))
        s16_market_val = s16_cash + sum(h["shares"] * valuation_price(h) for h in port_strategy16.get("holdings", []))
        s16_profit = s16_market_val - s16_total_cap
        s16_roi = (s16_profit / s16_total_cap) * 100.0
        s16_alloc = (s16_invested / s16_market_val) * 100.0 if s16_market_val > 0 else 0.0
        s16_sign = "+" if s16_profit >= 0 else ""
        report.append(f"| **HMM Intraday Router (S16)** | ${s16_market_val:,.2f} | ${s16_cash:,.2f} | ${s16_invested:,.2f} | {s16_alloc:.1f}% | {s16_sign}${s16_profit:,.2f} | {s16_sign}{s16_roi:.2f}% | 2026-07-07 | MXN |")
    else:
        report.append("| **HMM Intraday Router (S16)** | *Not Initialized* | - | - | - | - | - | - | MXN |")

    # Parse Strategy 7 (Consolidated Multi-Strategy)
    ms_val = float(port_multi_strategy.get("total_portfolio_value_usd", 0.0)) if port_multi_strategy else 0.0
    if port_multi_strategy and math.isfinite(ms_val) and ms_val > 0:
        ms_cash = port_multi_strategy.get("total_cash_balance_usd", 0.0)
        ms_invested = ms_val - ms_cash
        
        # historical return reference
        perf = port_multi_strategy.get("performance", {})
        cagr = perf.get("cagr", 0.0)
        sharpe = perf.get("sharpe_ratio", 0.0)
        max_dd = perf.get("max_drawdown", 0.0)
        
        # S7 initial capital reference is now updated to include new strategies initial base
        # S11 (200k), S10 (200k), S9 (200k), S4 (100k), S1 (20k), S8 (200k), S12 (200k), S13 (200k), S14 (200k), S15 (200k), S6 (100k), S5 (100k)
        # Total Initial Capital = 1,920,000 MXN / 17.43 = $110,154.91 USD
        # Let's dynamically sum up initial capital if needed or check existing.
        incept_capital = 337495.51 + (800000.0 / usd_mxn_rate)
        profit_usd = ms_val - incept_capital
        roi_ms = (profit_usd / incept_capital) * 100.0 if ms_val > 0 else 0.0
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
    
    # Ingest today's rates (already defined at top)
    # usd_mxn_rate is defined above
    
    
    # Calculate local conversions
    s1_nav_usd = s1_market_val / usd_mxn_rate
    s2_nav_usd = s2_market_val / usd_mxn_rate
    s3_nav_usd = s3_market_val
    s4_nav_usd = s4_market_val
    s5_nav_usd = s5_market_val
    s6_nav_usd = s6_market_val
    s8_nav_usd = s8_market_val / usd_mxn_rate
    s9_nav_usd = s9_market_val / usd_mxn_rate
    s10_nav_usd = s10_market_val / usd_mxn_rate
    s11_nav_usd = s11_market_val / usd_mxn_rate
    s12_nav_usd = s12_market_val / usd_mxn_rate
    s13_nav_usd = s13_market_val / usd_mxn_rate
    s14_nav_usd = s14_market_val / usd_mxn_rate
    s15_nav_usd = s15_market_val / usd_mxn_rate
    
    total_combined_usd = (s1_nav_usd + s2_nav_usd + s3_nav_usd + s4_nav_usd + s5_nav_usd + s6_nav_usd + 
                          s8_nav_usd + s9_nav_usd + s10_nav_usd + s11_nav_usd + s12_nav_usd + s13_nav_usd + 
                          s14_nav_usd + s15_nav_usd)
    
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
            "s12_nav_usd": s12_nav_usd,
            "s13_nav_usd": s13_nav_usd,
            "s14_nav_usd": s14_nav_usd,
            "s15_nav_usd": s15_nav_usd,
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
        "| Date | Strategy 1 | Strategy 2 | Strategy 3 | Strategy 4 | Strategy 5 | Strategy 6 | Strategy 8 | Strategy 9 | Strategy 10 | Strategy 11 | Strategy 12 | Strategy 13 | Strategy 14 | Strategy 15 | Total Combined NAV (USD) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    sorted_all_history = sorted(all_history, key=lambda x: x["date"], reverse=True)
    for entry in sorted_all_history:
        date = entry["date"]
        nav = entry["total_nav_usd"]
        if nav > 0:
            pct1 = (entry.get("s1_nav_usd", 0.0) / nav) * 100.0
            pct2 = (entry.get("s2_nav_usd", 0.0) / nav) * 100.0
            pct3 = (entry.get("s3_nav_usd", 0.0) / nav) * 100.0
            pct4 = (entry.get("s4_nav_usd", 0.0) / nav) * 100.0
            pct5 = (entry.get("s5_nav_usd", 0.0) / nav) * 100.0
            pct6 = (entry.get("s6_nav_usd", 0.0) / nav) * 100.0
            pct8 = (entry.get("s8_nav_usd", 0.0) / nav) * 100.0
            pct9 = (entry.get("s9_nav_usd", 0.0) / nav) * 100.0
            pct10 = (entry.get("s10_nav_usd", 0.0) / nav) * 100.0
            pct11 = (entry.get("s11_nav_usd", 0.0) / nav) * 100.0
            pct12 = (entry.get("s12_nav_usd", 0.0) / nav) * 100.0
            pct13 = (entry.get("s13_nav_usd", 0.0) / nav) * 100.0
            pct14 = (entry.get("s14_nav_usd", 0.0) / nav) * 100.0
            pct15 = (entry.get("s15_nav_usd", 0.0) / nav) * 100.0
        else:
            pct1 = pct2 = pct3 = pct4 = pct5 = pct6 = pct8 = pct9 = pct10 = pct11 = pct12 = pct13 = pct14 = pct15 = 0.0
            
        md_lines.append(f"| {date} | {pct1:.1f}% | {pct2:.1f}% | {pct3:.1f}% | {pct4:.1f}% | {pct5:.1f}% | {pct6:.1f}% | {pct8:.1f}% | {pct9:.1f}% | {pct10:.1f}% | {pct11:.1f}% | {pct12:.1f}% | {pct13:.1f}% | {pct14:.1f}% | {pct15:.1f}% | ${nav:,.2f} |")
        
    try:
        with open(history_md_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(md_lines) + "\n")
        print(f"All strategies allocation history saved to {history_md_path}")
    except Exception as e:
        print(f"Error saving all strategies allocation history: {e}")

if __name__ == "__main__":
    main()

