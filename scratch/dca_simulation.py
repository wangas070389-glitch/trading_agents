import pandas as pd

def run_dca_simulation():
    months = 60
    initial = 20000.0
    monthly_contrib = 2000.0
    
    # CAGR assumptions based on backtest data
    cagrs = {
        "Mattress Cash (0% APR)": 0.00,
        "Bondia Cash (11% APR)": 0.11,
        "Active Value Equity - Standard (5.12% CAGR)": 0.0512,
        "Active Value Equity - Aggressive (7.71% CAGR)": 0.0771,
        "Active Value Equity - Adaptive (14.09% CAGR)": 0.1409,
        "MACD Single-Asset (2.17% CAGR)": 0.0217,
        "MACD Multi-Asset (14.54% CAGR)": 0.1454,
        "SPY Buy & Hold (14.38% CAGR)": 0.1438
    }
    
    results = []
    
    for name, cagr in cagrs.items():
        balance = initial
        total_contributed = initial
        
        # Monthly return rate
        r_monthly = (1.0 + cagr) ** (1.0 / 12.0) - 1.0
        
        history = [balance]
        for m in range(1, months + 1):
            # Add contribution at the beginning of the month
            balance += monthly_contrib
            total_contributed += monthly_contrib
            
            # Compound interest at the end of the month
            balance *= (1.0 + r_monthly)
            history.append(balance)
            
        profit = balance - total_contributed
        results.append({
            "Strategy": name,
            "Total Contributed": total_contributed,
            "Final Balance": round(balance, 2),
            "Total Profit (MXN)": round(profit, 2),
            "ROI %": round((profit / total_contributed) * 100, 2)
        })
        
    print("| Strategy | Total Contributed | Final Balance | Total Profit (MXN) | ROI % |")
    print("| :--- | :---: | :---: | :---: | :---: |")
    for r in results:
        print(f"| {r['Strategy']} | ${r['Total Contributed']:,.2f} | ${r['Final Balance']:,.2f} | ${r['Total Profit (MXN)']:,.2f} | {r['ROI %']}% |")

if __name__ == "__main__":
    run_dca_simulation()
