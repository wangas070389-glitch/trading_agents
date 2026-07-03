import os
import sys
import json
import datetime
import yfinance as yf
import numpy as np
import pandas as pd

# Target allocations
W_S10, W_S9, W_S4, W_S1, W_S8, W_S6, W_S5 = 0.15, 0.20, 0.20, 0.15, 0.15, 0.10, 0.05

PORTFOLIO_FILE = "portfolio_multi_strategy.json"
REPORT_FILE = "multi_strategy_report_live.md"
CSV_FILE = "consolidated_portfolio_nav.csv"

def get_nav(portfolio_data):
    if not portfolio_data:
        return 0.0, 0.0
    cash = float(portfolio_data.get("cash_balance", 0.0))
    holdings_val = 0.0
    for h in portfolio_data.get("holdings", []):
        if "shares" in h:
            holdings_val += float(h["shares"]) * float(h.get("last_price", h.get("buy_price", 0.0)))
        elif "last_price" in h:
            holdings_val += float(h.get("last_price", h.get("buy_price", 0.0)))
    return cash + holdings_val, cash

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    print("=" * 80)
    print(f"LIVE ORCHESTRATOR: CONSOLIDATED MULTI-STRATEGY PORTFOLIO ({today_str})")
    print("=" * 80)

    # 1. Fetch USDMXN Exchange Rate
    print("Downloading USDMXN=X exchange rate...")
    usd_mxn_rate = 18.25 # fallback
    try:
        fx = yf.download("USDMXN=X", period="5d", progress=False)
        fx.columns = [c if isinstance(c, str) else c[0] for c in fx.columns]
        usd_mxn_rate = float(fx["Close"].iloc[-1])
        print(f"  USD/MXN Exchange Rate: {usd_mxn_rate:.4f}")
    except Exception as e:
        print(f"  [WARN] Failed to download USDMXN exchange rate: {e}. Using fallback {usd_mxn_rate:.4f}")

    # 2. Load individual strategy portfolio tracking files
    s1_path = os.path.join(dir_path, "portfolio.json")
    s4_path = os.path.join(dir_path, "portfolio_us_dcs.json")
    s5_path = os.path.join(dir_path, "portfolio_alternatives.json")
    s6_path = os.path.join(dir_path, "portfolio_high_beta.json")
    s8_path = os.path.join(dir_path, "portfolio_dividends.json")
    s9_path = os.path.join(dir_path, "portfolio_strategy9.json")
    s10_path = os.path.join(dir_path, "portfolio_strategy10.json")

    s1_data = None
    s4_data = None
    s5_data = None
    s6_data = None
    s8_data = None
    s9_data = None
    s10_data = None

    if os.path.exists(s1_path):
        with open(s1_path, 'r', encoding='utf-8') as f:
            s1_data = json.load(f)
    if os.path.exists(s4_path):
        with open(s4_path, 'r', encoding='utf-8') as f:
            s4_data = json.load(f)
    if os.path.exists(s5_path):
        with open(s5_path, 'r', encoding='utf-8') as f:
            s5_data = json.load(f)
    if os.path.exists(s6_path):
        with open(s6_path, 'r', encoding='utf-8') as f:
            s6_data = json.load(f)
    if os.path.exists(s8_path):
        with open(s8_path, 'r', encoding='utf-8') as f:
            s8_data = json.load(f)
    if os.path.exists(s9_path):
        with open(s9_path, 'r', encoding='utf-8') as f:
            s9_data = json.load(f)
    if os.path.exists(s10_path):
        with open(s10_path, 'r', encoding='utf-8') as f:
            s10_data = json.load(f)

    # Calculate individual NAVs in local currencies
    s1_nav_mxn, s1_cash_mxn = get_nav(s1_data)
    s4_nav_usd, s4_cash_usd = get_nav(s4_data)
    s5_nav_usd, s5_cash_usd = get_nav(s5_data)
    s6_nav_usd, s6_cash_usd = get_nav(s6_data)
    s8_nav_mxn, s8_cash_mxn = get_nav(s8_data)
    s9_nav_mxn, s9_cash_mxn = get_nav(s9_data)
    s10_nav_mxn, s10_cash_mxn = get_nav(s10_data)

    # Convert S1, S8, S9, S10 (MXN) to USD
    s1_nav_usd = s1_nav_mxn / usd_mxn_rate
    s1_cash_usd = s1_cash_mxn / usd_mxn_rate
    s8_nav_usd = s8_nav_mxn / usd_mxn_rate
    s8_cash_usd = s8_cash_mxn / usd_mxn_rate
    s9_nav_usd = s9_nav_mxn / usd_mxn_rate
    s9_cash_usd = s9_cash_mxn / usd_mxn_rate
    s10_nav_usd = s10_nav_mxn / usd_mxn_rate
    s10_cash_usd = s10_cash_mxn / usd_mxn_rate

    # Consolidated totals (USD)
    total_nav_usd = s1_nav_usd + s4_nav_usd + s5_nav_usd + s6_nav_usd + s8_nav_usd + s9_nav_usd + s10_nav_usd
    total_cash_usd = s1_cash_usd + s4_cash_usd + s5_cash_usd + s6_cash_usd + s8_cash_usd + s9_cash_usd + s10_cash_usd

    # Compute weights
    w1_curr = s1_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0
    w4_curr = s4_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0
    w5_curr = s5_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0
    w6_curr = s6_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0
    w8_curr = s8_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0
    w9_curr = s9_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0
    w10_curr = s10_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0

    print("\nCurrent NAV Breakdown:")
    print(f"  S10 (Intraday VWAP):${s10_nav_usd:,.2f} USD ({w10_curr*100:.1f}% vs Target 15.0%)")
    print(f"  S9 (AI Stat Arb):   ${s9_nav_usd:,.2f} USD ({w9_curr*100:.1f}% vs Target 20.0%)")
    print(f"  S4 (US DCS):        ${s4_nav_usd:,.2f} USD ({w4_curr*100:.1f}% vs Target 20.0%)")
    print(f"  S1 (MXN Value):     ${s1_nav_usd:,.2f} USD ({w1_curr*100:.1f}% vs Target 15.0%)")
    print(f"  S8 (Div Quality):   ${s8_nav_usd:,.2f} USD ({w8_curr*100:.1f}% vs Target 15.0%)")
    print(f"  S6 (High-Beta):     ${s6_nav_usd:,.2f} USD ({w6_curr*100:.1f}% vs Target 10.0%)")
    print(f"  S5 (Alternatives):  ${s5_nav_usd:,.2f} USD ({w5_curr*100:.1f}% vs Target 5.0%)")
    print(f"  Total Portfolio:    ${total_nav_usd:,.2f} USD")

    # 3. Load Multi-Strategy portfolio state
    state_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {
            "total_portfolio_value_usd": total_nav_usd,
            "total_cash_balance_usd": total_cash_usd,
            "last_updated": today_str + " 00:00:00",
            "usd_mxn_rate": usd_mxn_rate,
            "history": []
        }

    # Calculate returns R7 today if we have history
    r7_today = 0.0
    is_new_day = False
    
    if state.get("history"):
        last_entry = state["history"][-1]
        last_date_str = last_entry["date"]
        
        if last_date_str != today_str:
            is_new_day = True
            last_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d").date()
            today_date = datetime.date.today()
            
            # Detect monthly savings inflows on month transition
            is_new_month = today_date.year > last_date.year or (today_date.year == last_date.year and today_date.month > last_date.month)
            
            # S1, S8, S9, S10 (MXN Value Inflows 2000 MXN each)
            inflow_1_usd = (2000.0 / usd_mxn_rate) if is_new_month else 0.0
            inflow_8_usd = (2000.0 / usd_mxn_rate) if is_new_month else 0.0
            inflow_9_usd = (2000.0 / usd_mxn_rate) if is_new_month else 0.0
            inflow_10_usd = (2000.0 / usd_mxn_rate) if is_new_month else 0.0
            # S4, S5, S6 (USD Inflows 1000 USD each)
            inflow_4_usd = 1000.0 if is_new_month else 0.0
            inflow_5_usd = 1000.0 if is_new_month else 0.0
            inflow_6_usd = 1000.0 if is_new_month else 0.0
            
            # Compute daily returns
            r1 = (s1_nav_usd - inflow_1_usd) / last_entry["s1_nav_usd"] - 1.0 if last_entry.get("s1_nav_usd", 0) > 0 else 0.0
            r4 = (s4_nav_usd - inflow_4_usd) / last_entry["s4_nav_usd"] - 1.0 if last_entry.get("s4_nav_usd", 0) > 0 else 0.0
            r5 = (s5_nav_usd - inflow_5_usd) / last_entry["s5_nav_usd"] - 1.0 if last_entry.get("s5_nav_usd", 0) > 0 else 0.0
            r6 = (s6_nav_usd - inflow_6_usd) / last_entry["s6_nav_usd"] - 1.0 if last_entry.get("s6_nav_usd", 0) > 0 else 0.0
            r8 = (s8_nav_usd - inflow_8_usd) / last_entry.get("s8_nav_usd", s8_nav_usd) - 1.0 if last_entry.get("s8_nav_usd", 0) > 0 else 0.0
            r9 = (s9_nav_usd - inflow_9_usd) / last_entry.get("s9_nav_usd", s9_nav_usd) - 1.0 if last_entry.get("s9_nav_usd", 0) > 0 else 0.0
            r10 = (s10_nav_usd - inflow_10_usd) / last_entry.get("s10_nav_usd", s10_nav_usd) - 1.0 if last_entry.get("s10_nav_usd", 0) > 0 else 0.0
            
            # Combined R7
            r7_today = (W_S10 * r10) + (W_S4 * r4) + (W_S1 * r1) + (W_S6 * r6) + (W_S5 * r5) + (W_S8 * r8) + (W_S9 * r9)
            print(f"Calculated Returns: R10={r10*100:.2f}%, R9={r9*100:.2f}%, R4={r4*100:.2f}%, R1={r1*100:.2f}%, R8={r8*100:.2f}%, R6={r6*100:.2f}% | R7={r7_today*100:.2f}%")
    else:
        # First entry initialization
        is_new_day = True
        r7_today = 0.0

    # 4. Update consolidated CSV curve
    csv_path = os.path.join(dir_path, CSV_FILE)
    if os.path.exists(csv_path):
        df_csv = pd.read_csv(csv_path)
    else:
        print("  [WARN] consolidated_portfolio_nav.csv not found in root. Run consolidated backtest first.")
        df_csv = pd.DataFrame(columns=["Date", "CumTWR", "R7"])

    # Align dates
    if not df_csv.empty:
        df_csv["Date"] = pd.to_datetime(df_csv["Date"])
        last_csv_date = df_csv["Date"].iloc[-1].date()
        today_date = datetime.date.today()
        
        if last_csv_date < today_date:
            last_cumtwr = float(df_csv["CumTWR"].iloc[-1])
            new_cumtwr = last_cumtwr * (1.0 + r7_today)
            
            new_row = pd.DataFrame({
                "Date": [pd.to_datetime(today_str)],
                "CumTWR": [new_cumtwr],
                "R7": [r7_today]
            })
            df_csv = pd.concat([df_csv, new_row], ignore_index=True)
            df_csv.to_csv(csv_path, index=False)
            print(f"  Appended today's performance to consolidated_portfolio_nav.csv. New CumTWR: {new_cumtwr:.4f}")
    else:
        # Initialize CSV
        df_csv = pd.DataFrame({
            "Date": [pd.to_datetime(today_str)],
            "CumTWR": [1.0],
            "R7": [0.0]
        })
        df_csv.to_csv(csv_path, index=False)

    # 5. Compute overall updated performance statistics
    df_csv["Date"] = pd.to_datetime(df_csv["Date"])
    days = (df_csv["Date"].iloc[-1] - df_csv["Date"].iloc[0]).days
    years = max(days / 365.25, 0.01)
    
    cum_twr = df_csv["CumTWR"].iloc[-1]
    cagr = (cum_twr) ** (1.0 / years) - 1.0
    
    # Sharpe (assumed risk-free rate 4.5% sweep)
    excess_returns = df_csv["R7"] - (0.045 / 252.0)
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0.0
    
    # Max DD
    running_max = df_csv["CumTWR"].cummax()
    drawdowns = (df_csv["CumTWR"] - running_max) / running_max
    max_dd = drawdowns.min()

    # Update state history
    if is_new_day or not state.get("history"):
        # Prevent double adding on same date
        if not state.get("history") or state["history"][-1]["date"] != today_str:
            state["history"].append({
                "date": today_str,
                "nav_usd": total_nav_usd,
                "cash_usd": total_cash_usd,
                "s1_nav_usd": s1_nav_usd,
                "s4_nav_usd": s4_nav_usd,
                "s5_nav_usd": s5_nav_usd,
                "s6_nav_usd": s6_nav_usd,
                "s8_nav_usd": s8_nav_usd,
                "s9_nav_usd": s9_nav_usd,
                "s10_nav_usd": s10_nav_usd
            })

    # Update meta values
    state["total_portfolio_value_usd"] = total_nav_usd
    state["total_cash_balance_usd"] = total_cash_usd
    state["usd_mxn_rate"] = usd_mxn_rate
    state["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    state["allocations"] = {
        "strategy_10_intraday_vwap": {
            "nav_usd": s10_nav_usd,
            "nav_mxn": s10_nav_mxn,
            "current_weight": w10_curr,
            "target_weight": W_S10,
            "deviation": w10_curr - W_S10
        },
        "strategy_9_ai_arb": {
            "nav_usd": s9_nav_usd,
            "nav_mxn": s9_nav_mxn,
            "current_weight": w9_curr,
            "target_weight": W_S9,
            "deviation": w9_curr - W_S9
        },
        "strategy_1_mxn_value": {
            "nav_usd": s1_nav_usd,
            "nav_mxn": s1_nav_mxn,
            "current_weight": w1_curr,
            "target_weight": W_S1,
            "deviation": w1_curr - W_S1
        },
        "strategy_4_us_dcs": {
            "nav_usd": s4_nav_usd,
            "current_weight": w4_curr,
            "target_weight": W_S4,
            "deviation": w4_curr - W_S4
        },
        "strategy_8_dividend_quality": {
            "nav_usd": s8_nav_usd,
            "nav_mxn": s8_nav_mxn,
            "current_weight": w8_curr,
            "target_weight": W_S8,
            "deviation": w8_curr - W_S8
        },
        "strategy_5_alternatives": {
            "nav_usd": s5_nav_usd,
            "current_weight": w5_curr,
            "target_weight": W_S5,
            "deviation": w5_curr - W_S5
        },
        "strategy_6_high_beta": {
            "nav_usd": s6_nav_usd,
            "current_weight": w6_curr,
            "target_weight": W_S6,
            "deviation": w6_curr - W_S6
        }
    }
    state["performance"] = {
        "cagr": cagr,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe,
        "cum_twr": cum_twr
    }

    # Save consolidated state JSON
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

    # 5.5. Construct Underlying Holdings detail tables
    holdings_md = "\n## 4. Underlying Strategy Holdings Detail\n"
    
    # Strategy 1 (MXN Value)
    holdings_md += "\n### A. Strategy 1: MXN Dynamic Value Holdings (MXN / USD)\n"
    if s1_data and s1_data.get("holdings"):
        holdings_md += "| Ticker | Shares Held | Buy Price (MXN) | Current Price (MXN) | Market Value (MXN) | Market Value (USD) | Strategy Weight |\n"
        holdings_md += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        for h in s1_data["holdings"]:
            ticker = h["ticker"]
            shares = float(h["shares"])
            buy_p = float(h["buy_price"])
            last_p = float(h.get("last_price", buy_p))
            mval_mxn = shares * last_p
            mval_usd = mval_mxn / usd_mxn_rate
            weight = mval_usd / s1_nav_usd if s1_nav_usd > 0 else 0.0
            holdings_md += f"| **{ticker}** | {shares:,.4f} | ${buy_p:,.2f} | ${last_p:,.2f} | ${mval_mxn:,.2f} | ${mval_usd:,.2f} | {weight:.1%} |\n"
    else:
        holdings_md += "*No open stock positions currently held. Strategy is 100% Cash / Bondia sweep.*\n"

    # Strategy 4 (US DCS)
    holdings_md += "\n### B. Strategy 4: US DCS Value-Growth Holdings (USD)\n"
    if s4_data and s4_data.get("holdings"):
        holdings_md += "| Ticker | Shares Held | Buy Price (USD) | Current Price (USD) | Market Value (USD) | Strategy Weight | DCS MOS |\n"
        holdings_md += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        for h in s4_data["holdings"]:
            ticker = h["ticker"]
            shares = float(h["shares"])
            buy_p = float(h["buy_price"])
            last_p = float(h.get("last_price", buy_p))
            mval_usd = shares * last_p
            weight = mval_usd / s4_nav_usd if s4_nav_usd > 0 else 0.0
            dcs = h.get("dcs", 0.0)
            holdings_md += f"| **{ticker}** | {shares:,.2f} | ${buy_p:,.2f} | ${last_p:,.2f} | ${mval_usd:,.2f} | {weight:.1%} | {dcs:.3f} |\n"
    else:
        holdings_md += "*No open stock positions currently held. Strategy is 100% Cash.*\n"

    # Strategy 6 (High-Beta)
    holdings_md += "\n### C. Strategy 6: US High-Beta Momentum Holdings (USD)\n"
    if s6_data and s6_data.get("holdings"):
        holdings_md += "| Ticker | Shares Held | Buy Price (USD) | Current Price (USD) | Market Value (USD) | Strategy Weight | DCS MOS | Beta |\n"
        holdings_md += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        for h in s6_data["holdings"]:
            ticker = h["ticker"]
            shares = float(h["shares"])
            buy_p = float(h["buy_price"])
            last_p = float(h.get("last_price", buy_p))
            mval_usd = shares * last_p
            weight = mval_usd / s6_nav_usd if s6_nav_usd > 0 else 0.0
            dcs = h.get("dcs", 0.0)
            beta = h.get("beta", 0.0)
            holdings_md += f"| **{ticker}** | {shares:,.4f} | ${buy_p:,.2f} | ${last_p:,.2f} | ${mval_usd:,.2f} | {weight:.1%} | {dcs:.3f} | {beta:.2f} |\n"
    else:
        holdings_md += "*No open stock positions currently held. Strategy is 100% Cash.*\n"

    # Strategy 5 (Alternatives)
    holdings_md += "\n### D. Strategy 5: Alternatives Holdings (USD)\n"
    if s5_data and s5_data.get("holdings"):
        holdings_md += "| Ticker | Asset Type | Shares Held | Buy Price (USD) | Current Price (USD) | Market Value (USD) | Strategy Weight |\n"
        holdings_md += "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |\n"
        for h in s5_data["holdings"]:
            ticker = h["ticker"]
            asset_type = h.get("asset_type", "N/A").upper()
            shares = float(h["shares"])
            buy_p = float(h["buy_price"])
            last_p = float(h.get("last_price", buy_p))
            mval_usd = shares * last_p
            weight = mval_usd / s5_nav_usd if s5_nav_usd > 0 else 0.0
            holdings_md += f"| **{ticker}** | {asset_type} | {shares:,.4f} | ${buy_p:,.2f} | ${last_p:,.2f} | ${mval_usd:,.2f} | {weight:.1%} |\n"
    else:
        holdings_md += "*No open positions currently held. Strategy is 100% Cash.*\n"

    # Strategy 8 (Dividends)
    holdings_md += "\n### E. Strategy 8: Dividend Quality & Yield Holdings (MXN / USD)\n"
    if s8_data and s8_data.get("holdings"):
        holdings_md += "| Ticker | Shares Held | Buy Price (Local) | Current Price (Local) | Market Value (MXN) | Market Value (USD) | Strategy Weight |\n"
        holdings_md += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        for h in s8_data["holdings"]:
            ticker = h["ticker"]
            shares = float(h["shares"])
            buy_p = float(h["buy_price"])
            last_p = float(h.get("last_price", buy_p))
            mval_mxn = shares * last_p
            mval_usd = mval_mxn / usd_mxn_rate
            weight = mval_usd / s8_nav_usd if s8_nav_usd > 0 else 0.0
            holdings_md += f"| **{ticker}** | {shares:,.4f} | ${buy_p:,.2f} | ${last_p:,.2f} | ${mval_mxn:,.2f} | ${mval_usd:,.2f} | {weight:.1%} |\n"
    else:
        holdings_md += "*No open stock positions currently held. Strategy is 100% Cash / Bondia sweep.*\n"

    # Strategy 9 (AI Arb)
    holdings_md += "\n### F. Strategy 9: AI-Regime Adaptive Stat-Arb Holdings (MXN / USD)\n"
    if s9_data and s9_data.get("holdings"):
        holdings_md += "| Ticker | Type | Qty Y | Qty X | Buy/Alloc | Last Value | Value (MXN) | Value (USD) |\n"
        holdings_md += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        for h in s9_data["holdings"]:
            ticker = h["ticker"]
            is_pair = ticker.startswith("PAIR:")
            buy_p = float(h["buy_price"])
            last_p = float(h.get("last_price", buy_p))
            
            qty_y = h.get("qty_y", 0.0) if is_pair else h.get("shares", 0.0)
            qty_x = h.get("qty_x", 0.0)
            
            mval_mxn = last_p
            if not is_pair:
                mval_mxn = qty_y * last_p
                
            mval_usd = mval_mxn / usd_mxn_rate
            
            type_str = "Pairs Spread" if is_pair else "Regime Asset"
            holdings_md += f"| **{ticker}** | {type_str} | {qty_y:.4f} | {qty_x:.4f} | ${buy_p:,.2f} | ${last_p:,.2f} | ${mval_mxn:,.2f} | ${mval_usd:,.2f} |\n"
    else:
        holdings_md += "*No open arbitrage positions or regime assets held. Strategy is 100% Cash / Bondia sweep.*\n"

    # Strategy 10 (Intraday VWAP)
    holdings_md += "\n### G. Strategy 10: AI Intraday VWAP Alpha Holdings (MXN / USD)\n"
    if s10_data and s10_data.get("holdings"):
        holdings_md += "| Ticker | Type | Side | Shares | Buy/Alloc | Last Price | Value (MXN) | Value (USD) |\n"
        holdings_md += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        for h in s10_data["holdings"]:
            ticker = h["ticker"]
            side = h.get("side", "long").upper()
            shares = h["shares"]
            buy_p = float(h["buy_price"])
            last_p = float(h.get("last_price", buy_p))
            
            if side == "LONG":
                mval_mxn = shares * last_p
            else:
                mval_mxn = h["allocated"] + (h["allocated"] - shares * last_p)
                
            mval_usd = mval_mxn / usd_mxn_rate
            holdings_md += f"| **{ticker}** | INTRADAY | {side} | {shares:.4f} | ${buy_p:,.2f} | ${last_p:,.2f} | ${mval_mxn:,.2f} | ${mval_usd:,.2f} |\n"
    else:
        holdings_md += "*No active intraday positions currently held. Strategy is 100% Cash / Bondia sweep (Positions squared off daily at 2:30 PM CST).*\n"

    # 6. Generate report
    report_md = f"""# Strategy 7 (Consolidated Multi-Strategy) Daily Execution Report
**Execution Date:** {today_str} | **Orchestrator Version:** Live V2

## 1. Consolidated Portfolio Summary
* **Total Portfolio Value (USD):** ${total_nav_usd:,.2f} USD
* **Total Unallocated Cash (USD):** ${total_cash_usd:,.2f} USD
* **Currency Rate (USD/MXN):** {usd_mxn_rate:.4f}
* **Combined Cumulative Return (TWR Multiplier):** {cum_twr:.4f} ({((cum_twr - 1.0)*100):+.2f}%)

## 2. Multi-Strategy Performance Statistics (Historical + Live)
* **Strategy 7 CAGR:** {cagr*100:.2f}%
* **Strategy 7 Sharpe Ratio:** {sharpe:.2f}
* **Strategy 7 Maximum Drawdown:** {max_dd*100:.2f}%

## 3. Allocation Target Deviation
| Strategy Component | Target Allocation % | Current Allocation % | Deviation % | Current Value (USD) |
| :--- | :---: | :---: | :---: | :---: |
| **Strategy 10: AI Intraday VWAP** | {W_S10*100:.1f}% | {w10_curr*100:.1f}% | {(w10_curr - W_S10)*100:+.1f}% | ${s10_nav_usd:,.2f} |
| **Strategy 9: AI Stat-Arb & Regime** | {W_S9*100:.1f}% | {w9_curr*100:.1f}% | {(w9_curr - W_S9)*100:+.1f}% | ${s9_nav_usd:,.2f} |
| **Strategy 4: US DCS Value-Growth** | {W_S4*100:.1f}% | {w4_curr*100:.1f}% | {(w4_curr - W_S4)*100:+.1f}% | ${s4_nav_usd:,.2f} |
| **Strategy 1: MXN Dynamic Value** | {W_S1*100:.1f}% | {w1_curr*100:.1f}% | {(w1_curr - W_S1)*100:+.1f}% | ${s1_nav_usd:,.2f} |
| **Strategy 8: Dividend Quality & Yield** | {W_S8*100:.1f}% | {w8_curr*100:.1f}% | {(w8_curr - W_S8)*100:+.1f}% | ${s8_nav_usd:,.2f} |
| **Strategy 6: US High-Beta Momentum** | {W_S6*100:.1f}% | {w6_curr*100:.1f}% | {(w6_curr - W_S6)*100:+.1f}% | ${s6_nav_usd:,.2f} |
| **Strategy 5: Alternatives (Crypto/Forex/ETFs)** | {W_S5*100:.1f}% | {w5_curr*100:.1f}% | {(w5_curr - W_S5)*100:+.1f}% | ${s5_nav_usd:,.2f} |

{holdings_md}
---
*Generated by daily orchestrator at {state["last_updated"]}*
"""
    with open(os.path.join(dir_path, REPORT_FILE), 'w', encoding='utf-8') as f:
        f.write(report_md)

    # 7. Generate allocation history report
    history_md_path = os.path.join(dir_path, "multi_strategy_allocation_history.md")
    history_lines = [
        "# Consolidated Multi-Strategy Allocation History\n",
        "| Date | Strategy 10 (Intraday) | Strategy 9 (AI Arb) | Strategy 1 (MXN Value) | Strategy 4 (US DCS) | Strategy 8 (Dividends) | Strategy 5 (Alternatives) | Strategy 6 (High-Beta) | Total NAV (USD) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    sorted_history = sorted(state.get("history", []), key=lambda x: x["date"], reverse=True)
    for entry in sorted_history:
        date = entry["date"]
        nav = entry["nav_usd"]
        if nav > 0:
            pct10 = (entry.get("s10_nav_usd", 0.0) / nav) * 100.0
            pct9 = (entry.get("s9_nav_usd", 0.0) / nav) * 100.0
            pct1 = (entry["s1_nav_usd"] / nav) * 100.0
            pct4 = (entry["s4_nav_usd"] / nav) * 100.0
            pct8 = (entry.get("s8_nav_usd", 0.0) / nav) * 100.0
            pct5 = (entry["s5_nav_usd"] / nav) * 100.0
            pct6 = (entry["s6_nav_usd"] / nav) * 100.0
        else:
            pct10 = pct9 = pct1 = pct4 = pct8 = pct5 = pct6 = 0.0
            
        history_lines.append(f"| {date} | {pct10:.1f}% | {pct9:.1f}% | {pct1:.1f}% | {pct4:.1f}% | {pct8:.1f}% | {pct5:.1f}% | {pct6:.1f}% | ${nav:,.2f} |")
        
    with open(history_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(history_lines) + "\n")
    print(f"Saved allocation history to {history_md_path}")
    print(f"Saved allocation history to {history_md_path}")

    print(f"\nConsolidated execution complete! Saved report to {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
