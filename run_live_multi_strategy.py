import os
import sys
import json
import datetime
import yfinance as yf
import numpy as np
import pandas as pd

# Target allocations
W_S4, W_S1, W_S6, W_S5 = 0.40, 0.30, 0.20, 0.10

PORTFOLIO_FILE = "portfolio_multi_strategy.json"
REPORT_FILE = "multi_strategy_report_live.md"
CSV_FILE = "consolidated_portfolio_nav.csv"

def get_nav(portfolio_data):
    if not portfolio_data:
        return 0.0, 0.0
    cash = float(portfolio_data.get("cash_balance", 0.0))
    holdings_val = sum(float(h.get("shares", 0.0)) * float(h.get("last_price", h.get("buy_price", 0.0))) for h in portfolio_data.get("holdings", []))
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

    s1_data = None
    s4_data = None
    s5_data = None
    s6_data = None

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

    # Calculate individual NAVs in local currencies
    s1_nav_mxn, s1_cash_mxn = get_nav(s1_data)
    s4_nav_usd, s4_cash_usd = get_nav(s4_data)
    s5_nav_usd, s5_cash_usd = get_nav(s5_data)
    s6_nav_usd, s6_cash_usd = get_nav(s6_data)

    # Convert S1 (MXN) to USD
    s1_nav_usd = s1_nav_mxn / usd_mxn_rate
    s1_cash_usd = s1_cash_mxn / usd_mxn_rate

    # Consolidated totals (USD)
    total_nav_usd = s1_nav_usd + s4_nav_usd + s5_nav_usd + s6_nav_usd
    total_cash_usd = s1_cash_usd + s4_cash_usd + s5_cash_usd + s6_cash_usd

    # Compute weights
    w1_curr = s1_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0
    w4_curr = s4_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0
    w5_curr = s5_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0
    w6_curr = s6_nav_usd / total_nav_usd if total_nav_usd > 0 else 0.0

    print("\nCurrent NAV Breakdown:")
    print(f"  S1 (MXN Value):     ${s1_nav_usd:,.2f} USD ({w1_curr*100:.1f}% vs Target 30.0%)")
    print(f"  S4 (US DCS):        ${s4_nav_usd:,.2f} USD ({w4_curr*100:.1f}% vs Target 40.0%)")
    print(f"  S5 (Alternatives):  ${s5_nav_usd:,.2f} USD ({w5_curr*100:.1f}% vs Target 10.0%)")
    print(f"  S6 (High-Beta):     ${s6_nav_usd:,.2f} USD ({w6_curr*100:.1f}% vs Target 20.0%)")
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
            
            # S1 (MXN Value Inflow 2000 MXN)
            inflow_1_usd = (2000.0 / usd_mxn_rate) if is_new_month else 0.0
            # S4, S5, S6 (USD Inflows 1000 USD each)
            inflow_4_usd = 1000.0 if is_new_month else 0.0
            inflow_5_usd = 1000.0 if is_new_month else 0.0
            inflow_6_usd = 1000.0 if is_new_month else 0.0
            
            # Compute daily returns
            r1 = (s1_nav_usd - inflow_1_usd) / last_entry["s1_nav_usd"] - 1.0 if last_entry.get("s1_nav_usd", 0) > 0 else 0.0
            r4 = (s4_nav_usd - inflow_4_usd) / last_entry["s4_nav_usd"] - 1.0 if last_entry.get("s4_nav_usd", 0) > 0 else 0.0
            r5 = (s5_nav_usd - inflow_5_usd) / last_entry["s5_nav_usd"] - 1.0 if last_entry.get("s5_nav_usd", 0) > 0 else 0.0
            r6 = (s6_nav_usd - inflow_6_usd) / last_entry["s6_nav_usd"] - 1.0 if last_entry.get("s6_nav_usd", 0) > 0 else 0.0
            
            # Combined R7
            r7_today = (W_S4 * r4) + (W_S1 * r1) + (W_S6 * r6) + (W_S5 * r5)
            print(f"Calculated Today's Returns: R1={r1*100:.2f}%, R4={r4*100:.2f}%, R5={r5*100:.2f}%, R6={r6*100:.2f}% | Blended R7={r7_today*100:.2f}%")
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
                "s6_nav_usd": s6_nav_usd
            })

    # Update meta values
    state["total_portfolio_value_usd"] = total_nav_usd
    state["total_cash_balance_usd"] = total_cash_usd
    state["usd_mxn_rate"] = usd_mxn_rate
    state["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    state["allocations"] = {
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

    # 6. Generate report
    report_md = f"""# Strategy 7 (Consolidated Multi-Strategy) Daily Execution Report
**Execution Date:** {today_str} | **Orchestrator Version:** Live V1

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
| **Strategy 4: US DCS Value-Growth** | {W_S4*100:.1f}% | {w4_curr*100:.1f}% | {(w4_curr - W_S4)*100:+.1f}% | ${s4_nav_usd:,.2f} |
| **Strategy 1: MXN Dynamic Value** | {W_S1*100:.1f}% | {w1_curr*100:.1f}% | {(w1_curr - W_S1)*100:+.1f}% | ${s1_nav_usd:,.2f} |
| **Strategy 6: US High-Beta Momentum** | {W_S6*100:.1f}% | {w6_curr*100:.1f}% | {(w6_curr - W_S6)*100:+.1f}% | ${s6_nav_usd:,.2f} |
| **Strategy 5: Alternatives (Crypto/Forex/ETFs)** | {W_S5*100:.1f}% | {w5_curr*100:.1f}% | {(w5_curr - W_S5)*100:+.1f}% | ${s5_nav_usd:,.2f} |

---
*Generated by daily orchestrator at {state["last_updated"]}*
"""
    with open(os.path.join(dir_path, REPORT_FILE), 'w', encoding='utf-8') as f:
        f.write(report_md)

    # 7. Generate allocation history report
    history_md_path = os.path.join(dir_path, "multi_strategy_allocation_history.md")
    history_lines = [
        "# Consolidated Multi-Strategy Allocation History\n",
        "| Date | Strategy 1 (MXN Value) | Strategy 4 (US DCS) | Strategy 5 (Alternatives) | Strategy 6 (High-Beta) | Total NAV (USD) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    # Sort history entries descending (newest first)
    sorted_history = sorted(state.get("history", []), key=lambda x: x["date"], reverse=True)
    for entry in sorted_history:
        date = entry["date"]
        nav = entry["nav_usd"]
        if nav > 0:
            pct1 = (entry["s1_nav_usd"] / nav) * 100.0
            pct4 = (entry["s4_nav_usd"] / nav) * 100.0
            pct5 = (entry["s5_nav_usd"] / nav) * 100.0
            pct6 = (entry["s6_nav_usd"] / nav) * 100.0
        else:
            pct1 = pct4 = pct5 = pct6 = 0.0
            
        history_lines.append(f"| {date} | {pct1:.1f}% | {pct4:.1f}% | {pct5:.1f}% | {pct6:.1f}% | ${nav:,.2f} |")
        
    with open(history_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(history_lines) + "\n")
    print(f"Saved allocation history to {history_md_path}")

    print(f"\nConsolidated execution complete! Saved report to {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
