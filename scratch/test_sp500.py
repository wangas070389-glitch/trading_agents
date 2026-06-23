import pandas as pd
import requests

def test_fetch():
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    try:
        df = pd.read_csv(url)
        print(f"Successfully fetched {len(df)} tickers from {url}")
        print("First 5 tickers:")
        print(df.head())
        # Let's clean the tickers (replace '.' with '-' as yfinance expects)
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        print(f"Cleaned tickers count: {len(tickers)}")
    except Exception as e:
        print(f"Error fetching from datasets repo: {e}")
        # Fallback source (Wikipedia list raw json or similar, or try wikipedia read_html)
        try:
            wiki_df = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
            print(f"Successfully fetched {len(wiki_df)} tickers from Wikipedia")
            print(wiki_df.head())
        except Exception as wiki_err:
            print(f"Wikipedia fetch failed: {wiki_err}")

if __name__ == "__main__":
    test_fetch()
