"""Offline regression checks; no broker, network, or production-artifact writes.

Run with unittest when optional research/pytest dependencies are unavailable:
    python -B -m unittest tests.test_strategy_repair_regressions -v
"""
import ast
import contextlib
import io
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import backtest_dividends as dividends
import backtest_strategy24 as s24
import backtest_strategy25 as s25
import backtest_strategy30 as s30
import generate_clean_report as reporting
import graduation_report as graduation
import watchdog
from backtest_review import backtest_block
from skills.backtest_accounting import flow_adjusted_return
from skills import golden_macd_backtest as golden
from skills.macd_trailing_strategy import MACDTrailingStopStrategy

ROOT = Path(__file__).resolve().parents[1]


class PerformanceAccountingTests(unittest.TestCase):
    def test_deposit_is_not_profit(self):
        self.assertEqual(flow_adjusted_return(100, 150, 50), 0)
        self.assertEqual(flow_adjusted_return(100, 150, 50, timing="end"), 0)

    def test_flow_timing_and_investment_income(self):
        self.assertAlmostEqual(flow_adjusted_return(100, 165, 50), .1)
        self.assertAlmostEqual(flow_adjusted_return(100, 160, 50, timing="end"), .1)
        self.assertAlmostEqual(flow_adjusted_return(100, 102), .02)
        self.assertEqual(flow_adjusted_return(100, 80, -20), 0)

    def test_invalid_accounting_input_rejected(self):
        for args in ((0, 100, 0), (100, float("nan"), 0), (100, -1, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                flow_adjusted_return(*args)

    def test_macd_twr_includes_fees_without_flows(self):
        class FixedEntry(MACDTrailingStopStrategy):
            def compute_indicators(self, prices):
                return {"macd_line": np.r_[0., 0., np.ones(len(prices) - 2)],
                        "signal_line": np.zeros(len(prices)), "long_term_ma": np.full(len(prices), 99.)}

        prices = pd.DataFrame({"TEST": 100.}, index=pd.bdate_range("2026-01-05", periods=8))
        result = FixedEntry(long_term_ma_length=2, position_pct=.5, commission_pct=.01).run_portfolio_backtest(
            prices, initial_capital=100000, monthly_contribution=0)
        self.assertEqual(len(result["trade_log"]), 1)
        self.assertEqual(result["trade_log"][0]["fee"], 500)
        expected = result["nav_series"].iloc[-1] / 100000
        self.assertAlmostEqual(result["twr_series"].iloc[-1], expected)
        self.assertLess(result["metrics"]["strategy_total_return"], 0)

    def test_macd_twr_excludes_monthly_deposit(self):
        prices = pd.DataFrame({"TEST": 100.}, index=pd.bdate_range("2026-01-29", periods=8))
        algo = MACDTrailingStopStrategy(long_term_ma_length=2)
        result = algo.run_portfolio_backtest(prices, initial_capital=1000, monthly_contribution=500)
        self.assertGreater(result["nav_series"].iloc[-1], 2000)
        self.assertLess(result["twr_series"].iloc[-1], 1.01)

    def test_s1_metric_includes_initial_fee_and_drawdown(self):
        # Load the pure calculation only; importing the full runner would load
        # unrelated optional ML/news dependencies.
        tree = ast.parse((ROOT / "backtest_alpha_growth.py").read_text(encoding="utf-8"))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_metrics")
        namespace = {"pd": pd, "np": np}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "backtest_alpha_growth.py", "exec"), namespace)
        result = namespace["compute_metrics"](pd.Series([.99, .99], index=pd.date_range("2020-01-01", periods=2)), "test", initial_value=1.)
        self.assertAlmostEqual(result["total_return"], -.01)
        self.assertAlmostEqual(result["max_drawdown"], -.01)


