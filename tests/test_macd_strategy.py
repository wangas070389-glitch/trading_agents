import pytest
import numpy as np
import pandas as pd

from skills.macd_trend import calculate_rma, calculate_atr, calculate_adx, calculate_linreg_slope, calculate_macd

def test_calculate_rma():
    # Test series: 10, 11, 12, 13, 14, 15
    series = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])
    length = 3
    
    # Indices:
    # idx 0: 10
    # idx 1: 11
    # idx 2: 12 -> SMA = (10 + 11 + 12)/3 = 11.0. RMA[2] = 11.0
    # idx 3: 13 -> RMA[3] = 13.0 * (1/3) + 11.0 * (2/3) = 13/3 + 22/3 = 35/3 = 11.6667
    # idx 4: 14 -> RMA[4] = 14.0 * (1/3) + (35/3) * (2/3) = 14/3 + 70/9 = 112/9 = 12.4444
    
    rma = calculate_rma(series, length)
    
    assert np.isnan(rma.iloc[0])
    assert np.isnan(rma.iloc[1])
    assert pytest.approx(rma.iloc[2], 0.0001) == 11.0
    assert pytest.approx(rma.iloc[3], 0.0001) == 35.0 / 3.0
    assert pytest.approx(rma.iloc[4], 0.0001) == 112.0 / 9.0

def test_calculate_linreg_slope():
    # Linear increasing series
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    slope = calculate_linreg_slope(series, 3)
    
    assert np.isnan(slope.iloc[0])
    assert np.isnan(slope.iloc[1])
    assert pytest.approx(slope.iloc[2]) == 1.0
    assert pytest.approx(slope.iloc[3]) == 1.0
    assert pytest.approx(slope.iloc[4]) == 1.0

    # Decreasing series
    series2 = pd.Series([5.0, 4.0, 3.0, 2.0, 1.0])
    slope2 = calculate_linreg_slope(series2, 3)
    
    assert pytest.approx(slope2.iloc[2]) == -1.0
    assert pytest.approx(slope2.iloc[3]) == -1.0
    assert pytest.approx(slope2.iloc[4]) == -1.0

def test_calculate_macd():
    # Verify MACD runs without crashing and has correct length
    series = pd.Series(np.random.normal(100.0, 1.0, 100))
    macd_line, signal_line = calculate_macd(series, 12, 26, 9)
    assert len(macd_line) == 100
    assert len(signal_line) == 100
    assert not macd_line.isna().all()

def test_calculate_atr():
    # Mock dataframe with flat high/low/close
    df = pd.DataFrame({
        "high": [10.0, 10.0, 10.0, 10.0, 10.0],
        "low": [8.0, 8.0, 8.0, 8.0, 8.0],
        "close": [9.0, 9.0, 9.0, 9.0, 9.0]
    })
    atr = calculate_atr(df, length=3)
    assert len(atr) == 5

def test_run_multi_asset_simulation():
    from backtest_macd import run_multi_asset_simulation
    
    # Create mock dataframes for 2 assets
    dates = pd.date_range(start="2023-01-01", periods=10)
    df1 = pd.DataFrame({
        "open": [10.0] * 10,
        "high": [12.0] * 10,
        "low": [9.0] * 10,
        "close": [11.0] * 10,
        "volume": [1000] * 10
    }, index=dates)
    
    df2 = pd.DataFrame({
        "open": [20.0] * 10,
        "high": [22.0] * 10,
        "low": [19.0] * 10,
        "close": [21.0] * 10,
        "volume": [2000] * 10
    }, index=dates)
    
    data_dict = {
        "ASSET1": df1,
        "ASSET2": df2
    }
    
    params = {
        "longTermMALength": 3,
        "maType": "SMA",
        "fastLength": 2,
        "slowLength": 4,
        "signalLength": 2,
        "profitTriggerPercent": 5.0,
        "trailingStopPercent": 2.0,
        "defaultQtyValue": 10.0,
        "pyramiding": 1,
        "commission": 0.0010,
        "slippage_cents": 3,
    }
    
    nav_df, trades = run_multi_asset_simulation(data_dict, params)
    
    assert not nav_df.empty
    assert "NAV" in nav_df.columns
    assert len(nav_df) == 8  # 10 periods minus 2 periods warmup (for SMA 3)
