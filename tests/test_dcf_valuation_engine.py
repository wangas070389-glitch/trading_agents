import pytest
from skills.dcf_valuation_engine import (
    calculate_cost_of_equity,
    calculate_wacc,
    calculate_dcf_intrinsic_value,
)


class TestCostOfEquity:
    def test_capm_no_sovereign(self):
        # Ke = 0.095 + (1.0 * 0.055) + 0.0 = 0.15
        result = calculate_cost_of_equity(0.095, 1.0, 0.055, 0.0)
        assert result == pytest.approx(0.15)

    def test_capm_with_sovereign(self):
        # Ke = 0.095 + (1.2 * 0.055) + 0.02 = 0.181
        result = calculate_cost_of_equity(0.095, 1.2, 0.055, 0.02)
        assert result == pytest.approx(0.181)

    def test_zero_beta(self):
        result = calculate_cost_of_equity(0.09, 0.0, 0.055, 0.0)
        assert result == pytest.approx(0.09)

    def test_high_beta(self):
        result = calculate_cost_of_equity(0.0, 2.0, 0.10, 0.0)
        assert result == pytest.approx(0.20)


class TestWacc:
    def test_all_equity(self):
        # No debt → WACC = cost_of_equity
        result = calculate_wacc(0.15, 0.08, total_debt=0.0, market_cap=1_000_000.0, tax_rate=0.30)
        assert result == pytest.approx(0.15)

    def test_zero_capital_falls_back_to_equity(self):
        result = calculate_wacc(0.15, 0.08, total_debt=0.0, market_cap=0.0, tax_rate=0.30)
        assert result == pytest.approx(0.15)

    def test_blended_wacc(self):
        # 50% equity, 50% debt, tax=30%
        # WACC = 0.5*0.15 + 0.5*0.08*(1-0.30) = 0.075 + 0.028 = 0.103
        result = calculate_wacc(0.15, 0.08, total_debt=1_000_000.0, market_cap=1_000_000.0, tax_rate=0.30)
        assert result == pytest.approx(0.103)

    def test_high_leverage(self):
        # 80% debt, 20% equity
        # WACC = 0.2*0.15 + 0.8*0.08*0.7 = 0.03 + 0.0448 = 0.0748
        result = calculate_wacc(0.15, 0.08, total_debt=4_000_000.0, market_cap=1_000_000.0, tax_rate=0.30)
        assert result == pytest.approx(0.0748)


class TestDcfIntrinsicValue:
    def _base_kwargs(self, **overrides):
        defaults = dict(
            current_price=50.0,
            shares_outstanding=1_000_000.0,
            base_fcff=5_000_000.0,
            wacc=0.12,
            total_debt=10_000_000.0,
            cash_and_equivalents=2_000_000.0,
            growth_rate_stage1=0.06,
            terminal_growth=0.03,
            stage1_years=5,
            stage2_years=5,
        )
        defaults.update(overrides)
        return defaults

    def test_returns_expected_keys(self):
        r = calculate_dcf_intrinsic_value(**self._base_kwargs())
        for key in ("intrinsic_value", "margin_of_safety", "enterprise_value",
                    "equity_value", "terminal_value", "fcff_projections", "wacc", "base_fcff"):
            assert key in r

    def test_projections_length(self):
        r = calculate_dcf_intrinsic_value(**self._base_kwargs())
        assert len(r["fcff_projections"]) == 10  # stage1_years + stage2_years

    def test_margin_of_safety_formula(self):
        r = calculate_dcf_intrinsic_value(**self._base_kwargs())
        iv = r["intrinsic_value"]
        price = self._base_kwargs()["current_price"]
        expected_mos = (iv - price) / price
        assert r["margin_of_safety"] == pytest.approx(expected_mos)

    def test_zero_shares_gives_zero_intrinsic_value(self):
        r = calculate_dcf_intrinsic_value(**self._base_kwargs(shares_outstanding=0.0))
        assert r["intrinsic_value"] == 0.0

    def test_zero_current_price_gives_zero_margin(self):
        r = calculate_dcf_intrinsic_value(**self._base_kwargs(current_price=0.0))
        assert r["margin_of_safety"] == 0.0

    def test_negative_equity_value_floors_intrinsic_at_zero(self):
        # Very high debt crushes equity value
        r = calculate_dcf_intrinsic_value(**self._base_kwargs(total_debt=10_000_000_000.0))
        assert r["intrinsic_value"] == 0.0

    def test_wacc_near_terminal_growth_uses_floor(self):
        # When wacc ≈ terminal_growth the denominator would be tiny; floor kicks in
        r = calculate_dcf_intrinsic_value(**self._base_kwargs(wacc=0.031, terminal_growth=0.03))
        assert r["terminal_value"] > 0

    def test_high_growth_produces_higher_value_than_low_growth(self):
        high = calculate_dcf_intrinsic_value(**self._base_kwargs(growth_rate_stage1=0.15))
        low = calculate_dcf_intrinsic_value(**self._base_kwargs(growth_rate_stage1=0.02))
        assert high["intrinsic_value"] > low["intrinsic_value"]

    def test_single_stage(self):
        r = calculate_dcf_intrinsic_value(**self._base_kwargs(stage1_years=5, stage2_years=0))
        assert len(r["fcff_projections"]) == 5

    def test_enterprise_value_positive(self):
        r = calculate_dcf_intrinsic_value(**self._base_kwargs())
        assert r["enterprise_value"] > 0
