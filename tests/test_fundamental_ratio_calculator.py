import math
import pytest
from skills.fundamental_ratio_calculator import calculate_fundamental_ratios


def base_kwargs(**overrides):
    defaults = dict(
        current_price=50.0,
        shares_outstanding=1_000_000.0,
        ttm_net_income=5_000_000.0,    # EPS = 5.0 → P/E = 10x
        total_assets=80_000_000.0,
        total_liabilities=30_000_000.0, # book = 50M → BVPS = 50 → P/B = 1x
        total_debt=10_000_000.0,
        cash_and_equivalents=2_000_000.0,
        ttm_ebitda=8_000_000.0,
        annual_dividend_per_share=2.0,  # yield = 4%
    )
    defaults.update(overrides)
    return defaults


class TestPeRatio:
    def test_normal(self):
        r = calculate_fundamental_ratios(**base_kwargs())
        assert r["pe_ratio"] == pytest.approx(10.0)
        assert r["eps_ttm"] == pytest.approx(5.0)

    def test_negative_earnings_gives_inf(self):
        r = calculate_fundamental_ratios(**base_kwargs(ttm_net_income=-1_000_000.0))
        assert r["pe_ratio"] == float("inf")

    def test_zero_shares_gives_none(self):
        r = calculate_fundamental_ratios(**base_kwargs(shares_outstanding=0.0))
        assert r["pe_ratio"] is None
        assert r["eps_ttm"] == 0.0

    def test_zero_net_income_gives_none(self):
        r = calculate_fundamental_ratios(**base_kwargs(ttm_net_income=0.0))
        assert r["pe_ratio"] is None


class TestPbRatio:
    def test_normal(self):
        r = calculate_fundamental_ratios(**base_kwargs())
        assert r["pb_ratio"] == pytest.approx(1.0)
        assert r["bvps"] == pytest.approx(50.0)

    def test_negative_book_value_gives_inf(self):
        # liabilities > assets → negative book
        r = calculate_fundamental_ratios(**base_kwargs(total_assets=10_000_000.0, total_liabilities=30_000_000.0))
        assert r["pb_ratio"] == float("inf")

    def test_zero_shares_gives_none(self):
        r = calculate_fundamental_ratios(**base_kwargs(shares_outstanding=0.0))
        assert r["pb_ratio"] is None

    def test_book_value_computed_correctly(self):
        r = calculate_fundamental_ratios(**base_kwargs(total_assets=100_000_000.0, total_liabilities=40_000_000.0))
        assert r["book_value"] == pytest.approx(60_000_000.0)


class TestEvEbitda:
    def test_normal(self):
        r = calculate_fundamental_ratios(**base_kwargs())
        market_cap = 50.0 * 1_000_000.0   # 50M
        ev = market_cap + 10_000_000.0 - 2_000_000.0  # 58M
        assert r["enterprise_value"] == pytest.approx(ev)
        assert r["ev_ebitda"] == pytest.approx(ev / 8_000_000.0)

    def test_zero_ebitda_gives_none(self):
        r = calculate_fundamental_ratios(**base_kwargs(ttm_ebitda=0.0))
        assert r["ev_ebitda"] is None

    def test_negative_ebitda_gives_none(self):
        r = calculate_fundamental_ratios(**base_kwargs(ttm_ebitda=-1_000_000.0))
        assert r["ev_ebitda"] is None


class TestDividendYield:
    def test_normal(self):
        r = calculate_fundamental_ratios(**base_kwargs())
        assert r["dividend_yield"] == pytest.approx(0.04)

    def test_zero_price_gives_zero(self):
        r = calculate_fundamental_ratios(**base_kwargs(current_price=0.0))
        assert r["dividend_yield"] == 0.0

    def test_no_dividend(self):
        r = calculate_fundamental_ratios(**base_kwargs(annual_dividend_per_share=0.0))
        assert r["dividend_yield"] == 0.0


class TestMarketCap:
    def test_market_cap(self):
        r = calculate_fundamental_ratios(**base_kwargs())
        assert r["market_cap"] == pytest.approx(50_000_000.0)
