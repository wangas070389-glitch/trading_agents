"""
WALK-FORWARD VALIDATION: S10 / S11 / S16 frozen July-2026 configs
==================================================================
The July 2026 optimization tuned these strategies on their most recent
60 trading days -- the same window their published backtests report.
That makes the published numbers in-sample ceilings, not forecasts.

This harness re-runs each strategy's EXACT engine (parameters frozen:
1h bars, 60d diag-HMM lookback, hybrid 3.0->1.5 ATR stop, 0% commission,
90% allocation, same entry/exit rules) over every consecutive 60-trading-day
window available in ~730 days of 1h history. The most recent window is the
tuning window and is labeled IN-SAMPLE; all earlier windows are data the
July configs never saw.

Engines are verbatim copies of backtest_strategy10/11/16.py day-loops,
parameterized by window (repo convention: research variants live in scratch/).

Output: walkforward_report.md (repo root) + console summary.
Usage:  python scratch/walkforward_intraday.py
"""
import os
import sys
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WINDOW = 60          # trading days per test window
WARMUP = 60          # days reserved before the first window for HMM training
INITIAL_NAV = 200000.0
COMMISSION = 0.0000
RF_ANNUAL = 0.095    # same Sharpe convention as the published backtests
RF_DAILY = RF_ANNUAL / 252.0


def _strip_tz(df):
    if df.index.tz is not None:
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)
    return df


def _flat(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df


def calculate_atr(df, period=14):
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.fillna(tr.expanding().mean())


def calculate_cci(df, period=10):
    tp = (df['High'] + df['Low'] + df['Close']) / 3.0
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return ((tp - sma) / (0.015 * mad)).fillna(0.0)


def calculate_adx(df, period=7, with_di=False):
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    up_move = df['High'] - df['High'].shift(1)
    down_move = df['Low'].shift(1) - df['Low']
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr_s = tr.rolling(window=period).mean()
    plus_s = pd.Series(plus_dm, index=df.index).rolling(window=period).mean()
    minus_s = pd.Series(minus_dm, index=df.index).rolling(window=period).mean()
    plus_di = (plus_s / tr_s) * 100.0
    minus_di = (minus_s / tr_s) * 100.0
    dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di).replace(0.0, np.nan)) * 100.0
    adx = dx.rolling(window=period).mean().fillna(20.0)
    if with_di:
        return adx, plus_di.fillna(0.0), minus_di.fillna(0.0)
    return adx


def decode_regime(train_closes):
    """Shared 3-state diag HMM regime decoder (0=bull, 1=bear, 2=chop).
    Returns (regime, trend_score)."""
    log_returns = np.log(train_closes / train_closes.shift(1)).fillna(0.0)
    rolling_vol = log_returns.rolling(window=10).std().fillna(0.0)
    features = np.column_stack([log_returns.values, rolling_vol.values])
    try:
        hmm = GaussianHMM(n_components=3, covariance_type="diag", n_iter=100, random_state=42)
        hmm.fit(features)
        states = hmm.predict(features)
        state_vols = [np.mean(rolling_vol.values[states == i]) if np.any(states == i) else 1e9 for i in range(3)]
        bear_state = int(np.argmax(state_vols))
        rem = [i for i in range(3) if i != bear_state]
        state_means = [np.mean(log_returns.values[states == i]) if np.any(states == i) else -1e9 for i in range(3)]
        bull_state = rem[0] if state_means[rem[0]] > state_means[rem[1]] else rem[1]
        last = states[-1]
        if last == bull_state:
            return 0, abs(state_means[bull_state]) / state_vols[bull_state]
        if last == bear_state:
            return 1, abs(state_means[bear_state]) / state_vols[bear_state]
        return 2, -0.5
    except Exception:
        return 2, -1.0


