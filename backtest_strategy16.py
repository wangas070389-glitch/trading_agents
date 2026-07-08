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
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print("STRATEGY 16: MULTI-ASSET HMM INTRADAY ROUTER BACKTEST")
    print("=" * 80)
    
    universe = {
        "QQQ": {"bull": "TQQQ", "bear": "SQQQ"},
        "SPY": {"bull": "UPRO", "bear": "SPXS"},
        "SOXX": {"bull": "SOXL", "bear": "SOXS"},
        "IWM": {"bull": "URTY", "bear": "SRTY"}
    }
    
    print("Downloading historical daily data (2 years) for HMM training...")
    daily_data = {}
    for base in universe.keys():
        df = yf.download(base, start="2024-05-01", end="2026-07-01", interval="1d", progress=False)
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        daily_data[base] = df["Close"].ffill()

    print("\nDownloading 30m intraday bars (60 days) for all assets...")
    intraday = {}
    for base, assets in universe.items():
        print(f"  Downloading {base}, {assets['bull']}, {assets['bear']}...")
        df_base = _strip_tz(yf.download(base, period="60d", interval="30m", progress=False))
        df_bull = _strip_tz(yf.download(assets["bull"], period="60d", interval="30m", progress=False))
        df_bear = _strip_tz(yf.download(assets["bear"], period="60d", interval="30m", progress=False))
        
        if isinstance(df_base.columns, pd.MultiIndex): df_base.columns = [c[0] for c in df_base.columns]
        if isinstance(df_bull.columns, pd.MultiIndex): df_bull.columns = [c[0] for c in df_bull.columns]
        if isinstance(df_bear.columns, pd.MultiIndex): df_bear.columns = [c[0] for c in df_bear.columns]
        
        df_base["ATR"] = calculate_atr(df_base)
        
        df_bull["ATR"] = calculate_atr(df_bull)
        df_bull["CCI"] = calculate_cci(df_bull)
        df_bull["ADX"] = calculate_adx(df_bull)
        
        df_bear["ATR"] = calculate_atr(df_bear)
        df_bear["CCI"] = calculate_cci(df_bear)
        df_bear["ADX"] = calculate_adx(df_bear)
        
        # Merge
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

    INITIAL_NAV = 200000.0  # MXN
    TRANSACTION_FEE = 0.0029
    
    cash = INITIAL_NAV
    portfolio_value = INITIAL_NAV
    
    active_pos = None
    nav_history = []
    dates_list = []
    
    # We group by date based on the intersection of dates across all 4 datasets
    all_dates = sorted(list(set(intraday["QQQ"].index.strftime("%Y-%m-%d"))))
    
    print(f"\nSimulating {len(all_dates)} days of trading...")
    
    trade_logs = []
    
    for date_str in all_dates:
        # 1. Daily HMM selection
        scores = {}
        regimes = {}
        
        # Let's train HMM on each base asset daily return up to yesterday
        for base in universe.keys():
            closes = daily_data[base]
            yesterday = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            sub_closes = closes[closes.index.date < yesterday]
            if len(sub_closes) < 130:
                scores[base] = -1
                regimes[base] = 2 # default Chop
                continue
            
            log_returns = np.log(sub_closes / sub_closes.shift(1)).fillna(0.0)
            rolling_vol = log_returns.rolling(window=10).std().fillna(0.0)
            features = np.column_stack([log_returns.values, rolling_vol.values])
            
            hmm = GaussianHMM(n_components=3, covariance_type="diag", n_iter=100, random_state=42)
            hmm.fit(features)
            states = hmm.predict(features)
            
            # Map states
            state_vols = [np.mean(rolling_vol.values[states == i]) for i in range(3)]
            bear_state = np.argmax(state_vols)
            rem = [i for i in range(3) if i != bear_state]
            state_means = [np.mean(log_returns.values[states == i]) for i in range(3)]
            bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
            chop_state = [i for i in range(3) if i != bear_state and i != bull_state][0]
            
            curr_state_raw = states[-1]
            
            # Decoded state
            if curr_state_raw == bull_state:
                regimes[base] = 0
                scores[base] = abs(state_means[bull_state]) / state_vols[bull_state]
            elif curr_state_raw == bear_state:
                regimes[base] = 1
                scores[base] = abs(state_means[bear_state]) / state_vols[bear_state]
            else:
                regimes[base] = 2
                scores[base] = -0.5  # Low priority for Chop
                
        # Rank: pick highest score
        # Priority: Trending assets first. If all are Chop, pick the one with highest ATR yesterday.
        trending = {k: v for k, v in scores.items() if regimes[k] in (0, 1)}
        if trending:
            target_asset = max(trending, key=trending.get)
        else:
            # All Chop, pick highest average daily ATR in QQQ/SPY/SOXX/IWM over last 5 days
            atr_vals = {}
            for base in universe.keys():
                df = intraday[base]
                sub = df[df.index.strftime("%Y-%m-%d") < date_str]
                atr_vals[base] = float(sub["ATR_base"].iloc[-1]) if not sub.empty else 0.0
            target_asset = max(atr_vals, key=atr_vals.get)
            
        target_regime = regimes[target_asset]
        target_df = intraday[target_asset]
        day_bars = target_df[target_df.index.strftime("%Y-%m-%d") == date_str]
        
        if day_bars.empty:
            continue
            
        # 2. Intraday Trading simulation on the locked target
        bull_etf = universe[target_asset]["bull"]
        bear_etf = universe[target_asset]["bear"]
        
        # Calculate daily vwap and bands for target index today
        cum_pv = ((day_bars["High_base"] + day_bars["Low_base"] + day_bars["Close_base"]) / 3.0 * day_bars["Volume_base"]).sum()
        cum_vol = day_bars["Volume_base"].sum()
        vwap_base = cum_pv / cum_vol if cum_vol > 0 else float(day_bars["Close_base"].iloc[0])
        
        for idx in range(len(day_bars)):
            time_val = day_bars.index[idx]
            is_eod = time_val.time() >= datetime.time(15, 30)
            
            close_base = float(day_bars["Close_base"].iloc[idx])
            atr_base = float(day_bars["ATR_base"].iloc[idx])
            
            upper_band = vwap_base + 1.5 * atr_base
            lower_band = vwap_base - 1.5 * atr_base
            
            # Get latest pricing for the leveraged assets
            close_bull = float(day_bars["Close_bull"].iloc[idx])
            atr_bull = float(day_bars["ATR_bull"].iloc[idx])
            cci_bull = float(day_bars["CCI_bull"].iloc[idx])
            adx_bull = float(day_bars["ADX_bull"].iloc[idx])
            
            close_bear = float(day_bars["Close_bear"].iloc[idx])
            atr_bear = float(day_bars["ATR_bear"].iloc[idx])
            cci_bear = float(day_bars["CCI_bear"].iloc[idx])
            adx_bear = float(day_bars["ADX_bear"].iloc[idx])
            
            # Update active position valuation
            if active_pos:
                side = active_pos["side"]
                curr_price = close_bull if side == "long" else close_bear
                active_pos["peak_price"] = max(active_pos.get("peak_price", curr_price), curr_price)
                
                # S10 Stop-out: 1.5 * ATR trailing
                stop_threshold = active_pos["peak_price"] - 1.5 * (atr_bull if side == "long" else atr_bear)
                is_stop_out = curr_price < stop_threshold
                
                # Settle Condition
                is_settled = False
                if target_regime == 2:
                    # Settle at VWAP during Chop
                    if (side == "long" and close_base >= vwap_base) or (side == "short" and close_base <= vwap_base):
                        is_settled = True
                else:
                    # Settle when CCI crosses zero line during Trends
                    if side == "long" and cci_bull >= 0.0:
                        is_settled = True
                    elif side == "short" and cci_bear >= 0.0: # SQQQ CCI crosses zero
                        is_settled = True
                        
                if is_stop_out or is_settled or is_eod:
                    # Liquidate position
                    shares = active_pos["shares"]
                    val = shares * curr_price
                    cash += val * (1.0 - TRANSACTION_FEE)
                    exit_reason = "TRAILING_STOP" if is_stop_out else ("VWAP_REVERSION" if is_settled else "EOD_LIQUIDATION")
                    trade_logs.append(f"  EXIT: {active_pos['ticker']} ({side}) at {time_val.strftime('%H:%M')} via {exit_reason} (Cash: ${cash:,.2f})")
                    active_pos = None
                    
            # Entry triggers (only if flat and not EOD)
            if not active_pos and not is_eod:
                if target_regime == 0:
                    # Bull Trend -> Buy Bull ETF on pullback
                    if cci_bull < -100.0 and adx_bull > 20.0:
                        alloc = cash * 0.90
                        shares = alloc / (close_bull * (1.0 + TRANSACTION_FEE))
                        if shares > 0.01:
                            cash -= alloc
                            active_pos = {
                                "ticker": bull_etf,
                                "side": "long",
                                "shares": shares,
                                "buy_price": close_bull,
                                "peak_price": close_bull
                            }
                            trade_logs.append(f"  ENTRY: {bull_etf} (long) at {time_val.strftime('%H:%M')} (Regime: Bull {target_asset})")
                elif target_regime == 1:
                    # Bear Trend -> Buy Bear ETF on rally
                    if cci_bear < -100.0 and adx_bear > 20.0:
                        alloc = cash * 0.90
                        shares = alloc / (close_bear * (1.0 + TRANSACTION_FEE))
                        if shares > 0.01:
                            cash -= alloc
                            active_pos = {
                                "ticker": bear_etf,
                                "side": "short",
                                "shares": shares,
                                "buy_price": close_bear,
                                "peak_price": close_bear
                            }
                            trade_logs.append(f"  ENTRY: {bear_etf} (short) at {time_val.strftime('%H:%M')} (Regime: Bear {target_asset})")
                else:
                    # Chop Regime -> VWAP Mean Reversion
                    if close_base < lower_band:
                        # Buy Bull ETF
                        alloc = cash * 0.90
                        shares = alloc / (close_bull * (1.0 + TRANSACTION_FEE))
                        if shares > 0.01:
                            cash -= alloc
                            active_pos = {
                                "ticker": bull_etf,
                                "side": "long",
                                "shares": shares,
                                "buy_price": close_bull,
                                "peak_price": close_bull
                            }
                            trade_logs.append(f"  ENTRY: {bull_etf} (long reversion) at {time_val.strftime('%H:%M')} (Regime: Chop {target_asset})")
                    elif close_base > upper_band:
                        # Buy Bear ETF
                        alloc = cash * 0.90
                        shares = alloc / (close_bear * (1.0 + TRANSACTION_FEE))
                        if shares > 0.01:
                            cash -= alloc
                            active_pos = {
                                "ticker": bear_etf,
                                "side": "short",
                                "shares": shares,
                                "buy_price": close_bear,
                                "peak_price": close_bear
                            }
                            trade_logs.append(f"  ENTRY: {bear_etf} (short reversion) at {time_val.strftime('%H:%M')} (Regime: Chop {target_asset})")

        # Track EOD NAV
        eod_holding_val = 0.0
        if active_pos:
            curr_close = close_bull if active_pos["side"] == "long" else close_bear
            eod_holding_val = active_pos["shares"] * curr_close
        
        portfolio_value = cash + eod_holding_val
        nav_history.append(portfolio_value)
        dates_list.append(date_str)

    # 3. Output metrics
    nav_series = pd.Series(nav_history, index=pd.to_datetime(dates_list))
    total_return = (nav_series.iloc[-1] / INITIAL_NAV - 1.0) * 100.0
    
    daily_returns = nav_series.pct_change().dropna()
    sharpe = np.sqrt(252.0) * daily_returns.mean() / daily_returns.std() if len(daily_returns) > 1 and daily_returns.std() > 0 else 0.0
    
    peak = nav_series.cummax()
    drawdown = (nav_series - peak) / peak
    max_dd = drawdown.min() * 100.0
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS FOR STRATEGY 16")
    print("=" * 80)
    print(f"Initial Capital : ${INITIAL_NAV:,.2f} MXN")
    print(f"Final Value     : ${nav_series.iloc[-1]:,.2f} MXN")
    print(f"Total Return    : {total_return:+.2f}%")
    print(f"Sharpe Ratio    : {sharpe:.2f}")
    print(f"Max Drawdown    : {max_dd:.2f}%")
    print("=" * 80)

    # Save to CSV
    nav_df = pd.DataFrame({"NAV": nav_series})
    nav_df.to_csv(os.path.join(dir_path, "strategy16_backtest_nav.csv"))
    print(f"Saved backtest curve to strategy16_backtest_nav.csv")
    
    # Write report
    report = (
        f"# Strategy 16 Backtest Report\n\n"
        f"**Strategy Name**: Multi-Asset HMM Intraday Router\n"
        f"**Underlying Instruments**: QQQ, SPY, SOXX, IWM\n"
        f"**Leveraged Tradables**: TQQQ/SQQQ, UPRO/SPXS, SOXL/SOXS, URTY/SRTY\n\n"
        f"### Performance Metrics\n"
        f"* **Total Return**: {total_return:+.2f}%\n"
        f"* **Annualized Sharpe**: {sharpe:.2f}\n"
        f"* **Maximum Drawdown**: {max_dd:.2f}%\n"
        f"* **Backtest Period**: {dates_list[0]} to {dates_list[-1]} ({len(dates_list)} trading days)\n"
    )
    with open(os.path.join(dir_path, "strategy16_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print("Saved backtest report to strategy16_backtest_report.md")

if __name__ == "__main__":
    main()
