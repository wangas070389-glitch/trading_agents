import os
import sys
import json
import datetime
import time
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn import hmm

# Ensure path includes root directory for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from connectors.alpaca_connector import AlpacaConnector
from skills.macd_trend import calculate_macd

EXPANDED_UNIVERSE = [
    "SPY", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST",
    "AMXB.MX", "FEMSAUBD.MX", "WALMEX.MX", "GFNORTEO.MX", "GMEXICOB.MX", 
    "CEMEXCPO.MX", "BIMBOA.MX", "GAPB.MX", "ASURB.MX", "AC.MX"
]

COMMISSION_RATE = 0.0010
BONDIA_APR = 0.0653  # CETES/Bondia 6.53% APR
DEAD_ZONE = 0.10

def load_portfolio(dir_path):
    portfolio_path = os.path.join(dir_path, "portfolio_macd.json")
    if os.path.exists(portfolio_path):
        with open(portfolio_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "total_capital": 20000.0,
        "cash_balance": 20000.0,
        "holdings": [],
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def save_portfolio(dir_path, portfolio):
    portfolio_path = os.path.join(dir_path, "portfolio_macd.json")
    with open(portfolio_path, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    transactions_path = os.path.join(dir_path, "transactions_macd.md")
    gross = shares * price
    if action == "BUY":
        cash_flow_str = f"-{gross + fee:,.2f}"
    elif action == "INTEREST":
        cash_flow_str = f"+{gross:,.4f}"
    else:
        cash_flow_str = f"+{gross - fee:,.2f}"

    row = f"| {date_str} | {ticker} | {action} | {shares} | {price:.2f} | {cash_flow_str} | Market | FILLED | {note} |"

    if os.path.exists(transactions_path):
        with open(transactions_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# Transaction Ledger (MACD Strategy)\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"

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

    with open(transactions_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def update_capital_reconciliation(dir_path, portfolio):
    transactions_path = os.path.join(dir_path, "transactions_macd.md")
    if not os.path.exists(transactions_path):
        return
        
    with open(transactions_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    recon_start = None
    for i, line in enumerate(lines):
        if "## Portfolio Capital Reconciliation" in line:
            recon_start = i
            break

    total_capital = portfolio["total_capital"]
    cash = portfolio["cash_balance"]
    invested = sum(h["shares"] * h["buy_price"] for h in portfolio["holdings"])
    total_value = cash + sum(h["shares"] * h.get("last_price", h["buy_price"]) for h in portfolio["holdings"])

    recon_lines = [
        "## Portfolio Capital Reconciliation",
        "",
        f"* **Initial Starting Capital (2026-06-03)**: {total_capital:,.2f} MXN",
        f"* **Total Deployed Capital**: {invested:,.2f} MXN ({invested/total_value*100:.1f}% invested)",
        f"* **Unallocated Cash Reserves**: {cash:,.2f} MXN ({cash/total_value*100:.1f}% cash)",
        f"* **Current Portfolio Market Value**: {total_value:,.2f} MXN (including cash)",
        ""
    ]

    if recon_start is not None:
        lines = lines[:recon_start] + recon_lines
    else:
        lines.extend(["", "---", ""] + recon_lines)

    with open(transactions_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    print("=" * 80)
    print("RUNNING LIVE INGESTION & EXECUTION: 1D MACD + SMA + HMM TREND STRATEGY")
    print("=" * 80)
    
    # 1. Load portfolio
    portfolio = load_portfolio(dir_path)
    cash = portfolio["cash_balance"]
    
    # 2. Accrue Bondia overnight yield
    last_updated_str = portfolio.get("last_updated")
    days_elapsed = 0.0
    if last_updated_str:
        try:
            last_updated = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            time_diff = now - last_updated
            days_elapsed = time_diff.total_seconds() / 86400.0
            
            if days_elapsed > 0.001 and cash > 0:
                daily_rate = BONDIA_APR / 360.0
                accrued_interest = cash * daily_rate * days_elapsed
                cash = round(cash + accrued_interest, 2)
                portfolio["cash_balance"] = cash
                
                # Log interest credit
                note = f"Bondia overnight yield on cash reserves for {days_elapsed:.4f} days."
                log_transaction(dir_path, today_str, "BONDIA", "INTEREST", 1, accrued_interest, note)
                print(f"  |-- [BONDIA INTEREST] Cash reserves credited +{accrued_interest:,.4f} MXN for {days_elapsed:.4f} days.")
        except Exception as e:
            print(f"  |-- [WARN] Failed to accrue Bondia interest: {e}")

    # 3. Train HMM on SPY to get market regime
    print("\nFetching SPY daily historical data to determine market regime...")
    try:
        spy = yf.download("SPY", period="5y", interval="1d", progress=False)
        spy.columns = [c if isinstance(c, str) else c[0] for c in spy.columns]
        spy.index = pd.to_datetime(spy.index).tz_localize(None)
        spy["Return"] = np.log(spy["Close"] / spy["Close"].shift(1))
        spy = spy.dropna()
        
        obs = spy["Return"].values.reshape(-1, 1)
        model = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=50, random_state=42)
        model.fit(obs)
        states = model.predict(obs)
        
        means = model.means_[:, 0]
        bear_idx = np.argmin(means)
        bull_idx = np.argmax(means)
        sideways_idx = [i for i in range(3) if i not in (bear_idx, bull_idx)][0]
        
        state_map = {bear_idx: -1, bull_idx: 1, sideways_idx: 0}
        current_regime = state_map[states[-1]]
    except Exception as e:
        print(f"  |-- HMM calculation failed: {e}. Defaulting to sideways regime.")
        current_regime = 0

    regime_names = {-1: "BEAR (Max Exposure: 10%)", 1: "BULL (Max Exposure: 95%)", 0: "SIDEWAYS (Max Exposure: 50%)"}
    print(f"  |-- Current HMM Regime: {regime_names[current_regime]}")
    
    max_equity_exposure = 0.50
    if current_regime == 1:
        max_equity_exposure = 0.95
    elif current_regime == -1:
        max_equity_exposure = 0.10

    # 4. Fetch exchange rate for MXN conversion
    print("\nFetching current USD/MXN exchange rate...")
    try:
        usdmxn = yf.Ticker("MXN=X").history(period="1d")
        rate = float(usdmxn["Close"].iloc[-1])
        print(f"  |-- Current exchange rate: {rate:.4f} MXN/USD")
    except Exception:
        rate = 17.50
        print(f"  |-- Failed to fetch exchange rate. Defaulting to {rate:.2f} MXN/USD")

    # 5. Fetch signals
    print(f"\nAnalyzing signals for all {len(EXPANDED_UNIVERSE)} assets...")
    bullish_assets = []
    current_prices = {}
    
    for ticker in EXPANDED_UNIVERSE:
        try:
            hist = yf.download(ticker, period="1y", interval="1d", progress=False)
            if hist.empty or len(hist) < 50:
                continue
            hist.columns = [c if isinstance(c, str) else c[0] for c in hist.columns]
            hist.index = pd.to_datetime(hist.index).tz_localize(None)
            
            # Calculate Indicators
            hist["macd"], hist["signal"] = calculate_macd(hist["Close"])
            hist["sma50"] = hist["Close"].rolling(window=50).mean()
            
            row = hist.iloc[-1]
            close = float(row["Close"])
            macd_val = float(row["macd"])
            sig_val = float(row["signal"])
            sma50_val = float(row["sma50"])
            
            is_bullish = macd_val > sig_val and close > sma50_val
            price_mxn = close * rate if not ticker.endswith(".MX") else close
            current_prices[ticker] = price_mxn
            
            status_str = "BULLISH" if is_bullish else "BEARISH/NEUTRAL"
            print(f"  Ticker {ticker:12} | Price: {price_mxn:8,.2f} MXN | Signal: {status_str:15}")
            
            if is_bullish:
                bullish_assets.append(ticker)
        except Exception as e:
            print(f"  Ticker {ticker:12} | Failed to fetch/calculate: {e}")

    # Calculate target weights
    target_weights = {t: 0.0 for t in EXPANDED_UNIVERSE}
    if len(bullish_assets) > 0:
        weight_per_asset = max_equity_exposure / len(bullish_assets)
        weight_per_asset = min(0.20, weight_per_asset)  # 20% cap per position
        for ticker in bullish_assets:
            target_weights[ticker] = weight_per_asset

    # 6. Reconcile Holdings & Calculate Trades
    print("\nReconciling portfolio targets...")
    current_holdings = {h["ticker"]: h for h in portfolio["holdings"]}
    
    # Calculate current portfolio market value
    total_market_value = sum(h["shares"] * current_prices.get(h["ticker"], h["last_price"]) for h in portfolio["holdings"])
    portfolio_value = cash + total_market_value
    print(f"  |-- Current Portfolio Value: {portfolio_value:,.2f} MXN")
    
    rebalancing_trades = []
    
    for ticker in EXPANDED_UNIVERSE:
        if ticker not in current_prices:
            continue
        close_price = current_prices[ticker]
        target_w = target_weights[ticker]
        
        # Calculate current weight
        shares_held = current_holdings.get(ticker, {}).get("shares", 0.0)
        current_w = (shares_held * close_price) / portfolio_value if portfolio_value > 0 else 0.0
        
        if abs(target_w - current_w) > DEAD_ZONE:
            target_val = portfolio_value * target_w
            current_val = shares_held * close_price
            trade_val = target_val - current_val
            
            if trade_val > 0.0:
                shares_to_buy = int(trade_val / close_price)
                if shares_to_buy > 0:
                    fee = trade_val * COMMISSION_RATE
                    rebalancing_trades.append({
                        "ticker": ticker,
                        "action": "BUY",
                        "shares": shares_to_buy,
                        "price": close_price,
                        "fee": fee
                    })
            elif trade_val < 0.0 and shares_held > 0:
                shares_to_sell = int(abs(trade_val) / close_price)
                shares_to_sell = min(shares_to_sell, int(shares_held))
                if shares_to_sell > 0:
                    fee = abs(trade_val) * COMMISSION_RATE
                    rebalancing_trades.append({
                        "ticker": ticker,
                        "action": "SELL",
                        "shares": shares_to_sell,
                        "price": close_price,
                        "fee": fee
                    })

    # 7. Execute Trades (Alpaca connection for US equities, local simulation for MXN)
    alpaca_client = None
    try:
        alpaca_client = AlpacaConnector()
        account_info = alpaca_client.get_account_info()
        print(f"\nConnected to Alpaca Paper Account (ID: {account_info.get('id')})")
    except Exception as e:
        print(f"\nAlpaca client not active or credentials missing: {e}. US trades will run in mock mode.")
        alpaca_client = None

    updated_holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}
    
    for trade in rebalancing_trades:
        ticker = trade["ticker"]
        action = trade["action"]
        shares = trade["shares"]
        price = trade["price"]
        fee = trade["fee"]
        
        is_us = not ticker.endswith(".MX")
        note = "1D MACD systematic signal"
        
        if is_us and alpaca_client:
            try:
                print(f"  |-- [Alpaca Order] Submitting order to Alpaca: {action} {shares} shares of {ticker}...")
                # Convert shares count to float if fractional trades are used, otherwise int is fine
                # Alpaca expects price in USD for US assets
                price_usd = price / rate
                order = alpaca_client.submit_order(ticker=ticker, qty=shares, side=action)
                order_id = order.get("id")
                print(f"  +-- [Alpaca Order Created] Order ID: {order_id} | Status: {order.get('status')}")
                note = f"Alpaca Order {order_id} | {note}"
            except Exception as e:
                print(f"  +-- [Alpaca Order FAILED] Error submitting order for {ticker}: {e}. Executing locally in mock mode.")
                note = f"Alpaca Execution Failed ({e}) | {note}"
        elif not is_us and alpaca_client:
             print(f"  |-- [Mock Order] Ticker {ticker} is a local BMV asset. Alpaca does not support Mexican shares. Running in mock mode.")
             
        # Apply ledger changes
        net_impact = (shares * price) + fee if action == "BUY" else -(shares * price - fee)
        cash -= net_impact
        
        if action == "BUY":
            if ticker in updated_holdings_dict:
                h = updated_holdings_dict[ticker]
                old_total_cost = h["shares"] * h["buy_price"]
                new_total_cost = old_total_cost + (shares * price)
                h["shares"] += shares
                h["buy_price"] = round(new_total_cost / h["shares"], 2)
                h["last_price"] = price
                h["target_weight"] = target_weights[ticker]
                h["hmm_state"] = current_regime
            else:
                updated_holdings_dict[ticker] = {
                    "ticker": ticker,
                    "shares": shares,
                    "buy_price": price,
                    "last_price": price,
                    "target_weight": target_weights[ticker],
                    "hmm_state": current_regime
                }
        elif action == "SELL":
            if ticker in updated_holdings_dict:
                h = updated_holdings_dict[ticker]
                h["shares"] -= shares
                h["last_price"] = price
                h["target_weight"] = target_weights[ticker]
                h["hmm_state"] = current_regime
                if h["shares"] <= 0:
                    del updated_holdings_dict[ticker]

        log_transaction(dir_path, today_str, ticker, action, shares, price, note, fee=fee)

    # Update holdings last prices for final saving
    final_holdings = []
    for ticker, h in updated_holdings_dict.items():
        if ticker in current_prices:
            h["last_price"] = current_prices[ticker]
        final_holdings.append(h)

    # Save portfolio.json
    portfolio["holdings"] = final_holdings
    portfolio["cash_balance"] = round(cash, 2)
    portfolio["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_portfolio(dir_path, portfolio)
    update_capital_reconciliation(dir_path, portfolio)
    
    print("\nPortfolio updated successfully!")
    print("=" * 80)

if __name__ == "__main__":
    main()
