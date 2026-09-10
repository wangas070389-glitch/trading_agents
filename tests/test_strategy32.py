import numpy as np
import pandas as pd
import pytest
from strategy32 import ASSETS, targets, simulate
from paper_strategy32 import replay


def sample():
    dates = pd.bdate_range("2005-01-01", "2007-12-31")
    rng = np.random.default_rng(32)
    data = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, (len(dates), 4)), axis=0)), index=dates, columns=ASSETS)
    data["FX"] = 20.0
    return data


def test_targets_bounded_and_no_future_information():
    data = sample()
    weights = targets(data)
    assert (weights.sum(axis=1) <= 1 + 1e-10).all()
    assert (weights <= 0.35).all().all()
    altered = data.copy()
    altered.iloc[400:, :4] *= 2
    pd.testing.assert_frame_equal(weights.iloc[:400], targets(altered).iloc[:400])


def test_execution_only_initial_or_first_session_of_month():
    frame, events = simulate(sample())
    allowed = set(frame.groupby(frame.index.to_period("M")).head(1).index.strftime("%Y-%m-%d"))
    assert all(event["date"] in allowed for event in events)
    assert frame.cash_mxn.min() >= -1e-7


def test_cash_and_units_reconcile_and_replay_is_idempotent():
    data = sample()
    first = replay(data, "2006-01-01")
    assert first == replay(data, "2006-01-01")
    assert first["accounting_reconciled"]


def test_fees_reduce_flat_price_portfolio():
    data = sample()
    data[ASSETS] = 100.0
    free, _ = simulate(data, "equal", cost=0)
    paid, _ = simulate(data, "equal", cost=0.003)
    assert free.nav_mxn.iloc[-1] == pytest.approx(200000)
    assert paid.nav_mxn.iloc[-1] == pytest.approx(200000 / 1.003)


def test_bad_data_rejected():
    data = sample()
    data.iloc[300, 0] = np.nan
    with pytest.raises(ValueError):
        simulate(data)


def test_future_prices_do_not_change_past_fills():
    data = sample()
    baseline, events = simulate(data)
    modified = data.copy()
    modified.iloc[500:, :4] *= 1.5
    changed, changed_events = simulate(modified)
    pd.testing.assert_frame_equal(baseline.loc[:data.index[499]], changed.loc[:data.index[499]])
    cutoff = str(data.index[500].date())
    assert [e for e in events if e["date"] < cutoff] == [e for e in changed_events if e["date"] < cutoff]
