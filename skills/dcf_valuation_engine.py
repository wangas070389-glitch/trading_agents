def calculate_cost_of_equity(
    risk_free_rate: float,
    beta: float,
    equity_risk_premium: float,
    sovereign_risk_premium: float = 0.0
) -> float:
    """
    Computes Cost of Equity using the Capital Asset Pricing Model (CAPM).
    Keeps percentages as decimals (e.g., 0.06 for 6%).
    """
    return risk_free_rate + (beta * equity_risk_premium) + sovereign_risk_premium

def calculate_wacc(
    cost_of_equity: float,
    cost_of_debt: float,
    total_debt: float,
    market_cap: float,
    tax_rate: float
) -> float:
    """
    Computes the Weighted Average Cost of Capital (WACC).
    """
    total_capital = total_debt + market_cap
    if total_capital <= 0:
        return cost_of_equity
    
    weight_equity = market_cap / total_capital
    weight_debt = total_debt / total_capital
    
    wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
    return wacc

def calculate_dcf_intrinsic_value(
    current_price: float,
    shares_outstanding: float,
    base_fcff: float,
    wacc: float,
    total_debt: float,
    cash_and_equivalents: float,
    growth_rate_stage1: float = 0.06,  # 6% initial growth
    terminal_growth: float = 0.03,      # 3% terminal growth (conservatively capped)
    stage1_years: int = 5,
    stage2_years: int = 5
) -> dict:
    """
    Computes Intrinsic Value using a multi-stage FCFF model.
    Stage 1: High growth (years 1-5)
    Stage 2: Transition decay (years 6-10)
    Stage 3: Terminal constant growth (years 10+)
    """
    results = {}
    
    # 1. Project cash flows
    fcff_projections = []
    current_fcff = base_fcff
    
    # Stage 1: High Growth
    for t in range(1, stage1_years + 1):
        current_fcff = current_fcff * (1 + growth_rate_stage1)
        fcff_projections.append((t, current_fcff, growth_rate_stage1))
        
    # Stage 2: Transition Decay (linear decrease in growth rate from growth_rate_stage1 to terminal_growth)
    step = (growth_rate_stage1 - terminal_growth) / stage2_years if stage2_years > 0 else 0
    for i in range(1, stage2_years + 1):
        t = stage1_years + i
        current_growth = growth_rate_stage1 - (i * step)
        current_fcff = current_fcff * (1 + current_growth)
        fcff_projections.append((t, current_fcff, current_growth))
        
    # 2. Compute Terminal Value (at year 10)
    # Structurally bound terminal growth to not exceed WACC minus an economic buffer.
    # Flooring the denominator post-hoc masks impossible inputs; constrain at the source.
    max_sustainable_growth = min(wacc - 0.005, 0.03)
    effective_terminal_growth = min(terminal_growth, max_sustainable_growth)
    denominator = wacc - effective_terminal_growth

    last_year_fcff = fcff_projections[-1][1]
    terminal_value = (last_year_fcff * (1 + effective_terminal_growth)) / denominator
    
    # 3. Discount cash flows to present value
    pv_cash_flows = 0.0
    for t, fcff, _ in fcff_projections:
        pv_cash_flows += fcff / ((1 + wacc) ** t)
        
    pv_terminal_value = terminal_value / ((1 + wacc) ** (stage1_years + stage2_years))
    enterprise_value = pv_cash_flows + pv_terminal_value
    
    # 4. Compute Equity Value and Intrinsic Value Per Share
    equity_value = enterprise_value - total_debt + cash_and_equivalents
    
    if shares_outstanding > 0:
        intrinsic_value_per_share = equity_value / shares_outstanding
    else:
        intrinsic_value_per_share = 0.0
        
    # Prevent negative intrinsic values (floor at 0.0)
    if intrinsic_value_per_share < 0:
        intrinsic_value_per_share = 0.0
        
    # Margin of safety
    if current_price > 0:
        margin_of_safety = (intrinsic_value_per_share - current_price) / current_price
    else:
        margin_of_safety = 0.0
        
    results["base_fcff"] = base_fcff
    results["wacc"] = wacc
    results["enterprise_value"] = enterprise_value
    results["equity_value"] = equity_value
    results["intrinsic_value"] = intrinsic_value_per_share
    results["margin_of_safety"] = margin_of_safety
    results["fcff_projections"] = fcff_projections
    results["terminal_value"] = terminal_value
    
    return results
