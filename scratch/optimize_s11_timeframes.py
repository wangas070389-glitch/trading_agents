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
    return adx.fillna(20.0), plus_di.fillna(0.0), minus_di.fillna(0.0)

def run_backtest_for_timeframe(tf, universe, download_period):
    print(f"\n--- Backtesting Timeframe: {tf} ---")
    
    # 1. Download data
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
            interval = tf
            if tf == "1d":
                df_base = _strip_tz(yf.download(base, period="1y", interval=interval, progress=False))
                df_bull = _strip_tz(yf.download(assets["bull"], period="1y", interval=interval, progress=False))
                df_bear = _strip_tz(yf.download(assets["bear"], period="1y", interval=interval, progress=False))
            else:
                df_base = _strip_tz(yf.download(base, period=download_period, interval=interval, progress=False))
                df_bull = _strip_tz(yf.download(assets["bull"], period=download_period, interval=interval, progress=False))
                df_bear = _strip_tz(yf.download(assets["bear"], period=download_period, interval=interval, progress=False))
            
            for d in (df_base, df_bull, df_bear):
                if isinstance(d.columns, pd.MultiIndex):
                    d.columns = [c[0] for c in d.columns]
                    
        df_base["ATR"] = calculate_atr(df_base)
        df_bull["ATR"] = calculate_atr(df_bull)
        df_bull["CCI"] = calculate_cci(df_bull)
        adx_t, plus_di_t, minus_di_t = calculate_adx(df_bull)
        df_bull["ADX"] = adx_t
        df_bull["DI+"] = plus_di_t
        df_bull["DI-"] = minus_di_t
        
        df_bear["ATR"] = calculate_atr(df_bear)
        df_bear["CCI"] = calculate_cci(df_bear)
        adx_s, plus_di_s, minus_di_s = calculate_adx(df_bear)
        df_bear["ADX"] = adx_s
        df_bear["DI+"] = plus_di_s
        df_bear["DI-"] = minus_di_s
        
        merged = df_base[["Close", "High", "Low", "Volume"]].join(
            df_bull[["Close", "ATR", "CCI", "ADX", "DI+", "DI-"]], lsuffix="_QQQ", rsuffix="_TQQQ"
        ).join(
            df_bear[["Close", "ATR", "CCI", "ADX", "DI+", "DI-"]], rsuffix="_SQQQ"
        )
        merged.columns = [
            "Close_QQQ", "High_QQQ", "Low_QQQ", "Volume_QQQ",
            "Close_TQQQ", "ATR_TQQQ", "CCI_TQQQ", "ADX_TQQQ", "DI+_TQQQ", "DI-_TQQQ",
            "Close_SQQQ", "ATR_SQQQ", "CCI_SQQQ", "ADX_SQQQ", "DI+_SQQQ", "DI-_SQQQ"
        ]
        intraday[base] = merged.dropna()

    INITIAL_NAV = 200000.0
    cash = INITIAL_NAV
    active_position = None
    nav_history = []
    
    dates_available = sorted(list(set(intraday["QQQ"].index.strftime("%Y-%m-%d"))))
    backtest_dates = dates_available[-60:] if len(dates_available) >= 60 else dates_available
    
    trade_count = 0
    pnl_sum = 0.0
    
    for date_str in backtest_dates:
        regime = 2
        group = intraday["QQQ"][intraday["QQQ"].index.strftime("%Y-%m-%d") == date_str]
        if group.empty:
            continue
            
        first_bar_time = group.index[0]
        train_data = intraday["QQQ"][intraday["QQQ"].index < first_bar_time]
        
        if len(train_data) >= 30:
            sub_df = train_data.iloc[-30:]
            log_returns = np.log(sub_df["Close_QQQ"] / sub_df["Close_QQQ"].shift(1)).fillna(0.0)
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

        daily_high_qqq = float(group["High_QQQ"].max())
        daily_low_qqq = float(group["Low_QQQ"].min())
        
        for i in range(len(group)):
            bar_time = group.index[i]
            close_qqq = float(group["Close_QQQ"].iloc[i])
            
            close_tqqq = float(group["Close_TQQQ"].iloc[i])
            cci_tqqq = float(group["CCI_TQQQ"].iloc[i])
            adx_tqqq = float(group["ADX_TQQQ"].iloc[i])
            di_plus_t = float(group["DI+_TQQQ"].iloc[i])
            di_minus_t = float(group["DI-_TQQQ"].iloc[i])
            atr_tqqq = float(group["ATR_TQQQ"].iloc[i])
            
            close_sqqq = float(group["Close_SQQQ"].iloc[i])
            cci_sqqq = float(group["CCI_SQQQ"].iloc[i])
            adx_sqqq = float(group["ADX_SQQQ"].iloc[i])
            di_plus_s = float(group["DI+_SQQQ"].iloc[i])
            di_minus_s = float(group["DI-_SQQQ"].iloc[i])
            atr_sqqq = float(group["ATR_SQQQ"].iloc[i])
            
            is_eod = (bar_time.hour == 15 and bar_time.minute == 30) or i == (len(group) - 1)
            
            current_portfolio_value = cash
            if active_position:
                curr_price = close_tqqq if active_position["side"] == "long" else close_sqqq
                active_position["peak_price"] = max(active_position["peak_price"], curr_price)
                atr_exec = atr_tqqq if active_position["side"] == "long" else atr_sqqq
                
                stop_threshold = active_position["peak_price"] - 1.5 * atr_exec
                is_stop_out = curr_price < stop_threshold
                
                current_portfolio_value += active_position["shares"] * curr_price
                
                if is_stop_out or is_eod:
                    should_hold_overnight = False
                    if is_eod and not is_stop_out:
                        trade_profit = (curr_price > active_position["entry_price"])
                        if trade_profit:
                            if active_position["side"] == "long" and close_qqq >= (daily_high_qqq - 0.005 * daily_high_qqq) and (regime == 0 or regime == 2):
                                should_hold_overnight = True
                            elif active_position["side"] == "short" and close_qqq <= (daily_low_qqq + 0.005 * daily_low_qqq) and (regime == 1 or regime == 2):
                                should_hold_overnight = True
                                
                    if not should_hold_overnight:
                        val_credited = active_position["shares"] * curr_price
                        cash += val_credited
                        pnl = val_credited - active_position["allocated"]
                        pnl_sum += pnl
                        trade_count += 1
                        active_position = None
                        current_portfolio_value = cash
                        
            # Entry Triggers
            if not active_position and not is_eod:
                if (regime == 0 or regime == 2) and adx_tqqq >= 22.0 and cci_tqqq > 100.0 and di_plus_t > di_minus_t:
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
                elif (regime == 1 or regime == 2) and adx_sqqq >= 22.0 and cci_sqqq > 100.0 and di_plus_s > di_minus_s:
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
                elif adx_tqqq < 22.0 and cci_tqqq < -150.0:
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
                elif adx_sqqq < 22.0 and cci_sqqq < -150.0:
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
                side = active_position["side"]
                if side == "long":
                    if cci_tqqq >= 0.0:
                        val_credited = active_position["shares"] * close_tqqq
                        cash += val_credited
                        pnl = val_credited - active_position["allocated"]
                        pnl_sum += pnl
                        trade_count += 1
                        active_position = None
                        current_portfolio_value = cash
                else:
                    if cci_sqqq >= 0.0:
                        val_credited = active_position["shares"] * close_sqqq
                        cash += val_credited
                        pnl = val_credited - active_position["allocated"]
                        pnl_sum += pnl
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
    universe = {
        "QQQ": {"bull": "TQQQ", "bear": "SQQQ"}
    }
    timeframes = ["30m", "1h", "4h", "1d"]
    results = {}
    
    for tf in timeframes:
        try:
            res = run_backtest_for_timeframe(tf, universe, "60d")
            results[tf] = res
        except Exception as e:
            print(f"Error testing timeframe {tf}: {e}")
            
    print("\n" + "=" * 80)
    print("TIMEFRAME OPTIMIZATION RESULTS FOR S11 (30 PERIOD HMM LOOKBACK)")
    print("=" * 80)
    print(f"{'Timeframe':<12} | {'Final NAV':<16} | {'Total Return':<14} | {'Sharpe':<8} | {'Max DD':<10} | {'Trades':<8}")
    print("-" * 80)
    for tf, res in results.items():
        print(f"{tf:<12} | ${res['final_nav']:,.2f} MXN | {res['total_return']:+12.2f}% | {res['sharpe']:8.2f} | {res['max_dd']:9.2f}% | {res['trade_count']:<8}")
    print("=" * 80)

if __name__ == "__main__":
    main()
