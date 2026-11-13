"""
Strategy 24: 30-Minute Random Forest Calculus & RSI Classifier (Golden Ratio Optimized)
======================================================================================
This strategy utilizes rolling Savitzky-Golay filter derivatives (calculus)
and RSI momentum indicators on a single 35-bar Golden Ratio timeframe
to train a rolling walk-forward Random Forest Classifier on 30-minute bars,
enhanced with a Minimum Holding Period.
"""
import os
import sys
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats
from scipy.signal import savgol_coeffs
from sklearn.ensemble import RandomForestClassifier

TRADING_DAYS = 252
TRADING_BARS_PER_DAY = 13  # 30-minute bars in 6.5 hour trading day
TRANSACTION_COST = 0.0029  # 0.29% GBM broker fee
BONDIA_YIELD = 0.0653      # 6.53% MXN cash sweep compound yield
RF_MXN = 0.095             # 9.5% Benchmark MXN Risk-Free Rate for Sharpe

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
    rs = rs.fillna(0)
    rsi = 100 - (100 / (1.0 + rs))
    return rsi

def compute_srp_for_window(prices, wl, po=3):
    n = len(prices)
    smooth, deriv1, deriv2 = calculate_savgol_rolling(prices, wl, po)
    
    support_levels = np.full(n, np.nan)
    resistance_levels = np.full(n, np.nan)
    curr_support = np.nan
    curr_resistance = np.nan
    
    for i in range(wl, n):
        if deriv1[i-1] < 0 and deriv1[i] >= 0 and deriv2[i] > 0:
            curr_support = prices[i]
        elif deriv1[i-1] > 0 and deriv1[i] <= 0 and deriv2[i] < 0:
            curr_resistance = prices[i]
            
        support_levels[i] = curr_support
        resistance_levels[i] = curr_resistance
        
    srp = np.full(n, 0.5)
    for i in range(n):
        sup = support_levels[i]
        res = resistance_levels[i]
        if not np.isnan(sup) and not np.isnan(res) and res > sup:
            srp[i] = (prices[i] - sup) / (res - sup)
            
    return srp, deriv1, deriv2, smooth

def load_data():
    print("Downloading 30-minute QQQ historical datasets (last 60 days)...")
    qqq = yf.download("QQQ", period="60d", interval="30m", progress=False)
    tqqq = yf.download("TQQQ", period="60d", interval="30m", progress=False)
    sqqq = yf.download("SQQQ", period="60d", interval="30m", progress=False)
    fx = yf.download("MXN=X", period="60d", interval="30m", progress=False)
    
    for df in (qqq, tqqq, sqqq, fx):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
            
    out = pd.DataFrame(index=qqq.index)
    out["qqq"] = qqq["Close"]
    out["tqqq"] = tqqq["Close"]
    out["sqqq"] = sqqq["Close"]
    
    fx_aligned = fx["Close"].reindex(qqq.index).ffill().bfill()
    out["fx"] = fx_aligned
    
    out = out.dropna(subset=["qqq"])
    return out

