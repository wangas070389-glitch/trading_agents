"""Exercise the actual RF engine on synthetic prices, without a market feed."""
import numpy as np
import pandas as pd
from backtest_strategy24 import run_simulation


def test_future_market_data_cannot_change_past_rf_returns():
    rng = np.random.default_rng(2401)
    returns = rng.normal(0.0001, 0.002, 330)
    data = pd.DataFrame({
        "qqq": 100 * np.cumprod(1 + returns),
        "tqqq": 100 * np.cumprod(1 + 3 * returns),
        "sqqq": 100 * np.cumprod(1 - 3 * returns),
        "fx": np.full(330, 20.),
    }, index=pd.date_range("2025-01-01", periods=330, freq="30min"))
    first, _, _ = run_simulation(data, train_window=100, retrain_freq=50, n_estimators=5)
    altered = data.copy()
    altered.iloc[250:, :3] *= 1.5
    second, _, _ = run_simulation(altered, train_window=100, retrain_freq=50, n_estimators=5)
    pd.testing.assert_frame_equal(first.iloc[:250], second.iloc[:250])
    assert np.isfinite(first.nav).all()
    assert (first.nav > 0).all()
