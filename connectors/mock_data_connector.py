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
    """
    Simulates mcp_pricing_feed.
    Returns:
      - 'prices': list of closing prices for the last 30 days
      - 'volumes': list of traded volumes for the last 30 days
    """
    # Average targets:
    # FEMSAUBD: Price=200, Volume=750k (ADTV = 150M)
    # CEMEXCPO: Price=12.50, Volume=8.8M (ADTV = 110M)
    # ALFAA: Price=11.20, Volume=4.02M (ADTV = 45M)
    # PE&OLES: Price=230, Volume=78k (ADTV = 18M)
    # MTRAP: Price=5.00, Volume=80k (ADTV = 400k) -> Illiquid
    # VTRAP: Price=15.00, Volume=533k (ADTV = 8M) -> Passes gatekeeper, but has qualitative risks
    
    config = {
        "FEMSAUBD": {"avg_price": 135.00, "avg_volume": 750000},
        "CEMEXCPO": {"avg_price": 8.20, "avg_volume": 8800000},
        "ALFAA": {"avg_price": 11.20, "avg_volume": 4020000},
        "PE&OLES": {"avg_price": 230.0, "avg_volume": 78000},
        "MTRAP": {"avg_price": 5.00, "avg_volume": 80000},
        "VTRAP": {"avg_price": 12.00, "avg_volume": 533000}
    }
    
    cfg = config.get(ticker, {"avg_price": 10.0, "avg_volume": 100000})
    
    prices = []
    volumes = []
    
    # Generate 30 days of random-walk-like pricing and volumes
    current_price = cfg["avg_price"]
    for _ in range(30):
        current_price = current_price * (1 + random.uniform(-0.015, 0.015))
        prices.append(round(current_price, 2))
        
        # Vol varies around average
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
    Returns balance sheet and income statement metrics.
    """
    # Filings database
    filings = {
        "FEMSAUBD": {
            "shares_outstanding": 3578000000,
            "ttm_net_income": 45000000000,       # 45B MXN
            "total_assets": 720000000000,        # 720B MXN
            "total_liabilities": 410000000000,   # 410B MXN
            "total_debt": 160000000000,          # 160B MXN
            "cash_and_equivalents": 85000000000, # 85B MXN
            "ttm_ebitda": 88000000000,           # 88B MXN
            "annual_dividend_per_share": 5.60,
            "base_fcff": 45000000000,            # 45B MXN
            "beta": 0.85,
            "growth_rate_stage1": 0.07,
            "tax_rate": 0.30,
            "cost_of_debt": 0.075                 # 7.5%
        },
        "CEMEXCPO": {
            "shares_outstanding": 15000000000,
            "ttm_net_income": 19200000000,       # 19.2B MXN
            "total_assets": 560000000000,        # 560B MXN
            "total_liabilities": 310000000000,   # 310B MXN
            "total_debt": 178000000000,          # 178B MXN
            "cash_and_equivalents": 26000000000, # 26B MXN
            "ttm_ebitda": 57000000000,           # 57B MXN
            "annual_dividend_per_share": 0.28,
            "base_fcff": 23500000000,            # 23.5B MXN
            "beta": 1.20,
            "growth_rate_stage1": 0.055,
            "tax_rate": 0.30,
            "cost_of_debt": 0.082                 # 8.2%
        },
        "ALFAA": {
            "shares_outstanding": 4810000000,
            "ttm_net_income": 6200000000,         # 6.2B MXN
            "total_assets": 325000000000,        # 325B MXN
            "total_liabilities": 242000000000,   # 242B MXN
            "total_debt": 142000000000,          # 142B MXN
            "cash_and_equivalents": 21000000000, # 21B MXN
            "ttm_ebitda": 31500000000,           # 31.5B MXN
            "annual_dividend_per_share": 0.42,
            "base_fcff": 10500000000,            # 10.5B MXN
            "beta": 1.15,
            "growth_rate_stage1": 0.045,
            "tax_rate": 0.30,
            "cost_of_debt": 0.080                 # 8.0%
        },
        "PE&OLES": {
            "shares_outstanding": 397400000,
            "ttm_net_income": 2100000000,         # 2.1B MXN
            "total_assets": 152000000000,        # 152B MXN
            "total_liabilities": 61000000000,    # 61B MXN
            "total_debt": 31000000000,           # 31B MXN
            "cash_and_equivalents": 10500000000, # 10.5B MXN
            "ttm_ebitda": 12500000000,           # 12.5B MXN
            "annual_dividend_per_share": 1.60,
            "base_fcff": 3200000000,             # 3.2B MXN
            "beta": 1.05,
            "growth_rate_stage1": 0.035,
            "tax_rate": 0.30,
            "cost_of_debt": 0.078                 # 7.8%
        },
        "MTRAP": {
            "shares_outstanding": 100000000,
            "ttm_net_income": 155000000,          # 155M MXN
            "total_assets": 1250000000,          # 1.25B MXN
            "total_liabilities": 410000000,      # 410M MXN
            "total_debt": 95000000,              # 95M MXN
            "cash_and_equivalents": 52000000,    # 52M MXN
            "ttm_ebitda": 255000000,             # 255M MXN
            "annual_dividend_per_share": 0.52,
            "base_fcff": 122000000,              # 122M MXN
            "beta": 1.40,
            "growth_rate_stage1": 0.025,
            "tax_rate": 0.30,
            "cost_of_debt": 0.095                 # 9.5%
        },
        "VTRAP": {
            "shares_outstanding": 400000000,
            "ttm_net_income": 820000000,          # 820M MXN
            "total_assets": 10200000000,         # 10.2B MXN
            "total_liabilities": 6100000000,     # 6.1B MXN
            "total_debt": 3050000000,            # 3.05B MXN
            "cash_and_equivalents": 520000000,   # 520M MXN
            "ttm_ebitda": 1820000000,            # 1.82B MXN
            "annual_dividend_per_share": 0.62,
            "base_fcff": 920000000,              # 920M MXN
            "beta": 0.95,
            "growth_rate_stage1": 0.045,         # Trailing growth looks okay
            "tax_rate": 0.30,
            "cost_of_debt": 0.076                 # 7.6%
        }
    }
    return filings.get(ticker, filings["FEMSAUBD"])
