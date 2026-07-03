import os
import sys
import json
import datetime
from zoneinfo import ZoneInfo
import argparse
import requests
import yfinance as yf
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from connectors.alpaca_connector import AlpacaConnector

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
            "last_updated": datetime.datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S")
        }
    with open(p_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_portfolio(dir_path, portfolio, now):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    portfolio["last_updated"] = now.strftime("%Y-%m-%d %H:%M:%S")
    with open(p_path, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, indent=2)

def log_transaction(dir_path, date_str, ticker, action, shares, price, note, fee=0.0):
    t_path = os.path.join(dir_path, TRANSACTIONS_FILE)
    if not os.path.exists(t_path):
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("# Transaction Ledger (Strategy 10: Upgraded Intraday Alpha)\n\n| Date | Ticker | Action | Shares | Price | Fee | Net Impact | Note |\n| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |\n---\n")
            
    net_amount = shares * price
    if action in ["BUY_TQQQ", "BUY_SQQQ", "DEPOSIT"]:
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
    
    # === NYSE TIMEZONE ENFORCEMENT ===
    ny_tz = ZoneInfo("America/New_York")
    now = datetime.datetime.now(ny_tz)
    today_str = now.strftime("%Y-%m-%d")

    print("=" * 80)
    print(f"LIVE UPGRADED EXECUTION: STRATEGY 10: INTRADAY VWAP ALPHA ({today_str} EST)")
    print("=" * 80)

    # === API INSTANTIATION ===
    try:
        alpaca = AlpacaConnector()
    except Exception as e:
        print(f"FATAL: Alpaca API keys missing or invalid. Engine halted. {e}")
        return

    # === CIRCUIT BREAKER 1: MARKET CLOCK AWARENESS ===
    print("[Telemetry] Verifying live market state via Alpaca Clock API...")
    try:
        clock_url = f"{alpaca.base_url}/v2/clock"
        headers = {"APCA-API-KEY-ID": alpaca.api_key, "APCA-API-SECRET-KEY": alpaca.secret_key}
        clock_resp = requests.get(clock_url, headers=headers, timeout=10)
        if clock_resp.status_code == 200:
            is_open = clock_resp.json().get("is_open", False)
            if not is_open:
                print("ABORT: Market is currently CLOSED. Halting execution to prevent stale data triggers.")
                return
    except Exception as e:
        print(f"[Warning] Market clock validation bypassed ({e}). Relying on timestamp integrity.")

    # 1. Load portfolio and accrue sweep interest
    portfolio = load_portfolio(dir_path)
    current_cash = portfolio["cash_balance"]

    last_updated_str = portfolio.get("last_updated", today_str + " 00:00:00")
    if " " in last_updated_str:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ny_tz)
    else:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d").replace(tzinfo=ny_tz)

    days_elapsed = max((now - last_dt).total_seconds() / (24.0 * 3600.0), 0.0)
    accrued_interest = 0.0
    if days_elapsed > 0:
        accrued_interest = current_cash * ((BONDIA_YIELD / 365.25) * days_elapsed)
        current_cash = round(current_cash + accrued_interest, 2)
        portfolio["cash_balance"] = current_cash
        portfolio["total_capital"] += accrued_interest
        log_transaction(dir_path, today_str, "BONDIA", "INTEREST", 1, accrued_interest, "Accrued interest on sweep balance", fee=0.0)

    # 2. Check for month change DCA
    is_new_month = now.year > last_dt.year or (now.year == last_dt.year and now.month > last_dt.month)
    if is_new_month:
        current_cash += MONTHLY_CONTRIBUTION
        portfolio["cash_balance"] = current_cash
        portfolio["total_capital"] += MONTHLY_CONTRIBUTION
        log_transaction(dir_path, today_str, "CASH", "DEPOSIT", 1, MONTHLY_CONTRIBUTION, "Monthly DCA savings contribution", fee=0.0)

    # 3. Fetch data for QQQ, TQQQ, SQQQ and FX rates
    print("\nFetching pricing histories and FX rates...")
    try:
        usdmxn_ticker = yf.Ticker("MXN=X")
        fx_hist = usdmxn_ticker.history(period="1d")
        fx_rate = float(fx_hist["Close"].iloc[-1]) if not fx_hist.empty else 18.0
        
        spy_daily = yf.download("SPY", period="2y", interval="1d", progress=False)
        spy_daily.columns = [c[0] if isinstance(c, tuple) else c for c in spy_daily.columns]
        
        qqq_30m = yf.download("QQQ", period="5d", interval="30m", progress=False)
        tqqq_30m = yf.download("TQQQ", period="5d", interval="30m", progress=False)
        sqqq_30m = yf.download("SQQQ", period="5d", interval="30m", progress=False)
        
        if qqq_30m.empty or tqqq_30m.empty or sqqq_30m.empty:
            print("CRITICAL: yfinance returned empty DataFrames (Silent API failure). Halting.")
            return

        if isinstance(qqq_30m.columns, pd.MultiIndex): qqq_30m.columns = [c[0] for c in qqq_30m.columns]
        if isinstance(tqqq_30m.columns, pd.MultiIndex): tqqq_30m.columns = [c[0] for c in tqqq_30m.columns]
        if isinstance(sqqq_30m.columns, pd.MultiIndex): sqqq_30m.columns = [c[0] for c in sqqq_30m.columns]
        
        qqq_30m["ATR"] = calculate_atr(qqq_30m, period=14)
        tqqq_30m["ATR"] = calculate_atr(tqqq_30m, period=14)
        sqqq_30m["ATR"] = calculate_atr(sqqq_30m, period=14)
    except Exception as e:
        print(f"Failed to fetch market data: {e}")
        return

    # === CIRCUIT BREAKER 2: TIMESTAMP VALIDATION ===
    last_bar_time = qqq_30m.index[-1]
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if last_bar_time.tzinfo is not None:
        minutes_stale = (now_utc - last_bar_time).total_seconds() / 60.0
        if minutes_stale > 45.0:
            print(f"FATAL: Data feed stall detected. Last QQQ bar is {minutes_stale:.1f} minutes old. Engine halted.")
            return

    # 4. HMM Regime Prediction
    spy_returns = spy_daily["Close"].ffill().pct_change().dropna().values.reshape(-1, 1)
    hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
    hmm.fit(spy_returns)
    regimes = hmm.predict(spy_returns)
    
    state_means = [np.mean(spy_returns[regimes == i]) for i in range(3)]
    state_vols = [np.std(spy_returns[regimes == i]) for i in range(3)]
    
    bear_state = np.argmax(state_vols)
    rem = [i for i in range(3) if i != bear_state]
    bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
    
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

    # 5. Establish current bar metrics
    close_qqq = float(qqq_30m["Close"].iloc[-1])
    atr_qqq = float(qqq_30m["ATR"].iloc[-1])
    close_tqqq = float(tqqq_30m["Close"].iloc[-1])
    atr_tqqq = float(tqqq_30m["ATR"].iloc[-1])
    close_sqqq = float(sqqq_30m["Close"].iloc[-1])
    atr_sqqq = float(sqqq_30m["ATR"].iloc[-1])

    today_bars_qqq = qqq_30m[qqq_30m.index.strftime("%Y-%m-%d") == today_str]
    
    if today_bars_qqq.empty:
        print(f"FATAL ERROR: No intraday rows mapped to {today_str}. Engine halted.")
        return 
        
    cum_pv = ((today_bars_qqq["High"] + today_bars_qqq["Low"] + today_bars_qqq["Close"]) / 3.0 * today_bars_qqq["Volume"]).sum()
    cum_vol = today_bars_qqq["Volume"].sum()
    vwap_qqq = cum_pv / cum_vol if cum_vol > 0 else close_qqq
    daily_high_qqq = float(today_bars_qqq["High"].max())
    daily_low_qqq = float(today_bars_qqq["Low"].min())

    upper_band = vwap_qqq + 1.5 * atr_qqq
    lower_band = vwap_qqq - 1.5 * atr_qqq

    # strictly 15:30 EST (3:30 PM New York)
    is_eod = now.time() >= datetime.time(15, 30)
    
    holdings = portfolio["holdings"]
    active_pos = holdings[0] if holdings else None
    action_logs = []
    
    # 6. Evaluation Logic (Exits)
    if active_pos:
        side = active_pos.get("side", "long")
        ticker = active_pos["ticker"]
        shares = active_pos["shares"]
        
        current_price = close_tqqq if side == "long" else close_sqqq
        atr_exec = atr_tqqq if side == "long" else atr_sqqq
        
        active_pos["peak_price"] = max(active_pos.get("peak_price", current_price), current_price)
        stop_threshold = active_pos["peak_price"] - 1.5 * atr_exec
        is_stop_out = current_price < stop_threshold
        
        if is_stop_out or is_eod:
            should_hold_overnight = False
            if is_eod and not is_stop_out:
                price_mxn = current_price * fx_rate
                trade_in_profit = (price_mxn > active_pos["buy_price"])
                if trade_in_profit:
                    if side == "long" and close_qqq >= (daily_high_qqq - 0.005 * daily_high_qqq) and regime == 0:
                        should_hold_overnight = True
                    elif side == "short" and close_qqq <= (daily_low_qqq + 0.005 * daily_low_qqq) and (regime == 1 or regime == 2):
                        should_hold_overnight = True
            
            if not should_hold_overnight:
                price_mxn = current_price * fx_rate
                if side == "long":
                    val = shares * price_mxn
                else:
                    val = active_pos["allocated"] + (active_pos["allocated"] - shares * price_mxn)
                
                # LIVE API EXECUTION (Selling the ETF to close the position)
                try:
                    alpaca.submit_order(ticker=ticker, qty=int(shares), side="sell", order_type="market", time_in_force="day")
                    current_cash += val * (1.0 - TRANSACTION_FEE_RATE)
                    exit_reason = "TRAILING_STOP" if is_stop_out else "EOD_LIQUIDATION"
                    log_transaction(dir_path, today_str, ticker, f"EXIT_{side.upper()}", shares, price_mxn, f"Exit: {exit_reason}", fee=0.0)
                    action_logs.append(f"LIQUIDATED {side.upper()} position on {ticker} via {exit_reason}. Balance credited: ${val:,.2f} MXN.")
                    portfolio["holdings"] = []
                    active_pos = None
                except Exception as e:
                    action_logs.append(f"CRITICAL EXECUTION FAILURE: Alpaca API rejected SELL order for {ticker}. State preserved. Error: {e}")
            else:
                action_logs.append(f"HOLDING {side.upper()} position on {ticker} overnight. (Reason: Strong trend close, trade in profit).")
                active_pos["last_price"] = current_price * fx_rate
                
    # 7. Entry Triggers (Entries)
    if not active_pos and not is_eod:
        target_ticker = None
        target_side = None
        target_price_mxn = None
        target_price_usd = None
        reason = ""

        if regime == 1 and close_qqq < lower_band: # Bear Breakout
            target_ticker, target_side = "SQQQ", "short"
            target_price_usd = close_sqqq
            target_price_mxn = close_sqqq * fx_rate
            reason = "Bear breakdown entry"
        elif regime == 0 and close_qqq > upper_band: # Bull Breakout
            target_ticker, target_side = "TQQQ", "long"
            target_price_usd = close_tqqq
            target_price_mxn = close_tqqq * fx_rate
            reason = "Bull breakout entry"
        elif regime == 2:
            if close_qqq < lower_band: # Chop Lower Reversion
                target_ticker, target_side = "TQQQ", "long"
                target_price_usd = close_tqqq
                target_price_mxn = close_tqqq * fx_rate
                reason = "Lower band mean-reversion buy"
            elif close_qqq > upper_band: # Chop Upper Reversion
                target_ticker, target_side = "SQQQ", "short"
                target_price_usd = close_sqqq
                target_price_mxn = close_sqqq * fx_rate
                reason = "Upper band mean-reversion short"

        if target_ticker:
            alloc = current_cash * 0.90
            shares = alloc / (target_price_mxn * (1.0 + TRANSACTION_FEE_RATE))
            exec_shares = int(shares) # Force integer shares to prevent Alpaca fractional errors on leveraged ETFs

            if exec_shares > 0:
                # LIVE API EXECUTION (Buying the target ETF to open the position)
                try:
                    alpaca.submit_order(ticker=target_ticker, qty=exec_shares, side="buy", order_type="market", time_in_force="day")
                    
                    # Update Ledger only upon success
                    current_cash -= (exec_shares * target_price_mxn)
                    portfolio["holdings"].append({
                        "ticker": target_ticker,
                        "side": target_side,
                        "shares": exec_shares,
                        "buy_price": target_price_mxn,
                        "last_price": target_price_mxn,
                        "peak_price": target_price_usd,
                        "allocated": (exec_shares * target_price_mxn)
                    })
                    log_transaction(dir_path, today_str, target_ticker, f"BUY_{target_ticker}", exec_shares, target_price_mxn, reason, fee=0.0)
                    action_logs.append(f"ENTERED {target_side.upper()} via {target_ticker} at ${target_price_mxn:,.2f} MXN ({exec_shares} shares).")
                except Exception as e:
                    action_logs.append(f"CRITICAL EXECUTION FAILURE: Alpaca API rejected BUY order for {target_ticker}. Capital preserved. Error: {e}")

    # Mid-day Reversion Exit logic during Chop
    elif active_pos and regime == 2 and not is_eod:
        side = active_pos["side"]
        if (side == "long" and close_qqq >= vwap_qqq) or (side == "short" and close_qqq <= vwap_qqq):
            current_price = close_tqqq if side == "long" else close_sqqq
            price_mxn = current_price * fx_rate
            shares = active_pos["shares"]
            
            if side == "long": val = shares * price_mxn
            else: val = active_pos["allocated"] + (active_pos["allocated"] - shares * price_mxn)
                
            try:
                alpaca.submit_order(ticker=active_pos["ticker"], qty=int(shares), side="sell", order_type="market", time_in_force="day")
                current_cash += val * (1.0 - TRANSACTION_FEE_RATE)
                log_transaction(dir_path, today_str, active_pos["ticker"], f"SETTLE_{side.upper()}_VWAP", shares, price_mxn, "Reversion target met at VWAP line", fee=0.0)
                action_logs.append(f"SETTLED {side.upper()} reversion on QQQ at VWAP line (${vwap_qqq:.2f}). Cash credited: ${val:,.2f} MXN.")
                portfolio["holdings"] = []
                active_pos = None
            except Exception as e:
                action_logs.append(f"CRITICAL EXECUTION FAILURE: Alpaca API rejected reversion SELL order. State preserved. Error: {e}")

    # Recalculate valuations
    assets_equity = 0.0
    for h in portfolio["holdings"]:
        curr_p = close_tqqq if h["side"] == "long" else close_sqqq
        h["last_price"] = curr_p * fx_rate
        if h["side"] == "long":
            assets_equity += h["shares"] * h["last_price"]
        else:
            assets_equity += h["allocated"] + (h["allocated"] - h["shares"] * h["last_price"])
            
    portfolio_value = current_cash + assets_equity

    # Save state
    portfolio["cash_balance"] = round(current_cash, 2)
    portfolio["total_capital"] = round(portfolio_value, 2)
    save_portfolio(dir_path, portfolio, now)

    # Generate live report
    report_md = f"""# Strategy 10: Upgraded Intraday VWAP Execution Report
**Execution Date:** {now.strftime('%Y-%m-%d %H:%M:%S EST')} | **Strategy Version:** LIVE EXECUTOR V4 (API Linked)

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} MXN
* **Total Cash Balance:** ${current_cash:,.2f} MXN
* **Equity Exposure:** {((portfolio_value - current_cash)/portfolio_value * 100):.1f}%
* **Active Regime:** State {regime} ({regime_reason})

## 2. Current Holdings
| Ticker | Type | Side | Shares | Buy Price (MXN) | Last Price (MXN) | Market Value (MXN) |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
"""
    for h in portfolio["holdings"]:
        t = h["ticker"]
        side = h.get("side", "long").upper()
        mkt_val = h["shares"] * h["last_price"] if side == "LONG" else h["allocated"] + (h["allocated"] - h["shares"] * h["last_price"])
        report_md += f"| **{t}** | LEVERAGED INTRADAY | {side} | {h['shares']} | ${h['buy_price']:,.2f} | ${h['last_price']:,.2f} | ${mkt_val:,.2f} |\n"

    report_md += "\n## 3. Today's Execution Logs\n"
    if action_logs:
        for log in action_logs: report_md += f"* {log}\n"
    else:
        report_md += "* No trades executed. API standby.\n"

    report_md += "\n## 4. Upgraded Asset Telemetry\n"
    report_md += f"  * Decoded Regime: HMM State {current_state_raw} -> **Regime {regime}**\n"
    report_md += f"  * QQQ Intraday VWAP: ${vwap_qqq:.2f} USD\n"

    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\nExecution complete. Live API report written to {REPORT_FILE}")

if __name__ == "__main__":
    main()
