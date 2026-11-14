"""Shared S25/S30 single-asset simulation in the asset's native currency.

Signals use the previous completed close; orders fill at the next close.
The existing position earns that session's return before a fill and its fees.
Close-based stops are signals, not guaranteed stop-price fills.
"""
import numpy as np
import pandas as pd


def indicators(close):
    macd = close.ewm(span=13, adjust=False).mean() - close.ewm(span=34, adjust=False).mean()
    signal = macd.ewm(span=8, adjust=False).mean()
    return pd.DataFrame({
        "trend": close.ewm(span=55, adjust=False).mean(),
        "bull": (macd > signal) & (macd.shift(1) <= signal.shift(1)),
        "bear": (macd < signal) & (macd.shift(1) >= signal.shift(1)),
    })


def simulate(close, initial_capital, annual_cash_yield, transaction_cost):
    close = close.astype(float)
    if (len(close) < 2 or close.index.has_duplicates or not close.index.is_monotonic_increasing
            or not np.isfinite(close).all() or (close <= 0).any()):
        raise ValueError("At least two sorted, unique, positive prices required")
    if not np.isfinite(initial_capital) or initial_capital <= 0 or not 0 <= transaction_cost < 1:
        raise ValueError("Invalid capital or transaction cost")
    if not np.isfinite(annual_cash_yield) or annual_cash_yield <= -1:
        raise ValueError("Invalid cash yield")
    signals = indicators(close)
    returns = close.pct_change(fill_method=None).to_numpy()
    prices = close.to_numpy()
    nav = np.zeros(len(close))
    nav[0] = initial_capital
    position = False
    entry_price = peak = 0.0
    armed = False
    for t in range(1, len(close)):
        decision_price = prices[t - 1]
        signal = signals.iloc[t - 1]
        target = position
        if not position:
            target = bool(decision_price > signal.trend and signal.bull)
        else:
            peak = max(peak, decision_price)
            armed = armed or decision_price >= entry_price * 1.15
            stop = armed and decision_price <= peak * 0.98
            if stop or signal.bear or decision_price < signal.trend:
                target = False
        period_return = returns[t] if position else annual_cash_yield / 252.0
        marked_nav = nav[t - 1] * (1 + period_return)
        if target != position:
            # Enter fully funded, including fees; exits pay fees on sale value.
            marked_nav = marked_nav / (1 + transaction_cost) if target else marked_nav * (1 - transaction_cost)
            if target:
                entry_price = peak = prices[t]
                armed = False
        nav[t] = marked_nav
        position = target
    return nav
