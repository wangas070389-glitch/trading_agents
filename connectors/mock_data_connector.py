import random

# Seed for reproducibility of simulated series
random.seed(42)

def get_bmv_universe_metadata() -> list[dict]:
    """
    Returns general metadata of the BMV universe.
    """
    return [
        {"ticker": "FEMSAUBD", "name": "Fomento Economico Mexicano SAB de CV", "sector": "Consumer Staples"},
        {"ticker": "CEMEXCPO", "name": "Cemex SAB de CV", "sector": "Industrials/Materials"},
        {"ticker": "ALFAA", "name": "Alfa SAB de CV", "sector": "Conglomerate"},
        {"ticker": "PE&OLES", "name": "Industrias Penoles SAB de CV", "sector": "Materials/Mining"},
        {"ticker": "MTRAP", "name": "Minera Trap S.A.B. de C.V.", "sector": "Materials/Mining"},
        {"ticker": "VTRAP", "name": "Value Trap Retail S.A.B. de C.V.", "sector": "Consumer Discretionary"}
    ]

def get_pricing_series(ticker: str) -> dict:
    config = {
        "FEMSAUBD": {"avg_price": 135.00, "avg_volume": 750000},
        "CEMEXCPO": {"avg_price": 8.20, "avg_volume": 8800000},
        "ALFAA": {"avg_price": 11.20, "avg_volume": 4020000},
        "PE&OLES": {"avg_price": 230.0, "avg_volume": 78000},
        "MTRAP": {"avg_price": 5.00, "avg_volume": 80000},
        "VTRAP": {"avg_price": 12.00, "avg_volume": 533000}
    }
    
    cfg = config.get(ticker.split(".")[0], {"avg_price": 50.0, "avg_volume": 100000})
    
    prices = []
    volumes = []
    
    current_price = cfg["avg_price"]
    for _ in range(30):
        current_price = current_price * (1 + random.uniform(-0.015, 0.015))
        prices.append(round(current_price, 2))
        vol = int(cfg["avg_volume"] * random.uniform(0.7, 1.3))
        volumes.append(vol)
        
    return {
        "prices": prices,
        "volumes": volumes,
        "current_price": prices[-1]
    }