def metrics(nav_series_daily, trades):
    """Window metrics using the same conventions as the published backtests."""
    final = float(nav_series_daily.iloc[-1])
    total_ret = final / INITIAL_NAV - 1.0
    days = max((nav_series_daily.index[-1] - nav_series_daily.index[0]).days, 1)
    years = max(days / 365.25, 0.01)
    cagr = (final / INITIAL_NAV) ** (1.0 / years) - 1.0
    daily_pct = nav_series_daily.pct_change().dropna()
    ann_vol = daily_pct.std() * np.sqrt(252)
    sharpe = (cagr - RF_ANNUAL) / ann_vol if ann_vol > 0 else 0.0
    roll_max = nav_series_daily.cummax()
    max_dd = float(((nav_series_daily - roll_max) / roll_max).min())
    closed = [t for t in trades if t != 0.0]
    win_rate = (sum(1 for p in closed if p > 0) / len(closed) * 100.0) if closed else float("nan")
    return dict(ret=total_ret, sharpe=sharpe, max_dd=max_dd,
                n_trades=len(closed), win_rate=win_rate)


# ----------------------------------------------------------------------------
# S10: VWAP channel breakout/reversion (engine copied from backtest_strategy10)
# ----------------------------------------------------------------------------
def build_s10_s11_data():
    qqq = _strip_tz(_flat(yf.download("QQQ", period="730d", interval="1h", progress=False)))
    tqqq = _strip_tz(_flat(yf.download("TQQQ", period="730d", interval="1h", progress=False)))
    sqqq = _strip_tz(_flat(yf.download("SQQQ", period="730d", interval="1h", progress=False)))

    # S10 frame
    q10, t10, s10 = qqq.copy(), tqqq.copy(), sqqq.copy()
    q10["ATR"] = calculate_atr(q10)
    t10["ATR"] = calculate_atr(t10)
    s10["ATR"] = calculate_atr(s10)
    m10 = q10[["Close", "High", "Low", "Volume", "ATR"]].join(
        t10[["Close", "ATR"]], lsuffix="_QQQ", rsuffix="_TQQQ").join(
        s10[["Close", "ATR"]], rsuffix="_SQQQ")
    m10.columns = ["Close_QQQ", "High_QQQ", "Low_QQQ", "Volume_QQQ", "ATR_QQQ",
                   "Close_TQQQ", "ATR_TQQQ", "Close_SQQQ", "ATR_SQQQ"]
    m10 = m10.dropna()
    m10["DateOnly"] = m10.index.strftime("%Y-%m-%d")

    # S11 frame
    t11, s11 = tqqq.copy(), sqqq.copy()
    for d in (t11, s11):
        d["ATR"] = calculate_atr(d)
        d["CCI"] = calculate_cci(d)
        adx, pdi, mdi = calculate_adx(d, with_di=True)
        d["ADX"], d["DI+"], d["DI-"] = adx, pdi, mdi
    m11 = qqq[["Close", "High", "Low", "Volume"]].join(
        t11[["Close", "ATR", "CCI", "ADX", "DI+", "DI-"]], lsuffix="_QQQ", rsuffix="_TQQQ").join(
        s11[["Close", "ATR", "CCI", "ADX", "DI+", "DI-"]], rsuffix="_SQQQ")
    m11.columns = ["Close_QQQ", "High_QQQ", "Low_QQQ", "Volume_QQQ",
                   "Close_TQQQ", "ATR_TQQQ", "CCI_TQQQ", "ADX_TQQQ", "DI+_TQQQ", "DI-_TQQQ",
                   "Close_SQQQ", "ATR_SQQQ", "CCI_SQQQ", "ADX_SQQQ", "DI+_SQQQ", "DI-_SQQQ"]
    m11 = m11.dropna()
    m11["DateOnly"] = m11.index.strftime("%Y-%m-%d")
    return m10, m11


