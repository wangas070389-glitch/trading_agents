import pytest
import pandas as pd
import numpy as np
from backtest_intraday import _to_utc_naive, compute_hourly_macd, SPREADS

def test_to_utc_naive():
    # Create datetime index with US timezone
    idx = pd.date_range("2026-06-22 09:30:00", periods=5, freq="h", tz="America/New_York")
    df = pd.DataFrame({"Close": [100.0, 101.0, 102.0, 103.0, 104.0]}, index=idx)
    
    df_naive = _to_utc_naive(df)
    
    assert df_naive.index.tz is None
    # America/New_York is UTC-4 in June (daylight saving)
    # 09:30 America/New_York -> 13:30 UTC
    assert df_naive.index[0].hour == 13
    assert df_naive.index[0].minute == 30

def test_compute_hourly_macd():
    # Generate 50 points of dummy closing prices
    prices = np.linspace(100.0, 110.0, 50) + np.sin(np.linspace(0, 10, 50))
    idx = pd.date_range("2026-06-22 08:30:00", periods=50, freq="h")
    df = pd.DataFrame({"Close": prices}, index=idx)
    
    df_macd = compute_hourly_macd(df)
    
    assert "MACD" in df_macd.columns
    assert "Signal" in df_macd.columns
    assert "Hist" in df_macd.columns
    assert not df_macd["MACD"].isna().all()

def test_spreads_definitions():
    assert "SPY" in SPREADS
    assert "NVDA" in SPREADS
    assert "WALMEX.MX" in SPREADS
    assert SPREADS["SPY"] < SPREADS["WALMEX.MX"]
