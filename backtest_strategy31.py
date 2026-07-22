import os
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.signal import savgol_coeffs

TRADING_DAYS = 252
TRANSACTION_COST = 0.0029
BONDIA_YIELD = 0.0653
RF_MXN = 0.095

def calculate_savgol_rolling(prices, window_length, polyorder=3):
    n = len(prices)
    smooth = np.full(n, np.nan)
    deriv1 = np.full(n, np.nan)
    deriv2 = np.full(n, np.nan)
    
    coeffs0 = savgol_coeffs(window_length, polyorder, deriv=0, pos=0)
    coeffs1 = -savgol_coeffs(window_length, polyorder, deriv=1, pos=0)
    coeffs2 = savgol_coeffs(window_length, polyorder, deriv=2, pos=0)
    
    for i in range(window_length - 1, n):
        window = prices[i - window_length + 1 : i + 1]
        smooth[i] = np.dot(coeffs0, window)
        deriv1[i] = np.dot(coeffs1, window)
        deriv2[i] = np.dot(coeffs2, window)
        
    return smooth, deriv1, deriv2

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, adjust=False).mean()
    avg_loss = loss.ewm(com=period-1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1.0 + rs.fillna(0)))
    return rsi

def run_simulation():
    ticker = "QQQ"
    start_date = "2010-01-01"
    end_date = "2026-07-10"
    
    print(f"Downloading historical data for S31 backtest...")
    df = yf.download(["QQQ", "TQQQ", "SQQQ", "USDMXN=X"], start=start_date, end=end_date, progress=False)
    if df.empty:
        print("Failed to download data.")
        return
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [f"{col[0]}_{col[1]}".lower() for col in df.columns]
        
    # Squeeze if needed, map close prices
    df = df.rename(columns={
        "close_qqq": "qqq",
        "close_tqqq": "tqqq",
        "close_sqqq": "sqqq",
        "close_usdmxn=x": "fx",
        "high_qqq": "qqq_high",
        "low_qqq": "qqq_low"
    })
    
    # Fill any empty values
    df = df.ffill().dropna(subset=["qqq"])
    
    # Exogenous FX rates
    df["fx"] = df["fx"].fillna(17.43)
    
    n_days = len(df)
    prices = df["qqq"].values
    highs = df["qqq_high"].values
    lows = df["qqq_low"].values
    
    # 1. Short-term Savitzky-Golay Support & Resistance
    savgol_win = 13
    smooth, deriv1, deriv2 = calculate_savgol_rolling(prices, savgol_win, polyorder=3)
    
    support_levels = np.full(n_days, np.nan)
    resistance_levels = np.full(n_days, np.nan)
    curr_support = np.nan
    curr_resistance = np.nan
    last_sup_idx = None
    last_res_idx = None
    
    for i in range(savgol_win, n_days):
        if deriv1[i-1] < 0 and deriv1[i] >= 0 and deriv2[i] > 0:
            curr_support = prices[i]
            last_sup_idx = i
        elif deriv1[i-1] > 0 and deriv1[i] <= 0 and deriv2[i] < 0:
            curr_resistance = prices[i]
            last_res_idx = i
            
        # Resolve inverted bounds
        if not np.isnan(curr_support) and not np.isnan(curr_resistance):
            if curr_support >= curr_resistance:
                if last_res_idx is not None and last_res_idx < i:
                    curr_support = float(np.min(prices[last_res_idx : i + 1]))
                elif last_sup_idx is not None and last_sup_idx < i:
                    curr_resistance = float(np.max(prices[last_sup_idx : i + 1]))
                    
        support_levels[i] = curr_support
        resistance_levels[i] = curr_resistance
        
    # SRP Calculation
    srp = np.full(n_days, 0.5)
    for i in range(n_days):
        sup = support_levels[i]
        res = resistance_levels[i]
        if not np.isnan(sup) and not np.isnan(res) and res > sup:
            srp[i] = (prices[i] - sup) / (res - sup)
            
    # 2. Macro Swing Grid (55-day lookback)
    macro_win = 55
    df["Swing_High"] = df["qqq_high"].rolling(macro_win).max()
    df["Swing_Low"] = df["qqq_low"].rolling(macro_win).min()
    df["RSI"] = calculate_rsi(df["qqq"], 14)
    
    swing_high = df["Swing_High"].values
    swing_low = df["Swing_Low"].values
    rsi = df["RSI"].values
    
    # 3. Simulate execution loop (MXN denominated)
    initial_nav = 200000.0
    nav = np.zeros(n_days)
    nav[0] = initial_nav
    positions = np.zeros(n_days, dtype=int) # 0 = Cash, 1 = TQQQ, 2 = SQQQ
    current_asset = 0
    n_trades = 0
    total_fees_paid = 0.0
    
    # Return rates in MXN
    r_qqq = df["qqq"].pct_change().fillna(0.0)
    r_fx = df["fx"].pct_change().fillna(0.0)
    r_tqqq_real = df["tqqq"].pct_change().fillna(0.0)
    r_sqqq_real = df["sqqq"].pct_change().fillna(0.0)
    
    tqqq_drag = (2.0 * 0.045 + 0.0095) / TRADING_DAYS
    sqqq_drag = (2.0 * 0.055 + 0.0095) / TRADING_DAYS
    r_tqqq_synth = 3.0 * r_qqq - tqqq_drag
    r_sqqq_synth = -3.0 * r_qqq - sqqq_drag
    
    r_tqqq = np.where(df["tqqq"].notna() & (r_tqqq_real != 0.0), r_tqqq_real, r_tqqq_synth)
    r_sqqq = np.where(df["sqqq"].notna() & (r_sqqq_real != 0.0), r_sqqq_real, r_sqqq_synth)
    
    r_qqq_mxn = ((1.0 + r_qqq) * (1.0 + r_fx) - 1.0).values
    r_tqqq_mxn = ((1.0 + r_tqqq) * (1.0 + r_fx) - 1.0).values
    r_sqqq_mxn = ((1.0 + r_sqqq) * (1.0 + r_fx) - 1.0).values
    
    daily_cash_sweep = BONDIA_YIELD / TRADING_DAYS
    
    for t in range(1, n_days):
        px = prices[t-1]
        sup = support_levels[t-1]
        res = resistance_levels[t-1]
        curr_rsi = rsi[t-1]
        curr_srp = srp[t-1]
        
        sw_high = swing_high[t-1]
        sw_low = swing_low[t-1]
        
        target_asset = current_asset
        
        if not np.isnan(sup) and not np.isnan(res) and not np.isnan(sw_high) and not np.isnan(sw_low) and sw_high > sw_low:
            # Macro Fibonacci Retracements
            macro_range = sw_high - sw_low
            f50 = sw_high - 0.500 * macro_range
            f618 = sw_high - 0.618 * macro_range
            f382 = sw_high - 0.382 * macro_range
            
            # Confluence filter (Is support close to a key Fib level?)
            fib_levels = [f382, f50, f618]
            is_support_confluence = any(abs(sup - f) / f < 0.015 for f in fib_levels)
            is_resistance_confluence = any(abs(res - f) / f < 0.015 for f in fib_levels)
            
            # Triggers
            is_buy = is_support_confluence and (curr_srp < 0.20) and (curr_rsi < 45)
            is_sell = is_resistance_confluence and (curr_srp > 0.80) and (curr_rsi > 60)
            
            # Stop loss checks (Exit to cash if breaches the swing low / 78.6%)
            f786 = sw_high - 0.786 * macro_range
            
            if is_buy:
                target_asset = 1 # TQQQ
            elif is_sell:
                target_asset = 0 # Exit to Cash
            else:
                # Normal stops
                if current_asset == 1 and (px < f786 or curr_rsi > 70):
                    target_asset = 0
                elif current_asset == 2 and (px > f382 or curr_rsi < 30):
                    target_asset = 0
        else:
            target_asset = 0
            
        positions[t] = target_asset
        
        if target_asset == 0:
            ret = daily_cash_sweep
        elif target_asset == 1:
            ret = r_qqq_mxn[t]
        elif target_asset == 2:
            ret = r_sqqq_mxn[t]
            
        fee = 0.0
        if target_asset != current_asset:
            n_trades += 1
            fee = nav[t-1] * TRANSACTION_COST
            total_fees_paid += fee
            
        nav[t] = nav[t-1] * (1.0 + ret) - fee
        current_asset = target_asset
        
    df["nav"] = nav
    df["position"] = positions
    
    # Calculate Metrics
    final_nav = nav[-1]
    years = (df.index[-1] - df.index[0]).days / 365.25
    cagr = (final_nav / initial_nav) ** (1.0 / years) - 1.0
    
    df["return"] = df["nav"].pct_change().dropna()
    ann_vol = df["return"].std() * np.sqrt(TRADING_DAYS)
    sharpe = (cagr - RF_MXN) / ann_vol if ann_vol > 0 else np.nan
    
    running_max = df["nav"].cummax()
    drawdowns = (df["nav"] - running_max) / running_max
    max_dd = drawdowns.min()
    
    # Benchmark
    df["benchmark"] = initial_nav * (1.0 + r_qqq_mxn).cumprod()
    bench_final = df["benchmark"].iloc[-1]
    bench_cagr = (bench_final / initial_nav) ** (1.0 / years) - 1.0
    df["bench_return"] = df["benchmark"].pct_change()
    bench_vol = df["bench_return"].std() * np.sqrt(TRADING_DAYS)
    bench_sharpe = (bench_cagr - RF_MXN) / bench_vol if bench_vol > 0 else np.nan
    bench_roll_max = df["benchmark"].cummax()
    bench_max_dd = ((df["benchmark"] - bench_roll_max) / bench_roll_max).min()
    
    print("\n" + "="*50)
    print("S31 BACKTEST COMPLETE")
    print("="*50)
    print(f"Final NAV:       ${final_nav:,.2f} MXN")
    print(f"CAGR:           {cagr*100:.2f}% (Bench: {bench_cagr*100:.2f}%)")
    print(f"Sharpe (Rf=9.5%): {sharpe:.4f} (Bench: {bench_sharpe:.4f})")
    print(f"Max Drawdown:    {max_dd*100:.2f}% (Bench: {bench_max_dd*100:.2f}%)")
    print(f"Total Trades:    {n_trades}")
    print("="*50)
    
    # Save Report
    with open("strategy31_backtest_report.md", "w", encoding="utf-8") as f:
        f.write(f"""# Strategy 31 Backtest Report (Fibonacci S&R Reversal)
**Executed:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')} ({years:.2f} Years)

## Performance Comparison
| Metric | Strategy 31 (Fibonacci S&R Reversal) | Benchmark (QQQ Buy-and-Hold) |
| :--- | :---: | :---: |
| **Final Portfolio NAV** | ${final_nav:,.2f} MXN | ${bench_final:,.2f} MXN |
| **Cumulative Return** | +{((final_nav/initial_nav)-1.0)*100:.2f}% | +{((bench_final/initial_nav)-1.0)*100:.2f}% |
| **CAGR** | +{cagr*100:.2f}% | +{bench_cagr*100:.2f}% |
| **Annualized Volatility** | {ann_vol*100:.2f}% | {bench_vol*100:.2f}% |
| **Sharpe Ratio (Rf=9.5%)** | {sharpe:.2f} | {bench_sharpe:.2f} |
| **Maximum Drawdown** | {max_dd*100:.2f}% | {bench_max_dd*100:.2f}% |

## Execution Statistics
* **Starting Capital:** ${initial_nav:,.2f} MXN
* **Total Transactions:** {n_trades} trades
* **Total Fees Paid:** ${total_fees_paid:,.2f} MXN
""")

if __name__ == "__main__":
    run_simulation()
