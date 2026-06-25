import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from skills.us_dcf_valuation import calculate_us_dcs

# Universe Configuration
US_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX", "AMD", "JPM"]
ALL_TICKERS = US_TICKERS + ["SPY", "^TNX"]

# Strategy params
START_DATE = "2021-06-20"
END_DATE = "2026-06-20"
INITIAL_CAPITAL = 100000.0  # USD
MONTHLY_CONTRIBUTION = 1000.0  # USD
SLIPPAGE_PCT = 0.0002       # 0.02% slippage / fee
USD_CASH_YIELD = 0.045       # 4.5% annual cash yield on reserves
MAX_CONCURRENT_POSITIONS = 3
MAX_POSITION_WEIGHT = 0.33

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    df["sma100"] = close.rolling(window=100).mean()
    
    # ATR 14
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()
    
    # MACD (12, 26, 9)
    fast_ema = close.ewm(span=12, adjust=False).mean()
    slow_ema = close.ewm(span=26, adjust=False).mean()
    df["macd"] = fast_ema - slow_ema
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    return df

def main():
    print("=" * 80)
    print("STARTING UPGRADED HIGH-BETA VALUE-MOMENTUM STRATEGY (STRATEGY 6)")
    print("=" * 80)

    # Download data with 1-year warmup buffer for rolling calculations
    warmup_start = (datetime.datetime.strptime(START_DATE, "%Y-%m-%d") - datetime.timedelta(days=450)).strftime("%Y-%m-%d")
    print(f"Downloading data for {len(ALL_TICKERS)} tickers from {warmup_start} to {END_DATE}...")
    
    data = yf.download(ALL_TICKERS, start=warmup_start, end=END_DATE, group_by='ticker', progress=False)
    
    # Process prices & daily returns
    daily_returns = pd.DataFrame()
    price_data = {}
    
    for t in ALL_TICKERS:
        if t in data.columns.levels[0] if isinstance(data.columns, pd.MultiIndex) else t in data.columns:
            df = data[t].dropna(how='all')
            price_data[t] = df
            if t not in ["SPY", "^TNX"]:
                daily_returns[t] = df["Close"].pct_change()
            elif t == "SPY":
                daily_returns["SPY"] = df["Close"].pct_change()
                
    # Calculate rolling beta relative to SPY
    rolling_beta = pd.DataFrame()
    spy_var = daily_returns["SPY"].rolling(252).var()
    
    for t in US_TICKERS:
        if t in daily_returns.columns:
            rolling_cov = daily_returns[t].rolling(252).cov(daily_returns["SPY"])
            rolling_beta[t] = rolling_cov / spy_var

    # Prepare dynamic risk-free rate from ^TNX
    rf_series = price_data["^TNX"]["Close"] / 100.0
    rf_series = rf_series.ffill().bfill()

    # Calculate indicators for each US stock
    indicators_dict = {}
    for t in US_TICKERS:
        if t in price_data:
            indicators_dict[t] = calculate_indicators(price_data[t])

    # Align dates
    spy_df = price_data["SPY"]
    common_idx = spy_df.loc[START_DATE:END_DATE].index
    sim_dates = sorted(list(common_idx))
    
    print(f"Simulation window: {len(sim_dates)} trading days.")
    
    # Simulation State
    cash = INITIAL_CAPITAL
    holdings = {}  # ticker: {shares, buy_price, peak_price, armed}
    trade_log = []
    nav_history = []
    dates_history = []
    
    total_contributed = INITIAL_CAPITAL
    last_month = sim_dates[0].month

    for i, date in enumerate(sim_dates):
        date_str = date.strftime("%Y-%m-%d")
        
        # 1. Accrue Daily Yield on Cash
        cash *= (1.0 + USD_CASH_YIELD / 252.0)
        
        # 2. Savings DCA Inflow
        if date.month != last_month:
            cash += MONTHLY_CONTRIBUTION
            total_contributed += MONTHLY_CONTRIBUTION
            last_month = date.month
            
        current_rf = float(rf_series.loc[date])
        
        # 3. Calculate portfolio NAV & Update peak prices
        current_equity = 0.0
        for ticker, h in list(holdings.items()):
            curr_close = float(price_data[ticker].loc[date, "Close"])
            current_equity += h["shares"] * curr_close
            
            # Update peak price for trailing stop
            h["last_price"] = curr_close
            if curr_close > h["peak_price"]:
                h["peak_price"] = curr_close
                unrealized_ret = (curr_close / h["buy_price"]) - 1.0
                if unrealized_ret >= 0.15: # Arm trailing stop at +15%
                    h["armed"] = True
                    
        portfolio_value = cash + current_equity
        nav_history.append(portfolio_value)
        dates_history.append(date)

        # 4. Check exits for current holdings
        for ticker, h in list(holdings.items()):
            curr_low = float(price_data[ticker].loc[date, "Low"])
            curr_close = float(price_data[ticker].loc[date, "Close"])
            
            exit_triggered = False
            exit_reason = ""
            
            # A. Trailing Stop (5% trail matching Strategy 2)
            if h["armed"]:
                if curr_low < h["peak_price"] * 0.95:
                    exit_triggered = True
                    exit_price = h["peak_price"] * 0.95
                    exit_reason = f"Strategy 2 Trailing Stop Triggered (Peak: ${h['peak_price']:.2f}, Trigger: ${exit_price:.2f})"
            
            # B. Indicator Signals (MACD cross down or bearish SMA 100 break)
            if not exit_triggered:
                ind_df = indicators_dict[ticker]
                day_loc = ind_df.index.get_loc(date)
                curr_macd = ind_df.iloc[day_loc]["macd"]
                curr_signal = ind_df.iloc[day_loc]["signal"]
                curr_sma = ind_df.iloc[day_loc]["sma100"]
                
                prev_macd = ind_df.iloc[day_loc-1]["macd"]
                prev_signal = ind_df.iloc[day_loc-1]["signal"]
                
                macd_cross_down = (prev_macd >= prev_signal) and (curr_macd < curr_signal)
                below_trend = curr_close < curr_sma
                
                if macd_cross_down:
                    exit_triggered = True
                    exit_price = curr_close
                    exit_reason = "MACD cross down"
                elif below_trend:
                    exit_triggered = True
                    exit_price = curr_close
                    exit_reason = "SMA 100 trend break"
                    
            if exit_triggered:
                shares_to_sell = h["shares"]
                gross_proceeds = shares_to_sell * exit_price
                fee = gross_proceeds * SLIPPAGE_PCT
                cash += (gross_proceeds - fee)
                
                realized_pnl = gross_proceeds - (shares_to_sell * h["buy_price"])
                pnl_pct = (exit_price / h["buy_price"] - 1.0) * 100.0
                
                trade_log.append({
                    "ticker": ticker,
                    "entry_date": h["entry_date"],
                    "exit_date": date_str,
                    "entry_price": h["buy_price"],
                    "exit_price": exit_price,
                    "shares": shares_to_sell,
                    "pnl": realized_pnl,
                    "pnl_pct": pnl_pct,
                    "reason": exit_reason
                })
                del holdings[ticker]

        # 5. Evaluate entries
        if len(holdings) >= MAX_CONCURRENT_POSITIONS:
            continue
            
        # Get active betas on this day
        active_betas = {}
        for t in US_TICKERS:
            if t in rolling_beta.columns and date in rolling_beta.index:
                val = rolling_beta.loc[date, t]
                if not pd.isna(val):
                    active_betas[t] = val
                    
        # Sort tickers by current rolling beta (highest first)
        sorted_by_beta = sorted(active_betas.items(), key=lambda x: x[1], reverse=True)
        
        candidates = []
        for ticker, beta_val in sorted_by_beta:
            if ticker in holdings:
                continue
                
            ind_df = indicators_dict[ticker]
            day_loc = ind_df.index.get_loc(date)
            curr_close = ind_df.iloc[day_loc]["Close"]
            curr_sma = ind_df.iloc[day_loc]["sma100"]
            curr_macd = ind_df.iloc[day_loc]["macd"]
            curr_signal = ind_df.iloc[day_loc]["signal"]
            
            prev_macd = ind_df.iloc[day_loc-1]["macd"]
            prev_signal = ind_df.iloc[day_loc-1]["signal"]
            
            macd_cross_up = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
            trend_bull = curr_close > curr_sma
            
            if trend_bull and macd_cross_up:
                # Calculate DCS Value Anchor
                try:
                    dcf_res = calculate_us_dcs(ticker, curr_close, current_rf)
                    dcs = float(dcf_res["margin_of_safety"])
                except Exception:
                    dcs = 0.0
                
                # Upgraded filter: must be fundamentally undervalued (DCS >= 0.15)
                if dcs >= 0.15:
                    candidates.append((ticker, beta_val, curr_close, dcs))
                
        # Place buy orders
        for ticker, beta_val, close_price, dcs_val in candidates:
            if len(holdings) >= MAX_CONCURRENT_POSITIONS:
                break
                
            ind_df = indicators_dict[ticker]
            day_loc = ind_df.index.get_loc(date)
            
            # ATR-based risk sizing (2% risk)
            curr_atr = float(ind_df.iloc[day_loc]["atr"])
            risk_amt = portfolio_value * 0.02
            stop_dist = 2.5 * curr_atr
            
            if stop_dist > 0:
                target_shares = risk_amt / stop_dist
                target_val = target_shares * close_price
            else:
                target_val = portfolio_value * MAX_POSITION_WEIGHT
                
            # Cap target cost at the weight cap
            target_val = min(target_val, portfolio_value * MAX_POSITION_WEIGHT)
            
            if target_val > cash:
                target_val = cash * 0.98
                
            shares = int(target_val / (close_price * (1.0 + SLIPPAGE_PCT)))
            if shares > 0:
                cost = shares * close_price
                fee = cost * SLIPPAGE_PCT
                total_cost = cost + fee
                
                cash -= total_cost
                holdings[ticker] = {
                    "shares": shares,
                    "buy_price": close_price,
                    "peak_price": close_price,
                    "armed": False,
                    "entry_date": date_str,
                    "beta": beta_val,
                    "dcs": dcs_val
                }

    # Force close remaining
    final_date_str = sim_dates[-1].strftime("%Y-%m-%d")
    final_portfolio_val = cash
    for ticker, h in list(holdings.items()):
        curr_close = float(price_data[ticker].loc[sim_dates[-1], "Close"])
        shares_to_sell = h["shares"]
        gross_proceeds = shares_to_sell * curr_close
        fee = gross_proceeds * SLIPPAGE_PCT
        final_portfolio_val += (gross_proceeds - fee)
        
        realized_pnl = gross_proceeds - (shares_to_sell * h["buy_price"])
        pnl_pct = (curr_close / h["buy_price"] - 1.0) * 100.0
        
        trade_log.append({
            "ticker": ticker,
            "entry_date": h["entry_date"],
            "exit_date": final_date_str,
            "entry_price": h["buy_price"],
            "exit_price": curr_close,
            "shares": shares_to_sell,
            "pnl": realized_pnl,
            "pnl_pct": pnl_pct,
            "reason": "Simulation End Forced Exit"
        })

    # Calculations
    nav_series = pd.Series(nav_history)
    daily_returns = nav_series.pct_change().dropna()
    total_months = len(sim_dates) / 21.0
    cagr = ((final_portfolio_val / total_contributed) ** (12.0 / total_months)) - 1.0 if total_contributed > 0 else 0.0
    
    risk_free_daily = USD_CASH_YIELD / 252.0
    excess_returns = daily_returns - risk_free_daily
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0.0
    
    running_max = nav_series.cummax()
    drawdowns = (nav_series - running_max) / running_max
    max_dd = drawdowns.min()
    
    n_trades = len(trade_log)
    win_trades = [t for t in trade_log if t["pnl"] > 0]
    win_rate = (len(win_trades) / n_trades * 100.0) if n_trades > 0 else 0.0

    # Save NAV history to CSV
    nav_df = pd.DataFrame({"Date": sim_dates, "NAV": nav_history})
    nav_df.to_csv("high_beta_backtest_nav.csv", index=False)
    print("NAV history saved to high_beta_backtest_nav.csv")

    print("=" * 80)
    print("STRATEGY 6 (UPGRADED HIGH-BETA VALUE-MOMENTUM) RESULTS")
    print(f"Final NAV: ${final_portfolio_val:,.2f} USD")
    print(f"CAGR (TWR): {cagr*100:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")
    print(f"Sharpe Ratio: {sharpe:.2f}")
    print(f"Total Trades: {n_trades}")
    print(f"Win Rate: {win_rate:.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    main()
