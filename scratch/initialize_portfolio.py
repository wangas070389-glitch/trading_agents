import os
import json
import datetime
import yfinance as yf

BMV_TICKERS = [
    "AMXB.MX", "FEMSAUBD.MX", "WALMEX.MX", "GFNORTEO.MX", "GMEXICOB.MX",
    "CEMEXCPO.MX", "BIMBOA.MX", "GAPB.MX", "ASURB.MX", "OMAB.MX",
    "GRUMAB.MX", "ALFAA.MX", "KIMBERA.MX", "AC.MX", "ORBIA.MX",
    "PE&OLES.MX", "PINFRA.MX", "BBAJIOO.MX", "GENTERA.MX", "CUERVO.MX",
    "GCC.MX", "VESTA.MX"
]
US_TICKERS = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL"]

def main():
    print("Initializing portfolio.json to equal-weight benchmark...")
    tickers = BMV_TICKERS + US_TICKERS
    n_assets = len(tickers)
    
    total_capital = 20000.0
    cash_per_asset = total_capital / n_assets
    
    # Get current USD/MXN rate
    try:
        usdmxn = yf.Ticker("MXN=X").history(period="1d")["Close"].iloc[-1]
    except Exception:
        usdmxn = 18.0
        print(f"Fallback USD/MXN to {usdmxn}")
        
    holdings = []
    
    for ticker in tickers:
        print(f"Fetching price for {ticker}...")
        try:
            hist = yf.Ticker(ticker).history(period="1d")
            price = hist["Close"].iloc[-1]
            if ticker in US_TICKERS:
                price = price * usdmxn
            
            shares = int(cash_per_asset // price)
            if shares > 0:
                holdings.append({
                    "ticker": ticker,
                    "shares": shares,
                    "buy_price": round(price, 2),
                    "last_price": round(price, 2),
                    "target_weight": round(1.0 / n_assets, 4)
                })
        except Exception as e:
            print(f"Failed to fetch {ticker}: {e}")
            
    # Calculate cash balance
    invested = sum(h["shares"] * h["last_price"] for h in holdings)
    cash_balance = total_capital - invested
    
    portfolio = {
        "total_capital": total_capital,
        "cash_balance": round(cash_balance, 2),
        "holdings": holdings,
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open("portfolio.json", "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)
        
    print(f"portfolio.json initialized with {len(holdings)} holdings. Invested: {invested:.2f} MXN, Cash: {cash_balance:.2f} MXN")

if __name__ == "__main__":
    main()
