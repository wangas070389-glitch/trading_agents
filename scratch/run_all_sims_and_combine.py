import os
import sys
import subprocess
import pandas as pd
import yfinance as yf
import numpy as np

def run_script(path):
    print(f"Executing: {path}")
    result = subprocess.run([sys.executable, path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running {path}:")
        print(result.stderr)
        sys.exit(1)
    print(f"Completed {path} successfully.")

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Run Strategy 5 and Strategy 6 backtests to generate CSVs
    run_script(os.path.join(dir_path, "improve_backtest_alternatives.py"))
    run_script(os.path.join(dir_path, "backtest_high_beta.py"))
    
    print("\nAll individual backtests completed. Starting portfolio combination...")
    
    # 2. Load NAV files
    root_dir = os.path.dirname(dir_path)
    s1_path = os.path.join(root_dir, "backtest_alpha_growth_nav.csv")
    s4_path = os.path.join(root_dir, "us_stocks_dcf_backtest_nav.csv")
    s5_path = os.path.join(root_dir, "alternatives_backtest_nav.csv")
    s6_path = os.path.join(root_dir, "high_beta_backtest_nav.csv")
    
    if not os.path.exists(s1_path):
        # Fallback to local files
        s1_path = "backtest_alpha_growth_nav.csv"
        s4_path = "us_stocks_dcf_backtest_nav.csv"
        s5_path = "alternatives_backtest_nav.csv"
        s6_path = "high_beta_backtest_nav.csv"
        
    s1 = pd.read_csv(s1_path)
    s1.columns = ["Date", "S1", "Benchmark"]
    s1["Date"] = pd.to_datetime(s1["Date"])
    
    s4 = pd.read_csv(s4_path)
    s4.columns = ["Date", "S4", "Capital4"]
    s4["Date"] = pd.to_datetime(s4["Date"])
    
    s5 = pd.read_csv(s5_path)
    s5.columns = ["Date", "S5"]
    s5["Date"] = pd.to_datetime(s5["Date"])
    
    s6 = pd.read_csv(s6_path)
    s6.columns = ["Date", "S6"]
    s6["Date"] = pd.to_datetime(s6["Date"])
    
    # 3. Fetch USDMXN Exchange Rate
    print("Downloading USDMXN=X exchange rate...")
    fx = yf.download("USDMXN=X", start="2021-06-20", end="2026-06-20", progress=False)
    fx.columns = [c if isinstance(c, str) else c[0] for c in fx.columns]
    fx_close = fx["Close"].ffill().bfill()
    
    # 4. Set indexes to Date for alignment
    s1 = s1.set_index("Date")
    s4 = s4.set_index("Date")
    s5 = s5.set_index("Date")
    s6 = s6.set_index("Date")
    
    # Align FX rate
    s1["USDMXN"] = fx_close.reindex(s1.index).ffill().bfill()
    s1["S1_USD"] = s1["S1"] / s1["USDMXN"]
    
    # Merge datasets
    df = pd.DataFrame(index=s4.index)
    df = df.join(s1["S1_USD"], how="inner").rename(columns={"S1_USD": "S1"})
    df = df.join(s4, how="inner")
    df = df.join(s5["S5"], how="inner")
    df = df.join(s6["S6"], how="inner")
    df["USDMXN"] = fx_close.reindex(df.index).ffill().bfill()
    
    # 5. Calculate monthly DCA inflows for each strategy to calculate TWR adjusted daily returns
    # Strategy 1 (MXN): Inflow 2000 MXN
    # Strategy 4 (USD): Inflow 1000 USD
    # Strategy 5 (USD): Inflow 1000 USD
    # Strategy 6 (USD): Inflow 1000 USD
    
    df = df.sort_index()
    dates = df.index
    
    adj_ret_1 = [0.0]
    adj_ret_4 = [0.0]
    adj_ret_5 = [0.0]
    adj_ret_6 = [0.0]
    
    last_month = dates[0].month
    
    for i in range(1, len(df)):
        date = dates[i]
        is_new_month = date.month != last_month
        last_month = date.month
        
        # S1 (MXN converted to USD)
        prev_s1 = df["S1"].iloc[i-1]
        curr_s1 = df["S1"].iloc[i]
        fx_rate = df["USDMXN"].iloc[i]
        inflow_1 = (2000.0 / fx_rate) if is_new_month else 0.0
        r1 = (curr_s1 - inflow_1) / prev_s1 - 1.0
        adj_ret_1.append(r1)
        
        # S4 (USD)
        prev_s4 = df["S4"].iloc[i-1]
        curr_s4 = df["S4"].iloc[i]
        inflow_4 = 1000.0 if is_new_month else 0.0
        r4 = (curr_s4 - inflow_4) / prev_s4 - 1.0
        adj_ret_4.append(r4)
        
        # S5 (USD)
        prev_s5 = df["S5"].iloc[i-1]
        curr_s5 = df["S5"].iloc[i]
        inflow_5 = 1000.0 if is_new_month else 0.0
        r5 = (curr_s5 - inflow_5) / prev_s5 - 1.0
        adj_ret_5.append(r5)
        
        # S6 (USD)
        prev_s6 = df["S6"].iloc[i-1]
        curr_s6 = df["S6"].iloc[i]
        inflow_6 = 1000.0 if is_new_month else 0.0
        r6 = (curr_s6 - inflow_6) / prev_s6 - 1.0
        adj_ret_6.append(r6)
        
    df["R1"] = adj_ret_1
    df["R4"] = adj_ret_4
    df["R5"] = adj_ret_5
    df["R6"] = adj_ret_6
    
    # 6. Combined Strategy 7 Returns
    # Weight allocation: 40% Strategy 4, 30% Strategy 1, 20% Strategy 6, 10% Strategy 5
    w4, w1, w6, w5 = 0.40, 0.30, 0.20, 0.10
    df["R7"] = (w4 * df["R4"]) + (w1 * df["R1"]) + (w6 * df["R6"]) + (w5 * df["R5"])
    
    # Compound Returns (TWR Curve)
    df["CumTWR"] = (1.0 + df["R7"]).cumprod()
    
    # CAGR
    days = (df.index[-1] - df.index[0]).days
    years = max(days / 365.25, 0.01)
    cagr = (df["CumTWR"].iloc[-1]) ** (1.0 / years) - 1.0
    
    # Sharpe Ratio (USD cash sweep yield 4.5% assumed)
    excess = df["R7"] - (0.045 / 252.0)
    sharpe = (excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0
    
    # Max Drawdown
    cum_max = df["CumTWR"].cummax()
    drawdowns = (df["CumTWR"] - cum_max) / cum_max
    max_dd = drawdowns.min()
    
    # 7. Print consolidated report
    print("\n" + "=" * 80)
    print("CONSOLIDATED MULTI-STRATEGY PORTFOLIO (STRATEGY 7) RESULTS")
    print("=" * 80)
    print(f"Simulation Period:    {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"Target Weights:       40% S4 (US DCS), 30% S1 (MXN Value), 20% S6 (High-Beta), 10% S5 (Alternatives)")
    print(f"Strategy 7 CAGR:      {cagr*100:.2f}%")
    print(f"Strategy 7 Max DD:    {max_dd*100:.2f}%")
    print(f"Strategy 7 Sharpe:    {sharpe:.2f}")
    
    # Compare with SPY Buy & Hold (TWR)
    # Download SPY
    spy = yf.download("SPY", start=df.index[0], end=df.index[-1], progress=False)
    spy.columns = [c if isinstance(c, str) else c[0] for c in spy.columns]
    spy_ret = spy["Close"].pct_change().dropna()
    spy_cum = (1.0 + spy_ret).cumprod()
    spy_days = (spy_cum.index[-1] - spy_cum.index[0]).days
    spy_years = max(spy_days / 365.25, 0.01)
    spy_cagr = (spy_cum.iloc[-1]) ** (1.0 / spy_years) - 1.0
    spy_max_dd = (spy_cum / spy_cum.cummax() - 1.0).min()
    spy_excess = spy_ret - (0.045 / 252.0)
    spy_sharpe = (spy_excess.mean() / spy_excess.std() * np.sqrt(252)) if spy_excess.std() > 0 else 0.0
    
    print("-" * 80)
    print("BENCHMARK COMPARISON (SPY Buy & Hold)")
    print(f"SPY CAGR (TWR):       {spy_cagr*100:.2f}%")
    print(f"SPY Max DD:           {spy_max_dd*100:.2f}%")
    print(f"SPY Sharpe:           {spy_sharpe:.2f}")
    print("=" * 80 + "\n")
    
    # Save combined curve
    out_path = os.path.join(root_dir, "consolidated_portfolio_nav.csv")
    df[["CumTWR", "R7"]].to_csv(out_path)
    print(f"Consolidated curve saved to {out_path}")

if __name__ == "__main__":
    main()
