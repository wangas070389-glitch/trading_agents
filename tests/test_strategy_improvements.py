import numpy as np
import pytest
from skills.atr_risk_manager import (
    calculate_atr,
    calculate_atr_position_size,
    calculate_chandelier_stop
)
from skills.dcf_valuation_engine import calculate_monte_carlo_dcf
from skills.deep_regime_model import check_multi_timeframe_regime_confluence


def test_calculate_atr():
    np.random.seed(42)
    high = np.array([10, 12, 13, 15, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25], dtype=np.float64)
    low = np.array([8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22], dtype=np.float64)
    close = np.array([9, 11, 12, 14, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24], dtype=np.float64)

    atr = calculate_atr(high, low, close, period=14)
    assert len(atr) == len(close)
    # 14th element (index 13) should be valid ATR
    assert not np.isnan(atr[-1])
    assert atr[-1] > 0.0


def test_atr_position_sizing_volatility_parity():
    equity = 100000.0  # $100k equity

    # Asset A: Low volatility (Price $100, ATR $2.0)
    shares_a = calculate_atr_position_size(
        total_equity=equity,
        current_price=100.0,
        atr_val=2.0,
        target_risk_pct=0.01,  # $1,000 risk
        risk_multiplier=2.0
    )

    # Asset B: High volatility (Price $100, ATR $8.0)
    shares_b = calculate_atr_position_size(
        total_equity=equity,
        current_price=100.0,
        atr_val=8.0,
        target_risk_pct=0.01,  # $1,000 risk
        risk_multiplier=2.0
    )

    # High volatility asset B must result in fewer shares to equalize risk
    assert shares_a > shares_b
    assert shares_a == 250  # 1000 / (2.0 * 2) = 250
    assert shares_b == 62   # 1000 / (8.0 * 2) = 62.5 -> int 62


def test_chandelier_stop():
    peak_price = 150.0
    atr_val = 4.0

    # Long stop should be below peak by multiplier * ATR
    long_stop = calculate_chandelier_stop(peak_price, atr_val, multiplier=3.0, is_long=True)
    assert long_stop == 150.0 - (3.0 * 4.0)  # 138.0

    # Short stop should be above peak
    short_stop = calculate_chandelier_stop(peak_price, atr_val, multiplier=3.0, is_long=False)
    assert short_stop == 150.0 + (3.0 * 4.0)  # 162.0


def test_monte_carlo_dcf_valuation():
    res = calculate_monte_carlo_dcf(
        current_price=50.0,
        shares_outstanding=1_000_000,
        base_fcff=10_000_000,
        wacc=0.09,
        total_debt=5_000_000,
        cash_and_equivalents=2_000_000,
        growth_rate_stage1=0.08,
        terminal_growth=0.03,
        num_simulations=500,
        seed=42
    )

    assert "intrinsic_value_base" in res
    assert "iv_mean" in res
    assert "iv_p10" in res
    assert "iv_p90" in res
    assert "margin_of_safety_p10" in res

    # 10th percentile IV should be lower than 90th percentile IV
    assert res["iv_p10"] <= res["iv_mean"] <= res["iv_p90"]
    assert res["iv_p10"] > 0.0


def test_multi_timeframe_regime_confluence():
    # Both Bull
    res_bull = check_multi_timeframe_regime_confluence(daily_regime=0, intraday_regime=0)
    assert res_bull["has_confluence"] is True
    assert res_bull["action"] == "BULL_LONG"
    assert res_bull["confidence"] == 0.95

    # Both Bear
    res_bear = check_multi_timeframe_regime_confluence(daily_regime=1, intraday_regime=1)
    assert res_bear["has_confluence"] is True
    assert res_bear["action"] == "BEAR_SHORT"

    # Conflicting: Daily Bull vs Intraday Bear -> Dip Buy
    res_conflict = check_multi_timeframe_regime_confluence(daily_regime=0, intraday_regime=1)
    assert res_conflict["has_confluence"] is False
    assert res_conflict["action"] == "DIP_BUY"
