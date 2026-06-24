import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
from skills.us_dcf_valuation import calculate_us_dcs

US_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX", "AMD", "JPM"]

# Fetch data
data = yf.download(US_UNIVERSE, period="1y", interval="1d", group_by='ticker', progress=False)

# US 10Y Yield
tnx = yf.download("^TNX", period="5d", progress=False)
if isinstance(tnx.columns, pd.MultiIndex):
    tnx.columns = tnx.columns.get_level_values(0)
rf_rate = float(tnx["Close"].iloc[-1]) / 100.0

print("="*80)
print(f"DEBUG CANDIDATES (Risk-Free Rate: {rf_rate*100:.2f}%)")
print("="*80)
print(f"{'Ticker':6} | {'Price':8} | {'SMA100':8} | {'DCS':7} | {'DCS>=0.15':9} | {'Price>SMA100':12} | {'Candidate'}")
print("-"*80)

for ticker in US_UNIVERSE:
    try:
        hist = data[ticker].dropna(how='all')
        hist.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in hist.columns]
        
        close = float(hist["close"].iloc[-1])
        sma_100 = float(hist["close"].rolling(window=100).mean().iloc[-1])
        
        dcf_res = calculate_us_dcs(ticker, close, rf_rate)
        dcs = float(dcf_res["margin_of_safety"])
        
        dcs_ok = dcs >= 0.15
        trend_ok = close > sma_100
        is_candidate = dcs_ok and trend_ok
        
        print(f"{ticker:6} | ${close:7.2f} | ${sma_100:7.2f} | {dcs:+.1%} | {str(dcs_ok):9} | {str(trend_ok):12} | {is_candidate}")
    except Exception as e:
        print(f"{ticker:6} | Failed: {e}")
print("="*80)
