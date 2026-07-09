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
    return adx.fillna(20.0)

def main():
    universe = {
        "QQQ": {"bull": "TQQQ", "bear": "SQQQ"},
        "SPY": {"bull": "UPRO", "bear": "SPXS"},
        "SOXX": {"bull": "SOXL", "bear": "SOXS"},
        "IWM": {"bull": "URTY", "bear": "SRTY"}
    }
    
    print("Downloading 1h data (730 days) for all assets...")
    intraday = {}
    for base, assets in universe.items():
        df_base = _strip_tz(yf.download(base, period="730d", interval="1h", progress=False))
        df_bull = _strip_tz(yf.download(assets["bull"], period="730d", interval="1h", progress=False))
        df_bear = _strip_tz(yf.download(assets["bear"], period="730d", interval="1h", progress=False))
        
        for d in (df_base, df_bull, df_bear):
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = [c[0] for c in d.columns]
                
        df_base["ATR"] = calculate_atr(df_base)
        df_bull["ATR"] = calculate_atr(df_bull)
        df_bull["CCI"] = calculate_cci(df_bull)
        df_bull["ADX"] = calculate_adx(df_bull)
        df_bear["ATR"] = calculate_atr(df_bear)
        df_bear["CCI"] = calculate_cci(df_bear)
        df_bear["ADX"] = calculate_adx(df_bear)
        
        merged = df_base[["Close", "High", "Low", "Volume", "ATR"]].join(
            df_bull[["Close", "ATR", "CCI", "ADX"]], lsuffix="_base", rsuffix="_bull"
        ).join(
            df_bear[["Close", "ATR", "CCI", "ADX"]], rsuffix="_bear"
        )
        merged.columns = [
            "Close_base", "High_base", "Low_base", "Volume_base", "ATR_base",
            "Close_bull", "ATR_bull", "CCI_bull", "ADX_bull",
            "Close_bear", "ATR_bear", "CCI_bear", "ADX_bear"
        ]
        intraday[base] = merged.dropna()

    INITIAL_NAV = 200000.0
    cash = INITIAL_NAV
    active_pos = None
    nav_history = []
    
    dates_available = sorted(list(set(intraday["QQQ"].index.strftime("%Y-%m-%d"))))
    backtest_dates = dates_available[-60:]
    
    closed_trades = []
    
    for date_str in backtest_dates:
        regimes = {}
        scores = {}
        
        for base in universe.keys():
            df = intraday[base]
            sub_df = df[df.index.strftime("%Y-%m-%d") < date_str]
            unique_dates = sorted(list(set(sub_df.index.date)))
            if len(unique_dates) < 60:
                scores[base] = -1
                regimes[base] = 2
                continue
                
            target_dates = unique_dates[-60:]
            train_df = sub_df[sub_df.index.date >= target_dates[0]]
            train_closes = train_df["Close_base"]
            
            log_returns = np.log(train_closes / train_closes.shift(1)).fillna(0.0)
            rolling_vol = log_returns.rolling(window=10).std().fillna(0.0)
            features = np.column_stack([log_returns.values, rolling_vol.values])
            
            try:
                hmm = GaussianHMM(n_components=3, covariance_type="diag", n_iter=100, random_state=42)
                hmm.fit(features)
                states = hmm.predict(features)
                
                state_vols = [np.mean(rolling_vol.values[states == i]) for i in range(3)]
                bear_state = np.argmax(state_vols)
                rem = [i for i in range(3) if i != bear_state]
                state_means = [np.mean(log_returns.values[states == i]) for i in range(3)]
                bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
                
                curr_state_raw = states[-1]
                if curr_state_raw == bull_state:
                    regimes[base] = 0
                    scores[base] = abs(state_means[bull_state]) / state_vols[bull_state]
                elif curr_state_raw == bear_state:
                    regimes[base] = 1
                    scores[base] = abs(state_means[bear_state]) / state_vols[bear_state]
                else:
                    regimes[base] = 2
                    scores[base] = -0.5
            except Exception as e:
                regimes[base] = 2
                scores[base] = -1.0
                
        # Target Selection
        if active_pos:
            target_asset = active_pos["base"]
        else:
            trending = {k: v for k, v in scores.items() if regimes[k] in (0, 1)}
            if trending:
                target_asset = max(trending, key=trending.get)
            else:
                target_asset = "QQQ"
                
        target_regime = regimes[target_asset]
        day_bars = intraday[target_asset][intraday[target_asset].index.strftime("%Y-%m-%d") == date_str]
        
        if day_bars.empty:
            continue
            
        bull_etf = universe[target_asset]["bull"]
        bear_etf = universe[target_asset]["bear"]
        
        for idx in range(len(day_bars)):
            time_val = day_bars.index[idx]
            close_base = float(day_bars["Close_base"].iloc[idx])
            
            close_bull = float(day_bars["Close_bull"].iloc[idx])
            atr_bull = float(day_bars["ATR_bull"].iloc[idx])
            cci_bull = float(day_bars["CCI_bull"].iloc[idx])
            adx_bull = float(day_bars["ADX_bull"].iloc[idx])
            
            close_bear = float(day_bars["Close_bear"].iloc[idx])
            atr_bear = float(day_bars["ATR_bear"].iloc[idx])
            cci_bear = float(day_bars["CCI_bear"].iloc[idx])
            adx_bear = float(day_bars["ADX_bear"].iloc[idx])
            
            # Position monitor
            if active_pos:
                side = active_pos["side"]
                curr_price = close_bull if side == "long" else close_bear
                active_pos["peak_price"] = max(active_pos.get("peak_price", curr_price), curr_price)
                
                # Check paper profit to tighten trailing stop
                atr_val = atr_bull if side == "long" else atr_bear
                buy_price = active_pos["buy_price"]
                paper_profit_atr = (curr_price - buy_price) / atr_val
                
                # Default trailing stop multiplier is 3.0 ATR
                stop_mult = 3.0
                
                # Tightening rule: if profit > 1.5 ATR, tighten stop multiplier to 1.5 ATR
                if paper_profit_atr > 1.5:
                    stop_mult = 1.5
                    
                stop_threshold = active_pos["peak_price"] - stop_mult * atr_val
                is_stop_out = curr_price < stop_threshold
                
                is_regime_flip = False
                if side == "long" and target_regime != 0:
                    is_regime_flip = True
                elif side == "short" and target_regime != 1:
                    is_regime_flip = True
                    
                if is_stop_out or is_regime_flip:
                    shares = active_pos["shares"]
                    val = shares * curr_price
                    cash += val
                    pnl = val - active_pos["allocated"]
                    
                    exit_reason = "STOP_LOSS" if is_stop_out else "REGIME_FLIP"
                    closed_trades.append({"pnl": pnl, "exit": exit_reason})
                    active_pos = None
                    
            # Entry triggers
            if not active_pos:
                if target_regime == 0:
                    if cci_bull < -100.0 and adx_bull > 20.0:
                        alloc = cash * 0.90
                        shares = alloc / close_bull
                        if shares > 0.01:
                            cash -= alloc
                            active_pos = {
                                "ticker": bull_etf,
                                "side": "long",
                                "shares": shares,
                                "buy_price": close_bull,
                                "peak_price": close_bull,
                                "allocated": alloc,
                                "base": target_asset
                            }
                elif target_regime == 1:
                    if cci_bear < -100.0 and adx_bear > 20.0:
                        alloc = cash * 0.90
                        shares = alloc / close_bear
                        if shares > 0.01:
                            cash -= alloc
                            active_pos = {
                                "ticker": bear_etf,
                                "side": "short",
                                "shares": shares,
                                "buy_price": close_bear,
                                "peak_price": close_bear,
                                "allocated": alloc,
                                "base": target_asset
                            }
                            
        # Day Close NAV
        eod_holding_val = 0.0
        if active_pos:
            curr_close = close_bull if active_pos["side"] == "long" else close_bear
            eod_holding_val = active_pos["shares"] * curr_close
        nav_history.append(cash + eod_holding_val)
        
    df_nav = pd.DataFrame({"NAV": nav_history})
    final_nav = df_nav["NAV"].iloc[-1]
    total_ret = final_nav / INITIAL_NAV - 1.0
    
    daily_pct = df_nav["NAV"].pct_change().dropna()
    ann_vol = daily_pct.std() * np.sqrt(252)
    sharpe = (total_ret - 0.095) / ann_vol if ann_vol > 0 else 0.0
    
    roll_max = df_nav["NAV"].cummax()
    max_dd = float(((df_nav["NAV"] - roll_max) / roll_max).min())
    
    print("\n" + "=" * 80)
    print("HYBRID PULLBACK SWING + PROFIT-TIGHTENING STOP BACKTEST")
    print("=" * 80)
    print(f"Final NAV       : ${final_nav:,.2f} MXN")
    print(f"Total Return    : {total_ret*100:+.2f}%")
    print(f"Sharpe (Rf=9.5%): {sharpe:.2f}")
    print(f"Max Drawdown    : {max_dd*100:.2f}%")
    print("=" * 80)
    
    if closed_trades:
        tdf = pd.DataFrame(closed_trades)
        print(f"\nTotal trades: {len(tdf)}, Total PnL: ${tdf['pnl'].sum():,.2f}")
        print(tdf.groupby("exit")["pnl"].agg(["count", "sum", "mean"]))

if __name__ == "__main__":
    main()
