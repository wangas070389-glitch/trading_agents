import pandas as pd
import numpy as np

def run_calc(csv_file):
    df = pd.read_csv(csv_file)
    df.columns = ['date', 'strategy', 'benchmark']
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    daily_rate = 0.11 / 360.0
    cash_bondia = 20000.0
    prev_month = df['date'].iloc[0].month
    total_deposits = 20000.0

    for i in range(len(df)):
        current_date = df['date'].iloc[i]
        current_month = current_date.month
        
        # 1. Accrue daily interest
        if i > 0:
            date_prev = df['date'].iloc[i - 1]
            calendar_days = (current_date - date_prev).days
            interest = cash_bondia * daily_rate * calendar_days
            cash_bondia += interest
            
        # 2. Add monthly contributions
        if i == 0 or current_month != prev_month:
            if i > 0:
                cash_bondia += 2000.0
                total_deposits += 2000.0
            prev_month = current_month

    days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
    years = days / 365.25
    
    print(f"--- Results for {csv_file} ({years:.2f} years, {df['date'].iloc[0].date()} to {df['date'].iloc[-1].date()}) ---")
    print(f"Total Deposits: ${total_deposits:,.2f} MXN")
    print(f"Mattress Savings (0% APR) Final Value: ${total_deposits:,.2f} MXN")
    print(f"Bondia Savings (11% APR) Final Value: ${cash_bondia:,.2f} MXN")
    print(f"Strategy Final Value: ${df['strategy'].iloc[-1]:,.2f} MXN")
    print(f"Benchmark Final Value: ${df['benchmark'].iloc[-1]:,.2f} MXN")
    print()

run_calc('backtest_alpha_growth_nav.csv')
run_calc('backtest_macd_nav.csv')
run_calc('backtest_nav.csv')
