import os
import sys
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# BMV FIBRAs Universe
FIBRA_TICKERS = [
    "FUNO11.MX",      # Fibra Uno
    "FIBRAMQ12.MX",   # Fibra Macquarie
    "FIBRAPL14.MX",   # Fibra Prologis
    "TERRA13.MX",     # Fibra Terrafina
    "FMTY14.MX",      # Fibra Monterrey
    "DANHOS13.MX",    # Fibra Danhos
    "FIDE12.MX",      # Fibra Educativa
    "FIHO12.MX",      # Fibra Hotel
    "FINN13.MX",      # Fibra Inn
    "FSHOP13.MX"      # Fibra Shop
]

def get_fibra_metrics(ticker_symbol: str, history_df: pd.DataFrame = None) -> dict:
    """
    Downloads and extracts all dividend, safety, and trend metrics for a FIBRA ticker.
    Returns a dictionary of metrics, or None if downloading failed.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # 1. Fetch historical pricing if not provided
        if history_df is None or history_df.empty:
            history_df = ticker.history(period="1y")
            
        if history_df.empty or len(history_df) < 200:
            return None
            
        current_price = float(history_df["Close"].squeeze().iloc[-1]) if hasattr(history_df["Close"], "iloc") else float(history_df["Close"].squeeze())
        
        # Calculate SMA 200
        closes = history_df["Close"].squeeze().values
        sma200 = float(closes[-200:].mean())
        
        # 2. Retrieve info
        info = ticker.info
        
        # 3. Dividend Yield
        dividend_yield = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
        if dividend_yield is not None and dividend_yield > 1.0:
            dividend_yield = dividend_yield / 100.0
            
        if dividend_yield is None:
            # Fallback: sum up historical dividends paid in the last 365 days
            historical_divs = ticker.dividends
            if not historical_divs.empty:
                one_year_ago = datetime.datetime.now() - datetime.timedelta(days=365)
                if historical_divs.index.tz is not None:
                    historical_divs.index = historical_divs.index.tz_convert("UTC").tz_localize(None)
                recent_divs = historical_divs[historical_divs.index >= one_year_ago]
                annual_dividend = float(recent_divs.sum())
                dividend_yield = annual_dividend / current_price if current_price > 0 else 0.0
            else:
                dividend_yield = 0.0
                
        # 4. Leverage (Debt to Equity)
        debt_to_equity = info.get("debtToEquity")
        if debt_to_equity is not None and debt_to_equity > 5.0:
            debt_to_equity = debt_to_equity / 100.0
            
        payout_ratio = info.get("payoutRatio") or 0.0
        
        # Fill defaults
        debt_to_equity = debt_to_equity if debt_to_equity is not None else 0.0
        
        return {
            "ticker": ticker_symbol,
            "current_price": current_price,
            "sma200": sma200,
            "dividend_yield": dividend_yield,
            "payout_ratio": payout_ratio,
            "debt_to_equity": debt_to_equity,
            "dividend_score": dividend_yield * (1.0 / (1.0 + debt_to_equity)) # rank higher yield with lower debt
        }
    except Exception as e:
        print(f"  [WARN] Failed to retrieve metrics for {ticker_symbol}: {e}")
        return None

def evaluate_and_rank_fibras(min_yield=0.04, max_debt_equity=1.5) -> list:
    """
    Evaluates the full list of FIBRAs and ranks those that pass all screens.
    Returns a sorted list of dictionaries representing the passing candidates.
    """
    print(f"Screening FIBRAs universe ({len(FIBRA_TICKERS)} assets) with filters:")
    print(f"  - Min Yield: {min_yield*100:.2f}%")
    print(f"  - Max Debt/Equity: {max_debt_equity:.2f}")
    print(f"  - Trend filter: Price > SMA 200")
    print("-" * 60)
    
    passed_candidates = []
    
    for t in FIBRA_TICKERS:
        print(f"Evaluating {t}...")
        metrics = get_fibra_metrics(t)
        if metrics is None:
            continue
            
        dy = metrics["dividend_yield"]
        de = metrics["debt_to_equity"]
        price = metrics["current_price"]
        sma200 = metrics["sma200"]
        
        trend_bull = price > sma200
        
        # Check standard conditions
        if dy >= min_yield and de <= max_debt_equity and trend_bull:
            passed_candidates.append(metrics)
            print(f"  [PASS] {t} with Yield: {dy*100:.2f}%, Debt/Equity: {de:.2f}")
        else:
            reasons = []
            if dy < min_yield:
                reasons.append(f"yield {dy*100:.2f}% < {min_yield*100:.1f}%")
            if de > max_debt_equity:
                reasons.append(f"debt/equity {de:.2f} > {max_debt_equity:.2f}")
            if not trend_bull:
                reasons.append(f"price {price:.2f} <= SMA200 {sma200:.2f}")
            print(f"  [FAIL] {t} because: {', '.join(reasons)}")
            
    # Sort candidates by yield and safety score
    ranked = sorted(passed_candidates, key=lambda x: x["dividend_score"], reverse=True)
    return ranked
