import os
import sys
import datetime
import yfinance as yf

# Add current directory to path to enable local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from skills.liquidity_gatekeeper import calculate_adtv, passes_liquidity_gate
from skills.fundamental_ratio_calculator import calculate_fundamental_ratios
from skills.dcf_valuation_engine import calculate_cost_of_equity, calculate_wacc, calculate_dcf_intrinsic_value
from agents.agents import FundamentalScreener, MacroRiskAnalyst, PortfolioReconciler

# Major S&P/BMV IPC components to query
BMV_TICKERS = [
    "AMXB.MX",       # América Móvil
    "FEMSAUBD.MX",   # FEMSA
    "WALMEX.MX",     # Walmart de México
    "GFNORTEO.MX",   # Banorte
    "GMEXICOB.MX",   # Grupo México
    "CEMEXCPO.MX",   # Cemex
    "BIMBOA.MX",     # Grupo Bimbo
    "GAPB.MX",       # Grupo Aeroportuario del Pacífico
    "ASURB.MX",      # Grupo Aeroportuario del Sureste
    "OMAB.MX",       # Grupo Aeroportuario del Centro Norte
    "GRUMAB.MX",     # Gruma
    "ALFAA.MX",      # Alfa
    "KIMBERA.MX",    # Kimberly-Clark de México
    "AC.MX",         # Arca Continental
    "ORBIA.MX",      # Orbia Advance Corporation
    "PE&OLES.MX",    # Industrias Peñoles
    "PINFRA.MX",     # Pinfra
    "BBAJIOO.MX",    # Banco del Bajío
    "GENTERA.MX",    # Gentera
    "CUERVO.MX",     # Jose Cuervo
    "GCC.MX",        # Cementos de Chihuahua
    "VESTA.MX"       # Vesta (Industrial Real Estate warehouses)
]

