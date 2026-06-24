import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf
from skills.us_dcf_valuation import calculate_us_dcs

US_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX", "AMD", "JPM"]

# Fetch current prices
data = yf.download(US_UNIVERSE, period="5d", group_by='ticker', progress=False)

# US 10Y Yield
tnx = yf.download("^TNX", period="5d", progress=False)
if isinstance(tnx.columns, pd.MultiIndex):
    tnx.columns = tnx.columns.get_level_values(0)
rf_rate = float(tnx["Close"].iloc[-1]) / 100.0

print("="*60)
print(f"DEBUG DCS VALUATION (Risk-Free Rate: {rf_rate*100:.2f}%)")
print("="*60)
print(f"{'Ticker':6} | {'Price':8} | {'Intrinsic':9} | {'DCS':7} | {'Conviction'}")
print("-"*60)

for ticker in US_UNIVERSE:
    try:
        close = float(data[ticker]["Close"].iloc[-1])
        dcf_res = calculate_us_dcs(ticker, close, rf_rate)
        intrinsic = dcf_res["intrinsic_value"]
        dcs = dcf_res["margin_of_safety"]
        conviction = dcs >= 0.15
        print(f"{ticker:6} | ${close:7.2f} | ${intrinsic:8.2f} | {dcs:+.1%} | {conviction}")
    except Exception as e:
        print(f"{ticker:6} | Failed: {e}")
print("="*60)
