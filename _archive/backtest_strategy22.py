"""
Strategy 22: Walk-Forward Online Adaptive ML Classifier Systematic Allocation
=============================================================================
This strategy trains a daily/weekly rolling Random Forest Classifier on historical features
to predict QQQ's regime over the next 5 days.
  - Features: returns (1d, 5d, 10d, 20d, 60d), volatility (5d, 20d), trend SMAs (50d, 120d),
    Hurst Exponent (from S20), and Shannon Entropy (from S21).
  - Target labels: Bull (forward 5-day return > +1.5%), Bear (forward 5-day return < -1.5%),
    or Chop (between -1.5% and +1.5%).
  - Allocations: TQQQ (Bull), SQQQ (Bear), or Cash (Chop).

Retraining is performed walk-forward on a rolling 500-day window.
"""
import os
import sys
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats
from sklearn.ensemble import RandomForestClassifier

TRADING_DAYS = 252
TRANSACTION_COST = 0.0029  # 0.29% GBM fee
BONDIA_YIELD = 0.0653      # 6.53% MXN cash compound yield
RF_MXN = 0.095             # 9.5% Benchmark MXN Risk-Free Rate for Sharpe

def calculate_hurst_exponent_rolling(log_prices, window_size=100, max_lag=20):
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

def calculate_shannon_entropy_rolling(returns, window_size=60, num_bins=10):
    n = len(returns)
    entropy_values = np.full(n, 1.0)
    max_entropy = np.log2(num_bins)
    
    for i in range(window_size, n):
        sub_series = returns[i - window_size : i]
        counts, _ = np.histogram(sub_series, bins=num_bins)
        probs = counts / window_size
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log2(probs))
        entropy_values[i] = entropy / max_entropy if max_entropy > 0 else 1.0
    return entropy_values

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

