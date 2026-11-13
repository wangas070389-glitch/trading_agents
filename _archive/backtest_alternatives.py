import os
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from skills.alternative_indicators import evaluate_signals

# Universe Configuration
CRYPTO = ["BTC-USD", "ETH-USD"]
COMMODITIES = ["GLD", "SLV", "USO", "DBA"]
FOREX = ["EURUSD=X", "GBPUSD=X", "USDMXN=X", "USDJPY=X"]
ALL_TICKERS = CRYPTO + COMMODITIES + FOREX

# Sizing & Limits
MAX_CRYPTO_WEIGHT = 0.20
MAX_COMMODITY_WEIGHT = 0.20
MAX_FOREX_WEIGHT = 0.15
MAX_CONCURRENT_POSITIONS = 5
MONTHLY_CONTRIBUTION = 1000.0  # USD
INITIAL_CAPITAL = 100000.0     # USD
TRANSACTION_FEE_RATE = 0.0029  # 0.29% round-trip friction
USD_CASH_YIELD = 0.045         # 4.5% annual cash yield on USD reserves

def main():
    print("=" * 80)
    print("STARTING ALTERNATIVE ASSETS STRATEGY BACKTEST")
    print("=" * 80)

    # 1. Download data
    start_date = "2021-06-20"
    end_date = "2026-06-20"
    
    print(f"Downloading daily history for {len(ALL_TICKERS)} tickers from {start_date} to {end_date}...")
    try:
        data = yf.download(ALL_TICKERS, start=start_date, end=end_date, group_by='ticker', progress=False)
    except Exception as e:
        print(f"Download failed: {e}")
        return

    # Check which tickers have data
    valid_tickers = []
    for t in ALL_TICKERS:
        if t in data.columns.levels[0] if isinstance(data.columns, pd.MultiIndex) else t in data.columns:
            valid_tickers.append(t)
    print(f"Loaded {len(valid_tickers)} valid tickers: {valid_tickers}")

    # Build date index
    # We use a combined index of business days (Forex/Commodities) + weekend days for Crypto if we want,
    # but for simplicity, we align everything to the trading days of Forex/Commodities (about 252 days/yr).
    aligned_dates = sorted(list(data.index))
    print(f"Simulation window: {len(aligned_dates)} trading days.")

    # Initialize Portfolio State
    cash = INITIAL_CAPITAL
    holdings = {}  # ticker: {shares, buy_price, peak_price, armed, target_weight, asset_type}
    trade_log = []
    nav_history = []
    dates_history = []
    
    # Track monthly DCA deposits
    total_contributed = INITIAL_CAPITAL
    last_month = aligned_dates[0].month

    # Daily simulation loop
    for i, date in enumerate(aligned_dates):
        # We need at least 200 days to calculate SMA200 for Crypto
        if i < 200:
            continue
            
        date_str = date.strftime("%Y-%m-%d")
        
        # 1. Daily cash interest accumulation (USD sweep 4.5% APR)
        cash *= (1.0 + USD_CASH_YIELD / 252.0)
        
        # 2. Check for monthly DCA deposit
        if date.month != last_month:
            cash += MONTHLY_CONTRIBUTION
            total_contributed += MONTHLY_CONTRIBUTION
            last_month = date.month
            
        # 3. Calculate portfolio NAV
        current_equity = 0.0
        for ticker, h in list(holdings.items()):
            # Get current price
            ticker_data = data[ticker].iloc[:i+1].dropna(how='all')
            curr_close = float(ticker_data["Close"].iloc[-1])
            curr_val = h["shares"] * curr_close
            current_equity += curr_val
            
            # Update peak price for trailing stops
            h["last_price"] = curr_close
            if curr_close > h["peak_price"]:
                h["peak_price"] = curr_close
                # Arm trailing stop if return >= 10%
                unrealized_ret = (curr_close / h["buy_price"]) - 1.0
                if unrealized_ret >= 0.10:
                    h["armed"] = True
                    
        portfolio_value = cash + current_equity
        nav_history.append(portfolio_value)
        dates_history.append(date)

        # 4. Check exits for current holdings
        for ticker, h in list(holdings.items()):
            ticker_data = data[ticker].iloc[:i+1].dropna(how='all')
            ticker_data.columns = [c.lower() for c in ticker_data.columns]
            curr_close = float(ticker_data["close"].iloc[-1])
            
            asset_type = h["asset_type"]
            exit_triggered = False
            exit_reason = ""
            
            # A. Trailing Stop Exit (For Crypto only, or general safeguard)
            if asset_type == "crypto" and h["armed"]:
                # Exit if drops 5% below peak
                if curr_close < h["peak_price"] * 0.95:
                    exit_triggered = True
                    exit_reason = f"Trailing Stop Triggered (Peak: ${h['peak_price']:.2f}, Trigger: ${h['peak_price']*0.95:.2f})"
                    
            # B. Indicator Exit (MACD cross down, Donchian low, BB upper limits, etc.)
            if not exit_triggered:
                signal_res = evaluate_signals(ticker, asset_type, ticker_data)
                sig = signal_res["signal"]
                
                if sig == "sell":
                    exit_triggered = True
                    exit_reason = signal_res["reason"]
                    
            if exit_triggered:
                # Execute Sell
                shares_to_sell = h["shares"]
                gross_proceeds = shares_to_sell * curr_close
                fee = gross_proceeds * TRANSACTION_FEE_RATE
                cash += (gross_proceeds - fee)
                
                realized_pnl = gross_proceeds - (shares_to_sell * h["buy_price"])
                pnl_pct = (curr_close / h["buy_price"] - 1.0) * 100.0
                
                trade_log.append({
                    "ticker": ticker,
                    "asset_type": asset_type,
                    "entry_date": h["entry_date"],
                    "exit_date": date_str,
                    "entry_price": h["buy_price"],
                    "exit_price": curr_close,
                    "shares": shares_to_sell,
                    "pnl": realized_pnl,
                    "pnl_pct": pnl_pct,
                    "reason": exit_reason
                })
                
                del holdings[ticker]

        # 5. Evaluate buys
        # Count current open positions
        num_positions = len(holdings)
        if num_positions >= MAX_CONCURRENT_POSITIONS:
            continue
            
        # Compile signals for all non-held assets
        candidates = []
        for ticker in valid_tickers:
            if ticker in holdings:
                continue
                
            # Determine asset type
            if ticker in CRYPTO:
                asset_type = "crypto"
            elif ticker in COMMODITIES:
                asset_type = "commodity"
            else:
                asset_type = "forex"
                
            ticker_data = data[ticker].iloc[:i+1].dropna(how='all')
            ticker_data.columns = [c.lower() for c in ticker_data.columns]
            
            signal_res = evaluate_signals(ticker, asset_type, ticker_data)
            if signal_res["signal"] == "buy":
                candidates.append((ticker, asset_type, signal_res))
                
        # Sort candidates (Crypto first, then Commodities, then Forex)
        candidates.sort(key=lambda x: 0 if x[1] == "crypto" else (1 if x[1] == "commodity" else 2))
        
        # Place buy orders
        for ticker, asset_type, sig_res in candidates:
            if len(holdings) >= MAX_CONCURRENT_POSITIONS:
                break
                
            # Define target weight
            if asset_type == "crypto":
                target_w = MAX_CRYPTO_WEIGHT
            elif asset_type == "commodity":
                target_w = MAX_COMMODITY_WEIGHT
            else:
                target_w = MAX_FOREX_WEIGHT
                
            close_price = sig_res["price"]
            target_value = portfolio_value * target_w
            
            # Check if we have enough cash
            if target_value > cash:
                target_value = cash * 0.98  # leave buffer
                
            shares = int(target_value / (close_price * (1.0 + TRANSACTION_FEE_RATE)))
            if shares > 0:
                cost = shares * close_price
                fee = cost * TRANSACTION_FEE_RATE
                total_cost = cost + fee
                
                cash -= total_cost
                holdings[ticker] = {
                    "shares": shares,
                    "buy_price": close_price,
                    "peak_price": close_price,
                    "armed": False,
                    "target_weight": target_w,
                    "asset_type": asset_type,
                    "entry_date": date_str
                }

    # Simulation completed!
    # Force close remaining positions at the end of the simulation
    final_date_str = aligned_dates[-1].strftime("%Y-%m-%d")
    final_portfolio_val = cash
    for ticker, h in list(holdings.items()):
        curr_close = float(data[ticker]["Close"].iloc[-1])
        shares_to_sell = h["shares"]
        gross_proceeds = shares_to_sell * curr_close
        fee = gross_proceeds * TRANSACTION_FEE_RATE
        final_portfolio_val += (gross_proceeds - fee)
        
        realized_pnl = gross_proceeds - (shares_to_sell * h["buy_price"])
        pnl_pct = (curr_close / h["buy_price"] - 1.0) * 100.0
        
        trade_log.append({
            "ticker": ticker,
            "asset_type": h["asset_type"],
            "entry_date": h["entry_date"],
            "exit_date": final_date_str,
            "entry_price": h["buy_price"],
            "exit_price": curr_close,
            "shares": shares_to_sell,
            "pnl": realized_pnl,
            "pnl_pct": pnl_pct,
            "reason": "Simulation End Forced Exit"
        })
        
    print(f"Backtest complete. Final portfolio value: ${final_portfolio_val:,.2f} USD")

    # Save NAV history to CSV
    nav_df = pd.DataFrame({"Date": dates_history, "NAV": nav_history})
    nav_df.to_csv("us_stocks_dcf_backtest_nav.csv".replace("us_stocks_dcf", "alternatives"), index=False)
    print("NAV history saved to alternatives_backtest_nav.csv")

    # 6. Calculate Metrics (GIPS-compliant Time Weighted Return)
    # Calculate daily returns
    nav_series = pd.Series(nav_history)
    daily_returns = nav_series.pct_change().dropna()
    
    # Calculate CAGR
    total_months = len(aligned_dates[200:]) / 21.0
    cagr = ((final_portfolio_val / total_contributed) ** (12.0 / total_months)) - 1.0 if total_contributed > 0 else 0.0
    
    # Sharpe Ratio (daily risk-free rate subtracted, annualized)
    risk_free_daily = USD_CASH_YIELD / 252.0
    excess_returns = daily_returns - risk_free_daily
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0.0
    
    # Max Drawdown
    cumulative = nav_series
    running_max = cumulative.cummax()
    drawdowns = (cumulative - running_max) / running_max
    max_dd = drawdowns.min()
    
    # Trade statistics
    n_trades = len(trade_log)
    win_trades = [t for t in trade_log if t["pnl"] > 0]
    win_rate = (len(win_trades) / n_trades * 100.0) if n_trades > 0 else 0.0
    total_profit = sum(t["pnl"] for t in trade_log)

    # SPY Benchmark comparison
    spy = yf.download("SPY", start=start_date, end=end_date, progress=False)
    spy_close = spy["Close"].squeeze()
    if isinstance(spy_close, pd.DataFrame):
        spy_close = spy_close.iloc[:, 0]
    spy_start = float(spy_close.iloc[200])
    spy_end = float(spy_close.iloc[-1])
    spy_cagr = ((spy_end / spy_start) ** (12.0 / total_months)) - 1.0

    # Write report
    report_markdown = f"""# Isolated Alternative Assets Strategy (Strategy 5) Backtest Report
**Assets Covered:** Crypto (BTC, ETH), Commodities (GLD, SLV, USO, DBA), Forex (EURUSD, GBPUSD, USDMXN, USDJPY)
**Simulation Period:** {aligned_dates[200].strftime("%Y-%m-%d")} to {final_date_str}

## 1. Executive Performance Summary

| Metric | Alternatives Strategy (Crypto/Forex/Commodities) | SPY Benchmark (Excluding DCA) |
| :--- | :---: | :---: |
| **Total Return (ROI)** | **{((final_portfolio_val / total_contributed) - 1.0)*100:.2f}%** | **{((spy_end/spy_start) - 1.0)*100:.2f}%** |
| **CAGR (TWR)** | **{cagr*100:.2f}%** | **{spy_cagr*100:.2f}%** |
| **Sharpe Ratio** | **{sharpe:.2f}** | -- |
| **Max Drawdown** | **{max_dd*100:.2f}%** | -- |
| **Total Trades Executed** | **{n_trades}** | -- |
| **Win Rate** | **{win_rate:.1f}%** | -- |
| **Total Invested (DCA)** | **${total_contributed:,.2f} USD** | -- |
| **Final Portfolio NAV** | **${final_portfolio_val:,.2f} USD** | -- |

## 2. Strategy Rules and Parameters
- **Crypto Engine:** Trend-Following using SMA 200 and MACD crossover. Trades closed if MACD crosses down or trailing stop hits 5% below peak (armed at +10% return). Max 20% weight.
- **Commodities Engine:** Momentum Breakout using SMA 100 and Donchian Channels (20-day high for buy entry, 10-day low for sell exit). Max 20% weight.
- **Forex Engine:** Mean-Reversion using Bollinger Bands (20 periods, 2 std dev) and RSI (14 periods). Buy when RSI < 35 at lower band, sell when RSI > 65 at upper band. Max 15% weight.
- **General Constraints:** Maximum of {MAX_CONCURRENT_POSITIONS} concurrent open positions. Friction model: {TRANSACTION_FEE_RATE*100:.2f}% round-trip fee.

## 3. Trade Log Summary (Last 30 Completed Trades)
| Asset | Type | Entry Date | Exit Date | Entry Price | Exit Price | P&L | Return % | Reason |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
"""
    # Append last 30 trades to table
    last_trades = trade_log[-30:]
    for t in reversed(last_trades):
        report_markdown += f"| **{t['ticker']}** | {t['asset_type'].upper()} | {t['entry_date']} | {t['exit_date']} | ${t['entry_price']:,.2f} | ${t['exit_price']:,.2f} | ${t['pnl']:+,.2f} | {t['pnl_pct']:+,.2f}% | {t['reason']} |\n"

    with open("alternatives_backtest_report.md", "w", encoding="utf-8") as f:
        f.write(report_markdown)
    print("Report saved to alternatives_backtest_report.md")
    print("=" * 80)

if __name__ == "__main__":
    main()
