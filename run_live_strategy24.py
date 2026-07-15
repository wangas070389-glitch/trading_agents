"""
LIVE EXECUTION: STRATEGY 24 30-MINUTE RANDOM FOREST CLASSIFIER
=============================================================
Runs every 30 minutes to download trailing QQQ data, train a rolling Random Forest Classifier,
predict the current market regime, and rebalance between TQQQ, SQQQ, and MXN Cash.
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
from sklearn.ensemble import RandomForestClassifier

# Local settings
PORTFOLIO_FILE = "portfolio_strategy24.json"
TRANSACTIONS_FILE = "transactions_strategy24.md"
REPORT_FILE = "strategy24_report_live.md"
PARAMS_FILE = "learned_params_s24.json"

TRANSACTION_COST = 0.0029  # 0.29% GBM broker fee (spread + commission + VAT)
BONDIA_YIELD = 0.0653      # 6.53% MXN cash sweep compound yield
TRADING_BARS_PER_DAY = 13  # 30-minute bars per trading day

def calculate_savgol_rolling(prices, window_length=31, polyorder=3):
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
        content = f"# Strategy 24: 30-Minute Random Forest Transaction Ledger\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"
        
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
    print(f"LIVE EXECUTION: STRATEGY 24 30-MINUTE RANDOM FOREST ({today_str})")
    print("=" * 80)

    # 1. Load portfolio state
    portfolio = load_portfolio(dir_path)
    current_cash = portfolio["cash_balance"]
    last_updated_str = portfolio.get("last_updated", today_str + " 00:00:00")
    
    if " " in last_updated_str:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
    else:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d")

    # 2. Accrue Bondia cash sweep yield (per 30m bar equivalent)
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
        print(f"Loaded optimal parameters from {PARAMS_FILE}")
    else:
        params = {
            "n_estimators": 30,
            "max_depth": 3,
            "thresh": 0.40
        }
        print("Using default parameters")

    # 4. Fetch FX rate and current prices
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
        # Track holding duration and trailing stop peak price
        if "bars_held" not in h:
            h["bars_held"] = 0
        if "peak_price" not in h:
            h["peak_price"] = h["buy_price"]
        h["bars_held"] += 1
        h["peak_price"] = max(h["peak_price"], h["last_price"])
        
    portfolio_value = current_cash + holdings_val_mxn
    print(f"Current Portfolio Value: ${portfolio_value:,.2f} MXN (Cash: ${current_cash:,.2f} MXN, Holdings: ${holdings_val_mxn:,.2f} MXN)")

    # 6. Fetch 30-minute bars and execute model
    print("\nLoading trailing QQQ 30-minute bars to train model...")
    try:
        # Load QQQ 30-minute bars (max 60 days)
        qqq_history = yf.download("QQQ", period="60d", interval="30m", progress=False)
        if isinstance(qqq_history.columns, pd.MultiIndex):
            qqq_history.columns = [c[0] for c in qqq_history.columns]
            
        qqq_closes = qqq_history["Close"].dropna()
        n_bars = len(qqq_closes)
        
        if n_bars < 100:
            raise ValueError(f"Insufficient historical bars downloaded (fetched {n_bars}, required at least 100)")
            
        prices = qqq_closes.values
        
        # Calculate features matching backtest
        wl = 35
        smooth, deriv1, deriv2 = calculate_savgol_rolling(prices, window_length=wl, polyorder=3)
        rsi = calculate_rsi(qqq_closes, period=14).values
        
        support_levels = np.full(n_bars, np.nan)
        resistance_levels = np.full(n_bars, np.nan)
        curr_support = np.nan
        curr_resistance = np.nan
        
        for i in range(wl, n_bars):
            if deriv1[i-1] < 0 and deriv1[i] >= 0 and deriv2[i] > 0:
                curr_support = prices[i]
            elif deriv1[i-1] > 0 and deriv1[i] <= 0 and deriv2[i] < 0:
                curr_resistance = prices[i]
                
            support_levels[i] = curr_support
            resistance_levels[i] = curr_resistance
            
        srp = np.full(n_bars, 0.5)
        for i in range(n_bars):
            sup = support_levels[i]
            res = resistance_levels[i]
            if not np.isnan(sup) and not np.isnan(res) and res > sup:
                srp[i] = (prices[i] - sup) / (res - sup)
                
        r_qqq = qqq_closes.pct_change().fillna(0.0)
        
        features = pd.DataFrame(index=qqq_closes.index)
        features["dist_smooth"] = np.where(smooth > 0, (prices / smooth - 1.0), 0.0)
        features["deriv1"] = np.nan_to_num(deriv1)
        features["deriv2"] = np.nan_to_num(deriv2)
        features["srp"] = srp
        features["rsi"] = np.nan_to_num(rsi)
        features["ret_1b"] = r_qqq
        features["ret_3b"] = qqq_closes.pct_change(3).fillna(0.0)
        features["ret_5b"] = qqq_closes.pct_change(5).fillna(0.0)
        features["vol_5b"] = r_qqq.rolling(5).std().fillna(0.0)
        
        # Target labels (forward return over next 5 bars)
        forward_returns = (qqq_closes.shift(-5) / qqq_closes - 1.0).fillna(0.0)
        labels = np.full(n_bars, 1)
        labels[forward_returns > 0.003] = 2
        labels[forward_returns < -0.003] = 0
        
        # Prepare training data: we exclude the last 5 bars because their forward return is not yet known
        X = features.values
        y = labels
        
        X_train = X[35 : -5]
        y_train = y[35 : -5]
        
        # Train Random Forest
        clf = RandomForestClassifier(
            n_estimators=params["n_estimators"], 
            max_depth=params["max_depth"], 
            min_samples_leaf=10, 
            random_state=42, 
            n_jobs=None
        )
        clf.fit(X_train, y_train)
        
        # Predict today (using the last feature row corresponding to index -1)
        feat_today = X[-1].reshape(1, -1)
        probs = clf.predict_proba(feat_today)[0]
        
        full_probs = np.zeros(3)
        for idx, cls in enumerate(clf.classes_):
            full_probs[cls] = probs[idx]
            
        pred = np.argmax(full_probs)
        
        asset_map = {0: "SQQQ", 1: "CASH", 2: "TQQQ"}
        proposed_asset = asset_map[pred]
        confidence = full_probs[pred]
        
        print("\nModel Prediction Probability Breakdown:")
        print(f"  * Bear (SQQQ)        : {full_probs[0]*100:.2f}%")
        print(f"  * Chop (CASH)        : {full_probs[1]*100:.2f}%")
        print(f"  * Bull (TQQQ)        : {full_probs[2]*100:.2f}%")
        print(f"Proposed Regime Asset  : {proposed_asset} (Confidence: {confidence*100:.2f}%)")
        
        # Apply confidence gate
        if confidence > params["thresh"]:
            target_asset = proposed_asset
            gate_triggered = True
        else:
            target_asset = current_asset_name
            gate_triggered = False
            print(f"Confidence below threshold ({params['thresh']*100:.1f}%). Holding current asset: {target_asset}")
            
        # Check trailing stop-loss (overrides minimum hold bars)
        stop_triggered = False
        ts_pct = params.get("trailing_stop_pct", None)
        if current_asset_name != "CASH" and ts_pct is not None and len(portfolio.get("holdings", [])) > 0:
            active_h = portfolio["holdings"][0]
            last_px = active_h["last_price"]
            peak_px = active_h.get("peak_price", active_h["buy_price"])
            if last_px < peak_px * (1.0 - ts_pct):
                target_asset = "CASH"
                stop_triggered = True
                print(f"Trailing Stop-Loss Triggered! Price (${last_px:,.2f} MXN) fell below stop price (${peak_px * (1.0 - ts_pct):,.2f} MXN).")
                
        # Enforce minimum hold time (unless stop was triggered)
        min_hold = params.get("min_hold_bars", 0)
        if not stop_triggered and current_asset_name != "CASH" and min_hold > 0 and len(portfolio.get("holdings", [])) > 0:
            active_h = portfolio["holdings"][0]
            bars_held = active_h.get("bars_held", 0)
            if bars_held < min_hold:
                target_asset = current_asset_name
                print(f"Minimum hold period active ({bars_held}/{min_hold} bars held). Locking position: {target_asset}")
            
    except Exception as e:
        print(f"Error executing Strategy 24 ML model: {e}")
        target_asset = current_asset_name
        gate_triggered = False
        confidence = 0.0
        proposed_asset = "CASH"
        full_probs = np.zeros(3)

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
                "bars_held": 0,
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
        action_note = f"No action. Model predicted {proposed_asset} but confidence ({confidence*100:.1f}%) gate did not trigger." if not gate_triggered and proposed_asset != current_asset_name else "No action. Current asset matches target asset."

    portfolio["total_portfolio_value_mxn"] = round(current_cash + holdings_val_mxn, 2)
    portfolio["last_updated"] = now_str

    # Save state
    if not args.dry_run:
        save_portfolio(dir_path, portfolio)
        print("Portfolio state successfully saved.")

    # 8. Write Live Report
    report_md = f"""# Strategy 24: 30-Minute Random Forest Live Report
**Report Generated:** {now_str}

## Current Status
* **Total Portfolio Value:** ${portfolio["total_portfolio_value_mxn"]:,.2f} MXN
* **Cash Balance:** ${portfolio["cash_balance"]:,.2f} MXN
* **Holding Asset:** {target_asset}

## ML Prediction Details
* **Bear (SQQQ) Probability:** {full_probs[0]*100:.2f}%
* **Chop (CASH) Probability:** {full_probs[1]*100:.2f}%
* **Bull (TQQQ) Probability:** {full_probs[2]*100:.2f}%
* **Proposed Target:** {proposed_asset} (Confidence: {confidence*100:.2f}%)
* **Gate Triggered:** {gate_triggered} (Threshold: {params['thresh']*100:.1f}%)

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
