import argparse

def simulate_investment(years, annual_rate):
    # Initial parameters
    balance = 20000.0  # Initial 20K MXN
    total_contributed = 20000.0
    
    # Monthly compounding rate
    monthly_rate = (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0
    
    # Iterate month by month
    for month in range(1, years * 12 + 1):
        # 1. Accrue interest for the month
        balance *= (1.0 + monthly_rate)
        
        # 2. Inflows at the end of the month
        inflow = 0.0
        
        # Adding 2K each month
        inflow += 2000.0
        
        # Adding 5K each 3rd month (month 3, 6, 9, 12, ...)
        if month % 3 == 0:
            inflow += 5000.0
            
        # Adding 20K each 6th month (month 6, 12, 18, ...)
        if month % 6 == 0:
            inflow += 20000.0
            
        # Adding 50K each year (month 12, 24, 36, ...)
        if month % 12 == 0:
            inflow += 50000.0
            
        balance += inflow
        total_contributed += inflow
        
    return balance, total_contributed

def main():
    scenarios = [
        ("0% Cash (Pure Savings)", 0.00),
        ("6.53% APR (Daily Sweep)", 0.0653),
        ("11.00% APR (Bondia Cash)", 0.11),
        ("15.63% CAGR (Strategy 2/Hybrid)", 0.1563),
        ("20.07% CAGR (Strategy 1/Core)", 0.2007),
        ("31.32% CAGR (Strategy 4/US DCS)", 0.3132)
    ]
    
    horizons = [1, 3, 5, 10]
    
    print("=" * 100)
    print("SIMULATING INVESTMENT PLAN (Initial: 20K MXN)")
    print("Inflows: +2K/month, +5K/qtr (3mo), +20K/semi-annual (6mo), +50K/annual (12mo)")
    print("=" * 100)
    
    for label, rate in scenarios:
        print(f"\nScenario: {label} (Return: {rate*100:.2f}%)")
        print(f"{'Years':6} | {'Total Contributed':18} | {'Future Portfolio Value':24} | {'Total Growth (Profit)':22} | {'ROI %'}")
        print("-" * 85)
        for y in horizons:
            val, contrib = simulate_investment(y, rate)
            profit = val - contrib
            roi = (profit / contrib) * 100.0 if contrib > 0 else 0.0
            print(f"{y:5}y | ${contrib:16,.2f} | ${val:22,.2f} | ${profit:20,.2f} | {roi:+.2f}%")
        print("=" * 85)

if __name__ == "__main__":
    main()
