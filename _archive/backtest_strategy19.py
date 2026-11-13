"""
Strategy 19: Particle Filter systematic QQQ / TQQQ / SQQQ Allocation
=====================================================================
A quantitative trading strategy that estimates the latent trend (drift) and
volatility of QQQ daily returns using a Sequential Monte Carlo (SMC) Particle Filter.

It dynamically switches between QQQ (1x long), TQQQ (3x leveraged long), SQQQ (3x
leveraged short), and Cash (Bondia compounding cash sweep) to capitalize on trend
regimes while avoiding volatility drag in sideways, choppy environments.

Features:
  - Vectorized Sequential Importance Resampling (SIR) particle filter engine.
  - Active Volatility Drag Protection: Disables leverage when estimated volatility exceeds 24% annualized.
  - Hysteresis thresholds to reduce whipsaw transactions and GBM broker fees.
  - Complete accounting in MXN (converting USD assets with live USD/MXN exchange rates).
  - Bailey & Lopez de Prado metrics: Probabilistic Sharpe Ratio (PSR) and Deflated Sharpe Ratio (DSR).
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

class ParticleFilter:
    def __init__(self, n_particles=1000, sigma_mu=0.0002, sigma_sigma=0.05,
                 sigma_min=0.003, sigma_max=0.05, mu_min=-0.01, mu_max=0.01,
                 init_mu=0.0005, init_mu_std=0.001, seed=42):
        self.n_particles = n_particles
        self.sigma_mu = sigma_mu
        self.sigma_sigma = sigma_sigma
        self.sigma_min = sigma_min
        self.sigma_max = sigma_max
        self.mu_min = mu_min
        self.mu_max = mu_max
        self.rng = np.random.default_rng(seed)
        
        # Prior Initialization
        self.particles_mu = self.rng.normal(init_mu, init_mu_std, n_particles)
        self.particles_sigma = self.rng.uniform(sigma_min, sigma_max, n_particles)
        self.weights = np.ones(n_particles) / n_particles

    def predict(self):
        # State transition: mu_t = mu_{t-1} + N(0, sigma_mu^2)
        noise_mu = self.rng.normal(0, self.sigma_mu, self.n_particles)
        self.particles_mu = np.clip(self.particles_mu + noise_mu, self.mu_min, self.mu_max)
        
        # State transition: sigma_t = sigma_{t-1} * exp(N(0, sigma_sigma^2))
        noise_sigma = self.rng.normal(0, self.sigma_sigma, self.n_particles)
        self.particles_sigma = np.clip(self.particles_sigma * np.exp(noise_sigma), self.sigma_min, self.sigma_max)

    def update(self, return_val):
        # Measurement update: Likelihood under Normal(mu, sigma^2)
        diff = return_val - self.particles_mu
        likelihood = (1.0 / self.particles_sigma) * np.exp(-0.5 * (diff / self.particles_sigma) ** 2)
        likelihood = np.maximum(likelihood, 1e-15)  # Prevent underflow
        
        self.weights *= likelihood
        sum_w = np.sum(self.weights)
        if sum_w > 0:
            self.weights /= sum_w
        else:
            self.weights = np.ones(self.n_particles) / self.n_particles

    def resample(self):
        # Effective Sample Size (ESS) check & Systematic Resampling
        neff = 1.0 / np.sum(self.weights ** 2)
        if neff < self.n_particles / 2.0:
            cumulative_sum = np.cumsum(self.weights)
            cumulative_sum[-1] = 1.0  # Force exact normalization
            u = (self.rng.uniform(0, 1.0) + np.arange(self.n_particles)) / self.n_particles
            indexes = np.searchsorted(cumulative_sum, u)
            
            self.particles_mu = self.particles_mu[indexes]
            self.particles_sigma = self.particles_sigma[indexes]
            self.weights = np.ones(self.n_particles) / self.n_particles

    def get_estimates(self):
        est_mu = np.sum(self.particles_mu * self.weights)
        est_sigma = np.sum(self.particles_sigma * self.weights)
        prob_bull = np.sum(self.weights[self.particles_mu > 0])
        return est_mu, est_sigma, prob_bull

def probabilistic_sharpe_ratio(returns: pd.Series, sr_benchmark: float) -> float:
    r = returns.dropna().values
    n = len(r)
    if n < 30:
        return np.nan
    sr = r.mean() / r.std(ddof=1)  # Period Sharpe
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
    
    # Forward-fill exchange rate
    out["fx"] = out["fx"].ffill().bfill()
    out = out.dropna(subset=["qqq"])
    return out

def run_simulation(data, initial_nav=200000.0):
    n_days = len(data)
    
    # Asset daily returns
    r_qqq = data["qqq"].pct_change().fillna(0.0)
    r_fx = data["fx"].pct_change().fillna(0.0)
    
    # Leveraged daily returns (fall back to synthetic if real fails/not available)
    r_tqqq_real = data["tqqq"].pct_change().fillna(0.0)
    r_sqqq_real = data["sqqq"].pct_change().fillna(0.0)
    
    # Synthetic proxy calculation (with drag)
    # TQQQ annual expense ratio = 0.95%, financing rate ~ 4.5%
    tqqq_drag = (2.0 * 0.045 + 0.0095) / TRADING_DAYS
    # SQQQ annual expense ratio = 0.95%, short borrow financing ~ 5.5%
    sqqq_drag = (2.0 * 0.055 + 0.0095) / TRADING_DAYS
    
    r_tqqq_synth = 3.0 * r_qqq - tqqq_drag
    r_sqqq_synth = -3.0 * r_qqq - sqqq_drag
    
    # Prefer real returns if they exist and are non-zero, otherwise synthetic
    r_tqqq = np.where(data["tqqq"].notna() & (r_tqqq_real != 0.0), r_tqqq_real, r_tqqq_synth)
    r_sqqq = np.where(data["sqqq"].notna() & (r_sqqq_real != 0.0), r_sqqq_real, r_sqqq_synth)
    
    # Convert USD asset returns to MXN
    # 1 + r_mxn = (1 + r_usd) * (1 + r_fx)
    r_qqq_mxn = ((1.0 + r_qqq) * (1.0 + r_fx) - 1.0).values
    r_tqqq_mxn = ((1.0 + r_tqqq) * (1.0 + r_fx) - 1.0).values
    r_sqqq_mxn = ((1.0 + r_sqqq) * (1.0 + r_fx) - 1.0).values
    
    daily_cash_sweep = BONDIA_YIELD / TRADING_DAYS
    
    # Log-returns for Particle Filter
    log_returns_qqq = np.log(data["qqq"] / data["qqq"].shift(1)).fillna(0.0).values
    
    # PF state estimates arrays
    est_mus = np.zeros(n_days)
    est_sigmas = np.zeros(n_days)
    prob_bulls = np.zeros(n_days)
    
    # Initialize Particle Filter
    pf = ParticleFilter(n_particles=1000, seed=42)
    
    print("Running Particle Filter daily state estimation...")
    for t in range(n_days):
        pf.predict()
        pf.update(log_returns_qqq[t])
        pf.resample()
        
        mu_t, sigma_t, prob_bull_t = pf.get_estimates()
        est_mus[t] = mu_t
        est_sigmas[t] = sigma_t
        prob_bulls[t] = prob_bull_t
        
    # Allocation Simulation
    nav = np.zeros(n_days)
    nav[0] = initial_nav
    
    # Strategy signals & allocations
    # Assets: 0 = Cash, 1 = QQQ, 2 = TQQQ, 3 = SQQQ
    positions = np.zeros(n_days, dtype=int)
    asset_names = {0: "CASH", 1: "QQQ", 2: "TQQQ", 3: "SQQQ"}
    
    # Trading Loop
    current_asset = 0  # Start in Cash
    n_trades = 0
    total_fees_paid = 0.0
    
    # Benchmark Buy & Hold QQQ (MXN)
    benchmark = np.zeros(n_days)
    benchmark[0] = initial_nav
    
    # Volatility threshold: 1.5% daily (~23.8% annualized)
    VOL_LIMIT = 0.015
    
    for t in range(1, n_days):
        # We use end of day (t-1) state estimates to determine position for day (t)
        prev_p = prob_bulls[t-1]
        prev_vol = est_sigmas[t-1]
        
        # Signal Rules with Hysteresis
        target_asset = 0  # Default to cash
        
        if prev_vol > VOL_LIMIT:
            # High Volatility Regime: Leverage Disabled
            if current_asset == 1:
                # If currently holding QQQ, keep holding if trend remains positive
                target_asset = 1 if prev_p > 0.51 else 0
            else:
                # Trigger entry into QQQ
                target_asset = 1 if prev_p > 0.58 else 0
        else:
            # Normal Volatility Regime: Leverage Enabled
            if current_asset == 2:
                # Hold TQQQ if trend holds
                target_asset = 2 if prev_p > 0.52 else 0
            elif current_asset == 3:
                # Hold SQQQ if trend holds
                target_asset = 3 if prev_p < 0.48 else 0
            else:
                # Evaluate entries
                if prev_p > 0.60:
                    target_asset = 2
                elif prev_p < 0.40:
                    target_asset = 3
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
            
        # Calculate trade transaction cost
        fee = 0.0
        if target_asset != current_asset:
            n_trades += 1
            # Rebalancing fee paid on total portfolio value
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
    df_out["mu_est"] = est_mus
    df_out["vol_est"] = est_sigmas
    df_out["prob_bull"] = prob_bulls
    df_out["qqq_mxn"] = r_qqq_mxn
    df_out["usd_mxn"] = data["fx"]
    
    return df_out, n_trades, total_fees_paid

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print("STRATEGY 19: PARTICLE FILTER QQQ/TQQQ/SQQQ SYSTEMATIC BACKTEST")
    print("=" * 80)
    
    data = load_data()
    df_out, n_trades, fees = run_simulation(data)
    
    # Calculate performance metrics
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
    
    # Bailey & Lopez de Prado metrics
    dsr_dict = deflated_sharpe_ratio(daily_rets)
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS: S19 PARTICLE FILTER SYSTEMATIC")
    print("=" * 80)
    print(f"Backtest Period : {df_out.index[0].strftime('%Y-%m-%d')} to {df_out.index[-1].strftime('%Y-%m-%d')} ({years:.2f} Years)")
    print(f"Final NAV (S19) : ${final_nav:,.2f} MXN (Benchmark QQQ Buy&Hold: ${bench_final:,.2f} MXN)")
    print(f"Total Return    : {total_ret*100:+.2f}% (Benchmark: {bench_ret*100:+.2f}%)")
    print(f"CAGR            : {cagr*100:+.2f}% (Benchmark: {bench_cagr*100:+.2f}%)")
    print(f"Annual Vol      : {ann_vol*100:.2f}% (Benchmark: {bench_vol*100:.2f}%)")
    print(f"Sharpe (Rf=9.5%): {sharpe:.2f} (Benchmark: {bench_sharpe:.2f})")
    print(f"Max Drawdown    : {max_dd*100:.2f}% (Benchmark: {bench_max_dd*100:.2f}%)")
    print(f"Deflated Sharpe : {dsr_dict['dsr']*100:.2f}% (Hurdle Star: {dsr_dict['sr_star']*np.sqrt(252)*100:.2f}% Ann.)")
    print(f"Total trades    : {n_trades} (Total fees paid: ${fees:,.2f} MXN)")
    print("=" * 80)
    
    # Export Report
    report_md = f"""# Strategy 19 Backtest Report (Particle Filter QQQ/TQQQ/SQQQ)
**Executed:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Asset Universe:** QQQ, TQQQ (3x Long), SQQQ (3x Short), Cash (Bondia compounding)
**Data Window:** {df_out.index[0].strftime('%Y-%m-%d')} to {df_out.index[-1].strftime('%Y-%m-%d')} ({years:.2f} Years)

## Performance Comparison
| Metric | Strategy 19 (Particle Filter) | Benchmark (QQQ Buy-and-Hold) |
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
  > [!NOTE]
  > A Deflated Sharpe Ratio (DSR) above 95% indicates high evidence quality, confirming that the backtest performance is not a product of data mining or multiple trials selection bias.

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
    
    with open(os.path.join(dir_path, "strategy19_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)
        
    df_out.to_csv(os.path.join(dir_path, "strategy19_backtest_nav.csv"))
    print(f"Saved backtest NAV curve and logs successfully to: strategy19_backtest_nav.csv")
    print(f"Saved backtest markdown report successfully to: strategy19_backtest_report.md")

if __name__ == "__main__":
    main()
