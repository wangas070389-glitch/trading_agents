import os
import json
import tempfile
import pytest
import pandas as pd
from skills.file_io_utils import atomic_save_json, safe_load_json
from agents.agents import get_mbono_yield_series, get_us_yield_series, get_mbono_yield_at, get_us_yield_at, _get_cache_dir
from app import start_server

def test_atomic_save_json_and_safe_load(tmp_path):
    target_file = os.path.join(tmp_path, "sub_folder", "test_portfolio.json")
    data = {"total_capital": 50000.0, "holdings": [{"ticker": "AMXB.MX", "shares": 100}]}
    
    # Test atomic write creates file and parent directories
    atomic_save_json(target_file, data)
    assert os.path.exists(target_file)
    
    # Test safe load
    loaded = safe_load_json(target_file)
    assert loaded == data
    assert loaded["total_capital"] == 50000.0
    
    # Test atomic overwrite
    updated_data = {"total_capital": 60000.0, "holdings": []}
    atomic_save_json(target_file, updated_data)
    reloaded = safe_load_json(target_file)
    assert reloaded["total_capital"] == 60000.0
    
    # Test safe load non-existent file returns default
    non_existent = os.path.join(tmp_path, "does_not_exist.json")
    assert safe_load_json(non_existent, default={"default": True}) == {"default": True}

def test_yield_series_caching():
    cache_dir = _get_cache_dir()
    assert os.path.exists(cache_dir)
    
    # Test Mbono yield returns non-empty pandas Series and float yield
    mbono_series = get_mbono_yield_series()
    assert isinstance(mbono_series, pd.Series)
    assert len(mbono_series) > 0
    
    val_mbono = get_mbono_yield_at("2024-01-15")
    assert isinstance(val_mbono, float)
    assert 0.01 <= val_mbono <= 0.25
    
    # Test US yield returns non-empty pandas Series and float yield
    us_series = get_us_yield_series()
    assert isinstance(us_series, pd.Series)
    assert len(us_series) > 0
    
    val_us = get_us_yield_at("2024-01-15")
    assert isinstance(val_us, float)
    assert 0.001 <= val_us <= 0.15

def test_app_server_default_host():
    import inspect
    sig = inspect.signature(start_server)
    assert sig.parameters['host'].default == '127.0.0.1'
