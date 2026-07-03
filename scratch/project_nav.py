import pandas as pd

# Conversion rate
USD_MXN = 17.43

# Strategies details
# S1-S11, S7
# Initial NAV, CAGR, Monthly PMT (in native currency)
strategies = {
    "S1": {"name": "Adaptive Dynamic Value", "nav": 21003.73, "cagr": 0.2007, "pmt": 2000.0, "currency": "MXN"},
    "S2": {"name": "1d MACD Systematic", "nav": 19870.70, "cagr": 0.1310, "pmt": 0.0, "currency": "MXN"},
    "S3": {"name": "US Stock Momentum", "nav": 199212.58, "cagr": 0.2540, "pmt": 0.0, "currency": "USD"},
    "S4": {"name": "US DCS Value-Growth", "nav": 99647.84, "cagr": 0.2193, "pmt": 0.0, "currency": "USD"},
    "S5": {"name": "Alternative Assets", "nav": 101252.07, "cagr": 0.1840, "pmt": 0.0, "currency": "USD"},
    "S6": {"name": "High-Beta Momentum", "nav": 101036.96, "cagr": 0.2210, "pmt": 0.0, "currency": "USD"},
    "S8": {"name": "Dividend Quality", "nav": 200633.22, "cagr": 0.1450, "pmt": 2000.0, "currency": "MXN"},
    "S9": {"name": "AI Regime Stat-Arb", "nav": 197811.07, "cagr": 0.2680, "pmt": 2000.0, "currency": "MXN"},
    "S10": {"name": "AI Intraday VWAP", "nav": 200000.78, "cagr": 0.3090, "pmt": 2000.0, "currency": "MXN"},
    "S11": {"name": "AI Intraday CCI-ADX", "nav": 200000.38, "cagr": 0.3250, "pmt": 2000.0, "currency": "MXN"},
    "S7": {"name": "Consolidated Core", "nav": 348958.69, "cagr": 0.1563, "pmt": 114.75, "currency": "USD"} # USD pmt = 2000 / 17.43
}

def project(nav, cagr, pmt, years):
    # Monthly compounding projection
    monthly_rate = (1 + cagr) ** (1/12) - 1
    months = int(years * 12)
    val = nav
    for _ in range(months):
        val = val * (1 + monthly_rate) + pmt
    return val

print("| Strategy ID & Name | Native Currency | Current Live NAV | 1-Year Projected NAV | 5-Year Projected NAV | 1-Year (USD) | 5-Year (USD) |")
print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

for sid, info in strategies.items():
    nav_1y = project(info["nav"], info["cagr"], info["pmt"], 1)
    nav_5y = project(info["nav"], info["cagr"], info["pmt"], 5)
    
    usd_curr = info["nav"] if info["currency"] == "USD" else info["nav"] / USD_MXN
    usd_1y = nav_1y if info["currency"] == "USD" else nav_1y / USD_MXN
    usd_5y = nav_5y if info["currency"] == "USD" else nav_5y / USD_MXN
    
    print(f"| **{sid}: {info['name']}** | {info['currency']} | {info['nav']:,.2f} | {nav_1y:,.2f} | {nav_5y:,.2f} | ${usd_1y:,.2f} | ${usd_5y:,.2f} |")
