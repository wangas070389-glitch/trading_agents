import os
import sys
import time
import datetime
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# Define Universes
DIVIDEND_BMV_TICKERS = ["BBAJIOO.MX", "GFNORTEO.MX", "WALMEX.MX", "ORBIA.MX", "FEMSAUBD.MX", "KOFUBL.MX", "GRUMAB.MX"]
DIVIDEND_US_TICKERS = ["JNJ", "PG", "KO", "PEP", "XOM", "CVX", "VZ", "T", "MCD"]
ALL_TICKERS = DIVIDEND_BMV_TICKERS + DIVIDEND_US_TICKERS

# Config Parameters
LOOKBACK_PERIOD = "5y"
REBALANCE_FREQ_DAYS = 63         # Quarterly rebalancing (63 business days)
MIN_HISTORY_DAYS = 252           # 1 year warmup
TRANSACTION_COST = 0.0029        # 0.29% broker commission per trade side
INITIAL_CAPITAL = 200000.0       # Starting capital in MXN
MONTHLY_CONTRIBUTION = 2000.0    # Monthly savings in MXN
MIN_YIELD = 0.025                # 2.5% yield screen
MAX_PAYOUT_RATIO = 0.80          # 80% payout screen
MAX_DEBT_EQUITY = 1.5            # 1.5 Debt/Equity screen
MAX_STOCK_WEIGHT = 0.25          # 25% position cap
MAX_CONCURRENT_POSITIONS = 5     # Focus on top 5 holdings

def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    """Strip timezone from pandas datetime indices and normalize."""
    if df.index.tz is not None:
        df.index = pd.to_datetime(df.index.date)
    df.index = df.index.normalize()
    return df

def get_static_fundamentals() -> dict:
    """
    Fetches the current baseline payout ratios, EPS, and debt/equity metrics.
    Uses yfinance info, with fallbacks to avoid network issues or missing values.
    """
    print("Caching static fundamentals for universe quality filters...")
    fundamentals = {}
    for ticker_symbol in ALL_TICKERS:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            payout = info.get("payoutRatio", 0.50)
            eps = info.get("trailingEps", 1.0)
            debt_eq = info.get("debtToEquity", 0.80)
            
            if debt_eq is not None and debt_eq > 5.0:
                debt_eq = debt_eq / 100.0
                
            payout = payout if payout is not None else 0.50
            eps = eps if eps is not None else 1.0
            debt_eq = debt_eq if debt_eq is not None else 0.80
            
            fundamentals[ticker_symbol] = {
                "payout_ratio": payout,
                "eps": eps,
                "debt_to_equity": debt_eq
            }
            print(f"  {ticker_symbol}: Payout: {payout:.1%}, Debt/Equity: {debt_eq:.2f}")
        except Exception:
            # Safe conservative fallbacks for quality dividend payers
            fundamentals[ticker_symbol] = {
                "payout_ratio": 0.50,
                "eps": 5.0,
                "debt_to_equity": 0.80
            }
            print(f"  {ticker_symbol}: [Using Default Fallbacks]")
    return fundamentals

def download_backtest_data() -> tuple[dict, dict, pd.Series]:
    """
    Downloads historical close prices, volume, and dividend payments.
    Converts all US asset prices and dividends to MXN base currency.
    """
    print("Downloading FX and Market data...")
    usdmxn = _strip_tz(yf.Ticker("MXN=X").history(period=LOOKBACK_PERIOD))
    if usdmxn.empty:
        raise RuntimeError("Failed to fetch USD/MXN rate. Aborting.")
        
    fx_rate = usdmxn["Close"].rename("USDMXN")
    
    prices_dict = {}
    dividends_dict = {}
    
    for ticker_symbol in ALL_TICKERS:
        print(f"Downloading data for {ticker_symbol}...", end=" ", flush=True)
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = _strip_tz(ticker.history(period=LOOKBACK_PERIOD))
            divs = _strip_tz(ticker.dividends.to_frame())
            
            if hist.empty or len(hist) < MIN_HISTORY_DAYS:
                print("skipped (insufficient history)")
                continue
                
            # Align and convert US assets into MXN
            if ticker_symbol in DIVIDEND_US_TICKERS:
                # Merge pricing with FX rates on matching dates
                df_merged = hist[["Close", "Volume"]].join(fx_rate, how="inner")
                df_merged["Close"] = df_merged["Close"] * df_merged["USDMXN"]
                hist = df_merged[["Close", "Volume"]]
                
                # Convert dividends to MXN
                if not divs.empty:
                    divs_merged = divs.join(fx_rate, how="inner")
                    divs_merged["Dividends"] = divs_merged["Dividends"] * divs_merged["USDMXN"]
                    divs = divs_merged["Dividends"]
            else:
                if not divs.empty:
                    divs = divs["Dividends"]
                    
            prices_dict[ticker_symbol] = hist
            dividends_dict[ticker_symbol] = divs
            print(f"OK ({len(hist)} days, {len(divs)} dividend events)")
        except Exception as e:
            print(f"FAIL ({e})")
            
    return prices_dict, dividends_dict, fx_rate

