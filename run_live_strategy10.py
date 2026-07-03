import os
import sys
import json
import datetime
import argparse
import yfinance as yf
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

# local import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

PORTFOLIO_FILE = "portfolio_strategy10.json"
TRANSACTIONS_FILE = "transactions_strategy10.md"
REPORT_FILE = "strategy10_report_live.md"

TRANSACTION_FEE_RATE = 0.0000  # Alpaca commission-free
MONTHLY_CONTRIBUTION = 2000.0  # MXN
BONDIA_YIELD = 0.0653          # 6.53% MXN cash sweep yield

def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if not os.path.exists(p_path):
        return {
            "total_capital": 200000.0,
            "cash_balance": 200000.0,
            "holdings": [],
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    with open(p_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_portfolio(dir_path, portfolio):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    portfolio["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(p_path, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(t_path):
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("# Transaction Ledger (Strategy 10: Intraday VWAP Alpha)\n\n| Date | Ticker | Action | Shares | Price | Fee | Net Impact | Note |\n| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |\n---\n")
            
    net_amount = shares * price
    if action in ["BUY", "DEPOSIT"]:
        net_amount = -(net_amount + fee)
    else:
        net_amount = net_amount - fee
        
    lines = []
    with open(t_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split("\n")
    row = f"| {date_str} | {ticker} | {action} | {shares:.4f} | ${price:.4f} | ${fee:.2f} | ${net_amount:,.2f} | {note} |"
    
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

def calculate_atr(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.fillna(tr.expanding().mean())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-regime", type=int, choices=[0, 1, 2], help="Force a specific regime: 0=Bull, 1=Bear, 2=Chop")
    args = parser.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    now = datetime.datetime.now()

    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 10: INTRADAY VWAP ALPHA ({today_str})")
    print("=" * 80)

    # 1. Load portfolio and accrue sweep interest
    portfolio = load_portfolio(dir_path)
    current_cash = portfolio["cash_balance"]

    last_updated_str = portfolio.get("last_updated", today_str + " 00:00:00")
    if " " in last_updated_str:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
    else:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d")

    days_elapsed = max((now - last_dt).total_seconds() / (24.0 * 3600.0), 0.0)
    accrued_interest = 0.0
    if days_elapsed > 0:
        accrued_interest = current_cash * ((BONDIA_YIELD / 365.25) * days_elapsed)
        current_cash = round(current_cash + accrued_interest, 2)
        portfolio["cash_balance"] = current_cash
        portfolio["total_capital"] += accrued_interest
        print(f"[Sweep Yield] Accrued ${accrued_interest:,.4f} MXN interest on sweeps.")
        log_transaction(dir_path, today_str, "BONDIA", "INTEREST", 1, accrued_interest, "Accrued interest on sweep balance", fee=0.0)

    # 2. Check for month change DCA
    is_new_month = now.year > last_dt.year or (now.year == last_dt.year and now.month > last_dt.month)
    if is_new_month:
        current_cash += MONTHLY_CONTRIBUTION
        portfolio["cash_balance"] = current_cash
        portfolio["total_capital"] += MONTHLY_CONTRIBUTION
        print(f"[DCA Deposit] Month transition detected. Ingested ${MONTHLY_CONTRIBUTION:,.2f} MXN.")
        log_transaction(dir_path, today_str, "CASH", "DEPOSIT", 1, MONTHLY_CONTRIBUTION, "Monthly DCA savings contribution", fee=0.0)

    # 3. Check currency rate and fetch SPY daily + QQQ 30-min data
    print("\nFetching pricing histories and FX rates...")
    try:
        usdmxn_ticker = yf.Ticker("MXN=X")
        fx_hist = usdmxn_ticker.history(period="1d")
        fx_rate = float(fx_hist["Close"].iloc[-1]) if not fx_hist.empty else 18.0
        
        spy_daily = yf.download("SPY", period="2y", interval="1d", progress=False)
        spy_daily.columns = [c[0] if isinstance(c, tuple) else c for c in spy_daily.columns]
        
        qqq_30m = yf.download("QQQ", period="5d", interval="30m", progress=False)
        if isinstance(qqq_30m.columns, pd.MultiIndex):
            qqq_30m.columns = [c[0] for c in qqq_30m.columns]
    except Exception as e:
        print(f"Failed to fetch market data: {e}")
        return

    # 4. HMM Regime Prediction (Daily check)
    spy_returns = spy_daily["Close"].ffill().pct_change().dropna().values.reshape(-1, 1)
    hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
    hmm.fit(spy_returns)
    regimes = hmm.predict(spy_returns)
    
    state_means = [np.mean(spy_returns[regimes == i]) for i in range(3)]
    state_vols = [np.std(spy_returns[regimes == i]) for i in range(3)]
    
    bear_state = np.argmax(state_vols)
    rem = [i for i in range(3) if i != bear_state]
    bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
    chop_state = [i for i in range(3) if i != bear_state and i != bull_state][0]
    
    current_state_raw = regimes[-1]
    if args.force_regime is not None:
        regime = args.force_regime
        regime_reason = "FORCED via execution flag"
    else:
        if current_state_raw == bull_state:
            regime = 0
            regime_reason = "Bull trend, low volatility detected on SPY"
        elif current_state_raw == bear_state:
            regime = 1
            regime_reason = "High volatility, downward pressure detected on SPY"
        else:
            regime = 2
            regime_reason = "Range-bound chop, mean-reversion detected on SPY"
            
    print(f"Regime Decoded: State {regime} ({regime_reason})")

    # 5. Calculate intraday VWAP and ATR Bands
    # Standardize time to local market hours
    # We group bars belonging to today to compute rolling VWAP
    today_date_str = now.strftime("%Y-%m-%d")
    qqq_30m.index = pd.to_datetime(qqq_30m.index)
    
    # Calculate ATR
    qqq_30m["ATR"] = calculate_atr(qqq_30m, period=14)
    
    # Filter bars belonging to the current trading day
    today_bars = qqq_30m[qqq_30m.index.strftime("%Y-%m-%d") == today_date_str]
    
    action_logs = []
    close_price = float(qqq_30m["Close"].iloc[-1])
    atr_val = float(qqq_30m["ATR"].iloc[-1])
    
    if not today_bars.empty:
        cum_pv = ((today_bars["High"] + today_bars["Low"] + today_bars["Close"]) / 3.0 * today_bars["Volume"]).sum()
        cum_vol = today_bars["Volume"].sum()
        vwap_val = cum_pv / cum_vol if cum_vol > 0 else close_price
    else:
        vwap_val = close_price

    upper_band = vwap_val + 2.0 * atr_val
    lower_band = vwap_val - 2.0 * atr_val

    # Check for EOD Square-off (Alpaca market close closeout at 2:30 PM CST / 15:30 EST)
    # Market close is at 15:00 CST / 16:00 EST. We check if time is past 2:30 PM CST (14:30 CST)
    is_eod = now.time() >= datetime.time(14, 30) or now.time() >= datetime.time(15, 30) # handle EST/CST overlap
    
    # Load open position if any
    holdings = portfolio["holdings"]
    active_pos = holdings[0] if holdings else None
    
    if is_eod:
        # Liquidate all holdings immediately
        if active_pos:
            ticker = active_pos["ticker"]
            shares = active_pos["shares"]
            side = active_pos.get("side", "long")
            
            price_mxn = close_price * fx_rate
            if side == "long":
                val = shares * price_mxn
            else:
                val = active_pos["allocated"] + (active_pos["allocated"] - shares * price_mxn)
                
            current_cash += val * (1.0 - TRANSACTION_FEE_RATE)
            log_transaction(dir_path, today_str, ticker, f"CLOSE_{side.upper()}", shares, close_price * fx_rate, "EOD square-off forced liquidation", fee=0.0)
            action_logs.append(f"FORCE CLOSED intraday {side.upper()} position on {ticker} for end-of-day square-off. Cash credited: ${val:,.2f} MXN.")
            portfolio["holdings"] = []
            active_pos = None
    else:
        # Run active trading triggers based on regime
        if regime == 1:
            # Bear state: Stays in cash sweeps, close positions if any
            if active_pos:
                ticker = active_pos["ticker"]
                shares = active_pos["shares"]
                side = active_pos.get("side", "long")
                price_mxn = close_price * fx_rate
                if side == "long":
                    val = shares * price_mxn
                else:
                    val = active_pos["allocated"] + (active_pos["allocated"] - shares * price_mxn)
                current_cash += val * (1.0 - TRANSACTION_FEE_RATE)
                log_transaction(dir_path, today_str, ticker, f"CLOSE_{side.upper()}", shares, price_mxn, "Bear regime shift liquidation", fee=0.0)
                action_logs.append(f"CLOSED position on {ticker} due to Bear state classification.")
                portfolio["holdings"] = []
                active_pos = None
                
        elif regime == 0:
            # Bull state: Momentum Breakouts
            if not active_pos:
                if close_price > upper_band:
                    # Enter Long QQQ
                    price_mxn = close_price * fx_rate
                    alloc = current_cash * 0.90
                    shares = alloc / (price_mxn * (1.0 + TRANSACTION_FEE_RATE))
                    if shares > 0.01:
                        current_cash -= alloc
                        portfolio["holdings"].append({
                            "ticker": "QQQ",
                            "side": "long",
                            "shares": shares,
                            "buy_price": price_mxn,
                            "last_price": price_mxn,
                            "allocated": alloc
                        })
                        log_transaction(dir_path, today_str, "QQQ", "BUY_LONG", shares, price_mxn, "Bull breakout entry", fee=0.0)
                        action_logs.append(f"ENTERED LONG breakout on QQQ at ${price_mxn:,.2f} MXN.")
                elif close_price < lower_band:
                    # Enter Short QQQ
                    price_mxn = close_price * fx_rate
                    alloc = current_cash * 0.90
                    shares = alloc / (price_mxn * (1.0 + TRANSACTION_FEE_RATE))
                    if shares > 0.01:
                        current_cash -= alloc
                        portfolio["holdings"].append({
                            "ticker": "QQQ",
                            "side": "short",
                            "shares": shares,
                            "buy_price": price_mxn,
                            "last_price": price_mxn,
                            "allocated": alloc
                        })
                        log_transaction(dir_path, today_str, "QQQ", "SELL_SHORT", shares, price_mxn, "Bear breakdown entry", fee=0.0)
                        action_logs.append(f"ENTERED SHORT breakdown on QQQ at ${price_mxn:,.2f} MXN.")
                        
        else:
            # Chop state: Mean Reversion to VWAP
            if not active_pos:
                if close_price < lower_band:
                    # Buy reversion (Long)
                    price_mxn = close_price * fx_rate
                    alloc = current_cash * 0.90
                    shares = alloc / (price_mxn * (1.0 + TRANSACTION_FEE_RATE))
                    if shares > 0.01:
                        current_cash -= alloc
                        portfolio["holdings"].append({
                            "ticker": "QQQ",
                            "side": "long",
                            "shares": shares,
                            "buy_price": price_mxn,
                            "last_price": price_mxn,
                            "allocated": alloc
                        })
                        log_transaction(dir_path, today_str, "QQQ", "BUY_REVERSION", shares, price_mxn, "Lower band mean-reversion buy", fee=0.0)
                        action_logs.append(f"ENTERED LONG reversion on QQQ at ${price_mxn:,.2f} MXN (Price < Lower Band).")
                elif close_price > upper_band:
                    # Sell reversion (Short)
                    price_mxn = close_price * fx_rate
                    alloc = current_cash * 0.90
                    shares = alloc / (price_mxn * (1.0 + TRANSACTION_FEE_RATE))
                    if shares > 0.01:
                        current_cash -= alloc
                        portfolio["holdings"].append({
                            "ticker": "QQQ",
                            "side": "short",
                            "shares": shares,
                            "buy_price": price_mxn,
                            "last_price": price_mxn,
                            "allocated": alloc
                        })
                        log_transaction(dir_path, today_str, "QQQ", "SHORT_REVERSION", shares, price_mxn, "Upper band mean-reversion short", fee=0.0)
                        action_logs.append(f"ENTERED SHORT reversion on QQQ at ${price_mxn:,.2f} MXN (Price > Upper Band).")
            else:
                # Target reversion to VWAP line to settle early
                side = active_pos["side"]
                if (side == "long" and close_price >= vwap_val) or \
                   (side == "short" and close_price <= vwap_val):
                    price_mxn = close_price * fx_rate
                    shares = active_pos["shares"]
                    if side == "long":
                        val = shares * price_mxn
                    else:
                        val = active_pos["allocated"] + (active_pos["allocated"] - shares * price_mxn)
                    current_cash += val * (1.0 - TRANSACTION_FEE_RATE)
                    log_transaction(dir_path, today_str, "QQQ", f"SETTLE_{side.upper()}_VWAP", shares, price_mxn, "Reversion target met at VWAP line", fee=0.0)
                    action_logs.append(f"SETTLED {side.upper()} reversion on QQQ at VWAP line (${vwap_val:.2f}). Cash credited: ${val:,.2f} MXN.")
                    portfolio["holdings"] = []
                    active_pos = None

    # Calculate portfolio values
    assets_equity = 0.0
    for h in portfolio["holdings"]:
        h["last_price"] = close_price * fx_rate
        side = h.get("side", "long")
        if side == "long":
            assets_equity += h["shares"] * h["last_price"]
        else:
            assets_equity += h["allocated"] + (h["allocated"] - h["shares"] * h["last_price"])
            
    portfolio_value = current_cash + assets_equity

    # Save state
    portfolio["cash_balance"] = round(current_cash, 2)
    portfolio["total_capital"] = round(portfolio_value, 2)
    save_portfolio(dir_path, portfolio)

    # 7. Generate markdown report
    report_md = f"""# Strategy 10: Intraday VWAP Alpha Execution Report
**Execution Date:** {now.strftime('%Y-%m-%d %H:%M:%S')} | **Strategy Version:** Upgraded Live V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} MXN
* **Total Cash Balance:** ${current_cash:,.2f} MXN (Parked compounding in Bondia sweep at 6.53% APR)
* **Equity Exposure:** {((portfolio_value - current_cash)/portfolio_value * 100):.1f}%
* **Active Regime:** State {regime} ({regime_reason})

## 2. Current Holdings
| Ticker | Type | Side | Shares | Buy Price | Last Price | Market Value (MXN) |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
"""
    for h in portfolio["holdings"]:
        t = h["ticker"]
        side = h.get("side", "long").upper()
        if side == "LONG":
            mkt_val = h["shares"] * h["last_price"]
        else:
            mkt_val = h["allocated"] + (h["allocated"] - h["shares"] * h["last_price"])
        report_md += f"| **{t}** | INTRADAY POSITION | {side} | {h['shares']:.4f} | ${h['buy_price']:,.2f} | ${h['last_price']:,.2f} | ${mkt_val:,.2f} |\n"

    report_md += "\n## 3. Today's Execution Logs\n"
    if is_new_month:
        report_md += f"* **[SAVINGS DEPOSIT]** Month transition detected. Credited $2,000.00 MXN savings contribution.\n"
    if accrued_interest > 0:
        report_md += f"* **[INTEREST ACCRUED]** Cash reserves earned $${accrued_interest:,.4f} MXN sweep interest.\n"
    if action_logs:
        for log in action_logs:
            report_md += f"* {log}\n"
    else:
        report_md += "* No trades or rebalancing actions triggered in this 30-minute interval.\n"

    # Add Diagnostics
    report_md += "\n## 4. Asset Evaluation Diagnostics (VWAP & ATR telemetry)\n"
    report_md += f"  * Decoded Regime: HMM State {current_state_raw} -> **Regime {regime} ({regime_reason})**\n"
    report_md += f"  * QQQ Last Price: ${close_price:.2f} USD\n"
    report_md += f"  * QQQ Intraday VWAP: ${vwap_val:.2f} USD\n"
    report_md += f"  * QQQ Intraday ATR (14): ${atr_val:.2f} USD\n"
    report_md += f"  * VWAP Volatility bands:\n"
    report_md += f"    * Upper Band (+2.0 ATR): ${upper_band:.2f} USD\n"
    report_md += f"    * Lower Band (-2.0 ATR): ${lower_band:.2f} USD\n"

    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\nExecution complete. Live report written to {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
