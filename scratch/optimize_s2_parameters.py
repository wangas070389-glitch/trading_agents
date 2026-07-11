import os
import sys
import json
import datetime
import pandas as pd
import numpy as np
import yfinance as yf

# Include project root in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest_live_bmv import BMV_TICKERS, US_TICKERS
from skills.macd_trailing_strategy import MACDTrailingStopStrategy

def main():
    print("=" * 80)
    print("S2 MACD SYSTEMATIC MULTI-ASSET OPTIMIZER (BATCH MODE)")
    print("=" * 80)
    
    # 1. Download Data
    LOOKBACK_PERIOD = "5y"
    MIN_HISTORY_DAYS = 252
    
    print("Downloading exchange rate...")
    usdmxn = yf.Ticker("MXN=X").history(period=LOOKBACK_PERIOD)
    if usdmxn.index.tz is not None:
        usdmxn.index = pd.to_datetime(usdmxn.index.date)
    fx_rate = usdmxn["Close"].rename("USDMXN_Rate")

    all_tickers = BMV_TICKERS + US_TICKERS
    price_data = {}

    print("Downloading all ticker data in a single batch request...")
    data = yf.download(all_tickers, period=LOOKBACK_PERIOD, group_by='ticker', progress=False)
    
    for ticker in all_tickers:
        try:
            if ticker in data.columns.levels[0]:
                ticker_df = data[ticker].dropna(subset=["Close"])
                if not ticker_df.empty and len(ticker_df) >= MIN_HISTORY_DAYS:
                    if ticker_df.index.tz is not None:
                        ticker_df.index = pd.to_datetime(ticker_df.index.date)

                    if ticker in US_TICKERS:
                        df = pd.DataFrame({"Close": ticker_df["Close"]}).join(fx_rate, how="inner")
                        if not df.empty:
                            price_data[ticker] = df["Close"] * df["USDMXN_Rate"]
                    else:
                        price_data[ticker] = ticker_df["Close"]
        except Exception as e:
            print(f"  [WARN] Failed to process {ticker}: {e}")
            continue

    price_matrix = pd.DataFrame(price_data).ffill().bfill()
    valid_cols = [c for c in price_matrix.columns if price_matrix[c].notna().sum() >= MIN_HISTORY_DAYS]
    price_matrix = price_matrix[valid_cols]
    
    print(f"Loaded price matrix with shape {price_matrix.shape} ({len(price_matrix.columns)} valid assets).")
    
    # 2. Grid Search Parameters
    ma_lengths = [50, 100, 200]
    ma_types = ["SMA", "EMA"]
    macd_lengths = [(12, 26, 9), (8, 17, 9), (15, 35, 9)]
    profit_triggers = [3.0, 5.0, 10.0, 15.0]
    trailing_stops = [1.0, 2.0, 3.0, 5.0]
    
    best_sharpe = -99.0
    best_config = None
    results = []
    
    total_combinations = len(ma_lengths) * len(ma_types) * len(macd_lengths) * len(profit_triggers) * len(trailing_stops)
    print(f"Testing {total_combinations} parameter combinations...")
    
    count = 0
    for ma_len in ma_lengths:
        for ma_type in ma_types:
            for fast, slow, sig in macd_lengths:
                for p_trig in profit_triggers:
                    for t_stop in trailing_stops:
                        count += 1
                        
                        strategy = MACDTrailingStopStrategy(
                            long_term_ma_length=ma_len,
                            ma_type=ma_type,
                            macd_fast=fast,
                            macd_slow=slow,
                            macd_signal=sig,
                            profit_trigger_pct=p_trig,
                            trailing_stop_pct=t_stop,
                            position_pct=0.10,
                            commission_pct=0.0029,
                            max_positions=10
                        )
                        
                        try:
                            res = strategy.run_portfolio_backtest(price_matrix)
                            metrics = res["metrics"]
                            sharpe = metrics["strategy_sharpe"]
                            cagr = metrics["strategy_cagr"]
                            drawdown = metrics["strategy_max_dd"]
                            n_trades = metrics["n_trades"]
                            
                            # Filter for statistical significance
                            if n_trades >= 15:
                                results.append({
                                    "longTermMALength": ma_len,
                                    "maType": ma_type,
                                    "fastLength": fast,
                                    "slowLength": slow,
                                    "profitTriggerPercent": p_trig,
                                    "trailingStopPercent": t_stop,
                                    "sharpe": sharpe,
                                    "cagr": cagr,
                                    "drawdown": drawdown,
                                    "n_trades": n_trades
                                })
                                
                                if sharpe > best_sharpe:
                                    best_sharpe = sharpe
                                    best_config = results[-1]
                        except Exception as e:
                            continue
                            
                        if count % 50 == 0:
                            print(f"  Processed {count}/{total_combinations} combinations...")
                            
    if best_config is None:
        print("No viable configurations found with enough trades.")
        return
        
    print("\n" + "=" * 80)
    print("BEST CONFIGURATION FOUND")
    print("=" * 80)
    print(f"  Long-Term MA:       {best_config['longTermMALength']} ({best_config['maType']})")
    print(f"  MACD Fast/Slow/Sig: {best_config['fastLength']} / {best_config['slowLength']} / 9")
    print(f"  Profit Trigger:     {best_config['profitTriggerPercent']:.1f}%")
    print(f"  Trailing Stop:      {best_config['trailingStopPercent']:.1f}%")
    print(f"  Sharpe Ratio:       {best_config['sharpe']:.4f}")
    print(f"  CAGR:               {best_config['cagr']*100:.2f}%")
    print(f"  Max Drawdown:       {best_config['drawdown']*100:.2f}%")
    print(f"  Total Trades:       {best_config['n_trades']}")
    print("=" * 80)
    
    # Save optimal parameters
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "macd_learned_params.json")
    learned_dict = {
        "longTermMALength": best_config["longTermMALength"],
        "maType": best_config["maType"],
        "fastLength": best_config["fastLength"],
        "slowLength": best_config["slowLength"],
        "signalLength": 9,
        "profitTriggerPercent": best_config["profitTriggerPercent"],
        "trailingStopPercent": best_config["trailingStopPercent"],
        "pyramiding": 1
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(learned_dict, f, indent=4)
        
    print(f"Saved optimal parameters to: {out_path}")

if __name__ == "__main__":
    main()
