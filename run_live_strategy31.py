import os
import json
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.signal import savgol_coeffs

PORTFOLIO_FILE = "portfolio_strategy31.json"
LEDGER_FILE = "transactions_strategy31.md"
REPORT_FILE = "strategy31_report_live.md"
INITIAL_CAPITAL = 200000.0  # MXN
TRANSACTION_COST = 0.0029

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "strategy_name": "S31 Fibonacci S&R Reversal",
        "total_capital": INITIAL_CAPITAL,
        "cash_balance": INITIAL_CAPITAL,
        "holdings": [],
        "last_updated": datetime.date.today().strftime("%Y-%m-%d")
    }

def save_portfolio(p):
    p["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(p, f, indent=4)

def calculate_savgol_rolling(prices, window_length=13, polyorder=3):
    n = len(prices)
    smooth = np.full(n, np.nan)
    deriv1 = np.full(n, np.nan)
    deriv2 = np.full(n, np.nan)
    
    coeffs0 = savgol_coeffs(window_length, polyorder, deriv=0, pos=0)
    coeffs1 = -savgol_coeffs(window_length, polyorder, deriv=1, pos=0)
    coeffs2 = savgol_coeffs(window_length, polyorder, deriv=2, pos=0)
    
    for i in range(window_length - 1, n):
        window = prices[i - window_length + 1 : i + 1]
        smooth[i] = np.dot(coeffs0, window)
        deriv1[i] = np.dot(coeffs1, window)
        deriv2[i] = np.dot(coeffs2, window)
        
    return smooth, deriv1, deriv2

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, adjust=False).mean()
    avg_loss = loss.ewm(com=period-1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1.0 + rs.fillna(0)))
    return rsi

def check_signals():
    print("Downloading QQQ data for S31 live run...")
    df = yf.download(["QQQ", "TQQQ", "USDMXN=X"], period="1y", progress=False)
    if df.empty:
        print("Failed to download data.")
        return None
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [f"{col[0]}_{col[1]}".lower() for col in df.columns]
        
    df = df.rename(columns={
        "close_qqq": "qqq",
        "close_tqqq": "tqqq",
        "close_usdmxn=x": "fx",
        "high_qqq": "qqq_high",
        "low_qqq": "qqq_low"
    })
    
    df = df.ffill().dropna(subset=["qqq"])
    prices = df["qqq"].values
    
    # Savitzky-Golay support/resistance (13-day)
    smooth, deriv1, deriv2 = calculate_savgol_rolling(prices, 13, 3)
    
    curr_support = np.nan
    curr_resistance = np.nan
    last_sup_idx = None
    last_res_idx = None
    
    # Calculate historical pivots
    for i in range(13, len(df)):
        if deriv1[i-1] < 0 and deriv1[i] >= 0 and deriv2[i] > 0:
            curr_support = prices[i]
            last_sup_idx = i
        elif deriv1[i-1] > 0 and deriv1[i] <= 0 and deriv2[i] < 0:
            curr_resistance = prices[i]
            last_res_idx = i
            
        # Resolve inverted bounds
        if not np.isnan(curr_support) and not np.isnan(curr_resistance):
            if curr_support >= curr_resistance:
                if last_res_idx is not None and last_res_idx < i:
                    curr_support = float(np.min(prices[last_res_idx : i + 1]))
                elif last_sup_idx is not None and last_sup_idx < i:
                    curr_resistance = float(np.max(prices[last_sup_idx : i + 1]))
            
    # Macro Swing High and Low (55-day lookback)
    swing_high = df["qqq_high"].rolling(55).max().iloc[-1]
    swing_low = df["qqq_low"].rolling(55).min().iloc[-1]
    df["RSI"] = calculate_rsi(df["qqq"], 14)
    
    curr_rsi = df["RSI"].iloc[-1]
    curr_price = df["qqq"].iloc[-1]
    tqqq_price = df["tqqq"].iloc[-1]
    fx_rate = df["fx"].iloc[-1]
    
    if np.isnan(curr_support) or np.isnan(curr_resistance):
        return None
        
    # SRP
    curr_srp = (curr_price - curr_support) / (curr_resistance - curr_support) if curr_resistance > curr_support else 0.5
    
    # Fibonacci Levels
    macro_range = swing_high - swing_low
    f50 = swing_high - 0.500 * macro_range
    f618 = swing_high - 0.618 * macro_range
    f382 = swing_high - 0.382 * macro_range
    f786 = swing_high - 0.786 * macro_range
    
    fib_levels = [f382, f50, f618]
    is_support_confluence = any(abs(curr_support - f) / f < 0.015 for f in fib_levels)
    is_resistance_confluence = any(abs(curr_resistance - f) / f < 0.015 for f in fib_levels)
    
    is_buy = is_support_confluence and (curr_srp < 0.20) and (curr_rsi < 45)
    is_sell = is_resistance_confluence and (curr_srp > 0.80) and (curr_rsi > 60)
    
    return {
        "price": curr_price,
        "tqqq_price": tqqq_price,
        "fx_rate": fx_rate,
        "support": curr_support,
        "resistance": curr_resistance,
        "srp": curr_srp,
        "rsi": curr_rsi,
        "fib_50": f50,
        "fib_618": f618,
        "fib_786": f786,
        "swing_high": swing_high,
        "swing_low": swing_low,
        "is_buy": is_buy,
        "is_sell": is_sell,
        "stop_loss": f786
    }

