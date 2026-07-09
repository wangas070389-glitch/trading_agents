import os
import sys
import json
import datetime
import argparse
from zoneinfo import ZoneInfo
import yfinance as yf
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

PORTFOLIO_FILE = "portfolio_strategy16.json"
TRANSACTIONS_FILE = "transactions_strategy16.md"
REPORT_FILE = "strategy16_report_live.md"

TRANSACTION_FEE_RATE = 0.0000
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
            f.write("# Transaction Ledger (Strategy 16: Multi-Asset HMM Intraday Router)\n\n| Date | Ticker | Action | Shares | Price | Fee | Net Impact | Note |\n| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |\n---\n")
            
    net_amount = shares * price
    if action in ["BUY_TQQQ", "BUY_SQQQ", "BUY_UPRO", "BUY_SPXS", "BUY_SOXL", "BUY_SOXS", "BUY_URTY", "BUY_SRTY", "DEPOSIT"]:
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
    return adx.fillna(20.0)

def get_base_from_ticker(ticker, universe):
    for base, assets in universe.items():
        if ticker in [assets["bull"], assets["bear"]]:
            return base
    return "QQQ"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-target", type=str, choices=["QQQ", "SPY", "SOXX", "IWM"])
    parser.add_argument("--force-regime", type=int, choices=[0, 1, 2], help="0=Bull, 1=Bear, 2=Chop")
    args = parser.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    now = datetime.datetime.now()

    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 16: MULTI-ASSET HMM INTRADAY ROUTER ({today_str})")
    print("=" * 80)

    universe = {
        "QQQ": {"bull": "TQQQ", "bear": "SQQQ"},
        "SPY": {"bull": "UPRO", "bear": "SPXS"},
        "SOXX": {"bull": "SOXL", "bear": "SOXS"},
        "IWM": {"bull": "URTY", "bear": "SRTY"}
    }

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

    # 3. Fetch FX rate
    print("\nFetching pricing histories and FX rates...")
    try:
        usdmxn_ticker = yf.Ticker("MXN=X")
        fx_hist = usdmxn_ticker.history(period="1d")
        fx_rate = float(fx_hist["Close"].iloc[-1]) if not fx_hist.empty else 18.0
        print(f"USD/MXN Rate: {fx_rate:.4f}")
    except Exception as e:
        print(f"Error fetching FX rate: {e}. Defaulting to 18.0")
        fx_rate = 18.0

    # 4. Multi-asset HMM Regime Decoding (runs HMM on last 60 days of 1h bars)
    print("\nDecoding HMM regimes for universe...")
    regimes = {}
    scores = {}
    target_asset = None
    target_regime = None
    target_reason = ""

    for base in universe.keys():
        try:
            df = yf.download(base, period="730d", interval="1h", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            
            # Strip timezone
            if df.index.tz is not None:
                df.index = df.index.tz_convert("America/New_York").tz_localize(None)
                
            # Exclude today's incomplete daily bar to avoid lookahead bias
            df_train = df[df.index.date < datetime.date.today()]
            
            # Filter to exactly the last 60 trading days of history
            unique_dates = sorted(list(set(df_train.index.date)))
            if len(unique_dates) >= 60:
                target_dates = unique_dates[-60:]
                df_train = df_train[df_train.index.date >= target_dates[0]]
            
            if len(df_train) < 130:
                regimes[base] = 2
                scores[base] = -1
                continue

            train_closes = df_train["Close"]
            log_returns = np.log(train_closes / train_closes.shift(1)).fillna(0.0)
            rolling_vol = log_returns.rolling(window=10).std().fillna(0.0)
            features = np.column_stack([log_returns.values, rolling_vol.values])
            
            hmm = GaussianHMM(n_components=3, covariance_type="diag", n_iter=100, random_state=42)
            hmm.fit(features)
            states = hmm.predict(features)
            
            state_vols = [np.mean(rolling_vol.values[states == i]) if np.any(states == i) else 1e9 for i in range(3)]
            bear_state = np.argmax(state_vols)
            rem = [i for i in range(3) if i != bear_state]
            state_means = [np.mean(log_returns.values[states == i]) if np.any(states == i) else -1e9 for i in range(3)]
            bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
            
            curr_state_raw = states[-1]
            
            if curr_state_raw == bull_state:
                regimes[base] = 0
                scores[base] = abs(state_means[bull_state]) / state_vols[bull_state]
            elif curr_state_raw == bear_state:
                regimes[base] = 1
                scores[base] = abs(state_means[bear_state]) / state_vols[bear_state]
            else:
                regimes[base] = 2
                scores[base] = -0.5
        except Exception as e:
            print(f"Error HMM training on {base}: {e}")
            regimes[base] = 2
            scores[base] = -1.0

    # Target selection
    active_pos = portfolio["holdings"][0] if portfolio["holdings"] else None

    if active_pos:
        target_asset = active_pos.get("base", get_base_from_ticker(active_pos["ticker"], universe))
        target_regime = regimes[target_asset]
        target_reason = f"LOCKED to base asset of active holding ({target_asset})"
    elif args.force_target:
        target_asset = args.force_target
        target_regime = regimes[target_asset]
        target_reason = f"FORCED target selection via execution argument."
    else:
        # Prioritize trending assets
        trending = {k: v for k, v in scores.items() if regimes[k] in (0, 1)}
        if trending:
            target_asset = max(trending, key=trending.get)
            target_regime = regimes[target_asset]
            target_reason = f"Strongest decoded intraday trend state on {target_asset} (Score: {scores[target_asset]:.3f})"
        else:
            # All Chop, pick highest volume/volatility candidate (default QQQ)
            target_asset = "QQQ"
            target_regime = 2
            target_reason = f"All assets decoded to Chop. Reverting to default high-liquidity instrument QQQ."

    if args.force_regime is not None:
        target_regime = args.force_regime
        target_reason += " (Regime FORCED via execution argument)"

    print(f"Selected Target Asset: {target_asset}")
    print(f"Target Regime Decoded: State {target_regime} ({target_reason})")

    # 5. Fetch target intraday bars and calculate indicators
    bull_ticker = universe[target_asset]["bull"]
    bear_ticker = universe[target_asset]["bear"]

    print(f"\nFetching intraday metrics for {target_asset}, {bull_ticker}, {bear_ticker}...")
    try:
        base_df = yf.download(target_asset, period="10d", interval="1h", progress=False)
        bull_df = yf.download(bull_ticker, period="10d", interval="1h", progress=False)
        bear_df = yf.download(bear_ticker, period="10d", interval="1h", progress=False)

        if isinstance(base_df.columns, pd.MultiIndex): base_df.columns = [c[0] for c in base_df.columns]
        if isinstance(bull_df.columns, pd.MultiIndex): bull_df.columns = [c[0] for c in bull_df.columns]
        if isinstance(bear_df.columns, pd.MultiIndex): bear_df.columns = [c[0] for c in bear_df.columns]

        base_df["ATR"] = calculate_atr(base_df)
        
        bull_df["ATR"] = calculate_atr(bull_df)
        bull_df["CCI"] = calculate_cci(bull_df)
        bull_df["ADX"] = calculate_adx(bull_df)

        bear_df["ATR"] = calculate_atr(bear_df)
        bear_df["CCI"] = calculate_cci(bear_df)
        bear_df["ADX"] = calculate_adx(bear_df)
    except Exception as e:
        print(f"CRITICAL: Failed to download intraday bars: {e}")
        sys.exit(1)

    # 6. Extract indicators
    close_base = float(base_df["Close"].iloc[-1])
    atr_base = float(base_df["ATR"].iloc[-1])

    close_bull = float(bull_df["Close"].iloc[-1])
    atr_bull = float(bull_df["ATR"].iloc[-1])
    cci_bull = float(bull_df["CCI"].iloc[-1])
    adx_bull = float(bull_df["ADX"].iloc[-1])

    close_bear = float(bear_df["Close"].iloc[-1])
    atr_bear = float(bear_df["ATR"].iloc[-1])
    cci_bear = float(bear_df["CCI"].iloc[-1])
    adx_bear = float(bear_df["ADX"].iloc[-1])

    # Calculate VWAP for today
    today_date_str = datetime.datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    today_bars = base_df[base_df.index.strftime("%Y-%m-%d") == today_date_str]
    if not today_bars.empty:
        cum_pv = ((today_bars["High"] + today_bars["Low"] + today_bars["Close"]) / 3.0 * today_bars["Volume"]).sum()
        cum_vol = today_bars["Volume"].sum()
        vwap_base = cum_pv / cum_vol if cum_vol > 0 else close_base
        daily_high = float(today_bars["High"].max())
        daily_low = float(today_bars["Low"].min())
    else:
        vwap_base = close_base
        daily_high = close_base
        daily_low = close_base

    upper_band = vwap_base + 1.5 * atr_base
    lower_band = vwap_base - 1.5 * atr_base

    now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
    is_eod = now_et.time() >= datetime.time(15, 30)

    holdings = portfolio["holdings"]
    active_pos = holdings[0] if holdings else None
    action_logs = []

    # 7. Evaluate triggers
    if active_pos:
        side = active_pos["side"]
        ticker = active_pos["ticker"]
        shares = active_pos["shares"]
        
        current_price = close_bull if ticker == bull_ticker else close_bear
        atr_exec = atr_bull if ticker == bull_ticker else atr_bear
        
        # Stop check: starts at 3.0 ATR, tightens to 1.5 ATR when profit > 1.5 ATR
        active_pos["peak_price"] = max(active_pos.get("peak_price", current_price), current_price)
        buy_price_usd = active_pos["buy_price"] / fx_rate
        paper_profit_atr = (current_price - buy_price_usd) / atr_exec
        
        stop_mult = 3.0
        if paper_profit_atr > 1.5:
            stop_mult = 1.5
            
        stop_threshold = active_pos["peak_price"] - stop_mult * atr_exec
        is_stop_out = current_price < stop_threshold
        
        # Regime flip exit check
        is_regime_flip = False
        if side == "long" and target_regime != 0:
            is_regime_flip = True
        elif side == "short" and target_regime != 1:
            is_regime_flip = True

        if is_stop_out or is_regime_flip:
            price_mxn = current_price * fx_rate
            val = shares * price_mxn
            fee = val * TRANSACTION_FEE_RATE
            net_impact = val - fee
            
            if not args.dry_run:
                current_cash += net_impact
                exit_reason = "STOP_LOSS" if is_stop_out else "REGIME_FLIP"
                log_transaction(dir_path, today_str, ticker, f"SELL_{ticker}", shares, price_mxn, f"Exit target {target_asset} via {exit_reason}", fee=fee)
                portfolio["holdings"] = []
            
            active_pos = None
            action_logs.append(f"LIQUIDATED position in {ticker} ({side}) at ${price_mxn:,.2f} MXN. Reason: {'STOP_LOSS' if is_stop_out else 'REGIME_FLIP'}. Net cash returned: ${net_impact:,.2f} MXN.")

    # Entry triggers (if flat and not EOD) — Multi-day Swing pullback entries
    if not active_pos and not is_eod:
        if target_regime == 0:
            # Bull regime entry on bull ETF pullback
            if cci_bull < -100.0 and adx_bull > 20.0:
                price_mxn = close_bull * fx_rate
                alloc = current_cash * 0.90
                fee = alloc * TRANSACTION_FEE_RATE
                shares = (alloc - fee) / price_mxn
                if shares > 0.01:
                    if not args.dry_run:
                        current_cash -= alloc
                        portfolio["holdings"].append({
                            "ticker": bull_ticker,
                            "base": target_asset,
                            "side": "long",
                            "shares": shares,
                            "buy_price": price_mxn,
                            "last_price": price_mxn,
                            "peak_price": close_bull,
                            "allocated": alloc
                        })
                        log_transaction(dir_path, today_str, bull_ticker, f"BUY_{bull_ticker}", shares, price_mxn, "Bull swing pullback entry", fee=fee)
                    action_logs.append(f"ENTERED LONG {bull_ticker} at ${price_mxn:,.2f} MXN (CCI={cci_bull:.1f} ADX={adx_bull:.1f}).")
        elif target_regime == 1:
            # Bear regime entry on bear ETF pullback
            if cci_bear < -100.0 and adx_bear > 20.0:
                price_mxn = close_bear * fx_rate
                alloc = current_cash * 0.90
                fee = alloc * TRANSACTION_FEE_RATE
                shares = (alloc - fee) / price_mxn
                if shares > 0.01:
                    if not args.dry_run:
                        current_cash -= alloc
                        portfolio["holdings"].append({
                            "ticker": bear_ticker,
                            "base": target_asset,
                            "side": "short",
                            "shares": shares,
                            "buy_price": price_mxn,
                            "last_price": price_mxn,
                            "peak_price": close_bear,
                            "allocated": alloc
                        })
                        log_transaction(dir_path, today_str, bear_ticker, f"BUY_{bear_ticker}", shares, price_mxn, "Bear swing pullback entry", fee=fee)
                    action_logs.append(f"ENTERED SHORT {bear_ticker} at ${price_mxn:,.2f} MXN (CCI={cci_bear:.1f} ADX={adx_bear:.1f}).")

    # Update dynamic valuations (keep cached last_price if fresh price is NaN/invalid)
    holdings_equity = 0.0
    for h in portfolio["holdings"]:
        t = h["ticker"]
        curr_price = close_bull if t == bull_ticker else close_bear
        px_mxn = curr_price * fx_rate
        if np.isfinite(px_mxn) and px_mxn > 0:
            h["last_price"] = px_mxn
        holdings_equity += h["shares"] * h["last_price"]

    portfolio_value = current_cash + holdings_equity

    if not args.dry_run:
        portfolio["cash_balance"] = round(current_cash, 2)
        portfolio["total_capital"] = round(portfolio_value, 2)
        save_portfolio(dir_path, portfolio)

    # Live report markdown
    report_md = f"""# Strategy 16: Multi-Asset HMM Swing Router Execution Report
**Execution Date:** {now.strftime('%Y-%m-%d %H:%M:%S')} | **Strategy Version:** Router V2 (Hybrid Swing)

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} MXN
* **Total Cash Balance:** ${current_cash:,.2f} MXN (Parked compounding in Bondia sweep at 6.53% APR)
* **Equity Exposure:** {((portfolio_value - current_cash)/portfolio_value * 100) if portfolio_value > 0 else 0:.1f}%
* **Active Target Index:** **{target_asset}** (Regime: State {target_regime} - {target_reason})

## 2. Current Holdings
| Ticker | Type | Side | Shares | Buy Price (MXN) | Last Price (MXN) | Market Value (MXN) |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
"""
    for h in portfolio["holdings"]:
        t = h["ticker"]
        side = h.get("side", "long").upper()
        mkt_val = h["shares"] * h["last_price"]
        report_md += f"| **{t}** | LEVERAGED SWING | {side} | {h['shares']:.4f} | ${h['buy_price']:,.2f} | ${h['last_price']:,.2f} | ${mkt_val:,.2f} |\n"

    report_md += "\n## 3. Today's Execution Logs\n"
    if is_new_month:
        report_md += f"* **[SAVINGS DEPOSIT]** Month transition detected. Credited $2,000.00 MXN savings contribution.\n"
    if accrued_interest > 0:
        report_md += f"* **[INTEREST ACCRUED]** Cash reserves earned ${accrued_interest:,.4f} MXN sweep interest.\n"
    if action_logs:
        for log in action_logs:
            report_md += f"* {log}\n"
    else:
        report_md += "* No trades or rebalancing actions triggered in this 30-minute interval.\n"

    report_md += f"""
## 4. Multi-Asset HMM Telemetry
* Decoded Regimes:
  * **QQQ:** State {regimes.get('QQQ')} (Trend Score: {scores.get('QQQ', 0):.3f})
  * **SPY:** State {regimes.get('SPY')} (Trend Score: {scores.get('SPY', 0):.3f})
  * **SOXX:** State {regimes.get('SOXX')} (Trend Score: {scores.get('SOXX', 0):.3f})
  * **IWM:** State {regimes.get('IWM')} (Trend Score: {scores.get('IWM', 0):.3f})
* Active Telemetry ({target_asset}):
  * Base Price: ${close_base:.2f} USD | ATR (14): {atr_base:.2f}
  * VWAP: ${vwap_base:.2f} USD (Lower: ${lower_band:.2f} | Upper: ${upper_band:.2f})
"""

    if not args.dry_run:
        with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
            f.write(report_md)

    print(f"\nExecution complete. Live report generated.")
    print("=" * 80)

if __name__ == "__main__":
    main()