def run_s10(merged, window_dates):
    cash = INITIAL_NAV
    active = None
    daily_nav = {}
    trade_pnls = []

    for date_str in window_dates:
        group = merged[merged["DateOnly"] == date_str]
        if group.empty:
            continue
        first_bar = group.index[0]
        train = merged[merged.index < first_bar]
        u_dates = sorted(set(train.index.date))
        if len(u_dates) < 60:
            regime = 2
        else:
            tgt = u_dates[-60:]
            regime, _ = decode_regime(train[train.index.date >= tgt[0]]["Close_QQQ"])

        cum_pv = cum_vol = 0.0
        cash *= (1.0 + RF_DAILY / 13.0)
        d_high = float(group["High_QQQ"].max())
        d_low = group["Low_QQQ"].min()
        pv = cash

        for i in range(len(group)):
            bar = group.index[i]
            c_q = float(group["Close_QQQ"].iloc[i]); h_q = float(group["High_QQQ"].iloc[i])
            l_q = float(group["Low_QQQ"].iloc[i]); v_q = float(group["Volume_QQQ"].iloc[i])
            a_q = float(group["ATR_QQQ"].iloc[i])
            c_t = float(group["Close_TQQQ"].iloc[i]); a_t = float(group["ATR_TQQQ"].iloc[i])
            c_s = float(group["Close_SQQQ"].iloc[i]); a_s = float(group["ATR_SQQQ"].iloc[i])

            cum_pv += ((h_q + l_q + c_q) / 3.0) * v_q
            cum_vol += v_q
            vwap = cum_pv / cum_vol if cum_vol > 0 else c_q
            upper, lower = vwap + 1.0 * a_q, vwap - 1.0 * a_q
            is_eod = (bar.hour == 15 and bar.minute == 0) or i == len(group) - 1

            pv = cash
            if active:
                price = c_t if active["side"] == "long" else c_s
                active["peak_price"] = max(active["peak_price"], price)
                atr_e = a_t if active["side"] == "long" else a_s
                profit_atr = (price - active["entry_price"]) / atr_e
                stop_mult = 3.0 if profit_atr <= 1.5 else 1.5
                stop_out = price < active["peak_price"] - stop_mult * atr_e
                pv += active["shares"] * price
                if stop_out or is_eod:
                    hold = False
                    if is_eod and not stop_out and price > active["entry_price"]:
                        if active["side"] == "long" and c_q >= d_high * 0.995 and regime == 0:
                            hold = True
                        elif active["side"] == "short" and c_q <= d_low * 1.005 and regime in (1, 2):
                            hold = True
                    if not hold:
                        val = active["shares"] * price * (1.0 - COMMISSION)
                        cash += val
                        trade_pnls.append(val - active["allocated"])
                        active = None
                        pv = cash

            if not active and not is_eod:
                entry = None
                if regime == 1 and c_q < lower:
                    entry = ("short", c_s)
                elif regime == 0 and c_q > upper:
                    entry = ("long", c_t)
                elif regime == 2:
                    if c_q < lower:
                        entry = ("long", c_t)
                    elif c_q > upper:
                        entry = ("short", c_s)
                if entry:
                    side, px = entry
                    alloc = pv * 0.90
                    cash -= alloc
                    active = dict(side=side, shares=alloc / (px * (1.0 + COMMISSION)),
                                  entry_price=px, peak_price=px, allocated=alloc)
            elif active and regime == 2 and not is_eod:
                side = active["side"]
                if (side == "long" and c_q >= vwap) or (side == "short" and c_q <= vwap):
                    price = c_t if side == "long" else c_s
                    val = active["shares"] * price * (1.0 - COMMISSION)
                    cash += val
                    trade_pnls.append(val - active["allocated"])
                    active = None
                    pv = cash
        daily_nav[pd.Timestamp(date_str)] = pv
    return metrics(pd.Series(daily_nav).sort_index(), trade_pnls)


