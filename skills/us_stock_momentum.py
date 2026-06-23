import pandas as pd
import numpy as np

def calculate_us_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes indicators for the US Stock Momentum strategy:
    - 200-day Simple Moving Average (SMA 200)
    - MACD Line, Signal Line, and Histogram (12, 26, 9)
    """
    df = df.copy()
    # Normalize column names to lowercase/uppercase fallback
    close_col = None
    for col in ["Close", "close", "CLOSE"]:
        if col in df.columns:
            close_col = col
            break
            
    if close_col is None:
        raise ValueError("DataFrame must contain a 'Close' or 'close' column.")
        
    # Convert series to float to avoid type issues
    close_series = df[close_col].astype(float)
    
    # 200 SMA
    df["sma200"] = close_series.rolling(window=200).mean()
    
    # MACD (12, 26, 9)
    fast_ema = close_series.ewm(span=12, adjust=False).mean()
    slow_ema = close_series.ewm(span=26, adjust=False).mean()
    df["macd"] = fast_ema - slow_ema
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["hist"] = df["macd"] - df["signal"]
    
    return df

def check_trailing_stop(buy_price: float, current_price: float, peak_price: float, arm_pct: float = 0.10, trail_pct: float = 0.05) -> tuple[bool, float]:
    """
    Checks if a position has triggered its trailing stop-loss.
    - arm_pct: Unrealized profit percentage needed to arm the trailing stop (default +10%)
    - trail_pct: Drop percentage from peak to trigger sell (default 5%)
    Returns a tuple: (should_sell: bool, updated_peak_price: float)
    """
    new_peak = max(peak_price, current_price)
    
    # Check if we have ever achieved the target gain to arm the trailing stop
    unrealized_return = (new_peak / buy_price) - 1.0
    
    if unrealized_return >= arm_pct:
        # Armed! Check if current price is down by trail_pct from the peak
        drop_from_peak = (new_peak - current_price) / new_peak
        if drop_from_peak >= trail_pct:
            return True, new_peak
            
    return False, new_peak
