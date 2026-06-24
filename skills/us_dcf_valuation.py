import yfinance as yf
import pandas as pd
import numpy as np
from skills.dcf_valuation_engine import calculate_cost_of_equity, calculate_wacc, calculate_dcf_intrinsic_value

# USD Denominated Fundamental Filings Database for 12 US Mega-Cap Stocks
US_FILINGS_DATABASE = {
    "AAPL": {
        "shares_outstanding": 15300000000.0,
        "total_assets": 350000000000.0,
        "total_liabilities": 270000000000.0,
        "total_debt": 100000000000.0,
        "cash_and_equivalents": 70000000000.0,
        "base_fcff": 100000000000.0,
        "beta": 1.10,
        "growth_rate_stage1": 0.07,
        "tax_rate": 0.21,
        "cost_of_debt": 0.052
    },
    "MSFT": {
        "shares_outstanding": 7400000000.0,
        "total_assets": 470000000000.0,
        "total_liabilities": 220000000000.0,
        "total_debt": 80000000000.0,
        "cash_and_equivalents": 80000000000.0,
        "base_fcff": 70000000000.0,
        "beta": 1.10,
        "growth_rate_stage1": 0.09,
        "tax_rate": 0.21,
        "cost_of_debt": 0.054
    },
    "NVDA": {
        "shares_outstanding": 24600000000.0,
        "total_assets": 85000000000.0,
        "total_liabilities": 25000000000.0,
        "total_debt": 10000000000.0,
        "cash_and_equivalents": 30000000000.0,
        "base_fcff": 40000000000.0,
        "beta": 1.80,
        "growth_rate_stage1": 0.20,
        "tax_rate": 0.21,
        "cost_of_debt": 0.055
    },
    "AMZN": {
        "shares_outstanding": 10400000000.0,
        "total_assets": 520000000000.0,
        "total_liabilities": 310000000000.0,
        "total_debt": 130000000000.0,
        "cash_and_equivalents": 80000000000.0,
        "base_fcff": 40000000000.0,
        "beta": 1.20,
        "growth_rate_stage1": 0.10,
        "tax_rate": 0.21,
        "cost_of_debt": 0.058
    },
    "GOOGL": {
        "shares_outstanding": 12400000000.0,
        "total_assets": 400000000000.0,
        "total_liabilities": 110000000000.0,
        "total_debt": 28000000000.0,
        "cash_and_equivalents": 110000000000.0,
        "base_fcff": 70000000000.0,
        "beta": 1.10,
        "growth_rate_stage1": 0.08,
        "tax_rate": 0.21,
        "cost_of_debt": 0.053
    },
    "META": {
        "shares_outstanding": 2500000000.0,
        "total_assets": 220000000000.0,
        "total_liabilities": 70000000000.0,
        "total_debt": 18000000000.0,
        "cash_and_equivalents": 60000000000.0,
        "base_fcff": 43000000000.0,
        "beta": 1.20,
        "growth_rate_stage1": 0.12,
        "tax_rate": 0.21,
        "cost_of_debt": 0.052
    },
    "TSLA": {
        "shares_outstanding": 3100000000.0,
        "total_assets": 104000000000.0,
        "total_liabilities": 39000000000.0,
        "total_debt": 9000000000.0,
        "cash_and_equivalents": 26000000000.0,
        "base_fcff": 8000000000.0,
        "beta": 1.40,
        "growth_rate_stage1": 0.15,
        "tax_rate": 0.21,
        "cost_of_debt": 0.056
    },
    "AVGO": {
        "shares_outstanding": 460000000.0,
        "total_assets": 112000000000.0,
        "total_liabilities": 78000000000.0,
        "total_debt": 75000000000.0,
        "cash_and_equivalents": 12000000000.0,
        "base_fcff": 18000000000.0,
        "beta": 1.30,
        "growth_rate_stage1": 0.14,
        "tax_rate": 0.15,
        "cost_of_debt": 0.050
    },
    "COST": {
        "shares_outstanding": 440000000.0,
        "total_assets": 70000000000.0,
        "total_liabilities": 43000000000.0,
        "total_debt": 7000000000.0,
        "cash_and_equivalents": 11000000000.0,
        "base_fcff": 7000000000.0,
        "beta": 0.80,
        "growth_rate_stage1": 0.08,
        "tax_rate": 0.26,
        "cost_of_debt": 0.048
    },
    "NFLX": {
        "shares_outstanding": 430000000.0,
        "total_assets": 48000000000.0,
        "total_liabilities": 27000000000.0,
        "total_debt": 14000000000.0,
        "cash_and_equivalents": 7000000000.0,
        "base_fcff": 6000000000.0,
        "beta": 1.15,
        "growth_rate_stage1": 0.10,
        "tax_rate": 0.21,
        "cost_of_debt": 0.052
    },
    "AMD": {
        "shares_outstanding": 1600000000.0,
        "total_assets": 68000000000.0,
        "total_liabilities": 14000000000.0,
        "total_debt": 3000000000.0,
        "cash_and_equivalents": 6000000000.0,
        "base_fcff": 3000000000.0,
        "beta": 1.35,
        "growth_rate_stage1": 0.12,
        "tax_rate": 0.15,
        "cost_of_debt": 0.052
    },
    "JPM": {
        "shares_outstanding": 2800000000.0,
        "total_assets": 3800000000000.0,
        "total_liabilities": 3500000000000.0,
        "total_debt": 100000000000.0,
        "cash_and_equivalents": 80000000000.0,
        "base_fcff": 40000000000.0,
        "beta": 1.10,
        "growth_rate_stage1": 0.05,
        "tax_rate": 0.21,
        "cost_of_debt": 0.050
    }
}

def get_us_filing_data(ticker: str) -> dict:
    """Retrieve USD filing data for the ticker (stripped of exchange rate suffix)."""
    t = ticker.split(".")[0].upper()
    return US_FILINGS_DATABASE.get(t, US_FILINGS_DATABASE["AAPL"])

def calculate_us_dcs(ticker: str, current_price: float, risk_free_rate: float) -> dict:
    """
    Calculates cost of equity, WACC, and DCF intrinsic value details in USD.
    risk_free_rate: US 10-Year Treasury Yield (e.g. 0.045 for 4.5%).
    """
    filing = get_us_filing_data(ticker)
    
    # 1. Cost of Equity (CAPM)
    equity_risk_premium = 0.055
    cost_of_equity = calculate_cost_of_equity(
        risk_free_rate=risk_free_rate,
        beta=filing["beta"],
        equity_risk_premium=equity_risk_premium,
        sovereign_risk_premium=0.0
    )
    
    # 2. WACC
    market_cap = current_price * filing["shares_outstanding"]
    wacc = calculate_wacc(
        cost_of_equity=cost_of_equity,
        cost_of_debt=filing["cost_of_debt"],
        total_debt=filing["total_debt"],
        market_cap=market_cap,
        tax_rate=filing["tax_rate"]
    )
    
    # 3. Multi-Stage DCF intrinsic value
    dcf_res = calculate_dcf_intrinsic_value(
        current_price=current_price,
        shares_outstanding=filing["shares_outstanding"],
        base_fcff=filing["base_fcff"],
        wacc=wacc,
        total_debt=filing["total_debt"],
        cash_and_equivalents=filing["cash_and_equivalents"],
        growth_rate_stage1=filing["growth_rate_stage1"],
        terminal_growth=min(0.03, filing["growth_rate_stage1"] * 0.6)
    )
    
    return dcf_res
