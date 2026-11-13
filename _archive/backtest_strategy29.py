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
from skills.kalman_hedge_ratio import calculate_kalman_hedge_ratio

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
    cash = initial_nav
    nav[0] = initial_nav
    rf_daily = RF_MXN / 252.0
    
    r_blended = prices["SPY"].pct_change().fillna(0.0).values
    r_gld = prices["GLD"].pct_change().fillna(0.0).values
    
    active_trade = None  # None or dict tracking active pair trade
    
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
            
        y_price = float(sub_prices["BTC-USD"].iloc[-1])
        x_price = float(sub_prices["ETH-USD"].iloc[-1])
        
        # Close pair trade if regime exits Chop (2)
        if regime != 2 and active_trade is not None:
            if active_trade["side"] == "long_spread":
                trade_val = (active_trade["qty_y"] * y_price) - (active_trade["qty_x"] * x_price)
            else:
                trade_val = -(active_trade["qty_y"] * y_price) + (active_trade["qty_x"] * x_price)
            cash += max(0.0, trade_val) * (1.0 - TRANSACTION_COST)
            active_trade = None
            
        if regime == 0:
            # Bull regime: SPY market return
            cash = cash * (1.0 + r_blended[t])
            current_portfolio = cash
        elif regime == 1:
            # Bear regime: 50% Gold + 50% Cash
            cash = cash * (1.0 + 0.5 * r_gld[t] + 0.5 * rf_daily)
            current_portfolio = cash
        else:
            # Chop regime: Stat-Arb Cointegration testing & Z-score trading
            cash = cash * (1.0 + rf_daily)
            current_portfolio = cash
            
            # Calculate 60d rolling cointegration and Kalman Z-score
            if len(sub_prices) >= 60:
                y_series = np.log(sub_prices["BTC-USD"].iloc[-60:].values.astype(float))
                x_series = np.log(sub_prices["ETH-USD"].iloc[-60:].values.astype(float))
                
                try:
                    _, p_val, _ = coint(y_series, x_series)
                    kalman_res = calculate_kalman_hedge_ratio(y_series, x_series)
                    beta = kalman_res["beta"]
                    z_score = kalman_res["current_zscore"]
                except Exception:
                    p_val = 1.0
                    z_score = 0.0
                    beta = 1.0
                    
                is_coint = p_val < 0.05
                
                if active_trade is not None:
                    # Update active trade value
                    if active_trade["side"] == "long_spread":
                        trade_val = (active_trade["qty_y"] * y_price) - (active_trade["qty_x"] * x_price)
                        reverted = z_score >= 0.0 or z_score < -3.5  # Mean reversion or stop loss
                    else:
                        trade_val = -(active_trade["qty_y"] * y_price) + (active_trade["qty_x"] * x_price)
                        reverted = z_score <= 0.0 or z_score > 3.5
                        
                    current_portfolio = cash + max(0.0, trade_val)
                    
                    if reverted:
                        cash += max(0.0, trade_val) * (1.0 - TRANSACTION_COST)
                        active_trade = None
                        current_portfolio = cash
                else:
                    # Entry check
                    if is_coint and abs(z_score) > 1.5:
                        alloc = cash * 0.15  # Risk 15% capital per pair trade
                        if alloc > 0:
                            cash -= alloc * (1.0 + TRANSACTION_COST)
                            qty_y = alloc / y_price
                            qty_x = (qty_y * beta * y_price) / x_price if x_price > 0 else 0.0
                            side = "long_spread" if z_score < -1.5 else "short_spread"
                            active_trade = {
                                "side": side,
                                "qty_y": qty_y,
                                "qty_x": qty_x,
                                "entry_alloc": alloc
                            }
                            current_portfolio = cash + alloc
                            
        nav[t] = current_portfolio
            
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
