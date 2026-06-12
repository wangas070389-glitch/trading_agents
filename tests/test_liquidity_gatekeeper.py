import pytest
from skills.liquidity_gatekeeper import calculate_adtv, passes_liquidity_gate


class TestCalculateAdtv:
    def test_basic_average(self):
        prices = [100.0] * 10
        volumes = [50000.0] * 10
        assert calculate_adtv(prices, volumes) == pytest.approx(5_000_000.0)

    def test_uses_only_last_30_days(self):
        # First 10 days have huge volume that should be ignored
        prices = [100.0] * 10 + [100.0] * 30
        volumes = [1_000_000.0] * 10 + [50_000.0] * 30
        result = calculate_adtv(prices, volumes)
        assert result == pytest.approx(5_000_000.0)

    def test_fewer_than_30_days_uses_all(self):
        prices = [200.0, 200.0]
        volumes = [10_000.0, 20_000.0]
        # (200*10000 + 200*20000) / 2 = 3_000_000
        assert calculate_adtv(prices, volumes) == pytest.approx(3_000_000.0)

    def test_empty_prices_returns_zero(self):
        assert calculate_adtv([], [1000.0]) == 0.0

    def test_empty_volumes_returns_zero(self):
        assert calculate_adtv([100.0], []) == 0.0

    def test_both_empty_returns_zero(self):
        assert calculate_adtv([], []) == 0.0

    def test_mismatched_lengths_uses_shorter(self):
        # prices len=3, volumes len=5 → n=3; slices [-3:] from each
        # volumes[-3:] = [30_000, 40_000, 50_000]
        prices = [100.0, 100.0, 100.0]
        volumes = [10_000.0, 20_000.0, 30_000.0, 40_000.0, 50_000.0]
        expected = (100 * 30_000 + 100 * 40_000 + 100 * 50_000) / 3
        assert calculate_adtv(prices, volumes) == pytest.approx(expected)

    def test_varying_prices(self):
        prices = [50.0, 100.0, 150.0]
        volumes = [20_000.0, 10_000.0, 10_000.0]
        # (50*20k + 100*10k + 150*10k) / 3 = (1_000_000 + 1_000_000 + 1_500_000) / 3
        expected = 3_500_000.0 / 3
        assert calculate_adtv(prices, volumes) == pytest.approx(expected)


class TestPassesLiquidityGate:
    def test_passes_at_default_threshold(self):
        assert passes_liquidity_gate(5_000_000.0) is True

    def test_passes_above_threshold(self):
        assert passes_liquidity_gate(10_000_000.0) is True

    def test_fails_below_threshold(self):
        assert passes_liquidity_gate(4_999_999.99) is False

    def test_fails_at_zero(self):
        assert passes_liquidity_gate(0.0) is False

    def test_custom_threshold_passes(self):
        assert passes_liquidity_gate(3_000_000.0, threshold=2_000_000.0) is True

    def test_custom_threshold_fails(self):
        assert passes_liquidity_gate(1_000_000.0, threshold=2_000_000.0) is False

    def test_exactly_at_threshold(self):
        assert passes_liquidity_gate(5_000_000.0, threshold=5_000_000.0) is True
