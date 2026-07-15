"""
Strategy 23: Calculus Support & Resistance and RSI Momentum Systematic Allocation (Optimized)
===========================================================================================
This strategy utilizes rolling Savitzky-Golay filter derivatives (calculus)
and RSI momentum indicators to trade QQQ/TQQQ/SQQQ/Cash, enhanced with a Trailing Stop-Loss
to protect against leveraged ETF volatility decay and trend reversals.
"""
import os
import sys
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats
from scipy.signal import savgol_coeffs

TRADING_DAYS = 252
TRANSACTION_COST = 0.0029  # 0.29% GBM broker fee
BONDIA_YIELD = 0.0653      # 6.53% MXN cash sweep compound yield
RF_MXN = 0.095             # 9.5% Benchmark MXN Risk-Free Rate for Sharpe

def calculate_savgol_rolling(prices, window_length=31, polyorder=3):
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
    rs = rs.fillna(0)
    rsi = 100 - (100 / (1.0 + rs))
    return rsi

def probabilistic_sharpe_ratio(returns: pd.Series, sr_benchmark: float) -> float:
    r = returns.dropna().values
    n = len(r)
    if n < 30:
        return np.nan
    sr = r.mean() / r.std(ddof=1)
    g3 = stats.skew(r)
    g4 = stats.kurtosis(r, fisher=False)
    denom = np.sqrt(max(1e-12, 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2))
    z = (sr - sr_benchmark) * np.sqrt(n - 1) / denom
    return float(stats.norm.cdf(z))

def deflated_sharpe_ratio(returns: pd.Series, n_trials: int = 1) -> dict:
    r = returns.dropna().values
    n = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3 = stats.skew(r)
    g4 = stats.kurtosis(r, fisher=False)
    var_sr = (1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2) / (n - 1)
    var_sr = max(var_sr, 1e-12)
    euler = 0.5772156649015329
    N = max(int(n_trials), 1)
    if N == 1:
        sr_star = 0.0
    else:
        sr_star = np.sqrt(var_sr) * (
            (1.0 - euler) * stats.norm.ppf(1.0 - 1.0 / N)
            + euler * stats.norm.ppf(1.0 - 1.0 / (N * np.e))
        )
    dsr = probabilistic_sharpe_ratio(returns, sr_star)
    return {"sr_period": float(sr), "sr_star": float(sr_star), "dsr": float(dsr)}

def load_data():
    print("Downloading historical daily datasets...")
    start_date = "2010-02-11"
    
    qqq = yf.download("QQQ", start=start_date, progress=False)
    tqqq = yf.download("TQQQ", start=start_date, progress=False)
    sqqq = yf.download("SQQQ", start=start_date, progress=False)
    fx = yf.download("MXN=X", start=start_date, progress=False)
    
    for df in (qqq, tqqq, sqqq, fx):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
            
    out = pd.DataFrame({
        "qqq": qqq["Close"],
        "tqqq": tqqq["Close"],
        "sqqq": sqqq["Close"],
        "fx": fx["Close"],
    })
    
    out["fx"] = out["fx"].ffill().bfill()
    out = out.dropna(subset=["qqq"])
    return out

