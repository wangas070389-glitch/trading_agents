"""
LIVE EXECUTION: STRATEGY 23 CALCULUS S&R & RSI SYSTEMATIC
=========================================================
Runs daily to calculate rolling Savitzky-Golay derivatives and RSI on yfinance QQQ data,
generates support/resistance levels and momentum signals, and rebalances between TQQQ, SQQQ, and Cash.
"""
import os
import sys
import json
import argparse
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.signal import savgol_coeffs

# Local settings
PORTFOLIO_FILE = "portfolio_strategy23.json"
TRANSACTIONS_FILE = "transactions_strategy23.md"
REPORT_FILE = "strategy23_report_live.md"
PARAMS_FILE = "learned_params_s23.json"

TRANSACTION_COST = 0.0029  # 0.29% GBM broker fee (spread + commission + VAT)
BONDIA_YIELD = 0.0653      # 6.53% MXN cash sweep compound yield

def calculate_savgol_rolling(prices, window_length=31, polyorder=3):
    n = len(prices)
    smooth = np.full(n, np.nan)
    deriv1 = np.full(n, np.nan)
    deriv2 = np.full(n, np.nan)
    
    # We use pos=0 and sign correction to evaluate at the end of the window (causal)
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
    rs = rs.fillna(0)
    rsi = 100 - (100 / (1.0 + rs))
    return rsi

