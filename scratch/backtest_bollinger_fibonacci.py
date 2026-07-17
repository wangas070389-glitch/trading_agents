import os
import numpy as np
import pandas as pd
import yfinance as yf

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, adjust=False).mean()
    avg_loss = loss.ewm(com=period-1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1.0 + rs.fillna(0)))
    return rsi

def main():
    ticker = "QQQ"
    start_date = "2015-01-01"
    end_date = "2026-07-10"
    
    print(f"Downloading historical data for {ticker}...")
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    if df.empty:
        print("Failed to download data.")
        return
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df = df.dropna(subset=["Close"])
    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    
    # 1. Bollinger Bands (20-day, 2 standard deviations)
    bb_period = 20
    df["BB_Middle"] = close.rolling(bb_period).mean()
    df["BB_Std"] = close.rolling(bb_period).std()
    df["BB_Upper"] = df["BB_Middle"] + 2.0 * df["BB_Std"]
    df["BB_Lower"] = df["BB_Middle"] - 2.0 * df["BB_Std"]
    
    # 2. 55-day rolling swing windows (Fibonacci)
    lookback = 55
    df["Swing_High"] = high.rolling(lookback).max()
    df["Swing_Low"] = low.rolling(lookback).min()
    df["RSI"] = calculate_rsi(close, 14)
    
    # Retracement levels
    df["Range"] = df["Swing_High"] - df["Swing_Low"]
    df["Fib_382"] = df["Swing_High"] - 0.382 * df["Range"]
    df["Fib_50"] = df["Swing_High"] - 0.500 * df["Range"]
    df["Fib_618"] = df["Swing_High"] - 0.618 * df["Range"]
    df["Fib_786"] = df["Swing_High"] - 0.786 * df["Range"]
    
    # Simulation Parameters
    initial_cap = 100000.0
    cash = initial_cap
    shares = 0.0
    position = 0 # 0 = Cash, 1 = Long
    
    nav_history = []
    trade_logs = []
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    close_vals = close.values
    rsi_vals = df["RSI"].values
    rsi_prev_vals = df["RSI"].shift(1).values
    
    bb_lower = df["BB_Lower"].values
    bb_middle = df["BB_Middle"].values
    bb_upper = df["BB_Upper"].values
    
    fib_382 = df["Fib_382"].values
    fib_50 = df["Fib_50"].values
    fib_618 = df["Fib_618"].values
    fib_786 = df["Fib_786"].values
    
    dates = df.index
    
    print("Running Bollinger + Fibonacci Reversal Backtest simulation...")
    for t in range(lookback, len(df)):
        px = close_vals[t]
        curr_rsi = rsi_vals[t]
        prev_rsi = rsi_prev_vals[t]
        
        lower_b = bb_lower[t-1]
        mid_b = bb_middle[t-1]
        upper_b = bb_upper[t-1]
        
        f382 = fib_382[t-1]
        f50 = fib_50[t-1]
        f618 = fib_618[t-1]
        f786 = fib_786[t-1]
        
        if position == 0:
            # Confluence trigger:
            # 1. Price is near or below the Lower Bollinger Band
            # 2. Price is near a key Fib Level (38.2%, 50%, or 61.8%) within 1.5%
            at_bb_lower = (px <= lower_b * 1.015)
            
            fib_levels = [f382, f50, f618]
            near_fib = any(abs(px - f) / f < 0.015 for f in fib_levels)
            
            # RSI hook confirmation
            rsi_hook = (prev_rsi <= 35) and (curr_rsi > 35)
            
            if at_bb_lower and near_fib and rsi_hook:
                position = 1
                entry_price = px
                # Stop loss set slightly below 78.6% level or lower band
                stop_loss = min(f786, lower_b) * 0.99
                # Take profit set at upper band
                take_profit = upper_b
                
                shares = cash / px
                cash = 0.0
                trade_logs.append({
                    "Date": dates[t].strftime("%Y-%m-%d"),
                    "Type": "BUY",
                    "Price": px,
                    "Stop": stop_loss,
                    "Limit": take_profit
                })
        else:
            # Exit rules:
            # 1. Hit stop loss
            # 2. Reached upper band or RSI is overbought (> 70)
            if px <= stop_loss:
                cash = shares * px
                shares = 0.0
                position = 0
                trade_logs.append({
                    "Date": dates[t].strftime("%Y-%m-%d"),
                    "Type": "STOP",
                    "Price": px,
                    "P&L%": (px / entry_price - 1.0) * 100.0
                })
            elif px >= take_profit or curr_rsi >= 70:
                cash = shares * px
                shares = 0.0
                position = 0
                trade_logs.append({
                    "Date": dates[t].strftime("%Y-%m-%d"),
                    "Type": "LIMIT",
                    "Price": px,
                    "P&L%": (px / entry_price - 1.0) * 100.0
                })
                
        # Record daily NAV
        current_nav = cash + (shares * px)
        nav_history.append({"Date": dates[t], "NAV": current_nav})
        
    df_nav = pd.DataFrame(nav_history).set_index("Date")
    
    # Calculate performance metrics
    total_days = (df_nav.index[-1] - df_nav.index[0]).days
    years = total_days / 365.25
    final_nav = df_nav["NAV"].iloc[-1]
    total_return = (final_nav / initial_cap) - 1.0
    cagr = (final_nav / initial_cap) ** (1.0 / years) - 1.0
    
    df_nav["Return"] = df_nav["NAV"].pct_change()
    ann_vol = df_nav["Return"].std() * np.sqrt(252)
    sharpe = (cagr - 0.045) / ann_vol if ann_vol > 0 else np.nan
    
    running_max = df_nav["NAV"].cummax()
    drawdowns = (df_nav["NAV"] - running_max) / running_max
    max_dd = drawdowns.min()
    
    print("\n" + "="*50)
    print(f"BOLLINGER + FIBONACCI CONFLUENCE METRICS ({ticker})")
    print("="*50)
    print(f"Backtest Period:   {df_nav.index[0].strftime('%Y-%m-%d')} to {df_nav.index[-1].strftime('%Y-%m-%d')}")
    print(f"Initial Capital:   ${initial_cap:,.2f} USD")
    print(f"Final Value:       ${final_nav:,.2f} USD")
    print(f"Cumulative Return: {total_return*100:+.2f}%")
    print(f"Annualized CAGR:   {cagr*100:.2f}%")
    print(f"Volatility (Ann):  {ann_vol*100:.2f}%")
    print(f"Sharpe Ratio (Rf=4.5%): {sharpe:.4f}")
    print(f"Max Drawdown:      {max_dd*100:.2f}%")
    print(f"Total Trades:      {len(trade_logs)}")
    print("="*50)
    
    # Print recent trades
    if len(trade_logs) > 0:
        print("\nRecent simulated trades:")
        for log in trade_logs[-5:]:
            print(log)

if __name__ == "__main__":
    main()
