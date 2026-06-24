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

def get_contribution_for_month_index(m_idx):
    """
    m_idx is 1-based index of months elapsed since start of simulation.
    Month 1: M=1 -> +3K base + 60K annual.
    Month 3: M=3 -> +3K base + 6K quarterly.
    Month 6: M=6 -> +3K base + 6K quarterly + 20K semi-annual.
    Month 13: M=13 -> +3K base + 60K annual.
    """
    contrib = 3000.0 # base monthly
    if m_idx % 3 == 0:
        contrib += 6000.0
    if m_idx % 6 == 0:
        contrib += 20000.0
    if (m_idx - 1) % 12 == 0:
        contrib += 60000.0
    return contrib

def simulate_custom_cash_flows(df_reconstructed, initial_capital=20000.0):
    dates = df_reconstructed['date'].reset_index(drop=True)
    returns = df_reconstructed['strat_ret'].reset_index(drop=True).values
    bench_returns = df_reconstructed['bench_ret'].reset_index(drop=True).values
    
    portfolio_value = initial_capital
    bench_value = initial_capital
    
    prev_month = dates.iloc[0].month
    months_elapsed = 0
    total_deposited = initial_capital
    
    for i in range(len(dates)):
        current_date = dates.iloc[i]
        current_month = current_date.month
        
        is_contrib = (i == 0 or current_month != prev_month)
        
        if i > 0:
            portfolio_value *= (1.0 + returns[i])
            bench_value *= (1.0 + bench_returns[i])
            
        if is_contrib:
            months_elapsed += 1
            contrib = get_contribution_for_month_index(months_elapsed)
            portfolio_value += contrib
            bench_value += contrib
            if i > 0:
                total_deposited += contrib
            prev_month = current_month
            
    return portfolio_value, bench_value, total_deposited, months_elapsed

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alpha_path = os.path.join(base_dir, "backtest_alpha_growth_nav.csv")
    macd_path = os.path.join(base_dir, "backtest_macd_nav.csv")
    
    df_alpha = reconstruct_twr_returns(alpha_path)
    df_macd = reconstruct_twr_returns(macd_path)
    
    # 1. Aligned Period starting 2022-06-09
    start_date = df_alpha['date'].min()
    df_macd_aligned = df_macd[df_macd['date'] >= start_date].copy()
    
    # Simulate custom cash flows for Aligned Period
    final_alpha, final_alpha_bench, deposits_aligned, months_a = simulate_custom_cash_flows(df_alpha)
    final_macd_aligned, final_macd_bench_aligned, _, _ = simulate_custom_cash_flows(df_macd_aligned)
    
    # Simulate risk-free Bondia for the aligned period
    rf_daily = 0.11 / 360.0
    bondia_val = 20000.0
    prev_month_b = df_alpha['date'].iloc[0].month
    months_elapsed_b = 0
    
    for i in range(len(df_alpha)):
        curr_date = df_alpha['date'].iloc[i]
        curr_month = curr_date.month
        
        if i > 0:
            calendar_days = (curr_date - df_alpha['date'].iloc[i-1]).days
            bondia_val += bondia_val * rf_daily * calendar_days
            
        if i == 0 or curr_month != prev_month_b:
            months_elapsed_b += 1
            contrib = get_contribution_for_month_index(months_elapsed_b)
            bondia_val += contrib
            prev_month_b = curr_month
            
    print(f"--- Aligned Period Custom Scenario (2022-06-09 to 2026-06-19 — {months_a} months) ---")
    print(f"Total Deposited:                      ${deposits_aligned:,.2f} MXN")
    print(f"DCF Alpha-Momentum Final Value:       ${final_alpha:,.2f} MXN")
    print(f"DCF Benchmark Final Value:            ${final_alpha_bench:,.2f} MXN")
    print(f"MACD Trend (Aligned) Final Value:     ${final_macd_aligned:,.2f} MXN")
    print(f"MACD Benchmark (Aligned) Final Value:  ${final_macd_bench_aligned:,.2f} MXN")
    print(f"Bondia Cash Sweep (11% APR) Value:    ${bondia_val:,.2f} MXN")
    
    # 2. Full Period (unaligned)
    final_macd_full, final_macd_bench_full, deposits_full, months_f = simulate_custom_cash_flows(df_macd)
    
    # Simulate risk-free Bondia for the full period
    bondia_val_full = 20000.0
    prev_month_bf = df_macd['date'].iloc[0].month
    months_elapsed_bf = 0
    
    for i in range(len(df_macd)):
        curr_date = df_macd['date'].iloc[i]
        curr_month = curr_date.month
        
        if i > 0:
            calendar_days = (curr_date - df_macd['date'].iloc[i-1]).days
            bondia_val_full += bondia_val_full * rf_daily * calendar_days
            
        if i == 0 or curr_month != prev_month_bf:
            months_elapsed_bf += 1
            contrib = get_contribution_for_month_index(months_elapsed_bf)
            bondia_val_full += contrib
            prev_month_bf = curr_month

    print(f"\n--- Full Unconstrained Custom Scenario ---")
    print(f"DCF Alpha-Momentum (2022-06-09 to 2026-06-19 — {months_a} months):")
    print(f"  Total Deposited:                    ${deposits_aligned:,.2f} MXN")
    print(f"  Final Strategy Value:               ${final_alpha:,.2f} MXN")
    print(f"  Final Benchmark Value:              ${final_alpha_bench:,.2f} MXN")
    print(f"  Bondia Cash Sweep (11% APR) Value:  ${bondia_val:,.2f} MXN")
    print(f"MACD Trend Strategy (2021-06-21 to 2026-06-19 — {months_f} months):")
    print(f"  Total Deposited:                    ${deposits_full:,.2f} MXN")
    print(f"  Final Strategy Value:               ${final_macd_full:,.2f} MXN")
    print(f"  Final Benchmark Value:              ${final_macd_bench_full:,.2f} MXN")
    print(f"  Bondia Cash Sweep (11% APR) Value:  ${bondia_val_full:,.2f} MXN")

if __name__ == "__main__":
    main()
