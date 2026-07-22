import os
import sys
import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# BMV and US Seed Universes
DIVIDEND_BMV_TICKERS = ["BBAJIOO.MX", "GFNORTEO.MX", "WALMEX.MX", "ORBIA.MX", "FEMSAUBD.MX", "KOFUBL.MX", "GRUMAB.MX", "FUNO11.MX", "FIBRAMQ12.MX", "AC.MX", "OMAB.MX", "GAPB.MX"]
DIVIDEND_US_TICKERS = ["JNJ", "PG", "KO", "PEP", "XOM", "CVX", "VZ", "T", "MCD", "ABBV", "MMM", "TGT", "LOW", "O", "SPG", "ABT"]

def get_dividend_metrics(ticker_symbol: str, history_df: pd.DataFrame = None) -> dict:
    """
    Downloads and extracts all dividend, safety, and trend metrics for a ticker.
    Returns a dictionary of metrics, or None if downloading failed.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # 1. Fetch historical pricing if not provided
        if history_df is None or history_df.empty:
            history_df = ticker.history(period="1y")
            
        if history_df.empty or len(history_df) < 200:
            return None
            
        current_price = float(history_df["Close"].iloc[-1])
        
        # Calculate SMA 200
        closes = history_df["Close"].values
        sma200 = float(closes[-200:].mean())
        
        # 2. Retrieve info/financials
        info = ticker.info
        
        # 3. Dividend Yield calculation with robust fallback
        # First try info: 'dividendYield' is a decimal (e.g. 0.035 for 3.5%)
        dividend_yield = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
        
        if dividend_yield is not None and dividend_yield > 1.0:
            dividend_yield = dividend_yield / 100.0
            
        if dividend_yield is None:
            # Fallback: sum up historical dividends paid in the last 365 days
            historical_divs = ticker.dividends
            if not historical_divs.empty:
                # Filter to last 365 days
                one_year_ago = datetime.datetime.now() - datetime.timedelta(days=365)
                # Ensure index has no timezone for matching datetime index
                if historical_divs.index.tz is not None:
                    historical_divs.index = historical_divs.index.tz_convert("UTC").tz_localize(None)
                recent_divs = historical_divs[historical_divs.index >= one_year_ago]
                annual_dividend = float(recent_divs.sum())
                dividend_yield = annual_dividend / current_price if current_price > 0 else 0.0
            else:
                dividend_yield = 0.0
                
        # 4. Safety Metrics
        payout_ratio = info.get("payoutRatio") # Decimal, e.g. 0.60
        eps = info.get("trailingEps") or info.get("forwardEps")
        debt_to_equity = info.get("debtToEquity") # Often percentage (e.g., 120.0 for 120%), or decimal.
        
        # Normalize debt to equity to decimal (if it's e.g. 150.0, divide by 100)
        if debt_to_equity is not None and debt_to_equity > 5.0:
            debt_to_equity = debt_to_equity / 100.0
            
        # Free Cash Flow payout coverage
        # Try to retrieve cashflow statement to find FCF (Operating Cash Flow - Capital Expenditures)
        fcf_payout_ratio = None
        try:
            cashflow = ticker.cashflow
            financials = ticker.financials
            if not cashflow.empty and not financials.empty:
                # Look for operating cash flow and capex in recent TTM or annual statements
                # Capital expenditures is usually negative in yfinance, so we add it
                op_cash = cashflow.loc["Operating Cash Flow"].iloc[0] if "Operating Cash Flow" in cashflow.index else None
                capex = cashflow.loc["Capital Expenditures"].iloc[0] if "Capital Expenditures" in cashflow.index else None
                
                if op_cash is not None and capex is not None:
                    fcf = op_cash + capex  # capex is negative
                    # Total dividends paid
                    div_paid = cashflow.loc["Cash Dividends Paid"].iloc[0] if "Cash Dividends Paid" in cashflow.index else None
                    if div_paid is not None and fcf > 0:
                        # Cash Dividends Paid is usually negative, so take absolute value
                        fcf_payout_ratio = abs(div_paid) / fcf
        except Exception:
            pass # Fall back if financial sheet read fails
            
        # 5. Dividend growth rate (3-year CAGR)
        historical_divs = ticker.dividends
        div_growth_3y = 0.0
        if not historical_divs.empty:
            try:
                # Group by calendar year
                divs_by_year = historical_divs.groupby(historical_divs.index.year).sum()
                years = sorted(divs_by_year.index)
                if len(years) >= 4:
                    recent_years = years[-4:-1] # Exclude current incomplete year
                    div_y1 = divs_by_year.loc[recent_years[0]]
                    div_y3 = divs_by_year.loc[recent_years[2]]
                    if div_y1 > 0 and div_y3 > 0:
                        div_growth_3y = (div_y3 / div_y1) ** (1/3) - 1.0
            except Exception:
                pass
                
        # Fill defaults
        payout_ratio = payout_ratio if payout_ratio is not None else 0.0
        eps = eps if eps is not None else 0.0
        debt_to_equity = debt_to_equity if debt_to_equity is not None else 0.0
        fcf_payout_ratio = fcf_payout_ratio if fcf_payout_ratio is not None else payout_ratio
        
        return {
            "ticker": ticker_symbol,
            "current_price": current_price,
            "sma200": sma200,
            "dividend_yield": dividend_yield,
            "payout_ratio": payout_ratio,
            "fcf_payout_ratio": fcf_payout_ratio,
            "eps": eps,
            "debt_to_equity": debt_to_equity,
            "div_growth_3y": div_growth_3y
        }
    except Exception as e:
        print(f"  [WARN] Failed to retrieve metrics for {ticker_symbol}: {e}")
        return None

def evaluate_and_rank_dividend_universe(tickers=None, min_yield=0.025, max_payout=0.80, max_fcf_payout=0.85, max_debt_equity=1.5) -> list:
    """
    Evaluates the full list of tickers and ranks those that pass all screens.
    Returns a sorted list of dictionaries representing the passing candidates.
    """
    if tickers is None:
        tickers = DIVIDEND_BMV_TICKERS + DIVIDEND_US_TICKERS
        
    print(f"Screening dividend universe ({len(tickers)} assets) with filters:")
    print(f"  - Min Yield: {min_yield*100:.2f}%")
    print(f"  - Max Payout Ratio: {max_payout*100:.2f}%")
    print(f"  - Max FCF Payout: {max_fcf_payout*100:.2f}%")
    print(f"  - Max Debt/Equity: {max_debt_equity:.2f}")
    print(f"  - Trend filter: Price > SMA 200")
    print("-" * 60)
    
    passed_candidates = []
    
    for t in tickers:
        print(f"Evaluating {t}...")
        metrics = get_dividend_metrics(t)
        if metrics is None:
            continue
            
        # Extract metrics
        dy = metrics["dividend_yield"]
        pr = metrics["payout_ratio"]
        fcf_pr = metrics["fcf_payout_ratio"]
        eps = metrics["eps"]
        de = metrics["debt_to_equity"]
        price = metrics["current_price"]
        sma200 = metrics["sma200"]
        
        # Check Filters
        # Yield check
        if dy < min_yield:
            print(f"  |-- [REJECTED] Yield {dy*100:.2f}% below threshold.")
            continue
            
        # Payout ratio check (REITs/Fibras exception: allow up to 95%)
        is_reit = (".MX" not in t and t in ["O", "SPG", "AMT", "CCI"]) or ("FIBRA" in t or "MQ" in t)
        payout_threshold = 0.95 if is_reit else max_payout
        
        if pr > payout_threshold or pr < 0.05:
            print(f"  |-- [REJECTED] Earnings Payout {pr*100:.1f}% out of bounds (allowed: 5%-{payout_threshold*100:.0f}%).")
            continue
            
        # FCF payout check
        if fcf_pr > payout_threshold:
            print(f"  |-- [REJECTED] FCF Payout {fcf_pr*100:.1f}% exceeds threshold.")
            continue
            
        # Financial quality checks
        if eps <= 0:
            print(f"  |-- [REJECTED] EPS {eps:.2f} is non-positive.")
            continue
            
        if de > max_debt_equity and not is_reit:
            print(f"  |-- [REJECTED] Debt/Equity {de:.2f} exceeds limit.")
            continue
            
        # Trend check
        if price <= sma200:
            print(f"  |-- [REJECTED] Price ${price:.2f} <= SMA 200 (${sma200:.2f}) (Bear Trend).")
            continue
            
        # Passed all filters! Compute Dividend Score
        # 60% Yield + 40% 3y Dividend Growth CAGR (capped between 0% and 20%)
        growth_factor = max(0.0, min(0.20, metrics["div_growth_3y"]))
        score = (dy * 0.6) + (growth_factor * 0.4)
        metrics["dividend_score"] = score
        
        print(f"  +-- [PASSED] Yield: {dy*100:.2f}% | Payout: {pr*100:.1f}% | Growth: {metrics['div_growth_3y']*100:.1f}% | Score: {score:.4f}")
        passed_candidates.append(metrics)
        
    # Rank candidates by combined score
    ranked_candidates = sorted(passed_candidates, key=lambda x: x["dividend_score"], reverse=True)
    return ranked_candidates


def filter_dividend_quality(
    metrics: dict,
    max_fcf_payout: float = 0.85,
    max_debt_equity: float = 3.0,
    min_eps: float = 0.0
) -> dict:
    """
    Evaluates whether a candidate dividend asset is a sustainable quality asset vs a yield trap.
    Returns dictionary with boolean 'is_quality', 'rejection_reasons', and 'quality_score'.
    """
    reasons = []
    
    if metrics is None:
        return {"is_quality": False, "rejection_reasons": ["Missing metrics"], "quality_score": 0.0}

    dy = metrics.get("dividend_yield", 0.0)
    pr = metrics.get("payout_ratio", 0.0)
    fcf_pr = metrics.get("fcf_payout_ratio")
    eps = metrics.get("eps", 0.0)
    de = metrics.get("debt_to_equity", 0.0)
    is_reit = metrics.get("is_reit", False)

    # 1. Negative EPS
    if eps <= min_eps:
        reasons.append(f"Non-positive EPS ({eps:.2f})")

    # 2. FCF Payout exceeds maximum allowed threshold
    if fcf_pr is not None and fcf_pr > (0.95 if is_reit else max_fcf_payout):
        reasons.append(f"FCF payout ratio ({fcf_pr*100:.1f}%) exceeds max ({max_fcf_payout*100:.0f}%)")

    # 3. Earnings Payout exceeds limit
    payout_cap = 0.95 if is_reit else 0.85
    if pr > payout_cap:
        reasons.append(f"Earnings payout ratio ({pr*100:.1f}%) exceeds cap ({payout_cap*100:.0f}%)")

    # 4. Excessive Leverage
    if not is_reit and de > max_debt_equity:
        reasons.append(f"Debt-to-Equity ratio ({de:.2f}) exceeds max ({max_debt_equity:.2f})")

    is_quality = len(reasons) == 0
    quality_score = dy * 0.7 + (metrics.get("div_growth_3y", 0.0) * 0.3) if is_quality else 0.0

    return {
        "ticker": metrics.get("ticker", "UNKNOWN"),
        "is_quality": is_quality,
        "rejection_reasons": reasons,
        "quality_score": quality_score
    }

if __name__ == "__main__":
    # Test screening
    results = evaluate_and_rank_dividend_universe()
    print("\n--- SCREENER RESULTS ---")
    for idx, r in enumerate(results, start=1):
        print(f"{idx}. {r['ticker']} - Score: {r['dividend_score']:.4f} (Yield: {r['dividend_yield']*100:.2f}%)")
