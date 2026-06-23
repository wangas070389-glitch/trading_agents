"""
Live Execution & Paper Trading Script for DCF Alpha-Momentum Concentrated Strategy

Runs daily/monthly to:
  1. Fetch current price data and compute indicators (SMA 100, SMA 20).
  2. Load portfolio state from portfolio.json.
  3. Detect calendar month transitions to inject $2,000 MXN monthly savings.
  4. Perform Active DCA: deploy the $2,000 MXN inflow directly into up-trending undervalued holdings (Close > SMA 20, DCS >= 0.15).
  5. Check if quarterly rebalance is due (or forced via --rebalance flag).
     If yes:
       - Run screener and macro risk analyst.
       - Filter candidates: DCS >= 0.15 and Close > SMA 100.
       - Sort by DCS, select top 5.
       - Compute capped conviction weights (max 30% per stock).
       - Generate rebalancing buy/sell trades, incorporating 0.29% broker fees.
  6. Execute and log trades into portfolio.json and transactions.md.
  7. Generate a detailed markdown execution report: mexican_value_equity_report_live_alpha.md.

Run: python run_live_alpha_growth.py [--rebalance]
"""

import os
import sys
import json
import argparse
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# Local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    """Remove timezone from a DataFrame's DatetimeIndex and normalize to midnight."""
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    df.index = df.index.normalize()
    return df

# Stub out nlp sentiment
import skills.nlp_sentiment as _nlp_module
class _StubNLPEngine:
    def get_black_litterman_adjustments(self, tickers):
        return {t: 0.0 for t in tickers}
_nlp_module.NLPSentimentEngine = _StubNLPEngine

from agents.agents import FundamentalScreener, MacroRiskAnalyst
from ingest_live_bmv import BMV_TICKERS, US_TICKERS
from skills.hybrid_momentum_value import _sma

PORTFOLIO_FILE = "portfolio.json"
TRANSACTIONS_FILE = "transactions.md"
REPORT_FILE = "mexican_value_equity_report_live_alpha.md"
TRANSACTION_COST = 0.0029  # 0.29% broker fee
DCS_ENTRY_THRESHOLD = 0.15
MAX_STOCK_WEIGHT = 0.30
MAX_CONCURRENT_POSITIONS = 5

