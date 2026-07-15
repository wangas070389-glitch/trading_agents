import os
import datetime
import numpy as np
import pandas as pd

# Deposit parameters
INITIAL_DEPOSIT = 100000.0
MONTHLY_DEPOSIT = 2000.0
QUARTERLY_DEPOSIT = 4000.0
SEMI_ANNUAL_DEPOSIT = 20000.0
YEARLY_DEPOSIT = 50000.0
SIM_YEARS = 3
SIM_MONTHS = SIM_YEARS * 12

# Strategy CAGRs to simulate
STRATEGIES = {
    "Cash Sweep (Bondia)": 0.0653,
    "S21: Shannon Entropy": 0.1085,
    "S7: Core Hybrid Portfolio": 0.1850, # USD S7 CAGR translated to MXN
    "S22: Walk-Forward ML": 0.2113,
    "S19: Particle Filter": 0.2192,
    "S20: Hurst Exponent": 0.2429,
    "S2: 1d MACD (Alt - Conservative Projection)": 0.2500, # Capped S2 for realistic expectations
    "S2: 1d MACD (Alt - Historical CAGR)": 0.5606  # Full S2 historical CAGR
}

def run_simulation(cagr):
    # Compounding factor per month
    monthly_rate = (1.0 + cagr) ** (1.0 / 12.0) - 1.0
    
    balance = 0.0
    total_deposited = 0.0
    
    # Track monthly balances for projection curves
    history = []
    
    # Month 0: Initial Deposit
    balance += INITIAL_DEPOSIT
    total_deposited += INITIAL_DEPOSIT
    history.append((0, total_deposited, balance))
    
    for m in range(1, SIM_MONTHS + 1):
        # 1. Compound existing balance
        balance *= (1.0 + monthly_rate)
        
        # 2. Process deposits
        dep = 0.0
        # Monthly deposit
        dep += MONTHLY_DEPOSIT
        # Quarterly deposit (every 3 months)
        if m % 3 == 0:
            dep += QUARTERLY_DEPOSIT
        # Semi-annual deposit (every 6 months)
        if m % 6 == 0:
            dep += SEMI_ANNUAL_DEPOSIT
        # Yearly deposit (every 12 months)
        if m % 12 == 0:
            dep += YEARLY_DEPOSIT
            
        balance += dep
        total_deposited += dep
        history.append((m, total_deposited, balance))
        
    return total_deposited, balance, history