def fetch_live_metrics(ticker_symbol: str) -> dict:
    """
    Downloads live data for a ticker and extracts valuation parameters.
    Includes comprehensive fallbacks to avoid crashes when data is missing.
    """
    print(f"Fetching {ticker_symbol} from Yahoo Finance...")
    ticker = yf.Ticker(ticker_symbol)
    
    # 1. Fetch 30-day price history
    hist = ticker.history(period="1mo")
    if hist.empty:
        raise ValueError(f"No price history returned for {ticker_symbol}")
        
    prices = hist["Close"].tolist()
    volumes = hist["Volume"].tolist()
    current_price = prices[-1]
    
    # 2. Fetch Info
    info = ticker.info
    if not info:
        info = {}
        
    def get_field(keys: list[str], default=0.0):
        for k in keys:
            if k in info and info[k] is not None:
                return float(info[k])
        return default

    # Extract multiples & fundamentals
    shares_outstanding = get_field(["sharesOutstanding", "impliedSharesOutstanding"], 0.0)
    ttm_net_income = get_field(["netIncomeToCommon", "netIncome", "netIncomeFromContinuingOps"], 0.0)
    ttm_ebitda = get_field(["ebitda", "operatingIncome"], 0.0)
    total_debt = get_field(["totalDebt"], 0.0)
    cash_and_equivalents = get_field(["totalCash", "cashAndShortTermInvestments", "cash"], 0.0)
    total_assets = get_field(["totalAssets"], 0.0)
    total_liabilities = get_field(["totalLiabilities"], 0.0)
    annual_dividend_rate = get_field(["dividendRate", "trailingAnnualDividendRate", "dividendYield"], 0.0)
    beta = get_field(["beta"], 1.0)
    
    # Backup Balance Sheet parsing if info is empty
    try:
        if total_assets == 0 or total_liabilities == 0 or total_debt == 0:
            bs = ticker.balance_sheet
            if not bs.empty:
                col_0 = bs.columns[0]
                if total_assets == 0 and "Total Assets" in bs.index:
                    total_assets = float(bs.loc["Total Assets"].iloc[0])
                if total_liabilities == 0:
                    if "Total Liabilities Net Minor Interest" in bs.index:
                        total_liabilities = float(bs.loc["Total Liabilities Net Minor Interest"].iloc[0])
                    elif "Total Liabilities" in bs.index:
                        total_liabilities = float(bs.loc["Total Liabilities"].iloc[0])
                if total_debt == 0:
                    # Sum typical debt items in index
                    for row_name in bs.index:
                        if "debt" in row_name.lower() or "borrowing" in row_name.lower():
                            val = bs.loc[row_name].iloc[0]
                            if val and not hasattr(val, '__len__'):
                                total_debt += float(val)
    except Exception:
        pass

    # Backup Income Statement parsing
    try:
        if ttm_net_income == 0 or ttm_ebitda == 0:
            inc = ticker.financials
            if not inc.empty:
                col_0 = inc.columns[0]
                if ttm_net_income == 0:
                    if "Net Income Common Stockholders" in inc.index:
                        ttm_net_income = float(inc.loc["Net Income Common Stockholders"].iloc[0])
                    elif "Net Income" in inc.index:
                        ttm_net_income = float(inc.loc["Net Income"].iloc[0])
                if ttm_ebitda == 0:
                    if "EBITDA" in inc.index:
                        ttm_ebitda = float(inc.loc["EBITDA"].iloc[0])
                    elif "Operating Income" in inc.index:
                        ttm_ebitda = float(inc.loc["Operating Income"].iloc[0])
    except Exception:
        pass

    # Estimated Shares Outstanding fallback
    if shares_outstanding == 0 and current_price > 0:
        market_cap = get_field(["marketCap"], 0.0)
        if market_cap > 0:
            shares_outstanding = market_cap / current_price

    # 3. Calculate Base Free Cash Flow to Firm (FCFF)
    # Target: Operating Cash Flow - Capital Expenditures
    base_fcff = 0.0
    try:
        cf = ticker.cashflow
        if not cf.empty:
            ocf = 0.0
            if "Operating Cash Flow" in cf.index:
                ocf = float(cf.loc["Operating Cash Flow"].iloc[0])
            elif "Total Cash From Operating Activities" in cf.index:
                ocf = float(cf.loc["Total Cash From Operating Activities"].iloc[0])
                
            capex = 0.0
            if "Capital Expenditure" in cf.index:
                capex = float(cf.loc["Capital Expenditure"].iloc[0])
            elif "Net Capital Expenditures" in cf.index:
                capex = float(cf.loc["Net Capital Expenditures"].iloc[0])
                
            base_fcff = ocf + capex if capex < 0 else ocf - capex
    except Exception:
        pass

    # Safe proxy fallbacks for FCFF if Cash Flow statement failed
    if base_fcff <= 0:
        if ttm_ebitda > 0:
            base_fcff = ttm_ebitda * 0.60  # Assume 60% EBITDA conversion to FCFF
        elif ttm_net_income > 0:
            base_fcff = ttm_net_income * 1.10 # Net Income + D&A proxy
        else:
            base_fcff = 0.0

    # Ensure net income is aligned with P/E if EPS is reported
    if ttm_net_income <= 0 and "trailingEps" in info and info["trailingEps"] is not None and shares_outstanding > 0:
        ttm_net_income = float(info["trailingEps"]) * shares_outstanding

    # Growth rate estimate (stage 1): default conservative 5%
    growth_rate_stage1 = 0.05
    
    # Cost of debt: default 12% (reflecting average Mexican corporate yield curves)
    cost_of_debt = 0.12
    
    return {
        "prices": prices,
        "volumes": volumes,
        "current_price": current_price,
        "shares_outstanding": shares_outstanding,
        "ttm_net_income": ttm_net_income,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_debt": total_debt,
        "cash_and_equivalents": cash_and_equivalents,
        "ttm_ebitda": ttm_ebitda,
        "annual_dividend_per_share": annual_dividend_rate if annual_dividend_rate < current_price else 0.0,
        "base_fcff": base_fcff,
        "beta": beta,
        "growth_rate_stage1": growth_rate_stage1,
        "tax_rate": 0.30,
        "cost_of_debt": cost_of_debt
    }

