import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM

def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
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

def calculate_cci(df, period=10):
    tp = (df['High'] + df['Low'] + df['Close']) / 3.0
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma) / (0.015 * mad)
    return cci.fillna(0.0)

def calculate_adx(df, period=7):
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    tr_smooth = tr.rolling(window=period).mean()
    plus_dm_smooth = pd.Series(plus_dm, index=df.index).rolling(window=period).mean()
    minus_dm_smooth = pd.Series(minus_dm, index=df.index).rolling(window=period).mean()
    
    plus_di = (plus_dm_smooth / tr_smooth) * 100.0
    minus_di = (minus_dm_smooth / tr_smooth) * 100.0
    
    dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di).replace(0.0, np.nan)) * 100.0
    adx = dx.rolling(window=period).mean()
    
    return adx.fillna(20.0), plus_di.fillna(0.0), minus_di.fillna(0.0)

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print("DIRECT ASSET STRATEGY 11: CCI-ADX LEVERAGED BACKTEST")
    print("=" * 80)
    
    # 1. Download daily SPY returns for HMM regime checks
    print("Downloading historical daily SPY returns for HMM training (2 years)...")
    spy_daily = yf.download("SPY", start="2024-05-01", end="2026-07-01", interval="1d", progress=False)
    spy_daily.columns = [c[0] if isinstance(c, tuple) else c for c in spy_daily.columns]
    spy_daily_returns = spy_daily["Close"].ffill().pct_change().dropna()
    spy_rets_vals = spy_daily_returns.values.reshape(-1, 1)
    
    hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
    hmm.fit(spy_rets_vals)
    regimes = hmm.predict(spy_rets_vals)
    
    state_means = [np.mean(spy_rets_vals[regimes == i]) for i in range(3)]
    state_vols = [np.std(spy_rets_vals[regimes == i]) for i in range(3)]
    
    bear_state = np.argmax(state_vols)
    rem = [i for i in range(3) if i != bear_state]
    bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
    
    daily_regimes = {}
    for date, state in zip(spy_daily_returns.index, regimes):
        date_str = date.strftime("%Y-%m-%d")
        if state == bull_state:
            daily_regimes[date_str] = 0  # Bull
        elif state == bear_state:
            daily_regimes[date_str] = 1  # Bear
        else:
            daily_regimes[date_str] = 2  # Chop
            
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
    
    # Calculate indicators directly on TQQQ and SQQQ
    tqqq["ATR"] = calculate_atr(tqqq, period=14)
    tqqq["CCI"] = calculate_cci(tqqq, period=10)
    adx_t, plus_di_t, minus_di_t = calculate_adx(tqqq, period=7)
    tqqq["ADX"] = adx_t
    tqqq["DI+"] = plus_di_t
    tqqq["DI-"] = minus_di_t
    
    sqqq["ATR"] = calculate_atr(sqqq, period=14)
    sqqq["CCI"] = calculate_cci(sqqq, period=10)
    adx_s, plus_di_s, minus_di_s = calculate_adx(sqqq, period=7)
    sqqq["ADX"] = adx_s
    sqqq["DI+"] = plus_di_s
    sqqq["DI-"] = minus_di_s
    
    # Merge datasets
    merged = qqq[["Close", "High", "Low", "Volume"]].join(
        tqqq[["Close", "ATR", "CCI", "ADX", "DI+", "DI-"]], lsuffix="_QQQ", rsuffix="_TQQQ"
    ).join(
        sqqq[["Close", "ATR", "CCI", "ADX", "DI+", "DI-"]], rsuffix="_SQQQ"
    )
    merged.columns = [
        "Close_QQQ", "High_QQQ", "Low_QQQ", "Volume_QQQ",
        "Close_TQQQ", "ATR_TQQQ", "CCI_TQQQ", "ADX_TQQQ", "DI+_TQQQ", "DI-_TQQQ",
        "Close_SQQQ", "ATR_SQQQ", "CCI_SQQQ", "ADX_SQQQ", "DI+_SQQQ", "DI-_SQQQ"
    ]
    merged = merged.dropna()
    
    # Backtest parameters
    INITIAL_NAV = 200000.0  # MXN
    commission_rate = 0.0000  # Alpaca commission-free
    rf_annual = 0.095
    rf_daily = rf_annual / 252.0
    
    cash = INITIAL_NAV
    portfolio_value = INITIAL_NAV
    
    active_position = None  
    
    nav_history = []
    dates_list = []
    regimes_list = []
    
    merged["DateOnly"] = merged.index.strftime("%Y-%m-%d")
    grouped = merged.groupby("DateOnly")
    
    trade_logs = []
    
    for date_str, group in grouped:
        regime = daily_regimes.get(date_str, 2)
        
        # Calculate daily variables
        cash = cash * (1.0 + rf_daily / 13.0)
        daily_high_qqq = float(group["High_QQQ"].max())
        daily_low_qqq = group["Low_QQQ"].min()
        
        for i in range(len(group)):
            bar_time = group.index[i]
            
            close_qqq = float(group["Close_QQQ"].iloc[i])
            
            close_tqqq = float(group["Close_TQQQ"].iloc[i])
            cci_tqqq = float(group["CCI_TQQQ"].iloc[i])
            adx_tqqq = float(group["ADX_TQQQ"].iloc[i])
            di_plus_t = float(group["DI+_TQQQ"].iloc[i])
            di_minus_t = float(group["DI-_TQQQ"].iloc[i])
            atr_tqqq = float(group["ATR_TQQQ"].iloc[i])
            
            close_sqqq = float(group["Close_SQQQ"].iloc[i])
            cci_sqqq = float(group["CCI_SQQQ"].iloc[i])
            adx_sqqq = float(group["ADX_SQQQ"].iloc[i])
            di_plus_s = float(group["DI+_SQQQ"].iloc[i])
            di_minus_s = float(group["DI-_SQQQ"].iloc[i])
            atr_sqqq = float(group["ATR_SQQQ"].iloc[i])
            
            is_eod = (bar_time.hour == 15 and bar_time.minute == 30) or i == (len(group) - 1)
            
            # Valuate active positions
            current_portfolio_value = cash
            if active_position:
                current_price = close_tqqq if active_position["side"] == "long" else close_sqqq
                active_position["peak_price"] = max(active_position["peak_price"], current_price)
                
                # Trailing Stop exit
                atr_exec = atr_tqqq if active_position["side"] == "long" else atr_sqqq
                stop_threshold = active_position["peak_price"] - 1.5 * atr_exec
                is_stop_out = current_price < stop_threshold
                
                current_portfolio_value += active_position["shares"] * current_price
                
                if is_stop_out or is_eod:
                    should_hold_overnight = False
                    if is_eod and not is_stop_out:
                        trade_profit = (current_price > active_position["entry_price"])
                        # Determine overnight hold based on index closing state
                        if trade_profit:
                            if active_position["side"] == "long" and close_qqq >= (daily_high_qqq - 0.005 * daily_high_qqq) and (regime == 0 or regime == 2):
                                should_hold_overnight = True
                            elif active_position["side"] == "short" and close_qqq <= (daily_low_qqq + 0.005 * daily_low_qqq) and (regime == 1 or regime == 2):
                                should_hold_overnight = True
                                
                    if not should_hold_overnight:
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
                        
            # Trigger entries
            if not active_position and not is_eod:
                # 1. Breakout long TQQQ (Bull state, TQQQ breakout)
                if (regime == 0 or regime == 2) and adx_tqqq >= 22.0 and cci_tqqq > 100.0 and di_plus_t > di_minus_t:
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
                        "action": "BUY_TQQQ_TREND_BREAKOUT",
                        "price": close_tqqq,
                        "pnl": 0.0
                    })
                # 2. Breakout SQQQ (Bear state, SQQQ breakout)
                elif (regime == 1 or regime == 2) and adx_sqqq >= 22.0 and cci_sqqq > 100.0 and di_plus_s > di_minus_s:
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
                        "action": "BUY_SQQQ_TREND_BREAKDOWN",
                        "price": close_sqqq,
                        "pnl": 0.0
                    })
                # 3. Mean Reversion Long Pullback (CCI < -150 on TQQQ)
                elif adx_tqqq < 22.0 and cci_tqqq < -150.0:
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
                        "action": "BUY_TQQQ_CCI_REVERSION",
                        "price": close_tqqq,
                        "pnl": 0.0
                    })
                # 4. Mean Reversion Short Pullback (CCI < -150 on SQQQ)
                # When SQQQ is oversold (CCI < -150), it means market spiked up, we buy SQQQ as it reverts down?
                # No, if SQQQ's CCI < -150, SQQQ is extremely oversold, so we buy SQQQ expecting QQQ to revert down!
                elif adx_sqqq < 22.0 and cci_sqqq < -150.0:
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
                        "action": "BUY_SQQQ_CCI_REVERSION",
                        "price": close_sqqq,
                        "pnl": 0.0
                    })
            elif active_position and not is_eod:
                side = active_position["side"]
                # Settle at CCI zero
                if side == "long":
                    if cci_tqqq >= 0.0:
                        val_credited = active_position["shares"] * close_tqqq * (1.0 - commission_rate)
                        cash += val_credited
                        pnl = val_credited - active_position["allocated"]
                        trade_logs.append({
                            "date": date_str,
                            "time": bar_time.strftime("%H:%M"),
                            "action": "SETTLE_LONG_CCI_ZERO",
                            "price": close_tqqq,
                            "pnl": pnl
                        })
                        active_position = None
                        current_portfolio_value = cash
                else:
                    if cci_sqqq >= 0.0:
                        val_credited = active_position["shares"] * close_sqqq * (1.0 - commission_rate)
                        cash += val_credited
                        pnl = val_credited - active_position["allocated"]
                        trade_logs.append({
                            "date": date_str,
                            "time": bar_time.strftime("%H:%M"),
                            "action": "SETTLE_SHORT_CCI_ZERO",
                            "price": close_sqqq,
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
    print("STRATEGY 11: DIRECT ASSET CCI SIMULATION SUMMARY")
    print("=" * 60)
    print(f"  Final Portfolio NAV:  ${final_nav:,.2f} MXN")
    print(f"  Total Return:         {total_ret*100:.2f}%")
    print(f"  Time-Weighted CAGR:   {cagr*100:.2f}%")
    print(f"  Annual Volatility:    {ann_vol*100:.2f}%")
    print(f"  Sharpe Ratio (Rf=9.5%): {sharpe:.2f}")
    print(f"  Maximum Drawdown:     {max_dd*100:.2f}%")
    print("=" * 60 + "\n")
    
    # Save CSV
    csv_path = os.path.join(dir_path, "strategy11_backtest_nav.csv")
    df_nav.to_csv(csv_path)
    
    # Generate report
    report_path = os.path.join(dir_path, "strategy11_backtest_report.md")
    report = f"""# Strategy 11: Intraday Direct Asset CCI-ADX Leveraged Report
**Simulation Period:** {df_nav.index[0].date()} to {df_nav.index[-1].date()} ({years*365.25:.1f} Days)
**Assets Traded:** TQQQ & SQQQ based on direct asset indicators.

## 1. Performance Summary
* **Final Portfolio NAV**: ${final_nav:,.2f} MXN
* **Total Return**: {total_ret*100:.2f}%
* **Time-Weighted CAGR**: **{cagr*100:.2f}%**
* **Annualized Volatility**: {ann_vol*100:.2f}%
* **Sharpe Ratio**: **{sharpe:.2f}**
* **Maximum Drawdown**: **{max_dd*100:.2f}%**

## 2. Dynamic Settings
* **CCI Channels (10-period):** Breakout $\pm 100$, Reversion $\pm 150$ (Direct traded assets)
* **ADX Trend strength (7-period):** Threshold 22.0
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

def run_strategy11_backtest_for_api():
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
            "note": "Direct CCI-ADX"
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
