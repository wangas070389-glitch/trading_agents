import unittest
import io
from unittest.mock import patch
import pandas as pd
import numpy as np
from connectors.market_data import get_vix3m, get_daily_closes


class TestVIX3MResilience(unittest.TestCase):
    def test_get_vix3m_parses_cboe_fixture(self):
        """Exercise the CBOE parsing path without a live endpoint dependency."""
        dates = pd.bdate_range("2026-01-01", periods=60)
        fixture = pd.DataFrame({"DATE": dates.strftime("%m/%d/%Y"), "CLOSE": np.linspace(15., 25., 60)}).to_csv(index=False).encode()
        with patch("urllib.request.urlopen", return_value=io.BytesIO(fixture)):
            s = get_vix3m(days=50)
        self.assertIsInstance(s, pd.Series)
        self.assertEqual(len(s), 50)
        self.assertTrue((s > 0).all())
        self.assertEqual(s.name, "^VIX3M")

    def test_get_vix3m_synthetic_fallback(self):
        """Verify that when external networks fail, synthetic proxy is generated."""
        dates = pd.bdate_range("2026-01-01", periods=100)
        mock_vix = pd.Series(np.linspace(15.0, 25.0, 100), index=dates, name="^VIX")

        # Mock urllib to fail both CBOE and FRED, and mock yfinance to fail
        with patch("urllib.request.urlopen", side_effect=Exception("Network down")), \
             patch("yfinance.download", side_effect=Exception("Network down")):
            s = get_vix3m(days=50, vix_series=mock_vix)
            self.assertIsInstance(s, pd.Series)
            self.assertEqual(len(s), 50)
            self.assertEqual(s.name, "^VIX3M")
            expected = (mock_vix.rolling(40, min_periods=1).mean() * 1.05).tail(50)
            np.testing.assert_allclose(s.values, expected.values, rtol=1e-5)

    def test_market_data_routes_vix3m(self):
        """Verify that get_daily_closes with ^VIX3M correctly routes to get_vix3m."""
        expected = pd.Series(np.linspace(15., 25., 30), index=pd.bdate_range("2026-01-01", periods=30), name="^VIX3M")
        with patch("connectors.market_data.get_vix3m", return_value=expected) as provider:
            s = get_daily_closes("^VIX3M", days=30)
        provider.assert_called_once_with(30)
        self.assertIsInstance(s, pd.Series)
        self.assertEqual(len(s), 30)
        self.assertTrue((s > 0).all())

    def test_expert_targets_and_returns_alignment_guard(self):
        """Verify that expert_targets_and_returns in Strategy 14 handles aligned inputs safely."""
        from run_live_strategy14 import expert_targets_and_returns, PARAMS

        dates = pd.bdate_range("2025-01-01", periods=150)
        qqq = pd.Series(np.linspace(400, 480, 150), index=dates)
        vix = pd.Series(np.linspace(15, 20, 150), index=dates)
        vix3m = pd.Series(np.linspace(16, 21, 150), index=dates)
        hyg = pd.Series(np.linspace(75, 80, 150), index=dates)
        ief = pd.Series(np.linspace(90, 95, 150), index=dates)
        fx = pd.Series(np.linspace(18, 19, 150), index=dates)

        tgt, r_experts, base, rvol = expert_targets_and_returns(qqq, vix, vix3m, hyg, ief, fx, PARAMS)
        self.assertIn("CASH_MXN", tgt)
        self.assertIn("CARA", tgt)
        self.assertIn("VTTL", tgt)
        self.assertGreater(base, 0.0)
        self.assertGreater(rvol, 0.0)


if __name__ == "__main__":
    unittest.main()
