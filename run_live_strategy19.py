"""
LIVE EXECUTION: STRATEGY 19 PARTICLE FILTER SYSTEMATIC QQQ / TQQQ / SQQQ
========================================================================
Runs daily to evaluate the Particle Filter model on QQQ returns and execute
capital transitions between QQQ, TQQQ, SQQQ, and Cash.
"""
import os
import sys
import json
import argparse
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# Local settings
PORTFOLIO_FILE = "portfolio_strategy19.json"
TRANSACTIONS_FILE = "transactions_strategy19.md"
REPORT_FILE = "strategy19_report_live.md"

TRANSACTION_COST = 0.0029  # 0.29% GBM broker fee (spread + commission + VAT)
BONDIA_YIELD = 0.0653      # 6.53% MXN cash sweep compound yield
VOL_LIMIT = 0.015          # 1.5% daily volatility threshold (~23.8% annualized)

class ParticleFilter:
    def __init__(self, n_particles=1000, sigma_mu=0.0002, sigma_sigma=0.05,
                 sigma_min=0.003, sigma_max=0.05, mu_min=-0.01, mu_max=0.01,
                 init_mu=0.0005, init_mu_std=0.001, seed=42):
        self.n_particles = n_particles
        self.sigma_mu = sigma_mu
        self.sigma_sigma = sigma_sigma
        self.sigma_min = sigma_min
        self.sigma_max = sigma_max
        self.mu_min = mu_min
        self.mu_max = mu_max
        self.rng = np.random.default_rng(seed)
        
        self.particles_mu = self.rng.normal(init_mu, init_mu_std, n_particles)
        self.particles_sigma = self.rng.uniform(sigma_min, sigma_max, n_particles)
        self.weights = np.ones(n_particles) / n_particles

    def predict(self):
        noise_mu = self.rng.normal(0, self.sigma_mu, self.n_particles)
        self.particles_mu = np.clip(self.particles_mu + noise_mu, self.mu_min, self.mu_max)
        
        noise_sigma = self.rng.normal(0, self.sigma_sigma, self.n_particles)
        self.particles_sigma = np.clip(self.particles_sigma * np.exp(noise_sigma), self.sigma_min, self.sigma_max)

    def update(self, return_val):
        diff = return_val - self.particles_mu
        likelihood = (1.0 / self.particles_sigma) * np.exp(-0.5 * (diff / self.particles_sigma) ** 2)
        likelihood = np.maximum(likelihood, 1e-15)
        
        self.weights *= likelihood
        sum_w = np.sum(self.weights)
        if sum_w > 0:
            self.weights /= sum_w
        else:
            self.weights = np.ones(self.n_particles) / self.n_particles

    def resample(self):
        neff = 1.0 / np.sum(self.weights ** 2)
        if neff < self.n_particles / 2.0:
            cumulative_sum = np.cumsum(self.weights)
            cumulative_sum[-1] = 1.0
            u = (self.rng.uniform(0, 1.0) + np.arange(self.n_particles)) / self.n_particles
            indexes = np.searchsorted(cumulative_sum, u)
            
            self.particles_mu = self.particles_mu[indexes]
            self.particles_sigma = self.particles_sigma[indexes]
            self.weights = np.ones(self.n_particles) / self.n_particles

    def get_estimates(self):
        est_mu = np.sum(self.particles_mu * self.weights)
        est_sigma = np.sum(self.particles_sigma * self.weights)
        prob_bull = np.sum(self.weights[self.particles_mu > 0])
        return est_mu, est_sigma, prob_bull

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
        content = f"# Strategy 19: Particle Filter systematic Transaction Ledger\n\n| Date | Ticker | Action | Shares | Price | Net Capital Impact | Order Type | Status | Note |\n| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- |\n---\n"
        
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
    print(f"LIVE EXECUTION: STRATEGY 19 PARTICLE FILTER SYSTEMATIC ({today_str})")
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

    # 3. Fetch FX rate and tickers
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

    # 5. Fetch QQQ history and run Particle Filter
    print("\nLoading trailing QQQ daily return series...")
    try:
        qqq_history = yf.download("QQQ", period="300d", progress=False)
        if isinstance(qqq_history.columns, pd.MultiIndex):
            qqq_history.columns = [c[0] for c in qqq_history.columns]
        
        qqq_closes = qqq_history["Close"].dropna()
        log_rets = np.log(qqq_closes / qqq_closes.shift(1)).dropna().values
        
        # We need the last 250 returns
        log_rets = log_rets[-250:]
        
        # Initialize and run PF sequentially
        pf = ParticleFilter(n_particles=1000, seed=42)
        for val in log_rets:
            pf.predict()
            pf.update(val)
            pf.resample()
            
        est_mu, est_sigma, prob_bull = pf.get_estimates()
        print(f"Particle Filter Estimates:")
        print(f"  Estimated expected return (drift): {est_mu * 252 * 100:+.2f}% annualized")
        print(f"  Estimated volatility: {est_sigma * np.sqrt(252) * 100:.2f}% annualized")
        print(f"  Probability of Bull Regime (p_t): {prob_bull * 100:.1f}%")
    except Exception as e:
        print(f"Error executing Particle Filter engine: {e}. Defaulting to conservative state.")
        est_mu = 0.0
        est_sigma = 0.02
        prob_bull = 0.50

    # 6. Evaluate target position
    target_asset_name = "CASH"
    
    if est_sigma > VOL_LIMIT:
        # High Volatility Regime: Leverage Disabled
        if current_asset_name == "QQQ":
            target_asset_name = "QQQ" if prob_bull > 0.51 else "CASH"
        else:
            target_asset_name = "QQQ" if prob_bull > 0.58 else "CASH"
    else:
        # Normal Volatility Regime: Leverage Enabled
        if current_asset_name == "TQQQ":
            target_asset_name = "TQQQ" if prob_bull > 0.52 else "CASH"
        elif current_asset_name == "SQQQ":
            target_asset_name = "SQQQ" if prob_bull < 0.48 else "CASH"
        else:
            if prob_bull > 0.60:
                target_asset_name = "TQQQ"
            elif prob_bull < 0.40:
                target_asset_name = "SQQQ"
            else:
                target_asset_name = "CASH"

    print(f"Decision: Current Asset = {current_asset_name} | Target Asset = {target_asset_name}")

    # 7. Execute asset transition trades
    trade_executed = False
    rebalance_logs = []
    
    if target_asset_name != current_asset_name:
        trade_executed = True
        print(f"\nExecuting portfolio transition from {current_asset_name} to {target_asset_name}...")
        
        # Step A: Liquidate existing holdings
        if held_ticker:
            px_usd = current_prices[held_ticker]
            gross_usd = held_shares * px_usd
            gross_mxn = gross_usd * fx_rate
            fee_mxn = gross_mxn * TRANSACTION_COST
            current_cash = round(current_cash + (gross_mxn - fee_mxn), 2)
            portfolio["cash_balance"] = current_cash
            portfolio["holdings"] = []
            
            rebalance_logs.append(f"  |-- SOLD {held_shares:.4f} shares of {held_ticker} at ${px_usd:.2f} USD (${gross_mxn:,.2f} MXN) | Fee: ${fee_mxn:,.2f} MXN")
            print(rebalance_logs[-1])
            if not args.dry_run:
                px_mxn = px_usd * fx_rate
                log_transaction(dir_path, today_str, held_ticker, "SELL", held_shares, px_mxn, f"PF switch to {target_asset_name}", fee=fee_mxn)
                
        # Step B: Purchase target holdings
        if target_asset_name != "CASH":
            px_usd = current_prices[target_asset_name]
            px_mxn = px_usd * fx_rate
            
            # Substract fee on the buy allocation
            invest_mxn = current_cash
            fee_mxn = invest_mxn * TRANSACTION_COST
            net_invest_mxn = invest_mxn - fee_mxn
            
            shares_to_buy = net_invest_mxn / px_mxn
            if shares_to_buy > 0.0001:
                current_cash = 0.0  # Fully invested
                portfolio["cash_balance"] = 0.0
                portfolio["holdings"] = [{
                    "ticker": target_asset_name,
                    "shares": shares_to_buy,
                    "buy_price": px_usd * fx_rate,
                    "last_price": px_usd * fx_rate,
                    "target_weight": 1.0
                }]
                rebalance_logs.append(f"  |-- BOUGHT {shares_to_buy:.4f} shares of {target_asset_name} at ${px_usd:.2f} USD (${net_invest_mxn:,.2f} MXN) | Fee: ${fee_mxn:,.2f} MXN")
                print(rebalance_logs[-1])
                if not args.dry_run:
                    log_transaction(dir_path, today_str, target_asset_name, "BUY", shares_to_buy, px_mxn, f"PF systematic entry", fee=fee_mxn)
            else:
                print("Insufficient cash to execute purchase.")

    # 8. Update final portfolio NAV
    holdings_val_mxn = 0.0
    for h in portfolio.get("holdings", []):
        holdings_val_mxn = h["shares"] * h["last_price"]
        
    portfolio_value = current_cash + holdings_val_mxn
    portfolio["total_capital"] = portfolio_value
    portfolio["last_updated"] = now_str
    
    if not args.dry_run:
        save_portfolio(dir_path, portfolio)
        print("Portfolio state written to disk.")

    # 9. Generate Live execution markdown report
    report_md = f"""# Strategy 19: Particle Filter QQQ / TQQQ / SQQQ Live Execution Report
**Execution Timestamp:** {now_str} | **Strategy Version:** Live V1

## 1. Portfolio Summary
* **Total Portfolio NAV:** ${portfolio_value:,.2f} MXN
* **Total Cash sweep Balance:** ${current_cash:,.2f} MXN (Parked in Bondia compound at 6.53% APR)
* **Equity Exposure:** {((portfolio_value - current_cash) / portfolio_value * 100):.1f}%
* **Asset Allocation Target:** {target_asset_name}
* **USD/MXN Exchange Rate:** {fx_rate:.4f}

## 2. Current Holdings
| Ticker | Shares Held | Buy Price (USD) | Last Price (USD) | Market Value (USD) | Market Value (MXN) | Target Weight |
| :--- | :---: | :---: | :---: | ---: | ---: | :---: |
"""
    for h in portfolio.get("holdings", []):
        buy_usd = h["buy_price"] / fx_rate if fx_rate > 0 else h["buy_price"]
        last_usd = h["last_price"] / fx_rate if fx_rate > 0 else h["last_price"]
        val_usd = h["shares"] * last_usd
        val_mxn = h["shares"] * h["last_price"]
        report_md += f"| **{h['ticker']}** | {h['shares']:.4f} | ${buy_usd:.2f} | ${last_usd:.2f} | ${val_usd:,.2f} | ${val_mxn:,.2f} | 100.0% |\n"
    if not portfolio.get("holdings"):
        report_md += "| **CASH** | - | - | - | $0.00 | $0.00 | 100.0% |\n"

    report_md += "\n## 3. Sequential Monte Carlo (SMC) Estimates\n"
    report_md += rf"* **Latent Drift (Posterior $\hat{{\mu}}_t$):** {est_mu * 252 * 100:+.2f}% annualized\n"
    report_md += rf"* **Latent Volatility (Posterior $\hat{{\sigma}}_t$):** {est_sigma * np.sqrt(252) * 100:.2f}% annualized\n"
    report_md += rf"* **Probability of Bull Regime ($P(\mu_t > 0)$):** {prob_bull * 100:.1f}%\n"
    report_md += f"* **Volatility Drag Regime:** {'HIGH VOLATILITY (Leverage Disabled)' if est_sigma > VOL_LIMIT else 'NORMAL VOLATILITY (Leverage Enabled)'}\n"

    report_md += "\n## 4. Today's Execution Logs\n"
    if accrued_interest > 0:
        report_md += f"* **[INTEREST]** Cash sweep accrued yield of ${accrued_interest:,.4f} MXN.\n"
    if trade_executed:
        report_md += "### Transition Trades Executed:\n"
        for log_line in rebalance_logs:
            report_md += f"* {log_line.strip()}\n"
    else:
        report_md += f"* Hold current position in **{current_asset_name}**; no transition trades required.\n"

    with open(os.path.join(dir_path, REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print("=" * 80)
    print("LIVE PAPER TRADING SUMMARY - STRATEGY 19")
    print("=" * 80)
    print(f"  NAV:             ${portfolio_value:,.2f} MXN")
    print(f"  Holding Target:  {target_asset_name}")
    print(f"  Regime Bullish%: {prob_bull*100:.1f}%")
    print(f"  Execution logs:  {REPORT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
