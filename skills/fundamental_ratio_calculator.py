def calculate_fundamental_ratios(
    current_price: float,
    shares_outstanding: float,
    ttm_net_income: float,
    total_assets: float,
    total_liabilities: float,
    total_debt: float,
    cash_and_equivalents: float,
    ttm_ebitda: float,
    annual_dividend_per_share: float
) -> dict:
    """
    Computes fundamental valuation multiples and metrics.
    Returns a dictionary of:
    - P/E
    - P/B
    - EV
    - EV/EBITDA
    - Dividend Yield
    """
    metrics = {}
    
    # 1. Price-to-Earnings (P/E)
    if shares_outstanding > 0 and ttm_net_income != 0:
        eps_ttm = ttm_net_income / shares_outstanding
        metrics["eps_ttm"] = eps_ttm
        if eps_ttm > 0:
            metrics["pe_ratio"] = current_price / eps_ttm
        else:
            metrics["pe_ratio"] = float("inf")  # Negative earnings
    else:
        metrics["eps_ttm"] = 0.0
        metrics["pe_ratio"] = None

    # 2. Price-to-Book (P/B)
    book_value = total_assets - total_liabilities
    metrics["book_value"] = book_value
    if shares_outstanding > 0:
        bvps = book_value / shares_outstanding
        metrics["bvps"] = bvps
        if bvps > 0:
            metrics["pb_ratio"] = current_price / bvps
        else:
            metrics["pb_ratio"] = float("inf")
    else:
        metrics["bvps"] = 0.0
        metrics["pb_ratio"] = None

    # 3. Enterprise Value (EV) and EV/EBITDA
    market_cap = current_price * shares_outstanding
    metrics["market_cap"] = market_cap
    ev = market_cap + total_debt - cash_and_equivalents
    metrics["enterprise_value"] = ev
    
    if ttm_ebitda > 0:
        metrics["ev_ebitda"] = ev / ttm_ebitda
    else:
        metrics["ev_ebitda"] = None

    # 4. Dividend Yield
    if current_price > 0:
        metrics["dividend_yield"] = annual_dividend_per_share / current_price
    else:
        metrics["dividend_yield"] = 0.0

    return metrics
