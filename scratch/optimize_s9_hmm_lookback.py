"""
Strategy 9 HMM Lookback Grid Search
=====================================
Tests different rolling lookback windows for the SPY daily HMM regime
classifier used in S9's stat-arb logic.

Hypothesis: The current 5-year full-history HMM may be slow to react to
regime changes. A rolling 252d (1 year) or 504d (2 year) window may
produce crisper regime labeling and better stat-arb portfolio returns.

Lookbacks to test: 252d (1y), 504d (2y), 756d (3y), full (5y)
"""
import os
import sys
import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import statsmodels.api as sm

INITIAL_NAV = 200_000.0
MONTHLY_CONTRIBUTION = 2_000.0
COMMISSION = 0.0029
RF_DAILY = 0.095 / 252.0

def _strip_tz(df):
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    df.index = df.index.normalize()
    return df

def run_s9_backtest(prices, s1_rets, s4_rets, lookback_days, label):
    pairs = [
        ("BTC-USD", "ETH-USD"),
        ("EURUSD=X", "GBPUSD=X"),
    ]

    sim_dates = prices.index[252:]
    cash = INITIAL_NAV
    portfolio_value = INITIAL_NAV
    last_month = None
    nav_list = []
    active_trades = {}

    for date in sim_dates:
        if last_month is not None and date.month != last_month:
            cash += MONTHLY_CONTRIBUTION
            portfolio_value += MONTHLY_CONTRIBUTION
        last_month = date.month

        sub_prices = prices.loc[:date]
        if len(sub_prices) < 200:
            continue

        spy_sub = sub_prices["SPY"].pct_change().dropna()
        if lookback_days is not None and len(spy_sub) > lookback_days:
            spy_sub = spy_sub.iloc[-lookback_days:]
        spy_arr = spy_sub.values.reshape(-1, 1)

        try:
            roll_hmm = GaussianHMM(n_components=3, covariance_type="full",
                                    n_iter=100, random_state=42)
            roll_hmm.fit(spy_arr)
            roll_regimes = roll_hmm.predict(spy_arr)

            roll_means = [np.mean(spy_arr[roll_regimes == i]) if np.any(roll_regimes == i) else 0.0
                          for i in range(3)]
            roll_vols  = [np.std(spy_arr[roll_regimes == i])  if np.any(roll_regimes == i) else 0.0
                          for i in range(3)]

            bear_s = int(np.argmax(roll_vols))
            rem_s  = [i for i in range(3) if i != bear_s]
            bull_s = rem_s[0] if roll_means[rem_s[0]] > roll_means[rem_s[1]] else rem_s[1]

            cur_state = roll_regimes[-1]
            if cur_state == bull_s:
                regime = 0
            elif cur_state == bear_s:
                regime = 1
            else:
                regime = 2
        except Exception:
            regime = 2

        day_rets = prices.loc[:date].pct_change().iloc[-1]

        if regime != 2 and active_trades:
            for pair in list(active_trades.keys()):
                trade = active_trades[pair]
                y_t, x_t = pair
                y_p = float(sub_prices[y_t].iloc[-1])
                x_p = float(sub_prices[x_t].iloc[-1])
                if trade["side"] == "long_spread":
                    val = trade["qty_y"] * y_p - trade["qty_x"] * x_p
                else:
                    val = -trade["qty_y"] * y_p + trade["qty_x"] * x_p
                cash += val * (1.0 - COMMISSION)
                del active_trades[pair]

        if regime == 0:
            r1 = s1_rets.loc[date] if date in s1_rets.index else 0.0
            r4 = s4_rets.loc[date] if date in s4_rets.index else 0.0
            daily_ret = 0.5 * r1 + 0.5 * r4
            portfolio_value = portfolio_value * (1.0 + daily_ret)
            cash = cash * (1.0 + RF_DAILY)
        elif regime == 1:
            rgld = day_rets["GLD"] if not pd.isna(day_rets["GLD"]) else 0.0
            daily_ret = 0.5 * rgld + 0.5 * RF_DAILY
            portfolio_value = portfolio_value * (1.0 + daily_ret)
            cash = cash * (1.0 + RF_DAILY)
        else:
            cash = cash * (1.0 + RF_DAILY)
            portfolio_value = cash

            for pair in pairs:
                y_t, x_t = pair
                try:
                    y_ser = np.log(sub_prices[y_t].iloc[-120:].astype(float))
                    x_ser = np.log(sub_prices[x_t].iloc[-120:].astype(float))
                    y_p = float(sub_prices[y_t].iloc[-1])
                    x_p = float(sub_prices[x_t].iloc[-1])
                    if len(y_ser) < 30:
                        continue
                    X = sm.add_constant(x_ser)
                    res = sm.OLS(y_ser, X).fit()
                    beta = res.params.iloc[1] if len(res.params) > 1 else 0.0
                    spread = y_ser.iloc[-1] - beta * x_ser.iloc[-1]
                    spread_hist = y_ser - beta * x_ser
                    spread_mean = spread_hist.mean()
                    spread_std = spread_hist.std()
                    if spread_std < 1e-8:
                        continue
                    z = (spread - spread_mean) / spread_std
                    alloc = cash * 0.10
                    if pair not in active_trades:
                        if z > 1.5:
                            qty_y = (alloc * (1.0 - COMMISSION)) / y_p
                            qty_x = beta * qty_y
                            active_trades[pair] = {"side": "short_spread", "qty_y": qty_y, "qty_x": qty_x}
                        elif z < -1.5:
                            qty_y = (alloc * (1.0 - COMMISSION)) / y_p
                            qty_x = beta * qty_y
                            active_trades[pair] = {"side": "long_spread", "qty_y": qty_y, "qty_x": qty_x}
                    else:
                        trade = active_trades[pair]
                        if abs(z) < 0.3:
                            if trade["side"] == "long_spread":
                                val = trade["qty_y"] * y_p - trade["qty_x"] * x_p
                            else:
                                val = -trade["qty_y"] * y_p + trade["qty_x"] * x_p
                            cash += val * (1.0 - COMMISSION)
                            del active_trades[pair]
                except Exception:
                    continue

        nav_list.append(portfolio_value)

    nav_series = pd.Series(nav_list)
    if len(nav_series) < 5:
        return label, None, None, None, None

    total_return = (nav_series.iloc[-1] / nav_series.iloc[0] - 1.0) * 100.0
    rets = nav_series.pct_change().dropna()
    sharpe = (rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0.0
    rolling_max = nav_series.cummax()
    dd = (nav_series - rolling_max) / rolling_max
    max_dd = dd.min() * 100.0
    final_nav = nav_series.iloc[-1]

    return label, total_return, sharpe, max_dd, final_nav


if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.abspath(__file__))
    parent_path = os.path.dirname(dir_path)

    print("=" * 70)
    print("STRATEGY 9: HMM LOOKBACK GRID SEARCH (Daily SPY returns)")
    print("=" * 70)

    tickers = ["SPY", "GLD", "BTC-USD", "ETH-USD", "EURUSD=X", "GBPUSD=X"]
    print(f"Downloading 5y daily data for {tickers}...")
    data = yf.download(tickers, start="2021-06-20", end="2026-07-01",
                        interval="1d", group_by="ticker", progress=False)

    prices = pd.DataFrame()
    for t in tickers:
        try:
            if t in data.columns.levels[0]:
                prices[t] = data[t]["Close"].ffill().bfill()
        except Exception:
            pass
    prices.index = pd.to_datetime(prices.index)
    prices = _strip_tz(prices)

    s1_rets = pd.Series(dtype=float)
    s4_rets = pd.Series(dtype=float)
    s1_path = os.path.join(parent_path, "backtest_alpha_growth_nav.csv")
    s4_path = os.path.join(parent_path, "us_stocks_dcf_backtest_nav.csv")

    if os.path.exists(s1_path):
        df = pd.read_csv(s1_path)
        df["parsed_date"] = pd.to_datetime(df["Unnamed: 0"])
        df = df.set_index("parsed_date")
        s1_rets = df["strategy"].pct_change().fillna(0.0)

    if os.path.exists(s4_path):
        df = pd.read_csv(s4_path)
        df["parsed_date"] = pd.to_datetime(df["Date"])
        df = df.set_index("parsed_date")
        s4_rets = df["NAV"].pct_change().fillna(0.0)

    configs = [
        (252,  "252d (1-year rolling)"),
        (504,  "504d (2-year rolling)"),
        (756,  "756d (3-year rolling)"),
        (None, "Full-history (5y, baseline)"),
    ]

    results = []
    for lookback, label in configs:
        print(f"\nTesting: {label}...")
        try:
            lbl, ret, sh, dd, nav = run_s9_backtest(prices, s1_rets, s4_rets, lookback, label)
            results.append((lbl, ret, sh, dd, nav))
            if ret is not None:
                print(f"  Return: {ret:.2f}% | Sharpe: {sh:.3f} | MaxDD: {dd:.2f}% | NAV: ${nav:,.2f}")
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append((label, None, None, None, None))

    print("\n" + "=" * 70)
    print("GRID SEARCH RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Config':<30} {'Return':>10} {'Sharpe':>10} {'MaxDD':>10} {'Final NAV':>14}")
    print("-" * 70)
    for lbl, ret, sh, dd, nav in results:
        if ret is not None:
            print(f"{lbl:<30} {ret:>9.2f}% {sh:>10.3f} {dd:>9.2f}% ${nav:>12,.2f}")
        else:
            print(f"{lbl:<30} {'N/A':>10} {'N/A':>10} {'N/A':>10} {'N/A':>14}")