def load_portfolio(dir_path):
    p_path = os.path.join(dir_path, PORTFOLIO_FILE)
    if not os.path.exists(p_path):
        return {
            "total_capital": 20000.0,
            "cash_balance": 20000.0,
            "holdings": [],
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_rebalance_date": "2000-01-01"
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
    # Create file with headers if it doesn't exist
    if not os.path.exists(t_path):
        with open(t_path, "w", encoding="utf-8") as f:
            f.write("# Transaction Log\n\n| Date | Ticker | Action | Shares | Price | Fee | Net Amount | Note |\n| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |\n")
    
    net_amount = shares * price
    if action in ["BUY", "DCA_BUY", "DEPOSIT"]:
        net_amount = -(net_amount + fee)
    else:
        net_amount = net_amount - fee
        
    with open(t_path, "a", encoding="utf-8") as f:
        f.write(f"| {date_str} | {ticker} | {action} | {shares:.2f} | ${price:.2f} | ${fee:.2f} | ${net_amount:,.2f} | {note} |\n")

def solve_weights(dcs_scores, max_weight=0.30):
    if not dcs_scores:
        return {}
    tickers = list(dcs_scores.keys())
    scores = np.array([dcs_scores[t] for t in tickers])
    raw_weights = scores / np.sum(scores)
    
    weights = {t: raw_weights[i] for i, t in enumerate(tickers)}
    while True:
        capped = False
        excess = 0.0
        uncapped_sum = 0.0
        
        for t, w in weights.items():
            if w > max_weight:
                excess += (w - max_weight)
                weights[t] = max_weight
                capped = True
            else:
                uncapped_sum += w
                
        if not capped or excess <= 1e-6 or uncapped_sum <= 1e-6:
            break
            
        for t, w in weights.items():
            if w < max_weight:
                weights[t] += excess * (w / uncapped_sum)
    return weights

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebalance", action="store_true", help="Force a quarterly rebalancing screener run.")
    args = parser.parse_args()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    print("=" * 80)
    print(f"LIVE EXECUTION: DCF ALPHA-MOMENTUM CONCENTRATED STRATEGY ({today_str})")
    print("=" * 80)

    # 1. Load portfolio state
    portfolio = load_portfolio(dir_path)
    current_cash = portfolio["cash_balance"]
    
    # Map current holdings for lookup
    holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}
    current_equity = sum(h["shares"] * h["last_price"] for h in portfolio["holdings"])
    portfolio_value = current_cash + current_equity

    print(f"Current Cash Reserve: ${current_cash:,.2f} MXN")
    print(f"Current Equities Value: ${current_equity:,.2f} MXN")
    print(f"Total Portfolio Value: ${portfolio_value:,.2f} MXN")
    print()

    # 2. Check for monthly savings contribution
    last_updated_str = portfolio.get("last_updated", "2000-01-01")
    if " " in last_updated_str:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S").date()
    else:
        last_dt = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d").date()

    today = datetime.date.today()
    is_new_month = today.year > last_dt.year or (today.year == last_dt.year and today.month > last_dt.month)

    if is_new_month:
        inflow = 2000.0
        portfolio["cash_balance"] += inflow
        current_cash += inflow
        portfolio["total_capital"] += inflow
        portfolio_value += inflow
        print(f"[Savings Ingestion] New calendar month detected ({last_dt.strftime('%Y-%m')} -> {today.strftime('%Y-%m')}).")
        print(f"  |-- Injected ${inflow:,.2f} MXN monthly savings contribution.")
        log_transaction(dir_path, today_str, "CASH", "DEPOSIT", 1, inflow, "Monthly savings contribution", fee=0.0)

    # 3. Fetch data for universe tickers & Exogenous variables
    print("Downloading universe prices from Yahoo Finance...")
    usdmxn = _strip_tz(yf.Ticker("MXN=X").history(period="5y"))
    if usdmxn.empty:
        print("[ERROR] Failed to fetch USD/MXN rate. Aborting.")
        return
    fx_rate = usdmxn["Close"].iloc[-1]
    print(f"  Current USD/MXN exchange rate: {fx_rate:.4f}")

    spy = _strip_tz(yf.Ticker("SPY").history(period="5y"))
    spy_ret = np.log(spy["Close"] / spy["Close"].shift(1))
    usdmxn_ret = np.log(usdmxn["Close"] / usdmxn["Close"].shift(1))
    exog = pd.DataFrame({"SPY_Ret": spy_ret, "USDMXN_Ret": usdmxn_ret}).dropna()

    universe_data = {}
    ticker_history = {}
    
    # BMV + US universe
    for ticker in BMV_TICKERS + US_TICKERS:
        try:
            hist = _strip_tz(yf.Ticker(ticker).history(period="5y"))
            if hist.empty or len(hist) < 252:
                continue
            
            if ticker in US_TICKERS:
                # Convert price to MXN
                df = pd.DataFrame({"Close": hist["Close"], "Volume": hist["Volume"]}).join(usdmxn["Close"].rename("USDMXN"), how="inner")
                if df.empty or len(df) < 252:
                    continue
                df["Close"] = df["Close"] * df["USDMXN"]
                hist = df[["Close", "Volume"]]
            
            ticker_history[ticker] = hist
            
            # Slice details for screener
            df_aligned = hist[["Close", "Volume"]].rename(columns={"Close": "Price"}).join(exog, how="inner").fillna(0.0)
            universe_data[ticker] = {
                "prices": df_aligned["Price"].values,
                "volumes": df_aligned["Volume"].values,
                "exogenous": df_aligned[["SPY_Ret", "USDMXN_Ret"]].values,
            }
        except Exception as e:
            print(f"  [WARN] Failed to load data for {ticker}: {e}")

    # Compute indicators for held assets (SMA 20 and SMA 100)
    current_prices = {}
    sma_20_values = {}
    sma_100_values = {}

    for ticker, hist in ticker_history.items():
        closes = hist["Close"].values
        current_prices[ticker] = float(closes[-1])
        sma_20_values[ticker] = float(_sma(closes, 20)[-1])
        sma_100_values[ticker] = float(_sma(closes, 100)[-1])

    # 4. Check if rebalancing is due (quarterly = 90 days)
    last_rebalance_str = portfolio.get("last_rebalance_date", "2000-01-01")
    last_rebalance_date = datetime.datetime.strptime(last_rebalance_str, "%Y-%m-%d").date()
    days_since_rebalance = (today - last_rebalance_date).days
    
    should_rebalance = args.rebalance or (days_since_rebalance >= 90)
    print(f"Days since last rebalance: {days_since_rebalance} days.")

    screener = FundamentalScreener()
    analyst = MacroRiskAnalyst()
    adjusted_metrics = {}

    # Run Screener if rebalancing
    if should_rebalance:
        print("\n[Quarterly Rebalance] Running Agent Quantitative Valuation Pipeline...")
        raw_metrics = screener.screen(universe_data, execution_date=today_str)
        adjusted_metrics = analyst.stress_test(raw_metrics, {})
    else:
        # Load previous DCS from existing holdings as stub for report
        adjusted_metrics = {}
        for h in portfolio["holdings"]:
            adjusted_metrics[h["ticker"]] = {
                "current_price": current_prices[h["ticker"]],
                "dcs_adjusted": h["dcs"],
                "garch_vol_adjusted": h["garch_vol"],
                "relative_vol": h.get("vol_relative", 1.0)
            }

    # 5. Process Active DCA deployment on savings inflow
    dca_trades = []
    if is_new_month and portfolio["holdings"]:
        eligible_dca = []
        for h in portfolio["holdings"]:
            ticker = h["ticker"]
            price = current_prices[ticker]
            sma_20 = sma_20_values[ticker]
            dcs = h["dcs"]
            
            if price > sma_20 and dcs >= DCS_ENTRY_THRESHOLD:
                eligible_dca.append((ticker, dcs, price))
                
        if eligible_dca:
            eligible_dca.sort(key=lambda x: x[1], reverse=True)
            top_dca = eligible_dca[:3]
            dca_alloc = inflow / len(top_dca)
            
            print("\n[Active DCA Inflow] Deploying savings contribution into up-trending undervalued holdings:")
            for ticker, dcs_val, price in top_dca:
                shares = int(dca_alloc // price)
                if shares > 0:
                    cost = shares * price
                    fee = cost * TRANSACTION_COST
                    total_cost = cost + fee
                    if total_cost <= portfolio["cash_balance"]:
                        portfolio["cash_balance"] -= total_cost
                        current_cash -= total_cost
                        
                        # Add to holdings
                        for h in portfolio["holdings"]:
                            if h["ticker"] == ticker:
                                h["shares"] += shares
                                h["last_price"] = price
                                break
                        
                        log_transaction(dir_path, today_str, ticker, "DCA_BUY", shares, price, f"Active DCA (DCS={dcs_val:.3f})", fee=fee)
                        dca_trades.append(f"  |-- DCA BUY {shares} shares of {ticker} at ${price:.2f} MXN (DCS={dcs_val:.3f})")
                        print(dca_trades[-1])

    # 6. Execute rebalancing if scheduled
    rebalance_trades = []
    if should_rebalance:
        print("\nExecuting rebalancing optimization...")
        candidates = []
        for t, m in adjusted_metrics.items():
            dcs = m["dcs_adjusted"]
            price = current_prices[t]
            sma_100 = sma_100_values[t]
            
            if dcs >= DCS_ENTRY_THRESHOLD and price > sma_100:
                candidates.append((t, dcs))

        # Sort and take top 5
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:MAX_CONCURRENT_POSITIONS]
        
        # Conviction weight allocation
        target_dcs = {t: dcs for t, dcs in top_candidates}
        target_weights = solve_weights(target_dcs)
        
        full_target_weights = {t: 0.0 for t in BMV_TICKERS + US_TICKERS}
        for t, w in target_weights.items():
            full_target_weights[t] = w

        # Sells
        for h in list(portfolio["holdings"]):
            ticker = h["ticker"]
            target_w = full_target_weights.get(ticker, 0.0)
            curr_val = h["shares"] * current_prices[ticker]
            target_val = portfolio_value * target_w
            
            # Rebalance hysteresis check
            if curr_val > target_val and (curr_val - target_val) > (portfolio_value * 0.05):
                shares_to_sell = (curr_val - target_val) / current_prices[ticker]
                shares_to_sell = min(shares_to_sell, h["shares"])
                if shares_to_sell > 0.01:
                    sell_val = shares_to_sell * current_prices[ticker]
                    fee = sell_val * TRANSACTION_COST
                    portfolio["cash_balance"] += (sell_val - fee)
                    h["shares"] -= shares_to_sell
                    
                    log_transaction(dir_path, today_str, ticker, "SELL", shares_to_sell, current_prices[ticker], f"Quarterly Rebalance (Target weight: {target_w*100:.1f}%)", fee=fee)
                    rebalance_trades.append(f"  |-- SOLD {shares_to_sell:.2f} shares of {ticker} at ${current_prices[ticker]:.2f} MXN (reallocated to weights)")
                    print(rebalance_trades[-1])
                    
        # Remove empty holdings
        portfolio["holdings"] = [h for h in portfolio["holdings"] if h["shares"] > 0]
        holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}

        # Buys
        for t, w in target_weights.items():
            h = holdings_dict.get(t)
            curr_shares = h["shares"] if h else 0.0
            curr_val = curr_shares * current_prices[t]
            target_val = portfolio_value * w
            
            if target_val > curr_val and (target_val - curr_val) > (portfolio_value * 0.05):
                alloc = target_val - curr_val
                price = current_prices[t]
                shares_to_buy = alloc / price
                
                cost = shares_to_buy * price
                fee = cost * TRANSACTION_COST
                total_cost = cost + fee
                if total_cost > portfolio["cash_balance"]:
                    shares_to_buy = portfolio["cash_balance"] / (price * (1.0 + TRANSACTION_COST))
                    cost = shares_to_buy * price
                    fee = cost * TRANSACTION_COST
                    total_cost = cost + fee
                    
                if shares_to_buy > 0.01:
                    portfolio["cash_balance"] -= total_cost
                    if h:
                        h["shares"] += shares_to_buy
                    else:
                        portfolio["holdings"].append({
                            "ticker": t,
                            "shares": shares_to_buy,
                            "buy_price": price,
                            "last_price": price,
                            "target_weight": w,
                            "dcs": adjusted_metrics[t]["dcs_adjusted"],
                            "garch_vol": adjusted_metrics[t]["garch_vol_adjusted"],
                            "vol_relative": adjusted_metrics[t]["relative_vol"],
                            "hmm_state": adjusted_metrics[t].get("hmm_state", 0),
                            "zg_t": adjusted_metrics[t].get("zg_t", 0.0)
                        })
                    log_transaction(dir_path, today_str, t, "BUY", shares_to_buy, price, f"Quarterly Rebalance (Target weight: {w*100:.1f}%)", fee=fee)
                    rebalance_trades.append(f"  |-- BOUGHT {shares_to_buy:.2f} shares of {t} at ${price:.2f} MXN")
                    print(rebalance_trades[-1])

        portfolio["last_rebalance_date"] = today_str
        print("Rebalancing transactions completed.")

    # 7. Update holdings' last prices
    for h in portfolio["holdings"]:
        ticker = h["ticker"]
        if ticker in current_prices:
            h["last_price"] = current_prices[ticker]
            # Update DCS from latest adjusted scores if available
            if ticker in adjusted_metrics and should_rebalance:
                h["dcs"] = adjusted_metrics[ticker]["dcs_adjusted"]
                h["garch_vol"] = adjusted_metrics[ticker]["garch_vol_adjusted"]

    # 8. Save updated portfolio.json
    save_portfolio(dir_path, portfolio)

    # 9. Generate Markdown Execution Report
    print(f"\nWriting execution report to: {REPORT_FILE}...")
    report_markdown = f"""# Alpha-Momentum Concentrated Execution Report (Paper Trading)
**Execution Date:** {today_str} | **Strategy Version:** DCF Alpha-Momentum Concentrated V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} MXN
* **Total Cash Balance:** ${portfolio["cash_balance"]:,.2f} MXN (Compounding in Bondia Cash at 11% APR)
* **Equity Exposure:** {((portfolio_value - portfolio["cash_balance"])/portfolio_value * 100):.1f}%
* **Days Since Last Rebalance:** {(today - datetime.datetime.strptime(portfolio["last_rebalance_date"], "%Y-%m-%d").date()).days} days

## 2. Current Holdings
| Ticker | Shares Held | Last Price | Market Value | Target Weight | DCS Conviction |
| :--- | :---: | :---: | ---: | :---: | :---: |
"""
    for h in portfolio["holdings"]:
        mkt_val = h["shares"] * h["last_price"]
        report_markdown += f"| **{h['ticker']}** | {h['shares']:.2f} | ${h['last_price']:.2f} | ${mkt_val:,.2f} | {h['target_weight']*100:.1f}% | {h['dcs']:.3f} |\n"

    report_markdown += "\n## 3. Today's Execution Logs\n"
    if is_new_month:
        report_markdown += f"* **[SAVINGS DEPOSIT]** Detected calendar month transition. Injected $2,000.00 MXN savings contribution.\n"
    if dca_trades:
        report_markdown += "### Active DCA Allocations:\n"
        for trade in dca_trades:
            report_markdown += f"* {trade.strip()}\n"
    if should_rebalance:
        report_markdown += "### Quarterly Rebalancing Executed:\n"
        for trade in rebalance_trades:
            report_markdown += f"* {trade.strip()}\n"
    if not dca_trades and not rebalance_trades and not is_new_month:
        report_markdown += "* No actions required today. Portfolio matches target weights and cash remains parked in Bondia Cash.\n"

    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report_markdown)

    print("=" * 80)
    print("LIVE PAPER TRADING SUMMARY")
    print("=" * 80)
    print(f"  Date:            {today_str}")
    print(f"  Portfolio NAV:   ${portfolio_value:,.2f} MXN")
    print(f"  Cash Reserve:    ${portfolio['cash_balance']:,.2f} MXN")
    print(f"  Holdings Count:  {len(portfolio['holdings'])}")
    print(f"  Rebalanced:      {'YES (Quarterly)' if should_rebalance else 'NO (Normal Hold)'}")
    if dca_trades:
        print(f"  DCA Applied:     YES ({len(dca_trades)} buys)")
    print(f"  Report Saved:    {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