def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if os.path.exists(p_path):
        with open(p_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {
            "total_capital": 200000.0,
            "cash_balance": 200000.0,
            "holdings": [],
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_rebalance_date": datetime.date.today().isoformat()
        }

def save_portfolio(dir_path, portfolio):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    with open(p_path, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    gross = shares * price
    if action in ["BUY", "DEPOSIT"]:
        cash_flow_str = f"-{gross + fee:,.2f}"
    elif action in ["INTEREST", "DIVIDEND"]:
        cash_flow_str = f"+{gross:,.2f}"
    else:
        cash_flow_str = f"+{gross - fee:,.2f}"
        
    row = f"| {date_str} | {ticker} | {action} | {shares:.4f} | ${price:.2f} | ${cash_flow_str} | Market | FILLED | {note} |"
    
    if os.path.exists(t_path):
        with open(t_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = f"# Strategy 23: Calculus S&R & RSI Transaction Ledger\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"
        
    lines = content.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            insert_idx = i
            break
            
    if insert_idx is not None:
        lines.insert(insert_idx, row)
    else:
        lines.append(row)
        
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Calculate state and positions without modifying portfolio state files.")
    parser.add_argument("--force-rebalance", action="store_true", help="Force re-evaluation of target positions.")
    args = parser.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 23 CALCULUS S&R & RSI ({today_str})")
    print("=" * 80)

    # 1. Load portfolio state
    portfolio = load_portfolio(dir_path)
    current_cash = portfolio["cash_balance"]
    last_updated_str = portfolio.get("last_updated", today_str + " 00:00:00")
    
    if " " in last_updated_str:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
    else:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d")

    # 2. Accrue Bondia cash sweep yield
    time_diff = now - last_dt
    days_elapsed = time_diff.total_seconds() / 86400.0
    accrued_interest = 0.0
    if days_elapsed > 0.001 and current_cash > 0:
        daily_rate = BONDIA_YIELD / 365.25
        accrued_interest = current_cash * daily_rate * days_elapsed
        current_cash = round(current_cash + accrued_interest, 2)
        portfolio["cash_balance"] = current_cash
        portfolio["total_capital"] += accrued_interest
        if not args.dry_run:
            log_transaction(dir_path, today_str, "BONDIA", "INTEREST", 1, accrued_interest, f"Yield on cash for {days_elapsed:.4f} days.")
        print(f"  +-- [BONDIA YIELD] Compound interest: +${accrued_interest:,.2f} MXN accrued over {days_elapsed:.4f} days.")

    # 3. Load learned parameters
    params_path = os.path.join(dir_path, PARAMS_FILE)
    if os.path.exists(params_path):
        with open(params_path, "r", encoding="utf-8") as f:
            params = json.load(f)
        print(f"Loaded parameters from {PARAMS_FILE}")
    else:
        # Default backtest parameters
        params = {
            "window_length": 31,
            "polyorder": 3,
            "rsi_period": 14,
            "srp_buy": 0.20,
            "srp_sell": 0.70,
            "rsi_buy": 45,
            "rsi_sell": 65,
            "rsi_breakout_up": 55,
            "rsi_breakout_down": 45
        }
        print("Using default parameters")

    # 4. Fetch FX rate and prices
    print("\nFetching market prices and exchange rates...")
    try:
        usdmxn_ticker = yf.Ticker("MXN=X")
        fx_hist = usdmxn_ticker.history(period="5d")
        fx_rate = float(fx_hist["Close"].iloc[-1]) if not fx_hist.empty else 17.5
        print(f"USD/MXN Rate: {fx_rate:.4f}")
    except Exception as e:
        print(f"Error fetching FX rate: {e}. Defaulting to 17.5")
        fx_rate = 17.5

    tickers = ["QQQ", "TQQQ", "SQQQ"]
    current_prices = {}
    for tk in tickers:
        try:
            ticker_obj = yf.Ticker(tk)
            hist = ticker_obj.history(period="5d")
            if not hist.empty:
                current_prices[tk] = float(hist["Close"].iloc[-1])
            else:
                current_prices[tk] = 100.0
        except Exception as e:
            print(f"Error fetching price for {tk}: {e}")
            current_prices[tk] = 100.0

    # 5. Value existing holdings
    holdings_val_mxn = 0.0
    current_asset_name = "CASH"
    held_shares = 0.0
    held_ticker = None
    
    for h in portfolio.get("holdings", []):
        held_ticker = h["ticker"]
        held_shares = h["shares"]
        current_asset_name = held_ticker
        px_usd = current_prices.get(held_ticker, h["last_price"] / fx_rate if fx_rate > 0 else h["last_price"])
        h["last_price"] = px_usd * fx_rate
        holdings_val_mxn = held_shares * h["last_price"]
        # Track trailing stop peak price
        if "peak_price" not in h:
            h["peak_price"] = h["buy_price"]
        h["peak_price"] = max(h["peak_price"], h["last_price"])
        
    portfolio_value = current_cash + holdings_val_mxn
    print(f"Current Portfolio Value: ${portfolio_value:,.2f} MXN (Cash: ${current_cash:,.2f} MXN, Holdings: ${holdings_val_mxn:,.2f} MXN)")

    # 6. Fetch QQQ history and run indicators
    print("\nLoading trailing QQQ daily close series for signal generation...")
    try:
        wl = params["window_length"]
        # Fetch slightly more history than window_length to ensure stable indicators
        lookback_period = f"{wl * 3}d"
        qqq_history = yf.download("QQQ", period=lookback_period, progress=False)
        if isinstance(qqq_history.columns, pd.MultiIndex):
            qqq_history.columns = [c[0] for c in qqq_history.columns]
        
        qqq_closes = qqq_history["Close"].dropna()
        n_days = len(qqq_closes)
        
        if n_days < wl:
            raise ValueError(f"Insufficient QQQ history (fetched {n_days} days, required {wl})")
            
        prices = qqq_closes.values
        
        # Calculate rolling Savitzky-Golay smoothed prices and derivatives
        smooth, deriv1, deriv2 = calculate_savgol_rolling(prices, wl, params["polyorder"])
        
        # Calculate RSI
        rsi = calculate_rsi(qqq_closes, params["rsi_period"]).values
        
        # Find support and resistance levels historically over this trailing window
        support_levels = np.full(n_days, np.nan)
        resistance_levels = np.full(n_days, np.nan)
        
        curr_support = np.nan
        curr_resistance = np.nan
        
        for i in range(wl, n_days):
            if deriv1[i-1] < 0 and deriv1[i] >= 0 and deriv2[i] > 0:
                curr_support = prices[i]
            elif deriv1[i-1] > 0 and deriv1[i] <= 0 and deriv2[i] < 0:
                curr_resistance = prices[i]
                
            support_levels[i] = curr_support
            resistance_levels[i] = curr_resistance
            
        # Support-Resistance Position (SRP)
        srp = np.full(n_days, 0.5)
        for i in range(n_days):
            sup = support_levels[i]
            res = resistance_levels[i]
            if not np.isnan(sup) and not np.isnan(res) and res > sup:
                srp[i] = (prices[i] - sup) / (res - sup)
                
        # Last index values
        last_smooth = smooth[-1]
        last_deriv1 = deriv1[-1]
        last_deriv2 = deriv2[-1]
        last_rsi = rsi[-1]
        last_srp = srp[-1]
        last_support = support_levels[-1]
        last_resistance = resistance_levels[-1]
        last_price = prices[-1]
        
        print("\nTrailing Signal State:")
        print(f"  * QQQ Price          : ${last_price:.2f} USD")
        print(f"  * Smooth Close       : ${last_smooth:.2f} USD")
        print(f"  * 1st Derivative     : {last_deriv1:.6f}")
        print(f"  * 2nd Derivative     : {last_deriv2:.6f}")
        print(f"  * Support Level (S)  : ${last_support:.2f} USD")
        print(f"  * Resistance Level(R): ${last_resistance:.2f} USD")
        print(f"  * SRP Index          : {last_srp:.4f} (0=S, 1=R)")
        print(f"  * RSI (14-period)    : {last_rsi:.2f}")
        
        # Decide Target Position
        target_asset = current_asset_name
        signal_reason = "No trade condition triggered. Holding current asset."
        
        if not np.isnan(last_support) and not np.isnan(last_resistance):
            is_reversion_buy = (last_srp < params["srp_buy"]) and (last_rsi < params["rsi_buy"])
            is_breakout_buy = (last_srp > 1.0) and (last_rsi > params["rsi_breakout_up"])
            
            is_reversion_sell = (last_srp > params["srp_sell"]) and (last_rsi > params["rsi_sell"])
            is_breakdown_sell = (last_srp < 0.0) and (last_rsi < params["rsi_breakout_down"])
            
            if is_reversion_buy or is_breakout_buy:
                target_asset = "TQQQ"
                signal_reason = f"Bullish signal triggered: " + (f"Reversion Buy (SRP={last_srp:.2f} < {params['srp_buy']:.2f}, RSI={last_rsi:.1f})" if is_reversion_buy else f"Breakout Buy (SRP={last_srp:.2f} > 1.0, RSI={last_rsi:.1f})")
            elif is_reversion_sell or is_breakdown_sell:
                target_asset = "SQQQ"
                signal_reason = f"Bearish signal triggered: " + (f"Reversion Sell (SRP={last_srp:.2f} > {params['srp_sell']:.2f}, RSI={last_rsi:.1f})" if is_reversion_sell else f"Breakdown Sell (SRP={last_srp:.2f} < 0.0, RSI={last_rsi:.1f})")
            else:
                # Mean reversion exits
                if current_asset_name == "TQQQ" and (last_srp > 0.85 or last_rsi > 70):
                    target_asset = "CASH"
                    signal_reason = f"Exited TQQQ: Reached resistance (SRP={last_srp:.2f} > 0.85 or RSI={last_rsi:.1f} > 70)"
                elif current_asset_name == "SQQQ" and (last_srp < 0.15 or last_rsi < 30):
                    target_asset = "CASH"
                    signal_reason = f"Exited SQQQ: Reached support (SRP={last_srp:.2f} < 0.15 or RSI={last_rsi:.1f} < 30)"
        else:
            target_asset = "CASH"
            signal_reason = "Dynamic levels not yet formed. Staying in Cash."
            
        # Check trailing stop-loss
        ts_pct = params.get("trailing_stop_pct", None)
        if current_asset_name != "CASH" and ts_pct is not None and len(portfolio.get("holdings", [])) > 0:
            active_h = portfolio["holdings"][0]
            last_px = active_h["last_price"]
            peak_px = active_h.get("peak_price", active_h["buy_price"])
            if last_px < peak_px * (1.0 - ts_pct):
                target_asset = "CASH"
                signal_reason = f"Trailing Stop-Loss Triggered: Price (${last_px:,.2f} MXN) fell below stop price (${peak_px * (1.0 - ts_pct):,.2f} MXN) derived from peak price (${peak_px:,.2f} MXN)."
            
        print(f"Target Allocation    : {target_asset} ({signal_reason})")
        
    except Exception as e:
        print(f"Error calculating calculus and RSI signals: {e}")
        target_asset = current_asset_name
        signal_reason = f"Error during signal calculation: {e}. Holding current asset."
        last_price = last_support = last_resistance = last_srp = last_rsi = np.nan

    # 7. Execute Rebalance
    rebalanced = False
    action_note = ""
    
    if target_asset != current_asset_name or args.force_rebalance:
        rebalanced = True
        print(f"\nExecution Action: Rotating {current_asset_name} -> {target_asset}")
        
        # Phase A: Liquidation
        if current_asset_name != "CASH":
            sell_price_usd = current_prices[current_asset_name]
            sell_price_mxn = sell_price_usd * fx_rate
            fee = holdings_val_mxn * TRANSACTION_COST
            net_proceeds = holdings_val_mxn - fee
            current_cash = round(current_cash + net_proceeds, 2)
            
            action_note = f"Sold all {held_shares:.4f} shares of {current_asset_name} at ${sell_price_mxn:,.2f} MXN (Fee: ${fee:,.2f} MXN)."
            if not args.dry_run:
                log_transaction(dir_path, today_str, current_asset_name, "SELL", held_shares, sell_price_mxn, action_note, fee)
            print(f"  [LIQUIDATE] {action_note}")
            portfolio["holdings"] = []
            holdings_val_mxn = 0.0
            
        # Phase B: Purchase
        if target_asset != "CASH":
            buy_price_usd = current_prices[target_asset]
            buy_price_mxn = buy_price_usd * fx_rate
            
            # Substract fee from buying power
            buy_cash = current_cash / (1.0 + TRANSACTION_COST)
            fee = buy_cash * TRANSACTION_COST
            shares_to_buy = buy_cash / buy_price_mxn
            
            current_cash = round(current_cash - (buy_cash + fee), 2)
            holdings_val_mxn = buy_cash
            
            portfolio["holdings"] = [{
                "ticker": target_asset,
                "shares": shares_to_buy,
                "buy_price": buy_price_mxn,
                "last_price": buy_price_mxn,
                "peak_price": buy_price_mxn
            }]
            
            action_note = f"Purchased {shares_to_buy:.4f} shares of {target_asset} at ${buy_price_mxn:,.2f} MXN (Fee: ${fee:,.2f} MXN)."
            if not args.dry_run:
                log_transaction(dir_path, today_str, target_asset, "BUY", shares_to_buy, buy_price_mxn, action_note, fee)
            print(f"  [ALLOCATE] {action_note}")
            
        portfolio["cash_balance"] = current_cash
        portfolio["last_rebalance_date"] = today_str
        
    else:
        print(f"\nNo Rebalance Required. Maintaining allocation: {current_asset_name}")
        action_note = signal_reason

    portfolio["total_portfolio_value_mxn"] = round(current_cash + holdings_val_mxn, 2)
    portfolio["last_updated"] = now_str

    # Save state
    if not args.dry_run:
        save_portfolio(dir_path, portfolio)
        print("Portfolio state successfully saved.")

    # 8. Write Live Report
    report_md = f"""# Strategy 23: Calculus S&R & RSI Live Report
**Report Generated:** {now_str}

## Current Status
* **Total Portfolio Value:** ${portfolio["total_portfolio_value_mxn"]:,.2f} MXN
* **Cash Balance:** ${portfolio["cash_balance"]:,.2f} MXN
* **Holding Asset:** {target_asset}

## Signals & Levels Details
* **QQQ Close Price:** ${last_price:.2f} USD
* **Support Level (S):** ${last_support:.2f} USD
* **Resistance Level (R):** ${last_resistance:.2f} USD
* **SRP Index (0=S, 1=R):** {last_srp:.4f}
* **RSI (14-period):** {last_rsi:.2f}

## Execution Log
* **Action:** {action_note}
* **Last Rebalance Date:** {portfolio["last_rebalance_date"]}
"""
    
    if not args.dry_run:
        with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"Live report saved to: {REPORT_FILE}")

if __name__ == "__main__":
    main()