def run_simulation(data, initial_nav=200000.0, train_window=500, retrace_days=5, thresh=0.45):
    n_days = len(data)
    
    # daily returns
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
    
    daily_cash_sweep = BONDIA_YIELD / TRADING_DAYS
    
    # 1. Feature Engineering
    features = pd.DataFrame(index=data.index)
    features["ret_1d"] = r_qqq
    features["ret_5d"] = data["qqq"].pct_change(5).fillna(0.0)
    features["ret_10d"] = data["qqq"].pct_change(10).fillna(0.0)
    features["ret_20d"] = data["qqq"].pct_change(20).fillna(0.0)
    features["ret_60d"] = data["qqq"].pct_change(60).fillna(0.0)
    
    features["vol_5d"] = r_qqq.rolling(5).std().fillna(0.0)
    features["vol_20d"] = r_qqq.rolling(20).std().fillna(0.0)
    
    sma_50 = data["qqq"].rolling(50).mean()
    sma_120 = data["qqq"].rolling(120).mean()
    features["dist_sma50"] = (data["qqq"] / sma_50 - 1.0).fillna(0.0)
    features["dist_sma120"] = (data["qqq"] / sma_120 - 1.0).fillna(0.0)
    
    log_closes = np.log(data["qqq"].values)
    features["hurst"] = calculate_hurst_exponent_rolling(log_closes, window_size=100, max_lag=20)
    
    qqq_returns_val = r_qqq.values
    features["entropy"] = calculate_shannon_entropy_rolling(qqq_returns_val, window_size=60, num_bins=10)
    
    # 2. Define Targets (Forward 5-day return)
    forward_returns = (data["qqq"].shift(-5) / data["qqq"] - 1.0).fillna(0.0)
    labels = np.full(n_days, 1)  # Default: Chop (1)
    
    # Bull = 2 (return > 1.5%), Bear = 0 (return < -1.5%), Chop = 1
    labels[forward_returns > 0.015] = 2
    labels[forward_returns < -0.015] = 0
    
    X = features.values
    y = labels
    
    # Walk-forward classification simulation
    nav = np.zeros(n_days)
    nav[0] = initial_nav
    
    positions = np.zeros(n_days, dtype=int)
    
    current_asset = 0
    n_trades = 0
    total_fees_paid = 0.0
    
    benchmark = np.zeros(n_days)
    benchmark[0] = initial_nav
    
    # Fit loop
    clf = None
    for t in range(1, n_days):
        # Retrain every `retrace_days`
        if t >= train_window and (t - train_window) % retrace_days == 0:
            # We train on data from t-train_window to t-5 (avoiding look-ahead of forward return)
            X_train = X[t - train_window : t - 5]
            y_train = y[t - train_window : t - 5]
            
            # Simple, regularized Random Forest
            clf = RandomForestClassifier(n_estimators=50, max_depth=3, min_samples_leaf=10, random_state=42, n_jobs=None)
            clf.fit(X_train, y_train)
            
        # Generate prediction
        if t < train_window or clf is None:
            # Not enough data yet, default to cash
            target_asset = 0
        else:
            # Predict using today's feature vector (historical up to t-1)
            feat_today = X[t-1].reshape(1, -1)
            probs = clf.predict_proba(feat_today)[0]
            pred = np.argmax(probs)
            
            # Classes are ordered [0, 1, 2] -> corresponding to Bear (0), Chop (1), Bull (2)
            asset_map = {0: 3, 1: 0, 2: 2}
            proposed_asset = asset_map[pred]
            
            # Confidence gate: only transition if probability > thresh, else hold current position
            if probs[pred] > thresh:
                target_asset = proposed_asset
            else:
                target_asset = current_asset
                
        positions[t] = target_asset
        
        # Calculate daily asset return
        if target_asset == 0:
            ret = daily_cash_sweep
        elif target_asset == 1:
            ret = r_qqq_mxn[t]
        elif target_asset == 2:
            ret = r_tqqq_mxn[t]
        elif target_asset == 3:
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
    
    return df_out, n_trades, total_fees_paid

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print("STRATEGY 22: WALK-FORWARD ADAPTIVE ML BACKTEST")
    print("=" * 80)
    
    data = load_data()
    df_out, n_trades, fees = run_simulation(data)
    
    initial_nav = df_out["nav"].iloc[0]
    final_nav = df_out["nav"].iloc[-1]
    total_ret = final_nav / initial_nav - 1.0
    
    bench_final = df_out["benchmark"].iloc[-1]
    bench_ret = bench_final / initial_nav - 1.0
    
    days = (df_out.index[-1] - df_out.index[0]).days
    years = max(days / 365.25, 0.01)
    
    cagr = (final_nav / initial_nav) ** (1.0 / years) - 1.0
    bench_cagr = (bench_final / initial_nav) ** (1.0 / years) - 1.0
    
    daily_rets = df_out["nav"].pct_change().dropna()
    ann_vol = daily_rets.std() * np.sqrt(TRADING_DAYS)
    
    bench_daily_rets = df_out["benchmark"].pct_change().dropna()
    bench_vol = bench_daily_rets.std() * np.sqrt(TRADING_DAYS)
    
    sharpe = (cagr - RF_MXN) / ann_vol if ann_vol > 0 else np.nan
    bench_sharpe = (bench_cagr - RF_MXN) / bench_vol if bench_vol > 0 else np.nan
    
    roll_max = df_out["nav"].cummax()
    max_dd = float(((df_out["nav"] - roll_max) / roll_max).min())
    
    bench_roll_max = df_out["benchmark"].cummax()
    bench_max_dd = float(((df_out["benchmark"] - bench_roll_max) / bench_roll_max).min())
    
    dsr_dict = deflated_sharpe_ratio(daily_rets)
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS: S22 ADAPTIVE ML CLASSIFIER")
    print("=" * 80)
    print(f"Backtest Period : {df_out.index[0].strftime('%Y-%m-%d')} to {df_out.index[-1].strftime('%Y-%m-%d')} ({years:.2f} Years)")
    print(f"Final NAV (S22) : ${final_nav:,.2f} MXN (Benchmark QQQ Buy&Hold: ${bench_final:,.2f} MXN)")
    print(f"Total Return    : {total_ret*100:+.2f}% (Benchmark: {bench_ret*100:+.2f}%)")
    print(f"CAGR            : {cagr*100:+.2f}% (Benchmark: {bench_cagr*100:+.2f}%)")
    print(f"Annual Vol      : {ann_vol*100:.2f}% (Benchmark: {bench_vol*100:.2f}%)")
    print(f"Sharpe (Rf=9.5%): {sharpe:.2f} (Benchmark: {bench_sharpe:.2f})")
    print(f"Max Drawdown    : {max_dd*100:.2f}% (Benchmark: {bench_max_dd*100:.2f}%)")
    print(f"Deflated Sharpe : {dsr_dict['dsr']*100:.2f}% (Hurdle Star: {dsr_dict['sr_star']*np.sqrt(252)*100:.2f}% Ann.)")
    print(f"Total trades    : {n_trades} (Total fees paid: ${fees:,.2f} MXN)")
    print("=" * 80)
    
    # Export Report
    report_md = f"""# Strategy 22 Backtest Report (Adaptive Random Forest Classifier)
**Executed:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** {df_out.index[0].strftime('%Y-%m-%d')} to {df_out.index[-1].strftime('%Y-%m-%d')} ({years:.2f} Years)

## Performance Comparison
| Metric | Strategy 22 (Adaptive Random Forest) | Benchmark (QQQ Buy-and-Hold) |
| :--- | :---: | :---: |
| **Final Portfolio NAV** | ${final_nav:,.2f} MXN | ${bench_final:,.2f} MXN |
| **Cumulative Return** | {total_ret*100:+.2f}% | {bench_ret*100:+.2f}% |
| **CAGR** | {cagr*100:+.2f}% | {bench_cagr*100:+.2f}% |
| **Annualized Volatility** | {ann_vol*100:.2f}% | {bench_vol*100:.2f}% |
| **Sharpe Ratio (Rf=9.5%)** | {sharpe:.2f} | {bench_sharpe:.2f} |
| **Maximum Drawdown** | {max_dd*100:.2f}% | {bench_max_dd*100:.2f}% |

## Probabilistic Verification (Bailey & Lopez de Prado)
* **Realized Sharpe (Daily Period):** {dsr_dict['sr_period']:.4f}
* **Regret Hurdle ($\mu_*$ Sharpe):** {dsr_dict['sr_star']:.4f}
* **Deflated Sharpe Ratio (DSR):** {dsr_dict['dsr']*100:.2f}%

## Execution Statistics
* **Starting Capital:** ${initial_nav:,.2f} MXN
* **Total Transactions:** {n_trades} trades
* **Total Commissions & VAT Paid:** ${fees:,.2f} MXN
* **Position Breakdown:**
  * Cash: {(df_out["position"] == 0).sum()} days
  * QQQ: {(df_out["position"] == 1).sum()} days
  * TQQQ: {(df_out["position"] == 2).sum()} days
  * SQQQ: {(df_out["position"] == 3).sum()} days
"""
    
    with open(os.path.join(dir_path, "strategy22_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)
        
    df_out.to_csv(os.path.join(dir_path, "strategy22_backtest_nav.csv"))
    print(f"Saved backtest NAV curve and logs successfully to: strategy22_backtest_nav.csv")
    print(f"Saved backtest markdown report successfully to: strategy22_backtest_report.md")

if __name__ == "__main__":
    main()
