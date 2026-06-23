import os
import pandas as pd
import numpy as np

def reconstruct_twr_returns(csv_path, contribution=2000.0):
    df = pd.read_csv(csv_path)
    df.columns = ['date', 'strategy', 'benchmark']
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    dates = df['date']
    strat_nav = df['strategy']
    bench_nav = df['benchmark']
    
    n_days = len(df)
    strat_returns = [0.0] * n_days
    bench_returns = [0.0] * n_days
    
    prev_month = dates.iloc[0].month
    last_strat_nav = strat_nav.iloc[0]
    last_bench_nav = bench_nav.iloc[0]
    
    for i in range(1, n_days):
        curr_date = dates.iloc[i]
        curr_month = curr_date.month
        
        is_contrib = (curr_month != prev_month)
        
        strat_val_before = strat_nav.iloc[i]
        bench_val_before = bench_nav.iloc[i]
        
        if is_contrib:
            strat_val_before -= contribution
            bench_val_before -= contribution
            prev_month = curr_month
            
        r_s = (strat_val_before / last_strat_nav) - 1.0 if last_strat_nav > 0 else 0.0
        r_b = (bench_val_before / last_bench_nav) - 1.0 if last_bench_nav > 0 else 0.0
        
        strat_returns[i] = r_s
        bench_returns[i] = r_b
        
        last_strat_nav = strat_nav.iloc[i]
        last_bench_nav = bench_nav.iloc[i]
        
    df['strat_ret'] = strat_returns
    df['bench_ret'] = bench_returns
    return df