def main():
    results = []
    all_histories = {}
    
    for name, cagr in STRATEGIES.items():
        total_dep, final_bal, history = run_simulation(cagr)
        profit = final_bal - total_dep
        roi = (profit / total_dep) * 100.0
        results.append({
            "name": name,
            "cagr": cagr,
            "total_dep": total_dep,
            "final_bal": final_bal,
            "profit": profit,
            "roi": roi
        })
        all_histories[name] = history
        
    df_res = pd.DataFrame(results).sort_values(by="final_bal", ascending=False)
    
    # Generate Markdown report
    report = []
    report.append("# Capital Accumulation & Compounding Simulation Report")
    report.append(f"**Report Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\nThis simulation models the growth of your capital over the next **3 years (36 months)** under your custom deposit schedule:")
    report.append("\n* **Initial Deposit (Month 0):** $100,000 MXN")
    report.append("* **Monthly Deposit:** +$2,000 MXN")
    report.append("* **Quarterly (every 3 months) Deposit:** +$4,000 MXN")
    report.append("* **Semi-annual (every 6 months) Deposit:** +$20,000 MXN")
    report.append("* **Annual (every 12 months) Deposit:** +$50,000 MXN")
    
    # Show principal details
    total_deposited_calc = (
        INITIAL_DEPOSIT + 
        (MONTHLY_DEPOSIT * SIM_MONTHS) + 
        (QUARTERLY_DEPOSIT * (SIM_MONTHS // 3)) + 
        (SEMI_ANNUAL_DEPOSIT * (SIM_MONTHS // 6)) + 
        (YEARLY_DEPOSIT * (SIM_MONTHS // 12))
    )
    report.append(f"\n### 1. Cumulative Principal Contribution Breakdown")
    report.append(f"* **Initial Capital:** $100,000.00 MXN")
    report.append(f"* **Monthly Contributions (36 x $2k):** $72,000.00 MXN")
    report.append(f"* **Quarterly Contributions (12 x $4k):** $48,000.00 MXN")
    report.append(f"* **Semi-Annual Contributions (6 x $20k):** $120,000.00 MXN")
    report.append(f"* **Annual Contributions (3 x $50k):** $150,000.00 MXN")
    report.append(f"* **Total Capital Deposited over 3 Years:** **${total_deposited_calc:,.2f} MXN**")
    
    report.append("\n### 2. 3-Year Strategy Projections Grid")
    report.append("| Rank & Strategy | CAGR % | Total Principal | Projected Final NAV | Total Net Profit | Estimated ROI % |")
    report.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    
    for i, row in enumerate(df_res.itertuples(), 1):
        report.append(f"| **{i}. {row.name}** | {row.cagr*100:.2f}% | ${row.total_dep:,.2f} | **${row.final_bal:,.2f}** | ${row.profit:,.2f} | {row.roi:.2f}% |")
        
    report.append("\n### 3. Detailed Month-by-Month Balance Projection Table")
    report.append("This table compares the cash sweep baseline, Strategy 7 (Core Hybrid), Strategy 20 (Hurst), and Strategy 22 (Walk-Forward ML) at key milestones:")
    report.append("| Month | Total Principal | Cash Sweep NAV | S7 Core NAV | S22 ML NAV | S20 Hurst NAV |")
    report.append("| :---: | :---: | :---: | :---: | :---: | :---: |")
    
    milestones = [0, 6, 12, 18, 24, 30, 36]
    for m in milestones:
        p_val = all_histories["Cash Sweep (Bondia)"][m][1]
        cash_val = all_histories["Cash Sweep (Bondia)"][m][2]
        s7_val = all_histories["S7: Core Hybrid Portfolio"][m][2]
        s22_val = all_histories["S22: Walk-Forward ML"][m][2]
        s20_val = all_histories["S20: Hurst Exponent"][m][2]
        report.append(f"| **M{m:02d}** | ${p_val:,.2f} | ${cash_val:,.2f} | ${s7_val:,.2f} | ${s22_val:,.2f} | ${s20_val:,.2f} |")
        
    report.append("\n### 4. Strategic Analysis & Takeaways")
    report.append("1. **The Power of Dollar-Cost Averaging (DCA)**: By continuously injecting fresh capital into S22 or S20, you dynamically buy more shares of QQQ/TQQQ/SQQQ during market drawdowns, accelerating compounding once the market recovers.")
    report.append("2. **Core S7 vs. Satellite S20/S22**: S7 Core Hybrid represents your 'safe harbor' projection ($644k NAV, $154k profit). It does not experience the sharp drawdown swings of S20/S22. Allocating 80% to S7 and 20% divided between S20 and S22 creates a highly optimized blended path.")
    report.append("3. **MACD S2 Warning**: S2's historical CAGR of 56.06% yields an astronomical $937k NAV. However, over a 3-year horizon, maintaining a 56% Sharpe-efficient CAGR is mathematically rare. The capped **25% projection** ($702k NAV, $212k profit) is a safer planning anchor.")
    
    report_md_content = "\n".join(report)
    
    brain_path = "C:\\Users\\wanga\\.gemini\\antigravity-ide\\brain\\d60a4064-8913-4b11-ad45-c2212800287f"
    report_file_path = os.path.join(brain_path, "deposit_simulation_report.md")
    
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(report_md_content)
        
    print(f"Simulation report written successfully to: {report_file_path}")

if __name__ == "__main__":
    main()
