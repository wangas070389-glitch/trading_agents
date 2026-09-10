import json
import pytest
from accounting import nav_value
from reconcile_strategy_navs import parse_ledger
import graduation_report as graduation


def test_currency_cash_supersedes_legacy_alias():
    portfolio = {"cash_balance": 999, "cash_balance_mxn": 100,
                 "cash_balance_usd": 10, "holdings": [{"shares": 2, "last_price": 50}]}
    assert nav_value(portfolio, "MXN", 20) == (400, 300)


def test_nonfinite_marks_rejected():
    with pytest.raises(ValueError):
        nav_value({"cash_balance": float("nan")}, "MXN", 20)


def test_initial_funding_not_counted_as_contribution(tmp_path, monkeypatch):
    monkeypatch.setattr(graduation, "DIR", str(tmp_path))
    (tmp_path / "ledger.md").write_text(
        "| 2026-07-01 | CASH | DEPOSIT | 1 | $200,000 | Initial capital funding |\n"
        "| 2026-08-01 | CASH | DEPOSIT | 1 | $1,000 | contribution |\n")
    assert graduation.deposits_from_ledger("ledger.md") == 1000
    assert graduation.deposits_from_ledger("ledger.md", "2026-08-02") == 0


def test_malformed_and_unknown_ledger_rows_cannot_verify(tmp_path):
    path = tmp_path / "ledger.md"
    path.write_text("| Date | Ticker | Action | Qty | Price | Note |\n"
                    "| 2026-01-01 | USD | BUY_USD | 2 | 20 | FX |\n"
                    "| 2026-01-01 | CASH | DEPOSIT | 1 |\n")
    positions, cash, rows, errors = parse_ledger(path)
    assert len(errors) == 2


def test_deposit_does_not_create_investment_return(tmp_path, monkeypatch):
    monkeypatch.setattr(graduation, "DIR", str(tmp_path))
    (tmp_path / "ledger.md").write_text("| 2026-08-02 | CASH | DEPOSIT | 1 | 50 | Contribution |\n")
    strat = {"key": "sample", "ledger": "ledger.md", "inception": "2026-08-01", "ms_key": None}
    series, _ = graduation.daily_series(strat, [], {"sample": [
        {"ts": "2026-07-01", "nav": 99}, {"ts": "2026-08-01", "nav": 100},
        {"ts": "2026-08-02", "nav": 150}, {"ts": "2026-08-03", "nav": 165}]})
    assert series == pytest.approx([1, 1, 1.1])
