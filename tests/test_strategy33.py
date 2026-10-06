"""Synthetic safety/accounting checks for the research-only growth challenger."""
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

import strategy33 as s33


def sample(n=650):
    rng = np.random.default_rng(3301)
    r = rng.normal(.0006, .008, n)
    return pd.DataFrame({"QQQ": 100*np.cumprod(1+r),
                         "TQQQ": 50*np.cumprod(1+3*r-.0004),
                         "FX": 20*np.cumprod(1+rng.normal(0, .003, n))},
                        index=pd.bdate_range("2010-02-11", periods=n))


def test_targets_have_no_margin_or_shorting_and_respect_exposure():
    data = sample()
    for mode in s33.MODES:
        weights = s33.targets(data, mode)
        assert (weights >= 0).all().all()
        assert (weights.sum(axis=1) <= 1+1e-10).all()
        cap = 3 if mode == "tqqq" else 1 if mode == "qqq" else 1.5 if mode == "s12_reference" else 2
        assert ((weights.QQQ + 3*weights.TQQQ) <= cap+1e-10).all()


def test_future_prices_cannot_change_targets_nav_or_fills():
    data = sample()
    other = data.copy()
    other.iloc[500:] *= np.array([.7, .2, 1.2])
    pd.testing.assert_frame_equal(s33.targets(data).iloc[:500], s33.targets(other).iloc[:500])
    for mode in s33.MODES:
        first, trades = s33.simulate(data, mode)
        second, later_trades = s33.simulate(other, mode)
        pd.testing.assert_frame_equal(first.loc[:data.index[499]], second.loc[:data.index[499]])
        assert [t for t in trades if t["date"] < str(data.index[500].date())] == [t for t in later_trades if t["date"] < str(data.index[500].date())]


def test_fees_are_funded_and_full_switch_pays_both_sides():
    holdings, cash, fee, _ = s33.funded_rebalance(np.zeros(2), np.array([1., 0.]), 1000., .01)
    assert holdings.sum() == pytest.approx(1000/1.01)
    assert cash == pytest.approx(0, abs=1e-10)
    after, cash, fees, _ = s33.funded_rebalance(holdings, np.array([0., 1.]), holdings.sum(), .01)
    assert after.sum() == pytest.approx(holdings.sum()*.99/1.01)
    assert fees == pytest.approx(.01*(holdings.sum()+after.sum()))


def test_cash_quantities_nav_replay_from_trade_ledger():
    data = sample()
    frame, events = s33.simulate(data, cash_apr=.0653)
    cash, units = 200000., dict(QQQ=0., TQQQ=0.)
    by_date = {}
    for trade in events:
        by_date.setdefault(trade["date"], []).append(trade)
        assert trade["signal_date"] < trade["date"]
    for date, row in frame.iterrows():
        cash += row.interest_mxn
        for trade in by_date.get(str(date.date()), []):
            cash += trade["cash_delta"]
            units[trade["ticker"]] += trade["quantity"]
        assert cash == pytest.approx(row.cash_mxn, abs=1e-7)
        for ticker in s33.ASSETS:
            assert units[ticker] == pytest.approx(row[f"units_{ticker}"], abs=1e-8)
        nav = cash + sum(units[t]*data.loc[date, t]*data.loc[date, "FX"] for t in s33.ASSETS)
        assert nav == pytest.approx(row.nav_mxn, abs=1e-7)
    assert frame.cash_mxn.min() >= -1e-7


def test_entry_does_not_earn_the_pre_fill_return():
    data = sample()
    data.loc[:, ["QQQ", "TQQQ", "FX"]] = [100., 100., 20.]
    start = data.index[280]
    data.loc[start:, "QQQ"] *= 2
    frame, _ = s33.simulate(data, mode="qqq", start=start)
    assert frame.nav_mxn.iloc[0] == pytest.approx(200000/1.003)
    assert frame.nav_mxn.iloc[-1] == pytest.approx(frame.nav_mxn.iloc[0])
    result = s33.metrics(frame, "2010", "2020")
    assert result["max_dd"] == pytest.approx(1/1.003-1)
    assert result["total_return"] < 0


def test_challenger_risk_off_exits_on_non_weekly_day():
    data = sample()
    desired = pd.DataFrame({"QQQ": 1., "TQQQ": 0.}, index=data.index)
    exit_signal = next(d for d in data.index[300:310] if d.weekday() == 1)
    desired.loc[exit_signal:] = 0
    with patch.object(s33, "targets", return_value=desired):
        frame, events = s33.simulate(data)
    exit_date = data.index[data.index.get_loc(exit_signal)+1]
    assert frame.loc[exit_date, "units_QQQ"] == pytest.approx(0)
    assert any(e["date"] == str(exit_date.date()) and e["quantity"] < 0 for e in events)


def test_two_session_lag_is_obeyed():
    data = sample()
    _, events = s33.simulate(data, lag=2)
    assert events
    for event in events:
        assert data.index.get_loc(pd.Timestamp(event["date"])) - data.index.get_loc(pd.Timestamp(event["signal_date"])) == 2


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0., -1.])
def test_bad_market_data_rejected(bad):
    data = sample()
    data.iloc[300, 0] = bad
    with pytest.raises(ValueError):
        s33.simulate(data)


def test_frozen_manifest_matches_design_and_price_bytes():
    manifest_file = s33.OUTPUT / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    for file, key in (("prices.csv", "sha256"), ("design.json", "design_sha256")):
        assert s33.sha((s33.OUTPUT / file).read_bytes()) == manifest[key]


def test_not_registered_for_execution():
    from strategy_registry import STRATEGIES
    assert not any(spec.key == "s33" for spec in STRATEGIES)


def test_invalid_execution_assumptions_rejected():
    for params in ({"lag": 0}, {"seed": -1}, {"cost": -.1}, {"cash_apr": np.nan}):
        with pytest.raises(ValueError):
            s33.simulate(sample(), **params)


def test_control_has_same_target_beta_but_distinct_cash_and_fx_exposure():
    data = sample()
    candidate = s33.targets(data)
    control = s33.targets(data, "s12_scaled_control")
    np.testing.assert_allclose(candidate.QQQ + 3*candidate.TQQQ, 3*control.TQQQ)
    assert (candidate.sum(axis=1) >= control.sum(axis=1) - 1e-10).all()


def test_initial_units_do_not_depend_on_capital_scale():
    data = sample()
    first, _ = s33.simulate(data, seed=200000)
    second, _ = s33.simulate(data, seed=100000)
    np.testing.assert_allclose(first.nav_mxn, 2*second.nav_mxn)
    a = s33.metrics(first, "2011", "2012")
    b = s33.metrics(second, "2011", "2012")
    assert a["total_return"] == pytest.approx(b["total_return"])
    assert a["max_dd"] == pytest.approx(b["max_dd"])
