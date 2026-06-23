"""
DCF Alpha-Momentum Concentrated Backtest Runner

Features:
  - Valuation Screening (adjusted DCS >= 0.15) updated quarterly.
  - Trend Filter: Close > 100 SMA to avoid value traps.
  - Sizing: Conviction-based allocation (proportional to DCS), capped at 30% per stock.
  - Low turnover: Quarterly rebalancing (every 63 business days) to reduce fee drag.
  - Zero cash drag: Monthly DCA inflows immediately deployed into top undervalued uptrending holdings.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Stub out NLPSentimentEngine before importing agents to prevent live news fetch
import skills.nlp_sentiment as _nlp_module


class _StubNLPEngine:
    def get_black_litterman_adjustments(self, tickers):
        return {t: 0.0 for t in tickers}


_nlp_module.NLPSentimentEngine = _StubNLPEngine

from agents.agents import FundamentalScreener, MacroRiskAnalyst
from ingest_live_bmv import BMV_TICKERS, US_TICKERS
from skills.hybrid_momentum_value import _sma

# ---------- Config ----------
LOOKBACK_PERIOD = "5y"
REBALANCE_FREQ_DAYS = 63         # quarterly rebalancing
MIN_HISTORY_DAYS = 252           # 1y warmup
TRANSACTION_COST = 0.0029        # 0.29% per side (matches live broker)
INITIAL_CAPITAL = 20_000.0       # MXN
MONTHLY_CONTRIBUTION = 2_000.0   # MXN
DCS_ENTRY_THRESHOLD = 0.15
MAX_STOCK_WEIGHT = 0.30          # 30% concentration cap
MAX_CONCURRENT_POSITIONS = 5     # Concentrate in top 5
# ----------------------------


def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df.index = pd.to_datetime(df.index.date)
    return df


def download_universe() -> tuple[dict, pd.DataFrame, pd.Series]:
    """Pull 5y daily history for all tickers, plus SPY and USD/MXN exogenous.
    Returns (asset_data, exog_returns, usdmxn_rate). All US tickers converted to MXN."""
    print("Downloading SPY and USD/MXN exogenous regressors...")
    spy = _strip_tz(yf.Ticker("SPY").history(period=LOOKBACK_PERIOD))
    usdmxn = _strip_tz(yf.Ticker("MXN=X").history(period=LOOKBACK_PERIOD))
    if spy.empty or usdmxn.empty:
        raise RuntimeError("Failed to fetch SPY or USD/MXN. Network issue?")

    spy_ret = np.log(spy["Close"] / spy["Close"].shift(1))
    usdmxn_ret = np.log(usdmxn["Close"] / usdmxn["Close"].shift(1))
    exog = pd.DataFrame({"SPY_Ret": spy_ret, "USDMXN_Ret": usdmxn_ret}).dropna()
    fx_rate = usdmxn["Close"].rename("USDMXN_Rate")

    asset_data = {}
    for ticker in BMV_TICKERS + US_TICKERS:
        print(f"  Fetching {ticker}...", end=" ", flush=True)
        try:
            hist = _strip_tz(yf.Ticker(ticker).history(period=LOOKBACK_PERIOD))
            if hist.empty or len(hist) < MIN_HISTORY_DAYS:
                print(f"skip (only {len(hist)} days)")
                continue

            if ticker in US_TICKERS:
                # Convert to MXN
                df = pd.DataFrame({"Close": hist["Close"], "Volume": hist["Volume"]}).join(fx_rate, how="inner")
                if df.empty:
                    print("skip (no FX overlap)")
                    continue
                df["Close"] = df["Close"] * df["USDMXN_Rate"]
                hist = df[["Close", "Volume"]]

            asset_data[ticker] = hist
            print(f"OK ({len(hist)} days)")
        except Exception as exc:
            print(f"FAIL ({exc})")

    return asset_data, exog, fx_rate


def build_universe_data(asset_data: dict, exog: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """Build the {ticker: {prices, volumes, exogenous}} dict the screener expects, sliced to <= as_of."""
    universe = {}
    for ticker, hist in asset_data.items():
        sliced = hist.loc[hist.index <= as_of]
        if len(sliced) < 200:
            continue
        df = pd.DataFrame({
            "Price": sliced["Close"],
            "Volume": sliced["Volume"],
        })
        ret = np.log(df["Price"] / df["Price"].shift(1)).fillna(0.0)
        df["Ret"] = ret
        df_aligned = df.join(exog, how="inner").fillna(0.0)
        if len(df_aligned) < MIN_HISTORY_DAYS:
            continue
        universe[ticker] = {
            "prices": df_aligned["Price"].values,
            "volumes": df_aligned["Volume"].values,
            "exogenous": df_aligned[["SPY_Ret", "USDMXN_Ret"]].values,
        }
    return universe


def get_rebalance_dates(asset_data: dict) -> list[pd.Timestamp]:
    all_dates = sorted(set().union(*(set(df.index) for df in asset_data.values())))
    all_dates = [d for d in all_dates if d.weekday() < 5]
    start_idx = MIN_HISTORY_DAYS
    return all_dates[start_idx::REBALANCE_FREQ_DAYS]


def compute_metrics(nav_series: pd.Series, label: str) -> dict:
    returns = nav_series.pct_change().dropna()
    total_return = nav_series.iloc[-1] / nav_series.iloc[0] - 1
    days = (nav_series.index[-1] - nav_series.index[0]).days
    years = max(days / 365.25, 0.01)
    cagr = (1 + total_return) ** (1 / years) - 1
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0
    cumulative = (1 + returns).cumprod()
    drawdown = (cumulative / cumulative.cummax() - 1).min()
    return {
        "label": label,
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "n_obs": len(returns),
    }


def solve_weights(dcs_scores: dict) -> dict:
    """Solve conviction weights, applying the MAX_STOCK_WEIGHT cap and normalizing."""
    if not dcs_scores:
        return {}
    
    tickers = list(dcs_scores.keys())
    scores = np.array([dcs_scores[t] for t in tickers])
    
    # Weights proportional to DCS scores
    raw_weights = scores / np.sum(scores)
    
    # Cap loop
    weights = {t: raw_weights[i] for i, t in enumerate(tickers)}
    while True:
        capped = False
        excess = 0.0
        uncapped_sum = 0.0
        
        for t, w in weights.items():
            if w > MAX_STOCK_WEIGHT:
                excess += (w - MAX_STOCK_WEIGHT)
                weights[t] = MAX_STOCK_WEIGHT
                capped = True
            else:
                uncapped_sum += w
                
        if not capped or excess <= 1e-6 or uncapped_sum <= 1e-6:
            break
            
        # Redistribute excess
        for t, w in weights.items():
            if w < MAX_STOCK_WEIGHT:
                weights[t] += excess * (w / uncapped_sum)
                
    return weights


def main():
    print("=" * 80)
    print("DCF ALPHA-MOMENTUM CONCENTRATED BACKTEST")
    print("=" * 80)

    asset_data, exog, _ = download_universe()
    if not asset_data:
        print("No data downloaded. Aborting.")
        return
    tickers = list(asset_data.keys())

    rebalance_dates = get_rebalance_dates(asset_data)
    all_dates = sorted(set().union(*(set(df.index) for df in asset_data.values())))
    price_matrix = pd.DataFrame(index=all_dates)
    for ticker, hist in asset_data.items():
        price_matrix[ticker] = hist["Close"]
    price_matrix = price_matrix.ffill().bfill()

    # Slice to backtest period
    backtest_start = rebalance_dates[0]
    price_matrix = price_matrix.loc[price_matrix.index >= backtest_start]
    dates = price_matrix.index
    n_days = len(dates)

    # Pre-compute indicators for trend filters
    indicators = {}
    for ticker in tickers:
        prices = price_matrix[ticker].values.astype(np.float64)
        sma_100 = _sma(prices, 100)
        sma_20 = _sma(prices, 20)
        indicators[ticker] = {
            "sma_100": sma_100,
            "sma_20": sma_20,
        }

    # State
    cash = INITIAL_CAPITAL
    shares_held = {t: 0.0 for t in tickers}
    trade_log = []
    nav_history = []
    
    # Equal-weight stock benchmark
    bench_per_ticker = INITIAL_CAPITAL / len(tickers)
    bench_shares = {t: bench_per_ticker / price_matrix[t].iloc[0] for t in tickers}
    bench_nav_history = []

    # TWR Tracking
    last_nav = INITIAL_CAPITAL
    last_bench_nav = INITIAL_CAPITAL
    twr = 1.0
    bench_twr = 1.0
    twr_history = []
    bench_twr_history = []

    screener = FundamentalScreener()
    analyst = MacroRiskAnalyst()
    
    # Store latest monthly DCS scores (ticker -> float)
    latest_dcs = {}
    rebalance_idx = 0
    prev_month = dates[0].month

    print(f"\nBacktest period: {dates[0].date()} to {dates[-1].date()}")
    print("Starting simulation loop...")

    for i in range(n_days):
        current_date = dates[i]
        current_month = current_date.month

        # --- 0. Accrue daily interest on cash balance (11% APR) ---
        if i > 0:
            date_prev = dates[i - 1]
            calendar_days = (current_date - date_prev).days
            daily_rate = 0.11 / 360.0
            interest = cash * daily_rate * calendar_days
            cash += interest

        # --- 1. Compute today's NAV before any rebalance or cash additions ---
        equity_val = sum(shares_held[t] * price_matrix[t].iloc[i] for t in tickers if shares_held[t] > 0)
        nav_before = cash + equity_val
        bench_val = sum(bench_shares[t] * price_matrix[t].iloc[i] for t in tickers)

        # --- 2. Update TWR series ---
        if i > 0:
            r = (nav_before / last_nav) - 1.0 if last_nav > 0 else 0.0
            r_b = (bench_val / last_bench_nav) - 1.0 if last_bench_nav > 0 else 0.0
            twr *= (1.0 + r)
            bench_twr *= (1.0 + r_b)

        # --- 3. Monthly savings cash injection & Active DCA ---
        is_contribution_day = (i == 0 or current_month != prev_month)
        if is_contribution_day:
            cash += MONTHLY_CONTRIBUTION
            nav_before += MONTHLY_CONTRIBUTION
            
            # Passive Benchmark: allocate savings equally to all tickers
            bench_contrib_per = MONTHLY_CONTRIBUTION / len(tickers)
            for t in tickers:
                bench_shares[t] += bench_contrib_per / price_matrix[t].iloc[i]
            bench_val = sum(bench_shares[t] * price_matrix[t].iloc[i] for t in tickers)
            
            # Active DCA: Deploy $2,000 MXN immediately into top undervalued holdings in an uptrend
            if i > 0:
                eligible_dca = []
                for ticker in tickers:
                    if shares_held[ticker] > 0:
                        curr_price = price_matrix[ticker].iloc[i]
                        sma_20_val = indicators[ticker]["sma_20"][i]
                        dcs_val = latest_dcs.get(ticker, 0.0)
                        
                        if curr_price > sma_20_val and dcs_val >= DCS_ENTRY_THRESHOLD:
                            eligible_dca.append((ticker, dcs_val))
                
                if eligible_dca:
                    # Sort by DCS descending, take top 3
                    eligible_dca.sort(key=lambda x: x[1], reverse=True)
                    top_dca = eligible_dca[:3]
                    
                    dca_alloc = MONTHLY_CONTRIBUTION / len(top_dca)
                    print(f"  [{current_date.date()}] Active DCA Inflow: Deploying ${MONTHLY_CONTRIBUTION:.2f} across {len(top_dca)} positions:")
                    
                    for ticker, dcs_val in top_dca:
                        curr_price = price_matrix[ticker].iloc[i]
                        shares_to_buy = int(dca_alloc // curr_price)
                        if shares_to_buy > 0:
                            cost = shares_to_buy * curr_price
                            fee = cost * TRANSACTION_COST
                            total_cost = cost + fee
                            if total_cost <= cash:
                                cash -= total_cost
                                shares_held[ticker] += shares_to_buy
                                trade_log.append({
                                    "date": str(current_date.date()),
                                    "ticker": ticker,
                                    "action": "DCA_BUY",
                                    "shares": shares_to_buy,
                                    "price": curr_price,
                                    "fee": fee,
                                    "cost": total_cost,
                                    "reason": f"Active DCA (DCS={dcs_val:.3f}, Close>SMA20)",
                                })
                                print(f"    |-- DCA BUY {ticker}: {shares_to_buy} shares at ${curr_price:.2f} MXN")

            prev_month = current_month

        # --- 4. Quarterly Fundamental Rebalancing Loop ---
        if rebalance_idx < len(rebalance_dates) and current_date >= rebalance_dates[rebalance_idx]:
            print(f"  [{current_date.date()}] Quarterly Rebalancing... (step {rebalance_idx+1}/{len(rebalance_dates)})")
            try:
                universe = build_universe_data(asset_data, exog, current_date)
                if universe:
                    raw_metrics = screener.screen(universe, execution_date=current_date)
                    if raw_metrics:
                        adjusted = analyst.stress_test(raw_metrics, {})
                        
                        # Store adjusted DCS
                        for t in tickers:
                            if t in adjusted:
                                latest_dcs[t] = adjusted[t]["dcs_adjusted"]
                            else:
                                latest_dcs[t] = 0.0

                        # Filter undervalued candidates in an uptrend (Close > SMA 100)
                        candidates = []
                        for t in tickers:
                            dcs_val = latest_dcs.get(t, 0.0)
                            curr_price = price_matrix[t].iloc[i]
                            sma_100_val = indicators[t]["sma_100"][i]
                            
                            if dcs_val >= DCS_ENTRY_THRESHOLD and curr_price > sma_100_val:
                                candidates.append((t, dcs_val))

                        # Sort by DCS descending and take top 5
                        candidates.sort(key=lambda x: x[1], reverse=True)
                        top_candidates = candidates[:MAX_CONCURRENT_POSITIONS]
                        
                        # Compute conviction-based target weights
                        target_dcs_dict = {t: dcs_val for t, dcs_val in top_candidates}
                        target_weights = solve_weights(target_dcs_dict)
                        
                        # Set unselected/non-candidates to 0.0
                        full_target_weights = {t: 0.0 for t in tickers}
                        for t, w in target_weights.items():
                            full_target_weights[t] = w

                        # Execute rebalancing trades
                        # 1. Sell positions that are not in targets, or need size reduction
                        portfolio_value_now = cash + sum(shares_held[t] * price_matrix[t].iloc[i] for t in tickers if shares_held[t] > 0)
                        
                        for t in tickers:
                            target_w = full_target_weights[t]
                            curr_val = shares_held[t] * price_matrix[t].iloc[i]
                            target_val = portfolio_value_now * target_w
                            
                            # Hysteresis check: only trade if size change exceeds 5% of portfolio value
                            if curr_val > target_val and (curr_val - target_val) > (portfolio_value_now * 0.05):
                                shares_to_sell = (curr_val - target_val) / price_matrix[t].iloc[i]
                                shares_to_sell = min(shares_to_sell, shares_held[t])
                                if shares_to_sell > 0.01:
                                    sell_val = shares_to_sell * price_matrix[t].iloc[i]
                                    fee = sell_val * TRANSACTION_COST
                                    cash += (sell_val - fee)
                                    shares_held[t] -= shares_to_sell
                                    trade_log.append({
                                        "date": str(current_date.date()),
                                        "ticker": t,
                                        "action": "SELL",
                                        "shares": shares_to_sell,
                                        "price": price_matrix[t].iloc[i],
                                        "fee": fee,
                                        "cost": sell_val,
                                        "reason": f"Quarterly Rebalance (Target weight: {target_w*100:.1f}%)",
                                    })
                                    print(f"    |-- SELL {t}: {shares_to_sell:.2f} shares at ${price_matrix[t].iloc[i]:.2f} MXN")

                        # 2. Buy positions that need size increase
                        # Re-calculate cash and portfolio value after sells
                        portfolio_value_now = cash + sum(shares_held[t] * price_matrix[t].iloc[i] for t in tickers if shares_held[t] > 0)
                        
                        for t in tickers:
                            target_w = full_target_weights[t]
                            curr_val = shares_held[t] * price_matrix[t].iloc[i]
                            target_val = portfolio_value_now * target_w
                            
                            if target_val > curr_val and (target_val - curr_val) > (portfolio_value_now * 0.05):
                                alloc = target_val - curr_val
                                curr_price = price_matrix[t].iloc[i]
                                shares_to_buy = alloc / curr_price
                                
                                # Cap buy to fit available cash
                                cost = shares_to_buy * curr_price
                                fee = cost * TRANSACTION_COST
                                total_cost = cost + fee
                                if total_cost > cash:
                                    shares_to_buy = cash / (curr_price * (1.0 + TRANSACTION_COST))
                                    cost = shares_to_buy * curr_price
                                    fee = cost * TRANSACTION_COST
                                    total_cost = cost + fee
                                    
                                if shares_to_buy > 0.01:
                                    cash -= total_cost
                                    shares_held[t] += shares_to_buy
                                    trade_log.append({
                                        "date": str(current_date.date()),
                                        "ticker": t,
                                        "action": "BUY",
                                        "shares": shares_to_buy,
                                        "price": curr_price,
                                        "fee": fee,
                                        "cost": total_cost,
                                        "reason": f"Quarterly Rebalance (Target weight: {target_w*100:.1f}%)",
                                    })
                                    print(f"    |-- BUY {t}: {shares_to_buy:.2f} shares at ${curr_price:.2f} MXN")

            except Exception as e:
                print(f"  [ERROR] Fundamental screening failed on {current_date.date()}: {e}")
            rebalance_idx += 1

        # --- 5. Record daily NAV ---
        equity_val = sum(shares_held[t] * price_matrix[t].iloc[i] for t in tickers if shares_held[t] > 0)
        final_nav = cash + equity_val
        last_nav = final_nav
        last_bench_nav = sum(bench_shares[t] * price_matrix[t].iloc[i] for t in tickers)

        nav_history.append(final_nav)
        bench_nav_history.append(last_bench_nav)
        twr_history.append(twr)
        bench_twr_history.append(bench_twr)

    # --- Build final results ---
    strategy_series = pd.Series(nav_history, index=dates, name="strategy")
    benchmark_series = pd.Series(bench_nav_history, index=dates, name="benchmark")
    strategy_twr_pd = pd.Series(twr_history, index=dates, name="strategy_twr")
    benchmark_twr_pd = pd.Series(bench_twr_history, index=dates, name="benchmark_twr")

    strategy_metrics = compute_metrics(strategy_twr_pd, "Alpha Strategy")
    benchmark_metrics = compute_metrics(benchmark_twr_pd, "Equal-weight buy-and-hold")

    # Save CSV
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nav_df = pd.DataFrame({"strategy": strategy_series, "benchmark": benchmark_series})
    nav_df.to_csv(os.path.join(base_dir, "backtest_alpha_growth_nav.csv"))
    print(f"\n  NAV series saved: backtest_alpha_growth_nav.csv")

    # Write report
    report_path = os.path.join(base_dir, "backtest_alpha_growth_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# DCF Alpha-Momentum Concentrated Backtest Report\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Setup\n\n")
        f.write(f"- Universe: {len(tickers)} tickers (BMV + US, US converted to MXN)\n")
        f.write(f"- Backtest period: {strategy_series.index[0].date()} to {strategy_series.index[-1].date()}\n")
        f.write(f"- Strategy: DCF Valuation (DCS >= {DCS_ENTRY_THRESHOLD}) + Momentum Filter (Close > 100 SMA)\n")
        f.write(f"- Rebalancing frequency: every {REBALANCE_FREQ_DAYS} trading days (quarterly)\n")
        f.write(f"- Position Sizing: Conviction-based allocation, capped at {MAX_STOCK_WEIGHT*100:.0f}% weight per stock (Max {MAX_CONCURRENT_POSITIONS} positions)\n")
        f.write(f"- Active DCA Deployment: enabled (deposits routed immediately into top performing undervalued holdings)\n")
        f.write(f"- Transaction cost: {TRANSACTION_COST*100:.2f}% per side\n")
        f.write(f"- Initial capital: ${INITIAL_CAPITAL:,.2f} MXN\n")
        f.write(f"- Monthly contribution: ${MONTHLY_CONTRIBUTION:,.2f} MXN\n\n")

        f.write("## Results\n\n")
        f.write("| Metric | Alpha Strategy | Equal-weight Benchmark |\n")
        f.write("| :--- | ---: | ---: |\n")
        f.write(f"| Total return | {strategy_metrics['total_return']*100:+.2f}% | {benchmark_metrics['total_return']*100:+.2f}% |\n")
        f.write(f"| CAGR | {strategy_metrics['cagr']*100:+.2f}% | {benchmark_metrics['cagr']*100:+.2f}% |\n")
        f.write(f"| Sharpe (annualized) | {strategy_metrics['sharpe']:.2f} | {benchmark_metrics['sharpe']:.2f} |\n")
        f.write(f"| Max drawdown | {strategy_metrics['max_drawdown']*100:.2f}% | {benchmark_metrics['max_drawdown']*100:.2f}% |\n")
        f.write(f"| Final NAV | ${strategy_series.iloc[-1]:,.2f} | ${benchmark_series.iloc[-1]:,.2f} |\n\n")

        # Trading Activity
        total_fees = sum(t["fee"] for t in trade_log)
        
        f.write("## Trading Activity\n\n")
        f.write(f"- Total transaction costs paid: ${total_fees:,.2f} MXN\n")
        f.write(f"- Total trades executed: {len(trade_log)}\n\n")

        # Recent trade log
        if trade_log:
            f.write("## Recent Trade Log (last 30)\n\n")
            f.write("| Date | Ticker | Action | Shares | Price | Fee | Cost | Reason |\n")
            f.write("| :--- | :--- | :---: | ---: | ---: | ---: | ---: | :--- |\n")
            for t in trade_log[-30:]:
                f.write(f"| {t['date']} | {t['ticker']} | {t['action']} | {t['shares']:.2f} | ${t['price']:.2f} | ${t['fee']:.2f} | ${t['cost']:.2f} | {t['reason']} |\n")

    print(f"  Report saved: {report_path}")
    print("=" * 80)
    print("ALPHA BACKTEST SUMMARY")
    print("=" * 80)
    print(f"  Period:    {strategy_series.index[0].date()} -> {strategy_series.index[-1].date()}")
    print(f"  Strategy:  CAGR={strategy_metrics['cagr']*100:+.2f}%  Sharpe={strategy_metrics['sharpe']:.2f}  MaxDD={strategy_metrics['max_drawdown']*100:.2f}%")
    print(f"  Benchmark: CAGR={benchmark_metrics['cagr']*100:+.2f}%  Sharpe={benchmark_metrics['sharpe']:.2f}  MaxDD={benchmark_metrics['max_drawdown']*100:.2f}%")
    print(f"  Excess CAGR: {(strategy_metrics['cagr']-benchmark_metrics['cagr'])*100:+.2f}%")
    print(f"  Total Trades: {len(trade_log)} | Fees: ${total_fees:,.2f} MXN")


if __name__ == "__main__":
    main()