def execute():
    p = load_portfolio()
    diagnostics = check_signals()
    if not diagnostics:
        print("Failed to run diagnostics. Exiting S31.")
        return
        
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    fx_rate = diagnostics["fx_rate"]
    tqqq_px_usd = diagnostics["tqqq_price"]
    tqqq_px_mxn = tqqq_px_usd * fx_rate
    
    cash = p["cash_balance"]
    shares = sum(h["shares"] for h in p["holdings"] if h["ticker"] == "TQQQ")
    
    action = "HOLD"
    trade_price = 0.0
    trade_shares = 0.0
    
    # Signal execution
    is_buy = diagnostics["is_buy"]
    is_sell = diagnostics["is_sell"]
    stop_loss_hit = (diagnostics["price"] < diagnostics["fib_786"]) and (shares > 0)
    
    if is_buy and shares == 0:
        # Buy TQQQ
        action = "BUY"
        trade_price = tqqq_px_mxn
        cost = cash
        fee = cost * TRANSACTION_COST
        net_buy = cost - fee
        trade_shares = net_buy / trade_price
        
        p["holdings"].append({
            "ticker": "TQQQ",
            "shares": trade_shares,
            "buy_price": trade_price,
            "last_price": trade_price,
            "ccy": "MXN"
        })
        p["cash_balance"] = 0.0
        p["total_capital"] = net_buy
        
    elif (is_sell or stop_loss_hit) and shares > 0:
        # Sell TQQQ to cash
        action = "SELL" if is_sell else "STOP_OUT"
        trade_price = tqqq_px_mxn
        trade_shares = shares
        gross = shares * trade_price
        fee = gross * TRANSACTION_COST
        cash = gross - fee
        
        p["holdings"] = [h for h in p["holdings"] if h["ticker"] != "TQQQ"]
        p["cash_balance"] = cash
        p["total_capital"] = cash
        
    # Re-calculate total portfolio NAV in MXN
    shares_held = sum(h["shares"] for h in p["holdings"] if h["ticker"] == "TQQQ")
    portfolio_value = p["cash_balance"] + (shares_held * tqqq_px_mxn)
    p["total_capital"] = portfolio_value
    
    # Save ledger entries
    if action in ["BUY", "SELL", "STOP_OUT"]:
        if not os.path.exists(LEDGER_FILE):
            with open(LEDGER_FILE, "w", encoding="utf-8") as f:
                f.write("# S31 Reversal Transaction Ledger\n\n| Date | Ticker | Action | Shares | Price (MXN) | Value (MXN) | Note |\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        
        with open(LEDGER_FILE, "a", encoding="utf-8") as f:
            val = trade_shares * trade_price
            f.write(f"| {today_str} | TQQQ | {action} | {trade_shares:.4f} | ${trade_price:,.2f} | ${val:,.2f} | Live Reversal Signal |\n")
            
    save_portfolio(p)
    
    # Save live report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"""# Strategy 31: Fibonacci S&R Reversal Execution Report
**Execution Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} MXN (approx. ${portfolio_value/fx_rate:,.2f} USD)
* **Total Cash Balance:** ${p['cash_balance']:,.2f} MXN
* **TQQQ Exposure:** {((shares_held * tqqq_px_mxn)/portfolio_value*100.0) if portfolio_value > 0 else 0.0:.1f}%

## 2. Technical Diagnostics
* **QQQ Close Price:** ${diagnostics['price']:.2f} USD
* **14-Day RSI:** {diagnostics['rsi']:.1f}
* **Savitzky-Golay Support:** ${diagnostics['support']:.2f} USD
* **Savitzky-Golay Resistance:** ${diagnostics['resistance']:.2f} USD
* **Support-Resistance Position (SRP):** {diagnostics['srp']:.2f}
* **Macro Swing High (55d):** ${diagnostics['swing_high']:.2f} USD
* **Macro Swing Low (55d):** ${diagnostics['swing_low']:.2f} USD
* **Confluence Support Levels:** 38.2% (${diagnostics['fib_50']:.2f}), 50.0% (${diagnostics['fib_50']:.2f}), 61.8% (${diagnostics['fib_618']:.2f})
* **Stop Loss Level (78.6%):** ${diagnostics['fib_786']:.2f} USD

## 3. Execution Action Taken
* **Action:** {action}
""")

if __name__ == "__main__":
    execute()
