"""
ATR Risk Manager & Chandelier Exit Module

Provides pure, stateless functions for:
1. Average True Range (ATR) calculation.
2. ATR-based volatility parity position sizing.
3. Chandelier Exit (ATR trailing stop) calculation.
"""

import numpy as np
import pandas as pd


def calculate_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """
    Calculate Average True Range (ATR) over a given period.
    
    high, low, close: 1D numpy arrays of asset prices.
    period: lookback window (default 14).
    returns: 1D numpy array of ATR values matching input length.
    """
    if len(close) < 2:
        return np.full_like(close, np.nan, dtype=np.float64)
        
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    
    tr2[0] = tr1[0]
    tr3[0] = tr1[0]
    
    true_range = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # Wilder's Smoothing / EMA for ATR
    atr = np.full_like(close, np.nan, dtype=np.float64)
    if len(close) >= period:
        atr[period - 1] = np.mean(true_range[:period])
        alpha = 1.0 / period
        for i in range(period, len(close)):
            atr[i] = alpha * true_range[i] + (1.0 - alpha) * atr[i - 1]
            
    return atr


def calculate_atr_position_size(
    total_equity: float,
    current_price: float,
    atr_val: float,
    target_risk_pct: float = 0.01,
    risk_multiplier: float = 2.0,
    max_capital_pct: float = 0.25
) -> int:
    """
    Calculates volatility-adjusted position size (number of shares).
    
    total_equity: Current total portfolio value.
    current_price: Asset current price per share.
    atr_val: Current ATR value of asset.
    target_risk_pct: Maximum portfolio equity percentage to risk per position (e.g., 0.01 = 1%).
    risk_multiplier: Multiplier of ATR defining the dollar risk distance (default 2.0x ATR).
    max_capital_pct: Maximum allowable capital weight in a single position (default 25%).
    
    returns: Number of shares (integer) to purchase.
    """
    if current_price <= 0 or atr_val <= 0 or total_equity <= 0:
        return 0
        
    # Dollar amount willing to risk on this trade
    max_risk_amount = total_equity * target_risk_pct
    
    # Risk distance per share (k * ATR)
    risk_per_share = atr_val * risk_multiplier
    if risk_per_share <= 0:
        return 0
        
    # Share count based on risk tolerance
    shares = int(max_risk_amount / risk_per_share)
    
    # Cap position size by maximum capital weight
    max_capital_amount = total_equity * max_capital_pct
    max_shares_cap = int(max_capital_amount / current_price)
    
    return max(0, min(shares, max_shares_cap))


def calculate_chandelier_stop(
    highest_peak: float,
    atr_val: float,
    multiplier: float = 3.0,
    is_long: bool = True
) -> float:
    """
    Calculates the Chandelier Exit price level based on peak price and ATR.
    
    highest_peak: Highest close/high price reached since position entry.
    atr_val: Current 14-period ATR value.
    multiplier: ATR multiplier distance (default 3.0).
    is_long: True for long position trailing stop, False for short position.
    
    returns: Stop price level.
    """
    if is_long:
        return max(0.0, highest_peak - (multiplier * atr_val))
    else:
        return highest_peak + (multiplier * atr_val)