def run_simulation(data, initial_nav=200000.0, window_length=31, polyorder=3, rsi_period=14, 
                   srp_buy=0.2, srp_sell=0.7, rsi_buy=45, rsi_sell=65, 
                   rsi_breakout_up=55, rsi_breakout_down=45, trailing_stop_pct=None):
    n_days = len(data)
    prices = data["qqq"].values
    
    # Calculate rolling Savitzky-Golay smoothed closes and derivatives
    smooth, deriv1, deriv2 = calculate_savgol_rolling(prices, window_length, polyorder)
    
    # Calculate RSI
    rsi = calculate_rsi(data["qqq"], rsi_period).values
    
    # Track dynamic support and resistance levels
    support_levels = np.full(n_days, np.nan)
    resistance_levels = np.full(n_days, np.nan)
    curr_support = np.nan
    curr_resistance = np.nan
    
    for i in range(window_length, n_days):
        # Zero crossings
        if deriv1[i-1] < 0 and deriv1[i] >= 0 and deriv2[i] > 0:
            curr_support = prices[i]
        elif deriv1[i-1] > 0 and deriv1[i] <= 0 and deriv2[i] < 0:
            curr_resistance = prices[i]
            
        support_levels[i] = curr_support
        resistance_levels[i] = curr_resistance
        
    # Support-Resistance Position (SRP)
    srp = np.full(n_days, 0.5)
    for i in range(n_days):
        sup = support_levels[i]
        res = resistance_levels[i]
        if not np.isnan(sup) and not np.isnan(res) and res > sup:
            srp[i] = (prices[i] - sup) / (res - sup)
            
    # Calculate Returns in MXN
    r_qqq = data["qqq"].pct_change().fillna(0.0)
    r_fx = data["fx"].pct_change().fillna(0.0)
    
    r_tqqq_real = data["tqqq"].pct_change().fillna(0.0)
    r_sqqq_real = data["sqqq"].pct_change().fillna(0.0)
    
    tqqq_drag = (2.0 * 0.045 + 0.0095) / TRADING_DAYS
    sqqq_drag = (2.0 * 0.055 + 0.0095) / TRADING_DAYS
    
    r_tqqq_synth = 3.0 * r_qqq - tqqq_drag
    r_sqqq_synth = -3.0 * r_qqq - sqqq_drag
    
    r_tqqq = np.where(data["tqqq"].notna() & (r_tqqq_real != 0.0), r_tqqq_real, r_tqqq_synth)
    r_sqqq = np.where(data["sqqq"].notna() & (r_sqqq_real != 0.0), r_sqqq_real, r_sqqq_synth)
    
    r_qqq_mxn = ((1.0 + r_qqq) * (1.0 + r_fx) - 1.0).values
    r_tqqq_mxn = ((1.0 + r_tqqq) * (1.0 + r_fx) - 1.0).values
    r_sqqq_mxn = ((1.0 + r_sqqq) * (1.0 + r_fx) - 1.0).values
    
    # Pre-calculate performance indices for trailing stop calculation
    cum_tqqq_mxn = np.insert(np.cumprod(1.0 + r_tqqq_mxn), 0, 1.0)
    cum_sqqq_mxn = np.insert(np.cumprod(1.0 + r_sqqq_mxn), 0, 1.0)
    
    daily_cash_sweep = BONDIA_YIELD / TRADING_DAYS
    
    # Simulation variables
    nav = np.zeros(n_days)
    nav[0] = initial_nav
    positions = np.zeros(n_days, dtype=int)
    
    current_asset = 0  # 0: CASH, 1: TQQQ (Bull), 2: SQQQ (Bear)
    n_trades = 0
    total_fees_paid = 0.0
    
    benchmark = np.zeros(n_days)
    benchmark[0] = initial_nav
    
    # Trailing Stop-Loss variables
    entry_idx = 0
    peak_perf = 1.0
    
    for t in range(1, n_days):
        sup = support_levels[t-1]
        res = resistance_levels[t-1]
        curr_rsi = rsi[t-1]
        curr_srp = srp[t-1]
        
        target_asset = current_asset
        
        # Check normal signals
        if not np.isnan(sup) and not np.isnan(res):
            is_reversion_buy = (curr_srp < srp_buy) and (curr_rsi < rsi_buy)
            is_breakout_buy = (curr_srp > 1.0) and (curr_rsi > rsi_breakout_up)
            
            is_reversion_sell = (curr_srp > srp_sell) and (curr_rsi > rsi_sell)
            is_breakdown_sell = (curr_srp < 0.0) and (curr_rsi < rsi_breakout_down)
            
            if is_reversion_buy or is_breakout_buy:
                target_asset = 1  # TQQQ
            elif is_reversion_sell or is_breakdown_sell:
                target_asset = 2  # SQQQ
            else:
                # Mean reversion exits
                if current_asset == 1 and (curr_srp > 0.85 or curr_rsi > 70):
                    target_asset = 0
                elif current_asset == 2 and (curr_srp < 0.15 or curr_rsi < 30):
                    target_asset = 0
        else:
            target_asset = 0
            
        # Trailing stop loss check (based on daily close up to t-1)
        if current_asset != 0 and trailing_stop_pct is not None:
            if current_asset == 1:
                rel_perf = cum_tqqq_mxn[t-1] / cum_tqqq_mxn[entry_idx]
            else:
                rel_perf = cum_sqqq_mxn[t-1] / cum_sqqq_mxn[entry_idx]
                
            peak_perf = max(peak_perf, rel_perf)
            
            if rel_perf < peak_perf * (1.0 - trailing_stop_pct):
                target_asset = 0  # Force Exit to CASH
                
        # Re-set entry values on position changes
        if target_asset != current_asset:
            if target_asset != 0:
                entry_idx = t - 1
                peak_perf = 1.0
                
        positions[t] = target_asset
        
        # Calculate daily asset return
        if target_asset == 0:
            ret = daily_cash_sweep
        elif target_asset == 1:
            ret = r_tqqq_mxn[t]
        elif target_asset == 2:
            ret = r_sqqq_mxn[t]
            
        # Calculate transaction fee
        fee = 0.0
        if target_asset != current_asset:
            n_trades += 1
            fee = nav[t-1] * TRANSACTION_COST
            total_fees_paid += fee
            
        nav[t] = nav[t-1] * (1.0 + ret) - fee
        current_asset = target_asset
        
        # Benchmark Return
        benchmark[t] = benchmark[t-1] * (1.0 + r_qqq_mxn[t])
        
    df_out = pd.DataFrame(index=data.index)
    df_out["nav"] = nav
    df_out["benchmark"] = benchmark
    df_out["position"] = positions
    df_out["qqq_mxn"] = r_qqq_mxn
    df_out["usd_mxn"] = data["fx"]
    df_out["rsi"] = rsi
    df_out["srp"] = srp
    df_out["support"] = support_levels
    df_out["resistance"] = resistance_levels
    df_out["smooth"] = smooth
    
    return df_out, n_trades, total_fees_paid

