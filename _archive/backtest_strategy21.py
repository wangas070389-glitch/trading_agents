"""
Strategy 21: Shannon Entropy & Information Theory Systematic QQQ / TQQQ / SQQQ Allocation
========================================================================================
This strategy uses Shannon Information Entropy to dynamically select the QQQ exposure regime.
It calculates the rolling Normalized Shannon Entropy (H_t) of QQQ daily returns:
  - H_t <= 0.85: Ordered, predictable trending market. We allocate to TQQQ (3x Long) or SQQQ (3x Short)
    depending on the direction of a dual-SMA filter (50-day vs. 120-day SMA).
  - H_t > 0.85: Disordered, highly uncertain market. We exit to Cash (Bondia cash sweep at 6.53%)
    to avoid volatility drag and commission bleed.

Hysteresis trading bands are used to minimize transaction costs (0.29% GBM fee).
"""
import os
import sys
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

TRADING_DAYS = 252
TRANSACTION_COST = 0.0029  # 0.29% GBM fee (comissions + spread + VAT)
BONDIA_YIELD = 0.0653      # 6.53% MXN cash compound yield
RF_MXN = 0.095             # 9.5% Benchmark MXN Risk-Free Rate for Sharpe

def calculate_shannon_entropy_rolling(returns, window_size=60, num_bins=10):
    """
    Computes a rolling Normalized Shannon Entropy of QQQ daily returns.
    """
    n = len(returns)
    entropy_values = np.full(n, 1.0)  # Default to maximum uncertainty
    
    max_entropy = np.log2(num_bins)
    
    for i in range(window_size, n):
        sub_series = returns[i - window_size : i]
        
        # Discretize using histogram binning
        counts, _ = np.histogram(sub_series, bins=num_bins)
        probs = counts / window_size
        
        # Filter out zero probabilities to avoid log2(0)
        probs = probs[probs > 0]
        
        # Calculate Shannon Entropy
        entropy = -np.sum(probs * np.log2(probs))
        
        # Normalize between 0 and 1
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
    # Start in 2010 to align with leveraged ETFs inception
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

def run_simulation(data, initial_nav=200000.0, entry_thresh=0.85, exit_thresh=0.88):
    n_days = len(data)
    
    # Asset daily returns
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
    
    # Calculate rolling Normalized Shannon Entropy on return series
    qqq_returns = data["qqq"].pct_change().fillna(0.0).values
    entropy_values = calculate_shannon_entropy_rolling(qqq_returns, window_size=60, num_bins=10)
    
    # Smooth entropy slightly to filter short-term noise
    entropy_series = pd.Series(entropy_values)
    entropy_smoothed = entropy_series.rolling(window=5, min_periods=1).mean().values
    
    # Dual-SMA trend indicators
    sma_fast = data["qqq"].rolling(50).mean().values
    sma_slow = data["qqq"].rolling(120).mean().values
    
    # Allocation Simulation
    nav = np.zeros(n_days)
    nav[0] = initial_nav
    
    # Assets: 0 = Cash, 1 = QQQ, 2 = TQQQ, 3 = SQQQ
    positions = np.zeros(n_days, dtype=int)
    
    current_asset = 0
    n_trades = 0
    total_fees_paid = 0.0
    
    benchmark = np.zeros(n_days)
    benchmark[0] = initial_nav
    
    # Strategy Rules with Hysteresis
    # Ordered threshold: H <= 0.85. Disordered threshold: H > 0.85.
    # Hysteresis band: exit trending only if H > 0.88
    for t in range(1, n_days):
        h_val = entropy_smoothed[t-1]
        fast_sma = sma_fast[t-1]
        slow_sma = sma_slow[t-1]
        
        target_asset = 0  # Default to cash
        
        # Check if trend is defined (requires SMAs to be non-nan)
        if np.isnan(fast_sma) or np.isnan(slow_sma):
            target_asset = 0
        else:
            is_bull = fast_sma > slow_sma
            
            # Evaluate Entropy regime
            if current_asset in (2, 3):
                # We currently hold a trending asset (TQQQ/SQQQ)
                # Exit if Entropy rises above exit_thresh or trend flips
                if h_val < exit_thresh:
                    if current_asset == 2:
                        target_asset = 2 if is_bull else 3
                    else:
                        target_asset = 3 if not is_bull else 2
                else:
                    target_asset = 0
            else:
                # We currently hold Cash
                # Enter trending asset if Entropy falls below entry_thresh
                if h_val <= entry_thresh:
                    target_asset = 2 if is_bull else 3
                else:
                    target_asset = 0
                    
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
    df_out["entropy_raw"] = entropy_values
    df_out["entropy_smoothed"] = entropy_smoothed
    df_out["qqq_mxn"] = r_qqq_mxn
    df_out["usd_mxn"] = data["fx"]
    
    return df_out, n_trades, total_fees_paid

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print("STRATEGY 21: SHANNON ENTROPY SYSTEMATIC BACKTEST")
    print("=" * 80)
    
    data = load_data()
    
    # We will test thresholds dynamically or use default
    df_out, n_trades, fees = run_simulation(data, entry_thresh=0.85, exit_thresh=0.88)
    
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
    print("BACKTEST RESULTS: S21 SHANNON ENTROPY SYSTEMATIC")
    print("=" * 80)
    print(f"Backtest Period : {df_out.index[0].strftime('%Y-%m-%d')} to {df_out.index[-1].strftime('%Y-%m-%d')} ({years:.2f} Years)")
    print(f"Final NAV (S21) : ${final_nav:,.2f} MXN (Benchmark QQQ Buy&Hold: ${bench_final:,.2f} MXN)")
    print(f"Total Return    : {total_ret*100:+.2f}% (Benchmark: {bench_ret*100:+.2f}%)")
    print(f"CAGR            : {cagr*100:+.2f}% (Benchmark: {bench_cagr*100:+.2f}%)")
    print(f"Annual Vol      : {ann_vol*100:.2f}% (Benchmark: {bench_vol*100:.2f}%)")
    print(f"Sharpe (Rf=9.5%): {sharpe:.2f} (Benchmark: {bench_sharpe:.2f})")
    print(f"Max Drawdown    : {max_dd*100:.2f}% (Benchmark: {bench_max_dd*100:.2f}%)")
    print(f"Deflated Sharpe : {dsr_dict['dsr']*100:.2f}% (Hurdle Star: {dsr_dict['sr_star']*np.sqrt(252)*100:.2f}% Ann.)")
    print(f"Total trades    : {n_trades} (Total fees paid: ${fees:,.2f} MXN)")
    print("=" * 80)
    
    # Export Report
    report_md = f"""# Strategy 21 Backtest Report (Shannon Entropy Dynamic Allocation)
**Executed:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** {df_out.index[0].strftime('%Y-%m-%d')} to {df_out.index[-1].strftime('%Y-%m-%d')} ({years:.2f} Years)

## Performance Comparison
| Metric | Strategy 21 (Shannon Entropy) | Benchmark (QQQ Buy-and-Hold) |
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
    
    with open(os.path.join(dir_path, "strategy21_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)
        
    df_out.to_csv(os.path.join(dir_path, "strategy21_backtest_nav.csv"))
    print(f"Saved backtest NAV curve and logs successfully to: strategy21_backtest_nav.csv")
    print(f"Saved backtest markdown report successfully to: strategy21_backtest_report.md")

if __name__ == "__main__":
    main()