# ----------------------------------------------------------------------------
# S11: direct-asset CCI-ADX (engine copied from backtest_strategy11)
# ----------------------------------------------------------------------------
def run_s11(merged, window_dates):
    cash = INITIAL_NAV
    active = None
    daily_nav = {}
    trade_pnls = []

    for date_str in window_dates:
        group = merged[merged["DateOnly"] == date_str]
        if group.empty:
            continue
        first_bar = group.index[0]
        train = merged[merged.index < first_bar]
        u_dates = sorted(set(train["DateOnly"]))
        if len(u_dates) < 60:
            regime = 2
        else:
            tgt = u_dates[-60:]
            regime, _ = decode_regime(train[train["DateOnly"] >= tgt[0]]["Close_QQQ"])

        cash *= (1.0 + RF_DAILY / 13.0)
        d_high = float(group["High_QQQ"].max())
        d_low = group["Low_QQQ"].min()
        pv = cash

        for i in range(len(group)):
            bar = group.index[i]
            c_q = float(group["Close_QQQ"].iloc[i])
            c_t = float(group["Close_TQQQ"].iloc[i]); cci_t = float(group["CCI_TQQQ"].iloc[i])
            adx_t = float(group["ADX_TQQQ"].iloc[i]); dip_t = float(group["DI+_TQQQ"].iloc[i])
            dim_t = float(group["DI-_TQQQ"].iloc[i]); a_t = float(group["ATR_TQQQ"].iloc[i])
            c_s = float(group["Close_SQQQ"].iloc[i]); cci_s = float(group["CCI_SQQQ"].iloc[i])
            adx_s = float(group["ADX_SQQQ"].iloc[i]); dip_s = float(group["DI+_SQQQ"].iloc[i])
            dim_s = float(group["DI-_SQQQ"].iloc[i]); a_s = float(group["ATR_SQQQ"].iloc[i])
            is_eod = (bar.hour == 15 and bar.minute == 30) or i == len(group) - 1

            pv = cash
            if active:
                price = c_t if active["side"] == "long" else c_s
                active["peak_price"] = max(active["peak_price"], price)
                atr_e = a_t if active["side"] == "long" else a_s
                profit_atr = (price - active["entry_price"]) / atr_e
                stop_mult = 3.0 if profit_atr <= 1.5 else 1.5
                stop_out = price < active["peak_price"] - stop_mult * atr_e
                pv += active["shares"] * price
                if stop_out or is_eod:
                    hold = False
                    if is_eod and not stop_out and price > active["entry_price"]:
                        if active["side"] == "long" and c_q >= d_high * 0.995 and regime in (0, 2):
                            hold = True
                        elif active["side"] == "short" and c_q <= d_low * 1.005 and regime in (1, 2):
                            hold = True
                    if not hold:
                        val = active["shares"] * price * (1.0 - COMMISSION)
                        cash += val
                        trade_pnls.append(val - active["allocated"])
                        active = None
                        pv = cash

            if not active and not is_eod:
                entry = None
                if regime in (0, 2) and adx_t >= 22.0 and cci_t > 100.0 and dip_t > dim_t:
                    entry = ("long", c_t)
                elif regime in (1, 2) and adx_s >= 22.0 and cci_s > 100.0 and dip_s > dim_s:
                    entry = ("short", c_s)
                elif adx_t < 22.0 and cci_t < -150.0:
                    entry = ("long", c_t)
                elif adx_s < 22.0 and cci_s < -150.0:
                    entry = ("short", c_s)
                if entry:
                    side, px = entry
                    alloc = pv * 0.90
                    cash -= alloc
                    active = dict(side=side, shares=alloc / (px * (1.0 + COMMISSION)),
                                  entry_price=px, peak_price=px, allocated=alloc)
            elif active and not is_eod:
                side = active["side"]
                if side == "long" and cci_t >= 0.0:
                    val = active["shares"] * c_t * (1.0 - COMMISSION)
                    cash += val
                    trade_pnls.append(val - active["allocated"])
                    active = None
                    pv = cash
                elif side == "short" and cci_s >= 0.0:
                    val = active["shares"] * c_s * (1.0 - COMMISSION)
                    cash += val
                    trade_pnls.append(val - active["allocated"])
                    active = None
                    pv = cash
        daily_nav[pd.Timestamp(date_str)] = pv
    return metrics(pd.Series(daily_nav).sort_index(), trade_pnls)


# ----------------------------------------------------------------------------
# S16: multi-asset HMM router (engine copied from backtest_strategy16)
# ----------------------------------------------------------------------------
UNIVERSE = {
    "QQQ": {"bull": "TQQQ", "bear": "SQQQ"},
    "SPY": {"bull": "UPRO", "bear": "SPXS"},
    "SOXX": {"bull": "SOXL", "bear": "SOXS"},
    "IWM": {"bull": "URTY", "bear": "SRTY"},
}


def build_s16_data():
    intraday = {}
    for base, assets in UNIVERSE.items():
        db = _strip_tz(_flat(yf.download(base, period="730d", interval="1h", progress=False)))
        dbu = _strip_tz(_flat(yf.download(assets["bull"], period="730d", interval="1h", progress=False)))
        dbe = _strip_tz(_flat(yf.download(assets["bear"], period="730d", interval="1h", progress=False)))
        db["ATR"] = calculate_atr(db)
        for d in (dbu, dbe):
            d["ATR"] = calculate_atr(d)
            d["CCI"] = calculate_cci(d)
            d["ADX"] = calculate_adx(d)
        merged = db[["Close", "High", "Low", "Volume", "ATR"]].join(
            dbu[["Close", "ATR", "CCI", "ADX"]], lsuffix="_base", rsuffix="_bull").join(
            dbe[["Close", "ATR", "CCI", "ADX"]], rsuffix="_bear")
        merged.columns = ["Close_base", "High_base", "Low_base", "Volume_base", "ATR_base",
                          "Close_bull", "ATR_bull", "CCI_bull", "ADX_bull",
                          "Close_bear", "ATR_bear", "CCI_bear", "ADX_bear"]
        intraday[base] = merged.dropna()
    return intraday


