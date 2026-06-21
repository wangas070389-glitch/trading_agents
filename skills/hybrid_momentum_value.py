"""
Hybrid MACD-DCF Momentum-Value Strategy

Combines:
  - Fundamental Filter: DCS from the DCF valuation engine must be >= 0.05 (undervalued).
  - Technical Trend Filter: Close > 200 SMA (bull market filter).
  - Crossover Trigger: MACD line crosses above Signal line.
  - Pyramiding: Up to 3 tranches (10% equity each) per asset.
  - Let Winners Run: Trailing stop arms at +20% profit, trails at 7.5% below peak close.
  - Overvaluation Exit: Force-sell if DCS drops below -0.10.
  - Active DCA: Deploys monthly cash inflows directly into top performing holdings (Close > 20 SMA, DCS >= 0.05).
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


class TrancheState:
    """Tracks a single tranche of an open position."""
    def __init__(self, entry_price: float, shares: float, entry_idx: int):
        self.entry_price = entry_price
        self.shares = shares
        self.entry_idx = entry_idx


class HybridPositionState:
    """Tracks the state of a multi-tranche open position for trailing stop and pyramiding."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.tranches = []  # List of TrancheState
        self.highest_since_entry = 0.0
        self.trailing_armed = False
        self.stop_level = 0.0

    @property
    def total_shares(self) -> float:
        return sum(t.shares for t in self.tranches)

    @property
    def average_entry_price(self) -> float:
        if not self.tranches:
            return 0.0
        total_cost = sum(t.shares * t.entry_price for t in self.tranches)
        return total_cost / self.total_shares

    def add_tranche(self, entry_price: float, shares: float, entry_idx: int):
        self.tranches.append(TrancheState(entry_price, shares, entry_idx))
        if len(self.tranches) == 1:
            self.highest_since_entry = entry_price
        else:
            # Recalculate highest peak based on the current price
            if entry_price > self.highest_since_entry:
                self.highest_since_entry = entry_price

    def update(self, current_price: float, profit_trigger_pct: float, trailing_stop_pct: float) -> bool:
        """Update trailing stop logic. Returns True if trailing stop is triggered (should SELL ALL)."""
        if not self.tranches:
            return False

        # Track highest price since the first entry
        if current_price > self.highest_since_entry:
            self.highest_since_entry = current_price

        # Check if trailing stop should arm based on average entry price
        avg_entry = self.average_entry_price
        unrealized_pct = (current_price / avg_entry - 1.0) * 100.0
        
        if not self.trailing_armed and unrealized_pct >= profit_trigger_pct:
            self.trailing_armed = True

        # If armed, check if we hit the stop level
        if self.trailing_armed:
            self.stop_level = self.highest_since_entry * (1.0 - trailing_stop_pct / 100.0)
            if current_price <= self.stop_level:
                return True  # Trigger SELL ALL
            
        return False
