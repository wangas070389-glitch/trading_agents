import numpy as np
import pandas as pd
import pytest
from skills.kalman_hedge_ratio import KalmanHedgeTracker, calculate_kalman_hedge_ratio
from skills.hierarchical_risk_parity import calculate_hrp_weights
from skills.dividend_screener import filter_dividend_quality
from skills.alternative_indicators import calculate_dynamic_fib_confluence


def test_kalman_hedge_tracker_convergence():
    np.random.seed(42)
    n = 100
    true_alpha = 2.0
    true_beta = 1.5
    
    x = np.linspace(10, 50, n)
    y = true_alpha + true_beta * x + np.random.normal(0, 0.1, n)
    
    res = calculate_kalman_hedge_ratio(y, x)
    
    assert "beta" in res
    assert "alpha" in res
    assert "current_zscore" in res
    # Estimated beta should converge close to true beta (1.5)
    assert abs(res["beta"] - true_beta) < 0.25


def test_hierarchical_risk_parity_weights():
    np.random.seed(42)
    # Generate 4 asset returns with synthetic covariance
    returns = pd.DataFrame(np.random.randn(200, 4), columns=["AssetA", "AssetB", "AssetC", "AssetD"])
    returns["AssetB"] += returns["AssetA"] * 0.8  # Correlate A and B
    
    cov_matrix = returns.cov()
    weights = calculate_hrp_weights(cov_matrix)
    
    assert isinstance(weights, pd.Series)
    assert len(weights) == 4
    # All weights must be positive and sum to 1.0
    assert np.all(weights >= 0.0)
    assert pytest.approx(weights.sum(), abs=1e-6) == 1.0


def test_filter_dividend_quality():
    # Good dividend quality candidate
    good_metrics = {
        "ticker": "WALMEX.MX",
        "dividend_yield": 0.045,
        "payout_ratio": 0.65,
        "fcf_payout_ratio": 0.70,
        "eps": 2.50,
        "debt_to_equity": 0.80,
        "div_growth_3y": 0.08
    }
    res_good = filter_dividend_quality(good_metrics)
    assert res_good["is_quality"] is True
    assert len(res_good["rejection_reasons"]) == 0
    assert res_good["quality_score"] > 0.0
    
    # Yield trap candidate (FCF payout > 85%, high leverage)
    bad_metrics = {
        "ticker": "BADTRAP.MX",
        "dividend_yield": 0.12,
        "payout_ratio": 1.20,
        "fcf_payout_ratio": 1.10,
        "eps": -0.50,
        "debt_to_equity": 5.50,
        "div_growth_3y": -0.05
    }
    res_bad = filter_dividend_quality(bad_metrics)
    assert res_bad["is_quality"] is False
    assert len(res_bad["rejection_reasons"]) > 0


def test_calculate_dynamic_fib_confluence():
    fib_levels = [100.0, 150.0, 200.0]
    
    # Baseline ATR (3.0): tolerance = 1.5%
    res_base = calculate_dynamic_fib_confluence(151.5, fib_levels, atr_val=3.0, base_tolerance=0.015)
    assert res_base["is_confluent"] is True
    assert res_base["effective_tolerance"] == 0.015
    
    # High ATR (12.0): tolerance expands toward 2.5%
    res_high_atr = calculate_dynamic_fib_confluence(153.2, fib_levels, atr_val=12.0, base_tolerance=0.015, max_tolerance=0.025)
    assert res_high_atr["is_confluent"] is True
    assert res_high_atr["effective_tolerance"] > 0.015
