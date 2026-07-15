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
    
    # Simulating S1/S4 index proxy returns
    r_blended = prices["SPY"].pct_change().fillna(0.0).values
    r_gld = prices["GLD"].pct_change().fillna(0.0).values
    
    pairs = [("BTC-USD", "ETH-USD")]
    active_trades = {}
    
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
            
        # Pairs liquidation on regime exit
        if regime != 2 and active_trades:
            for pair in list(active_trades.keys()):
                trade = active_trades[pair]
                y_p = float(sub_prices["BTC-USD"].iloc[-1])
                x_p = float(sub_prices["ETH-USD"].iloc[-1])
                val = (trade["qty_y"] * y_p) - (trade["qty_x"] * x_p) if trade["side"] == "long" else -(trade["qty_y"] * y_p) + (trade["qty_x"] * x_p)
                cash += val * (1.0 - TRANSACTION_COST)
                del active_trades[pair]
                
        if regime == 0:
            nav[t] = nav[t-1] * (1.0 + r_blended[t])
            cash = cash * (1.0 + rf_daily)
        elif regime == 1:
            nav[t] = nav[t-1] * (1.0 + 0.5 * r_gld[t] + 0.5 * rf_daily)
            cash = cash * (1.0 + rf_daily)
        else:
            # Chop
            cash = cash * (1.0 + rf_daily)
            nav[t] = cash
            
            for pair in pairs:
                y_series = np.log(sub_prices["BTC-USD"].iloc[-89:].astype(float))
                x_series = np.log(sub_prices["ETH-USD"].iloc[-89:].astype(float))
                y_p = float(sub_prices["BTC-USD"].iloc[-1])
                x_p = float(sub_prices["ETH-USD"].iloc[-1])
                
                try:
                    _, p_val, _ = coint(y_series, x_series)
                except Exception:
                    p_val = 1.0
                    
                if p_val < 0.05 and pair not in active_trades:
                    try:
                        ols = sm.OLS(y_series, sm.add_constant(x_series)).fit()
                        beta = ols.params.iloc[1]
                        active_trades[pair] = {"side": "long", "qty_y": 1.0, "qty_x": beta, "entry_val": y_p - beta * x_p}
                        cash -= (y_p + beta * x_p) * TRANSACTION_COST
                    except Exception:
                        pass
                        
        if regime != 2:
            nav[t] = nav[t-1]
            
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
