import os
import json
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

from skills.macd_trend import calculate_all_indicators
from backtest_macd import download_data, run_single_asset_simulation, calculate_metrics

# Grid definition for search
FAST_SLOW_GRID = [
    (8, 17),
    (12, 26),   # Standard MACD
    (15, 35)
]
PROFIT_TRIGGER_GRID = [3.0, 5.0, 7.0]
TRAILING_STOP_GRID = [1.0, 2.0, 3.0]
PYRAMIDING_GRID = [1, 2]

def main():
    ticker = "SPY"
    start_date = "2021-06-15"
    end_date = "2026-06-15"
    
    print("=" * 80)
    print(f"STARTING PARAMETER OPTIMIZATION GRID SEARCH FOR {ticker}")
    print("=" * 80)
    
    data_dict = download_data([ticker], start_date, end_date)
    if ticker not in data_dict:
        print(f"Failed to fetch data for {ticker}. Aborting.")
        return
        
    df = data_dict[ticker]
    
    # Split training vs validation (e.g. 60% train, 40% validation)
    # Exclude warmup buffer of 200 days from both split calculations
    warmup_days = 200
    valid_data_start = df.index[warmup_days]
    
    total_valid_len = len(df) - warmup_days
    train_split_idx = warmup_days + int(total_valid_len * 0.6)
    
    train_df = df.iloc[:train_split_idx].copy()
    val_df = df.iloc[train_split_idx - warmup_days:].copy()  # maintain warmup overlap for indicators
    
    print(f"Total Daily Bars:   {len(df)}")
    print(f"Training Period:    {train_df.index[warmup_days].date()} to {train_df.index[-1].date()}")
    print(f"Validation Period:  {val_df.index[warmup_days].date()} to {val_df.index[-1].date()}")
    
    # Search loop
    best_sharpe = -999.0
    best_params = None
    results = []
    
    # Base configuration params
    base_params = {
        "longTermMALength": 200,
        "maType": "SMA",
        "fastLength": 12,
        "slowLength": 26,
        "signalLength": 9,
        "profitTriggerPercent": 5.0,
        "trailingStopPercent": 2.0,
        "defaultQtyValue": 10.0,
        "pyramiding": 1,
        "commission": 0.0010,
        "slippage_cents": 3,
    }
    
    count = 0
    total_combos = len(FAST_SLOW_GRID) * len(PROFIT_TRIGGER_GRID) * len(TRAILING_STOP_GRID) * len(PYRAMIDING_GRID)
    
    print(f"\nSearching {total_combos} combinations in parameter space...")
    
    for fast_slow in FAST_SLOW_GRID:
        fast_len, slow_len = fast_slow
        for prof_trig in PROFIT_TRIGGER_GRID:
            for trail_pct in TRAILING_STOP_GRID:
                for pyram in PYRAMIDING_GRID:
                    count += 1
                    
                    # Update configuration
                    test_params = base_params.copy()
                    test_params["fastLength"] = fast_len
                    test_params["slowLength"] = slow_len
                    test_params["profitTriggerPercent"] = prof_trig
                    test_params["trailingStopPercent"] = trail_pct
                    test_params["pyramiding"] = pyram
                    
                    try:
                        # Run strategy on training portion
                        nav_df, trades = run_single_asset_simulation(train_df, ticker, test_params)
                        if nav_df.empty:
                            continue
                            
                        metrics = calculate_metrics(nav_df["NAV"], "MACD Test")
                        sharpe = metrics["sharpe"]
                        total_ret = metrics["total_return"]
                        
                        results.append({
                            "fastLength": fast_len,
                            "slowLength": slow_len,
                            "profitTriggerPercent": prof_trig,
                            "trailingStopPercent": trail_pct,
                            "pyramiding": pyram,
                            "sharpe": sharpe,
                            "return": total_ret,
                            "trades": len(trades)
                        })
                        
                        if sharpe > best_sharpe and len(trades) >= 3:  # reject zero-trade fitting anomalies
                            best_sharpe = sharpe
                            best_params = test_params.copy()
                            
                    except Exception as e:
                        print(f"Error testing combo {fast_slow}-{prof_trig}-{trail_pct}-{pyram}: {e}")
                        continue
                        
                    if count % 10 == 0:
                        print(f"  Processed {count}/{total_combos} combinations...")
                        
    if best_params is None:
        print("Failed to find any viable parameter combinations with active trades.")
        return
        
    print("\n" + "=" * 80)
    print("BEST PARAMETERS FOUND ON TRAINING DATA")
    print("=" * 80)
    print(f"  MACD Fast/Slow:     {best_params['fastLength']} / {best_params['slowLength']}")
    print(f"  Profit Trigger:     {best_params['profitTriggerPercent']:.1f}%")
    print(f"  Trailing Stop:      {best_params['trailingStopPercent']:.1f}%")
    print(f"  Pyramiding limit:   {best_params['pyramiding']}")
    print(f"  Training Sharpe:    {best_sharpe:.4f}")
    
    # Save best parameters to json
    out_file = "macd_learned_params.json"
    with open(out_file, "w", encoding="utf-8") as f:
        learned_dict = {
            "fastLength": best_params["fastLength"],
            "slowLength": best_params["slowLength"],
            "profitTriggerPercent": best_params["profitTriggerPercent"],
            "trailingStopPercent": best_params["trailingStopPercent"],
            "pyramiding": best_params["pyramiding"]
        }
        json.dump(learned_dict, f, indent=4)
    print(f"Saved optimal parameters to {out_file}")
    
    # Verify on validation set
    print("\nRunning verification on validation set (out-of-sample)...")
    val_nav_df, val_trades = run_single_asset_simulation(val_df, ticker, best_params)
    val_metrics = calculate_metrics(val_nav_df["NAV"], "Out-of-sample Validation")
    
    # Verify Benchmark Buy & Hold on same validation window
    bench_shares = 10000.0 / val_df.loc[val_df.index >= val_nav_df.index[0], "close"].iloc[0]
    bench_nav = val_df.loc[val_df.index >= val_nav_df.index[0], "close"] * bench_shares
    bench_nav.index = [d.strftime("%Y-%m-%d") for d in bench_nav.index]
    
    common_idx = val_nav_df.index.intersection(bench_nav.index)
    val_nav_df = val_nav_df.loc[common_idx]
    bench_nav = bench_nav.loc[common_idx]
    
    val_bench_metrics = calculate_metrics(bench_nav, f"Buy & Hold {ticker}")
    
    print("=" * 80)
    print("OUT-OF-SAMPLE VALIDATION METRICS")
    print("=" * 80)
    print(f"  Strategy Return:   {val_metrics['total_return']*100:.2f}% (CAGR: {val_metrics['cagr']*100:.2f}%)")
    print(f"  Strategy Sharpe:   {val_metrics['sharpe']:.2f}")
    print(f"  Strategy Max DD:   {val_metrics['max_drawdown']*100:.2f}%")
    print(f"  Benchmark Return:  {val_bench_metrics['total_return']*100:.2f}% (CAGR: {val_bench_metrics['cagr']*100:.2f}%)")
    print(f"  Benchmark Sharpe:  {val_bench_metrics['sharpe']:.2f}")
    print(f"  Benchmark Max DD:  {val_bench_metrics['max_drawdown']*100:.2f}%")
    print(f"  Validation Trades: {len(val_trades)}")
    
if __name__ == "__main__":
    main()
