import uuid
from connectors.mock_data_connector import get_bmv_universe_metadata, get_pricing_series, get_filing_data
from skills.liquidity_gatekeeper import calculate_adtv, passes_liquidity_gate
from skills.fundamental_ratio_calculator import calculate_fundamental_ratios
from skills.dcf_valuation_engine import calculate_cost_of_equity, calculate_wacc, calculate_dcf_intrinsic_value
from agents.agents import FundamentalScreener, MacroRiskAnalyst, PortfolioReconciler

def run_valuation_pipeline(execution_date: str) -> str:
    print("=" * 80)
    print(f"STARTING MEXICAN VALUE STOCK EVALUATION PIPELINE | DATE: {execution_date}")
    print("=" * 80)

    # Sovereign market baseline parameters for Mexico (Banxico rates and risk premiums)
    RISK_FREE_RATE = 0.095        # 9.5% (Mbonos 10Y yield)
    EQUITY_RISK_PREMIUM = 0.055   # 5.5% 
    SOVEREIGN_RISK_PREMIUM = 0.020 # 2.0% EMBI+ spread for Mexico
    TAX_RATE = 0.30               # 30% Mexican corporate tax rate

    # Fetch active tickers from simulated BMV/BIVA endpoints
    universe = get_bmv_universe_metadata()
    print(f"\n[Ingest] Ingested raw metadata for {len(universe)} BMV entities.")

    # Phase 1: Filter & Compute (Stateless Skills Layer)
    print("\n--- PHASE 1: FILTER & STATISTIC COMPUTE ---")
    
    liquid_candidates = []
    ticker_to_anon_map = {}
    anon_to_ticker_map = {}
    
    # Counter for generating anonymous IDs
    anon_counter = 1
    
    for asset in universe:
        ticker = asset["ticker"]
        print(f"\nProcessing ticker: {ticker}...")
        
        # 1. Fetch Pricing Feed
        pricing = get_pricing_series(ticker)
        prices = pricing["prices"]
        volumes = pricing["volumes"]
        current_price = pricing["current_price"]
        
        # 2. Compute 30-day ADTV
        adtv = calculate_adtv(prices, volumes)
        print(f"  |-- Calculated ADTV: {adtv:,.2f} MXN (Price: {current_price} MXN)")
        
        # 3. Apply Liquidity Gatekeeper (Vulnerability 1 Mitigation)
        if not passes_liquidity_gate(adtv, threshold=5000000.0):
            print(f"  +-- [REJECTED] ADTV below 5M MXN threshold. Dropped from pipeline.")
            continue
        print(f"  |-- [PASSED] Liquidity clearance verified.")
        
        # 4. Fetch Filing Data
        filing = get_filing_data(ticker)
        
        # 5. Calculate Fundamental Ratios
        ratios = calculate_fundamental_ratios(
            current_price=current_price,
            shares_outstanding=filing["shares_outstanding"],
            ttm_net_income=filing["ttm_net_income"],
            total_assets=filing["total_assets"],
            total_liabilities=filing["total_liabilities"],
            total_debt=filing["total_debt"],
            cash_and_equivalents=filing["cash_and_equivalents"],
            ttm_ebitda=filing["ttm_ebitda"],
            annual_dividend_per_share=filing["annual_dividend_per_share"]
        )
        
        # 6. Calculate Baseline Cost of Equity & WACC
        cost_of_equity = calculate_cost_of_equity(
            risk_free_rate=RISK_FREE_RATE,
            beta=filing["beta"],
            equity_risk_premium=EQUITY_RISK_PREMIUM,
            sovereign_risk_premium=SOVEREIGN_RISK_PREMIUM
        )
        
        wacc = calculate_wacc(
            cost_of_equity=cost_of_equity,
            cost_of_debt=filing["cost_of_debt"],
            total_debt=filing["total_debt"],
            market_cap=ratios["market_cap"],
            tax_rate=TAX_RATE
        )
        
        # 7. Calculate Baseline DCF Valuation
        dcf_results = calculate_dcf_intrinsic_value(
            current_price=current_price,
            shares_outstanding=filing["shares_outstanding"],
            base_fcff=filing["base_fcff"],
            wacc=wacc,
            total_debt=filing["total_debt"],
            cash_and_equivalents=filing["cash_and_equivalents"],
            growth_rate_stage1=filing["growth_rate_stage1"],
            terminal_growth=min(0.035, filing["growth_rate_stage1"] * 0.6)
        )
        
        # 8. Anonymize the data (Vulnerability 3 Mitigation)
        anon_id = f"EQUITY_{chr(64 + anon_counter)}" # EQUITY_A, EQUITY_B, etc.
        anon_counter += 1
        
        ticker_to_anon_map[ticker] = anon_id
        anon_to_ticker_map[anon_id] = ticker
        
        # Create sanitized record
        sanitized_record = {
            "anon_id": anon_id,
            "current_price": current_price,
            "pe_ratio": ratios["pe_ratio"],
            "pb_ratio": ratios["pb_ratio"],
            "ev_ebitda": ratios["ev_ebitda"],
            "dividend_yield": ratios["dividend_yield"],
            "margin_of_safety": dcf_results["margin_of_safety"],
            "adtv": adtv,
            "raw_dcf_inputs": {
                "shares_outstanding": filing["shares_outstanding"],
                "base_fcff": filing["base_fcff"],
                "wacc": wacc,
                "total_debt": filing["total_debt"],
                "cash_and_equivalents": filing["cash_and_equivalents"],
                "growth_rate_stage1": filing["growth_rate_stage1"],
                "pre_stress_mos": dcf_results["margin_of_safety"]
            }
        }
        
        liquid_candidates.append(sanitized_record)
        print(f"  +-- Anonymized ticker {ticker} as {anon_id}. Metrics sent to agent queue.")

    print(f"\nPhase 1 Complete. {len(liquid_candidates)} equities advanced to Agent screening.")

    # Phase 2: Screen (Agent 1)
    print("\n--- PHASE 2: AGENT SCREENING (BLIND EVALUATION) ---")
    screener = FundamentalScreener()
    screened_candidates, screening_log = screener.screen(liquid_candidates)
    
    # Phase 3: Stress-Test (Agent 2)
    print("\n--- PHASE 3: AGENT STRESS-TESTING (QUALITATIVE DECONSTRUCTION) ---")
    analyst = MacroRiskAnalyst()
    stressed_candidates = analyst.stress_test(screened_candidates, anon_to_ticker_map)
    
    # Phase 4: Reconcile & Export (Agent 3)
    print("\n--- PHASE 4: PORTFOLIO RECONCILIATION & EXPORT ---")
    reconciler = PortfolioReconciler()
    report_markdown = reconciler.reconcile(stressed_candidates, anon_to_ticker_map, execution_date)
    
    print("\nVALUATION PIPELINE COMPLETED SUCCESSFULLY.")
    print("=" * 80)
    
    return report_markdown
