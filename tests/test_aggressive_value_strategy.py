import pytest
import numpy as np
from agents.agents import PortfolioReconciler

def test_reconcile_with_custom_concentration_cap_and_max_positions():
    reconciler = PortfolioReconciler()
    
    # 4 strong tickers with identical DCS to bypass 30th percentile screen gate filtering
    adjusted_metrics = {
        "TICKER1": {
            "dcs_adjusted": 0.9,
            "garch_vol_adjusted": 0.10,
            "relative_vol": 2.0,
            "hmm_state": 1,
            "current_price": 100.0,
            "spy_hmm_state": 1,  # Bull regime allows high exposure
            "zg_t": 0.0,
            "wacc_adjustment": 0.0,
            "growth_adjustment": 0.0,
            "macro_description": "Test ticker 1"
        },
        "TICKER2": {
            "dcs_adjusted": 0.9,
            "garch_vol_adjusted": 0.10,
            "relative_vol": 2.0,
            "hmm_state": 1,
            "current_price": 100.0,
            "spy_hmm_state": 1,
            "zg_t": 0.0,
            "wacc_adjustment": 0.0,
            "growth_adjustment": 0.0,
            "macro_description": "Test ticker 2"
        },
        "TICKER3": {
            "dcs_adjusted": 0.9,
            "garch_vol_adjusted": 0.10,
            "relative_vol": 2.0,
            "hmm_state": 1,
            "current_price": 100.0,
            "spy_hmm_state": 1,
            "zg_t": 0.0,
            "wacc_adjustment": 0.0,
            "growth_adjustment": 0.0,
            "macro_description": "Test ticker 3"
        },
        "TICKER4": {
            "dcs_adjusted": 0.9,
            "garch_vol_adjusted": 0.10,
            "relative_vol": 2.0,
            "hmm_state": 1,
            "current_price": 100.0,
            "spy_hmm_state": 1,
            "zg_t": 0.0,
            "wacc_adjustment": 0.0,
            "growth_adjustment": 0.0,
            "macro_description": "Test ticker 4"
        }
    }
    
    portfolio = {
        "total_capital": 20000.0,
        "cash_balance": 20000.0,
        "holdings": []
    }
    
    # Test 1: Standard settings (default concentration cap 20%, max positions 6)
    learning_context_standard = {
        "dcs_threshold": 0.15,
        "vr_threshold": 1.2,
        "max_positions": 6,
        "concentration_cap": 0.20,
        "dead_zone_threshold": 0.05
    }
    
    updated_port_std, _, trades_std = reconciler.reconcile(
        adjusted_metrics, portfolio.copy(), "2026-06-19",
        learning_context=learning_context_standard
    )
    
    # All 4 tickers should be bought, none should exceed 20% target weight
    assert len(updated_port_std["holdings"]) == 4
    for h in updated_port_std["holdings"]:
        assert h["target_weight"] <= 0.2001
        
    # Test 2: Aggressive settings (concentration cap 40%, max positions 2)
    learning_context_aggressive = {
        "dcs_threshold": 0.15,
        "vr_threshold": 1.2,
        "max_positions": 2,
        "concentration_cap": 0.40,
        "dead_zone_threshold": 0.05
    }
    
    updated_port_agg, _, trades_agg = reconciler.reconcile(
        adjusted_metrics, portfolio.copy(), "2026-06-19",
        learning_context=learning_context_aggressive
    )
    
    # Only 2 tickers should be bought (max positions limit)
    assert len(updated_port_agg["holdings"]) == 2
    held_tickers = [h["ticker"] for h in updated_port_agg["holdings"]]
    
    # Cap should allow target weights up to 40%
    for h in updated_port_agg["holdings"]:
        assert h["target_weight"] <= 0.4001
        assert h["target_weight"] > 0.2001  # Because inv-vol weights scale with dcs and cap is 40%

def test_reconcile_dead_zone_threshold():
    reconciler = PortfolioReconciler()
    
    # 1 ticker, we already hold a position at 18% weight, target weight is computed near 20%
    adjusted_metrics = {
        "TICKER1": {
            "dcs_adjusted": 0.9,
            "garch_vol_adjusted": 0.10,
            "relative_vol": 2.0,
            "hmm_state": 1,
            "current_price": 100.0,
            "spy_hmm_state": 1,
            "zg_t": 0.0,
            "wacc_adjustment": 0.0,
            "growth_adjustment": 0.0,
            "macro_description": "Test ticker 1"
        }
    }
    
    # Portfolio already holds TICKER1 at 18% weight (36 shares at 100.0 price, out of 20000.0 total capital)
    portfolio = {
        "total_capital": 20000.0,
        "cash_balance": 16400.0,
        "holdings": [{
            "ticker": "TICKER1",
            "shares": 36,
            "buy_price": 100.0,
            "last_price": 100.0,
            "target_weight": 0.18
        }]
    }
    
    # Case A: Dead zone threshold is 5% (0.05). Since target is ~20% (or less, scaled by exposure),
    # let's assume we request target_weight = 0.20. The difference is 0.02.
    # 0.02 < 0.05, so the dead-zone should prevent trading.
    learning_context_std = {
        "dcs_threshold": 0.15,
        "vr_threshold": 1.2,
        "max_positions": 6,
        "concentration_cap": 0.20,
        "dead_zone_threshold": 0.05
    }
    
    updated_port_std, _, trades_std = reconciler.reconcile(
        adjusted_metrics, portfolio.copy(), "2026-06-19",
        learning_context=learning_context_std
    )
    
    # With dead-zone active, we should NOT see any trades, shares should remain at 36
    assert len(trades_std) == 0
    assert updated_port_std["holdings"][0]["shares"] == 36
    
    # Case B: Dead zone threshold is 1% (0.01). Target weight is 20% (0.20).
    # Difference is 0.02. 0.02 > 0.01, so dead-zone should NOT prevent trading.
    learning_context_tight = {
        "dcs_threshold": 0.15,
        "vr_threshold": 1.2,
        "max_positions": 6,
        "concentration_cap": 0.20,
        "dead_zone_threshold": 0.01
    }
    
    # Make sure TICKER1 dcs forces target weight to max cap 20%
    updated_port_tight, _, trades_tight = reconciler.reconcile(
        adjusted_metrics, portfolio.copy(), "2026-06-19",
        learning_context=learning_context_tight
    )
    
    # With a tight dead-zone, a trade should execute (buying to reach 20% target weight, which is 40 shares)
    assert len(trades_tight) > 0
    assert updated_port_tight["holdings"][0]["shares"] == 40
