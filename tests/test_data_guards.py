"""Regression tests for the 2026-07 data-integrity hardening.

Covers the guards added after the 2026-07-09 NaN incident (yfinance returned
NaN closes for BMV tickers while the market was closed and runners persisted
them) and the W6 401-masquerade fix (a dead Alpaca key parsed as a clean,
empty account). If any of these fail, a silent-corruption path has reopened.
"""
import math

import pytest

import compare_strategies
import generate_clean_report
import graduation_report
import monitor_portfolio
import run_live_multi_strategy
import watchdog

NAN = float("nan")


# ---------------------------------------------------------------------------
# valuation_price: NaN last_price must fall back to buy_price, never propagate
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module", [compare_strategies, generate_clean_report,
                                    run_live_multi_strategy, graduation_report])
class TestValuationPrice:
    def test_valid_last_price_wins(self, module):
        assert module.valuation_price({"last_price": 10.5, "buy_price": 9.0}) == 10.5

    def test_nan_last_price_falls_back_to_buy(self, module):
        assert module.valuation_price({"last_price": NAN, "buy_price": 9.0}) == 9.0

    def test_missing_last_price_falls_back_to_buy(self, module):
        assert module.valuation_price({"buy_price": 9.0}) == 9.0

    def test_inf_last_price_falls_back_to_buy(self, module):
        assert module.valuation_price({"last_price": float("inf"), "buy_price": 9.0}) == 9.0

    def test_zero_and_negative_are_invalid(self, module):
        assert module.valuation_price({"last_price": 0.0, "buy_price": 9.0}) == 9.0
        assert module.valuation_price({"last_price": -3.0, "buy_price": 9.0}) == 9.0

    def test_both_invalid_returns_zero(self, module):
        assert module.valuation_price({"last_price": NAN, "buy_price": NAN}) == 0.0

    def test_non_numeric_handled(self, module):
        assert module.valuation_price({"last_price": None, "buy_price": "abc"}) == 0.0


# ---------------------------------------------------------------------------
# monitor_portfolio.is_valid_price
# ---------------------------------------------------------------------------
def test_is_valid_price_accepts_positive_finite():
    assert monitor_portfolio.is_valid_price(123.45)
    assert monitor_portfolio.is_valid_price("123.45")  # numeric strings coerce


@pytest.mark.parametrize("bad", [NAN, float("inf"), float("-inf"),
                                 0.0, -1.0, None, "n/a", ""])
def test_is_valid_price_rejects_invalid(bad):
    assert not monitor_portfolio.is_valid_price(bad)


# ---------------------------------------------------------------------------
# get_nav aggregation must not poison the consolidated NAV
# ---------------------------------------------------------------------------
def test_multi_strategy_get_nav_survives_nan_holdings():
    portfolio = {
        "cash_balance": 1000.0,
        "holdings": [
            {"ticker": "A", "shares": 10, "buy_price": 5.0, "last_price": NAN},
            {"ticker": "B", "shares": 2, "buy_price": 3.0, "last_price": 4.0},
        ],
    }
    total, cash, cash_usd = run_live_multi_strategy.get_nav(portfolio)
    assert math.isfinite(total)
    assert total == 1000.0 + 10 * 5.0 + 2 * 4.0  # NaN leg valued at buy_price


def test_clean_report_get_nav_survives_nan_holdings():
    portfolio = {
        "cash_balance": 500.0,
        "holdings": [{"ticker": "A", "shares": 3, "buy_price": 7.0, "last_price": NAN}],
    }
    total, cash, cash_usd = generate_clean_report.get_nav(portfolio)
    assert math.isfinite(total)
    assert total == 500.0 + 3 * 7.0


# ---------------------------------------------------------------------------
# graduation_report helpers
# ---------------------------------------------------------------------------
def test_series_stats_insufficient_samples_returns_none():
    sharpe, dd = graduation_report.series_stats([100.0] * (graduation_report.MIN_SAMPLES_FOR_STATS - 1))
    assert sharpe is None and dd is None


def test_series_stats_drawdown_and_sharpe():
    vals = [100, 102, 104, 103, 106, 108, 110, 112, 95, 111]
    sharpe, dd = graduation_report.series_stats(vals)
    assert dd == pytest.approx(95 / 112 - 1.0)
    assert math.isfinite(sharpe)


def test_deposits_from_ledger(tmp_path, monkeypatch):
    ledger = tmp_path / "transactions_x.md"
    ledger.write_text(
        "# Ledger\n"
        "| 2026-07-01 | CASH | DEPOSIT | 1.00 | $2,000.00 | $0.00 | $-2,000.00 | DCA |\n"
        "| 2026-07-02 | SPY | BUY | 3.00 | $500.00 | $0.00 | $-1,500.00 | trade |\n"
        "| 2026-08-01 | CASH | DEPOSIT | 1.00 | $2,000.00 | $0.00 | $-2,000.00 | DCA |\n",
        encoding="utf-8")
    monkeypatch.setattr(graduation_report, "DIR", str(tmp_path))
    assert graduation_report.deposits_from_ledger("transactions_x.md") == pytest.approx(4000.0)


def test_finite_helper():
    assert graduation_report.finite(1.0)
    assert not graduation_report.finite(NAN)
    assert not graduation_report.finite(None)
    assert not graduation_report.finite("x")


# ---------------------------------------------------------------------------
# watchdog W6: dead credentials must NOT masquerade as a clean reconciliation
# ---------------------------------------------------------------------------
class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _fake_get_factory(responses):
    calls = iter(responses)

    def fake_get(url, headers=None, timeout=None):
        return next(calls)

    return fake_get


def test_w6_401_reports_warning_not_clean(monkeypatch):
    import requests
    monkeypatch.setenv("APCA_API_KEY_ID", "PKDEAD")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "deadsecret")
    monkeypatch.setattr(requests, "get", _fake_get_factory([
        _FakeResponse(401, {"message": "unauthorized"}),
        _FakeResponse(401, {"message": "unauthorized"}),
    ]))
    findings = watchdog.check_broker_reconciliation(".", None, {"us_stocks"})
    assert len(findings) == 1
    assert findings[0].level == "WARNING"
    assert "401" in findings[0].msg
    # the pre-fix bug: 401 parsed as cash $0.00 / 0 positions -> "Reconciliado"
    assert "Reconciliado" not in findings[0].msg


def test_w6_negative_cash_is_critical_when_active(monkeypatch, tmp_path):
    import requests
    monkeypatch.setenv("APCA_API_KEY_ID", "PKLIVE")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "livesecret")
    monkeypatch.setattr(requests, "get", _fake_get_factory([
        _FakeResponse(200, {"cash": "-62477.40", "equity": "101046.51"}),
        _FakeResponse(200, []),
    ]))
    findings = watchdog.check_broker_reconciliation(str(tmp_path), None, {"us_stocks"})
    neg = [f for f in findings if "NEGATIVO" in f.msg]
    assert neg and neg[0].level == "CRITICAL"


def test_w6_missing_credentials_skips(monkeypatch):
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    findings = watchdog.check_broker_reconciliation(".", None, set())
    assert len(findings) == 1
    assert findings[0].level == "WARNING"
    assert "Sin credenciales" in findings[0].msg
