import os
import sys
import json
import datetime
import argparse
import yfinance as yf
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

PORTFOLIO_FILE = "portfolio_strategy11.json"
TRANSACTIONS_FILE = "transactions_strategy11.md"
REPORT_FILE = "strategy11_report_live.md"

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
            f.write("# Transaction Ledger (Strategy 11: CCI-ADX Twin Strategy)\n\n| Date | Ticker | Action | Shares | Price | Fee | Net Impact | Note |\n| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |\n---\n")
            
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

def calculate_cci(df, period=10):
    tp = (df['High'] + df['Low'] + df['Close']) / 3.0
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma) / (0.015 * mad)
    return cci.fillna(0.0)

def calculate_adx(df, period=7):
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    tr_smooth = tr.rolling(window=period).mean()
    plus_dm_smooth = pd.Series(plus_dm, index=df.index).rolling(window=period).mean()
    minus_dm_smooth = pd.Series(minus_dm, index=df.index).rolling(window=period).mean()
    
    plus_di = (plus_dm_smooth / tr_smooth) * 100.0
    minus_di = (minus_dm_smooth / tr_smooth) * 100.0
    
    dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di).replace(0.0, np.nan)) * 100.0
    adx = dx.rolling(window=period).mean()
    
    return adx.fillna(20.0), plus_di.fillna(0.0), minus_di.fillna(0.0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-regime", type=int, choices=[0, 1, 2], help="Force a specific regime: 0=Bull, 1=Bear, 2=Chop")
    args = parser.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    now = datetime.datetime.now()

    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 11: DIRECT ASSET CCI-ADX ({today_str})")
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

    # 3. Fetch data
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
        
        if isinstance(qqq_30m.columns, pd.MultiIndex): qqq_30m.columns = [c[0] for c in qqq_30m.columns]
        if isinstance(tqqq_30m.columns, pd.MultiIndex): tqqq_30m.columns = [c[0] for c in tqqq_30m.columns]
        if isinstance(sqqq_30m.columns, pd.MultiIndex): sqqq_30m.columns = [c[0] for c in sqqq_30m.columns]
        
        # Calculate indicators directly on TQQQ and SQQQ
        tqqq_30m["ATR"] = calculate_atr(tqqq_30m, period=14)
        tqqq_30m["CCI"] = calculate_cci(tqqq_30m, period=10)
        adx_t, plus_di_t, minus_di_t = calculate_adx(tqqq_30m, period=7)
        tqqq_30m["ADX"] = adx_t
        tqqq_30m["DI+"] = plus_di_t
        tqqq_30m["DI-"] = minus_di_t
        
        sqqq_30m["ATR"] = calculate_atr(sqqq_30m, period=14)
        sqqq_30m["CCI"] = calculate_cci(sqqq_30m, period=10)
        adx_s, plus_di_s, minus_di_s = calculate_adx(sqqq_30m, period=7)
        sqqq_30m["ADX"] = adx_s
        sqqq_30m["DI+"] = plus_di_s
        sqqq_30m["DI-"] = minus_di_s
        
    except Exception as e:
        print(f"Failed to fetch market data: {e}")
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

    # 5. Extract current metrics
    close_qqq = float(qqq_30m["Close"].iloc[-1])
    
    close_tqqq = float(tqqq_30m["Close"].iloc[-1])
    cci_tqqq = float(tqqq_30m["CCI"].iloc[-1])
    adx_tqqq = float(tqqq_30m["ADX"].iloc[-1])
    di_plus_t = float(tqqq_30m["DI+"].iloc[-1])
    di_minus_t = float(tqqq_30m["DI-"].iloc[-1])
    atr_tqqq = float(tqqq_30m["ATR"].iloc[-1])
    
    close_sqqq = float(sqqq_30m["Close"].iloc[-1])
    cci_sqqq = float(sqqq_30m["CCI"].iloc[-1])
    adx_sqqq = float(sqqq_30m["ADX"].iloc[-1])
    di_plus_s = float(sqqq_30m["DI+"].iloc[-1])
    di_minus_s = float(sqqq_30m["DI-"].iloc[-1])
    atr_sqqq = float(sqqq_30m["ATR"].iloc[-1])

    today_date_str = now.strftime("%Y-%m-%d")
    today_bars_qqq = qqq_30m[qqq_30m.index.strftime("%Y-%m-%d") == today_date_str]
    
    if not today_bars_qqq.empty:
        daily_high_qqq = float(today_bars_qqq["High"].max())
        daily_low_qqq = float(today_bars_qqq["Low"].min())
    else:
        daily_high_qqq = close_qqq
        daily_low_qqq = close_qqq

    is_eod = now.time() >= datetime.time(14, 30) or now.time() >= datetime.time(15, 30)
    
    holdings = portfolio["holdings"]
    active_pos = holdings[0] if holdings else None
    action_logs = []
    
    # 6. Evaluation Logic
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
                    if side == "long" and close_qqq >= (daily_high_qqq - 0.005 * daily_high_qqq) and (regime == 0 or regime == 2):
                        should_hold_overnight = True
                    elif side == "short" and close_qqq <= (daily_low_qqq + 0.005 * daily_low_qqq) and (regime == 1 or regime == 2):
                        should_hold_overnight = True
            
            if not should_hold_overnight:
                price_mxn = current_price * fx_rate
                if side == "long":
                    val = shares * price_mxn
                else:
                    val = active_pos["allocated"] + (active_pos["allocated"] - shares * price_mxn)
                    
                current_cash += val * (1.0 - TRANSACTION_FEE_RATE)
                exit_reason = "TRAILING_STOP" if is_stop_out else "EOD_CLOSE"
                log_transaction(dir_path, today_str, ticker, f"EXIT_{side.upper()}", shares, price_mxn, f"Exit: {exit_reason}", fee=0.0)
                action_logs.append(f"LIQUIDATED {side.upper()} position on {ticker} via {exit_reason}. Balance credited: ${val:,.2f} MXN.")
                portfolio["holdings"] = []
                active_pos = None
            else:
                action_logs.append(f"HOLDING {side.upper()} position on {ticker} overnight due to strong ADX/trend close.")
                active_pos["last_price"] = current_price * fx_rate
                
    # 7. Entry triggers
    if not active_pos and not is_eod:
        # 1. Breakout long TQQQ (Bull state, TQQQ breakout)
        if (regime == 0 or regime == 2) and adx_tqqq >= 22.0 and cci_tqqq > 100.0 and di_plus_t > di_minus_t:
            price_mxn = close_tqqq * fx_rate
            alloc = current_cash * 0.90
            shares = alloc / (price_mxn * (1.0 + TRANSACTION_FEE_RATE))
            if shares > 0.01:
                current_cash -= alloc
                portfolio["holdings"].append({
                    "ticker": "TQQQ",
                    "side": "long",
                    "shares": shares,
                    "buy_price": price_mxn,
                    "last_price": price_mxn,
                    "peak_price": close_tqqq,
                    "allocated": alloc
                })
                log_transaction(dir_path, today_str, "TQQQ", "BUY_TQQQ", shares, price_mxn, "Direct asset trend breakout entry", fee=0.0)
                action_logs.append(f"ENTERED LONG trend breakout on TQQQ at ${price_mxn:,.2f} MXN (ADX={adx_tqqq:.1f}, CCI={cci_tqqq:.1f}).")
        # 2. Breakout SQQQ (Bear state, SQQQ breakout)
        elif (regime == 1 or regime == 2) and adx_sqqq >= 22.0 and cci_sqqq > 100.0 and di_plus_s > di_minus_s:
            price_mxn = close_sqqq * fx_rate
            alloc = current_cash * 0.90
            shares = alloc / (price_mxn * (1.0 + TRANSACTION_FEE_RATE))
            if shares > 0.01:
                current_cash -= alloc
                portfolio["holdings"].append({
                    "ticker": "SQQQ",
                    "side": "short",
                    "shares": shares,
                    "buy_price": price_mxn,
                    "last_price": price_mxn,
                    "peak_price": close_sqqq,
                    "allocated": alloc
                })
                log_transaction(dir_path, today_str, "SQQQ", "BUY_SQQQ", shares, price_mxn, "Direct asset trend breakdown entry", fee=0.0)
                action_logs.append(f"ENTERED SHORT trend breakdown on SQQQ at ${price_mxn:,.2f} MXN (ADX={adx_sqqq:.1f}, CCI={cci_sqqq:.1f}).")
        else:
            # Mean Reversion
            if adx_tqqq < 22.0 and cci_tqqq < -150.0:
                price_mxn = close_tqqq * fx_rate
                alloc = current_cash * 0.90
                shares = alloc / (price_mxn * (1.0 + TRANSACTION_FEE_RATE))
                if shares > 0.01:
                    current_cash -= alloc
                    portfolio["holdings"].append({
                        "ticker": "TQQQ",
                        "side": "long",
                        "shares": shares,
                        "buy_price": price_mxn,
                        "last_price": price_mxn,
                        "peak_price": close_tqqq,
                        "allocated": alloc
                    })
                    log_transaction(dir_path, today_str, "TQQQ", "BUY_TQQQ", shares, price_mxn, "Direct asset CCI reversion entry", fee=0.0)
                    action_logs.append(f"ENTERED LONG reversion on TQQQ at ${price_mxn:,.2f} MXN (CCI={cci_tqqq:.1f} oversold).")
            elif adx_sqqq < 22.0 and cci_sqqq < -150.0:
                price_mxn = close_sqqq * fx_rate
                alloc = current_cash * 0.90
                shares = alloc / (price_mxn * (1.0 + TRANSACTION_FEE_RATE))
                if shares > 0.01:
                    current_cash -= alloc
                    portfolio["holdings"].append({
                        "ticker": "SQQQ",
                        "side": "short",
                        "shares": shares,
                        "buy_price": price_mxn,
                        "last_price": price_mxn,
                        "peak_price": close_sqqq,
                        "allocated": alloc
                    })
                    log_transaction(dir_path, today_str, "SQQQ", "BUY_SQQQ", shares, price_mxn, "Direct asset CCI reversion entry", fee=0.0)
                    action_logs.append(f"ENTERED SHORT reversion on SQQQ at ${price_mxn:,.2f} MXN (CCI={cci_sqqq:.1f} oversold).")
    elif active_pos and not is_eod:
        side = active_pos["side"]
        cci_val = cci_tqqq if side == "long" else cci_sqqq
        if cci_val >= 0.0:
            current_price = close_tqqq if side == "long" else close_sqqq
            price_mxn = current_price * fx_rate
            shares = active_pos["shares"]
            
            if side == "long":
                val = shares * price_mxn
            else:
                val = active_pos["allocated"] + (active_pos["allocated"] - shares * price_mxn)
                
            current_cash += val * (1.0 - TRANSACTION_FEE_RATE)
            log_transaction(dir_path, today_str, active_pos["ticker"], f"SETTLE_{side.upper()}_CCI_ZERO", shares, price_mxn, "Direct CCI returned to zero line", fee=0.0)
            action_logs.append(f"SETTLED {side.upper()} reversion at direct CCI zero mark. Cash credited: ${val:,.2f} MXN.")
            portfolio["holdings"] = []
            active_pos = None

    # Calculate NAV
    assets_equity = 0.0
    for h in portfolio["holdings"]:
        curr_p = close_tqqq if h["side"] == "long" else close_sqqq
        h["last_price"] = curr_p * fx_rate
        if h["side"] == "long":
            assets_equity += h["shares"] * h["last_price"]
        else:
            assets_equity += h["allocated"] + (h["allocated"] - h["shares"] * h["last_price"])
            
    portfolio_value = current_cash + assets_equity

    portfolio["cash_balance"] = round(current_cash, 2)
    portfolio["total_capital"] = round(portfolio_value, 2)
    save_portfolio(dir_path, portfolio)

    # Live report
    report_md = f"""# Strategy 11: CCI-ADX Twin Strategy Execution Report
**Execution Date:** {now.strftime('%Y-%m-%d %H:%M:%S')} | **Strategy Version:** Twin V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} MXN
* **Total Cash Balance:** ${current_cash:,.2f} MXN (Parked compounding in Bondia sweep at 6.53% APR)
* **Equity Exposure:** {((portfolio_value - current_cash)/portfolio_value * 100):.1f}%
* **Active Regime:** State {regime} ({regime_reason})

## 2. Current Holdings
| Ticker | Type | Side | Shares | Buy Price (MXN) | Last Price (MXN) | Market Value (MXN) |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
"""
    for h in portfolio["holdings"]:
        t = h["ticker"]
        side = h.get("side", "long").upper()
        if side == "LONG":
            mkt_val = h["shares"] * h["last_price"]
        else:
            mkt_val = h["allocated"] + (h["allocated"] - h["shares"] * h["last_price"])
        report_md += f"| **{t}** | LEVERAGED INTRADAY | {side} | {h['shares']:.4f} | ${h['buy_price']:,.2f} | ${h['last_price']:,.2f} | ${mkt_val:,.2f} |\n"

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

    report_md += "\n## 4. CCI-ADX Telemetry\n"
    report_md += f"  * Decoded Regime: HMM State {current_state_raw} -> **Regime {regime} ({regime_reason})**\n"
    report_md += f"  * QQQ Close: ${close_qqq:.2f} USD\n"
    report_md += f"  * TQQQ CCI (10): {cci_tqqq:.1f} | ADX (7): {adx_tqqq:.1f}\n"
    report_md += f"  * SQQQ CCI (10): {cci_sqqq:.1f} | ADX (7): {adx_sqqq:.1f}\n"

    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\nExecution complete. Live report written to {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
