"""
Strategy 27 LIVE Runner: Golden Hurst Exponent Regime System
===========================================================
Runs daily to switch regimes between TQQQ, SQQQ, and Cash based on 55d Hurst.
"""
import os
import sys
import json
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

PORTFOLIO_FILE = "portfolio_strategy27.json"
TRANSACTIONS_FILE = "transactions_strategy27.md"
REPORT_FILE = "strategy27_report_live.md"

TRADING_DAYS = 252
TRANSACTION_COST = 0.0029
BONDIA_YIELD = 0.0653

def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if not os.path.exists(p_path):
        return {"total_capital": 200000.0, "cash_balance": 200000.0, "holdings": [],
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    with open(p_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_portfolio(dir_path, portfolio):
    portfolio["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(dir_path, PORTFOLIO_FILE), "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(t_path):
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("# Strategy 27 Transaction Ledger (Golden Hurst)\n\n"
                    "| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n"
                    "| :--- | :--- | :--- | ---: | ---: | ---: | :--- | :--- | :--- |\n---\n")
    with open(t_path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    gross = shares * price
    impact = f"-{gross + fee:,.2f}" if action in ["BUY", "DEPOSIT"] else f"+{gross - fee:,.2f}" if action != "INTEREST" else f"+{gross:,.2f}"
    row = f"| {date_str} | {ticker} | {action} | {shares:.4f} | ${price:.4f} | ${impact} | Market | FILLED | {note} |"
    idx = next((i for i, l in enumerate(lines) if l.strip() == "---"), None)
    lines.insert(idx, row) if idx is not None else lines.append(row)
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def calculate_hurst_exponent(log_prices, window_size=55, max_lag=20):
    sub_series = log_prices[-window_size:]
    lags = np.arange(2, max_lag)
    log_lags = np.log(lags)
    log_lags_mean = np.mean(log_lags)
    log_lags_variance = np.sum((log_lags - log_lags_mean) ** 2)
    
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
        return 0.5
    log_stds = np.array(log_stds)
    covariance = np.sum((log_lags - log_lags_mean) * (log_stds - np.mean(log_stds)))
    slope = covariance / log_lags_variance
    return np.clip(slope, 0.0, 1.0)

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().isoformat()
    now_local = datetime.datetime.now()
    
    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 27 GOLDEN HURST ({today_str})")
    print("=" * 80)
    
    portfolio = load_portfolio(dir_path)
    cash = portfolio["cash_balance"]
    
    # Calculate sweep interest
    last_str = portfolio.get("last_updated", today_str + " 00:00:00")
    fmt = "%Y-%m-%d %H:%M:%S" if " " in last_str else "%Y-%m-%d"
    last_dt = datetime.datetime.strptime(last_str, fmt)
    days = max((now_local - last_dt).total_seconds() / 86400.0, 0.0)
    
    if days > 0:
        interest = cash * (BONDIA_YIELD / 365.25) * days
        cash = round(cash + interest, 2)
        portfolio["cash_balance"] = cash
        log_transaction(dir_path, today_str, "BONDIA", "INTEREST", 1, interest, "Sweep interest", 0.0)
        print(f"[Sweep] +${interest:,.4f} MXN")
        
    print("Downloading recent index prices...")
    try:
        qqq_hist = yf.Ticker("QQQ").history(period="100d").dropna(subset=["Close"])
        tqqq_hist = yf.Ticker("TQQQ").history(period="5d").dropna(subset=["Close"])
        sqqq_hist = yf.Ticker("SQQQ").history(period="5d").dropna(subset=["Close"])
        fx_now = yf.Ticker("MXN=X").history(period="1d").dropna(subset=["Close"])
        if qqq_hist.empty or tqqq_hist.empty or sqqq_hist.empty or fx_now.empty:
            print("CRITICAL: price feed empty. Exit.")
            save_portfolio(dir_path, portfolio)
            return
    except Exception as e:
        print(f"CRITICAL: price download failed ({e}). Exit.")
        save_portfolio(dir_path, portfolio)
        return
        
    fx_rate = float(fx_now["Close"].iloc[-1])
    tqqq_close = float(tqqq_hist["Close"].iloc[-1]) * fx_rate
    sqqq_close = float(sqqq_hist["Close"].iloc[-1]) * fx_rate
    
    log_prices = np.log(qqq_hist["Close"].values)
    hurst_val = calculate_hurst_exponent(log_prices, window_size=55)
    
    # 21 vs 55 EMA Trend Filters
    ma_fast = qqq_hist["Close"].ewm(span=21, adjust=False).mean().values[-1]
    ma_slow = qqq_hist["Close"].ewm(span=55, adjust=False).mean().values[-1]
    
    # Determine target regime
    target_regime = 0 # 0=Cash, 1=TQQQ, 2=SQQQ
    regime_note = "Chop/Mean Reverting"
    if hurst_val > 0.52:
        if ma_fast > ma_slow:
            target_regime = 1
            regime_note = "Persistent Bull Trend"
        else:
            target_regime = 2
            regime_note = "Persistent Bear Trend"
            
    print(f"Current Metrics: Hurst={hurst_val:.4f}, Fast EMA={ma_fast:.2f}, Slow EMA={ma_slow:.2f} ({regime_note})")
    
    active_holdings = {h["ticker"]: h for h in portfolio.get("holdings", [])}
    new_holdings = []
    
    # Check if we need to exit previous holdings
    current_asset = list(active_holdings.keys())[0] if active_holdings else None
    
    # Determine what to trade
    target_ticker = "TQQQ" if target_regime == 1 else "SQQQ" if target_regime == 2 else None
    
    if current_asset and current_asset != target_ticker:
        # Sell current position
        h = active_holdings[current_asset]
        price = tqqq_close if current_asset == "TQQQ" else sqqq_close
        val = h["shares"] * price
        fee = val * TRANSACTION_COST
        cash = round(cash + (val - fee), 2)
        log_transaction(dir_path, today_str, current_asset, "SELL", h["shares"], price, "Regime pivot liquidation", fee)
        print(f"[Exit] Sold {h['shares']:.4f} shares of {current_asset} @ ${price:.2f} MXN")
        current_asset = None
        
    if target_ticker and not current_asset:
        # Buy target asset
        price = tqqq_close if target_ticker == "TQQQ" else sqqq_close
        usable_cash = cash
        fee = usable_cash * TRANSACTION_COST
        shares = (usable_cash - fee) / price
        cash = 0.0
        log_transaction(dir_path, today_str, target_ticker, "BUY", shares, price, "Regime pivot entry", fee)
        new_holdings.append({
            "ticker": target_ticker,
            "shares": shares,
            "buy_price": price,
            "last_price": price
        })
        print(f"[Entry] Bought {shares:.4f} shares of {target_ticker} @ ${price:.2f} MXN")
    elif current_asset:
        # Carry forward active holding
        h = active_holdings[current_asset]
        price = tqqq_close if current_asset == "TQQQ" else sqqq_close
        h["last_price"] = price
        new_holdings.append(h)
        
    portfolio["cash_balance"] = cash
    portfolio["holdings"] = new_holdings
    
    total_val = cash
    for h in new_holdings:
        total_val += h["shares"] * h["last_price"]
        
    portfolio["total_capital"] = total_val
    portfolio["total_portfolio_value_mxn"] = total_val
    
    save_portfolio(dir_path, portfolio)
    
    # Generate live report
    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(f"# Strategy 27 Live Status Report\n\n")
        f.write(f"**Last Run:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Current Regime:** {regime_note} (Hurst: {hurst_val:.4f})\n")
        f.write(f"**Total Capital:** ${total_val:,.2f} MXN\n")
        f.write(f"**Cash Balance:** ${cash:,.2f} MXN\n\n")
        f.write(f"## Current Holdings\n\n")
        if new_holdings:
            f.write(f"| Ticker | Shares | Buy Price | Current Price | Return |\n")
            f.write(f"| :--- | ---: | ---: | ---: | ---: |\n")
            for h in new_holdings:
                ret = (h['last_price'] / h['buy_price'] - 1.0) * 100
                f.write(f"| {h['ticker']} | {h['shares']:.4f} | ${h['buy_price']:.2f} | ${h['last_price']:.2f} | {ret:+.2f}% |\n")
        else:
            f.write(f"No active leveraged ETF positions. 100% Cash sweep.\n")
            
    print(f"Strategy 27 Live Update Completed. Portfolio NAV: ${total_val:,.2f} MXN")

if __name__ == "__main__":
    main()