def get_filing_data(ticker: str) -> dict:
    """
    Simulates mcp_bmv_scraper pulling financial data.
    Returns balance sheet and income statement metrics for the given ticker.
    Supports all 27 tickers in the backtest and live universe.
    """
    # Standardize ticker name (strip suffix like .MX)
    t = ticker.split(".")[0].upper()
    
    # Filings database (amounts in MXN, US tickers converted using a baseline USDMXN rate of 18.0)
    filings = {
        "FEMSAUBD": {
            "shares_outstanding": 3578000000,
            "ttm_net_income": 45000000000,
            "total_assets": 720000000000,
            "total_liabilities": 410000000000,
            "total_debt": 160000000000,
            "cash_and_equivalents": 85000000000,
            "ttm_ebitda": 88000000000,
            "annual_dividend_per_share": 5.60,
            "base_fcff": 45000000000,
            "beta": 0.85,
            "growth_rate_stage1": 0.07,
            "tax_rate": 0.30,
            "cost_of_debt": 0.075
        },
        "CEMEXCPO": {
            "shares_outstanding": 15000000000,
            "ttm_net_income": 19200000000,
            "total_assets": 560000000000,
            "total_liabilities": 310000000000,
            "total_debt": 178000000000,
            "cash_and_equivalents": 26000000000,
            "ttm_ebitda": 57000000000,
            "annual_dividend_per_share": 0.28,
            "base_fcff": 23500000000,
            "beta": 1.20,
            "growth_rate_stage1": 0.055,
            "tax_rate": 0.30,
            "cost_of_debt": 0.082
        },
        "ALFAA": {
            "shares_outstanding": 4810000000,
            "ttm_net_income": 6200000000,
            "total_assets": 325000000000,
            "total_liabilities": 242000000000,
            "total_debt": 142000000000,
            "cash_and_equivalents": 21000000000,
            "ttm_ebitda": 31500000000,
            "annual_dividend_per_share": 0.42,
            "base_fcff": 10500000000,
            "beta": 1.15,
            "growth_rate_stage1": 0.045,
            "tax_rate": 0.30,
            "cost_of_debt": 0.080
        },
        "PE&OLES": {
            "shares_outstanding": 397400000,
            "ttm_net_income": 2100000000,
            "total_assets": 152000000000,
            "total_liabilities": 61000000000,
            "total_debt": 31000000000,
            "cash_and_equivalents": 10500000000,
            "ttm_ebitda": 12500000000,
            "annual_dividend_per_share": 1.60,
            "base_fcff": 3200000000,
            "beta": 1.05,
            "growth_rate_stage1": 0.035,
            "tax_rate": 0.30,
            "cost_of_debt": 0.078
        },
        "MTRAP": {
            "shares_outstanding": 100000000,
            "ttm_net_income": 155000000,
            "total_assets": 1250000000,
            "total_liabilities": 410000000,
            "total_debt": 95000000,
            "cash_and_equivalents": 52000000,
            "ttm_ebitda": 255000000,
            "annual_dividend_per_share": 0.52,
            "base_fcff": 122000000,
            "beta": 1.40,
            "growth_rate_stage1": 0.025,
            "tax_rate": 0.30,
            "cost_of_debt": 0.095
        },
        "VTRAP": {
            "shares_outstanding": 400000000,
            "ttm_net_income": 820000000,
            "total_assets": 10200000000,
            "total_liabilities": 6100000000,
            "total_debt": 3050000000,
            "cash_and_equivalents": 520000000,
            "ttm_ebitda": 1820000000,
            "annual_dividend_per_share": 0.62,
            "base_fcff": 920000000,
            "beta": 0.95,
            "growth_rate_stage1": 0.045,
            "tax_rate": 0.30,
            "cost_of_debt": 0.076
        },
        "AMXB": {
            "shares_outstanding": 60000000000,
            "ttm_net_income": 85000000000,
            "total_assets": 950000000000,
            "total_liabilities": 600000000000,
            "total_debt": 400000000000,
            "cash_and_equivalents": 50000000000,
            "ttm_ebitda": 160000000000,
            "annual_dividend_per_share": 0.48,
            "base_fcff": 80000000000,
            "beta": 0.90,
            "growth_rate_stage1": 0.04,
            "tax_rate": 0.30,
            "cost_of_debt": 0.078
        },
        "WALMEX": {
            "shares_outstanding": 17460000000,
            "ttm_net_income": 50000000000,
            "total_assets": 420000000000,
            "total_liabilities": 200000000000,
            "total_debt": 20000000000,
            "cash_and_equivalents": 40000000000,
            "ttm_ebitda": 85000000000,
            "annual_dividend_per_share": 2.20,
            "base_fcff": 60000000000,
            "beta": 0.80,
            "growth_rate_stage1": 0.06,
            "tax_rate": 0.30,
            "cost_of_debt": 0.070
        },
        "GFNORTEO": {
            "shares_outstanding": 2880000000,
            "ttm_net_income": 45000000000,
            "total_assets": 1500000000000,
            "total_liabilities": 1300000000000,
            "total_debt": 100000000000,
            "cash_and_equivalents": 80000000000,
            "ttm_ebitda": 70000000000,
            "annual_dividend_per_share": 6.50,
            "base_fcff": 40000000000,
            "beta": 1.10,
            "growth_rate_stage1": 0.07,
            "tax_rate": 0.30,
            "cost_of_debt": 0.080
        },
        "GMEXICOB": {
            "shares_outstanding": 7780000000,
            "ttm_net_income": 80000000000,
            "total_assets": 650000000000,
            "total_liabilities": 300000000000,
            "total_debt": 180000000000,
            "cash_and_equivalents": 120000000000,
            "ttm_ebitda": 140000000000,
            "annual_dividend_per_share": 4.00,
            "base_fcff": 60000000000,
            "beta": 1.10,
            "growth_rate_stage1": 0.05,
            "tax_rate": 0.30,
            "cost_of_debt": 0.082
        },
        "BIMBOA": {
            "shares_outstanding": 4400000000,
            "ttm_net_income": 18000000000,
            "total_assets": 380000000000,
            "total_liabilities": 260000000000,
            "total_debt": 110000000000,
            "cash_and_equivalents": 15000000000,
            "ttm_ebitda": 55000000000,
            "annual_dividend_per_share": 1.20,
            "base_fcff": 25000000000,
            "beta": 0.80,
            "growth_rate_stage1": 0.05,
            "tax_rate": 0.30,
            "cost_of_debt": 0.076
        },
        "GAPB": {
            "shares_outstanding": 500000000,
            "ttm_net_income": 9500000000,
            "total_assets": 85000000000,
            "total_liabilities": 50000000000,
            "total_debt": 35000000000,
            "cash_and_equivalents": 12000000000,
            "ttm_ebitda": 15000000000,
            "annual_dividend_per_share": 14.20,
            "base_fcff": 15000000000,
            "beta": 1.00,
            "growth_rate_stage1": 0.06,
            "tax_rate": 0.30,
            "cost_of_debt": 0.078
        },
        "ASURB": {
            "shares_outstanding": 300000000,
            "ttm_net_income": 7200000000,
            "total_assets": 65000000000,
            "total_liabilities": 25000000000,
            "total_debt": 15000000000,
            "cash_and_equivalents": 10000000000,
            "ttm_ebitda": 11000000000,
            "annual_dividend_per_share": 10.00,
            "base_fcff": 10000000000,
            "beta": 0.90,
            "growth_rate_stage1": 0.05,
            "tax_rate": 0.30,
            "cost_of_debt": 0.074
        },
        "OMAB": {
            "shares_outstanding": 390000000,
            "ttm_net_income": 4800000000,
            "total_assets": 45000000000,
            "total_liabilities": 25000000000,
            "total_debt": 18000000000,
            "cash_and_equivalents": 6000000000,
            "ttm_ebitda": 8000000000,
            "annual_dividend_per_share": 8.00,
            "base_fcff": 7000000000,
            "beta": 1.00,
            "growth_rate_stage1": 0.06,
            "tax_rate": 0.30,
            "cost_of_debt": 0.079
        },
        "GRUMAB": {
            "shares_outstanding": 380000000,
            "ttm_net_income": 8500000000,
            "total_assets": 90000000000,
            "total_liabilities": 55000000000,
            "total_debt": 30000000000,
            "cash_and_equivalents": 8000000000,
            "ttm_ebitda": 18000000000,
            "annual_dividend_per_share": 6.80,
            "base_fcff": 12000000000,
            "beta": 0.70,
            "growth_rate_stage1": 0.04,
            "tax_rate": 0.30,
            "cost_of_debt": 0.072
        },
        "KIMBERA": {
            "shares_outstanding": 3100000000,
            "ttm_net_income": 6500000000,
            "total_assets": 60000000000,
            "total_liabilities": 45000000000,
            "total_debt": 25000000000,
            "cash_and_equivalents": 5000000000,
            "ttm_ebitda": 12500000000,
            "annual_dividend_per_share": 1.80,
            "base_fcff": 8000000000,
            "beta": 0.70,
            "growth_rate_stage1": 0.04,
            "tax_rate": 0.30,
            "cost_of_debt": 0.073
        },
        "AC": {
            "shares_outstanding": 1760000000,
            "ttm_net_income": 15000000000,
            "total_assets": 160000000000,
            "total_liabilities": 70000000000,
            "total_debt": 25000000000,
            "cash_and_equivalents": 30000000000,
            "ttm_ebitda": 32000000000,
            "annual_dividend_per_share": 4.50,
            "base_fcff": 18000000000,
            "beta": 0.70,
            "growth_rate_stage1": 0.05,
            "tax_rate": 0.30,
            "cost_of_debt": 0.071
        },
        "ORBIA": {
            "shares_outstanding": 2000000000,
            "ttm_net_income": 5000000000,
            "total_assets": 200000000000,
            "total_liabilities": 130000000000,
            "total_debt": 60000000000,
            "cash_and_equivalents": 15000000000,
            "ttm_ebitda": 22000000000,
            "annual_dividend_per_share": 1.50,
            "base_fcff": 10000000000,
            "beta": 1.20,
            "growth_rate_stage1": 0.03,
            "tax_rate": 0.30,
            "cost_of_debt": 0.084
        },
        "PINFRA": {
            "shares_outstanding": 380000000,
            "ttm_net_income": 6000000000,
            "total_assets": 85000000000,
            "total_liabilities": 25000000000,
            "total_debt": 10000000000,
            "cash_and_equivalents": 25000000000,
            "ttm_ebitda": 10000000000,
            "annual_dividend_per_share": 5.40,
            "base_fcff": 8000000000,
            "beta": 0.70,
            "growth_rate_stage1": 0.04,
            "tax_rate": 0.30,
            "cost_of_debt": 0.075
        },
        "BBAJIOO": {
            "shares_outstanding": 1200000000,
            "ttm_net_income": 11000000000,
            "total_assets": 280000000000,
            "total_liabilities": 240000000000,
            "total_debt": 10000000000,
            "cash_and_equivalents": 20000000000,
            "ttm_ebitda": 15000000000,
            "annual_dividend_per_share": 5.80,
            "base_fcff": 8000000000,
            "beta": 1.00,
            "growth_rate_stage1": 0.06,
            "tax_rate": 0.30,
            "cost_of_debt": 0.080
        },
        "GENTERA": {
            "shares_outstanding": 1500000000,
            "ttm_net_income": 4500000000,
            "total_assets": 75000000000,
            "total_liabilities": 50000000000,
            "total_debt": 25000000000,
            "cash_and_equivalents": 12000000000,
            "ttm_ebitda": 8000000000,
            "annual_dividend_per_share": 1.80,
            "base_fcff": 4000000000,
            "beta": 1.20,
            "growth_rate_stage1": 0.05,
            "tax_rate": 0.30,
            "cost_of_debt": 0.088
        },
        "CUERVO": {
            "shares_outstanding": 3600000000,
            "ttm_net_income": 5800000000,
            "total_assets": 110000000000,
            "total_liabilities": 50000000000,
            "total_debt": 20000000000,
            "cash_and_equivalents": 10000000000,
            "ttm_ebitda": 10000000000,
            "annual_dividend_per_share": 0.60,
            "base_fcff": 6000000000,
            "beta": 0.80,
            "growth_rate_stage1": 0.04,
            "tax_rate": 0.30,
            "cost_of_debt": 0.076
        },
        "GCC": {
            "shares_outstanding": 330000000,
            "ttm_net_income": 3800000000,
            "total_assets": 55000000000,
            "total_liabilities": 25000000000,
            "total_debt": 10000000000,
            "cash_and_equivalents": 8000000000,
            "ttm_ebitda": 8500000000,
            "annual_dividend_per_share": 3.50,
            "base_fcff": 4000000000,
            "beta": 0.90,
            "growth_rate_stage1": 0.06,
            "tax_rate": 0.30,
            "cost_of_debt": 0.077
        },
        "VESTA": {
            "shares_outstanding": 700000000,
            "ttm_net_income": 2800000000,
            "total_assets": 60000000000,
            "total_liabilities": 30000000000,
            "total_debt": 20000000000,
            "cash_and_equivalents": 5000000000,
            "ttm_ebitda": 5000000000,
            "annual_dividend_per_share": 1.20,
            "base_fcff": 3000000000,
            "beta": 0.80,
            "growth_rate_stage1": 0.08,
            "tax_rate": 0.30,
            "cost_of_debt": 0.078
        },
        # US Tickers (Nominal USD converted using 18.0 exchange rate)
        "NVDA": {
            "shares_outstanding": 24600000000,
            "ttm_net_income": 40000000000 * 18.0,
            "total_assets": 85000000000 * 18.0,
            "total_liabilities": 25000000000 * 18.0,
            "total_debt": 10000000000 * 18.0,
            "cash_and_equivalents": 30000000000 * 18.0,
            "ttm_ebitda": 45000000000 * 18.0,
            "annual_dividend_per_share": 0.04 * 18.0,
            "base_fcff": 40000000000 * 18.0,
            "beta": 1.80,
            "growth_rate_stage1": 0.20,
            "tax_rate": 0.21,
            "cost_of_debt": 0.055
        },
        "AAPL": {
            "shares_outstanding": 15300000000,
            "ttm_net_income": 100000000000 * 18.0,
            "total_assets": 350000000000 * 18.0,
            "total_liabilities": 270000000000 * 18.0,
            "total_debt": 100000000000 * 18.0,
            "cash_and_equivalents": 70000000000 * 18.0,
            "ttm_ebitda": 130000000000 * 18.0,
            "annual_dividend_per_share": 1.00 * 18.0,
            "base_fcff": 100000000000 * 18.0,
            "beta": 1.10,
            "growth_rate_stage1": 0.07,
            "tax_rate": 0.21,
            "cost_of_debt": 0.052
        },
        "MSFT": {
            "shares_outstanding": 7400000000,
            "ttm_net_income": 88000000000 * 18.0,
            "total_assets": 470000000000 * 18.0,
            "total_liabilities": 220000000000 * 18.0,
            "total_debt": 80000000000 * 18.0,
            "cash_and_equivalents": 80000000000 * 18.0,
            "ttm_ebitda": 125000000000 * 18.0,
            "annual_dividend_per_share": 3.00 * 18.0,
            "base_fcff": 70000000000 * 18.0,
            "beta": 1.10,
            "growth_rate_stage1": 0.09,
            "tax_rate": 0.21,
            "cost_of_debt": 0.054
        },
        "AMZN": {
            "shares_outstanding": 10400000000,
            "ttm_net_income": 35000000000 * 18.0,
            "total_assets": 520000000000 * 18.0,
            "total_liabilities": 310000000000 * 18.0,
            "total_debt": 130000000000 * 18.0,
            "cash_and_equivalents": 80000000000 * 18.0,
            "ttm_ebitda": 100000000000 * 18.0,
            "annual_dividend_per_share": 0.0,
            "base_fcff": 40000000000 * 18.0,
            "beta": 1.20,
            "growth_rate_stage1": 0.10,
            "tax_rate": 0.21,
            "cost_of_debt": 0.058
        },
        "GOOGL": {
            "shares_outstanding": 12400000000,
            "ttm_net_income": 75000000000 * 18.0,
            "total_assets": 400000000000 * 18.0,
            "total_liabilities": 110000000000 * 18.0,
            "total_debt": 28000000000 * 18.0,
            "cash_and_equivalents": 110000000000 * 18.0,
            "ttm_ebitda": 105000000000 * 18.0,
            "annual_dividend_per_share": 0.80 * 18.0,
            "base_fcff": 70000000000 * 18.0,
            "beta": 1.10,
            "growth_rate_stage1": 0.08,
            "tax_rate": 0.21,
            "cost_of_debt": 0.053
        }
    }
    return filings.get(t, filings["FEMSAUBD"])
