import pandas as pd
import numpy as np

def calculate_sma(series: pd.Series, period: int = 200) -> pd.Series:
    """Calculate Simple Moving Average."""
    return series.rolling(window=period).mean()

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Calculate MACD Line and Signal Line."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Use Exponential Moving Average for wilder smoothing
    avg_gain = gain.ewm(com=period-1, adjust=False).mean()
    avg_loss = loss.ewm(com=period-1, adjust=False).mean()
    
    # Avoid division by zero
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rs = rs.fillna(0)
    
    rsi = 100 - (100 / (1.0 + rs))
    return rsi

def calculate_bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0):
    """Calculate Bollinger Bands (Upper, Middle, Lower)."""
    middle_band = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper_band = middle_band + (num_std * std)
    lower_band = middle_band - (num_std * std)
    return upper_band, middle_band, lower_band

def calculate_donchian_channels(high_series: pd.Series, low_series: pd.Series, period: int = 20):
    """Calculate Donchian Channels (Upper and Lower)."""
    upper_channel = high_series.rolling(window=period).max()
    lower_channel = low_series.rolling(window=period).min()
    return upper_channel, lower_channel

def evaluate_signals(ticker: str, asset_type: str, df: pd.DataFrame) -> dict:
    """
    Evaluate indicators and return signal details.
    df must have columns: ['open', 'high', 'low', 'close']
    asset_type: 'crypto', 'forex', 'commodity'
    """
    if df.empty or len(df) < 200:
        return {"ticker": ticker, "signal": "neutral", "reason": "Insufficient data"}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    
    curr_close = float(close.iloc[-1])
    
    if asset_type == "crypto":
        # Crypto: SMA 200 + MACD Crossover
        sma_200 = calculate_sma(close, 200)
        macd, signal = calculate_macd(close)
        
        curr_sma = float(sma_200.iloc[-1])
        curr_macd = float(macd.iloc[-1])
        curr_signal = float(signal.iloc[-1])
        
        prev_macd = float(macd.iloc[-2])
        prev_signal = float(signal.iloc[-2])
        
        # Trend check
        trend_bull = curr_close > curr_sma
        
        # Crossover check
        macd_cross_up = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
        macd_cross_down = (prev_macd >= prev_signal) and (curr_macd < curr_signal)
        
        if trend_bull and macd_cross_up:
            return {
                "ticker": ticker,
                "signal": "buy",
                "price": curr_close,
                "indicators": {"sma_200": curr_sma, "macd": curr_macd, "signal": curr_signal},
                "reason": "MACD cross up in bullish trend"
            }
        elif macd_cross_down or not trend_bull:
            return {
                "ticker": ticker,
                "signal": "sell",
                "price": curr_close,
                "indicators": {"sma_200": curr_sma, "macd": curr_macd, "signal": curr_signal},
                "reason": "MACD cross down or bearish trend break"
            }
        else:
            return {
                "ticker": ticker,
                "signal": "hold",
                "price": curr_close,
                "indicators": {"sma_200": curr_sma, "macd": curr_macd, "signal": curr_signal},
                "reason": "No cross or trend changes"
            }
            
    elif asset_type == "commodity":
        # Commodities: SMA 100 + Donchian Channel
        sma_100 = calculate_sma(close, 100)
        donch_high_20, _ = calculate_donchian_channels(high, low, 20)
        _, donch_low_10 = calculate_donchian_channels(high, low, 10)
        
        curr_sma = float(sma_100.iloc[-1])
        
        # Previous day's channels to prevent lookahead bias
        prev_donch_high = float(donch_high_20.iloc[-2])
        prev_donch_low = float(donch_low_10.iloc[-2])
        
        trend_bull = curr_close > curr_sma
        
        if trend_bull and curr_close > prev_donch_high:
            return {
                "ticker": ticker,
                "signal": "buy",
                "price": curr_close,
                "indicators": {"sma_100": curr_sma, "donchian_high": prev_donch_high, "donchian_low": prev_donch_low},
                "reason": "Breakout above 20-day high in bullish trend"
            }
        elif curr_close < prev_donch_low or not trend_bull:
            return {
                "ticker": ticker,
                "signal": "sell",
                "price": curr_close,
                "indicators": {"sma_100": curr_sma, "donchian_high": prev_donch_high, "donchian_low": prev_donch_low},
                "reason": "Breakout below 10-day low or bearish trend break"
            }
        else:
            return {
                "ticker": ticker,
                "signal": "hold",
                "price": curr_close,
                "indicators": {"sma_100": curr_sma, "donchian_high": prev_donch_high, "donchian_low": prev_donch_low},
                "reason": "Inside Donchian Channel limits"
            }
            
    elif asset_type == "forex":
        # Forex: Bollinger Bands + RSI
        upper, middle, lower = calculate_bollinger_bands(close, 20, 2.0)
        rsi = calculate_rsi(close, 14)
        
        curr_upper = float(upper.iloc[-1])
        curr_lower = float(lower.iloc[-1])
        curr_rsi = float(rsi.iloc[-1])
        
        if curr_close <= curr_lower and curr_rsi <= 35:
            return {
                "ticker": ticker,
                "signal": "buy",
                "price": curr_close,
                "indicators": {"upper_bb": curr_upper, "lower_bb": curr_lower, "rsi": curr_rsi},
                "reason": f"Oversold (RSI={curr_rsi:.1f}) at lower Bollinger Band"
            }
        elif curr_close >= curr_upper and curr_rsi >= 65:
            return {
                "ticker": ticker,
                "signal": "sell",
                "price": curr_close,
                "indicators": {"upper_bb": curr_upper, "lower_bb": curr_lower, "rsi": curr_rsi},
                "reason": f"Overbought (RSI={curr_rsi:.1f}) at upper Bollinger Band"
            }
        else:
            return {
                "ticker": ticker,
                "signal": "hold",
                "price": curr_close,
                "indicators": {"upper_bb": curr_upper, "lower_bb": curr_lower, "rsi": curr_rsi},
                "reason": "No extreme volatility or RSI signals"
            }
            
    return {"ticker": ticker, "signal": "neutral", "reason": "Unknown asset type"}


def calculate_dynamic_fib_confluence(
    level_price: float,
    fib_levels: list,
    atr_val: float = 3.0,
    base_tolerance: float = 0.015,
    max_tolerance: float = 0.025,
    baseline_atr: float = 3.0
) -> dict:
    """
    Evaluates dynamic Fibonacci level confluence.
    Expands tolerance from base_tolerance (1.5%) up to max_tolerance (2.5%) during high ATR regimes.
    
    returns: dict with 'is_confluent', 'nearest_fib', and 'effective_tolerance'.
    """
    if level_price <= 0 or not fib_levels:
        return {"is_confluent": False, "nearest_fib": None, "effective_tolerance": base_tolerance}

    # Dynamically expand tolerance based on ATR ratio
    atr_ratio = max(1.0, atr_val / baseline_atr) if baseline_atr > 0 else 1.0
    effective_tol = min(max_tolerance, base_tolerance * np.sqrt(atr_ratio))

    nearest_fib = min(fib_levels, key=lambda f: abs(level_price - f))
    pct_diff = abs(level_price - nearest_fib) / nearest_fib

    is_confluent = pct_diff <= effective_tol

    return {
        "is_confluent": bool(is_confluent),
        "nearest_fib": float(nearest_fib),
        "pct_diff": float(pct_diff),
        "effective_tolerance": float(effective_tol)
    }