def main():
    execution_date = datetime.date.today().strftime("%Y-%m-%d")
    print("=" * 80)
    print(f"STARTING LIVE S&P/BMV IPC VALUE STOCK EVALUATION PIPELINE | DATE: {execution_date}")
    print("=" * 80)

    # Sovereign parameters for WACC
    RISK_FREE_RATE = 0.095          # 9.5% 10-Yr Mbonos
    EQUITY_RISK_PREMIUM = 0.055     # 5.5%
    SOVEREIGN_RISK_PREMIUM = 0.020   # 2.0% EMBI+
    TAX_RATE = 0.30

    liquid_candidates = []
    ticker_to_anon_map = {}
    anon_to_ticker_map = {}
    anon_counter = 1

    print("\n--- PHASE 1: FILTER & STATISTIC COMPUTE (LIVE DATA) ---")
    for ticker in BMV_TICKERS:
        try:
            # 1. Fetch live metrics
            data = fetch_live_metrics(ticker)
            current_price = data["current_price"]
            
            # 2. Calculate 30-day ADTV
            adtv = calculate_adtv(data["prices"], data["volumes"])
            print(f"  |-- Calculated ADTV: {adtv:,.2f} MXN (Price: {current_price:.2f} MXN)")
            
            # 3. Apply Liquidity Gatekeeper
            if not passes_liquidity_gate(adtv, threshold=5000000.0):
                print(f"  +-- [REJECTED] ADTV below 5M MXN threshold. Dropping.")
                continue
            print(f"  |-- [PASSED] Liquidity clearance verified.")
            
            # 4. Check for essential metrics
            if data["shares_outstanding"] <= 0 or data["total_assets"] <= 0:
                print(f"  +-- [REJECTED] Incomplete balance sheet metrics on Yahoo Finance. Dropping.")
                continue
                
            # 5. Calculate ratios
            ratios = calculate_fundamental_ratios(
                current_price=current_price,
                shares_outstanding=data["shares_outstanding"],
                ttm_net_income=data["ttm_net_income"],
                total_assets=data["total_assets"],
                total_liabilities=data["total_liabilities"],
                total_debt=data["total_debt"],
                cash_and_equivalents=data["cash_and_equivalents"],
                ttm_ebitda=data["ttm_ebitda"],
                annual_dividend_per_share=data["annual_dividend_per_share"]
            )
            
            # 6. Calculate WACC
            cost_of_equity = calculate_cost_of_equity(
                risk_free_rate=RISK_FREE_RATE,
                beta=data["beta"],
                equity_risk_premium=EQUITY_RISK_PREMIUM,
                sovereign_risk_premium=SOVEREIGN_RISK_PREMIUM
            )
            wacc = calculate_wacc(
                cost_of_equity=cost_of_equity,
                cost_of_debt=data["cost_of_debt"],
                total_debt=data["total_debt"],
                market_cap=ratios["market_cap"],
                tax_rate=TAX_RATE
            )
            
            # 7. Calculate Baseline DCF Intrinsic Value
            dcf_results = calculate_dcf_intrinsic_value(
                current_price=current_price,
                shares_outstanding=data["shares_outstanding"],
                base_fcff=data["base_fcff"],
                wacc=wacc,
                total_debt=data["total_debt"],
                cash_and_equivalents=data["cash_and_equivalents"],
                growth_rate_stage1=data["growth_rate_stage1"],
                terminal_growth=min(0.035, data["growth_rate_stage1"] * 0.6)
            )
            
            # 8. Anonymize records
            anon_id = f"EQUITY_{chr(64 + anon_counter)}" if anon_counter <= 26 else f"EQUITY_Z{anon_counter}"
            anon_counter += 1
            
            ticker_to_anon_map[ticker] = anon_id
            anon_to_ticker_map[anon_id] = ticker
            
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
                    "shares_outstanding": data["shares_outstanding"],
                    "base_fcff": data["base_fcff"],
                    "wacc": wacc,
                    "total_debt": data["total_debt"],
                    "cash_and_equivalents": data["cash_and_equivalents"],
                    "growth_rate_stage1": data["growth_rate_stage1"],
                    "pre_stress_mos": dcf_results["margin_of_safety"]
                }
            }
            liquid_candidates.append(sanitized_record)
            print(f"  +-- Anonymized {ticker} as {anon_id}. Ratios: P/E: {ratios['pe_ratio'] if ratios['pe_ratio'] is not None else 'N/A' :.1f}x, MOS: {dcf_results['margin_of_safety']*100:.1f}%. Added to Agent queue.")
            
        except Exception as e:
            print(f"  +-- [ERROR] Failed to process {ticker}: {e}")
            continue

    print(f"\nPhase 1 Complete. {len(liquid_candidates)} equities passed to Agent screening.")
    if not liquid_candidates:
        print("No candidates survived Phase 1. Exiting.")
        return

    # Phase 2: Screen (Agent 1)
    print("\n--- PHASE 2: AGENT SCREENING (BLIND EVALUATION) ---")
    screener = FundamentalScreener()
    screened_candidates, _ = screener.screen(liquid_candidates)
    
    # Phase 3: Stress-Test (Agent 2)
    print("\n--- PHASE 3: AGENT STRESS-TESTING (QUALITATIVE DECONSTRUCTION) ---")
    if screened_candidates:
        analyst = MacroRiskAnalyst()
        stressed_candidates = analyst.stress_test(screened_candidates, anon_to_ticker_map)
    else:
        print("No candidates passed the screening phase. Skipping stress testing.")
        stressed_candidates = []
        
    # Phase 4: Reconcile & Export (Agent 3)
    print("\n--- PHASE 4: PORTFOLIO RECONCILIATION & EXPORT ---")
    reconciler = PortfolioReconciler()
    report_markdown = reconciler.reconcile(stressed_candidates, anon_to_ticker_map, execution_date)
    
    # Save Report
    output_filename = "mexican_value_equity_report_live.md"
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_markdown)
        
    print(f"\n[Export] Saved live report to: {output_path}")
    print("\n--- LIVE REPORT OUTPUT ---")
    print(report_markdown)
    print("=" * 80)

if __name__ == "__main__":
    main()