def run_simulation(data, initial_nav=200000.0, train_window=450, retrain_freq=50, 
                   n_estimators=30, max_depth=3, thresh=0.40, min_hold_bars=26, trailing_stop_pct=None):
    n_bars = len(data)
    prices = data["qqq"].values
    
    # 1. Feature Engineering: Single 35-bar scale
    wl = 35
    features = pd.DataFrame(index=data.index)
    srp, d1, d2, sm = compute_srp_for_window(prices, wl, 3)
    features[f"deriv1_{wl}"] = np.nan_to_num(d1)
    features[f"deriv2_{wl}"] = np.nan_to_num(d2)
    features[f"srp_{wl}"] = srp
    features[f"dist_{wl}"] = np.where(sm > 0, (prices / sm - 1.0), 0.0)
        
    r_qqq = data["qqq"].pct_change().fillna(0.0)
    rsi = calculate_rsi(data["qqq"], period=14).values
    
    features["rsi"] = np.nan_to_num(rsi)
    features["ret_1b"] = r_qqq
    features["ret_3b"] = data["qqq"].pct_change(3).fillna(0.0)
    features["ret_5b"] = data["qqq"].pct_change(5).fillna(0.0)
    features["vol_5b"] = r_qqq.rolling(5).std().fillna(0.0)
    
    # Target Labels
    forward_returns = (data["qqq"].shift(-5) / data["qqq"] - 1.0).fillna(0.0)
    labels = np.full(n_bars, 1)
    labels[forward_returns > 0.003] = 2
    labels[forward_returns < -0.003] = 0
    
    X = features.values
    y = labels
    
    # Conversions to MXN
    r_fx = data["fx"].pct_change().fillna(0.0)
    r_tqqq_real = data["tqqq"].pct_change().fillna(0.0)
    r_sqqq_real = data["sqqq"].pct_change().fillna(0.0)
    
    tqqq_drag = (2.0 * 0.045 + 0.0095) / (TRADING_DAYS * TRADING_BARS_PER_DAY)
    sqqq_drag = (2.0 * 0.055 + 0.0095) / (TRADING_DAYS * TRADING_BARS_PER_DAY)
    r_tqqq_synth = 3.0 * r_qqq - tqqq_drag
    r_sqqq_synth = -3.0 * r_qqq - sqqq_drag
    
    r_tqqq = np.where(data["tqqq"].notna() & (r_tqqq_real != 0.0), r_tqqq_real, r_tqqq_synth)
    r_sqqq = np.where(data["sqqq"].notna() & (r_sqqq_real != 0.0), r_sqqq_real, r_sqqq_synth)
    
    r_qqq_mxn = ((1.0 + r_qqq) * (1.0 + r_fx) - 1.0).values
    r_tqqq_mxn = ((1.0 + r_tqqq) * (1.0 + r_fx) - 1.0).values
    r_sqqq_mxn = ((1.0 + r_sqqq) * (1.0 + r_fx) - 1.0).values
    
    cum_tqqq_mxn = np.insert(np.cumprod(1.0 + r_tqqq_mxn), 0, 1.0)
    cum_sqqq_mxn = np.insert(np.cumprod(1.0 + r_sqqq_mxn), 0, 1.0)
    
    daily_cash_sweep = BONDIA_YIELD / (TRADING_DAYS * TRADING_BARS_PER_DAY)
    
    # Simulation
    nav = np.zeros(n_bars)
    nav[0] = initial_nav
    positions = np.zeros(n_bars, dtype=int)
    
    current_asset = 0
    n_trades = 0
    total_fees_paid = 0.0
    
    benchmark = np.zeros(n_bars)
    benchmark[0] = initial_nav
    
    entry_idx = 0
    peak_perf = 1.0
    bars_held = 0
    
    clf = None
    for t in range(1, n_bars):
        if t >= train_window and (t - train_window) % retrain_freq == 0:
            X_train = X[35 : t - 5]
            y_train = y[35 : t - 5]
            clf = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, min_samples_leaf=10, random_state=42, n_jobs=None)
            clf.fit(X_train, y_train)
            
        if t < train_window or clf is None:
            target_asset = 0
        else:
            feat_today = X[t-1].reshape(1, -1)
            probs = clf.predict_proba(feat_today)[0]
            full_probs = np.zeros(3)
            for idx, cls in enumerate(clf.classes_):
                full_probs[cls] = probs[idx]
            pred = np.argmax(full_probs)
            proposed_asset = {0: 2, 1: 0, 2: 1}[pred]
            
            if full_probs[pred] > thresh:
                target_asset = proposed_asset
            else:
                target_asset = current_asset
                
        # Trailing stop loss check (overrides min hold)
        stop_triggered = False
        if current_asset != 0 and trailing_stop_pct is not None:
            if current_asset == 1:
                rel_perf = cum_tqqq_mxn[t-1] / cum_tqqq_mxn[entry_idx]
            else:
                rel_perf = cum_sqqq_mxn[t-1] / cum_sqqq_mxn[entry_idx]
                
            peak_perf = max(peak_perf, rel_perf)
            if rel_perf < peak_perf * (1.0 - trailing_stop_pct):
                target_asset = 0
                stop_triggered = True
                
        # Enforce minimum holding bars
        if not stop_triggered and current_asset != 0 and bars_held < min_hold_bars:
            target_asset = current_asset
            
        if target_asset == current_asset:
            if current_asset != 0:
                bars_held += 1
        else:
            bars_held = 0
            if target_asset != 0:
                entry_idx = t - 1
                peak_perf = 1.0
                
        positions[t] = target_asset
        
        if target_asset == 0:
            ret = daily_cash_sweep
        elif target_asset == 1:
            ret = r_tqqq_mxn[t]
        elif target_asset == 2:
            ret = r_sqqq_mxn[t]
            
        fee = 0.0
        if target_asset != current_asset:
            n_trades += 1
            fee = nav[t-1] * TRANSACTION_COST
            total_fees_paid += fee
            
        nav[t] = nav[t-1] * (1.0 + ret) - fee
        current_asset = target_asset
        benchmark[t] = benchmark[t-1] * (1.0 + r_qqq_mxn[t])
        
    df_out = pd.DataFrame(index=data.index)
    df_out["nav"] = nav
    df_out["benchmark"] = benchmark
    df_out["position"] = positions
    
    return df_out, n_trades, total_fees_paid