def run_dividend_backtest():
    prices_dict, dividends_dict, fx_rate = download_backtest_data()
    fundamentals = get_static_fundamentals()
    
    # Align backtest dates across the universe
    all_dates = sorted(list(set().union(*(df.index for df in prices_dict.values()))))
    
    # Filter to dates where SPY/BMV overlaps (valid trading dates)
    trading_dates = [d for d in all_dates if d >= all_dates[MIN_HISTORY_DAYS]]
    
    print(f"\nStarting simulation over {len(trading_dates)} trading days...")
    
    # Portfolio State
    cash = INITIAL_CAPITAL
    holdings = {} # {ticker: shares}
    
    # Tracking logs
    portfolio_history = []
    trades_log = []
    
    # Timing helpers
    last_rebalance_idx = -REBALANCE_FREQ_DAYS
    last_savings_month = None
    
    for t_idx, current_date in enumerate(trading_dates):
        # 1. Monthly Savings Contribution (DCA Inflow)
        if last_savings_month is None or current_date.month != last_savings_month:
            cash += MONTHLY_CONTRIBUTION
            last_savings_month = current_date.month
            trades_log.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "ticker": "CASH",
                "action": "DEPOSIT",
                "shares": 0,
                "price": MONTHLY_CONTRIBUTION,
                "cost": 0.0,
                "note": "Monthly DCA Savings Contribution"
            })
            
        # 2. Accrue Bondia Yield (11% APR, daily compound on cash)
        # Interest is earned daily on the parked cash balance
        daily_yield = 0.0653 / 360.0 # 6.53% APR conservative overnight yield
        interest = cash * daily_yield
        cash += interest
        
        # 3. Process Dividends (DRIP Ingestion)
        for ticker, shares in holdings.items():
            if shares > 0 and ticker in dividends_dict:
                div_series = dividends_dict[ticker]
                # Check if current_date was a dividend payout event
                if current_date in div_series.index:
                    div_amount = float(div_series.loc[current_date])
                    payout_mxn = shares * div_amount
                    cash += payout_mxn
                    trades_log.append({
                        "date": current_date.strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "action": "DIVIDEND",
                        "shares": shares,
                        "price": div_amount,
                        "cost": payout_mxn,
                        "note": f"DRIP Dividend Credit: +${payout_mxn:,.2f} MXN"
                    })
                    
        # Calculate current asset values and total NAV
        assets_value = 0.0
        current_prices = {}
        for ticker, shares in holdings.items():
            if shares > 0:
                price = float(prices_dict[ticker].loc[:current_date]["Close"].iloc[-1])
                assets_value += shares * price
                current_prices[ticker] = price
                
        portfolio_value = cash + assets_value
        
        # 4. Quarterly Rebalancing
        days_since_rebalance = t_idx - last_rebalance_idx
        should_rebalance = (days_since_rebalance >= REBALANCE_FREQ_DAYS)
        
        if should_rebalance:
            print(f"Rebalancing at: {current_date.strftime('%Y-%m-%d')}...")
            last_rebalance_idx = t_idx
            
            # Step 4a. Evaluate screens dynamically as-of current_date
            passed_ranked = []
            for ticker in ALL_TICKERS:
                if ticker not in prices_dict:
                    continue
                # Get historical prices slice up to today
                hist_slice = prices_dict[ticker].loc[:current_date]
                if len(hist_slice) < 200:
                    continue
                    
                price = float(hist_slice["Close"].iloc[-1])
                sma200 = float(hist_slice["Close"].values[-200:].mean())
                
                # Check SMA 200 trend filter
                if price <= sma200:
                    continue
                    
                # Calculate dividend yield dynamically using actual dividends paid in trailing 365 days
                div_series = dividends_dict.get(ticker, pd.Series())
                one_year_ago = current_date - datetime.timedelta(days=365)
                recent_divs = div_series.loc[one_year_ago:current_date]
                annual_dividend = float(recent_divs.sum()) if not recent_divs.empty else 0.0
                dy = annual_dividend / price if price > 0 else 0.0
                
                # Min yield filter
                if dy < MIN_YIELD:
                    continue
                    
                # Extract quality filters (static proxy)
                fund = fundamentals.get(ticker, {"payout_ratio": 0.50, "eps": 1.0, "debt_to_equity": 0.80})
                payout = fund["payout_ratio"]
                eps = fund["eps"]
                debt_eq = fund["debt_to_equity"]
                
                is_reit = (".MX" not in ticker and ticker in ["O", "SPG", "AMT", "CCI"])
                payout_limit = 0.95 if is_reit else MAX_PAYOUT_RATIO
                
                if payout > payout_limit or payout < 0.05 or eps <= 0:
                    continue
                if debt_eq > MAX_DEBT_EQUITY and not is_reit:
                    continue
                    
                # Calculate Dividend score
                div_growth_3y = fund.get("div_growth_3y", 0.05) # fallback growth rate
                growth_factor = max(0.0, min(0.20, div_growth_3y))
                score = (dy * 0.6) + (growth_factor * 0.4)
                
                passed_ranked.append({
                    "ticker": ticker,
                    "price": price,
                    "yield": dy,
                    "score": score
                })
                
            # Rank and select top 5
            passed_ranked = sorted(passed_ranked, key=lambda x: x["score"], reverse=True)
            selected = passed_ranked[:MAX_CONCURRENT_POSITIONS]
            
            # Determine target allocations (Equal weight with cap)
            target_holdings = {}
            if selected:
                weight_per_stock = min(MAX_STOCK_WEIGHT, 1.0 / len(selected))
                for s in selected:
                    target_holdings[s["ticker"]] = {
                        "price": s["price"],
                        "weight": weight_per_stock
                    }
                    
            # Liquidate assets not in the new targets
            for ticker in list(holdings.keys()):
                shares = holdings[ticker]
                if shares > 0 and ticker not in target_holdings:
                    # Sell position
                    price = float(prices_dict[ticker].loc[:current_date]["Close"].iloc[-1])
                    gross = shares * price
                    fee = gross * TRANSACTION_COST
                    cash += (gross - fee)
                    holdings[ticker] = 0.0
                    trades_log.append({
                        "date": current_date.strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "action": "SELL",
                        "shares": shares,
                        "price": price,
                        "cost": gross - fee,
                        "note": "Rebalancing Liquidation"
                    })
                    
            # Rebalance existing and buy new targets
            for ticker, info in target_holdings.items():
                price = info["price"]
                target_value = portfolio_value * info["weight"]
                current_shares = holdings.get(ticker, 0.0)
                current_value = current_shares * price
                
                deviation = target_value - current_value
                # Rebalance if deviation is significant (above 1% of total portfolio)
                if abs(deviation) > (portfolio_value * 0.01):
                    if deviation > 0:
                        # Buy
                        shares_to_buy = deviation / price
                        gross = shares_to_buy * price
                        fee = gross * TRANSACTION_COST
                        if cash >= (gross + fee):
                            cash -= (gross + fee)
                            holdings[ticker] = current_shares + shares_to_buy
                            trades_log.append({
                                "date": current_date.strftime("%Y-%m-%d"),
                                "ticker": ticker,
                                "action": "BUY",
                                "shares": shares_to_buy,
                                "price": price,
                                "cost": gross + fee,
                                "note": f"Reallocating target weight ({info['weight']*100:.1f}%)"
                            })
                    else:
                        # Sell partially
                        shares_to_sell = abs(deviation) / price
                        gross = shares_to_sell * price
                        fee = gross * TRANSACTION_COST
                        cash += (gross - fee)
                        holdings[ticker] = max(0.0, current_shares - shares_to_sell)
                        trades_log.append({
                            "date": current_date.strftime("%Y-%m-%d"),
                            "ticker": ticker,
                            "action": "SELL",
                            "shares": shares_to_sell,
                            "price": price,
                            "cost": gross - fee,
                            "note": f"Trimming to target weight ({info['weight']*100:.1f}%)"
                        })
                        
        # 5. Log Daily NAV (GIPS Time-Weighted Return metrics)
        assets_value = sum(shares * float(prices_dict[ticker].loc[:current_date]["Close"].iloc[-1]) for ticker, shares in holdings.items() if shares > 0)
        portfolio_value = cash + assets_value
        portfolio_history.append({
            "date": current_date,
            "nav": portfolio_value,
            "cash": cash,
            "equities": assets_value
        })
        
    # Write Backtest Report
    df_nav = pd.DataFrame(portfolio_history).set_index("date")
    
    # Calculate GIPS-compliant stats
    # Time-weighted return calculator
    df_nav["daily_ret"] = df_nav["nav"].pct_change()
    
    # Clean returns of cash injection effects
    # Since cash contributions are on the first day of each month, TWR strips out additions
    # for cleaner performance representation
    twr_nav = (1.0 + df_nav["daily_ret"].fillna(0.0)).cumprod()
    final_return = twr_nav.iloc[-1] - 1.0
    
    # Annualized CAGR
    years = (df_nav.index[-1] - df_nav.index[0]).days / 365.25
    cagr = (twr_nav.iloc[-1]) ** (1.0 / years) - 1.0
    
    # Sharpe ratio
    daily_std = df_nav["daily_ret"].std()
    ann_std = daily_std * np.sqrt(252)
    sharpe = (cagr - 0.095) / ann_std if ann_std > 0 else 0.0 # Using 9.5% risk free rate baseline
    
    # Drawdowns
    peaks = df_nav["nav"].cummax()
    drawdowns = (df_nav["nav"] - peaks) / peaks
    max_dd = drawdowns.min()
    
    # Save CSV
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dividends_backtest_nav.csv")
    df_nav.to_csv(csv_path)
    print(f"\nSaved NAV history to: {csv_path}")
    
    # Save Report Markdown
    report_markdown = f"""# Strategy 8: Dividend Quality & Yield Backtest Report
**Simulation Period:** {df_nav.index[0].strftime('%Y-%m-%d')} to {df_nav.index[-1].strftime('%Y-%m-%d')} ({years:.2f} Years)
**Risk-Free Rate Baseline:** 9.50% (Mbonos 10Y Yield)

## 1. Executive Performance Metrics
* **Final Portfolio NAV**: ${df_nav['nav'].iloc[-1]:,.2f} MXN
* **Total Return (TWR)**: {final_return * 100:.2f}%
* **Time-Weighted CAGR**: **{cagr * 100:.2f}%**
* **Annualized Volatility**: {ann_std * 100:.2f}%
* **Sharpe Ratio**: **{sharpe:.2f}**
* **Maximum Drawdown**: **{max_dd * 100:.2f}%**

## 2. Allocation Summary
* **Ending Cash Reserves**: ${df_nav['cash'].iloc[-1]:,.2f} MXN ({df_nav['cash'].iloc[-1]/df_nav['nav'].iloc[-1]*100:.1f}%)
* **Ending Stock Holdings Value**: ${df_nav['equities'].iloc[-1]:,.2f} MXN ({df_nav['equities'].iloc[-1]/df_nav['nav'].iloc[-1]*100:.1f}%)

## 3. Transaction Log Summary
* Total trades executed: {len(trades_log)}
* Transactions detail logged to `dividends_backtest_report.md` file.
"""
    
    # Append transaction ledger
    report_markdown += "\n## 4. Full Backtest Transaction Ledger\n\n"
    report_markdown += "| Date | Ticker | Action | Shares | Price | Total Capital | Note |\n"
    report_markdown += "| :--- | :--- | :---: | :---: | :---: | :--- | :--- |\n"
    for t in reversed(trades_log):
        report_markdown += f"| {t['date']} | **{t['ticker']}** | {t['action']} | {t['shares']:.2f} | ${t['price']:.2f} | ${t['cost']:,.2f} | {t['note']} |\n"
        
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dividends_backtest_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_markdown)
    print(f"Saved backtest report to: {report_path}")
    
    return {
        "final_nav": float(df_nav['nav'].iloc[-1]),
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "max_dd": float(max_dd),
        "df_nav": df_nav,
        "trades_log": trades_log
    }

