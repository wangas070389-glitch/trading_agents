import pandas as pd
import os

def get_spx_tickers(dir_path=None) -> list:
    """
    Fetches S&P 500 tickers from raw GitHub dataset constituents, falling back to
    Wikipedia page parsing and a hardcoded list on network failures.
    """
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    try:
        df = pd.read_csv(url)
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        if len(tickers) > 400:
            return tickers
    except Exception as e:
        print(f"  [index_constituents] Primary fetch failed: {e}. Trying Wikipedia fallback...")
        
    try:
        wiki_df = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        tickers = wiki_df["Symbol"].str.replace(".", "-", regex=False).tolist()
        if len(tickers) > 400:
            return tickers
    except Exception as e2:
        print(f"  [index_constituents] Wikipedia fallback failed: {e2}")
        
    # Hardcoded fallback list if both fetch methods fail
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK-B", "UNH", "JNJ", 
        "XOM", "JPM", "TSLA", "V", "PG", "MA", "AVGO", "HD", "CVX", "MRK", "ABBV"
    ]