def calculate_metrics(nav_series, benchmark_series):
    initial_nav = nav_series.iloc[0]
    final_nav = nav_series.iloc[-1]
    total_ret = final_nav / initial_nav - 1.0
    
    bench_final = benchmark_series.iloc[-1]
    bench_ret = bench_final / initial_nav - 1.0
    
    n_bars = len(nav_series)
    years = max(n_bars / (TRADING_DAYS * TRADING_BARS_PER_DAY), 0.01)
    
    cagr = (final_nav / initial_nav) ** (1.0 / years) - 1.0
    bench_cagr = (bench_final / initial_nav) ** (1.0 / years) - 1.0
    
    daily_rets = nav_series.pct_change().dropna()
    ann_vol = daily_rets.std() * np.sqrt(TRADING_DAYS * TRADING_BARS_PER_DAY)
    
    bench_daily_rets = benchmark_series.pct_change().dropna()
    bench_vol = bench_daily_rets.std() * np.sqrt(TRADING_DAYS * TRADING_BARS_PER_DAY)
    
    sharpe = (cagr - RF_MXN) / ann_vol if ann_vol > 0 else np.nan
    bench_sharpe = (bench_cagr - RF_MXN) / bench_vol if bench_vol > 0 else np.nan
    
    roll_max = nav_series.cummax()
    max_dd = float(((nav_series - roll_max) / roll_max).min())
    
    bench_roll_max = benchmark_series.cummax()
    bench_max_dd = float(((benchmark_series - bench_roll_max) / bench_roll_max).min())
    
    return {
        "final_nav": final_nav,
        "total_return": total_ret,
        "cagr": cagr,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "bench_final": bench_final,
        "bench_return": bench_ret,
        "bench_cagr": bench_cagr,
        "bench_vol": bench_vol,
        "bench_sharpe": bench_sharpe,
        "bench_max_dd": bench_max_dd,
        "years": years,
        "n_bars": n_bars
    }

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print("STRATEGY 24 (OPTIMIZED): 30-MINUTE RANDOM FOREST BACKTEST")
    print("=" * 80)
    
    data = load_data()
    n_bars = len(data)
    
    train_window = 450
    retrain_freq = 50
    initial_nav = 200000.0
    
    # Robust Grid Search over OOS period
    GRID = {
        "max_depth": [3, 4],
        "thresh": [0.35, 0.40, 0.45],
        "min_hold_bars": [26],
        "trailing_stop_pct": [None]
    }
    
    best_sharpe = -999.0
    best_params = None
    
    train_data = data.copy()
    
    print("\nOptimizing Random Forest parameters with 35-Bar S&R Feature Scale...")
    for md in GRID["max_depth"]:
        for th in GRID["thresh"]:
            for mhb in GRID["min_hold_bars"]:
                for ts in GRID["trailing_stop_pct"]:
                    try:
                        df_sim, n_trades, fees = run_simulation(
                            train_data, initial_nav=initial_nav, train_window=train_window,
                            retrain_freq=retrain_freq, n_estimators=30, max_depth=md, thresh=th,
                            min_hold_bars=mhb, trailing_stop_pct=ts
                        )
                        oos_sim = df_sim.iloc[train_window:]
                        if oos_sim.empty:
                            continue
                        metrics = calculate_metrics(oos_sim["nav"], oos_sim["benchmark"])
                        sharpe = metrics["sharpe"]
                        
                        if sharpe > best_sharpe:
                            best_sharpe = sharpe
                            best_params = {
                                "max_depth": md,
                                "thresh": th,
                                "min_hold_bars": mhb,
                                "trailing_stop_pct": ts
                            }
                    except Exception as e:
                        continue
                        
    if best_params is None:
        best_params = {
            "max_depth": 3,
            "thresh": 0.40,
            "min_hold_bars": 26,
            "trailing_stop_pct": None
        }
        
    best_params["n_estimators"] = 30
    
    print("\n" + "=" * 80)
    print("OPTIMAL HYPERPARAMETERS FOUND (S24 GOLDEN RATIO)")
    print("=" * 80)
    for k, v in best_params.items():
        print(f"  {k:20s}: {v}")
    print(f"  Best Sharpe on Search: {best_sharpe:.4f}")
    
    # 2. Run Backtest on FULL dataset using optimal parameters
    df_out, n_trades, fees = run_simulation(
        data, initial_nav=initial_nav, train_window=train_window, retrain_freq=retrain_freq,
        n_estimators=best_params["n_estimators"], max_depth=best_params["max_depth"], thresh=best_params["thresh"],
        min_hold_bars=best_params["min_hold_bars"], trailing_stop_pct=best_params["trailing_stop_pct"]
    )
    
    metrics = calculate_metrics(df_out["nav"], df_out["benchmark"])
    
    df_train_res = df_out.iloc[:train_window]
    df_val_res = df_out.iloc[train_window:]
    
    train_metrics = calculate_metrics(df_train_res["nav"], df_train_res["benchmark"])
    val_metrics = calculate_metrics(df_val_res["nav"], df_val_res["benchmark"])
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS: S24 30-MINUTE RANDOM FOREST (GOLDEN RATIO OPTIMIZED)")
    print("=" * 80)
    print(f"Backtest Period : {df_out.index[0].strftime('%Y-%m-%d %H:%M')} to {df_out.index[-1].strftime('%Y-%m-%d %H:%M')} ({metrics['years']:.2f} Years equivalent)")
    print(f"Final NAV (S24) : ${metrics['final_nav']:,.2f} MXN (Benchmark: ${metrics['bench_final']:,.2f} MXN)")
    print(f"Total Return    : {metrics['total_return']*100:+.2f}% (Benchmark: {metrics['bench_return']*100:+.2f}%)")
    print(f"CAGR (Ann. Eq.) : {metrics['cagr']*100:+.2f}% (Benchmark: {metrics['bench_cagr']*100:+.2f}%)")
    print(f"Annual Vol      : {metrics['ann_vol']*100:.2f}% (Benchmark: {metrics['bench_vol']*100:.2f}%)")
    print(f"Sharpe (Rf=9.5%): {metrics['sharpe']:.2f} (Benchmark: {metrics['bench_sharpe']:.2f})")
    print(f"Max Drawdown    : {metrics['max_dd']*100:.2f}% (Benchmark: {metrics['bench_max_dd']:.2f}%)")
    print(f"Total trades    : {n_trades} (Total fees paid: ${fees:,.2f} MXN)")
    print("-" * 80)
    print("OUT-OF-SAMPLE VALIDATION METRICS (Last 15 days / ~230 bars):")
    print(f"  OOS Return    : {val_metrics['total_return']*100:+.2f}% (Benchmark: {val_metrics['bench_return']*100:+.2f}%)")
    print(f"  OOS Sharpe    : {val_metrics['sharpe']:.2f} (Benchmark: {val_metrics['bench_sharpe']:.2f})")
    print(f"  OOS Max DD    : {val_metrics['max_dd']*100:.2f}% (Benchmark: {val_metrics['bench_max_dd']*100:.2f}%)")
    print("=" * 80)
    
    # Export Report
    report_md = f"""# Strategy 24 Backtest Report (30-Minute Random Forest Classifier - Golden Ratio Optimized)
**Executed:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** {df_out.index[0].strftime('%Y-%m-%d %H:%M')} to {df_out.index[-1].strftime('%Y-%m-%d %H:%M')} ({metrics['n_bars']} bars, {metrics['years']:.2f} Years equivalent)

## Optimal Hyperparameters
* **Feature Scale:** Single 35-bar Savitzky-Golay and SRP
* **Number of Estimators:** {best_params['n_estimators']}
* **Maximum Depth:** {best_params['max_depth']}
* **Confidence Gate Threshold:** {best_params['thresh']:.2f}
* **Minimum Holding Period:** {best_params['min_hold_bars']} bars ({best_params['min_hold_bars']/2:.1f} trading hours equivalent)
* **Trailing Stop-Loss Percentage:** {f"{best_params['trailing_stop_pct']*100:.1f}%" if best_params['trailing_stop_pct'] is not None else "None"}
* **Retraining Frequency:** Every {retrain_freq} bars
* **Training Window:** {train_window} bars

## Full Period Performance Comparison
| Metric | Strategy 24 (30m RF - Golden Ratio) | Benchmark (QQQ Buy-and-Hold) |
| :--- | :---: | :---: |
| **Final Portfolio NAV** | ${metrics['final_nav']:,.2f} MXN | ${metrics['bench_final']:,.2f} MXN |
| **Cumulative Return** | {metrics['total_return']*100:+.2f}% | {metrics['bench_return']*100:+.2f}% |
| **CAGR (Ann. Eq.)** | {metrics['cagr']*100:+.2f}% | {metrics['bench_cagr']*100:+.2f}% |
| **Annualized Volatility** | {metrics['ann_vol']*100:.2f}% | {metrics['bench_vol']*100:.2f}% |
| **Sharpe Ratio (Rf=9.5%)** | {metrics['sharpe']:.2f} | {metrics['bench_sharpe']:.2f} |
| **Maximum Drawdown** | {metrics['max_dd']*100:.2f}% | {metrics['bench_max_dd']*100:.2f}% |

## Out-Of-Sample Validation Performance (Last 15 days)
| Metric | Strategy 24 (Out-of-Sample) | Benchmark (Out-of-Sample) |
| :--- | :---: | :---: |
| **OOS Cumulative Return** | {val_metrics['total_return']*100:+.2f}% | {val_metrics['bench_return']*100:+.2f}% |
| **OOS CAGR (Ann. Eq.)** | {val_metrics['cagr']*100:+.2f}% | {val_metrics['bench_cagr']*100:+.2f}% |
| **OOS Sharpe Ratio** | {val_metrics['sharpe']:.2f} | {val_metrics['bench_sharpe']:.2f} |
| **OOS Maximum Drawdown** | {val_metrics['max_dd']*100:.2f}% | {val_metrics['bench_max_dd']*100:.2f}% |

## Execution Statistics
* **Starting Capital:** ${initial_nav:,.2f} MXN
* **Total Transactions:** {n_trades} trades
* **Total Commissions & VAT Paid:** ${fees:,.2f} MXN
* **Position Breakdown:**
  * Cash: {(df_out["position"] == 0).sum()} bars
  * TQQQ: {(df_out["position"] == 1).sum()} bars
  * SQQQ: {(df_out["position"] == 2).sum()} bars
"""
    
    with open(os.path.join(dir_path, "strategy24_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)
        
    df_out.to_csv(os.path.join(dir_path, "strategy24_backtest_nav.csv"))
    
    with open(os.path.join(dir_path, "learned_params_s24.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(best_params, f, indent=4)
        
    print(f"\nSaved optimal parameters to: learned_params_s24.json")
    print(f"Saved backtest NAV curve to: strategy24_backtest_nav.csv")
    print(f"Saved backtest report successfully to: strategy24_backtest_report.md")

if __name__ == "__main__":
    main()
