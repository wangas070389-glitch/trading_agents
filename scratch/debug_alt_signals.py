import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
from skills.alternative_indicators import evaluate_signals

def main():
    tickers = ["BTC-USD", "GLD", "EURUSD=X"]
    start_date = "2021-06-20"
    end_date = "2026-06-20"
    
    print("Downloading data for debugging...")
    data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', progress=False)
    
    for t in tickers:
        print("\n" + "="*50)
        print(f"DEBUGGING SIGNALS FOR {t}")
        print("="*50)
        
        hist = data[t].dropna(how='all')
        hist.columns = [c.lower() for c in hist.columns]
        
        if t == "BTC-USD":
            asset_type = "crypto"
        elif t == "GLD":
            asset_type = "commodity"
        else:
            asset_type = "forex"
            
        print(f"Total days: {len(hist)}")
        
        buy_signals = 0
        sell_signals = 0
        hold_signals = 0
        
        # Test signal evaluation on a subset of dates
        for idx in range(200, len(hist)):
            df_subset = hist.iloc[:idx+1]
            res = evaluate_signals(t, asset_type, df_subset)
            sig = res["signal"]
            if sig == "buy":
                buy_signals += 1
                if buy_signals <= 5:
                    print(f"  [BUY] Date: {hist.index[idx].strftime('%Y-%m-%d')} | Price: ${res['price']:.2f} | Reason: {res['reason']}")
            elif sig == "sell":
                sell_signals += 1
                if sell_signals <= 5:
                    print(f"  [SELL] Date: {hist.index[idx].strftime('%Y-%m-%d')} | Price: ${res['price']:.2f} | Reason: {res['reason']}")
            else:
                hold_signals += 1
                
        print(f"Summary: Buy signals: {buy_signals} | Sell signals: {sell_signals} | Hold: {hold_signals}")

if __name__ == "__main__":
    main()
