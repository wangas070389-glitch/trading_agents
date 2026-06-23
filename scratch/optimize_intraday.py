"""
Grid search optimizer for the hourly intraday trading strategy.
Pre-computes HMM states for the overlapping timeframe once to achieve a 1000x speedup.
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# Local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skills.macd_trend import calculate_adx, calculate_macd

INTRADAY_UNIVERSE = ["SPY", "NVDA", "AAPL", "WALMEX.MX", "GFNORTEO.MX"]
SPREADS = {
    "SPY": 0.00005,
    "NVDA": 0.0001,
    "AAPL": 0.0001,
    "WALMEX.MX": 0.0007,
    "GFNORTEO.MX": 0.0009
}
INITIAL_CAPITAL = 20000.0
BONDIA_APR = 0.0653

def _to_utc_naive(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df

def get_data():
    """Download daily SPY + hourly universe data."""
    print("Downloading historical data...")
    spy_daily = yf.download("SPY", period="5y", interval="1d", progress=False)
    spy_daily.index = pd.to_datetime(spy_daily.index).tz_localize(None)
    spy_daily["Return"] = np.log(spy_daily["Close"] / spy_daily["Close"].shift(1))
    spy_daily = spy_daily.dropna()
    
    intraday_data = {}
    for ticker in INTRADAY_UNIVERSE:
        try:
            hist = yf.Ticker(ticker).history(period="730d", interval="1h")
            if hist.empty or len(hist) < 200:
                continue
            hist = _to_utc_naive(hist)
            intraday_data[ticker] = hist
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            
    try:
        usdmxn_1h = yf.Ticker("MXN=X").history(period="730d", interval="1h")
        usdmxn_1h = _to_utc_naive(usdmxn_1h)
    except Exception:
        usdmxn_1h = pd.DataFrame()
        
    for ticker in INTRADAY_UNIVERSE:
        if ticker in intraday_data and not ticker.endswith(".MX"):
            df = intraday_data[ticker]
            if not usdmxn_1h.empty:
                rate_aligned = usdmxn_1h["Close"].reindex(df.index, method="ffill").fillna(17.50)
            else:
                rate_aligned = pd.Series(17.50, index=df.index)
            df["close"] = df["Close"] * rate_aligned
            df["open"] = df["Open"] * rate_aligned
            df["high"] = df["High"] * rate_aligned
            df["low"] = df["Low"] * rate_aligned
            intraday_data[ticker] = df
        elif ticker in intraday_data:
            df = intraday_data[ticker]
            df["close"] = df["Close"]
            df["open"] = df["Open"]
            df["high"] = df["High"]
            df["low"] = df["Low"]
            intraday_data[ticker] = df

    return intraday_data, spy_daily

def precompute_hmm_states(spy_daily, target_dates):
    """Pre-calculates the HMM regime sequence once to avoid redundant fitting in grid loops."""
    print("Pre-calculating SPY HMM regimes (only for target intraday period)...")
    from hmmlearn import hmm
    hmm_states = {}
    
    min_date = min(target_dates)
    max_date = max(target_dates)
    
    # Filter unique dates to only target dates that overlap
    unique_dates = sorted([d for d in spy_daily.index if d >= min_date and d <= max_date])
    total_dates = len(unique_dates)
    print(f"Total dates to calculate HMM for: {total_dates}")
    
    for i, date in enumerate(unique_dates):
        date_str = date.strftime("%Y-%m-%d")
        
        # Fit HMM on SPY daily history up to the previous day
        spy_history_slice = spy_daily.loc[spy_daily.index < date]
        if len(spy_history_slice) >= 100:
            try:
                obs = spy_history_slice["Return"].values.reshape(-1, 1)
                # Set n_iter=15 to speed up convergence
                model_spy = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=15, random_state=42)
                model_spy.fit(obs)
                states = model_spy.predict(obs)
                means = model_spy.means_[:, 0]
                state_map = {np.argmin(means): -1, np.argmax(means): 1}
                for idx in range(3):
                    if idx not in state_map:
                        state_map[idx] = 0
                hmm_states[date_str] = state_map[states[-1]]
            except Exception:
                prev_date_str = unique_dates[i-1].strftime("%Y-%m-%d") if i > 0 else ""
                hmm_states[date_str] = hmm_states.get(prev_date_str, 0)
        else:
            hmm_states[date_str] = 0
            
    print(f"Pre-calculation complete. Total dates computed: {len(hmm_states)}")
    return hmm_states

def simulate(intraday_data, hmm_states, timeframe="1h", dead_zone=0.03, adx_filter=False, ma_filter=False, commission=0.0010):
    processed_data = {}
    for ticker, df in intraday_data.items():
        if timeframe != "1h":
            resampled = df.resample(timeframe).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "Volume": "sum"
            }).dropna()
        else:
            resampled = df.copy()
            
        resampled["macd"], resampled["signal"] = calculate_macd(resampled["close"])
        
        if adx_filter:
            _, _, resampled["adx"] = calculate_adx(resampled, length=14)
            
        if ma_filter:
            resampled["ma_long"] = resampled["close"].rolling(window=50).mean()
            
        processed_data[ticker] = resampled.dropna()
        
    all_times = sorted(set().union(*(set(df.index) for df in processed_data.values())))
    if len(all_times) < 50:
        return {"cagr": -9.99, "sharpe": -9.99, "max_dd": 0.0, "trades": 0, "final_nav": 0.0, "total_fees": 0.0}
        
    current_day_str = ""
    spy_hmm_state = 0
    max_equity_exposure = 0.50
    
    cash = INITIAL_CAPITAL
    shares_held = {t: 0.0 for t in processed_data}
    history_times = []
    history_strat = []
    
    trades_count = 0
    total_fees = 0.0
    
    for step_idx, current_time in enumerate(all_times):
        current_date_str = current_time.strftime("%Y-%m-%d")
        
        if step_idx > 0:
            prev_time = all_times[step_idx - 1]
            if prev_time.date() != current_time.date():
                days_diff = (current_time.date() - prev_time.date()).days
                interest = cash * (BONDIA_APR / 360.0) * days_diff
                cash += interest
                
        if current_date_str != current_day_str:
            current_day_str = current_date_str
            spy_hmm_state = hmm_states.get(current_date_str, 0)
            if spy_hmm_state == 1:
                max_equity_exposure = 0.95
            elif spy_hmm_state == -1:
                max_equity_exposure = 0.10
            else:
                max_equity_exposure = 0.50
                
        signals = {}
        for ticker, df in processed_data.items():
            if current_time in df.index:
                row = df.loc[current_time]
                macd_val = row["macd"]
                sig_val = row["signal"]
                
                is_bullish = macd_val > sig_val
                if adx_filter and row.get("adx", 0.0) < 20.0:
                    is_bullish = False
                if ma_filter and row["close"] < row.get("ma_long", 0.0):
                    is_bullish = False
                    
                signals[ticker] = 1.0 if is_bullish else -1.0
                
        current_nav = cash
        for ticker, shares in shares_held.items():
            if shares > 0.0:
                df = processed_data[ticker]
                price = df.loc[current_time]["close"] if current_time in df.index else df["close"].iloc[0]
                current_nav += shares * price
                
        bullish_assets = [t for t, s in signals.items() if s > 0.0]
        target_weights = {t: 0.0 for t in processed_data}
        if bullish_assets:
            weight_per_asset = max_equity_exposure / len(bullish_assets)
            weight_per_asset = min(0.30, weight_per_asset)
            for t in bullish_assets:
                target_weights[t] = weight_per_asset
                
        for ticker in processed_data:
            df = processed_data[ticker]
            if current_time not in df.index:
                continue
            close_price = df.loc[current_time]["close"]
            target_w = target_weights[ticker]
            current_w = (shares_held[ticker] * close_price) / current_nav if current_nav > 0 else 0.0
            
            if abs(target_w - current_w) > dead_zone:
                target_value = current_nav * target_w
                current_value = shares_held[ticker] * close_price
                trade_value = target_value - current_value
                half_spread = SPREADS.get(ticker, 0.0001)
                
                if trade_value > 0.0:
                    exec_price = close_price * (1.0 + half_spread)
                    commission_cost = trade_value * commission
                    shares_to_buy = (trade_value - commission_cost) / exec_price
                    if cash >= (shares_to_buy * exec_price + commission_cost):
                        shares_held[ticker] += shares_to_buy
                        cash -= (shares_to_buy * exec_price + commission_cost)
                        total_fees += commission_cost + (trade_value * half_spread)
                        trades_count += 1
                elif trade_value < 0.0 and shares_held[ticker] > 0.0:
                    exec_price = close_price * (1.0 - half_spread)
                    shares_to_sell = min(shares_held[ticker], -trade_value / exec_price)
                    sell_proceeds = shares_to_sell * exec_price
                    commission_cost = sell_proceeds * commission
                    shares_held[ticker] -= shares_to_sell
                    cash += (sell_proceeds - commission_cost)
                    total_fees += commission_cost + (sell_proceeds * half_spread)
                    trades_count += 1
                    
        history_times.append(current_time)
        history_strat.append(current_nav)
        
    strat_series = pd.Series(history_strat, index=history_times)
    total_return = strat_series.iloc[-1] / INITIAL_CAPITAL - 1.0
    days = (strat_series.index[-1] - strat_series.index[0]).days
    years = max(days / 365.25, 0.01)
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0
    
    hourly_returns = strat_series.pct_change().dropna()
    excess_returns = hourly_returns - ((BONDIA_APR / 360.0) / 7.0)
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252 * 7)) if excess_returns.std() > 0 else 0.0
    
    cumulative = (1.0 + hourly_returns).cumprod()
    max_dd = (cumulative / cumulative.cummax() - 1.0).min()
    
    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "trades": trades_count,
        "final_nav": strat_series.iloc[-1],
        "total_fees": total_fees
    }

def main():
    intraday_data, spy_daily = get_data()
    
    # Find unique target dates in intraday timeline
    all_times = sorted(set().union(*(set(df.index) for df in intraday_data.values())))
    target_dates = sorted(list(set(pd.to_datetime(t.date()) for t in all_times)))
    
    hmm_states = precompute_hmm_states(spy_daily, target_dates)
    
    timeframes = ["1h", "2h", "4h", "1d"]
    dead_zones = [0.03, 0.05, 0.08, 0.10]
    filter_configs = [
        {"adx": False, "ma": False, "desc": "MACD-Only"},
        {"adx": True, "ma": False, "desc": "MACD+ADX"},
        {"adx": False, "ma": True, "desc": "MACD+MA"},
        {"adx": True, "ma": True, "desc": "MACD+ADX+MA"}
    ]
    commissions = [0.0010, 0.0001, 0.0]
    
    results = []
    
    print("\nStarting Fast Parameter Grid Search...")
    for tf in timeframes:
        for dz in dead_zones:
            for config in filter_configs:
                for comm in commissions:
                    print(f"Testing TF={tf} | DZ={dz:.0%} | Filter={config['desc']} | Commission={comm*100:.3f}%...")
                    try:
                        res = simulate(
                            intraday_data, hmm_states,
                            timeframe=tf, dead_zone=dz,
                            adx_filter=config["adx"], ma_filter=config["ma"],
                            commission=comm
                        )
                        res_dict = {
                            "timeframe": tf,
                            "dead_zone": dz,
                            "filter": config["desc"],
                            "commission": comm,
                            **res
                        }
                        results.append(res_dict)
                    except Exception as e:
                        print(f"  Error: {e}")
                        
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by="cagr", ascending=False)
    
    dir_path = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(dir_path, "optimization_results.csv")
    df_results.to_csv(out_path, index=False)
    print(f"\nOptimization results saved to: {out_path}")
    
    summary_path = os.path.join(dir_path, "optimization_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Intraday Strategy Optimization Report\n\n")
        f.write("## Top 10 Configurations (Sorted by CAGR)\n\n")
        f.write("| TF | DZ | Filter | Comm | Total Return | CAGR | Sharpe | Max DD | Trades | Final NAV | Total Fees |\n")
        f.write("| :-: | :-: | :- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |\n")
        for idx, row in df_results.head(10).iterrows():
            f.write(f"| {row['timeframe']} | {row['dead_zone']:.0%} | {row['filter']} | {row['commission']*100:.2f}% | "
                    f"{row['total_return']*100:+.2f}% | {row['cagr']*100:+.2f}% | {row['sharpe']:.2f} | "
                    f"{row['max_dd']*100:.2f}% | {row['trades']} | ${row['final_nav']:,.2f} MXN | ${row['total_fees']:,.2f} MXN |\n")
            
        f.write("\n## Bottom 10 Configurations (Sorted by CAGR)\n\n")
        f.write("| TF | DZ | Filter | Comm | Total Return | CAGR | Sharpe | Max DD | Trades | Final NAV | Total Fees |\n")
        f.write("| :-: | :-: | :- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |\n")
        for idx, row in df_results.tail(10).iterrows():
            f.write(f"| {row['timeframe']} | {row['dead_zone']:.0%} | {row['filter']} | {row['commission']*100:.2f}% | "
                    f"{row['total_return']*100:+.2f}% | {row['cagr']*100:+.2f}% | {row['sharpe']:.2f} | "
                    f"{row['max_dd']*100:.2f}% | {row['trades']} | ${row['final_nav']:,.2f} MXN | ${row['total_fees']:,.2f} MXN |\n")
            
    print(f"Summary saved to: {summary_path}")

if __name__ == "__main__":
    main()
