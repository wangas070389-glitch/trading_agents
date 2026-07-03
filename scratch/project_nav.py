import os
import sys

def project_nav(initial_capital, monthly_dca, cagr, months):
    nav = initial_capital
    total_injected = initial_capital
    monthly_rate = (1.0 + cagr) ** (1.0 / 12.0) - 1.0
    
    for m in range(1, months + 1):
        # compound previous balance
        nav = nav * (1.0 + monthly_rate)
        # inject monthly savings
        nav += monthly_dca
        total_injected += monthly_dca
        
    net_profit = nav - total_injected
    return nav, total_injected, net_profit

def main():
    print("=" * 80)
    print("PORTFOLIO NAV PROJECTION SIMULATOR (1-YEAR & 5-YEARS)")
    print("=" * 80)
    
    # USD/MXN exchange rate
    usd_mxn = 17.42
    
    # Strategy settings
    # ID: (Name, Initial Capital, Monthly DCA, CAGR, Currency)
    strategies = {
        "S1": ("MXN Dynamic Value", 20000.0, 2000.0, 0.1852, "MXN"),
        "S2": ("1d MACD Systematic", 20000.0, 2000.0, 0.1245, "MXN"),
        "S3": ("US Momentum (Isolated)", 100000.0, 1000.0, 0.2410, "USD"),
        "S4": ("US DCS Value-Growth", 100000.0, 1000.0, 0.2840, "USD"),
        "S5": ("Alternative Assets", 100000.0, 1000.0, 0.0410, "USD"),
        "S6": ("High-Beta Momentum", 100000.0, 1000.0, 0.1480, "USD"),
        "S8": ("Dividend Quality", 200000.0, 2000.0, 0.1632, "MXN"),
        "S9": ("AI Regime Stat-Arb", 200000.0, 2000.0, 0.1592, "MXN"),
        "S10": ("AI Intraday VWAP", 200000.0, 2000.0, 0.2540, "MXN"),
        "S7": ("Consolidated Multi-Strategy", 337495.51, 3459.24, 0.1680, "USD")
    }
    
    print(f"Using USD/MXN rate: {usd_mxn}")
    print("\n" + "-" * 80)
    print("1-YEAR NAV SIMULATION (12 MONTHS)")
    print("-" * 80)
    print(f"{'ID & Strategy Name':<30} | {'Total Injected':<18} | {'Projected NAV':<18} | {'Net Profit':<15} | Curr")
    print("-" * 80)
    
    for s_id, (name, init, dca, cagr, curr) in strategies.items():
        nav, injected, profit = project_nav(init, dca, cagr, 12)
        print(f"{s_id:<4} {name:<25} | {curr} {injected:,.2f} | {curr} {nav:,.2f} | {curr} {profit:,.2f} | {curr}")
        
    print("\n" + "-" * 80)
    print("5-YEAR NAV SIMULATION (60 MONTHS)")
    print("-" * 80)
    print(f"{'ID & Strategy Name':<30} | {'Total Injected':<18} | {'Projected NAV':<18} | {'Net Profit':<15} | Curr")
    print("-" * 80)
    
    for s_id, (name, init, dca, cagr, curr) in strategies.items():
        nav, injected, profit = project_nav(init, dca, cagr, 60)
        print(f"{s_id:<4} {name:<25} | {curr} {injected:,.2f} | {curr} {nav:,.2f} | {curr} {profit:,.2f} | {curr}")
        
    print("=" * 80)

if __name__ == "__main__":
    main()