def run_s16(intraday, window_dates):
    cash = INITIAL_NAV
    active = None
    daily_nav = {}
    trade_pnls = []

    for date_str in window_dates:
        regimes, scores = {}, {}
        for base in UNIVERSE:
            df = intraday[base]
            sub = df[df.index.strftime("%Y-%m-%d") < date_str]
            u_dates = sorted(set(sub.index.date))
            if len(u_dates) < 60:
                regimes[base], scores[base] = 2, -1
                continue
            tgt = u_dates[-60:]
            regimes[base], scores[base] = decode_regime(sub[sub.index.date >= tgt[0]]["Close_base"])

        if active:
            target = active["base"]
        else:
            trending = {k: v for k, v in scores.items() if regimes[k] in (0, 1)}
            target = max(trending, key=trending.get) if trending else "QQQ"
        t_regime = regimes[target]
        day = intraday[target][intraday[target].index.strftime("%Y-%m-%d") == date_str]
        if day.empty:
            continue

        c_bull = c_bear = None
        for i in range(len(day)):
            c_bull = float(day["Close_bull"].iloc[i]); a_bull = float(day["ATR_bull"].iloc[i])
            cci_bull = float(day["CCI_bull"].iloc[i]); adx_bull = float(day["ADX_bull"].iloc[i])
            c_bear = float(day["Close_bear"].iloc[i]); a_bear = float(day["ATR_bear"].iloc[i])
            cci_bear = float(day["CCI_bear"].iloc[i]); adx_bear = float(day["ADX_bear"].iloc[i])

            if active:
                side = active["side"]
                price = c_bull if side == "long" else c_bear
                active["peak_price"] = max(active.get("peak_price", price), price)
                atr_v = a_bull if side == "long" else a_bear
                profit_atr = (price - active["buy_price"]) / atr_v
                stop_mult = 3.0 if profit_atr <= 1.5 else 1.5
                stop_out = price < active["peak_price"] - stop_mult * atr_v
                flip = (side == "long" and t_regime != 0) or (side == "short" and t_regime != 1)
                if stop_out or flip:
                    val = active["shares"] * price
                    cash += val * (1.0 - COMMISSION)
                    trade_pnls.append(val - active["allocated"])
                    active = None

            if not active:
                if t_regime == 0 and cci_bull < -100.0 and adx_bull > 20.0:
                    alloc = cash * 0.90
                    shares = alloc / (c_bull * (1.0 + COMMISSION))
                    if shares > 0.01:
                        cash -= alloc
                        active = dict(side="long", shares=shares, buy_price=c_bull,
                                      peak_price=c_bull, allocated=alloc, base=target)
                elif t_regime == 1 and cci_bear < -100.0 and adx_bear > 20.0:
                    alloc = cash * 0.90
                    shares = alloc / (c_bear * (1.0 + COMMISSION))
                    if shares > 0.01:
                        cash -= alloc
                        active = dict(side="short", shares=shares, buy_price=c_bear,
                                      peak_price=c_bear, allocated=alloc, base=target)

        eod_val = 0.0
        if active:
            eod_val = active["shares"] * (c_bull if active["side"] == "long" else c_bear)
        daily_nav[pd.Timestamp(date_str)] = cash + eod_val
    return metrics(pd.Series(daily_nav).sort_index(), trade_pnls)


# ----------------------------------------------------------------------------
def make_windows(all_dates):
    """Consecutive 60-day windows aligned so the LAST one equals the July
    tuning window; earliest windows need >= WARMUP prior days for the HMM."""
    windows = []
    end = len(all_dates)
    while end - WINDOW >= WARMUP:
        windows.append(all_dates[end - WINDOW:end])
        end -= WINDOW
    return list(reversed(windows))


