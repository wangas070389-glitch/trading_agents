"""
Strategy 25: Golden MACD Systematic (BMV Value Stocks)
======================================================
Trades the top 5 BMV Mexican stocks in MXN using Golden Ratio parameters:
  - Long-term Trend Filter: 55 EMA
  - MACD Crossover Engine: 13, 34, 8
  - Trailing Stop: Armed at 15.0% profit, trailing by 2.0%
"""
import os
import datetime
import numpy as np
import pandas as pd
from skills.golden_macd_backtest import simulate

TRADING_DAYS = 252
TRANSACTION_COST = 0.0029
BONDIA_YIELD = 0.0653
RF_MXN = 0.095

def download_data(tickers, start_date, end_date):
    import yfinance as yf
    print(f"Downloading daily data for {tickers}...")
    warmup_start = (datetime.datetime.strptime(start_date, "%Y-%m-%d") - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    
    if len(tickers) == 1:
        df = yf.download(tickers[0], start=warmup_start, end=end_date, progress=False)
        if df.empty:
            return {}
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]
        return {tickers[0]: df}
    else:
        data = yf.download(tickers, start=warmup_start, end=end_date, group_by='ticker', progress=False)
        universe_data = {}
        for ticker in tickers:
            try:
                if ticker in data.columns.levels[0]:
                    df = data[ticker].dropna(how='all')
                    if len(df) > 100:
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = [c[0].lower() for c in df.columns]
                        else:
                            df.columns = [c.lower() for c in df.columns]
                        universe_data[ticker] = df
            except Exception:
                continue
        return universe_data

def run_single_asset_simulation(df, ticker, initial_capital=40000.0):
    if not ticker.upper().endswith(".MX"):
        raise ValueError("S25 requires native-MXN BMV prices (.MX ticker)")
    return simulate(df["close"], initial_capital, BONDIA_YIELD, TRANSACTION_COST)

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    tickers = ["AMXB.MX", "WALMEX.MX", "GMEXICOB.MX", "FEMSAUBD.MX", "CEMEXCPO.MX"]
    start_date = "2010-02-11"
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    data = download_data(tickers, start_date, end_date)
    if not data:
        print("No stock data downloaded.")
        return
        
    # Align to common index
    common_idx = None
    for t, df in data.items():
        # Exclude warmup phase
        df_clean = df.loc[df.index >= start_date]
        if common_idx is None:
            common_idx = df_clean.index
        else:
            common_idx = common_idx.intersection(df_clean.index)
            
    dates = common_idx
    navs = []
    
    for t in tickers:
        if t in data:
            df_aligned = data[t].reindex(dates).ffill().bfill()
            n = run_single_asset_simulation(df_aligned, t, initial_capital=40000.0)
            navs.append(n)
            
    portfolio_nav = np.sum(navs, axis=0)
    
    # Save CSV
    pd.DataFrame(portfolio_nav, index=dates, columns=["strategy"]).to_csv(os.path.join(dir_path, "strategy25_backtest_nav.csv"))
    
    # Calculate performance metrics
    nav_series = pd.Series(portfolio_nav, index=dates)
    total_ret = nav_series.iloc[-1] / nav_series.iloc[0] - 1.0
    years = (nav_series.index[-1] - nav_series.index[0]).days / 365.25
    cagr = (nav_series.iloc[-1] / nav_series.iloc[0]) ** (1.0 / years) - 1.0
    daily_rets = nav_series.pct_change().dropna()
    vol = daily_rets.std() * np.sqrt(252)
    sharpe = (cagr - RF_MXN) / vol if vol > 0 else np.nan
    roll_max = nav_series.cummax()
    max_dd = float(((nav_series - roll_max) / roll_max).min())
    
    # Write report
    with open(os.path.join(dir_path, "strategy25_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(f"# Strategy 25: Golden MACD Systematic Backtest Report\n\n")
        f.write(f"**Period:** {dates[0].date()} to {dates[-1].date()}\n")
        f.write(f"**Capital Allocated:** $200,000.00 MXN\n\n")
        f.write(f"## Key Performance Metrics\n\n")
        f.write(f"- **Final Portfolio Value:** ${portfolio_nav[-1]:,.2f} MXN\n")
        f.write(f"- **Total Return:** {total_ret*100:+.2f}%\n")
        f.write(f"- **CAGR:** {cagr*100:.2f}%\n")
        f.write(f"- **Annualized Volatility:** {vol*100:.2f}%\n")
        f.write(f"- **Sharpe Ratio:** {sharpe:.4f}\n")
        f.write(f"- **Maximum Drawdown:** {max_dd*100:.2f}%\n")
        
    print("Strategy 25 Backtest Completed Successfully.")

if __name__ == "__main__":
    main()