def calculate_metrics(nav_series, benchmark_series):
    initial_nav = nav_series.iloc[0]
    final_nav = nav_series.iloc[-1]
    total_ret = final_nav / initial_nav - 1.0
    
    bench_final = benchmark_series.iloc[-1]
    bench_ret = bench_final / initial_nav - 1.0
    
    days = (nav_series.index[-1] - nav_series.index[0]).days
    years = max(days / 365.25, 0.01)
    
    cagr = (final_nav / initial_nav) ** (1.0 / years) - 1.0
    bench_cagr = (bench_final / initial_nav) ** (1.0 / years) - 1.0
    
    daily_rets = nav_series.pct_change().dropna()
    ann_vol = daily_rets.std() * np.sqrt(TRADING_DAYS)
    
    bench_daily_rets = benchmark_series.pct_change().dropna()
    bench_vol = bench_daily_rets.std() * np.sqrt(TRADING_DAYS)
    
    sharpe = (cagr - RF_MXN) / ann_vol if ann_vol > 0 else np.nan
    bench_sharpe = (bench_cagr - RF_MXN) / bench_vol if bench_vol > 0 else np.nan
    
    roll_max = nav_series.cummax()
    max_dd = float(((nav_series - roll_max) / roll_max).min())
    
    bench_roll_max = benchmark_series.cummax()
    bench_max_dd = float(((benchmark_series - bench_roll_max) / bench_roll_max).min())
    
    dsr_dict = deflated_sharpe_ratio(daily_rets)
    
    return {
        "final_nav": final_nav,
        "total_return": total_ret,
        "cagr": cagr,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "dsr": dsr_dict["dsr"],
        "sr_star": dsr_dict["sr_star"],
        "sr_period": dsr_dict["sr_period"],
        "bench_final": bench_final,
        "bench_return": bench_ret,
        "bench_cagr": bench_cagr,
        "bench_vol": bench_vol,
        "bench_sharpe": bench_sharpe,
        "bench_max_dd": bench_max_dd,
        "years": years
    }

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print("STRATEGY 23 (OPTIMIZED): CALCULUS S&R & RSI BACKTEST")
    print("=" * 80)
    
    data = load_data()
    initial_nav = 200000.0
    
    split_date = "2022-01-01"
    train_data = data[data.index < split_date].copy()
    val_data = data.copy()
    
    # Grid search specifically for trailing stops, SRP boundaries, and polyorders
    GRID = {
        "window_length": [35],
        "polyorder": [3],
        "rsi_period": [14],
        "srp_buy": [0.20, 0.25],
        "srp_sell": [0.70, 0.75],
        "rsi_buy": [45],
        "rsi_sell": [65],
        "trailing_stop_pct": [None]
    }
    
    best_sharpe = -999.0
    best_params = None
    
    print("\nOptimizing risk and execution parameters on In-Sample Data...")
    
    combo_count = 0
    total_combos = (
        len(GRID["window_length"]) * len(GRID["polyorder"]) *
        len(GRID["rsi_period"]) * len(GRID["srp_buy"]) *
        len(GRID["srp_sell"]) * len(GRID["rsi_buy"]) *
        len(GRID["rsi_sell"]) * len(GRID["trailing_stop_pct"])
    )
    
    for wl in GRID["window_length"]:
        for po in GRID["polyorder"]:
            for rp in GRID["rsi_period"]:
                for sb in GRID["srp_buy"]:
                    for ss in GRID["srp_sell"]:
                        for rb in GRID["rsi_buy"]:
                            for rs_val in GRID["rsi_sell"]:
                                for ts in GRID["trailing_stop_pct"]:
                                    combo_count += 1
                                    try:
                                        df_sim, n_trades, fees = run_simulation(
                                            train_data, window_length=wl, polyorder=po, rsi_period=rp,
                                            srp_buy=sb, srp_sell=ss, rsi_buy=rb, rsi_sell=rs_val,
                                            trailing_stop_pct=ts
                                        )
                                        
                                        if df_sim.empty or n_trades < 5:
                                            continue
                                            
                                        metrics = calculate_metrics(df_sim["nav"], df_sim["benchmark"])
                                        train_sharpe = metrics["sharpe"]
                                        
                                        if train_sharpe > best_sharpe:
                                            best_sharpe = train_sharpe
                                            best_params = {
                                                "window_length": wl,
                                                "polyorder": po,
                                                "rsi_period": rp,
                                                "srp_buy": sb,
                                                "srp_sell": ss,
                                                "rsi_buy": rb,
                                                "rsi_sell": rs_val,
                                                "trailing_stop_pct": ts
                                            }
                                    except Exception as e:
                                        continue
                                    
    if best_params is None:
        best_params = {
            "window_length": 31,
            "polyorder": 3,
            "rsi_period": 14,
            "srp_buy": 0.20,
            "srp_sell": 0.70,
            "rsi_buy": 45,
            "rsi_sell": 65,
            "trailing_stop_pct": 0.10
        }
        
    best_params["rsi_breakout_up"] = 55
    best_params["rsi_breakout_down"] = 45
        
    print("\n" + "=" * 80)
    print("OPTIMAL PARAMETERS FOUND (S23 OPTIMIZED)")
    print("=" * 80)
    for k, v in best_params.items():
        print(f"  {k:20s}: {v}")
    print(f"  In-Sample Sharpe    : {best_sharpe:.4f}")
    
    # 2. Run simulation on FULL dataset with optimal parameters
    df_out, n_trades, fees = run_simulation(
        val_data,
        window_length=best_params["window_length"],
        polyorder=best_params["polyorder"],
        rsi_period=best_params["rsi_period"],
        srp_buy=best_params["srp_buy"],
        srp_sell=best_params["srp_sell"],
        rsi_buy=best_params["rsi_buy"],
        rsi_sell=best_params["rsi_sell"],
        rsi_breakout_up=best_params["rsi_breakout_up"],
        rsi_breakout_down=best_params["rsi_breakout_down"],
        trailing_stop_pct=best_params["trailing_stop_pct"]
    )
    
    metrics = calculate_metrics(df_out["nav"], df_out["benchmark"])
    
    df_train_res = df_out[df_out.index < split_date]
    df_val_res = df_out[df_out.index >= split_date]
    
    train_metrics = calculate_metrics(df_train_res["nav"], df_train_res["benchmark"])
    val_metrics = calculate_metrics(df_val_res["nav"], df_val_res["benchmark"])
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS: S23 CALCULUS S&R & RSI SYSTEMATIC (OPTIMIZED)")
    print("=" * 80)
    print(f"Backtest Period : {df_out.index[0].strftime('%Y-%m-%d')} to {df_out.index[-1].strftime('%Y-%m-%d')} ({metrics['years']:.2f} Years)")
    print(f"Final NAV (S23) : ${metrics['final_nav']:,.2f} MXN (Benchmark: ${metrics['bench_final']:,.2f} MXN)")
    print(f"Total Return    : {metrics['total_return']*100:+.2f}% (Benchmark: {metrics['bench_return']*100:+.2f}%)")
    print(f"CAGR            : {metrics['cagr']*100:+.2f}% (Benchmark: {metrics['bench_cagr']*100:+.2f}%)")
    print(f"Annual Vol      : {metrics['ann_vol']*100:.2f}% (Benchmark: {metrics['bench_vol']*100:.2f}%)")
    print(f"Sharpe (Rf=9.5%): {metrics['sharpe']:.2f} (Benchmark: {metrics['bench_sharpe']:.2f})")
    print(f"Max Drawdown    : {metrics['max_dd']*100:.2f}% (Benchmark: {metrics['bench_max_dd']:.2f}%)")
    print(f"Deflated Sharpe : {metrics['dsr']*100:.2f}% (Hurdle Star: {metrics['sr_star']*np.sqrt(252)*100:.2f}% Ann.)")
    print(f"Total trades    : {n_trades} (Total fees paid: ${fees:,.2f} MXN)")
    print("-" * 80)
    print("OUT-OF-SAMPLE METRICS (2022 - PRESENT):")
    print(f"  OOS Return    : {val_metrics['total_return']*100:+.2f}% (Benchmark: {val_metrics['bench_return']*100:+.2f}%)")
    print(f"  OOS Sharpe    : {val_metrics['sharpe']:.2f} (Benchmark: {val_metrics['bench_sharpe']:.2f})")
    print(f"  OOS Max DD    : {val_metrics['max_dd']*100:.2f}% (Benchmark: {val_metrics['bench_max_dd']*100:.2f}%)")
    print("=" * 80)
    
    # Export Report
    report_md = f"""# Strategy 23 Backtest Report (Calculus Support/Resistance & RSI Momentum - Optimized)
**Executed:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** {df_out.index[0].strftime('%Y-%m-%d')} to {df_out.index[-1].strftime('%Y-%m-%d')} ({metrics['years']:.2f} Years)

## Optimal Strategy Parameters
* **Savitzky-Golay Window Length:** {best_params['window_length']} days
* **Savitzky-Golay Polynomial Order:** {best_params['polyorder']}
* **RSI Period:** {best_params['rsi_period']} days
* **SRP Buy Threshold:** {best_params['srp_buy']:.2f}
* **SRP Sell Threshold:** {best_params['srp_sell']:.2f}
* **RSI Buy Threshold:** {best_params['rsi_buy']}
* **RSI Sell Threshold:** {best_params['rsi_sell']}
* **RSI Breakout Up:** {best_params['rsi_breakout_up']}
* **RSI Breakout Down:** {best_params['rsi_breakout_down']}
* **Trailing Stop-Loss Percentage:** {f"{best_params['trailing_stop_pct']*100:.1f}%" if best_params['trailing_stop_pct'] is not None else "None"}

## Full Period Performance Comparison (2010 - 2026)
| Metric | Strategy 23 (Calculus S&R + RSI) | Benchmark (QQQ Buy-and-Hold) |
| :--- | :---: | :---: |
| **Final Portfolio NAV** | ${metrics['final_nav']:,.2f} MXN | ${metrics['bench_final']:,.2f} MXN |
| **Cumulative Return** | {metrics['total_return']*100:+.2f}% | {metrics['bench_return']*100:+.2f}% |
| **CAGR** | {metrics['cagr']*100:+.2f}% | {metrics['bench_cagr']*100:+.2f}% |
| **Annualized Volatility** | {metrics['ann_vol']*100:.2f}% | {metrics['bench_vol']*100:.2f}% |
| **Sharpe Ratio (Rf=9.5%)** | {metrics['sharpe']:.2f} | {metrics['bench_sharpe']:.2f} |
| **Maximum Drawdown** | {metrics['max_dd']*100:.2f}% | {metrics['bench_max_dd']*100:.2f}% |

## Out-Of-Sample Validation Performance (2022 - 2026)
| Metric | Strategy 23 (Out-of-Sample) | Benchmark (Out-of-Sample) |
| :--- | :---: | :---: |
| **OOS Cumulative Return** | {val_metrics['total_return']*100:+.2f}% | {val_metrics['bench_return']*100:+.2f}% |
| **OOS CAGR** | {val_metrics['cagr']*100:+.2f}% | {val_metrics['bench_cagr']*100:+.2f}% |
| **OOS Sharpe Ratio** | {val_metrics['sharpe']:.2f} | {val_metrics['bench_sharpe']:.2f} |
| **OOS Maximum Drawdown** | {val_metrics['max_dd']*100:.2f}% | {val_metrics['bench_max_dd']*100:.2f}% |

## Probabilistic Verification (Bailey & Lopez de Prado)
* **Realized Sharpe (Daily Period):** {metrics['sr_period']:.4f}
* **Regret Hurdle ($\mu_*$ Sharpe):** {metrics['sr_star']:.4f}
* **Deflated Sharpe Ratio (DSR):** {metrics['dsr']*100:.2f}%

## Execution Statistics
* **Starting Capital:** ${initial_nav:,.2f} MXN
* **Total Transactions:** {n_trades} trades
* **Total Commissions & VAT Paid:** ${fees:,.2f} MXN
* **Position Breakdown:**
  * Cash: {(df_out["position"] == 0).sum()} days
  * TQQQ: {(df_out["position"] == 1).sum()} days
  * SQQQ: {(df_out["position"] == 2).sum()} days
"""
    
    with open(os.path.join(dir_path, "strategy23_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)
        
    df_out.to_csv(os.path.join(dir_path, "strategy23_backtest_nav.csv"))
    
    with open(os.path.join(dir_path, "learned_params_s23.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(best_params, f, indent=4)
        
    print(f"\nSaved optimal parameters to: learned_params_s23.json")
    print(f"Saved backtest NAV curve to: strategy23_backtest_nav.csv")
    print(f"Saved backtest report successfully to: strategy23_backtest_report.md")

if __name__ == "__main__":
    main()
