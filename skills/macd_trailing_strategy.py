"""
MACD Entry + Trailing Stop Exit Strategy

Translated from Pine Script //@version=6.
Implements a trend-following strategy:
  - Bull trend filter: Close > 200-period SMA
  - Entry: MACD(12, 26, 9) line crosses above signal line while in bull trend
  - Exit:  Trailing stop that arms after +5% unrealized profit,
           then trails at 2% below the highest close since entry

Each position is sized at a fixed percentage of current equity.
"""

import numpy as np
import pandas as pd


def _ema(series: np.ndarray, span: int) -> np.ndarray:
    """Exponential moving average matching TradingView's ta.ema (multiplier = 2/(span+1))."""
    alpha = 2.0 / (span + 1)
    out = np.empty_like(series, dtype=np.float64)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _sma(series: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average. First (window-1) values are NaN."""
    out = np.full_like(series, np.nan, dtype=np.float64)
    cumsum = np.cumsum(series)
    out[window - 1:] = (cumsum[window - 1:] - np.concatenate(([0.0], cumsum[:-window]))) / window
    return out


class PositionState:
    """Tracks the state of a single open position for trailing-stop logic."""

    def __init__(self, ticker: str, entry_price: float, shares: float, entry_idx: int):
        self.ticker = ticker
        self.entry_price = entry_price
        self.shares = shares
        self.entry_idx = entry_idx
        self.highest_since_entry = entry_price
        self.trailing_armed = False
        self.stop_level = 0.0

    def update(self, current_price: float, profit_trigger_pct: float, trailing_stop_pct: float) -> bool:
        """Update the trailing stop state.  Returns True if the stop is triggered (should SELL)."""
        # Track highest close since entry
        if current_price > self.highest_since_entry:
            self.highest_since_entry = current_price

        # Check if trailing stop should arm
        unrealized_pct = (current_price / self.entry_price - 1.0) * 100.0
        if not self.trailing_armed and unrealized_pct >= profit_trigger_pct:
            self.trailing_armed = True

        # If armed, compute and check the stop level
        if self.trailing_armed:
            self.stop_level = self.highest_since_entry * (1.0 - trailing_stop_pct / 100.0)
            if current_price <= self.stop_level:
                return True  # SELL

        return False


class MACDTrailingStopStrategy:
    """
    MACD Entry + Trailing Stop Exit strategy.

    Parameters match the Pine Script defaults:
        long_term_ma_length  = 200
        ma_type              = "SMA"
        macd_fast            = 12
        macd_slow            = 26
        macd_signal          = 9
        profit_trigger_pct   = 5.0   (% profit to arm trailing stop)
        trailing_stop_pct    = 2.0   (% below peak to trigger exit)
        position_pct         = 0.10  (fraction of equity per trade)
        commission_pct       = 0.0029  (0.29% per side)
        max_positions        = 10    (max concurrent open positions)
    """

    def __init__(
        self,
        long_term_ma_length: int = 200,
        ma_type: str = "SMA",
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        profit_trigger_pct: float = 5.0,
        trailing_stop_pct: float = 2.0,
        position_pct: float = 0.10,
        commission_pct: float = 0.0029,
        max_positions: int = 10,
    ):
        self.long_term_ma_length = long_term_ma_length
        self.ma_type = ma_type
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.profit_trigger_pct = profit_trigger_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.position_pct = position_pct
        self.commission_pct = commission_pct
        self.max_positions = max_positions

    def compute_indicators(self, prices: np.ndarray) -> dict:
        """Compute MACD line, signal line, histogram, and long-term MA."""
        ema_fast = _ema(prices, self.macd_fast)
        ema_slow = _ema(prices, self.macd_slow)
        macd_line = ema_fast - ema_slow
        signal_line = _ema(macd_line, self.macd_signal)
        histogram = macd_line - signal_line

        if self.ma_type == "EMA":
            long_term_ma = _ema(prices, self.long_term_ma_length)
        else:
            long_term_ma = _sma(prices, self.long_term_ma_length)

        return {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram,
            "long_term_ma": long_term_ma,
        }

    def run_portfolio_backtest(
        self,
        price_matrix: pd.DataFrame,
        initial_capital: float = 20_000.0,
        monthly_contribution: float = 2_000.0,
    ) -> dict:
        """
        Run the full portfolio-level backtest across all tickers in price_matrix.

        Parameters
        ----------
        price_matrix : pd.DataFrame
            Columns = tickers, Index = dates, values = close prices (MXN).
        initial_capital : float
            Starting capital in MXN.
        monthly_contribution : float
            Monthly cash injection in MXN.

        Returns
        -------
        dict with keys: nav_series, benchmark_nav, trade_log, metrics
        """
        dates = price_matrix.index
        tickers = list(price_matrix.columns)
        n_days = len(dates)

        # Pre-compute indicators for all tickers
        indicators = {}
        for ticker in tickers:
            prices = price_matrix[ticker].values.astype(np.float64)
            indicators[ticker] = self.compute_indicators(prices)

        # State
        cash = initial_capital
        positions = {}  # ticker -> PositionState
        nav_history = []
        trade_log = []

        # Equal-weight benchmark
        bench_per_ticker = initial_capital / len(tickers)
        bench_shares = {}
        for ticker in tickers:
            first_price = price_matrix[ticker].iloc[0]
            if first_price > 0 and np.isfinite(first_price):
                bench_shares[ticker] = bench_per_ticker / first_price
            else:
                bench_shares[ticker] = 0.0
        bench_nav_history = []

        # TWR tracking
        last_nav = initial_capital
        last_bench_nav = initial_capital
        twr = 1.0
        bench_twr = 1.0
        twr_history = []
        bench_twr_history = []

        prev_month = dates[0].month if n_days > 0 else None

        for i in range(n_days):
            current_date = dates[i]

            # --- 0. Accrue interest on cash (11% APR from Bondia) ---
            if i > 0:
                date_prev = dates[i - 1]
                calendar_days = (current_date - date_prev).days
                daily_rate = 0.11 / 360.0
                interest = cash * daily_rate * calendar_days
                cash += interest

            # --- 1. Compute pre-action NAV ---
            equity_val = sum(
                pos.shares * price_matrix[pos.ticker].iloc[i]
                for pos in positions.values()
            )
            nav_before = cash + equity_val
            bench_val = sum(
                bench_shares[t] * price_matrix[t].iloc[i] for t in tickers
            )

            # --- 2. TWR update ---
            if i > 0:
                r = (nav_before / last_nav) - 1.0 if last_nav > 0 else 0.0
                r_b = (bench_val / last_bench_nav) - 1.0 if last_bench_nav > 0 else 0.0
                twr *= (1.0 + r)
                bench_twr *= (1.0 + r_b)

            # --- 3. Monthly contribution ---
            current_month = current_date.month
            if i == 0 or current_month != prev_month:
                cash += monthly_contribution
                nav_before += monthly_contribution
                # Benchmark also gets the contribution, equally distributed
                contrib_per = monthly_contribution / len(tickers)
                for t in tickers:
                    p = price_matrix[t].iloc[i]
                    if p > 0 and np.isfinite(p):
                        bench_shares[t] += contrib_per / p
                bench_val = sum(bench_shares[t] * price_matrix[t].iloc[i] for t in tickers)
                prev_month = current_month

            # --- 4. Process exits (trailing stop checks) ---
            tickers_to_close = []
            for ticker, pos in positions.items():
                current_price = price_matrix[ticker].iloc[i]
                if not np.isfinite(current_price) or current_price <= 0:
                    continue
                triggered = pos.update(current_price, self.profit_trigger_pct, self.trailing_stop_pct)
                if triggered:
                    tickers_to_close.append(ticker)

            for ticker in tickers_to_close:
                pos = positions[ticker]
                sell_price = price_matrix[ticker].iloc[i]
                revenue = pos.shares * sell_price
                fee = revenue * self.commission_pct
                cash += (revenue - fee)
                pnl = (sell_price - pos.entry_price) * pos.shares - fee
                trade_log.append({
                    "date": str(current_date.date()),
                    "ticker": ticker,
                    "action": "SELL",
                    "shares": pos.shares,
                    "price": sell_price,
                    "fee": fee,
                    "pnl": pnl,
                    "reason": f"Trailing stop at {pos.stop_level:.2f} (peak {pos.highest_since_entry:.2f})",
                })
                del positions[ticker]

            # --- 5. Process entries (MACD crossover + bull trend) ---
            # Only check for entries if we have enough history for the 200 MA
            if i >= self.long_term_ma_length and len(positions) < self.max_positions:
                for ticker in tickers:
                    if ticker in positions:
                        continue  # already holding
                    if len(positions) >= self.max_positions:
                        break

                    ind = indicators[ticker]
                    long_ma = ind["long_term_ma"][i]
                    current_price = price_matrix[ticker].iloc[i]

                    if not np.isfinite(long_ma) or not np.isfinite(current_price):
                        continue

                    # Bull trend filter
                    is_bull = current_price > long_ma

                    # MACD crossover: macd_line crosses above signal_line
                    if i < 1:
                        continue
                    macd_today = ind["macd_line"][i]
                    signal_today = ind["signal_line"][i]
                    macd_yesterday = ind["macd_line"][i - 1]
                    signal_yesterday = ind["signal_line"][i - 1]

                    crossover = (macd_yesterday <= signal_yesterday) and (macd_today > signal_today)

                    if is_bull and crossover:
                        # Position sizing: position_pct of current equity
                        equity_now = cash + sum(
                            p.shares * price_matrix[p.ticker].iloc[i] for p in positions.values()
                        )
                        alloc = equity_now * self.position_pct
                        shares_to_buy = int(alloc // current_price)
                        if shares_to_buy <= 0:
                            continue
                        cost = shares_to_buy * current_price
                        fee = cost * self.commission_pct
                        total_cost = cost + fee
                        if total_cost > cash:
                            # Reduce to fit available cash
                            shares_to_buy = int(cash // (current_price * (1.0 + self.commission_pct)))
                            if shares_to_buy <= 0:
                                continue
                            cost = shares_to_buy * current_price
                            fee = cost * self.commission_pct
                            total_cost = cost + fee

                        cash -= total_cost
                        positions[ticker] = PositionState(
                            ticker=ticker,
                            entry_price=current_price,
                            shares=shares_to_buy,
                            entry_idx=i,
                        )
                        trade_log.append({
                            "date": str(current_date.date()),
                            "ticker": ticker,
                            "action": "BUY",
                            "shares": shares_to_buy,
                            "price": current_price,
                            "fee": fee,
                            "pnl": 0.0,
                            "reason": f"MACD crossover + bull trend (MA200={long_ma:.2f})",
                        })

            # --- 6. Record daily NAV ---
            equity_val = sum(
                pos.shares * price_matrix[pos.ticker].iloc[i]
                for pos in positions.values()
            )
            final_nav = cash + equity_val
            last_nav = final_nav
            last_bench_nav = sum(bench_shares[t] * price_matrix[t].iloc[i] for t in tickers)

            nav_history.append(final_nav)
            bench_nav_history.append(last_bench_nav)
            twr_history.append(twr)
            bench_twr_history.append(bench_twr)

        # --- Build results ---
        nav_series = pd.Series(nav_history, index=dates, name="strategy")
        bench_series = pd.Series(bench_nav_history, index=dates, name="benchmark")
        twr_series = pd.Series(twr_history, index=dates, name="strategy_twr")
        bench_twr_series = pd.Series(bench_twr_history, index=dates, name="benchmark_twr")

        metrics = self._compute_metrics(twr_series, bench_twr_series, trade_log)

        return {
            "nav_series": nav_series,
            "benchmark_nav": bench_series,
            "twr_series": twr_series,
            "bench_twr_series": bench_twr_series,
            "trade_log": trade_log,
            "metrics": metrics,
        }

    @staticmethod
    def _compute_metrics(twr_series: pd.Series, bench_twr_series: pd.Series, trade_log: list) -> dict:
        """Compute CAGR, Sharpe, Max DD, win rate from TWR series."""
        # TWR returns
        twr_returns = twr_series.pct_change().dropna()
        bench_returns = bench_twr_series.pct_change().dropna()

        # Total return
        strat_total = twr_series.iloc[-1] - 1.0
        bench_total = bench_twr_series.iloc[-1] - 1.0

        # CAGR
        days = (twr_series.index[-1] - twr_series.index[0]).days
        years = max(days / 365.25, 0.01)
        strat_cagr = (1 + strat_total) ** (1 / years) - 1
        bench_cagr = (1 + bench_total) ** (1 / years) - 1

        # Sharpe
        strat_sharpe = (twr_returns.mean() / twr_returns.std() * np.sqrt(252)) if twr_returns.std() > 0 else 0.0

        # Max drawdown
        cumulative = twr_series.values
        peaks = np.maximum.accumulate(cumulative)
        dd = (cumulative - peaks) / peaks
        max_dd = dd.min()

        bench_cumulative = bench_twr_series.values
        bench_peaks = np.maximum.accumulate(bench_cumulative)
        bench_dd = (bench_cumulative - bench_peaks) / bench_peaks
        bench_max_dd = bench_dd.min()

        # Trade statistics
        sells = [t for t in trade_log if t["action"] == "SELL"]
        n_trades = len(sells)
        wins = [t for t in sells if t["pnl"] > 0]
        win_rate = len(wins) / n_trades if n_trades > 0 else 0.0
        total_pnl = sum(t["pnl"] for t in sells)
        total_fees = sum(t["fee"] for t in trade_log)
        avg_pnl = total_pnl / n_trades if n_trades > 0 else 0.0

        return {
            "strategy_total_return": strat_total,
            "strategy_cagr": strat_cagr,
            "strategy_sharpe": strat_sharpe,
            "strategy_max_dd": max_dd,
            "benchmark_total_return": bench_total,
            "benchmark_cagr": bench_cagr,
            "benchmark_max_dd": bench_max_dd,
            "n_trades": n_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "total_fees": total_fees,
            "n_buys": len([t for t in trade_log if t["action"] == "BUY"]),
        }
