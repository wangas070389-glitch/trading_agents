"""Entirely synthetic invariant tests. No synthetic return is market evidence."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from skills.earnings_momentum import Dataset, DataError, PARAMS, select, simulate, funded_allocation
import strategy34 as cli


def sample(n=280, stocks=6, start="2024-01-02"):
    dates = pd.bdate_range(start, periods=n)
    ids = [f"ID:{i}" for i in range(stocks)]
    bundle = dict(schema_version=1, dataset_kind="synthetic", sessions=[], securities=[], prices=[],
                  universes=[], actuals=[], estimates=[], provenance={})
    for field in ("provider", "universe_definition", "calendar_source", "price_adjustment_method", "eps_basis_method", "availability_method"):
        bundle["provenance"][field] = "SYNTHETIC TEST ONLY"
    bundle["provenance"]["exported_at"] = "2026-01-01T00:00:00Z"
    for sid in ids+["QQQ"]:
        bundle["securities"].append(dict(sid=sid, kind="benchmark" if sid == "QQQ" else "common_stock", currency="USD", label=sid))
    for i, date in enumerate(dates):
        day = date.date().isoformat()
        bundle["sessions"].append(dict(date=day, close_at=day+"T21:00:00Z", decision_at=day+"T21:15:00Z"))
        for j, sid in enumerate(ids+["QQQ"]):
            price = 100*np.exp((.0006+.0001*j)*i + .002*np.sin(i*.31+j))
            bundle["prices"].append(dict(sid=sid, date=day, available_at=day+"T21:01:00Z",
                                          tr_index=float(price), raw_close=float(price), dollar_volume=20_000_000.,
                                          tradable=True, terminal=False))
        if i % 10 == 0:
            bundle["universes"].append(dict(asof_at=day+"T20:00:00Z", available_at=day+"T20:05:00Z", source_ref="fixture",
                                             members=[dict(sid=sid, sector=f"sector:{j%3}") for j, sid in enumerate(ids)]))
            for j, sid in enumerate(ids):
                bundle["estimates"].append(dict(sid=sid, period_end="2026-12-31", period_type="annual", asof_at=day+"T18:00:00Z",
                                                 available_at=day+"T18:05:00Z", eps=2.+i*.005+j*.01,
                                                 basis_id="fixture_USD_EPS", currency="USD", source_ref="fixture"))
        if i >= 120 and i % 30 == 0:
            period = (date-pd.Timedelta(days=40)).date().isoformat()
            prior = dates[i-2].date().isoformat()
            for j, sid in enumerate(ids):
                bundle["actuals"].append(dict(sid=sid, event_id=f"{sid}:{i}", period_end=period, announced_at=day+"T22:00:00Z",
                                               available_at=day+"T22:05:00Z", eps=1.2+j*.01, basis_id="fixture_USD_EPS",
                                               currency="USD", version=0, source_ref="fixture"))
                bundle["estimates"].append(dict(sid=sid, period_end=period, period_type="quarter", asof_at=prior+"T18:00:00Z",
                                                 available_at=prior+"T18:05:00Z", eps=1., basis_id="fixture_USD_EPS",
                                                 currency="USD", source_ref="fixture"))
    return bundle


def test_initial_actual_uses_strict_preannouncement_consensus():
    bundle = sample()
    original = Dataset(bundle).earnings("ID:0", 151)
    assert original["surprise"] == pytest.approx(.2)
    # A late-arriving record with a backdated as-of must never replace consensus.
    estimate = copy.deepcopy(next(r for r in bundle["estimates"] if r["sid"] == "ID:0" and r["period_type"] == "quarter" and r["period_end"] == bundle["actuals"][6]["period_end"]))
    estimate["available_at"] = bundle["sessions"][151]["decision_at"]
    estimate["eps"] = .01
    bundle["estimates"].append(estimate)
    assert Dataset(bundle).earnings("ID:0", 151) == original


def test_after_hours_earnings_not_usable_before_publication():
    data = Dataset(sample())
    assert data.earnings("ID:0", 150)["event_id"] == "ID:0:120"
    assert data.earnings("ID:0", 151)["event_id"] == "ID:0:150"


def test_restatements_never_replace_initial_actual():
    bundle = sample()
    base = Dataset(bundle).earnings("ID:0", 151)
    revised = copy.deepcopy(next(r for r in bundle["actuals"] if r["event_id"] == "ID:0:150"))
    revised.update(version=1, eps=1000., available_at=bundle["sessions"][151]["decision_at"])
    bundle["actuals"].append(revised)
    assert Dataset(bundle).earnings("ID:0", 151) == base


def test_eps_basis_mismatch_excludes_signal():
    bundle = sample()
    for r in bundle["estimates"]:
        if r["sid"] == "ID:0" and r["period_type"] == "quarter":
            r["basis_id"] = "incompatible_split_or_GAAP_basis"
    assert Dataset(bundle).earnings("ID:0", 151) is None


def test_revision_never_compares_different_fiscal_periods():
    bundle = sample()
    cutoff = pd.Timestamp(bundle["sessions"][151-PARAMS["revision_sessions"]]["decision_at"])
    for r in bundle["estimates"]:
        if r["sid"] == "ID:0" and r["period_type"] == "annual" and pd.Timestamp(r["available_at"]) <= cutoff:
            r["period_end"] = "2023-12-31"
    assert Dataset(bundle).earnings("ID:0", 151) is None


def test_future_data_cannot_change_past_selections_or_fills():
    first = sample()
    second = copy.deepcopy(first)
    cutoff = first["sessions"][210]["decision_at"]
    for r in second["prices"]:
        if r["date"] >= first["sessions"][211]["date"]:
            r["tr_index"] *= .5
    for r in second["estimates"]:
        if r["available_at"] > cutoff:
            r["eps"] *= 3
    a, b = Dataset(first), Dataset(second)
    assert select(a, 200) == select(b, 200)
    nav_a, trades_a, _, _ = simulate(a)
    nav_b, trades_b, _, _ = simulate(b)
    date = first["sessions"][210]["date"]
    pd.testing.assert_frame_equal(nav_a.loc[:date], nav_b.loc[:date])
    assert [t for t in trades_a if t["date"] <= date] == [t for t in trades_b if t["date"] <= date]


def test_universe_membership_available_later_is_not_visible_early():
    bundle = sample()
    initial = Dataset(bundle).universe(pd.Timestamp(bundle["sessions"][151]["decision_at"]))
    record = copy.deepcopy(bundle["universes"][15])
    record["available_at"] = bundle["sessions"][160]["decision_at"]
    record["members"] = []
    bundle["universes"].append(record)
    assert Dataset(bundle).universe(pd.Timestamp(bundle["sessions"][151]["decision_at"])) == initial


def test_position_sector_and_funding_caps():
    data = Dataset(sample(stocks=25))
    weights, selected = select(data, 151)
    assert 0 < len(weights) <= 20
    assert max(weights.values()) <= .05
    assert sum(weights.values()) <= 1+1e-10
    for sector in {r["sector"] for r in selected}:
        assert sum(weights[r["sid"]] for r in selected if r["sector"] == sector) <= .25+1e-10


def test_two_sided_fees_are_funded():
    target, cash, trades, fees = funded_allocation({"A": 1000.}, {"B": 1.}, 1000., .01)
    assert target["B"] == pytest.approx(1000*.99/1.01)
    assert cash == pytest.approx(0, abs=1e-10)
    assert fees == pytest.approx(.01*(1000+target["B"]))
    assert trades["A"] == -1000


def test_nav_cash_ledger_reconcile_and_signals_fill_later():
    data = Dataset(sample())
    frame, ledger, _, rejected = simulate(data)
    assert not rejected
    cash, units = 100000., {}
    assert ledger
    for date, row in frame.iterrows():
        day = str(date.date())
        for event in (r for r in ledger if r["date"] == day):
            assert pd.Timestamp(event["decision_at"]).date() < date.date()
            cash += event["cash_delta"]
            quote = data.prices[(day, event["sid"])]["tr_index"]
            change = event["notional"]/quote*(1 if event["action"] == "BUY" else -1)
            units[event["sid"]] = units.get(event["sid"], 0)+change
        nav = cash+sum(q*data.prices[(day, sid)]["tr_index"] for sid, q in units.items())
        assert cash == pytest.approx(row.cash, abs=1e-7)
        assert nav == pytest.approx(row.nav, abs=1e-7)
    assert frame.cash.min() >= -1e-7


def test_failed_sell_never_finances_buys():
    bundle = sample()
    data = Dataset(bundle)
    switch_index = next(i for i in range(140, 150) if pd.Timestamp(data.sessions[i]["date"]).weekday() == 0)
    fill_date = data.sessions[switch_index+1]["date"]
    data.prices[(fill_date, "ID:0")]["tradable"] = False
    def fixed_select(data, index, mode):
        sid = "ID:0" if index < switch_index else "ID:1"
        return {sid: .5}, [dict(sid=sid, adv=20_000_000.)]
    with patch("skills.earnings_momentum.select", side_effect=fixed_select):
        frame, ledger, _, rejected = simulate(data)
    assert any(r["date"] == fill_date for r in rejected)
    assert not any(r["date"] == fill_date for r in ledger)
    assert frame.loc[fill_date, "holdings"] == 1


def test_missing_held_price_aborts_not_erases_loss():
    data = Dataset(sample())
    with patch("skills.earnings_momentum.select", return_value=({"ID:0": .5}, [dict(sid="ID:0", adv=20_000_000.)])):
        del data.prices[(data.sessions[150]["date"], "ID:0")]
        with pytest.raises(DataError, match="held mark"):
            simulate(data)


def test_zero_terminal_settlement_preserves_total_loss():
    bundle = sample()
    terminal_date = bundle["sessions"][150]["date"]
    bundle["prices"] = [r for r in bundle["prices"] if r["sid"] != "ID:0" or r["date"] <= terminal_date]
    next(r for r in bundle["prices"] if r["sid"] == "ID:0" and r["date"] == terminal_date).update(terminal=True, tradable=False, tr_index=0., raw_close=0.)
    data = Dataset(bundle)
    with patch("skills.earnings_momentum.select", return_value=({"ID:0": .5}, [dict(sid="ID:0", adv=20_000_000.)])):
        frame, ledger, _, _ = simulate(data)
    assert frame.loc[terminal_date, "nav"] < frame.iloc[23].nav*.6
    assert any(r["action"] == "TERMINAL" and r["cash_delta"] == 0 for r in ledger)


@pytest.mark.parametrize("change", ["naive_timestamp", "duplicate_price", "negative_price", "late_benchmark", "duplicate_actual"])
def test_bad_data_fails_closed(change):
    bundle = sample()
    if change == "naive_timestamp":
        bundle["actuals"][0]["available_at"] = "2024-07-01"
    elif change == "duplicate_price":
        bundle["prices"].append(copy.deepcopy(bundle["prices"][0]))
    elif change == "negative_price":
        bundle["prices"][0]["tr_index"] = -1
    elif change == "late_benchmark":
        next(r for r in bundle["prices"] if r["sid"] == "QQQ")["available_at"] = "2030-01-01T00:00:00Z"
    else:
        bundle["actuals"].append(copy.deepcopy(bundle["actuals"][0]))
    with pytest.raises(DataError):
        Dataset(bundle)


def test_missing_data_and_review_never_publish_performance(tmp_path):
    status, data = cli.audit(tmp_path / "missing.json")
    assert status["status"] == "BLOCKED_DATA_REQUIRED"
    assert status["performance_available"] is False
    assert data is None


def test_synthetic_bundle_cannot_be_market_evidence(tmp_path):
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(sample()), encoding="utf-8")
    status, _ = cli.audit(path)
    assert any("MARKET_DATA_REQUIRED" in e for e in status["errors"])
    assert not status["performance_available"]


def test_review_hash_and_attestation_fail_closed(tmp_path):
    path, review_path = tmp_path / "fixture.json", tmp_path / "review.json"
    path.write_text(json.dumps(sample()), encoding="utf-8")
    review_path.write_text(json.dumps(dict(dataset_sha256="wrong", reviewer="fixture", coverage_notes="fixture", reviewed_at="2025-01-01T00:00:00Z", checks={})), encoding="utf-8")
    status, _ = cli.audit(path, review_path)
    assert "REVIEW_HASH_MISMATCH" in status["errors"]
    assert any("REVIEW_INCOMPLETE" in e for e in status["errors"])


def test_output_cannot_overwrite_operating_or_public_artifacts(tmp_path):
    with pytest.raises(DataError, match="private"):
        cli.run(tmp_path / "missing", None, cli.ROOT / "research/strategy34/report")


def test_unregistered_and_no_trade_authorization():
    from strategy_registry import STRATEGIES
    assert not any(s.key == "s34" for s in STRATEGIES)
    design = json.loads((cli.RESEARCH / "design.json").read_text(encoding="utf-8"))
    assert design["params"] == PARAMS
    assert design["execution"]["margin"] is False


def test_reviewed_schema_passes_input_gate_without_claiming_profit(tmp_path):
    bundle = sample(n=1000, stocks=2, start="2019-01-02")
    # Simulated vendor export to test the gate, never an empirical result.
    bundle["dataset_kind"] = "market"
    path, review_path = tmp_path / "fixture.json", tmp_path / "review.json"
    raw = json.dumps(bundle).encode()
    path.write_bytes(raw)
    review = dict(dataset_sha256=cli.sha(raw), reviewer="unit-test fixture", coverage_notes="synthetic gate test only",
                  reviewed_at="2026-01-02T00:00:00Z", checks={k: True for k in cli.REVIEW_CHECKS})
    review_path.write_text(json.dumps(review), encoding="utf-8")
    status, data = cli.audit(path, review_path)
    assert status["errors"] == []
    assert status["status"] == "INPUTS_REVIEWED_RESEARCH_ONLY"
    assert status["performance_available"] is False
    assert status["deployment_approved"] is False
    assert data is not None
    # Modifying a reviewed input invalidates its review.
    path.write_bytes(raw+b"\n")
    changed, _ = cli.audit(path, review_path)
    assert "REVIEW_HASH_MISMATCH" in changed["errors"]


def test_private_end_to_end_replay_and_no_overwrite(tmp_path, monkeypatch):
    data = Dataset(sample(n=165, stocks=2))
    private = tmp_path / "private"
    review_path = tmp_path / "review.json"
    review_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli, "PRIVATE", private)
    monkeypatch.setattr(cli, "audit", lambda *args: ({"errors": [], "dataset_sha256": "synthetic_fixture"}, data))
    result = cli.run(tmp_path / "fixture.json", review_path, private / "run")
    assert not result["deployment_approved"]
    saved = json.loads((private / "run/results.json").read_text(encoding="utf-8"))
    assert len(saved["results"]) == 15
    for value in saved["results"].values():
        assert value["filled_legs"] > 0
        assert value["terminal_settlements"] == 0
    assert saved["status"] == "RETROSPECTIVE_RESEARCH_ONLY_NO_PROMOTION"
    assert (private / "run/report.md").exists()
    with pytest.raises(DataError, match="already exists"):
        cli.run(tmp_path / "fixture.json", review_path, private / "run")


def test_cli_missing_bundle_exits_nonzero_without_results(tmp_path, capsys):
    code = cli.main(["audit", "--bundle", str(tmp_path / "missing.json")])
    assert code == 2
    assert json.loads(capsys.readouterr().out)["performance_available"] is False
    assert not (tmp_path / "results.json").exists()


def test_two_session_fill_waits_for_second_close():
    data = Dataset(sample(n=155, stocks=2))
    _, ledger, _, _ = simulate(data, lag=2)
    assert ledger
    for leg in ledger:
        signal_date = str(pd.Timestamp(leg["decision_at"]).date())
        assert data.date_index[leg["date"]]-data.date_index[signal_date] == 2


def test_coverage_matched_momentum_ignores_earnings_sign_but_not_missing_data():
    bundle = sample()
    for r in bundle["actuals"]:
        if r["sid"] == "ID:0":
            r["eps"] = .5  # Negative surprise, but still usable coverage.
    bundle["estimates"] = [r for r in bundle["estimates"] if r["sid"] != "ID:1" or r["period_type"] != "quarter"]
    data = Dataset(bundle)
    primary, _ = select(data, 151, "combined")
    covered, _ = select(data, 151, "momentum_covered")
    broad, _ = select(data, 151, "momentum_only")
    assert "ID:0" not in primary and "ID:0" in covered
    assert "ID:1" not in covered and "ID:1" in broad