def main():
    print("=" * 80)
    print("WALK-FORWARD VALIDATION: S10 / S11 / S16 (frozen July 2026 configs)")
    print("=" * 80)

    print("\nDownloading QQQ/TQQQ/SQQQ 730d 1h data...")
    m10, m11 = build_s10_s11_data()
    print("Downloading S16 universe 730d 1h data (12 tickers)...")
    s16_data = build_s16_data()

    dates_1011 = sorted(set(m10["DateOnly"]))
    dates_16 = sorted(set(s16_data["QQQ"].index.strftime("%Y-%m-%d")))

    results = {}
    for name, runner, dates, data in (
        ("S10 VWAP", run_s10, dates_1011, m10),
        ("S11 CCI-ADX", run_s11, dates_1011, m11),
        ("S16 Router", run_s16, dates_16, s16_data),
    ):
        windows = make_windows(dates)
        print(f"\n{name}: {len(windows)} windows of {WINDOW} trading days "
              f"({dates[0]} .. {dates[-1]})")
        rows = []
        for w_i, w in enumerate(windows):
            label = "IN-SAMPLE (tuning)" if w_i == len(windows) - 1 else "out-of-sample"
            res = runner(data, w)
            res.update(start=w[0], end=w[-1], label=label)
            rows.append(res)
            print(f"  {w[0]} .. {w[-1]}  ret {res['ret']*100:+7.2f}%  "
                  f"sharpe {res['sharpe']:+6.2f}  dd {res['max_dd']*100:6.2f}%  "
                  f"trades {res['n_trades']:3d}  [{label}]")
        results[name] = rows

    # ---- report ----
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Walk-Forward Validation — S10 / S11 / S16 (Frozen July 2026 Configs)",
        f"**Generated:** {now} | Window: {WINDOW} trading days | Data: ~730d of 1h bars",
        "",
        "The July 2026 optimization tuned these strategies on their most recent 60 trading",
        "days. Every earlier window below is **data the frozen configs never saw** — the",
        "closest thing to live evidence that doesn't require waiting.",
        "",
    ]
    for name, rows in results.items():
        oos = [r for r in rows if r["label"] == "out-of-sample"]
        ins = [r for r in rows if r["label"] != "out-of-sample"]
        lines += [f"## {name}", "",
                  "| Window | Return (60d) | Sharpe | MaxDD | Trades | Win rate | Sample |",
                  "| :--- | ---: | ---: | ---: | ---: | ---: | :--- |"]
        for r in rows:
            wr = f"{r['win_rate']:.0f}%" if not np.isnan(r["win_rate"]) else "n/a"
            lines.append(f"| {r['start']} → {r['end']} | {r['ret']*100:+.2f}% | "
                         f"{r['sharpe']:+.2f} | {r['max_dd']*100:.2f}% | "
                         f"{r['n_trades']} | {wr} | {r['label']} |")
        if oos:
            rets = [r["ret"] for r in oos]
            pos = sum(1 for x in rets if x > 0)
            lines += ["",
                      f"**Out-of-sample summary ({len(oos)} windows):** "
                      f"mean {np.mean(rets)*100:+.2f}%, median {np.median(rets)*100:+.2f}%, "
                      f"worst {min(rets)*100:+.2f}%, best {max(rets)*100:+.2f}%, "
                      f"{pos}/{len(oos)} positive. "
                      + (f"In-sample (tuning) window: {ins[0]['ret']*100:+.2f}%." if ins else ""),
                      ""]
    lines += [
        "## How to read this",
        "- **If out-of-sample windows cluster near the in-sample result**, the edge is",
        "  likely real and the live paper record should confirm it.",
        "- **If the in-sample window is a clear outlier**, the July optimization mostly",
        "  fit noise; expect live performance closer to the out-of-sample mean.",
        "- Same engines, parameters and conventions as the published backtests",
        "  (1h bars, 60d diag-HMM, hybrid 3.0→1.5 ATR stop, 0% commission, Rf 9.5%).",
        "- Caveat: consecutive windows share the same underlying market era (2024-2026",
        "  bull regime dominates); this validates robustness, not all-weather behavior.",
    ]
    out = os.path.join(ROOT, "walkforward_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nReport written to {out}")


if __name__ == "__main__":
    main()
