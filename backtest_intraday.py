"""
Intraday Hourly Backtest of trading_agents strategies.
Downloads 1h candles for SPY, NVDA, AAPL, WALMEX.MX, and GFNORTEO.MX.
Simulates hourly trading, session bounds, overnight sweeps, and combined spread/commission fees.
"""

import os
import sys
import time
import datetime
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# Define universe and average half-spreads
INTRADAY_UNIVERSE = ["SPY", "NVDA", "AAPL", "WALMEX.MX", "GFNORTEO.MX"]
SPREADS = {
    "SPY": 0.00005,        # 0.005% half-spread
    "NVDA": 0.0001,        # 0.01% half-spread
    "AAPL": 0.0001,        # 0.01% half-spread
    "WALMEX.MX": 0.0007,   # 0.07% half-spread (higher for MXN local market)
    "GFNORTEO.MX": 0.0009  # 0.09% half-spread
}

COMMISSION = 0.0010        # 0.10% brokerage commission per transaction
INITIAL_CAPITAL = 20000.0  # MXN
BONDIA_APR = 0.0653          # 6.53% APR

def _to_utc_naive(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df

def download_intraday_data() -> tuple[dict, pd.DataFrame]:
    """Download 730d of 1h bar data for universe, plus daily SPY for HMM training."""
    print("Downloading daily SPY historical data for HMM training...")
    spy_daily = yf.download("SPY", period="5y", interval="1d", progress=False)
    spy_daily.index = pd.to_datetime(spy_daily.index).tz_localize(None)
    
    # Calculate daily returns
    spy_daily["Return"] = np.log(spy_daily["Close"] / spy_daily["Close"].shift(1))
    spy_daily = spy_daily.dropna()
    
    print("\nDownloading 1-hour bar data for universe (max 730 days)...")
    intraday_data = {}
    for ticker in INTRADAY_UNIVERSE:
        print(f"  Fetching 1h bars for {ticker}...", end=" ", flush=True)
        try:
            # Download 1h bars
            hist = yf.Ticker(ticker).history(period="730d", interval="1h")
            if hist.empty or len(hist) < 200:
                print(f"skip (insufficient data: {len(hist)} bars)")
                continue
                
            hist = _to_utc_naive(hist)
            
            # If US ticker, convert Close to MXN using daily USD/MXN rate or a fixed rate
            # For simplicity, we can fetch USD/MXN hourly rate if available or fall back to daily.
            # Let's fetch hourly USDMXN rate to be precise!
            intraday_data[ticker] = hist
            print(f"OK ({len(hist)} hourly bars)")
        except Exception as e:
            print(f"FAIL ({e})")
            
    # Download hourly USD/MXN exchange rate to convert US stock prices
    print("  Fetching 1h USD/MXN exchange rate...", end=" ", flush=True)
    try:
        usdmxn_1h = yf.Ticker("MXN=X").history(period="730d", interval="1h")
        usdmxn_1h = _to_utc_naive(usdmxn_1h)
        print(f"OK ({len(usdmxn_1h)} hourly bars)")
    except Exception as e:
        print(f"FAIL ({e}). Using static 17.50 MXN/USD rate.")
        usdmxn_1h = pd.DataFrame()
        
    # Convert US ticker prices to MXN
    for ticker in INTRADAY_UNIVERSE:
        if ticker in intraday_data and not ticker.endswith(".MX"):
            df = intraday_data[ticker]
            if not usdmxn_1h.empty:
                # Align on close timestamps using reindex/ffill
                rate_aligned = usdmxn_1h["Close"].reindex(df.index, method="ffill").fillna(17.50)
            else:
                rate_aligned = pd.Series(17.50, index=df.index)
            df["Close_MXN"] = df["Close"] * rate_aligned
            df["Open_MXN"] = df["Open"] * rate_aligned
            intraday_data[ticker] = df

    return intraday_data, spy_daily

def compute_hourly_macd(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate hourly MACD metrics: MACD line, Signal line, Histogram."""
    close_col = "Close_MXN" if "Close_MXN" in df.columns else "Close"
    
    # 12 and 26 period EMAs
    ema12 = df[close_col].ewm(span=12, adjust=False).mean()
    ema26 = df[close_col].ewm(span=26, adjust=False).mean()
    
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    return df

def run_intraday_backtest():
    print("=" * 80)
    print("STARTING INTRADAY HOURLY BACKTEST (730d WINDOW)")
    print("=" * 80)
    
    intraday_data, spy_daily = download_intraday_data()
    if not intraday_data:
        print("No intraday data available. Aborting.")
        return
        
    # Pre-calculate MACD for all assets
    for ticker in list(intraday_data.keys()):
        intraday_data[ticker] = compute_hourly_macd(intraday_data[ticker])
        
    # Build a unified aligned hourly timeline (union of all hours)
    all_hours = sorted(set().union(*(set(df.index) for df in intraday_data.values())))
    print(f"\nAligned hourly timeline has {len(all_hours)} steps.")
    
    # Track states
    cash = INITIAL_CAPITAL
    shares_held = {t: 0.0 for t in intraday_data}
    history_times = []
    history_strat = []
    
    # Performance tracking metrics
    trade_log = []
    total_commission_paid = 0.0
    total_spread_cost = 0.0
    total_interest_earned = 0.0
    
    # Fit daily SPY HMM for regime overlay to avoid lookahead bias
    from hmmlearn import hmm
    
    current_day_str = ""
    spy_hmm_state = 0  # Default to Sideways
    max_equity_exposure = 0.50
    
    # Step hour-by-hour through the aligned timeline
    for step_idx, current_time in enumerate(all_hours):
        current_date_str = current_time.strftime("%Y-%m-%d")
        
        # 1. Accrue Bondia overnight interest on cash balance when date changes
        if step_idx > 0:
            prev_time = all_hours[step_idx - 1]
            if prev_time.date() != current_time.date():
                days_diff = (current_time.date() - prev_time.date()).days
                daily_rate = BONDIA_APR / 360.0
                interest = cash * daily_rate * days_diff
                cash += interest
                total_interest_earned += interest
                
        # 2. Daily Recalibration (at the start of each new trading day)
        if current_date_str != current_day_str:
            current_day_str = current_date_str
            # Train HMM on SPY daily history up to the previous day
            spy_history_slice = spy_daily.loc[spy_daily.index < pd.to_datetime(current_date_str)]
            if len(spy_history_slice) >= 100:
                try:
                    obs = spy_history_slice["Return"].values.reshape(-1, 1)
                    model_spy = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=50, random_state=42)
                    model_spy.fit(obs)
                    states = model_spy.predict(obs)
                    
                    means = model_spy.means_[:, 0]
                    bear_idx = np.argmin(means)
                    bull_idx = np.argmax(means)
                    sideways_idx = [idx for idx in range(3) if idx not in (bear_idx, bull_idx)][0]
                    
                    state_map = {bear_idx: -1, bull_idx: 1, sideways_idx: 0}
                    spy_hmm_state = state_map[states[-1]]
                except Exception:
                    pass  # Keep previous HMM state on failure
                    
            # Set target exposure bounds based on HMM state
            if spy_hmm_state == 1:
                max_equity_exposure = 0.95  # Bull
            elif spy_hmm_state == -1:
                max_equity_exposure = 0.10  # Bear
            else:
                max_equity_exposure = 0.50  # Sideways
                
        # 3. Strategy Logic (run every hour)
        # Determine signals for each asset
        signals = {}
        for ticker, df in intraday_data.items():
            if current_time in df.index:
                row = df.loc[current_time]
                macd = row["MACD"]
                signal = row["Signal"]
                hist = row["Hist"]
                
                # Signal is bullish if MACD is above Signal, bearish if below
                signals[ticker] = 1.0 if macd > signal else -1.0
                
        # Check active holds value to calculate current NAV
        current_nav = cash
        for ticker, shares in shares_held.items():
            if shares > 0.0:
                df = intraday_data[ticker]
                price = df.loc[current_time]["Close_MXN" if "Close_MXN" in df.columns else "Close"] if current_time in df.index else df["Close"].iloc[0]
                current_nav += shares * price
                
        # Re-allocate portfolio target weights based on signals
        bullish_assets = [t for t, s in signals.items() if s > 0.0]
        
        # Sizing: Equal weight among active bullish assets, capped by max equity exposure
        target_weights = {t: 0.0 for t in intraday_data}
        if bullish_assets:
            weight_per_asset = max_equity_exposure / len(bullish_assets)
            # Limit individual position cap to 30% for risk diversification
            weight_per_asset = min(0.30, weight_per_asset)
            for t in bullish_assets:
                target_weights[t] = weight_per_asset
                
        # Execute Trades
        for ticker in intraday_data:
            df = intraday_data[ticker]
            if current_time not in df.index:
                continue
                
            close_col = "Close_MXN" if "Close_MXN" in df.columns else "Close"
            close_price = df.loc[current_time][close_col]
            
            target_w = target_weights[ticker]
            current_w = (shares_held[ticker] * close_price) / current_nav if current_nav > 0 else 0.0
            
            # Simple dead-zone threshold of 3% to reduce transaction churn
            if abs(target_w - current_w) > 0.03:
                target_value = current_nav * target_w
                current_value = shares_held[ticker] * close_price
                trade_value = target_value - current_value
                
                half_spread = SPREADS.get(ticker, 0.0001)
                
                if trade_value > 0.0:
                    # BUY
                    exec_price = close_price * (1.0 + half_spread)
                    commission_cost = trade_value * COMMISSION
                    spread_cost = trade_value * half_spread
                    
                    shares_to_buy = (trade_value - commission_cost) / exec_price
                    if cash >= (shares_to_buy * exec_price + commission_cost):
                        shares_held[ticker] += shares_to_buy
                        cash -= (shares_to_buy * exec_price + commission_cost)
                        total_commission_paid += commission_cost
                        total_spread_cost += spread_cost
                        trade_log.append({
                            "time": current_time,
                            "ticker": ticker,
                            "type": "BUY",
                            "shares": shares_to_buy,
                            "price": exec_price,
                            "value": trade_value
                        })
                elif trade_value < 0.0 and shares_held[ticker] > 0.0:
                    # SELL
                    exec_price = close_price * (1.0 - half_spread)
                    shares_to_sell = min(shares_held[ticker], -trade_value / exec_price)
                    sell_proceeds = shares_to_sell * exec_price
                    commission_cost = sell_proceeds * COMMISSION
                    spread_cost = sell_proceeds * half_spread
                    
                    shares_held[ticker] -= shares_to_sell
                    cash += (sell_proceeds - commission_cost)
                    total_commission_paid += commission_cost
                    total_spread_cost += spread_cost
                    trade_log.append({
                        "time": current_time,
                        "ticker": ticker,
                        "type": "SELL",
                        "shares": shares_to_sell,
                        "price": exec_price,
                        "value": sell_proceeds
                    })
                    
        # Record hourly history
        history_times.append(current_time)
        history_strat.append(current_nav)

    # 4. Final Performance Analysis
    strat_series = pd.Series(history_strat, index=history_times)
    total_return = strat_series.iloc[-1] / INITIAL_CAPITAL - 1.0
    days = (strat_series.index[-1] - strat_series.index[0]).days
    years = max(days / 365.25, 0.01)
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0
    
    # Calculate Sharpe Ratio
    hourly_returns = strat_series.pct_change().dropna()
    excess_returns = hourly_returns - ((BONDIA_APR / 360.0) / 7.0) # Approx 7 trading hours per day
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252 * 7)) if excess_returns.std() > 0 else 0.0
    
    # Calculate Drawdown
    cumulative = (1.0 + hourly_returns).cumprod()
    max_dd = (cumulative / cumulative.cummax() - 1.0).min()
    
    # Save Report
    report_path = "intraday_backtest_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Intraday Hourly Backtest Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Setup\n\n")
        f.write(f"- Universe: {', '.join(INTRADAY_UNIVERSE)}\n")
        f.write(f"- Interval: 1-Hour bars\n")
        f.write(f"- Backtest period: {strat_series.index[0]} to {strat_series.index[-1]}\n")
        f.write(f"- Brokerage Commission: {COMMISSION*100:.2f}%\n")
        f.write("- Bid-Ask Spread Modeling: **Active (variable half-spread per asset)**\n")
        f.write(f"- Initial Capital: ${INITIAL_CAPITAL:,.2f} MXN\n")
        f.write(f"- Bondia Yield Sweep: {BONDIA_APR*100:.1f}% APR overnight sweep active\n\n")
        
        f.write("## Results\n\n")
        f.write("| Metric | Hourly Intraday Strategy |\n")
        f.write("| :--- | ---: |\n")
        f.write(f"| Total Return | {total_return*100:+.2f}% |\n")
        f.write(f"| CAGR | {cagr*100:+.2f}% |\n")
        f.write(f"| Sharpe (annualized) | {sharpe:.2f} |\n")
        f.write(f"| Max Drawdown | {max_dd*100:.2f}% |\n")
        f.write(f"| Final NAV | ${strat_series.iloc[-1]:,.2f} MXN |\n\n")
        
        f.write("## Activity & Costs\n\n")
        f.write(f"- Total executed trades: {len(trade_log)}\n")
        f.write(f"- Total brokerage commissions paid: ${total_commission_paid:,.2f} MXN\n")
        f.write(f"- Total bid-ask spread costs incurred: ${total_spread_cost:,.2f} MXN\n")
        f.write(f"- Total interest yield earned (Bondia): ${total_interest_earned:,.2f} MXN\n")
        
    print(f"\nIntraday Backtest Completed. Report saved to: {report_path}")
    print(f"CAGR: {cagr*100:+.2f}% | Sharpe: {sharpe:.2f} | MaxDD: {max_dd*100:.2f}%")

if __name__ == "__main__":
    run_intraday_backtest()
