import os
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM

# Strategy 16 v2 prototype: S10's exact trade engine (VWAP band breakout/reversion,
# 1.5 ATR trailing stop, conditional overnight holds, Alpaca zero commission)
# wrapped in S16's multi-asset HMM router. The router picks which index to trade
# each day; if a position was held overnight, the router locks to that asset
# until flat.

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

def decode_regime(train_closes):
    """S10-style HMM on 30m intraday closes. Returns (regime, score).
    regime: 0=bull, 1=bear, 2=chop. score: |mean|/vol of current state."""
    if len(train_closes) < 130:
        return 2, -1.0
    log_returns = np.log(train_closes / train_closes.shift(1)).fillna(0.0)
    rolling_vol = log_returns.rolling(window=10).std().fillna(0.0)
    features = np.column_stack([log_returns.values, rolling_vol.values])

    hmm = GaussianHMM(n_components=3, covariance_type="diag", n_iter=100, random_state=42)
    hmm.fit(features)
    states = hmm.predict(features)

    state_vols = [np.mean(rolling_vol.values[states == i]) for i in range(3)]
    bear_state = int(np.argmax(state_vols))
    rem = [i for i in range(3) if i != bear_state]
    state_means = [np.mean(log_returns.values[states == i]) for i in range(3)]
    bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]

    last_state = states[-1]
    if last_state == bull_state:
        vol = state_vols[bull_state] if state_vols[bull_state] > 0 else 1e-9
        return 0, abs(state_means[bull_state]) / vol
    elif last_state == bear_state:
        vol = state_vols[bear_state] if state_vols[bear_state] > 0 else 1e-9
        return 1, abs(state_means[bear_state]) / vol
    return 2, -0.5