class DividendTests(unittest.TestCase):
    def test_api_uses_twr_and_does_not_invent_winning_trades(self):
        nav = pd.DataFrame({"nav": [1100., 1200., 1300.], "twr": [1., 1., 1.],
                            "external_flow": [100., 100., 100.]},
                           index=pd.to_datetime(["2026-01-30", "2026-02-02", "2026-03-02"]))
        result = dict(df_nav=nav, trades_log=[], cagr=0., sharpe=0., max_dd=0.)
        with patch.object(dividends, "run_dividend_backtest", return_value=result), \
             patch.multiple(dividends, INITIAL_CAPITAL=1000., CASH_APR=0.):
            response = dividends.run_dividends_backtest_for_api()
        self.assertEqual(response["metrics"]["strategy_return"], 0.)
        self.assertEqual(response["metrics"]["total_pnl"], 0.)
        self.assertEqual(response["metrics"]["benchmark_return"], 0.)
        self.assertEqual(response["benchmark"], [1100., 1200., 1300.])
        self.assertIsNone(response["metrics"]["win_rate"])

    def test_deposit_only_backtest_has_zero_return(self):
        dates = pd.to_datetime(["2026-01-30", "2026-02-02", "2026-03-02"])
        prices = {"TEST.MX": pd.DataFrame({"Close": 100., "Volume": 1000.}, index=dates)}
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()), \
             patch.object(dividends, "__file__", str(Path(folder) / "runner.py")), \
             patch.object(dividends, "download_backtest_data", return_value=(prices, {}, pd.Series(dtype=float))), \
             patch.object(dividends, "get_static_fundamentals", return_value={}), \
             patch.multiple(dividends, ALL_TICKERS=["TEST.MX"], MIN_HISTORY_DAYS=0, INITIAL_CAPITAL=1000., MONTHLY_CONTRIBUTION=100., CASH_APR=0.):
            result = dividends.run_dividend_backtest()
            self.assertEqual(result["final_nav"], 1300.)
            self.assertAlmostEqual(result["cagr"], 0)
            self.assertAlmostEqual(result["max_dd"], 0)
            saved = pd.read_csv(Path(folder) / "dividends_backtest_nav.csv")
            self.assertEqual(saved.external_flow.sum(), 300.)
            self.assertTrue((saved.daily_ret == 0).all())

    def test_explicit_dividends_use_unadjusted_prices(self):
        calls = []
        dates = pd.date_range("2026-01-01", periods=3)

        class Ticker:
            def __init__(self, symbol):
                self.symbol = symbol
                self.dividends = pd.Series([1.], index=dates[:1], name="Dividends")

            def history(self, **kwargs):
                calls.append((self.symbol, kwargs))
                return pd.DataFrame({"Close": 100., "Volume": 1000.}, index=dates)

        with patch.dict("sys.modules", {"yfinance": types.SimpleNamespace(Ticker=Ticker)}), \
             patch.multiple(dividends, ALL_TICKERS=["TEST.MX"], MIN_HISTORY_DAYS=0), \
             contextlib.redirect_stdout(io.StringIO()):
            prices, _, _ = dividends.download_backtest_data()
        self.assertIn("TEST.MX", prices)
        self.assertIs(next(kwargs for name, kwargs in calls if name == "TEST.MX")["auto_adjust"], False)

    def test_missing_fundamentals_do_not_invent_qualified_assets(self):
        fake = types.SimpleNamespace(Ticker=lambda _: types.SimpleNamespace(info={}))
        with patch.dict("sys.modules", {"yfinance": fake}), patch.object(dividends, "ALL_TICKERS", ["TEST.MX"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(dividends.get_static_fundamentals(), {})


class GoldenMacdTests(unittest.TestCase):
    @staticmethod
    def signals(close):
        result = pd.DataFrame({"trend": 0., "bull": False, "bear": False}, index=close.index)
        result.iloc[1, result.columns.get_loc("bull")] = True
        return result

    def simulate(self, values, fee=0):
        close = pd.Series(values, index=pd.bdate_range("2026-01-01", periods=len(values)))
        with patch.object(golden, "indicators", side_effect=self.signals):
            return golden.simulate(close, 1000, 0, fee)

    def test_trailing_stop_arms_then_exits(self):
        nav = self.simulate([100, 100, 100, 116, 112, 110, 70])
        self.assertAlmostEqual(nav[-2], 1100)
        self.assertAlmostEqual(nav[-1], 1100)

    def test_stop_uses_fill_price_not_decision_price(self):
        nav = self.simulate([100, 100, 150, 155, 150, 145, 140])
        self.assertAlmostEqual(nav[2], 1000)  # Cannot earn the jump before the fill.
        self.assertAlmostEqual(nav[-1], 1000 * 140 / 150)

    def test_fees_are_funded_on_entry_and_exit(self):
        nav = self.simulate([100, 100, 100, 116, 112, 110, 70], fee=.01)
        self.assertAlmostEqual(nav[2], 1000 / 1.01)
        self.assertAlmostEqual(nav[-1], 1000 / 1.01 * 1.10 * .99)

    def test_bmv_curve_has_no_spurious_fx_exposure(self):
        close = pd.Series(100 + np.sin(np.arange(120) / 6) * 10 + np.arange(120), index=pd.bdate_range("2026-01-01", periods=120))
        original = pd.DataFrame({"close": close, "fx": 20.})
        changed = original.copy()
        changed["fx"] = np.linspace(1, 100, len(changed))
        np.testing.assert_allclose(s25.run_single_asset_simulation(original, "TEST.MX"), s25.run_single_asset_simulation(changed, "TEST.MX"))
        np.testing.assert_allclose(s25.run_single_asset_simulation(original.drop(columns="fx"), "TEST.MX"), s25.run_single_asset_simulation(original, "TEST.MX"))

    def test_s25_rejects_wrong_currency_universe(self):
        with self.assertRaises(ValueError):
            s25.run_single_asset_simulation(pd.DataFrame({"close": [100, 101]}), "AAPL")

    def test_s30_uses_shared_execution_logic(self):
        close = pd.Series([100, 100, 100, 116, 112, 110, 70])
        with patch.object(golden, "indicators", side_effect=self.signals):
            expected = golden.simulate(close, 20000, s30.RF_USD, s30.TRANSACTION_COST)
            np.testing.assert_allclose(s30.run_single_asset_simulation(pd.DataFrame({"close": close}), "TEST"), expected)

    def test_future_prices_do_not_change_past_nav(self):
        close = pd.Series(100 + np.arange(100) + 5 * np.sin(np.arange(100)))
        first = golden.simulate(close, 1000, .04, .003)
        changed = close.copy()
        changed.iloc[60:] *= 2
        second = golden.simulate(changed, 1000, .04, .003)
        np.testing.assert_allclose(first[:60], second[:60])

    def test_bad_prices_rejected(self):
        for values in ([100], [100, np.nan], [100, -1]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                golden.simulate(pd.Series(values), 1000, 0, .003)

    def test_live_purchase_checks_include_fees(self):
        for filename in ("run_live_strategy25.py", "run_live_strategy30.py"):
            tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
            comparison = next(n.test for n in ast.walk(tree) if isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Name) and n.test.left.id == "cash")
            expression = compile(ast.Expression(comparison), filename, "eval")
            self.assertFalse(eval(expression, {"cash": 100., "target_alloc": 100., "TRANSACTION_COST": .01}))
            self.assertTrue(eval(expression, {"cash": 101., "target_alloc": 100., "TRANSACTION_COST": .01}))


class HoldoutTests(unittest.TestCase):
    def test_holdout_changes_cannot_change_selected_parameters(self):
        data = pd.DataFrame({"qqq": np.arange(800) + 100.}, index=pd.date_range("2026-01-01", periods=800, freq="30min"))
        calls = []

        def simulation(prefix, **kwargs):
            calls.append(prefix.copy())
            score = kwargs["max_depth"] + kwargs["thresh"]
            return pd.DataFrame({"nav": score, "benchmark": 1.}, index=prefix.index), 0, 0

        with patch.object(s24, "run_simulation", side_effect=simulation), \
             patch.object(s24, "calculate_metrics", side_effect=lambda nav, _: {"sharpe": nav.iloc[-1]}):
            first = s24.select_parameters(data)
            changed = data.copy()
            changed.iloc[600:] *= 10
            second = s24.select_parameters(changed)
        self.assertEqual(first, second)
        self.assertEqual(first[1], 600)
        self.assertEqual(len(calls), 12)
        for prefix in calls:
            pd.testing.assert_frame_equal(prefix, data.iloc[:600])

    def test_short_data_cannot_claim_holdout(self):
        with self.assertRaises(ValueError):
            s24.select_parameters(pd.DataFrame({"qqq": np.arange(500)}))

    def test_failed_parameter_search_is_not_silently_accepted(self):
        with patch.object(s24, "run_simulation", side_effect=RuntimeError("bad inputs")), self.assertRaises(RuntimeError):
            s24.select_parameters(pd.DataFrame({"qqq": np.arange(800)}))


class WatchdogAndReportingTests(unittest.TestCase):
    def test_invalidated_backtest_blocks_otherwise_passing_graduation(self):
        strategy = next(s.copy() for s in graduation.STRATS if s["label"].startswith("S29 "))
        strategy["inception"] = str(graduation.datetime.date.today() - graduation.datetime.timedelta(days=365))
        strategy["note"] = ""
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()), \
             patch.multiple(graduation, DIR=folder, OUT=str(Path(folder) / "report.md"), STRATS=[strategy], BY_PORTFOLIO_FILE={}), \
             patch.object(graduation, "load_json", return_value={}), \
             patch.object(graduation, "portfolio_nav", return_value=400000.), \
             patch.object(graduation, "deposits_from_ledger", return_value=0.), \
             patch.object(graduation, "daily_series", return_value=([1., 2.], "fixture")), \
             patch.object(graduation, "series_stats", return_value=(1., -.01)), \
             patch.object(graduation, "history_verified", return_value=True), \
             patch.object(graduation, "portfolio_freshness_block", return_value=None), \
             patch.object(graduation, "backtest_max_dd", return_value=-.20):
            graduation.main()
            report = (Path(folder) / "report.md").read_text(encoding="utf-8")
        self.assertIn("**BLOCKED**", report)
        self.assertIn("Backtest evidence invalidated", report)
        self.assertNotIn("**READY**", report)
        self.assertNotIn("25.18", report)

    def test_registry_import_does_not_mark_everything_inactive(self):
        active = watchdog.get_active_strategies(str(ROOT))
        self.assertIn("us_stocks", active)
        self.assertIn("strategy25", active)
        self.assertIn("core", active)

    def test_inactive_registry_entry_is_respected(self):
        spec = types.SimpleNamespace(portfolio_file="portfolio_test.json", active=False)
        with patch.object(watchdog, "BY_RUNNER", {"test.py": spec}):
            self.assertEqual(watchdog.get_active_strategies("unused"), set())

    def run_watchdog(self, dry_run):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()), \
             patch.object(watchdog, "__file__", str(Path(folder) / "watchdog.py")), \
             patch("sys.argv", ["watchdog.py"] + (["--dry-run"] if dry_run else [])), \
             patch.object(watchdog.glob, "glob", return_value=["portfolio_strategy25.json"]), \
             patch.object(watchdog, "check_strategy", return_value=([watchdog.Finding("CRITICAL", "strategy25", "W4", "negative cash")], {})), \
             patch.object(watchdog, "check_broker_reconciliation", return_value=[]), \
             patch.object(watchdog, "atomic_save_json") as save:
            code = watchdog.main()
            if dry_run:
                save.assert_not_called()
                self.assertFalse((Path(folder) / "watchdog_report.md").exists())
            else:
                save.assert_called_once()
                self.assertIn("CRITICAL: 1", (Path(folder) / "watchdog_report.md").read_text(encoding="utf-8"))
            return code

    def test_critical_watchdog_returns_failure(self):
        self.assertEqual(self.run_watchdog(False), 1)

    def test_dry_run_does_not_write_or_fail(self):
        self.assertEqual(self.run_watchdog(True), 0)

    def test_invalidated_metrics_cannot_be_ranked_or_projected(self):
        text = reporting.build_kpi_report("2026-10-05")
        ranked, quarantined = text.split("## Invalidated")
        self.assertNotIn("S29:", ranked)
        self.assertIn("S29:", quarantined)
        self.assertNotIn("253.45", text)
        self.assertNotIn("Year 5 (MXN)", text)
        self.assertIsNotNone(backtest_block("S29 Golden Stat-Arb"))
        self.assertIsNotNone(backtest_block("S8: Dividend Quality"))
        self.assertIsNone(backtest_block("S12 VTTL"))


if __name__ == "__main__":
    unittest.main()
