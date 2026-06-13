import sys
import os
import pandas as pd
import yfinance as yf

# Ensure path includes root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.index_constituents import get_spx_tickers
from skills.prefilter import prefilter_us_universe, MAX_DEEP_CANDIDATES, MAX_PRICE_FRACTION

def test_funnel():
    print("====================================================")
    print("RUNNING S&P 500 PRE-FILTER FUNNEL TESTS")
    print("====================================================")
    
    # 1. Fetch SPX constituents
    print("Fetching tickers...")
    tickers = get_spx_tickers()
    print(f"Total tickers fetched: {len(tickers)}")
    assert len(tickers) >= 10, "Error: Tickers count is too small"
    
    # Take a sample of 50 tickers to keep yfinance download quick in unit test
    sample_tickers = tickers[:50]
    
    # 2. Download sample batch
    print(f"Downloading 6-month batch for {len(sample_tickers)} tickers...")
    batch = yf.download(sample_tickers, period="6mo", progress=False, group_by="column")
    assert not batch.empty, "Error: yfinance download returned empty DataFrame"
    
    # 3. Setup parameters
    usdmxn_rate = 17.50
    portfolio_value = 25000.0  # MXN
    max_price_mxn = portfolio_value * MAX_PRICE_FRACTION
    
    print(f"Estimated Portfolio: {portfolio_value:.2f} MXN")
    print(f"Max Allowed share price: {max_price_mxn:.2f} MXN (approx. ${max_price_mxn/usdmxn_rate:.2f} USD)")
    
    # 4. Run pre-filter
    candidates = prefilter_us_universe(
        batch_close=batch["Close"],
        batch_volume=batch["Volume"],
        usdmxn_rate=usdmxn_rate,
        portfolio_value_mxn=portfolio_value,
        max_candidates=15
    )
    
    # 5. Asserts
    print(f"\nFiltered candidates: {list(candidates.keys())}")
    print(f"Number of candidates: {len(candidates)}")
    
    assert len(candidates) <= 15, f"Error: candidates count {len(candidates)} exceeded max limit 15"
    
    for ticker, info in candidates.items():
        price_mxn = info["price_mxn"]
        print(f"  {ticker}: Price = {price_mxn:.2f} MXN | ADTV = {info['adtv_mxn']:,.0f} MXN | Momentum = {info['momentum_score']:.4f}")
        assert price_mxn <= max_price_mxn, f"Error: {ticker} price {price_mxn:.2f} MXN exceeds max allowed {max_price_mxn:.2f} MXN"
        
    print("\nALL PRE-FILTER FUNNEL TESTS PASSED SUCCESSFULLY!")
    print("====================================================")

if __name__ == "__main__":
    test_funnel()
