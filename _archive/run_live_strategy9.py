import os
import sys
import json
import datetime
import argparse
import yfinance as yf
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from arch import arch_model
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint

# local import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Strategy Universe
US_TICKERS = ["SPY", "GLD", "BTC-USD", "ETH-USD", "EURUSD=X", "GBPUSD=X"]
PORTFOLIO_FILE = "portfolio_strategy9.json"
TRANSACTIONS_FILE = "transactions_strategy9.md"
REPORT_FILE = "strategy9_report_live.md"

TRANSACTION_FEE_RATE = 0.0029
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
            f.write("# Transaction Ledger (Strategy 9: AI-Regime Adaptive Arbitrage)\n\n| Date | Ticker | Action | Shares | Price | Fee | Net Impact | Note |\n| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |\n---\n")
            
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

def calculate_garch_vol(returns, default=0.15):
    try:
        if len(returns) < 50:
            return default
        model = arch_model(returns * 100, vol='Garch', p=1, q=1, dist='normal', show_warning=False)
        res = model.fit(disp='off')
        forecast = res.forecast(horizon=1)
        forecast_vol = np.sqrt(forecast.variance.iloc[-1].values[0]) / 100.0
        return forecast_vol * np.sqrt(252)
    except Exception:
        return default

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-regime", type=int, choices=[0, 1, 2], help="Force a specific regime: 0=Bull, 1=Bear, 2=Chop")
    args = parser.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    from halt_gate import halted
    if halted(dir_path, "strategy9"):
        return
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    now = datetime.datetime.now()

    print("=" * 80)
    print(f"LIVE EXECUTION: STRATEGY 9: AI REGIME STAT-ARB ({today_str})")
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

    # 3. Download data and check FX rate
    print("\nFetching ticker histories from yfinance (2 years)...")
    try:
        data = yf.download(US_TICKERS, period="2y", interval="1d", group_by="ticker", progress=False)
        usdmxn_ticker = yf.Ticker("MXN=X")
        fx_hist = usdmxn_ticker.history(period="1d")
        fx_rate = float(fx_hist["Close"].iloc[-1]) if not fx_hist.empty else 18.0
        if not (np.isfinite(fx_rate) and fx_rate > 0):
            fx_rate = 18.0
    except Exception as e:
        print(f"Failed to fetch market data: {e}")
        return

    prices = pd.DataFrame()
    for t in US_TICKERS:
        if t in data.columns.levels[0]:
            prices[t] = data[t]["Close"].ffill().bfill()
    prices.index = pd.to_datetime(prices.index)

    current_prices = {t: float(prices[t].iloc[-1]) for t in US_TICKERS if t in prices.columns}
    invalid = [t for t in US_TICKERS
               if t not in current_prices or not (np.isfinite(current_prices[t]) and current_prices[t] > 0)]
    if invalid:
        print(f"CRITICAL: no valid price for {invalid} (market closed or empty feed). Aborting run without trading.")
        return
    
    # 4. HMM Regime Prediction
    spy_returns = prices["SPY"].pct_change().dropna().values.reshape(-1, 1)
    
    # Train Gaussian HMM
    hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
    hmm.fit(spy_returns)
    regimes = hmm.predict(spy_returns)
    
    # Map HMM states to strategic regimes
    state_means = [np.mean(spy_returns[regimes == i]) for i in range(3)]
    state_vols = [np.std(spy_returns[regimes == i]) for i in range(3)]
    
    bear_state = np.argmax(state_vols)
    rem = [i for i in range(3) if i != bear_state]
    bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
    chop_state = [i for i in range(3) if i != bear_state and i != bull_state][0]
    
    # Map raw HMM states to strategic regimes for the last 3 days to apply consensus filter
    last_3_raw = regimes[-3:] if len(regimes) >= 3 else regimes
    last_3_regimes = []
    for r_raw in last_3_raw:
        if r_raw == bull_state:
            last_3_regimes.append(0)
        elif r_raw == bear_state:
            last_3_regimes.append(1)
        else:
            last_3_regimes.append(2)
            
    # Consensus filter: take the mode (majority vote) of the last 3 days
    from collections import Counter
    counts = Counter(last_3_regimes)
    mode_val, mode_count = counts.most_common(1)[0]
    if mode_count >= 2:
        consensus_regime = mode_val
    else:
        consensus_regime = last_3_regimes[-1]
        
    current_state_raw = regimes[-1]
    raw_regime = 0 if current_state_raw == bull_state else (1 if current_state_raw == bear_state else 2)
    
    if args.force_regime is not None:
        regime = args.force_regime
        regime_reason = "FORCED via execution flag"
    else:
        regime = consensus_regime
        reasons = {
            0: "Bull trend, low volatility detected on SPY (3-day HMM consensus)",
            1: "High volatility, downward pressure detected on SPY (3-day HMM consensus)",
            2: "Range-bound chop, mean-reversion detected on SPY (3-day HMM consensus)"
        }
        regime_reason = reasons[regime]
        
    print(f"\nRegime Decoded: Raw today={raw_regime} | Consensus={regime} ({regime_reason})")
    
    # 5. Process Exits
    holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}
    action_logs = []
    
    # Rotate out of status-holding assets if regime shifts
    for ticker, h in list(holdings_dict.items()):
        # Liquidate SPY if we exit Bull regime
        if ticker == "SPY" and regime != 0:
            p = current_prices["SPY"] * fx_rate
            value = h["shares"] * p
            fee = value * TRANSACTION_FEE_RATE
            current_cash += (value - fee)
            log_transaction(dir_path, today_str, "SPY", "SELL", h["shares"], p, "Regime shifted out of Bull mode", fee=fee)
            action_logs.append(f"SOLD {h['shares']:.4f} shares of SPY due to regime rotation.")
            del holdings_dict["SPY"]
            
        # Liquidate GLD if we exit Bear regime
        if ticker == "GLD" and regime != 1:
            p = current_prices["GLD"] * fx_rate
            value = h["shares"] * p
            fee = value * TRANSACTION_FEE_RATE
            current_cash += (value - fee)
            log_transaction(dir_path, today_str, "GLD", "SELL", h["shares"], p, "Regime shifted out of Bear mode", fee=fee)
            action_logs.append(f"SOLD {h['shares']:.4f} shares of GLD due to regime rotation.")
            del holdings_dict["GLD"]

        # Liquidate pairs if we exit Chop regime
        if ticker.startswith("PAIR:") and regime != 2:
            # Settle pair spread
            pair_name = ticker.split("PAIR:")[1]
            y, x = pair_name.split("/")
            p_y = current_prices[y]
            p_x = current_prices[x]
            
            # Settle value:
            # We fetch from JSON notes or calculate
            side = h.get("side", "long_spread")
            if side == "long_spread":
                val = (h["qty_y"] * p_y) - (h["qty_x"] * p_x)
            else:
                val = -(h["qty_y"] * p_y) + (h["qty_x"] * p_x)
                
            # Convert spread to MXN if US/USD assets
            is_us = y in ["BTC-USD", "ETH-USD", "EURUSD=X", "GBPUSD=X"]
            if is_us:
                val *= fx_rate
                
            current_cash += val * (1.0 - TRANSACTION_FEE_RATE)
            log_transaction(dir_path, today_str, ticker, "SELL", 1.0, val, f"Regime shifted out of Chop mode. Settle value: ${val:,.2f} MXN", fee=0.0)
            action_logs.append(f"LIQUIDATED pair spread {pair_name} due to regime rotation.")
            del holdings_dict[ticker]

    # Save intermediate cash
    portfolio["holdings"] = list(holdings_dict.values())
    portfolio["cash_balance"] = round(current_cash, 2)

    # Calculate portfolio values
    assets_equity = 0.0
    for h in portfolio["holdings"]:
        t = h["ticker"]
        if t == "SPY":
            h["last_price"] = current_prices["SPY"] * fx_rate
            assets_equity += h["shares"] * h["last_price"]
        elif t == "GLD":
            h["last_price"] = current_prices["GLD"] * fx_rate
            assets_equity += h["shares"] * h["last_price"]
        elif t.startswith("PAIR:"):
            # Update pair pricing
            pair_name = t.split("PAIR:")[1]
            y, x = pair_name.split("/")
            p_y = current_prices[y]
            p_x = current_prices[x]
            side = h.get("side", "long_spread")
            if side == "long_spread":
                val = (h["qty_y"] * p_y) - (h["qty_x"] * p_x)
            else:
                val = -(h["qty_y"] * p_y) + (h["qty_x"] * p_x)
            if y in ["BTC-USD", "ETH-USD", "EURUSD=X", "GBPUSD=X"]:
                val *= fx_rate
            h["last_price"] = val
            assets_equity += val
            
    portfolio_value = current_cash + assets_equity

    # 6. Process Entries based on Regime
    if regime == 0:
        # Bull: Hold SPY
        if "SPY" not in holdings_dict:
            price_mxn = current_prices["SPY"] * fx_rate
            target_allocation = portfolio_value * 0.90
            shares = int(target_allocation / (price_mxn * (1.0 + TRANSACTION_FEE_RATE)))
            if shares > 0:
                cost = shares * price_mxn
                fee = cost * TRANSACTION_FEE_RATE
                current_cash -= (cost + fee)
                portfolio["holdings"].append({
                    "ticker": "SPY",
                    "shares": shares,
                    "buy_price": price_mxn,
                    "last_price": price_mxn
                })
                log_transaction(dir_path, today_str, "SPY", "BUY", shares, price_mxn, "Bull regime allocation", fee=fee)
                action_logs.append(f"BOUGHT {shares} shares of SPY at ${price_mxn:,.2f} MXN.")
                
    elif regime == 1:
        # Bear: Hold GLD
        if "GLD" not in holdings_dict:
            price_mxn = current_prices["GLD"] * fx_rate
            target_allocation = portfolio_value * 0.90
            shares = int(target_allocation / (price_mxn * (1.0 + TRANSACTION_FEE_RATE)))
            if shares > 0:
                cost = shares * price_mxn
                fee = cost * TRANSACTION_FEE_RATE
                current_cash -= (cost + fee)
                portfolio["holdings"].append({
                    "ticker": "GLD",
                    "shares": shares,
                    "buy_price": price_mxn,
                    "last_price": price_mxn
                })
                log_transaction(dir_path, today_str, "GLD", "BUY", shares, price_mxn, "Bear regime allocation", fee=fee)
                action_logs.append(f"BOUGHT {shares} shares of GLD at ${price_mxn:,.2f} MXN.")
                
    else:
        # Chop: Pairs Arbitrage
        pairs = [
            ("BTC-USD", "ETH-USD"),
            ("EURUSD=X", "GBPUSD=X")
        ]
        
        all_evaluations = {}
        
        for pair in pairs:
            y, x = pair
            pair_ticker = f"PAIR:{y}/{x}"
            if pair_ticker in holdings_dict:
                # evaluate exit check
                h = holdings_dict[pair_ticker]
                y_series = np.log(prices[y].iloc[-120:].astype(float))
                x_series = np.log(prices[x].iloc[-120:].astype(float))
                
                try:
                    ols_model = sm.OLS(y_series, sm.add_constant(x_series)).fit()
                    mean_spread = (y_series - ols_model.params[1] * x_series).mean()
                    std_spread = (y_series - ols_model.params[1] * x_series).std()
                    z_score = ((np.log(current_prices[y]) - ols_model.params[1] * np.log(current_prices[x])) - mean_spread) / std_spread
                except Exception:
                    z_score = 0.0
                    
                # Exit when Z score reverts back to 0
                if (h["side"] == "long_spread" and z_score >= 0.0) or \
                   (h["side"] == "short_spread" and z_score <= 0.0):
                    p_y = current_prices[y]
                    p_x = current_prices[x]
                    
                    if h["side"] == "long_spread":
                        val = (h["qty_y"] * p_y) - (h["qty_x"] * p_x)
                    else:
                        val = -(h["qty_y"] * p_y) + (h["qty_x"] * p_x)
                        
                    if y in ["BTC-USD", "ETH-USD", "EURUSD=X", "GBPUSD=X"]:
                        val *= fx_rate
                        
                    current_cash += val * (1.0 - TRANSACTION_FEE_RATE)
                    log_transaction(dir_path, today_str, pair_ticker, "SELL", 1.0, val, f"Pairs trading reversion (Z={z_score:.2f})", fee=0.0)
                    action_logs.append(f"SETTLED pair spread {y}/{x} at reversion. Value: ${val:,.2f} MXN.")
                    portfolio["holdings"] = [pos for pos in portfolio["holdings"] if pos["ticker"] != pair_ticker]
            else:
                # entry check
                y_series = np.log(prices[y].iloc[-120:].astype(float))
                x_series = np.log(prices[x].iloc[-120:].astype(float))
                
                try:
                    _, p_val, _ = coint(y_series, x_series)
                    ols_model = sm.OLS(y_series, sm.add_constant(x_series)).fit()
                    beta = ols_model.params[1]
                    mean_spread = (y_series - beta * x_series).mean()
                    std_spread = (y_series - beta * x_series).std()
                    z_score = ((np.log(current_prices[y]) - beta * np.log(current_prices[x])) - mean_spread) / std_spread
                except Exception:
                    p_val = 1.0
                    z_score = 0.0
                    beta = 1.0
                    
                is_coint = p_val < 0.05
                all_evaluations[pair_ticker] = (is_coint, z_score, beta)
                
                if is_coint and abs(z_score) > 2.0:
                    y_ret = prices[y].pct_change().dropna().values
                    vol = calculate_garch_vol(y_ret)
                    
                    kelly_f = (0.55 - 0.45) / (vol ** 2) if vol > 0 else 0.10
                    kelly_f = max(0.02, min(0.15, kelly_f))
                    
                    trade_allocation = portfolio_value * kelly_f
                    if trade_allocation <= current_cash:
                        current_cash -= trade_allocation * (1.0 + TRANSACTION_FEE_RATE)
                        
                        qty_y = trade_allocation / (current_prices[y] * fx_rate)
                        qty_x = (qty_y * beta * current_prices[y]) / current_prices[x]
                        
                        side = "long_spread" if z_score < -2.0 else "short_spread"
                        portfolio["holdings"].append({
                            "ticker": pair_ticker,
                            "side": side,
                            "qty_y": qty_y,
                            "qty_x": qty_x,
                            "buy_price": trade_allocation,
                            "last_price": trade_allocation
                        })
                        log_transaction(dir_path, today_str, pair_ticker, "BUY", 1.0, trade_allocation, f"Stat-Arb Entry (Z={z_score:.2f}, beta={beta:.2f})", fee=trade_allocation * TRANSACTION_FEE_RATE)
                        action_logs.append(f"ENTERED {side.upper()} spread on {y}/{x} at Z={z_score:.2f}.")

    # Save state
    portfolio["cash_balance"] = round(current_cash, 2)
    portfolio["total_capital"] = round(portfolio_value, 2)
    save_portfolio(dir_path, portfolio)

    # 7. Generate markdown report
    report_md = f"""# Strategy 9: AI-Regime Adaptive Statistical Arbitrage Execution Report
**Execution Date:** {now.strftime('%Y-%m-%d %H:%M:%S')} | **Strategy Version:** Upgraded Live V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} MXN
* **Total Cash Balance:** ${current_cash:,.2f} MXN (Parked compounding in Bondia sweep at 6.53% APR)
* **Equity Exposure:** {((portfolio_value - current_cash)/portfolio_value * 100):.1f}%
* **Active Regime:** State {regime} ({regime_reason})

## 2. Current Holdings
| Ticker | Type | Shares/Qty Y | Shares/Qty X | Buy Price/Alloc | Last Price | Market Value (MXN) |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: |
"""
    for h in portfolio["holdings"]:
        t = h["ticker"]
        if t in ["SPY", "GLD"]:
            mkt_val = h["shares"] * h["last_price"]
            report_md += f"| **{t}** | REGIME ASSET | {h['shares']:.4f} | -- | ${h['buy_price']:,.2f} | ${h['last_price']:,.2f} | ${mkt_val:,.2f} |\n"
        else:
            report_md += f"| **{t}** | PAIRS ARB ({h['side'].upper()}) | {h['qty_y']:.6f} | {h['qty_x']:.6f} | ${h['buy_price']:,.2f} | ${h['last_price']:,.2f} | ${h['last_price']:,.2f} |\n"

    report_md += "\n## 3. Today's Execution Logs\n"
    if is_new_month:
        report_md += f"* **[SAVINGS DEPOSIT]** Month transition detected. Credited $2,000.00 MXN savings contribution.\n"
    if accrued_interest > 0:
        report_md += f"* **[INTEREST ACCRUED]** Cash reserves earned $${accrued_interest:,.4f} MXN sweep interest.\n"
    if action_logs:
        for log in action_logs:
            report_md += f"* {log}\n"
    else:
        report_md += "* No trades or rebalancing actions triggered today.\n"

    # Add Diagnostics
    report_md += "\n## 4. Asset Evaluation Diagnostics (Regime & Arbitrage checks)\n"
    report_md += "* **Regime Signal Classifier (HMM on SPY):**\n"
    report_md += f"  * Current Decoded Regime: HMM State {current_state_raw} -> **Regime {regime} ({regime_reason})**\n\n"
    
    if regime == 2:
        report_md += "### Statistical Arbitrage Pairs Cointegration Telemetry:\n"
        report_md += "| Pair | Cointegrated? | Current Z-Score | Hedge Ratio (Beta) | Decision |\n"
        report_md += "| :--- | :---: | :---: | :---: | :--- |\n"
        
        for pair_ticker in ["PAIR:BTC-USD/ETH-USD", "PAIR:EURUSD=X/GBPUSD=X"]:
            y, x = pair_ticker.split("PAIR:")[1].split("/")
            if pair_ticker in all_evaluations:
                is_coint, z_score, beta = all_evaluations[pair_ticker]
                coint_str = "YES" if is_coint else "NO"
                if abs(z_score) > 2.0 and is_coint:
                    decision = "ENTRY TRIGGERED"
                else:
                    decision = "No signal"
                report_md += f"| {y}/{x} | {coint_str} | {z_score:.3f} | {beta:.3f} | {decision} |\n"
                
    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\nExecution complete. Live report written to {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