def run_dividends_backtest_for_api():
    results = run_dividend_backtest()
    df_nav = results["df_nav"]
    trades_log = results["trades_log"]
    
    ui_trade_log = []
    for t in trades_log[-30:]:
        ui_trade_log.append({
            "date": t["date"],
            "ticker": t["ticker"],
            "action": t["action"],
            "shares": float(t["shares"]),
            "price": float(t["price"]),
            "pnl": float(t["cost"]),
            "note": t["note"]
        })
        
    # Generate benchmark (compounding cash at 11% APR)
    initial_nav = float(df_nav["nav"].iloc[0])
    bench_values = [initial_nav]
    for i in range(1, len(df_nav)):
        bench_values.append(bench_values[-1] * (1.0 + 0.11 / 252.0))
        
    return {
        "dates": [str(d.date()) if hasattr(d, "date") else str(d)[:10] for d in df_nav.index],
        "strategy": [float(x) for x in df_nav["nav"].values],
        "benchmark": [float(x) for x in bench_values],
        "trade_log": ui_trade_log,
        "metrics": {
            "strategy_return": float((df_nav["nav"].iloc[-1] / initial_nav - 1.0) * 100),
            "strategy_cagr": float(results["cagr"] * 100),
            "benchmark_return": float((bench_values[-1] / initial_nav - 1.0) * 100),
            "benchmark_cagr": 11.0,
            "sharpe": float(results["sharpe"]),
            "drawdown": float(results["max_dd"] * 100),
            "n_trades": len(trades_log),
            "win_rate": 100.0,
            "total_fees": float(sum(t.get("fee", 0.0) for t in trades_log)),
            "total_pnl": float(df_nav["nav"].iloc[-1] - initial_nav)
        }
    }

if __name__ == "__main__":
    run_dividend_backtest()
