import os
import json
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

from skills.liquidity_gatekeeper import calculate_adtv, passes_liquidity_gate
from skills.adaptive_learning import load_learned_params
from agents.agents import FundamentalScreener, MacroRiskAnalyst, PortfolioReconciler
from ingest_live_bmv import BMV_TICKERS, US_TICKERS, fetch_historical_exogenous, fetch_historical_asset

def run_backtest_simulation(starting_capital=20000.0, backtest_days=60, rebalance_freq=15):
    print("=" * 80)
    print(f"STARTINGwalk-forward BACKTEST SIMULATION (LAST {backtest_days} BUSINESS DAYS)")
    print("=" * 80)

    # 1. Fetch exogenous regressors
    df_exog, raw_rate = fetch_historical_exogenous()
    
    # 2. Gather historical data for BMV and US universe
    universe_history = {}
    print("\n[Backtest Ingestion] Ingesting and aligning historical data...")
    for ticker in BMV_TICKERS:
        try:
            hist = fetch_historical_asset(ticker)
            if len(hist) < 200: continue
            hist.index = hist.index.tz_localize(None)
            
            asset_ret = np.log(hist["Close"] / hist["Close"].shift(1)).fillna(0.0)
            
            df_asset = pd.DataFrame({
                "Asset_Price": hist["Close"],
                "Asset_Vol": hist["Volume"],
                "Asset_Ret": asset_ret
            })
            df_aligned = df_asset.join(df_exog, how="right")
            # BUGFIX: .bfill() leaked FUTURE prices into the past (look-ahead bias).
            # Forward-fill only; rows before the ticker's first real quote stay NaN
            # and are excluded from each rebalance lookback below.
            df_aligned["Asset_Price"] = df_aligned["Asset_Price"].ffill()
            df_aligned["Asset_Vol"] = df_aligned["Asset_Vol"].fillna(0.0)
            df_aligned["Asset_Ret"] = df_aligned["Asset_Ret"].fillna(0.0)
            universe_history[ticker] = df_aligned
        except Exception:
            continue
            
    print("Fetching S&P 500 tickers...")
    from skills.index_constituents import get_spx_tickers
    sp500_all = get_spx_tickers()
    
    print(f"Downloading historical data for {len(sp500_all)} S&P 500 components...")
    sp500_data = yf.download(sp500_all, period="5y", progress=False)
    sp500_close = sp500_data["Close"]
    sp500_vol = sp500_data["Volume"]
    
    for ticker in sp500_all:
        try:
            if ticker not in sp500_close.columns or ticker not in sp500_vol.columns:
                continue
            close_col = sp500_close[ticker].dropna()
            vol_col = sp500_vol[ticker].reindex(close_col.index).fillna(0.0)
            if len(close_col) < 200: continue
            
            close_col.index = close_col.index.tz_localize(None)
            vol_col.index = vol_col.index.tz_localize(None)
            
            df_usd = pd.DataFrame({
                "Close_USD": close_col,
                "Volume": vol_col
            }).join(raw_rate, how="inner")
            
            df_usd["Close_MXN"] = df_usd["Close_USD"] * df_usd["USDMXN_Rate"]
            asset_ret_mxn = np.log(df_usd["Close_MXN"] / df_usd["Close_MXN"].shift(1)).fillna(0.0)
            
            df_asset = pd.DataFrame({
                "Asset_Price": df_usd["Close_MXN"],
                "Asset_Vol": df_usd["Volume"],
                "Asset_Ret": asset_ret_mxn,
                "Close_USD": df_usd["Close_USD"],
                "USDMXN_Rate": df_usd["USDMXN_Rate"]
            })
            df_aligned = df_asset.join(df_exog, how="right")
            df_aligned["Asset_Price"] = df_aligned["Asset_Price"].ffill()
            df_aligned["Asset_Vol"] = df_aligned["Asset_Vol"].fillna(0.0)
            df_aligned["Asset_Ret"] = df_aligned["Asset_Ret"].fillna(0.0)
            df_aligned["Close_USD"] = df_aligned["Close_USD"].ffill()
            df_aligned["USDMXN_Rate"] = df_aligned["USDMXN_Rate"].ffill()
            
            universe_history[ticker] = df_aligned
        except Exception:
            continue

    if not universe_history:
        raise ValueError("Failed to ingest any historical data for backtesting.")

    # 3. Find the common aligned timeline for the backtest period
    # Get the dates from one of the exogenous series and select the last N business days
    backtest_dates = df_exog.index[-backtest_days:]
    print(f"Backtest period: {backtest_dates[0].strftime('%Y-%m-%d')} to {backtest_dates[-1].strftime('%Y-%m-%d')}")
    
    # 4. Initialize portfolio balances
    strat_value = starting_capital
    cash = starting_capital
    holdings = {} # Ticker -> Shares
    
    cash_value = starting_capital # Cash benchmark (100% Bondia)
    
    # Buy and hold SPY Benchmark (expressed in MXN)
    # Get SPY MXN price on start date
    spy_history = yf.Ticker("SPY").history(period="5y")
    spy_history.index = spy_history.index.tz_localize(None)
    spy_mxn_series = spy_history["Close"] * raw_rate
    spy_mxn_series = spy_mxn_series.reindex(backtest_dates).ffill()
    if spy_mxn_series.isna().any():
        raise ValueError("SPY benchmark series has gaps at the start of the backtest window.")
    
    # Buy SPY on day 0
    spy_start_price = spy_mxn_series.iloc[0]
    spy_shares = (starting_capital * (1.0 - 0.0029)) / spy_start_price
    
    # Track daily portfolio values (actual NAV with deposits)
    history_dates = []
    history_strat = []
    history_cash_bench = []
    history_spy_bench = []
    
    # Time-Weighted Return (TWR) Tracking
    strategy_last_nav = starting_capital
    cash_last_nav = starting_capital
    spy_last_nav = starting_capital
    
    history_strat_twr = []
    history_cash_twr = []
    history_spy_twr = []
    
    current_strat_twr = 1.0
    current_cash_twr = 1.0
    current_spy_twr = 1.0
    
    # Active screening agents
    screener = FundamentalScreener()
    analyst = MacroRiskAnalyst()
    reconciler = PortfolioReconciler()
    
    total_fees_paid = 0.0
    total_interest_earned = 0.0
    
    # Day-by-day Walk-forward simulation
    for t_idx, current_date in enumerate(backtest_dates):
        # Calculate calendar days since last step to accrue Bondia interest
        if t_idx > 0:
            date_prev = backtest_dates[t_idx - 1]
            calendar_days = (current_date - date_prev).days
        else:
            calendar_days = 1
            
        daily_rate = 0.11 / 360.0
        
        # Accrue interest on cash for active strategy
        interest = cash * daily_rate * calendar_days
        cash += interest
        total_interest_earned += interest
        
        # Accrue interest on Cash Benchmark
        cash_interest = cash_value * daily_rate * calendar_days
        cash_value += cash_interest
        
        # Get prices of holdings on day t before any contribution or rebalance
        stock_value = sum(holdings.get(t, 0.0) * universe_history[t]["Asset_Price"].loc[current_date] for t in holdings if holdings.get(t, 0.0) > 0)
        strat_nav_before = cash + stock_value
        cash_nav_before = cash_value
        spy_nav_before = spy_shares * spy_mxn_series.loc[current_date]
        
        # Update TWR series
        if t_idx > 0:
            r_strat = (strat_nav_before / strategy_last_nav) - 1.0 if strategy_last_nav > 0 else 0.0
            r_cash = (cash_nav_before / cash_last_nav) - 1.0 if cash_last_nav > 0 else 0.0
            r_spy = (spy_nav_before / spy_last_nav) - 1.0 if spy_last_nav > 0 else 0.0
            current_strat_twr *= (1.0 + r_strat)
            current_cash_twr *= (1.0 + r_cash)
            current_spy_twr *= (1.0 + r_spy)
            
        # Apply monthly savings contribution of 2,000 MXN
        is_contribution_day = False
        if t_idx == 0:
            is_contribution_day = True
        else:
            prev_date = backtest_dates[t_idx - 1]
            if current_date.month != prev_date.month:
                is_contribution_day = True
                
        if is_contribution_day:
            cash += 2000.0
            strat_nav_before += 2000.0
            cash_value += 2000.0
            cash_nav_before += 2000.0
            spy_price_t = spy_mxn_series.loc[current_date]
            spy_contribution_shares = (2000.0 * (1.0 - 0.0029)) / spy_price_t
            spy_shares += spy_contribution_shares
            spy_nav_before += 2000.0
            
        # Rebalancing triggers: Day 0, and then every 15 business days
        if t_idx == 0 or t_idx % rebalance_freq == 0:
            # Recompute active portfolio value (including the new cash injection)
            portfolio_value_mxn = cash + sum(holdings.get(t, 0.0) * universe_history[t]["Asset_Price"].loc[current_date] for t in holdings if holdings.get(t, 0.0) > 0)
            print(f"  |-- Walk-Forward Rebalancing on {current_date.strftime('%Y-%m-%d')}... Portfolio Value: {portfolio_value_mxn:.2f}")
            
            # Separate BMV and US tickers
            bmv_tickers = [t for t in universe_history.keys() if t.endswith(".MX")]
            us_tickers = [t for t in universe_history.keys() if not t.endswith(".MX")]
            
            # S&P 500 Pre-filtering for current_date
            us_close_dict = {}
            us_vol_dict = {}
            usdmxn_rate = None
            
            for ticker in us_tickers:
                df = universe_history[ticker]
                df_lb = df.loc[df.index <= current_date]
                if len(df_lb) >= 100:
                    slice_lb = df_lb.iloc[-130:]
                    us_close_dict[ticker] = slice_lb["Close_USD"]
                    us_vol_dict[ticker] = slice_lb["Asset_Vol"]
                    if usdmxn_rate is None and not slice_lb["USDMXN_Rate"].isna().all():
                        usdmxn_rate = float(slice_lb["USDMXN_Rate"].iloc[-1])
            
            if us_close_dict and usdmxn_rate is not None:
                batch_close = pd.DataFrame(us_close_dict)
                batch_volume = pd.DataFrame(us_vol_dict)
                
                from skills.prefilter import prefilter_us_universe
                selected_us = prefilter_us_universe(
                    batch_close=batch_close,
                    batch_volume=batch_volume,
                    usdmxn_rate=usdmxn_rate,
                    portfolio_value_mxn=portfolio_value_mxn
                )
                selected_us_tickers = list(selected_us.keys())
            else:
                selected_us_tickers = []
                
            # Held US positions must ALWAYS reach the deep stage, even if the
            # momentum funnel would cut them — otherwise the reconciler loses
            # signal coverage on open positions (carry-warning territory).
            held_us = {tick for tick in holdings.keys() if not tick.endswith(".MX") and holdings[tick] > 0}
            selected_us_tickers = list(dict.fromkeys(selected_us_tickers + sorted(held_us)))
            candidates = bmv_tickers + selected_us_tickers
            
            # Slice historical lookback data (only up to current_date)
            # This avoids lookahead bias in model training!
            lookback_universe = {}
            for ticker in candidates:
                if ticker not in universe_history:
                    continue
                df_ticker = universe_history[ticker]
                df_lookback = df_ticker.loc[df_ticker.index <= current_date]
                df_lookback = df_lookback.dropna(subset=["Asset_Price"])
                if len(df_lookback) < 50: continue
                
                # Check liquidity gate on lookback data
                prices_30 = df_lookback["Asset_Price"].iloc[-30:].tolist()
                volumes_30 = df_lookback["Asset_Vol"].iloc[-30:].tolist()
                adtv = calculate_adtv(prices_30, volumes_30)
                
                if not passes_liquidity_gate(adtv, threshold=5000000.0):
                    continue
                    
                lookback_universe[ticker] = {
                    "prices": df_lookback["Asset_Price"].values,
                    "volumes": df_lookback["Asset_Vol"].values,
                    "exogenous": df_lookback[["SPY_Ret", "USDMXN_Ret"]].values
                }
                
            # Assemble current portfolio dict
            portfolio_sim = {
                "total_capital": portfolio_value_mxn,
                "cash_balance": cash,
                "holdings": [{"ticker": tick, "shares": sh, "buy_price": universe_history[tick]["Asset_Price"].loc[current_date], "last_price": universe_history[tick]["Asset_Price"].loc[current_date]} for tick, sh in holdings.items() if sh > 0]
            }
            
            # Run quantitative V3 screener + rebalancer
            raw_metrics = screener.screen(lookback_universe, execution_date=current_date)
            adjusted_metrics = analyst.stress_test(raw_metrics, {})
            
            # Load learned parameters (or defaults) and build context
            dir_path = os.path.dirname(os.path.abspath(__file__))
            learned = load_learned_params(dir_path)
            learning_context = {
                "dcs_threshold": 0.15,  # Relaxed for aggressive capital growth
                "vr_threshold": learned["vr_threshold"],
                "confidence": {},
                "exposure_scalar": 1.0,
                "normalize_weights": True,
                "min_fx_scalar": 0.7
            }
            
            # Optimize and calculate weights
            universe_prices_dict = {t: data["prices"] for t, data in lookback_universe.items()}
            updated_portfolio_sim, _, _ = reconciler.reconcile(
                adjusted_metrics, portfolio_sim, current_date.strftime("%Y-%m-%d"),
                learning_context=learning_context,
                universe_prices_dict=universe_prices_dict
            )
            
            # Apply rebalanced holdings to simulation
            new_holdings = {h["ticker"]: h["shares"] for h in updated_portfolio_sim["holdings"]}
            
            # Calculate transaction fees from executed trades
            costo_corretaje = 0.0029
            all_tickers = set(holdings.keys()).union(new_holdings.keys())
            
            step_fees = 0.0
            for ticker in all_tickers:
                old_shares = holdings.get(ticker, 0)
                new_shares = new_holdings.get(ticker, 0)
                if old_shares != new_shares:
                    current_price = universe_history[ticker]["Asset_Price"].loc[current_date]
                    shares_traded = abs(new_shares - old_shares)
                    trade_cost = shares_traded * current_price
                    fee = trade_cost * costo_corretaje
                    step_fees += fee
                    
            cash = updated_portfolio_sim["cash_balance"]
            holdings = new_holdings
            total_fees_paid += step_fees
            print(f"      Rebalanced: Holdings={holdings} | Cash={cash:.2f} MXN | Fees Paid={step_fees:.2f} MXN")

        # Record today's final NAV (after cash injections/rebalance)
        stock_value = sum(holdings.get(t, 0.0) * universe_history[t]["Asset_Price"].loc[current_date] for t in holdings if holdings.get(t, 0.0) > 0)
        strat_value = cash + stock_value
        
        strategy_last_nav = strat_value
        cash_last_nav = cash_value
        spy_last_nav = spy_shares * spy_mxn_series.loc[current_date]
        
        # Record daily history
        history_dates.append(current_date.strftime("%Y-%m-%d"))
        history_strat.append(round(strat_value, 2))
        history_cash_bench.append(round(cash_value, 2))
        
        # SPY benchmark value on day t (less transaction fee at final day to be realistic)
        spy_bench_val = spy_last_nav
        if t_idx == len(backtest_dates) - 1:
            spy_bench_val = spy_bench_val * (1.0 - 0.0029)
        history_spy_bench.append(round(spy_bench_val, 2))
        
        history_strat_twr.append(current_strat_twr)
        history_cash_twr.append(current_cash_twr)
        history_spy_twr.append(current_spy_twr)

    # 5. Compute backtest statistics using Time-Weighted Return (TWR)
    # Convert TWR series to pandas Series
    strat_twr_pd = pd.Series(history_strat_twr, index=backtest_dates)
    cash_twr_pd = pd.Series(history_cash_twr, index=backtest_dates)
    spy_twr_pd = pd.Series(history_spy_twr, index=backtest_dates)
    
    # Compute daily pct changes of the TWR series
    strat_twr_returns = strat_twr_pd.pct_change().dropna()
    cash_twr_returns = cash_twr_pd.pct_change().dropna()
    spy_twr_returns = spy_twr_pd.pct_change().dropna()
    
    # Cumulative TWR returns
    strat_cum_return = (strat_twr_pd.iloc[-1] - 1.0) * 100.0
    cash_cum_return = (cash_twr_pd.iloc[-1] - 1.0) * 100.0
    spy_cum_return = (spy_twr_pd.iloc[-1] - 1.0) * 100.0
    
    # Sharpe ratio (annualized, excess over 11% Bondia rate / 252)
    excess_returns = strat_twr_returns - (0.11 / 252.0)
    sharpe_strat = np.sqrt(252.0) * np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0.0
    
    # Max Drawdowns from TWR cumulative series
    peaks_strat = np.maximum.accumulate(history_strat_twr)
    dd_strat = (np.array(history_strat_twr) - peaks_strat) / peaks_strat
    max_dd_strat = dd_strat.min() * 100.0
    
    # SPY Bench drawdowns
    peaks_spy = np.maximum.accumulate(history_spy_twr)
    dd_spy = (np.array(history_spy_twr) - peaks_spy) / peaks_spy
    max_dd_spy = dd_spy.min() * 100.0
    
    strat_vals = np.array(history_strat)
    cash_vals = np.array(history_cash_bench)
    spy_vals = np.array(history_spy_bench)
    
    # Save backtest report to markdown
    report = []
    report.append("# BACKTEST ANALYSIS REPORT (Hedge Fund Method V4)")
    report.append(f"**Analysis Period:** {backtest_dates[0].strftime('%Y-%m-%d')} to {backtest_dates[-1].strftime('%Y-%m-%d')} ({backtest_days} Business Days)")
    report.append(f"**Starting Capital:** ${starting_capital:,.2f} MXN | **Rebalancing Frequency:** every {rebalance_freq} Business Days\n")
    
    report.append("## 1. Performance Overview Comparison")
    report.append("| Portfolio Strategy | Cumulative Return | Final Capital | Sharpe Ratio | Max Drawdown |")
    report.append("| :--- | :---: | :---: | :---: | :---: |")
    report.append(f"| **V4 Quantitative Strategy** | **{strat_cum_return:+.2f}%** | ${strat_vals[-1]:,.2f} MXN | {sharpe_strat:.2f} | {max_dd_strat:.2f}% |")
    report.append(f"| Bondia Cash Benchmark (11% APR) | {cash_cum_return:+.2f}% | ${cash_vals[-1]:,.2f} MXN | 0.00 | 0.00% |")
    report.append(f"| SPY Buy & Hold Index | {spy_cum_return:+.2f}% | ${spy_vals[-1]:,.2f} MXN | -- | {max_dd_spy:.2f}% |")
    
    report.append("\n## 2. Operational Metrics")
    report.append(f"* **Total Transaction Fees Paid (0.29% rate)**: ${total_fees_paid:,.2f} MXN")
    report.append(f"* **Total Passive Bondia Yield Earned**: ${total_interest_earned:,.2f} MXN")
    report.append(f"* **Active vs. Cash Outperformance**: {strat_cum_return - cash_cum_return:+.2f}%")
    report.append(f"* **Active vs. SPY Outperformance**: {strat_cum_return - spy_cum_return:+.2f}%")
    
    report_markdown = "\n".join(report)
    
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_markdown)
        
    print(f"\n[Backtest] Analysis report saved to: {report_path}")
    
    backtest_data = {
        "dates": history_dates,
        "strategy": [float(x) for x in history_strat],
        "cash": [float(x) for x in history_cash_bench],
        "benchmark": [float(x) for x in history_spy_bench],
        "metrics": {
            "strategy_return": strat_cum_return,
            "cash_return": cash_cum_return,
            "benchmark_return": spy_cum_return,
            "sharpe": sharpe_strat,
            "drawdown": max_dd_strat,
            "fees": total_fees_paid,
            "interest": total_interest_earned
        }
    }
    return backtest_data

if __name__ == "__main__":
    run_backtest_simulation()