def main():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    print("=" * 80)
    print("STRATEGY 16 v2: HMM ROUTER + S10 ENGINE (VWAP BANDS, OVERNIGHT HOLDS, 0% FEE)")
    print("=" * 80)

    universe = {
        "QQQ": {"bull": "TQQQ", "bear": "SQQQ"},
        "SPY": {"bull": "UPRO", "bear": "SPXS"},
        "SOXX": {"bull": "SOXL", "bear": "SOXS"},
        "IWM": {"bull": "URTY", "bear": "SRTY"}
    }

    print("\nDownloading 30m intraday bars (60 days) for all assets...")
    intraday = {}
    for base, assets in universe.items():
        print(f"  Downloading {base}, {assets['bull']}, {assets['bear']}...")
        df_base = _strip_tz(yf.download(base, period="60d", interval="30m", progress=False))
        df_bull = _strip_tz(yf.download(assets["bull"], period="60d", interval="30m", progress=False))
        df_bear = _strip_tz(yf.download(assets["bear"], period="60d", interval="30m", progress=False))

        for d in (df_base, df_bull, df_bear):
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = [c[0] for c in d.columns]

        df_base["ATR"] = calculate_atr(df_base)
        df_bull["ATR"] = calculate_atr(df_bull)
        df_bear["ATR"] = calculate_atr(df_bear)

        merged = df_base[["Close", "High", "Low", "Volume", "ATR"]].join(
            df_bull[["Close", "ATR"]], lsuffix="_base", rsuffix="_bull"
        ).join(
            df_bear[["Close", "ATR"]], rsuffix="_bear"
        )
        merged.columns = [
            "Close_base", "High_base", "Low_base", "Volume_base", "ATR_base",
            "Close_bull", "ATR_bull", "Close_bear", "ATR_bear"
        ]
        intraday[base] = merged.dropna()

    INITIAL_NAV = 200000.0  # MXN
    COMMISSION = 0.0000  # Alpaca commission-free
    rf_annual = 0.095
    rf_daily = rf_annual / 252.0

    cash = INITIAL_NAV
    active_position = None  # {side, shares, entry_price, peak_price, allocated, base, ticker}

    nav_history = []
    nav_times = []
    trade_logs = []
    closed_trades = []
    route_counts = {b: 0 for b in universe}

    all_dates = sorted(set(intraday["QQQ"].index.strftime("%Y-%m-%d")))
    print(f"\nSimulating {len(all_dates)} days of trading...")

    for date_str in all_dates:
        # --- 1. Daily HMM decode per asset (trained on 30m bars before today) ---
        regimes = {}
        scores = {}
        for base in universe:
            df = intraday[base]
            day_bars_b = df[df.index.strftime("%Y-%m-%d") == date_str]
            if day_bars_b.empty:
                regimes[base], scores[base] = 2, -1.0
                continue
            train = df[df.index < day_bars_b.index[0]]
            regimes[base], scores[base] = decode_regime(train["Close_base"])

        # --- 2. Route: locked to held asset, else best trending score, else ATR% ---
        if active_position:
            target = active_position["base"]
        else:
            trending = {k: v for k, v in scores.items() if regimes[k] in (0, 1)}
            if trending:
                target = max(trending, key=trending.get)
            else:
                atr_pct = {}
                for base in universe:
                    df = intraday[base]
                    prior = df[df.index.strftime("%Y-%m-%d") < date_str]
                    if prior.empty:
                        atr_pct[base] = 0.0
                    else:
                        atr_pct[base] = float(prior["ATR_base"].iloc[-1] / prior["Close_base"].iloc[-1])
                target = max(atr_pct, key=atr_pct.get)

        regime = regimes[target]
        group = intraday[target][intraday[target].index.strftime("%Y-%m-%d") == date_str]
        if group.empty:
            # No bars for target today; NAV carries at last known valuation
            continue
        route_counts[target] += 1

        bull_etf = universe[target]["bull"]
        bear_etf = universe[target]["bear"]

        # Daily sweep interest on idle cash (as in S10 backtest)
        cash = cash * (1.0 + rf_daily / 13.0)

        daily_high = float(group["High_base"].max())
        daily_low = float(group["Low_base"].min())

        cum_pv = 0.0
        cum_vol = 0.0

        for i in range(len(group)):
            bar_time = group.index[i]
            close_base = float(group["Close_base"].iloc[i])
            high_base = float(group["High_base"].iloc[i])
            low_base = float(group["Low_base"].iloc[i])
            vol_base = float(group["Volume_base"].iloc[i])
            atr_base = float(group["ATR_base"].iloc[i])
            close_bull = float(group["Close_bull"].iloc[i])
            atr_bull = float(group["ATR_bull"].iloc[i])
            close_bear = float(group["Close_bear"].iloc[i])
            atr_bear = float(group["ATR_bear"].iloc[i])

            cum_pv += ((high_base + low_base + close_base) / 3.0) * vol_base
            cum_vol += vol_base
            vwap = cum_pv / cum_vol if cum_vol > 0 else close_base

            upper_band = vwap + 1.5 * atr_base
            lower_band = vwap - 1.5 * atr_base

            is_eod = (bar_time.hour == 15 and bar_time.minute == 30) or i == (len(group) - 1)

            current_pv = cash
            if active_position:
                side = active_position["side"]
                current_price = close_bull if side == "long" else close_bear
                active_position["peak_price"] = max(active_position["peak_price"], current_price)

                atr_exec = atr_bull if side == "long" else atr_bear
                stop_threshold = active_position["peak_price"] - 1.5 * atr_exec
                is_stop_out = current_price < stop_threshold

                current_pv += active_position["shares"] * current_price

                if is_stop_out or is_eod:
                    should_hold = False
                    if is_eod and not is_stop_out:
                        in_profit = current_price > active_position["entry_price"]
                        if in_profit:
                            if side == "long" and close_base >= daily_high * 0.995 and regime == 0:
                                should_hold = True
                            elif side == "short" and close_base <= daily_low * 1.005 and regime in (1, 2):
                                should_hold = True
                    if not should_hold:
                        val = active_position["shares"] * current_price * (1.0 - COMMISSION)
                        cash += val
                        pnl = val - active_position["allocated"]
                        exit_type = "TRAILING_STOP" if is_stop_out else "EOD_CLOSE"
                        trade_logs.append(f"  EXIT {active_position['ticker']} ({side}) {date_str} {bar_time.strftime('%H:%M')} via {exit_type} PnL ${pnl:,.2f}")
                        closed_trades.append({"base": active_position["base"], "regime_at_entry": active_position["regime_at_entry"],
                                              "exit": exit_type, "pnl": pnl, "held_overnight": active_position["held_overnight"]})
                        active_position = None
                        current_pv = cash
                    elif is_eod:
                        active_position["held_overnight"] = True
                        trade_logs.append(f"  HOLD OVERNIGHT {active_position['ticker']} ({side}) {date_str}")

            # Entries (flat, not EOD)
            if not active_position and not is_eod:
                entry = None
                if regime == 1 and close_base < lower_band:
                    entry = ("short", bear_etf, close_bear, "BEAR_BREAK")
                elif regime == 0 and close_base > upper_band:
                    entry = ("long", bull_etf, close_bull, "BULL_BREAK")
                elif regime == 2:
                    if close_base < lower_band:
                        entry = ("long", bull_etf, close_bull, "CHOP_REVERSION")
                    elif close_base > upper_band:
                        entry = ("short", bear_etf, close_bear, "CHOP_REVERSION")
                if entry:
                    side, ticker, px, tag = entry
                    alloc = current_pv * 0.90
                    shares = alloc / (px * (1.0 + COMMISSION))
                    cash -= alloc
                    active_position = {
                        "side": side, "shares": shares, "entry_price": px,
                        "peak_price": px, "allocated": alloc, "base": target,
                        "ticker": ticker, "regime_at_entry": tag, "held_overnight": False
                    }
                    trade_logs.append(f"  ENTRY {ticker} ({side}) {date_str} {bar_time.strftime('%H:%M')} [{tag} {target}]")
            elif active_position and regime == 2 and not is_eod:
                # Settle at VWAP center during chop
                side = active_position["side"]
                if (side == "long" and close_base >= vwap) or (side == "short" and close_base <= vwap):
                    current_price = close_bull if side == "long" else close_bear
                    val = active_position["shares"] * current_price * (1.0 - COMMISSION)
                    cash += val
                    pnl = val - active_position["allocated"]
                    trade_logs.append(f"  SETTLE {active_position['ticker']} ({side}) {date_str} {bar_time.strftime('%H:%M')} VWAP PnL ${pnl:,.2f}")
                    closed_trades.append({"base": active_position["base"], "regime_at_entry": active_position["regime_at_entry"],
                                          "exit": "VWAP_SETTLE", "pnl": pnl, "held_overnight": active_position["held_overnight"]})
                    active_position = None
                    current_pv = cash

            nav_history.append(current_pv)
            nav_times.append(bar_time)

    # --- 3. Metrics ---
    df_nav = pd.DataFrame({"NAV": nav_history}, index=pd.DatetimeIndex(nav_times))
    final_nav = float(df_nav["NAV"].iloc[-1])
    total_ret = final_nav / INITIAL_NAV - 1.0

    days = (df_nav.index[-1] - df_nav.index[0]).days
    years = max(days / 365.25, 0.01)
    cagr = (final_nav / INITIAL_NAV) ** (1.0 / years) - 1.0

    daily_pct = df_nav["NAV"].resample("1D").last().pct_change().dropna()
    ann_vol = daily_pct.std() * np.sqrt(252)
    sharpe = (cagr - rf_annual) / ann_vol if ann_vol > 0 else 0.0

    roll_max = df_nav["NAV"].cummax()
    max_dd = float(((df_nav["NAV"] - roll_max) / roll_max).min())

    print("\n" + "=" * 80)
    print("BACKTEST RESULTS: S16 v2 (HMM ROUTER + S10 ENGINE)")
    print("=" * 80)
    print(f"Final NAV       : ${final_nav:,.2f} MXN")
    print(f"Total Return    : {total_ret*100:+.2f}%")
    print(f"CAGR            : {cagr*100:+.2f}%")
    print(f"Annual Vol      : {ann_vol*100:.2f}%")
    print(f"Sharpe (Rf=9.5%): {sharpe:.2f}")
    print(f"Max Drawdown    : {max_dd*100:.2f}%")
    print(f"Routing days    : {route_counts}")
    print("=" * 80)

    if closed_trades:
        tdf = pd.DataFrame(closed_trades)
        print("\nPnL BY ENTRY TYPE:")
        g = tdf.groupby("regime_at_entry")["pnl"].agg(["count", "sum", "mean"])
        g["win_rate"] = tdf.groupby("regime_at_entry")["pnl"].apply(lambda s: (s > 0).mean() * 100.0)
        print(g.round(2).to_string())
        print("\nPnL BY EXIT REASON:")
        g = tdf.groupby("exit")["pnl"].agg(["count", "sum", "mean"])
        g["win_rate"] = tdf.groupby("exit")["pnl"].apply(lambda s: (s > 0).mean() * 100.0)
        print(g.round(2).to_string())
        print("\nPnL BY ROUTED ASSET:")
        g = tdf.groupby("base")["pnl"].agg(["count", "sum", "mean"])
        print(g.round(2).to_string())
        overnight = tdf[tdf["held_overnight"]]
        print(f"\nOvernight-held trades: {len(overnight)}, PnL: ${overnight['pnl'].sum():,.2f}")
        print(f"Total trades: {len(tdf)}, Total PnL: ${tdf['pnl'].sum():,.2f}")

    # Generate standard markdown backtest report
    report_md = f"""# Strategy 16 v2 Backtest Report
**Executed:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Asset Universe:** QQQ, SPY, SOXX, IWM (3x Leveraged Bull/Bear Pairs)

## Performance Metrics
* **Final NAV:** ${final_nav:,.2f} MXN
* **Total Return:** {total_ret*100:+.2f}%
* **Time-Weighted CAGR:** {cagr*100:+.2f}%
* **Annual Volatility:** {ann_vol*100:.2f}%
* **Sharpe Ratio (Rf=9.5%):** {sharpe:.2f}
* **Maximum Drawdown:** {max_dd*100:.2f}%
* **Routing Days Map:** {route_counts}
"""
    if closed_trades:
        tdf = pd.DataFrame(closed_trades)
        overnight = tdf[tdf["held_overnight"]]
        report_md += f"""
## Summary Diagnostics
* **Total Trades Executed:** {len(tdf)}
* **Total PnL:** ${tdf['pnl'].sum():,.2f} MXN
* **Overnight Held Trades:** {len(overnight)} (PnL: ${overnight['pnl'].sum():,.2f} MXN)
"""
    with open(os.path.join(dir_path, "strategy16_backtest_report.md"), "w", encoding="utf-8") as f:
        f.write(report_md)

    df_nav.to_csv(os.path.join(dir_path, "strategy16_backtest_nav.csv"))
    print("\nSaved NAV curve to strategy16_backtest_nav.csv")

if __name__ == "__main__":
    main()