def compute_metrics_for_subset(df_subset, rf_annual=0.11):
    if len(df_subset) == 0:
        return {"return": 0.0, "max_dd": 0.0, "sharpe_rf": 0.0, "sharpe_raw": 0.0}
        
    rf_daily = rf_annual / 252.0
    s_ret = df_subset['strat_ret'].values
    
    # Yearly return (compounded)
    strat_ret = np.prod(1.0 + s_ret) - 1.0
    
    # Sharpe (raw)
    std_s = s_ret.std()
    sharpe_raw = (s_ret.mean() / std_s * np.sqrt(252.0)) if std_s > 1e-6 else 0.0
    
    # Sharpe (excess over Rf)
    excess = s_ret - rf_daily
    sharpe_rf = (excess.mean() / std_s * np.sqrt(252.0)) if std_s > 1e-6 else 0.0
    
    # Max DD (properly anchored to 1.0 at start of subset)
    cum = np.cumprod(1.0 + s_ret)
    cum = np.insert(cum, 0, 1.0)
    peaks = np.maximum.accumulate(cum)
    dd = (cum - peaks) / peaks
    max_dd = dd.min()
    
    # If strategy has no positions (std is near 0), Sharpe is N/A or 0
    if std_s < 1e-5:
        sharpe_raw = 0.0
        sharpe_rf = 0.0
        
    return {
        "return": strat_ret,
        "max_dd": max_dd,
        "sharpe_rf": sharpe_rf,
        "sharpe_raw": sharpe_raw,
    }

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alpha_path = os.path.join(base_dir, "backtest_alpha_growth_nav.csv")
    macd_path = os.path.join(base_dir, "backtest_macd_nav.csv")
    
    df_alpha = reconstruct_twr_returns(alpha_path)
    df_macd = reconstruct_twr_returns(macd_path)
    
    # Aligned datasets
    start_date_alpha = df_alpha['date'].min()
    end_date_alpha = df_alpha['date'].max()
    
    df_macd_aligned = df_macd[(df_macd['date'] >= start_date_alpha) & (df_macd['date'] <= end_date_alpha)].copy()
    
    # Print overall stats
    metrics_alpha_all = compute_metrics_for_subset(df_alpha)
    metrics_macd_all = compute_metrics_for_subset(df_macd)
    metrics_macd_aligned_all = compute_metrics_for_subset(df_macd_aligned)
    
    print("=== OVERALL ALIGNED PERIOD (2022-06-09 to 2026-06-19) ===")
    print(f"DCF Alpha-Momentum: Return={metrics_alpha_all['return']:.2%}, CAGR={metrics_alpha_all['sharpe_rf']:.2f} (Sharpe Raw), MaxDD={metrics_alpha_all['strat_max_dd'] if 'strat_max_dd' in metrics_alpha_all else metrics_alpha_all['max_dd']:.2%}")
    # Wait, let's output a structured Markdown table to copy directly
    
    years = [2022, 2023, 2024, 2025, 2026]
    
    print("\n| Year | Strategy | Active Period | Return (%) | Max Drawdown (%) | Sharpe Ratio (Raw) | Sharpe Ratio (Rf=11%) |")
    print("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
    
    for y in years:
        # DCF
        sub_alpha = df_alpha[df_alpha['date'].dt.year == y]
        m_a = compute_metrics_for_subset(sub_alpha)
        period_a = f"{sub_alpha['date'].min().strftime('%m-%d')} to {sub_alpha['date'].max().strftime('%m-%d')}"
        print(f"| {y} | **DCF Alpha-Momentum** | {period_a} | {m_a['return']*100:+.2f}% | {m_a['max_dd']*100:.2f}% | {m_a['sharpe_raw']:.2f} | {m_a['sharpe_rf']:.2f} |")
        
        # MACD (Aligned to DCF for 2022)
        sub_macd = df_macd_aligned[df_macd_aligned['date'].dt.year == y]
        m_m = compute_metrics_for_subset(sub_macd)
        period_m = f"{sub_macd['date'].min().strftime('%m-%d')} to {sub_macd['date'].max().strftime('%m-%d')}"
        print(f"| | **MACD Trend (Aligned)** | {period_m} | {m_m['return']*100:+.2f}% | {m_m['max_dd']*100:.2f}% | {m_m['sharpe_raw']:.2f} | {m_m['sharpe_rf']:.2f} |")
        print("| --- | --- | :---: | :---: | :---: | :---: | :---: |")

    # Unconstrained full history comparison (including 2021)
    print("\n\n=== UNCONSTRAINED FULL HISTORIES (Each starting at inception) ===")
    print("| Year | Strategy | Active Period | Return (%) | Max Drawdown (%) | Sharpe Ratio (Raw) | Sharpe (Rf=11%) |")
    print("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
    
    # 2021
    sub_macd_2021 = df_macd[df_macd['date'].dt.year == 2021]
    m_m_2021 = compute_metrics_for_subset(sub_macd_2021)
    period_m_2021 = f"{sub_macd_2021['date'].min().strftime('%m-%d')} to {sub_macd_2021['date'].max().strftime('%m-%d')}"
    print(f"| 2021 | **DCF Alpha-Momentum** | N/A (Warmup) | - | - | - | - |")
    print(f"| | **MACD Trend (Unconstrained)** | {period_m_2021} | {m_m_2021['return']*100:+.2f}% | {m_m_2021['max_dd']*100:.2f}% | {m_m_2021['sharpe_raw']:.2f} | {m_m_2021['sharpe_rf']:.2f} |")
    print("| --- | --- | :---: | :---: | :---: | :---: | :---: |")
    
    for y in years:
        # DCF
        sub_alpha = df_alpha[df_alpha['date'].dt.year == y]
        m_a = compute_metrics_for_subset(sub_alpha)
        period_a = f"{sub_alpha['date'].min().strftime('%m-%d')} to {sub_alpha['date'].max().strftime('%m-%d')}"
        print(f"| {y} | **DCF Alpha-Momentum** | {period_a} | {m_a['return']*100:+.2f}% | {m_a['max_dd']*100:.2f}% | {m_a['sharpe_raw']:.2f} | {m_a['sharpe_rf']:.2f} |")
        
        # MACD (Full year for 2022)
        sub_macd = df_macd[df_macd['date'].dt.year == y]
        m_m = compute_metrics_for_subset(sub_macd)
        period_m = f"{sub_macd['date'].min().strftime('%m-%d')} to {sub_macd['date'].max().strftime('%m-%d')}"
        print(f"| | **MACD Trend (Unconstrained)** | {period_m} | {m_m['return']*100:+.2f}% | {m_m['max_dd']*100:.2f}% | {m_m['sharpe_raw']:.2f} | {m_m['sharpe_rf']:.2f} |")
        print("| --- | --- | :---: | :---: | :---: | :---: | :---: |")

if __name__ == "__main__":
    main()
