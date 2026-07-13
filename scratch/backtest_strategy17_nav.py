import os
import sys
import datetime
import pandas as pd
import numpy as np
import yfinance as yf

# Universe of FIBRAs
FIBRA_TICKERS = [
    "FUNO11.MX", "FIBRAMQ12.MX", "FIBRAPL14.MX", "TERRA13.MX", "FMTY14.MX",
    "DANHOS13.MX", "FIDE12.MX", "FIHO12.MX", "FINN13.MX", "FSHOP13.MX"
]

START_DATE = "2021-06-01"  # start earlier to calculate SMA200 for 2022-06-21
END_DATE = "2026-07-03"
FEE_RATE = 0.0029
BONDIA_RATE = 0.0653

def get_historical_data():
    prices = {}
    dividends = {}
    debt_equity = {}
    
    print("Downloading historical data for FIBRAs backtest...")
    for t in FIBRA_TICKERS:
        ticker = yf.Ticker(t)
        # Download prices
        hist = yf.download(t, start=START_DATE, end=END_DATE, auto_adjust=False, progress=False)
        if hist.empty:
            continue
        close = hist["Close"].squeeze()
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        prices[t] = close
        
        # Download dividends
        divs = ticker.dividends
        if not divs.empty:
            if divs.index.tz is not None:
                divs.index = divs.index.tz_convert("UTC").tz_localize(None)
            dividends[t] = divs[(divs.index >= START_DATE) & (divs.index <= END_DATE)]
        else:
            dividends[t] = pd.Series(dtype=float)
            
        # Get Debt to Equity from ticker.info (assume constant backtest approximation)
        try:
            info = ticker.info
            de = info.get("debtToEquity")
            if de is not None and de > 5.0:
                de = de / 100.0
            debt_equity[t] = de if de is not None else 0.0
        except Exception:
            debt_equity[t] = 0.5  # safe default
            
    return prices, dividends, debt_equity

def get_val(series, date):
    if date in series.index:
        v = series.loc[date]
        return float(v.iloc[0]) if hasattr(v, "iloc") else float(v)
    past = series.index[series.index <= date]
    if not past.empty:
        v = series.loc[past[-1]]
        return float(v.iloc[0]) if hasattr(v, "iloc") else float(v)
    return 0.0

def run_backtest():
    prices, dividends, debt_equity = get_historical_data()
    
    # We want daily index from 2022-06-21 to 2026-07-02 (based on common trading days)
    trading_dates = sorted(list(prices["FUNO11.MX"].index))
    trading_dates = [d for d in trading_dates if d >= pd.Timestamp("2022-06-21") and d <= pd.Timestamp("2026-07-02")]
    
    initial_capital = 200000.0  # 200k MXN
    cash = initial_capital
    portfolio = {}  # ticker -> shares
    
    nav_history = []
    
    # Set up quarterly rebalance schedule
    rebalance_dates = [trading_dates[0]]
    for i in range(1, len(trading_dates)):
        prev_d = trading_dates[i-1]
        curr_d = trading_dates[i]
        if prev_d.month in [3, 6, 9, 12] and curr_d.month != prev_d.month:
            rebalance_dates.append(curr_d)
            
    last_dt = trading_dates[0]
    
    for d in trading_dates:
        # 1. Accrue Bondia cash interest
        days_elapsed = (d - last_dt).days
        if days_elapsed > 0 and cash > 0:
            daily_rate = BONDIA_RATE / 360.0
            accrued = cash * daily_rate * days_elapsed
            cash += accrued
            
        # 2. Accrue dividends paid
        for t, shares in list(portfolio.items()):
            if t in dividends and d in dividends[t].index:
                div_val = dividends[t].loc[d]
                if hasattr(div_val, "iloc"):
                    div_val = div_val.iloc[0]
                cash += shares * float(div_val)
                
        # 3. Rebalance day
        if d in rebalance_dates:
            # Rank candidates
            ranked = []
            for t in FIBRA_TICKERS:
                if t in prices and d in prices[t].index:
                    px = get_val(prices[t], d)
                    de = debt_equity.get(t, 0.0)
                    
                    # Calculate SMA 200 at this date
                    past_prices = prices[t].loc[prices[t].index <= d]
                    if len(past_prices) >= 200:
                        sma200 = past_prices.iloc[-200:].mean()
                    else:
                        sma200 = px
                        
                    # Calculate yield (trailing 12m)
                    one_yr_ago = d - pd.Timedelta(days=365)
                    divs_yr = dividends[t][(dividends[t].index >= one_yr_ago) & (dividends[t].index < d)]
                    dy = divs_yr.sum() / px if px > 0 else 0.0
                    
                    if dy >= 0.04 and de <= 1.5 and px > sma200:
                        score = dy * (1.0 / (1.0 + de))
                        ranked.append((t, px, dy, score))
                        
            ranked = sorted(ranked, key=lambda x: x[3], reverse=True)[:4]
            
            # Calculate current total portfolio value
            assets_val = 0.0
            for t, shares in portfolio.items():
                assets_val += shares * get_val(prices[t], d)
            portfolio_val = cash + assets_val
            
            # Target weights: 25% each
            target_weight = 0.25 if len(ranked) >= 4 else (1.0 / len(ranked) if ranked else 0.0)
            target_value = portfolio_val * target_weight
            
            # Liquidation of non-targets
            new_portfolio = {}
            target_tickers = [x[0] for x in ranked]
            for t, shares in list(portfolio.items()):
                if t not in target_tickers:
                    px = get_val(prices[t], d)
                    gross = shares * px
                    fee = gross * FEE_RATE
                    cash += (gross - fee)
                else:
                    new_portfolio[t] = shares
                    
            # Rebalance to targets
            for t, px, dy, score in ranked:
                curr_shares = new_portfolio.get(t, 0.0)
                curr_val = curr_shares * px
                diff = target_value - curr_val
                
                if diff > 0.01 * portfolio_val:
                    shares_to_buy = diff / px
                    cost = shares_to_buy * px
                    fee = cost * FEE_RATE
                    if cash >= (cost + fee):
                        cash -= (cost + fee)
                        new_portfolio[t] = curr_shares + shares_to_buy
                elif diff < -0.01 * portfolio_val:
                    shares_to_sell = abs(diff) / px
                    gross = shares_to_sell * px
                    fee = gross * FEE_RATE
                    cash += (gross - fee)
                    new_portfolio[t] = curr_shares - shares_to_sell
                else:
                    new_portfolio[t] = curr_shares
                    
            portfolio = new_portfolio
            
        # 4. Calculate daily NAV
        assets_val = 0.0
        for t, shares in portfolio.items():
            assets_val += shares * get_val(prices[t], d)
        nav = cash + assets_val
        nav_history.append({"date": d.strftime("%Y-%m-%d"), "nav": nav})
        
        last_dt = d
        
    df_out = pd.DataFrame(nav_history)
    df_out.to_csv("strategy17_backtest_nav.csv", index=False)
    print(f"FIBRA backtest completed. Saved to strategy17_backtest_nav.csv. Total return: {((df_out['nav'].iloc[-1]/df_out['nav'].iloc[0]) - 1.0)*100:+.2f}%")

if __name__ == "__main__":
    run_backtest()
