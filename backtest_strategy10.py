import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM

def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)
    return df

def calculate_atr(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.fillna(tr.expanding().mean())

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print("UPGRADED STRATEGY 10: INTRADAY VWAP LEVERAGED BACKTEST")
    print("=" * 80)
    
    # 1. Download daily SPY data for HMM training
    print("Downloading historical daily SPY returns for HMM training (2 years)...")
    spy_daily = yf.download("SPY", start="2024-05-01", end="2026-07-01", interval="1d", progress=False)
    spy_daily.columns = [c[0] if isinstance(c, tuple) else c for c in spy_daily.columns]
    spy_daily_returns = spy_daily["Close"].ffill().pct_change().dropna()
    pass
            
    # 2. Download Intraday QQQ, TQQQ, SQQQ 30-minute bars
    print("\nDownloading QQQ, TQQQ, SQQQ 30m intraday bars (60 days)...")
    qqq = yf.download("QQQ", period="60d", interval="30m", progress=False)
    tqqq = yf.download("TQQQ", period="60d", interval="30m", progress=False)
    sqqq = yf.download("SQQQ", period="60d", interval="30m", progress=False)
    
    if isinstance(qqq.columns, pd.MultiIndex): qqq.columns = [c[0] for c in qqq.columns]
    if isinstance(tqqq.columns, pd.MultiIndex): tqqq.columns = [c[0] for c in tqqq.columns]
    if isinstance(sqqq.columns, pd.MultiIndex): sqqq.columns = [c[0] for c in sqqq.columns]
    
    qqq = _strip_tz(qqq)
    tqqq = _strip_tz(tqqq)
    sqqq = _strip_tz(sqqq)
    
    # Calculate indicators
    qqq["ATR"] = calculate_atr(qqq, period=14)
    tqqq["ATR"] = calculate_atr(tqqq, period=14)
    sqqq["ATR"] = calculate_atr(sqqq, period=14)
    
    # Merge datasets to align timestamps
    merged = qqq[["Close", "High", "Low", "Volume", "ATR"]].join(
        tqqq[["Close", "ATR"]], lsuffix="_QQQ", rsuffix="_TQQQ"
    ).join(
        sqqq[["Close", "ATR"]], rsuffix="_SQQQ"
    )
    merged.columns = ["Close_QQQ", "High_QQQ", "Low_QQQ", "Volume_QQQ", "ATR_QQQ", "Close_TQQQ", "ATR_TQQQ", "Close_SQQQ", "ATR_SQQQ"]
    merged = merged.dropna()
    
    # Backtest parameters
    INITIAL_NAV = 200000.0  # MXN
    commission_rate = 0.0000  # Alpaca commission-free
    rf_annual = 0.095
    rf_daily = rf_annual / 252.0
    
    cash = INITIAL_NAV
    portfolio_value = INITIAL_NAV
    
    # Position state
    active_position = None  
    
    # Record tracking lists
    nav_history = []
    dates_list = []
    regimes_list = []
    
    merged["DateOnly"] = merged.index.strftime("%Y-%m-%d")
    grouped = merged.groupby("DateOnly")
    
    trade_logs = []
    
    for date_str, group in grouped:
        # Fit HMM dynamically on historical daily returns up to yesterday
        cutoff_date = pd.to_datetime(date_str)
        train_rets = spy_daily_returns[spy_daily_returns.index < cutoff_date]
        if len(train_rets) < 100:
            regime = 2
        else:
            train_vals = train_rets.values.reshape(-1, 1)
            hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
            hmm.fit(train_vals)
            regimes = hmm.predict(train_vals)
            
            state_means = [np.mean(train_vals[regimes == i]) for i in range(3)]
            state_vols = [np.std(train_vals[regimes == i]) for i in range(3)]
            
            bear_state = np.argmax(state_vols)
            rem = [i for i in range(3) if i != bear_state]
            bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
            
            last_state = regimes[-1] # state at yesterday's close
            if last_state == bull_state:
                regime = 0
            elif last_state == bear_state:
                regime = 1
            else:
                regime = 2
        
        # Calculate daily variables
        cum_pv = 0.0
        cum_vol = 0.0
        
        # Compounding overnight sweep interest
        cash = cash * (1.0 + rf_daily / 13.0)
        
        # Keep track of daily highs/lows for holding check
        daily_high_qqq = float(group["High_QQQ"].max())
        daily_low_qqq = group["Low_QQQ"].min()
        
        for i in range(len(group)):
            bar_time = group.index[i]
            
            close_qqq = float(group["Close_QQQ"].iloc[i])
            high_qqq = float(group["High_QQQ"].iloc[i])
            low_qqq = float(group["Low_QQQ"].iloc[i])
            vol_qqq = float(group["Volume_QQQ"].iloc[i])
            atr_qqq = float(group["ATR_QQQ"].iloc[i])
            
            close_tqqq = float(group["Close_TQQQ"].iloc[i])
            atr_tqqq = float(group["ATR_TQQQ"].iloc[i])
            
            close_sqqq = float(group["Close_SQQQ"].iloc[i])
            atr_sqqq = float(group["ATR_SQQQ"].iloc[i])
            
            # Intraday VWAP calculations on QQQ index
            cum_pv += ((high_qqq + low_qqq + close_qqq) / 3.0) * vol_qqq
            cum_vol += vol_qqq
            vwap_qqq = cum_pv / cum_vol if cum_vol > 0 else close_qqq
            
            # Tightened bands (1.5 * ATR)
            upper_band = vwap_qqq + 1.5 * atr_qqq
            lower_band = vwap_qqq - 1.5 * atr_qqq
            
            is_eod = (bar_time.hour == 15 and bar_time.minute == 30) or i == (len(group) - 1)
            
            # Valuate active positions
            current_portfolio_value = cash
            if active_position:
                current_price = close_tqqq if active_position["side"] == "long" else close_sqqq
                active_position["peak_price"] = max(active_position["peak_price"], current_price)
                
                # Check Trailing Stop exit
                atr_exec = atr_tqqq if active_position["side"] == "long" else atr_sqqq
                stop_threshold = active_position["peak_price"] - 1.5 * atr_exec
                
                is_stop_out = current_price < stop_threshold
                
                # Valuation
                current_portfolio_value += active_position["shares"] * current_price
                
                # Trigger exits
                if is_stop_out or is_eod:
                    # Overnight Hold Evaluation
                    should_hold_overnight = False
                    if is_eod and not is_stop_out:
                        # Trade must be in profit
                        trade_profit = (current_price > active_position["entry_price"])
                        if trade_profit:
                            if active_position["side"] == "long" and close_qqq >= (daily_high_qqq - 0.005 * daily_high_qqq) and regime == 0:
                                should_hold_overnight = True
                            elif active_position["side"] == "short" and close_qqq <= (daily_low_qqq + 0.005 * daily_low_qqq) and (regime == 1 or regime == 2):
                                should_hold_overnight = True
                                
                    if not should_hold_overnight:
                        # Liquidate
                        val_credited = active_position["shares"] * current_price * (1.0 - commission_rate)
                        cash += val_credited
                        pnl = val_credited - active_position["allocated"]
                        exit_type = "TRAILING_STOP" if is_stop_out else "EOD_CLOSE"
                        
                        trade_logs.append({
                            "date": date_str,
                            "time": bar_time.strftime("%H:%M"),
                            "action": f"EXIT_{active_position['side'].upper()}_{exit_type}",
                            "price": current_price,
                            "pnl": pnl
                        })
                        active_position = None
                        current_portfolio_value = cash
                        
            # Trigger entries (only if no active position)
            if not active_position and not is_eod:
                if regime == 1:
                    # Bear State: Only trade short breaks (SQQQ)
                    if close_qqq < lower_band:
                        alloc = current_portfolio_value * 0.90
                        shares = alloc / (close_sqqq * (1.0 + commission_rate))
                        cash -= alloc
                        active_position = {
                            "side": "short",
                            "shares": shares,
                            "entry_price": close_sqqq,
                            "peak_price": close_sqqq,
                            "allocated": alloc
                        }
                        trade_logs.append({
                            "date": date_str,
                            "time": bar_time.strftime("%H:%M"),
                            "action": "BUY_SQQQ_BEAR_BREAK",
                            "price": close_sqqq,
                            "pnl": 0.0
                        })
                elif regime == 0:
                    # Bull State: Momentum Breakouts
                    if close_qqq > upper_band:
                        # Enter Long TQQQ
                        alloc = current_portfolio_value * 0.90
                        shares = alloc / (close_tqqq * (1.0 + commission_rate))
                        cash -= alloc
                        active_position = {
                            "side": "long",
                            "shares": shares,
                            "entry_price": close_tqqq,
                            "peak_price": close_tqqq,
                            "allocated": alloc
                        }
                        trade_logs.append({
                            "date": date_str,
                            "time": bar_time.strftime("%H:%M"),
                            "action": "BUY_TQQQ_BULL_BREAK",
                            "price": close_tqqq,
                            "pnl": 0.0
                        })
                else:
                    # Chop State: Mean Reversion to VWAP
                    if close_qqq < lower_band:
                        # Buy reversion (Long TQQQ)
                        alloc = current_portfolio_value * 0.90
                        shares = alloc / (close_tqqq * (1.0 + commission_rate))
                        cash -= alloc
                        active_position = {
                            "side": "long",
                            "shares": shares,
                            "entry_price": close_tqqq,
                            "peak_price": close_tqqq,
                            "allocated": alloc
                        }
                        trade_logs.append({
                            "date": date_str,
                            "time": bar_time.strftime("%H:%M"),
                            "action": "BUY_TQQQ_REVERSION",
                            "price": close_tqqq,
                            "pnl": 0.0
                        })
                    elif close_qqq > upper_band:
                        # Short reversion (Buy SQQQ)
                        alloc = current_portfolio_value * 0.90
                        shares = alloc / (close_sqqq * (1.0 + commission_rate))
                        cash -= alloc
                        active_position = {
                            "side": "short",
                            "shares": shares,
                            "entry_price": close_sqqq,
                            "peak_price": close_sqqq,
                            "allocated": alloc
                        }
                        trade_logs.append({
                            "date": date_str,
                            "time": bar_time.strftime("%H:%M"),
                            "action": "BUY_SQQQ_REVERSION",
                            "price": close_sqqq,
                            "pnl": 0.0
                        })
            elif active_position and regime == 2 and not is_eod:
                # Settle at VWAP center line early during chop regime
                side = active_position["side"]
                if (side == "long" and close_qqq >= vwap_qqq) or \
                   (side == "short" and close_qqq <= vwap_qqq):
                    current_price = close_tqqq if side == "long" else close_sqqq
                    val_credited = active_position["shares"] * current_price * (1.0 - commission_rate)
                    cash += val_credited
                    pnl = val_credited - active_position["allocated"]
                    
                    trade_logs.append({
                        "date": date_str,
                        "time": bar_time.strftime("%H:%M"),
                        "action": f"SETTLE_{side.upper()}_VWAP",
                        "price": current_price,
                        "pnl": pnl
                    })
                    active_position = None
                    current_portfolio_value = cash
            
            portfolio_value = current_portfolio_value
            dates_list.append(bar_time)
            nav_history.append(portfolio_value)
            regimes_list.append(regime)
            
    df_nav = pd.DataFrame({
        "Date": dates_list,
        "NAV": nav_history,
        "Regime": regimes_list
    }).set_index("Date")
    
    # Calculate performance metrics
    final_nav = float(df_nav["NAV"].iloc[-1])
    total_ret = (final_nav / INITIAL_NAV) - 1.0
    
    days = (df_nav.index[-1] - df_nav.index[0]).days
    years = max(days / 365.25, 0.01)
    cagr = (final_nav / INITIAL_NAV) ** (1.0 / years) - 1.0
    
    daily_pct = df_nav["NAV"].resample("1D").last().pct_change().dropna()
    ann_vol = daily_pct.std() * np.sqrt(252)
    sharpe = (cagr - rf_annual) / ann_vol if ann_vol > 0 else 0.0
    
    roll_max = df_nav["NAV"].cummax()
    drawdowns = (df_nav["NAV"] - roll_max) / roll_max
    max_dd = float(drawdowns.min())
    
    print("\n" + "=" * 60)
    print("UPGRADED LEVERAGED SIMULATION SUMMARY (TQQQ/SQQQ)")
    print("=" * 60)
    print(f"  Final Portfolio NAV:  ${final_nav:,.2f} MXN")
    print(f"  Total Return:         {total_ret*100:.2f}%")
    print(f"  Time-Weighted CAGR:   {cagr*100:.2f}%")
    print(f"  Annual Volatility:    {ann_vol*100:.2f}%")
    print(f"  Sharpe Ratio (Rf=9.5%): {sharpe:.2f}")
    print(f"  Maximum Drawdown:     {max_dd*100:.2f}%")
    print("=" * 60 + "\n")
    
    # Save CSV
    csv_path = os.path.join(dir_path, "strategy10_backtest_nav.csv")
    df_nav.to_csv(csv_path)
    
    # Generate report
    report_path = os.path.join(dir_path, "strategy10_backtest_report.md")
    report = f"""# Strategy 10: Intraday VWAP Leveraged Breakout & Reversion Report
**Simulation Period:** {df_nav.index[0].date()} to {df_nav.index[-1].date()} ({years*365.25:.1f} Days)
**Assets Traded:** TQQQ (3x Long QQQ) & SQQQ (3x Short QQQ) based on QQQ indicators.

## 1. Upgraded Performance Summary
* **Final Portfolio NAV**: ${final_nav:,.2f} MXN
* **Total Return**: {total_ret*100:.2f}%
* **Time-Weighted CAGR**: **{cagr*100:.2f}%**
* **Annualized Volatility**: {ann_vol*100:.2f}%
* **Sharpe Ratio**: **{sharpe:.2f}**
* **Maximum Drawdown**: **{max_dd*100:.2f}%**

## 2. Updated Settings
* **Conditional Overnight Holds:** ACTIVE (Evaluates day-end trend strength)
* **Entry Band Threshold:** 1.5 * ATR (Tightened)
* **Trailing Stop-Loss:** 1.5 * ATR (Active)
* **Broker Commission Rate:** 0.00% (Alpaca zero-commission)

## 3. Transaction Summary (Last 20 Closed Trades)
| Date | Time | Action | Settle Price | Trade P/L (MXN) |
| :--- | :---: | :---: | ---: | ---: |
"""
    closed_trades = [t for t in trade_logs if t["action"].startswith("EXIT") or t["action"].startswith("SETTLE")]
    for t in closed_trades[-20:]:
        sign = "+" if t["pnl"] >= 0 else ""
        report += f"| {t['date']} | {t['time']} | {t['action']} | ${t['price']:.2f} | {sign}${t['pnl']:,.2f} |\n"
        
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    return {
        "df_nav": df_nav,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "trade_logs": trade_logs
    }

def run_strategy10_backtest_for_api():
    res = main()
    df_nav = res["df_nav"]
    initial_nav = float(df_nav["NAV"].iloc[0])
    
    # Compounding cash values (9.5% APR)
    cash_values = []
    curr_c = initial_nav
    for val in df_nav["NAV"]:
        cash_values.append(curr_c)
        curr_c *= (1.0 + 0.095 / (252.0 * 13.0))
        
    # Benchmark (11% APR)
    bench_values = []
    curr_b = initial_nav
    for val in df_nav["NAV"]:
        bench_values.append(curr_b)
        curr_b *= (1.0 + 0.11 / (252.0 * 13.0))
        
    ui_trade_log = []
    closed_trades = [t for t in res["trade_logs"] if t["action"].startswith("EXIT") or t["action"].startswith("SETTLE")]
    for t in closed_trades[-30:]:
        ui_trade_log.append({
            "date": t["date"] + " " + t["time"],
            "ticker": "TQQQ/SQQQ",
            "action": t["action"],
            "shares": 0.0,
            "price": float(t["price"]),
            "pnl": float(t["pnl"]),
            "note": "Upgraded Intraday Alpha"
        })
        
    return {
        "dates": [d.strftime("%Y-%m-%d %H:%M") for d in df_nav.index],
        "strategy": [float(x) for x in df_nav["NAV"].values],
        "cash": [float(x) for x in cash_values],
        "benchmark": [float(x) for x in bench_values],
        "trade_log": ui_trade_log,
        "metrics": {
            "strategy_return": float((df_nav["NAV"].iloc[-1] / initial_nav - 1.0) * 100),
            "strategy_cagr": float(res["cagr"] * 100),
            "cash_return": float((cash_values[-1] / initial_nav - 1.0) * 100),
            "benchmark_return": float((bench_values[-1] / initial_nav - 1.0) * 100),
            "benchmark_cagr": 11.0,
            "sharpe": float(res["sharpe"]),
            "drawdown": float(res["max_dd"] * 100),
            "n_trades": len(closed_trades),
            "win_rate": float(sum(1 for t in closed_trades if t["pnl"] > 0) / len(closed_trades) * 100) if closed_trades else 50.0,
            "total_fees": 0.0,
            "total_pnl": float(df_nav["NAV"].iloc[-1] - initial_nav)
        }
    }

if __name__ == "__main__":
    main()
