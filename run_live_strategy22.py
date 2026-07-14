"""
LIVE EXECUTION: STRATEGY 22 WALK-FORWARD ONLINE ADAPTIVE ML CLASSIFIER
======================================================================
Runs daily to train a rolling Random Forest Classifier on yfinance QQQ data,
predicts the next 5-day market regime, and rebalances between TQQQ, SQQQ, and Cash.
"""
import os
import sys
import json
import argparse
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier

# Local settings
PORTFOLIO_FILE = "portfolio_strategy22.json"
TRANSACTIONS_FILE = "transactions_strategy22.md"
REPORT_FILE = "strategy22_report_live.md"

TRANSACTION_COST = 0.0029  # 0.29% GBM broker fee (spread + commission + VAT)
BONDIA_YIELD = 0.0653      # 6.53% MXN cash sweep compound yield
CONFIDENCE_THRESHOLD = 0.45  # Confidence gate threshold

def calculate_hurst_exponent_rolling(log_prices, window_size=100, max_lag=20):
    n = len(log_prices)
    hurst_values = np.full(n, 0.5)
    lags = np.arange(2, max_lag)
    log_lags = np.log(lags)
    log_lags_mean = np.mean(log_lags)
    log_lags_variance = np.sum((log_lags - log_lags_mean) ** 2)
    
    for i in range(window_size, n):
        sub_series = log_prices[i - window_size : i]
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
            continue
        log_stds = np.array(log_stds)
        covariance = np.sum((log_lags - log_lags_mean) * (log_stds - np.mean(log_stds)))
        slope = covariance / log_lags_variance
        hurst_values[i] = np.clip(slope, 0.0, 1.0)
    return hurst_values

def calculate_shannon_entropy_rolling(returns, window_size=60, num_bins=10):
    n = len(returns)
    entropy_values = np.full(n, 1.0)
    max_entropy = np.log2(num_bins)
    
    for i in range(window_size, n):
        sub_series = returns[i - window_size : i]
        counts, _ = np.histogram(sub_series, bins=num_bins)
        probs = counts / window_size
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log2(probs))
        entropy_values[i] = entropy / max_entropy if max_entropy > 0 else 1.0
    return entropy_values

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
        content = f"# Strategy 22: Walk-Forward ML Classifier Transaction Ledger\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"
        
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
    print(f"LIVE EXECUTION: STRATEGY 22 WALK-FORWARD ML ({today_str})")
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

    # 3. Fetch FX rate and prices
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

    # 4. Value existing holdings
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
        
    portfolio_value = current_cash + holdings_val_mxn
    print(f"Current Portfolio Value: ${portfolio_value:,.2f} MXN (Cash: ${current_cash:,.2f} MXN, Holdings: ${holdings_val_mxn:,.2f} MXN)")

    # 5. Fetch QQQ history and run Feature Engineering
    print("\nLoading trailing QQQ daily close series for ML training...")
    try:
        qqq_history = yf.download("QQQ", period="600d", progress=False)
        if isinstance(qqq_history.columns, pd.MultiIndex):
            qqq_history.columns = [c[0] for c in qqq_history.columns]
        
        qqq_closes = qqq_history["Close"].dropna()
        r_qqq = qqq_closes.pct_change().fillna(0.0)
        
        # Calculate features matching backtest
        features = pd.DataFrame(index=qqq_closes.index)
        features["ret_1d"] = r_qqq
        features["ret_5d"] = qqq_closes.pct_change(5).fillna(0.0)
        features["ret_10d"] = qqq_closes.pct_change(10).fillna(0.0)
        features["ret_20d"] = qqq_closes.pct_change(20).fillna(0.0)
        features["ret_60d"] = qqq_closes.pct_change(60).fillna(0.0)
        
        features["vol_5d"] = r_qqq.rolling(5).std().fillna(0.0)
        features["vol_20d"] = r_qqq.rolling(20).std().fillna(0.0)
        
        sma_50 = qqq_closes.rolling(50).mean()
        sma_120 = qqq_closes.rolling(120).mean()
        features["dist_sma50"] = (qqq_closes / sma_50 - 1.0).fillna(0.0)
        features["dist_sma120"] = (qqq_closes / sma_120 - 1.0).fillna(0.0)
        
        log_closes = np.log(qqq_closes.values)
        features["hurst"] = calculate_hurst_exponent_rolling(log_closes, window_size=100, max_lag=20)
        
        qqq_returns_val = r_qqq.values
        features["entropy"] = calculate_shannon_entropy_rolling(qqq_returns_val, window_size=60, num_bins=10)
        
        # Forward returns for training set
        forward_returns = (qqq_closes.shift(-5) / qqq_closes - 1.0).fillna(0.0)
        labels = np.full(len(qqq_closes), 1)
        labels[forward_returns > 0.015] = 2
        labels[forward_returns < -0.015] = 0
        
        # We split features:
        # Today's feature (last row in features) has no forward label (it's NaN or 0), but we use it for predicting.
        # Training set is data up to t-5 (which is index -6 in Python)
        X = features.values
        y = labels
        
        X_train = X[50:-5]
        y_train = y[50:-5]
        
        # Train Random Forest Classifier
        clf = RandomForestClassifier(n_estimators=50, max_depth=3, min_samples_leaf=10, random_state=42, n_jobs=None)
        clf.fit(X_train, y_train)
        
        # Predict today
        feat_today = X[-1].reshape(1, -1)
        probs = clf.predict_proba(feat_today)[0]
        pred = np.argmax(probs)
        
        asset_map = {0: "SQQQ", 1: "CASH", 2: "TQQQ"}
        proposed_asset = asset_map[pred]
        confidence = probs[pred]
        
        print("\nModel Prediction Probability Breakdown:")
        print(f"  * Bear (SQQQ)        : {probs[0]*100:.2f}%")
        print(f"  * Chop (CASH)        : {probs[1]*100:.2f}%")
        print(f"  * Bull (TQQQ)        : {probs[2]*100:.2f}%")
        print(f"Proposed Regime Asset  : {proposed_asset} (Confidence: {confidence*100:.2f}%)")
        
        # Apply confidence gate
        if confidence > CONFIDENCE_THRESHOLD:
            target_asset = proposed_asset
            gate_triggered = True
        else:
            target_asset = current_asset_name
            gate_triggered = False
            print(f"Confidence below threshold ({CONFIDENCE_THRESHOLD*100:.1f}%). Holding current asset: {target_asset}")
            
    except Exception as e:
        print(f"Error executing ML model: {e}. Defaulting to current position.")
        target_asset = current_asset_name
        gate_triggered = False
        confidence = 0.0
        proposed_asset = "CASH"

    # 6. Execute Rebalance
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
                "last_price": buy_price_mxn
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

    # 7. Write Live Report
    report_md = f"""# Strategy 22: Walk-Forward ML Live Report
**Report Generated:** {now_str}

## Current Status
* **Total Portfolio Value:** ${portfolio["total_portfolio_value_mxn"]:,.2f} MXN
* **Cash Balance:** ${portfolio["cash_balance"]:,.2f} MXN
* **Holding Asset:** {target_asset}

## ML Prediction Details
* **Bear (SQQQ) Probability:** {probs[0]*100:.2f}%
* **Chop (CASH) Probability:** {probs[1]*100:.2f}%
* **Bull (TQQQ) Probability:** {probs[2]*100:.2f}%
* **Proposed Target:** {proposed_asset} (Confidence: {confidence*100:.2f}%)
* **Gate Triggered:** {gate_triggered} (Threshold: {CONFIDENCE_THRESHOLD*100:.1f}%)

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
