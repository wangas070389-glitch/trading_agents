import numpy as np
import pandas as pd

def calculate_rma(series, length):
    """Calculate Running Moving Average (RMA) like TradingView's ta.rma.
    It is initialized with the simple moving average (SMA) of the first 'length' values,
    and then calculated recursively with alpha = 1 / length.
    """
    rma = np.full(len(series), np.nan)
    valid_indices = series.dropna().index
    if len(valid_indices) < length:
        return pd.Series(rma, index=series.index)
    
    start_idx = valid_indices[length - 1]
    start_loc = series.index.get_loc(start_idx)
    
    # Initialize the first rma value as the SMA
    first_sma = series.iloc[:start_loc + 1].dropna().tail(length).mean()
    rma[start_loc] = first_sma
    
    alpha = 1.0 / length
    for i in range(start_loc + 1, len(series)):
        val = series.iloc[i]
        if not np.isnan(val):
            rma[i] = val * alpha + rma[i - 1] * (1.0 - alpha)
        else:
            rma[i] = rma[i - 1]
            
    return pd.Series(rma, index=series.index)

def calculate_atr(df, length=14):
    """Calculate Average True Range (ATR) like TradingView's ta.atr."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    return calculate_rma(tr, length)

def calculate_adx(df, length=14):
    """Calculate DMI (+DI, -DI) and ADX like TradingView's ta.dmi."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    plus_dm_series = pd.Series(plus_dm, index=df.index)
    minus_dm_series = pd.Series(minus_dm, index=df.index)
    
    atr = calculate_atr(df, length)
    
    plus_di = 100.0 * calculate_rma(plus_dm_series, length) / atr
    minus_di = 100.0 * calculate_rma(minus_dm_series, length) / atr
    
    # Filter division by zero issues
    denom = plus_di + minus_di
    dx = np.where(denom != 0.0, 100.0 * np.abs(plus_di - minus_di) / denom, 0.0)
    dx_series = pd.Series(dx, index=df.index)
    
    adx = calculate_rma(dx_series, length)
    return plus_di, minus_di, adx

def calculate_linreg_slope(series, length):
    """Calculate rolling linear regression slope like TradingView's ta.linreg(source, length, 0)."""
    y = series.values
    if len(y) < length:
        return pd.Series(np.nan, index=series.index)
        
    slopes = np.full(len(y), np.nan)
    x = np.arange(length)
    sum_x = np.sum(x)
    sum_xx = np.sum(x**2)
    denom = length * sum_xx - sum_x**2
    
    for t in range(length - 1, len(y)):
        window = y[t - length + 1 : t + 1]
        if np.isnan(window).any():
            continue
        sum_y = np.sum(window)
        sum_xy = np.sum(x * window)
        slopes[t] = (length * sum_xy - sum_x * sum_y) / denom
        
    return pd.Series(slopes, index=series.index)

def calculate_macd(series, fast_len=12, slow_len=26, signal_len=9):
    """Calculate MACD Line and Signal Line."""
    fast_ema = series.ewm(span=fast_len, adjust=False).mean()
    slow_ema = series.ewm(span=slow_len, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal_len, adjust=False).mean()
    return macd_line, signal_line

def calculate_all_indicators(df, params):
    """Adds all systematic strategy indicators to the dataframe."""
    df = df.copy()
    
    # 1. Long-Term MA
    ma_len = params.get("longTermMALength", 200)
    ma_type = params.get("maType", "SMA")
    if ma_type == "SMA":
        df["ma_long"] = df["close"].rolling(window=ma_len).mean()
    else:
        df["ma_long"] = df["close"].ewm(span=ma_len, adjust=False).mean()
        
    # 2. MACD
    fast_len = params.get("fastLength", 12)
    slow_len = params.get("slowLength", 26)
    sig_len = params.get("signalLength", 9)
    df["macd"], df["signal"] = calculate_macd(df["close"], fast_len, slow_len, sig_len)
    
    # 3. ATR
    atr_len = params.get("atrLength", 14)
    df["atr"] = calculate_atr(df, atr_len)
    
    # 4. ADX / DMI
    adx_len = params.get("adxLength", 14)
    _, _, df["adx"] = calculate_adx(df, adx_len)
    
    # 5. Linear Regression Slope
    slope_len = params.get("slopeLength", 14)
    df["slope"] = calculate_linreg_slope(df["close"], slope_len)
    
    # Deceleration Counting
    slope_epsilon = params.get("slopeEpsilon", 0.0)
    
    decel_count = np.zeros(len(df))
    count = 0
    slope_vals = df["slope"].values
    
    for i in range(1, len(df)):
        slope_t = slope_vals[i]
        slope_prev = slope_vals[i - 1]
        
        # Check Decel condition: slope falling and positive trend above epsilon
        if not np.isnan(slope_t) and not np.isnan(slope_prev):
            is_rising = slope_t > slope_epsilon
            is_decel = slope_t < slope_prev
            if is_rising and is_decel:
                count += 1
            else:
                count = 0
        else:
            count = 0
        decel_count[i] = count
        
    df["decel_count"] = decel_count
    return df
