import os
import sys
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn import hmm

# Local imports path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from connectors.alpaca_connector import AlpacaConnector
from skills.macd_trend import calculate_macd

EXPANDED_UNIVERSE = [
    "SPY", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST",
    "AMXB.MX", "FEMSAUBD.MX", "WALMEX.MX", "GFNORTEO.MX", "GMEXICOB.MX", 
    "CEMEXCPO.MX", "BIMBOA.MX", "GAPB.MX", "ASURB.MX", "AC.MX"
]

def prepare():
    print("=" * 80)
    print("PREPARING TRADING SCENARIO FOR TOMORROW (1d MACD + SMA + HMM Strategy)")
    print("=" * 80)
    
    # 1. Fetch SPY daily history for HMM training
    print("\nFetching SPY daily historical data to determine market regime...")
    spy = yf.download("SPY", period="5y", interval="1d", progress=False)
    spy.columns = [c if isinstance(c, str) else c[0] for c in spy.columns]
    spy.index = pd.to_datetime(spy.index).tz_localize(None)
    spy["Return"] = np.log(spy["Close"] / spy["Close"].shift(1))
    spy = spy.dropna()
    
    # 2. Train HMM on SPY
    obs = spy["Return"].values.reshape(-1, 1)
    model = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=50, random_state=42)
    model.fit(obs)
    states = model.predict(obs)
    
    means = model.means_[:, 0]
    bear_idx = np.argmin(means)
    bull_idx = np.argmax(means)
    sideways_idx = [i for i in range(3) if i not in (bear_idx, bull_idx)][0]
    
    state_map = {bear_idx: -1, bull_idx: 1, sideways_idx: 0}
    current_regime = state_map[states[-1]]
    
    regime_names = {-1: "BEAR (Max Exposure: 10%)", 1: "BULL (Max Exposure: 95%)", 0: "SIDEWAYS (Max Exposure: 50%)"}
    print(f"\n>>> CURRENT HMM REGIME FOR TOMORROW: {regime_names[current_regime]}")
    
    max_equity_exposure = 0.50
    if current_regime == 1:
        max_equity_exposure = 0.95
    elif current_regime == -1:
        max_equity_exposure = 0.10
        
    # 3. Fetch Alpaca Paper Account status
    print("\nFetching Alpaca Paper Account status...")
    alpaca = AlpacaConnector()
    account_value = 20000.0  # fallback
    try:
        acc = alpaca.get_account_info()
        account_value = float(acc["portfolio_value"])
        cash_avail = float(acc["cash"])
        print(f"  |-- Alpaca Account Connected.")
        print(f"  |-- Portfolio Value: ${account_value:,.2f} USD")
        print(f"  |-- Cash Balance:    ${cash_avail:,.2f} USD")
    except Exception as e:
        print(f"  |-- Could not fetch Alpaca account info: {e}. Defaulting to simulated $20,000.00 MXN portfolio.")
        cash_avail = 20000.0
        
    # 4. Fetch exchange rate for MXN conversion
    print("\nFetching current USD/MXN exchange rate...")
    try:
        usdmxn = yf.Ticker("MXN=X").history(period="1d")
        rate = float(usdmxn["Close"].iloc[-1])
        print(f"  |-- Current exchange rate: {rate:.4f} MXN/USD")
    except Exception:
        rate = 17.50
        print(f"  |-- Failed to fetch exchange rate. Defaulting to {rate:.2f} MXN/USD")
        
    # 5. Fetch daily bars for expanded universe and calculate signals
    print(f"\nAnalyzing signals for all {len(EXPANDED_UNIVERSE)} assets...")
    bullish_assets = []
    
    for ticker in EXPANDED_UNIVERSE:
        try:
            hist = yf.download(ticker, period="1y", interval="1d", progress=False)
            if hist.empty or len(hist) < 50:
                continue
            hist.columns = [c if isinstance(c, str) else c[0] for c in hist.columns]
            hist.index = pd.to_datetime(hist.index).tz_localize(None)
            
            # Indicators
            hist["macd"], hist["signal"] = calculate_macd(hist["Close"])
            hist["sma50"] = hist["Close"].rolling(window=50).mean()
            
            row = hist.iloc[-1]
            close = float(row["Close"])
            macd_val = float(row["macd"])
            sig_val = float(row["signal"])
            sma50_val = float(row["sma50"])
            
            is_bullish = macd_val > sig_val and close > sma50_val
            
            # Check price affordability for MXN sizing
            price_mxn = close * rate if not ticker.endswith(".MX") else close
            
            status_icon = "BULLISH" if is_bullish else "BEARISH/NEUTRAL"
            print(f"  Ticker {ticker:12} | Price: {price_mxn:8,.2f} MXN | Signal: {status_icon:15} | Close > 50SMA: {close > sma50_val}")
            
            if is_bullish:
                bullish_assets.append({
                    "ticker": ticker,
                    "price_usd": close if not ticker.endswith(".MX") else close / rate,
                    "price_mxn": price_mxn
                })
        except Exception as e:
            print(f"  Ticker {ticker:12} | Failed to fetch/calculate: {e}")
            
    # 6. Calculate target allocations
    print("\n" + "="*80)
    print("TARGET PORTFOLIO ALLOCATION")
    print("="*80)
    print(f"Active Bullish Assets ({len(bullish_assets)}): {[a['ticker'] for a in bullish_assets]}")
    print(f"Max Equity Exposure Cap: {max_equity_exposure*100:.1f}%")
    
    if len(bullish_assets) > 0:
        weight_per_asset = max_equity_exposure / len(bullish_assets)
        weight_per_asset = min(0.20, weight_per_asset)  # 20% cap per position
        print(f"Target weight per active asset: {weight_per_asset*100:.1f}%")
        
        # Calculate shares to hold
        print("\nTarget Trades Blotter:")
        print("| Ticker | Current Price (MXN) | Target Weight | Target Value (MXN) | Target Shares | Broker Execution |")
        print("| :--- | :---: | :---: | :---: | :---: | :--- |")
        
        # Convert total account value to MXN for uniform sizing calculations
        account_value_mxn = account_value * rate if not alpaca.api_key else account_value
        currency_label = "USD" if alpaca.api_key else "MXN"
        
        for asset in bullish_assets:
            target_val_mxn = account_value_mxn * weight_per_asset
            target_shares = target_val_mxn / asset["price_mxn"]
            exec_mode = "ALPACA (US Paper)" if not asset["ticker"].endswith(".MX") and alpaca.api_key else "MOCK LOCAL (MXN)"
            
            price_disp = asset["price_usd"] if exec_mode.startswith("ALPACA") else asset["price_mxn"]
            val_disp = target_val_mxn / (rate if exec_mode.startswith("ALPACA") else 1.0)
            
            print(f"| {asset['ticker']:10} | ${price_disp:18,.2f} | {weight_per_asset*100:12.1f}% | ${val_disp:16,.2f} | {int(target_shares):13d} | {exec_mode:18} |")
    else:
        print("\nNo bullish assets identified. Portfolio will be 100% Cash / Bondia sweep yield.")

if __name__ == "__main__":
    prepare()
