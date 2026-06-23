"""
Expanded Intraday Backtest of trading_agents strategies on 10 US and 10 BMV assets.
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

# Define expanded universe (10 US and 10 BMV assets)
EXPANDED_UNIVERSE = [
    # US (10 assets)
    "SPY", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST",
    # BMV (10 assets)
    "AMXB.MX", "FEMSAUBD.MX", "WALMEX.MX", "GFNORTEO.MX", "GMEXICOB.MX", 
    "CEMEXCPO.MX", "BIMBOA.MX", "GAPB.MX", "ASURB.MX", "AC.MX"
]

SPREADS = {
    # US
    "SPY": 0.00005,
    "AAPL": 0.0001,
    "MSFT": 0.0001,
    "NVDA": 0.0001,
    "AMZN": 0.0001,
    "GOOGL": 0.0001,
    "META": 0.0001,
    "TSLA": 0.00015,
    "AVGO": 0.00015,
    "COST": 0.0001,
    # BMV
    "AMXB.MX": 0.0006,
    "FEMSAUBD.MX": 0.0007,
    "WALMEX.MX": 0.0007,
    "GFNORTEO.MX": 0.0009,
    "GMEXICOB.MX": 0.0009,
    "CEMEXCPO.MX": 0.0010,
    "BIMBOA.MX": 0.0011,
    "GAPB.MX": 0.0012,
    "ASURB.MX": 0.0012,
    "AC.MX": 0.0010
}

COMMISSION = 0.0010        # 0.10% brokerage commission
INITIAL_CAPITAL = 20000.0  # MXN
BONDIA_APR = 0.0653          # 6.53% APR

def _to_utc_naive(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df

def download_data() -> tuple[dict, pd.DataFrame]:
    print("Downloading daily SPY historical data for HMM training...")
    spy_daily = yf.download("SPY", period="5y", interval="1d", progress=False)
    spy_daily.index = pd.to_datetime(spy_daily.index).tz_localize(None)
    spy_daily["Return"] = np.log(spy_daily["Close"] / spy_daily["Close"].shift(1))
    spy_daily = spy_daily.dropna()
    
    print("\nDownloading 1-hour bar data for expanded universe (max 730 days)...")
    intraday_data = {}
    for ticker in EXPANDED_UNIVERSE:
        print(f"  Fetching 1h bars for {ticker}...", end=" ", flush=True)
        try:
            hist = yf.Ticker(ticker).history(period="730d", interval="1h")
            if hist.empty or len(hist) < 200:
                print(f"skip (insufficient data: {len(hist)} bars)")
                continue
            hist = _to_utc_naive(hist)
            intraday_data[ticker] = hist
            print(f"OK ({len(hist)} hourly bars)")
        except Exception as e:
            print(f"FAIL ({e})")
            
    print("  Fetching 1h USD/MXN exchange rate...", end=" ", flush=True)
    try:
        usdmxn_1h = yf.Ticker("MXN=X").history(period="730d", interval="1h")
        usdmxn_1h = _to_utc_naive(usdmxn_1h)
        print(f"OK ({len(usdmxn_1h)} hourly bars)")
    except Exception as e:
        print(f"FAIL ({e}). Using static 17.50 MXN/USD rate.")
        usdmxn_1h = pd.DataFrame()
        
    for ticker in EXPANDED_UNIVERSE:
        if ticker in intraday_data and not ticker.endswith(".MX"):
            df = intraday_data[ticker]
            if not usdmxn_1h.empty:
                rate_aligned = usdmxn_1h["Close"].reindex(df.index, method="ffill").fillna(17.50)
            else:
                rate_aligned = pd.Series(17.50, index=df.index)
            df["Close_MXN"] = df["Close"] * rate_aligned
            df["Open_MXN"] = df["Open"] * rate_aligned
            intraday_data[ticker] = df
        elif ticker in intraday_data:
            df = intraday_data[ticker]
            df["Close_MXN"] = df["Close"]
            df["Open_MXN"] = df["Open"]
            intraday_data[ticker] = df

    return intraday_data, spy_daily

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close_col = "Close_MXN" if "Close_MXN" in df.columns else "Close"
    # MACD
    ema12 = df[close_col].ewm(span=12, adjust=False).mean()
    ema26 = df[close_col].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    # 50 SMA
    df["SMA50"] = df[close_col].rolling(window=50).mean()
    return df

def run_simulation(intraday_data, spy_daily, timeframe="4h", dead_zone=0.10, use_filters=True):
    # Precompute SPY HMM
    from hmmlearn import hmm
    print("\n[HMM Setup] Pre-calculating HMM daily regimes...")
    all_times = sorted(set().union(*(set(df.index) for df in intraday_data.values())))
    target_dates = sorted(list(set(pd.to_datetime(t.date()) for t in all_times)))
    
    hmm_states = {}
    last_state = 0
    for i, date in enumerate(target_dates):
        date_str = date.strftime("%Y-%m-%d")
        if i % 5 == 0 or i == 0 or not hmm_states:
            spy_history_slice = spy_daily.loc[spy_daily.index < date]
            if len(spy_history_slice) >= 100:
                try:
                    obs = spy_history_slice["Return"].values.reshape(-1, 1)
                    model_spy = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=15, random_state=42)
                    model_spy.fit(obs)
                    states = model_spy.predict(obs)
                    means = model_spy.means_[:, 0]
                    state_map = {np.argmin(means): -1, np.argmax(means): 1}
                    for idx in range(3):
                        if idx not in state_map:
                            state_map[idx] = 0
                    last_state = state_map[states[-1]]
                except Exception:
                    pass
            else:
                last_state = 0
        hmm_states[date_str] = last_state

    print("Resampling and calculating signals...")
    processed_data = {}
    for ticker, df in intraday_data.items():
        if timeframe != "1h":
            resampled = df.resample(timeframe).agg({
                "Open_MXN": "first",
                "Close_MXN": "last"
            }).dropna()
        else:
            resampled = df.copy()
        
        resampled = calculate_indicators(resampled).dropna()
        processed_data[ticker] = resampled

    # Aligned timelines
    timeline = sorted(set().union(*(set(df.index) for df in processed_data.values())))
    
    cash = INITIAL_CAPITAL
    shares_held = {t: 0.0 for t in processed_data}
    history_nav = []
    history_times = []
    
    current_day_str = ""
    spy_hmm_state = 0
    max_equity_exposure = 0.50
    
    trade_count = 0
    total_commission = 0.0
    total_spread_cost = 0.0
    total_interest = 0.0
    
    for step_idx, current_time in enumerate(timeline):
        current_date_str = current_time.strftime("%Y-%m-%d")
        
        # Interest
        if step_idx > 0:
            prev_time = timeline[step_idx - 1]
            if prev_time.date() != current_time.date():
                days_diff = (current_time.date() - prev_time.date()).days
                interest = cash * (BONDIA_APR / 360.0) * days_diff
                cash += interest
                total_interest += interest
                
        # HMM Regime
        if current_date_str != current_day_str:
            current_day_str = current_date_str
            spy_hmm_state = hmm_states.get(current_date_str, 0)
            if spy_hmm_state == 1:
                max_equity_exposure = 0.95
            elif spy_hmm_state == -1:
                max_equity_exposure = 0.10
            else:
                max_equity_exposure = 0.50
                
        # Signals
        signals = {}
        for ticker, df in processed_data.items():
            if current_time in df.index:
                row = df.loc[current_time]
                macd_val = row["MACD"]
                sig_val = row["Signal"]
                close_price = row["Close_MXN"]
                sma50 = row["SMA50"]
                
                is_bullish = macd_val > sig_val
                if use_filters and close_price < sma50:
                    is_bullish = False
                signals[ticker] = 1.0 if is_bullish else -1.0
                
        # Calculate NAV
        current_nav = cash
        for ticker, shares in shares_held.items():
            if shares > 0.0:
                df = processed_data[ticker]
                price = df.loc[current_time]["Close_MXN"] if current_time in df.index else df["Close_MXN"].iloc[0]
                current_nav += shares * price
                
        bullish_assets = [t for t, s in signals.items() if s > 0.0]
        
        # Weight allocation: Equal weight among bullish assets, capped by max equity exposure
        target_weights = {t: 0.0 for t in processed_data}
        if bullish_assets:
            weight_per_asset = max_equity_exposure / len(bullish_assets)
            # individual asset exposure cap is set dynamically or static, let's use 20% cap here for diversification
            weight_per_asset = min(0.20, weight_per_asset)
            for t in bullish_assets:
                target_weights[t] = weight_per_asset
                
        # Trading execution
        for ticker in processed_data:
            df = processed_data[ticker]
            if current_time not in df.index:
                continue
            close_price = df.loc[current_time]["Close_MXN"]
            target_w = target_weights[ticker]
            current_w = (shares_held[ticker] * close_price) / current_nav if current_nav > 0 else 0.0
            
            if abs(target_w - current_w) > dead_zone:
                target_value = current_nav * target_w
                current_value = shares_held[ticker] * close_price
                trade_value = target_value - current_value
                half_spread = SPREADS.get(ticker, 0.0001)
                
                if trade_value > 0.0:
                    # Buy
                    exec_price = close_price * (1.0 + half_spread)
                    comm = trade_value * COMMISSION
                    shares_to_buy = (trade_value - comm) / exec_price
                    if cash >= (shares_to_buy * exec_price + comm):
                        shares_held[ticker] += shares_to_buy
                        cash -= (shares_to_buy * exec_price + comm)
                        total_commission += comm
                        total_spread_cost += trade_value * half_spread
                        trade_count += 1
                elif trade_value < 0.0 and shares_held[ticker] > 0.0:
                    # Sell
                    exec_price = close_price * (1.0 - half_spread)
                    shares_to_sell = min(shares_held[ticker], -trade_value / exec_price)
                    proceeds = shares_to_sell * exec_price
                    comm = proceeds * COMMISSION
                    shares_held[ticker] -= shares_to_sell
                    cash += (proceeds - comm)
                    total_commission += comm
                    total_spread_cost += proceeds * half_spread
                    trade_count += 1
                    
        history_nav.append(current_nav)
        history_times.append(current_time)
        
    nav_series = pd.Series(history_nav, index=history_times)
    total_return = nav_series.iloc[-1] / INITIAL_CAPITAL - 1.0
    days = (nav_series.index[-1] - nav_series.index[0]).days
    years = max(days / 365.25, 0.01)
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0
    
    returns = nav_series.pct_change().dropna()
    excess_returns = returns - ((BONDIA_APR / 360.0) / (7.0 if timeframe in ["1h", "2h", "4h"] else 1.0))
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252 * (7 if timeframe in ["1h", "2h", "4h"] else 1))) if excess_returns.std() > 0 else 0.0
    
    max_dd = (nav_series / nav_series.cummax() - 1.0).min()
    
    return {
        "timeframe": timeframe,
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "trades": trade_count,
        "total_fees": total_commission + total_spread_cost,
        "interest": total_interest,
        "final_nav": nav_series.iloc[-1]
    }

def main():
    intraday_data, spy_daily = download_data()
    
    print("\n" + "="*50)
    print("RUNNING SIMULATIONS ON EXPANDED 20-ASSET UNIVERSE")
    print("="*50)
    
    configs = [
        {"tf": "1h", "dz": 0.03, "filter": False, "desc": "1h MACD Baseline (No SMA Filter, 3% Dead Zone)"},
        {"tf": "4h", "dz": 0.10, "filter": True, "desc": "4h MACD + SMA Filter + 10% Dead Zone"},
        {"tf": "1d", "dz": 0.10, "filter": True, "desc": "1d MACD + SMA Filter + 10% Dead Zone"}
    ]
    
    results = []
    for config in configs:
        print(f"\nRunning {config['desc']}...")
        res = run_simulation(intraday_data, spy_daily, timeframe=config["tf"], dead_zone=config["dz"], use_filters=config["filter"])
        results.append({**res, "desc": config["desc"]})
        
    print("\n" + "="*50)
    print("COMPARISON RESULTS ON EXPANDED 20-ASSET UNIVERSE")
    print("="*50)
    for r in results:
        print(f"\n{r['desc']}:")
        print(f"  Total Return: {r['total_return']*100:+.2f}%")
        print(f"  CAGR:         {r['cagr']*100:+.2f}%")
        print(f"  Sharpe Ratio: {r['sharpe']:.2f}")
        print(f"  Max Drawdown: {r['max_dd']*100:.2f}%")
        print(f"  Trades:       {r['trades']}")
        print(f"  Total Fees:   ${r['total_fees']:,.2f} MXN")
        print(f"  Interest:     ${r['interest']:,.2f} MXN")
        print(f"  Final NAV:    ${r['final_nav']:,.2f} MXN")

if __name__ == "__main__":
    main()
