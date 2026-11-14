"""Reproducibility and accounting safeguards for the research-only validator."""
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import validate_strategies as validation


class ValidationPipelineTests(unittest.TestCase):
    def test_s3_halt_exits_before_broker_access(self):
        import run_live_alpaca_us_stocks as runner
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "HALT_us_stocks.flag").write_text("Unreconciled cash", encoding="utf-8")
            with patch.object(runner, "__file__", str(Path(folder) / "runner.py")), \
                 patch.object(runner, "AlpacaConnector") as broker:
                runner.main()
            broker.assert_not_called()

    def test_committed_price_snapshots_match_manifest(self):
        folder = validation.ROOT / "research/validation/2026-10-05"
        manifest = json.loads((folder / "prices_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["datasets"]), set(validation.UNIVERSES))
        for key, record in manifest["datasets"].items():
            prices = validation.read_frozen(folder, key, record)
            self.assertEqual(len(prices), record["rows"])
            self.assertEqual(str(prices.index[0].date()), record["first"])
            self.assertEqual(str(prices.index[-1].date()), record["last"])

    def test_workflow_saves_ledger_before_propagating_watchdog_failure(self):
        workflow = (validation.ROOT / ".github/workflows/monitor.yml").read_text(encoding="utf-8")
        audit = workflow.index("- name: Run Watchdog Audit")
        commit = workflow.index("- name: Commit and Push Changes")
        failure = workflow.index("- name: Fail cycle on critical watchdog findings")
        self.assertLess(audit, commit)
        self.assertLess(commit, failure)
        self.assertIn("id: watchdog", workflow[audit:commit])
        self.assertIn("continue-on-error: true", workflow[audit:commit])
        self.assertIn("if: steps.watchdog.outcome == 'failure'", workflow[failure:])
        self.assertIn("run: exit 1", workflow[failure:])

    def test_passive_entry_fees_are_funded_and_counted(self):
        prices = pd.DataFrame({"A": 100., "B": 20.}, index=pd.bdate_range("2020-01-01", periods=253))
        nav = validation.passive_basket(prices, 1000., .01)
        np.testing.assert_allclose(nav, 1000. / 1.01)
        result = validation.metrics(nav, 1000.)
        self.assertLess(result["cagr"], 0.)
        self.assertAlmostEqual(result["max_dd"], 1 / 1.01 - 1)

    def test_metrics_zero_return_is_finite(self):
        nav = pd.Series(1000., index=pd.bdate_range("2020-01-01", periods=253))
        result = validation.metrics(nav, 1000.)
        self.assertEqual(result["cagr"], 0.)
        self.assertEqual(result["sharpe_zero_rf"], 0.)
        json.dumps(result, allow_nan=False)

    def test_nonpositive_nav_is_rejected(self):
        with self.assertRaises(ValueError):
            validation.metrics(pd.Series([100., -1.], index=pd.date_range("2020-01-01", periods=2)), 100.)

    def test_frozen_prices_reject_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "s25_prices.csv"
            path.write_text("date,A\n2020-01-01,100\n", encoding="utf-8")
            record = {"file": path.name, "sha256": validation.digest(path.read_bytes())}
            path.write_text("date,A\n2020-01-01,200\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                validation.read_frozen(Path(folder), "s25", record)

    def test_prices_require_exact_universe_and_complete_calendar(self):
        prices = pd.DataFrame({"A": 100.}, index=pd.bdate_range("2020-01-01", periods=253))
        validation.validate_prices(prices, ["A"])
        with self.assertRaises(ValueError):
            validation.validate_prices(prices, ["B"])
        prices.iloc[100, 0] = np.nan
        with self.assertRaises(ValueError):
            validation.validate_prices(prices, ["A"])

    def test_ledger_audit_uses_committed_copies(self):
        spec = types.SimpleNamespace(key="s1", label="Fixture", currency="MXN", portfolio_file="portfolio.json")
        portfolio = json.dumps({"initial_seed_capital": 100., "cash_balance": 90., "holdings": [{"ticker": "A", "shares": 1}]}).encode()
        ledger = b"| Date | Ticker | Action | Shares | Price | Fee |\n| 2020-01-01 | A | BUY | 1 | 10 | 0 |\n"
        def source(*args):
            self.assertEqual(args[0], "show")
            return portfolio if args[1] == "pinned:portfolio.json" else ledger
        with tempfile.TemporaryDirectory() as folder, patch("strategy_registry.STRATEGIES", (spec,)), \
             patch("reconcile_strategy_navs.STRATEGIES", (spec,)), patch.object(validation, "git", side_effect=source):
            output = Path(folder)
            result = validation.ledger_audit(output, "pinned")
            self.assertEqual(result["strategies"][0]["status"], "VERIFIED")
            self.assertEqual(result["source_revision"], "pinned")
            self.assertEqual(result["input_sha256"]["portfolio.json"], validation.digest(portfolio))
            self.assertFalse((output / "portfolio.json").exists())
            self.assertTrue((output / "ledger_audit.json").exists())


if __name__ == "__main__":
    unittest.main()
