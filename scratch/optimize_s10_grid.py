import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM

def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)
    return df

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

def run_backtest(tf, lookback_days, stop_type, band_mult=1.5):
    download_period = "60d" if tf == "30m" else "150d"
    universe = {"QQQ": {"bull": "TQQQ", "bear": "SQQQ"}}
    
    intraday = {}
    for base, assets in universe.items():
        if tf == "4h":
            df_base_1h = _strip_tz(yf.download(base, period=download_period, interval="1h", progress=False))
            df_bull_1h = _strip_tz(yf.download(assets["bull"], period=download_period, interval="1h", progress=False))
            df_bear_1h = _strip_tz(yf.download(assets["bear"], period=download_period, interval="1h", progress=False))
            
            for d in (df_base_1h, df_bull_1h, df_bear_1h):
                if isinstance(d.columns, pd.MultiIndex):
                    d.columns = [c[0] for c in d.columns]
                    
            df_base = df_base_1h.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()
            df_bull = df_bull_1h.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()
            df_bear = df_bear_1h.resample("4h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()
        else:
            df_base = _strip_tz(yf.download(base, period=download_period, interval=tf, progress=False))
            df_bull = _strip_tz(yf.download(assets["bull"], period=download_period, interval=tf, progress=False))
            df_bear = _strip_tz(yf.download(assets["bear"], period=download_period, interval=tf, progress=False))
            
            for d in (df_base, df_bull, df_bear):
                if isinstance(d.columns, pd.MultiIndex):
                    d.columns = [c[0] for c in d.columns]
                    
        df_base["ATR"] = calculate_atr(df_base)
        df_bull["ATR"] = calculate_atr(df_bull)
        df_bear["ATR"] = calculate_atr(df_bear)
        
        merged = df_base[["Close", "High", "Low", "Volume", "ATR"]].join(
            df_bull[["Close", "ATR"]], lsuffix="_QQQ", rsuffix="_TQQQ"
        ).join(
            df_bear[["Close", "ATR"]], rsuffix="_SQQQ"
        )
        merged.columns = [
            "Close_QQQ", "High_QQQ", "Low_QQQ", "Volume_QQQ", "ATR_QQQ",
            "Close_TQQQ", "ATR_TQQQ",
            "Close_SQQQ", "ATR_SQQQ"
        ]
        intraday[base] = merged.dropna()

    INITIAL_NAV = 200000.0
    cash = INITIAL_NAV
    active_position = None
    nav_history = []
    
    dates_available = sorted(list(set(intraday["QQQ"].index.strftime("%Y-%m-%d"))))
    # If 30m data is downloaded, we only have 60 days, so slice to whatever is available safely
    backtest_dates = dates_available[-60:] if len(dates_available) >= 60 else dates_available
    
    trade_count = 0
    
    for date_str in backtest_dates:
        regime = 2
        group = intraday["QQQ"][intraday["QQQ"].index.strftime("%Y-%m-%d") == date_str]
        if group.empty:
            continue
            
        first_bar_time = group.index[0]
        train_data = intraday["QQQ"][intraday["QQQ"].index < first_bar_time]
        
        unique_dates = sorted(list(set(train_data.index.date)))
        if len(unique_dates) >= lookback_days:
            target_dates = unique_dates[-lookback_days:]
            train_df = train_data[train_data.index.date >= target_dates[0]]
            train_closes = train_df["Close_QQQ"]
            
            log_returns = np.log(train_closes / train_closes.shift(1)).fillna(0.0)
            rolling_vol = log_returns.rolling(window=10).std().fillna(0.0)
            features = np.column_stack([log_returns.values, rolling_vol.values])
            try:
                hmm = GaussianHMM(n_components=3, covariance_type="diag", n_iter=100, random_state=42)
                hmm.fit(features)
                regimes = hmm.predict(features)
                
                state_vols = [np.mean(rolling_vol.values[regimes == i]) if np.any(regimes == i) else 1e9 for i in range(3)]
                bear_state = np.argmax(state_vols)
                rem = [i for i in range(3) if i != bear_state]
                state_means = [np.mean(log_returns.values[regimes == i]) if np.any(regimes == i) else -1e9 for i in range(3)]
                bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
                
                last_state = regimes[-1]
                if last_state == bull_state:
                    regime = 0
                elif last_state == bear_state:
                    regime = 1
                else:
                    regime = 2
            except Exception as e:
                regime = 2

        # Daily VWAP variables
        cum_pv = ((group["High_QQQ"] + group["Low_QQQ"] + group["Close_QQQ"]) / 3.0 * group["Volume_QQQ"]).cumsum()
        cum_vol = group["Volume_QQQ"].cumsum()
        vwaps = cum_pv / cum_vol.replace(0, 1)
        daily_high_qqq = float(group["High_QQQ"].max())
        daily_low_qqq = float(group["Low_QQQ"].min())
        
        for i in range(len(group)):
            bar_time = group.index[i]
            close_qqq = float(group["Close_QQQ"].iloc[i])
            atr_qqq = float(group["ATR_QQQ"].iloc[i])
            vwap_qqq = float(vwaps.iloc[i])
            
            close_tqqq = float(group["Close_TQQQ"].iloc[i])
            atr_tqqq = float(group["ATR_TQQQ"].iloc[i])
            
            close_sqqq = float(group["Close_SQQQ"].iloc[i])
            atr_sqqq = float(group["ATR_SQQQ"].iloc[i])
            
            is_eod = (bar_time.hour == 15 and bar_time.minute == 30) or i == (len(group) - 1)
            
            current_portfolio_value = cash
            if active_position:
                curr_price = close_tqqq if active_position["side"] == "long" else close_sqqq
                active_position["peak_price"] = max(active_position["peak_price"], curr_price)
                atr_exec = atr_tqqq if active_position["side"] == "long" else atr_sqqq
                
                if stop_type == "hybrid":
                    buy_price = active_position["entry_price"]
                    paper_profit_atr = (curr_price - buy_price) / atr_exec
                    stop_mult = 3.0 if paper_profit_atr <= 1.5 else 1.5
                else:
                    stop_mult = 1.5
                    
                stop_threshold = active_position["peak_price"] - stop_mult * atr_exec
                is_stop_out = curr_price < stop_threshold
                
                current_portfolio_value += active_position["shares"] * curr_price
                
                if is_stop_out or is_eod:
                    should_hold_overnight = False
                    if is_eod and not is_stop_out:
                        trade_profit = (curr_price > active_position["entry_price"])
                        if trade_profit:
                            if active_position["side"] == "long" and close_qqq >= (daily_high_qqq - 0.005 * daily_high_qqq) and regime == 0:
                                should_hold_overnight = True
                            elif active_position["side"] == "short" and close_qqq <= (daily_low_qqq + 0.005 * daily_low_qqq) and (regime == 1 or regime == 2):
                                should_hold_overnight = True
                                
                    if not should_hold_overnight:
                        val_credited = active_position["shares"] * curr_price
                        cash += val_credited
                        trade_count += 1
                        active_position = None
                        current_portfolio_value = cash
                        
            # Entry triggers
            if not active_position and not is_eod:
                upper_band = vwap_qqq + band_mult * atr_qqq
                lower_band = vwap_qqq - band_mult * atr_qqq
                
                if regime == 0 and close_qqq > upper_band:
                    # Bull breakout long TQQQ
                    alloc = current_portfolio_value * 0.90
                    shares = alloc / close_tqqq
                    cash -= alloc
                    active_position = {
                        "side": "long",
                        "shares": shares,
                        "entry_price": close_tqqq,
                        "peak_price": close_tqqq,
                        "allocated": alloc
                    }
                elif regime == 1 and close_qqq < lower_band:
                    # Bear breakdown long SQQQ
                    alloc = current_portfolio_value * 0.90
                    shares = alloc / close_sqqq
                    cash -= alloc
                    active_position = {
                        "side": "short",
                        "shares": shares,
                        "entry_price": close_sqqq,
                        "peak_price": close_sqqq,
                        "allocated": alloc
                    }
            elif active_position and not is_eod:
                # Settle mean reversion back to VWAP
                side = active_position["side"]
                if side == "long" and close_qqq <= vwap_qqq:
                    val_credited = active_position["shares"] * close_tqqq
                    cash += val_credited
                    trade_count += 1
                    active_position = None
                    current_portfolio_value = cash
                elif side == "short" and close_qqq >= vwap_qqq:
                    val_credited = active_position["shares"] * close_sqqq
                    cash += val_credited
                    trade_count += 1
                    active_position = None
                    current_portfolio_value = cash
                        
        eod_holding_val = 0.0
        if active_position:
            curr_c = close_tqqq if active_position["side"] == "long" else close_sqqq
            eod_holding_val = active_position["shares"] * curr_c
        nav_history.append(cash + eod_holding_val)
        
    df_nav = pd.DataFrame({"NAV": nav_history})
    final_nav = df_nav["NAV"].iloc[-1]
    total_ret = final_nav / INITIAL_NAV - 1.0
    
    daily_pct = df_nav["NAV"].pct_change().dropna()
    ann_vol = daily_pct.std() * np.sqrt(252)
    sharpe = (total_ret - 0.095) / ann_vol if ann_vol > 0 else 0.0
    
    roll_max = df_nav["NAV"].cummax()
    max_dd = float(((df_nav["NAV"] - roll_max) / roll_max).min())
    
    return {
        "final_nav": final_nav,
        "total_return": total_ret * 100.0,
        "sharpe": sharpe,
        "max_dd": max_dd * 100.0,
        "trade_count": trade_count
    }

def main():
    grid = [
        ("30m", 30, "fixed", 1.5),
        ("1h", 60, "hybrid", 0.5),
        ("1h", 60, "hybrid", 0.75),
        ("1h", 60, "hybrid", 1.0),
        ("1h", 60, "hybrid", 1.25),
        ("1h", 60, "hybrid", 1.5)
    ]
    
    results = []
    for tf, lb, st, bm in grid:
        try:
            print(f"Testing S10: Timeframe={tf}, Lookback={lb}d, Stop={st}, Band={bm}...")
            res = run_backtest(tf, lb, st, bm)
            results.append((tf, lb, st, bm, res))
        except Exception as e:
            print(f"Error testing {tf} + {lb}d: {e}")
            
    print("\n" + "=" * 80)
    print("STRATEGY 10 GRID OPTIMIZATION SEARCH RESULTS")
    print("=" * 80)
    print(f"{'Timeframe':<10} | {'Lookback':<8} | {'Stop-Loss':<9} | {'Band':<5} | {'Final NAV':<16} | {'Total Return':<14} | {'Sharpe':<8} | {'Max DD':<10} | {'Trades':<8}")
    print("-" * 80)
    for tf, lb, st, bm, res in results:
        print(f"{tf:<10} | {lb:<8} | {st:<9} | {bm:<5} | ${res['final_nav']:,.2f} MXN | {res['total_return']:+12.2f}% | {res['sharpe']:8.2f} | {res['max_dd']:9.2f}% | {res['trade_count']:<8}")
    print("=" * 80)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
