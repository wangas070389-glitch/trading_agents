"""
Strategy 29: Golden Stat-Arb Cointegration System
=================================================
Trades daily ETF/Crypto/FX pairs in MXN using Golden Ratio parameters:
  - Cointegration lookback window: 89 days (Fibonacci)
  - HMM consensus filter (majority vote over 3 days) to manage regimes
"""
import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
from statsmodels.tsa.stattools import coint
import statsmodels.api as sm

TRADING_DAYS = 252
TRANSACTION_COST = 0.0029
BONDIA_YIELD = 0.0653
RF_MXN = 0.095

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    tickers = ["SPY", "GLD", "BTC-USD", "ETH-USD"]
    print("Downloading Strategy 9/29 pricing universe...")
    data = yf.download(tickers, start="2021-06-20", end="2026-07-01", group_by="ticker", progress=False)
    
    prices = pd.DataFrame()
    for t in tickers:
        prices[t] = data[t]["Close"].ffill().bfill()
    prices = prices.dropna()
    spy_returns = prices["SPY"].pct_change().dropna()
    
    # Train 3-State Gaussian HMM on SPY returns
    spy_rets_vals = spy_returns.values.reshape(-1, 1)
    hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
    hmm.fit(spy_rets_vals)
    regimes = hmm.predict(spy_rets_vals)
    
    state_vols = [np.std(spy_rets_vals[regimes == i]) for i in range(3)]
    bear_state = np.argmax(state_vols)
    rem = [i for i in range(3) if i != bear_state]
    state_means = [np.mean(spy_rets_vals[regimes == i]) for i in range(3)]
    bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
    
    n = len(prices)
    nav = np.zeros(n)
    initial_nav = 200000.0
    nav[0] = initial_nav
    cash = initial_nav
    rf_daily = RF_MXN / 252.0
    
    r_btc = prices["BTC-USD"].pct_change().fillna(0.0).values
    r_eth = prices["ETH-USD"].pct_change().fillna(0.0).values
    r_blended = prices["SPY"].pct_change().fillna(0.0).values
    r_gld = prices["GLD"].pct_change().fillna(0.0).values
    
    current_position = 0 # 0: Cash, 1: Bull Blended, 2: Bear Gold, 3: Stat-Arb Pair
    pair_beta = 1.0
    
    for t in range(1, n):
        date = prices.index[t]
        sub_prices = prices.iloc[:t+1]
        
        # HMM regime consensus
        spy_sub = spy_returns.loc[:date].values.reshape(-1, 1)
        if len(spy_sub) < 3:
            regime = 2
        else:
            all_pred = hmm.predict(spy_sub)
            last_3_raw = all_pred[-3:]
            last_3_regimes = []
            for r in last_3_raw:
                if r == bull_state: last_3_regimes.append(0)
                elif r == bear_state: last_3_regimes.append(1)
                else: last_3_regimes.append(2)
            regime = max(set(last_3_regimes), key=last_3_regimes.count)
            
        fee = 0.0
        ret = 0.0
        
        if regime == 0:
            target_pos = 1
            ret = r_blended[t]
        elif regime == 1:
            target_pos = 2
            ret = 0.5 * r_gld[t] + 0.5 * rf_daily
        else:
            # Chop - check cointegration of BTC vs ETH over 89d
            y_series = np.log(sub_prices["BTC-USD"].iloc[-89:].astype(float))
            x_series = np.log(sub_prices["ETH-USD"].iloc[-89:].astype(float))
            
            try:
                _, p_val, _ = coint(y_series, x_series)
            except Exception:
                p_val = 1.0
                
            if p_val < 0.05:
                target_pos = 3
                try:
                    ols = sm.OLS(y_series, sm.add_constant(x_series)).fit()
                    pair_beta = float(ols.params.iloc[1])
                except Exception:
                    pair_beta = 1.0
                # Spread return: 0.5 * BTC return - 0.5 * beta * ETH return + 0.5 * rf_daily
                ret = 0.5 * r_btc[t] - 0.5 * pair_beta * r_eth[t] + 0.5 * rf_daily
            else:
                target_pos = 0
                ret = rf_daily

        if target_pos != current_position:
            fee = nav[t-1] * TRANSACTION_COST
            current_position = target_pos

        nav[t] = nav[t-1] * (1.0 + ret) - fee
            
    # Save CSV
    pd.DataFrame(nav, index=prices.index, columns=["strategy"]).to_csv(os.path.join(dir_path, "strategy29_backtest_nav.csv"))
    
    # Calculate performance metrics
    nav_series = pd.Series(nav, index=prices.index)
    total_ret = nav_series.iloc[-1] / nav_series.iloc[0] - 1.0
    years = (nav_series.index[-1] - nav_series.index[0]).days / 365.25
    cagr = (nav_series.iloc[-1] / nav_series.iloc[0]) ** (1.0 / years) - 1.0
    daily_rets = nav_series.pct_change().dropna()
    vol = daily_rets.std() * np.sqrt(252)
    sharpe = (cagr - RF_MXN) / vol if vol > 0 else np.nan
    roll_max = nav_series.cummax()
    max_dd = float(((nav_series - roll_max) / roll_max).min())
    
    # Write report
    with open(os.path.join(dir_path, "strategy29_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(f"# Strategy 29: Golden Stat-Arb Cointegration Backtest Report\n\n")
        f.write(f"**Period:** {prices.index[0].date()} to {prices.index[-1].date()}\n")
        f.write(f"**Capital Allocated:** $200,000.00 MXN\n\n")
        f.write(f"## Key Performance Metrics\n\n")
        f.write(f"- **Final Portfolio Value:** ${nav[-1]:,.2f} MXN\n")
        f.write(f"- **Total Return:** {total_ret*100:+.2f}%\n")
        f.write(f"- **CAGR:** {cagr*100:.2f}%\n")
        f.write(f"- **Annualized Volatility:** {vol*100:.2f}%\n")
        f.write(f"- **Sharpe Ratio:** {sharpe:.4f}\n")
        f.write(f"- **Maximum Drawdown:** {max_dd*100:.2f}%\n")
        
    print("Strategy 29 Backtest Completed Successfully.")

if __name__ == "__main__":
    main()
