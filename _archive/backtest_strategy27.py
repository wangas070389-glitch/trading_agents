"""
Strategy 27: Golden Hurst Exponent Regime System
===============================================
Trades daily QQQ / TQQQ / SQQQ in MXN using Golden Ratio parameters:
  - Hurst Exponent Window: 55 days
  - Dual EMA Filter: 21 EMA vs 55 EMA
"""
import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

TRADING_DAYS = 252
TRANSACTION_COST = 0.0029
BONDIA_YIELD = 0.0653
RF_MXN = 0.095

def calculate_hurst_exponent_rolling(log_prices, window_size=55, max_lag=20):
    n = len(log_prices)
    hurst_values = np.full(n, 0.5)
    lags = np.arange(2, max_lag)
    log_lags = np.log(lags)
    log_lags_mean = np.mean(log_lags)
    log_lags_variance = np.sum((log_lags - log_lags_mean) ** 2)
    
    for i in range(window_size, n):
        sub_series = log_prices[i - window_size : i]
        log_stds = []
        valid = True
        for lag in lags:
            diff = sub_series[lag:] - sub_series[:-lag]
            std_val = np.std(diff)
            if std_val > 0:
                log_stds.append(np.log(std_val))
            else:
                valid = False
                break
        if not valid:
            continue
        log_stds = np.array(log_stds)
        covariance = np.sum((log_lags - log_lags_mean) * (log_stds - np.mean(log_stds)))
        slope = covariance / log_lags_variance
        hurst_values[i] = np.clip(slope, 0.0, 1.0)
    return hurst_values

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    start_date = "2010-02-11"
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    print("Downloading daily QQQ, TQQQ, SQQQ and FX data...")
    qqq = yf.download("QQQ", start=start_date, end=end_date, progress=False)
    tqqq = yf.download("TQQQ", start=start_date, end=end_date, progress=False)
    sqqq = yf.download("SQQQ", start=start_date, end=end_date, progress=False)
    fx = yf.download("MXN=X", start=start_date, end=end_date, progress=False)
    
    for df in (qqq, tqqq, sqqq, fx):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
            
    dates = qqq.index.intersection(tqqq.index).intersection(fx.index)
    prices = qqq["Close"].reindex(dates).values
    tqqq_mxn = ((1.0 + tqqq["Close"].pct_change().fillna(0.0)) * (1.0 + fx["Close"].pct_change().fillna(0.0)) - 1.0).reindex(dates).values
    sqqq_mxn = ((1.0 + sqqq["Close"].pct_change().fillna(0.0)) * (1.0 + fx["Close"].pct_change().fillna(0.0)) - 1.0).reindex(dates).values
    
    n = len(dates)
    log_prices = np.log(prices)
    hurst = calculate_hurst_exponent_rolling(log_prices, window_size=55)
    
    # 21 vs 55 EMA Trend filter
    ma_fast = qqq["Close"].ewm(span=21, adjust=False).mean().reindex(dates).values
    ma_slow = qqq["Close"].ewm(span=55, adjust=False).mean().reindex(dates).values
    
    daily_cash_sweep = BONDIA_YIELD / TRADING_DAYS
    nav = np.zeros(n)
    initial_nav = 200000.0
    nav[0] = initial_nav
    position = 0 # 0=Cash, 1=TQQQ, 2=SQQQ
    
    for t in range(1, n):
        h_t = hurst[t-1]
        fast_t = ma_fast[t-1]
        slow_t = ma_slow[t-1]
        
        target_pos = position
        if h_t > 0.52:
            if fast_t > slow_t:
                target_pos = 1
            else:
                target_pos = 2
        else:
            target_pos = 0
            
        ret = daily_cash_sweep
        if position == 1:
            ret = tqqq_mxn[t]
        elif position == 2:
            ret = sqqq_mxn[t]
            
        fee = nav[t-1] * TRANSACTION_COST if target_pos != position else 0.0
        nav[t] = nav[t-1] * (1.0 + ret) - fee
        position = target_pos
        
    # Save CSV
    pd.DataFrame(nav, index=dates, columns=["strategy"]).to_csv(os.path.join(dir_path, "strategy27_backtest_nav.csv"))
    
    # Calculate performance metrics
    nav_series = pd.Series(nav, index=dates)
    total_ret = nav_series.iloc[-1] / nav_series.iloc[0] - 1.0
    years = (nav_series.index[-1] - nav_series.index[0]).days / 365.25
    cagr = (nav_series.iloc[-1] / nav_series.iloc[0]) ** (1.0 / years) - 1.0
    daily_rets = nav_series.pct_change().dropna()
    vol = daily_rets.std() * np.sqrt(252)
    sharpe = (cagr - RF_MXN) / vol if vol > 0 else np.nan
    roll_max = nav_series.cummax()
    max_dd = float(((nav_series - roll_max) / roll_max).min())
    
    # Write report
    with open(os.path.join(dir_path, "strategy27_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(f"# Strategy 27: Golden Hurst Exponent Backtest Report\n\n")
        f.write(f"**Period:** {dates[0].date()} to {dates[-1].date()}\n")
        f.write(f"**Capital Allocated:** $200,000.00 MXN\n\n")
        f.write(f"## Key Performance Metrics\n\n")
        f.write(f"- **Final Portfolio Value:** ${nav[-1]:,.2f} MXN\n")
        f.write(f"- **Total Return:** {total_ret*100:+.2f}%\n")
        f.write(f"- **CAGR:** {cagr*100:.2f}%\n")
        f.write(f"- **Annualized Volatility:** {vol*100:.2f}%\n")
        f.write(f"- **Sharpe Ratio:** {sharpe:.4f}\n")
        f.write(f"- **Maximum Drawdown:** {max_dd*100:.2f}%\n")
        
    print("Strategy 27 Backtest Completed Successfully.")

if __name__ == "__main__":
    main()
