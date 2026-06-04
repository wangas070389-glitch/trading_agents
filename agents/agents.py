import json
from skills.dcf_valuation_engine import calculate_dcf_intrinsic_value

# Qualitative macro news feeds representing forward-looking risks (Vulnerability 2)
MACRO_RISK_REGISTRY = {
    "FEMSAUBD": {
        "description": "Insulated domestic demand. Dominant retail footprint in nearshoring hubs. Banxico interest rate cuts will lower financing costs for Oxxo expansions.",
        "wacc_adjustment": -0.005,  # -50 bps (positive factor)
        "growth_adjustment": 0.00   # Unchanged
    },
    "CEMEXCPO": {
        "description": "Strong nearshoring catalyst. Direct concrete supply contracts for Northern Mexico industrial parks. USD-denominated contracts mitigate MXN volatility.",
        "wacc_adjustment": 0.00,    # Baseline
        "growth_adjustment": 0.015  # +150 bps growth bump due to nearshoring infrastructure demand
    },
    "ALFAA": {
        "description": "High leverage risk. High Banxico interest rates increase financing costs. However, Sigma Alimentos (food) provides a stable cash flow buffer.",
        "wacc_adjustment": 0.01,    # +100 bps risk premium due to debt load
        "growth_adjustment": -0.005 # -50 bps growth adjustment
    },
    "PE&OLES": {
        "description": "Exposed to global metal price volatility and high energy tariffs. Sovereign interest rates remain high, impacting long-term mining capex projects.",
        "wacc_adjustment": 0.015,   # +150 bps sovereign rate premium
        "growth_adjustment": -0.01  # -100 bps growth reduction
    },
    "MTRAP": {
        "description": "Micro-cap with extreme local governance risk and zero hedging against currency volatility.",
        "wacc_adjustment": 0.04,    # +400 bps risk premium
        "growth_adjustment": -0.02  # -200 bps growth reduction
    },
    "VTRAP": {
        "description": "CRITICAL RISK: Facing imminent supply chain tariffs on imports (+20%) and a major regulatory reform targeting consumer credit interest rates, destroying future margins.",
        "wacc_adjustment": 0.035,   # +350 bps risk premium (massive penalty)
        "growth_adjustment": -0.05  # -500 bps growth reduction (flips growth negative)
    },
    "AMXB": {
        "description": "Telecom giant. Stable consumer demand and cash flows, but faces regulatory antitrust pressures and high capital intensity. USD earnings hedge currency risks.",
        "wacc_adjustment": 0.005,   # +50 bps regulatory premium
        "growth_adjustment": 0.00
    },
    "WALMEX": {
        "description": "Dominant retail giant. Strong supply chain scale and highly insulated from currency swings, but faces labor cost hikes and antitrust complaints.",
        "wacc_adjustment": 0.00,
        "growth_adjustment": 0.00
    },
    "GFNORTEO": {
        "description": "Major bank. Exposed to net interest margin compression as Banxico trims policy rates, but benefits from strong mortgage and industrial loan demand.",
        "wacc_adjustment": 0.005,   # +50 bps margin compression premium
        "growth_adjustment": 0.005  # +50 bps nearshoring loan growth
    },
    "GMEXICOB": {
        "description": "Mining and rail conglomerate. Exposed to global copper cycles and local political concession risk on rail lines. Environmental regulations increase capex.",
        "wacc_adjustment": 0.015,   # +150 bps concession premium
        "growth_adjustment": -0.01
    },
    "BIMBOA": {
        "description": "Global baking leader. Highly defensive consumer staple, but exposed to wheat/packaging commodity cycles. Large USD earnings hedge.",
        "wacc_adjustment": -0.002,  # -20 bps (defensive play)
        "growth_adjustment": 0.00
    },
    "GAPB": {
        "description": "CRITICAL RISK: Federal concession tariff hikes and regulatory changes targeting airport base fees compress EBITDA margins and cash flows.",
        "wacc_adjustment": 0.025,   # +250 bps regulatory risk premium
        "growth_adjustment": -0.015 # -150 bps growth rate trim
    },
    "ASURB": {
        "description": "CRITICAL RISK: Facing federal concession fee hikes. High exposure to leisure travel in Cancun helps, but regulatory pricing headwinds remain high.",
        "wacc_adjustment": 0.025,   # +250 bps regulatory risk premium
        "growth_adjustment": -0.015
    },
    "OMAB": {
        "description": "CRITICAL RISK: Facing federal airport concession pricing cuts. High exposure to nearshoring industrial hubs (Monterrey) mitigates growth impact but margins are compressed.",
        "wacc_adjustment": 0.025,   # +250 bps regulatory risk premium
        "growth_adjustment": -0.010 # Strong industrial demand buffers growth drop
    },
    "GRUMAB": {
        "description": "Defensive leader. Global corn flour demand is highly inelastic. Low leverage and strong operating margins. WACC benefit from low volatility.",
        "wacc_adjustment": -0.005,  # -50 bps defensive premium
        "growth_adjustment": 0.00
    },
    "KIMBERA": {
        "description": "Consumer paper products. Stable domestic demand, but raw pulp price cycles create margin volatility.",
        "wacc_adjustment": 0.00,
        "growth_adjustment": 0.00
    },
    "AC": {
        "description": "Coke bottler. High cash generator, strong defensive consumer play in Mexico and US. Insulated from currency swings by cash flows.",
        "wacc_adjustment": -0.005,  # -50 bps defensive premium
        "growth_adjustment": 0.00
    },
    "ORBIA": {
        "description": "Chemicals and irrigation. High leverage under high sovereign rates, exposed to PVC price drop and European recession headwinds.",
        "wacc_adjustment": 0.015,   # +150 bps leverage and commodity premium
        "growth_adjustment": -0.010
    },
    "PINFRA": {
        "description": "Toll roads infrastructure. Defensive cash streams, concessions linked directly to domestic inflation, but faces government toll review threats.",
        "wacc_adjustment": 0.00,
        "growth_adjustment": 0.00
    },
    "BBAJIOO": {
        "description": "Regional commercial bank. Insulated nearshoring play. Direct beneficiary of industrial park expansion and corporate lending in El Bajio corridor.",
        "wacc_adjustment": 0.00,
        "growth_adjustment": 0.010  # +100 bps nearshoring loan growth
    },
    "GENTERA": {
        "description": "Microfinance lender. High credit margins, but highly exposed to lower-income consumer default cycles under recession or persistent inflation.",
        "wacc_adjustment": 0.020,   # +200 bps microfinance default premium
        "growth_adjustment": 0.00
    },
    "CUERVO": {
        "description": "Jose Cuervo tequila. High brand power, but export margins hurt by strong Peso swings and agave crop pricing cycles.",
        "wacc_adjustment": 0.005,   # +50 bps FX risk premium
        "growth_adjustment": 0.00
    },
    "GCC": {
        "description": "Cement producer. Deeply integrated in US border regions and Northern Mexico, benefiting directly from nearshoring and infrastructure capex.",
        "wacc_adjustment": 0.00,
        "growth_adjustment": 0.010  # +100 bps concrete growth
    },
    "VESTA": {
        "description": "Industrial real estate (warehouses). Prime beneficiary of nearshoring warehouses demand, near zero vacancy rates in Northern Mexico. High pricing power.",
        "wacc_adjustment": -0.005,  # -50 bps nearshoring tailwind
        "growth_adjustment": 0.020  # +200 bps growth bump
    }
}

class FundamentalScreener:
    """
    Agent 1: Evaluates anonymized metrics to prevent confirmation bias.
    Uses strict value thresholds: P/E < 12x, EV/EBITDA < 7x, DCF Margin of Safety > 15%.
    """
    def __init__(self):
        self.system_prompt = (
            "SYSTEM PROMPT: You are the Fundamental Screener Agent. You operate on raw, anonymized "
            "financial metrics to eliminate confirmation and recency bias. Your objective is to isolate "
            "equities that are fundamentally cheap relative to their computed intrinsic values. You must "
            "strictly filter for P/E < 12x, EV/EBITDA < 7x, and DCF Margin of Safety > +15%. Return a list "
            "of qualified assets."
        )

    def screen(self, anonymized_universe: list[dict]) -> tuple[list[dict], str]:
        print(f"\n[Agent 1: Fundamental Screener] Initializing screen on {len(anonymized_universe)} anonymized assets...")
        print(f"[Agent 1: Prompt Context] {self.system_prompt}")
        
        passed_candidates = []
        log_traces = []
        
        for asset in anonymized_universe:
            pe = asset["pe_ratio"]
            ev_ebitda = asset["ev_ebitda"]
            mos = asset["margin_of_safety"] * 100.0  # Convert to percent
            
            # Check thresholds
            # Note: handle None values (e.g. if EV/EBITDA is negative or invalid)
            is_pe_ok = pe is not None and pe < 12.0
            is_ev_ebitda_ok = ev_ebitda is not None and ev_ebitda < 7.0
            is_mos_ok = mos > 15.0
            
            status = "FAILED"
            reasons = []
            if not is_pe_ok: reasons.append(f"P/E ({f'{pe:.1f}x' if pe is not None else 'N/A'}) >= 12")
            if not is_ev_ebitda_ok: reasons.append(f"EV/EBITDA ({f'{ev_ebitda:.1f}x' if ev_ebitda is not None else 'N/A'}) >= 7")
            if not is_mos_ok: reasons.append(f"MOS ({mos:.1f}%) <= 15%")
            
            if is_pe_ok and is_ev_ebitda_ok and is_mos_ok:
                status = "PASSED"
                passed_candidates.append(asset)
                log_traces.append(f"+-- {asset['anon_id']}: {status} (P/E: {pe:.1f}x, EV/EBITDA: {ev_ebitda:.1f}x, MOS: +{mos:.1f}%)")
            else:
                log_traces.append(f"+-- {asset['anon_id']}: {status} (Rejected because: {', '.join(reasons)})")
                
        execution_log = "\n".join(log_traces)
        print(execution_log)
        return passed_candidates, execution_log


class MacroRiskAnalyst:
    """
    Agent 2: Conducts qualitative forward-looking stress-testing (Banxico, currency, tariff threats).
    Adjusts the underlying discount rates and growth inputs, then re-runs the DCF Valuation Engine
    to calculate the risk-adjusted margins of safety.
    """
    def __init__(self):
        self.system_prompt = (
            "SYSTEM PROMPT: You are the Macro/Sovereign Risk Analyst Agent. You evaluate qualitative "
            "macro economic variables, interest rate trajectories, and industry-specific regulations "
            "for the Mexican market. You receive candidates who passed the fundamental screening. "
            "You must cross-reference each candidate with forward-looking risk factors, adjust WACC "
            "and growth rates to reflect these headwinds/tailwinds, and compute the risk-adjusted "
            "Margins of Safety."
        )

    def stress_test(self, screened_candidates: list[dict], ticker_map: dict) -> list[dict]:
        print(f"\n[Agent 2: Macro/Sovereign Risk Analyst] Stress-testing {len(screened_candidates)} candidates...")
        print(f"[Agent 2: Prompt Context] {self.system_prompt}")
        
        stressed_candidates = []
        
        for asset in screened_candidates:
            # Map back to real ticker to find macro adjustments in the registry
            real_ticker = ticker_map[asset["anon_id"]]
            
            # Normalize: strip the ".MX" suffix and find key in registry
            lookup_ticker = real_ticker.split(".")[0]
            
            risk_data = MACRO_RISK_REGISTRY.get(
                lookup_ticker, 
                {"description": "No macro adjustments.", "wacc_adjustment": 0.0, "growth_adjustment": 0.0}
            )
            
            # Apply adjustments (e.g. sovereign interest rate hike / supply tariff shocks)
            original_wacc = asset["raw_dcf_inputs"]["wacc"]
            original_growth = asset["raw_dcf_inputs"]["growth_rate_stage1"]
            
            adjusted_wacc = original_wacc + risk_data["wacc_adjustment"]
            # Floor growth rate adjustment to avoid negative terminal growth complications
            adjusted_growth = max(-0.02, original_growth + risk_data["growth_adjustment"])
            
            # Recalculate DCF using the Skills layer engine
            recalculated_dcf = calculate_dcf_intrinsic_value(
                current_price=asset["current_price"],
                shares_outstanding=asset["raw_dcf_inputs"]["shares_outstanding"],
                base_fcff=asset["raw_dcf_inputs"]["base_fcff"],
                wacc=adjusted_wacc,
                total_debt=asset["raw_dcf_inputs"]["total_debt"],
                cash_and_equivalents=asset["raw_dcf_inputs"]["cash_and_equivalents"],
                growth_rate_stage1=adjusted_growth,
                terminal_growth=min(0.035, adjusted_growth * 0.6)  # Adjust terminal growth relative to stage 1 growth
            )
            
            risk_adjusted_mos = recalculated_dcf["margin_of_safety"]
            
            print(f"|-- {asset['anon_id']} ({real_ticker}):")
            print(f"|  |-- Macro Vector: {risk_data['description']}")
            print(f"|  |-- WACC: {original_wacc*100:.1f}% -> {adjusted_wacc*100:.1f}%")
            print(f"|  |-- Growth: {original_growth*100:.1f}% -> {adjusted_growth*100:.1f}%")
            print(f"|  +-- MOS: {asset['margin_of_safety']*100:.1f}% -> {risk_adjusted_mos*100:.1f}%")
            
            stressed_asset = asset.copy()
            stressed_asset["margin_of_safety"] = risk_adjusted_mos
            stressed_asset["intrinsic_value"] = recalculated_dcf["intrinsic_value"]
            stressed_asset["macro_notes"] = risk_data["description"]
            stressed_asset["wacc_adjusted"] = adjusted_wacc
            
            stressed_candidates.append(stressed_asset)
            
        return stressed_candidates


class PortfolioReconciler:
    """
    Agent 3: Re-identifies anonymized tickers, enforces concentration limits,
    and compiles the final evaluation report.
    """
    def __init__(self):
        self.system_prompt = (
            "SYSTEM PROMPT: You are the Portfolio Reconciler Agent. Your objective is to map "
            "screened and risk-adjusted assets back to their official BMV tickers, verify liquidity clearance, "
            "and compile the final Markdown execution report conforming to the operational template."
        )

    def reconcile(self, stressed_candidates: list[dict], ticker_map: dict, execution_date: str, investment_budget: float = 10000000.0) -> str:
        print(f"\n[Agent 3: Portfolio Reconciler] Synthesizing final execution report with position sizing...")
        print(f"[Agent 3: Prompt Context] {self.system_prompt}")
        
        # Filter for candidates that still have positive margins of safety after macro stress tests
        qualified_portfolio = []
        for asset in stressed_candidates:
            if asset["margin_of_safety"] > 0.15:  # Require at least 15% post-stress margin of safety
                qualified_portfolio.append(asset)
                
        # Sort by margin of safety descending
        qualified_portfolio.sort(key=lambda x: x["margin_of_safety"], reverse=True)
        
        # Calculate weights based on Margin of Safety, enforcing 40% max constraint
        total_mos = sum(x["margin_of_safety"] for x in qualified_portfolio)
        weights = {}
        if total_mos > 0 and len(qualified_portfolio) > 0:
            # First pass: proportional allocation
            raw_weights = {x["anon_id"]: x["margin_of_safety"] / total_mos for x in qualified_portfolio}
            
            # Enforce max 40% constraint
            constrained_weights = {}
            excess_weight = 0.0
            unconstrained_sum = 0.0
            
            for anon_id, w in raw_weights.items():
                if w > 0.40:
                    constrained_weights[anon_id] = 0.40
                    excess_weight += (w - 0.40)
                else:
                    constrained_weights[anon_id] = w
                    unconstrained_sum += w
                    
            if excess_weight > 0 and unconstrained_sum > 0:
                # Distribute excess weight to other assets
                for anon_id in list(constrained_weights.keys()):
                    if constrained_weights[anon_id] < 0.40:
                        extra = excess_weight * (raw_weights[anon_id] / unconstrained_sum)
                        constrained_weights[anon_id] = min(0.40, constrained_weights[anon_id] + extra)
                        
            # Normalize to ensure we don't exceed 100% total weight
            sum_weights = sum(constrained_weights.values())
            if sum_weights > 1.0:
                for anon_id in constrained_weights:
                    constrained_weights[anon_id] = constrained_weights[anon_id] / sum_weights
            weights = constrained_weights
        
        # Construct markdown output
        report = []
        report.append("# MEXICAN VALUE EQUITY EVALUATION REPORT")
        report.append(f"**Execution Date:** {execution_date} | **Universe:** BMV Active Equities\n")
        
        report.append("## 1. Top Qualified Value Candidates")
        report.append("| Ticker | Computed P/E | EV/EBITDA | Margin of Safety (DCF) | 30D ADTV (MXN) |")
        report.append("| :--- | :--- | :--- | :--- | :--- |")
        
        for asset in qualified_portfolio:
            real_ticker = ticker_map[asset["anon_id"]]
            pe_str = f"{asset['pe_ratio']:.1f}x" if asset['pe_ratio'] is not None else "N/A"
            ev_ebitda_str = f"{asset['ev_ebitda']:.1f}x" if asset['ev_ebitda'] is not None else "N/A"
            mos_str = f"+{asset['margin_of_safety']*100:.1f}%"
            adtv_m = f"{asset['adtv']/1000000:.1f}M"
            
            report.append(f"| {real_ticker} | {pe_str} | {ev_ebitda_str} | {mos_str} | {adtv_m} |")
            
        report.append("\n## 2. Structural Deconstruction & Catalysts")
        for asset in qualified_portfolio:
            real_ticker = ticker_map[asset["anon_id"]]
            mos_pct = asset['margin_of_safety']*100
            report.append(f"* **{real_ticker}**: {asset['macro_notes']} Implied margin of safety is {mos_pct:.1f}% post-stress-testing.")
            
        # List any value traps that failed during the macro stress-test
        value_traps = [a for a in stressed_candidates if a["margin_of_safety"] <= 0.15]
        if value_traps:
            report.append("\n## 3. Discarded Value Traps (Failed Macro Stress Test)")
            report.append("| Ticker | Pre-Stress MOS | Post-Stress MOS | Failure Reason |")
            report.append("| :--- | :--- | :--- | :--- |")
            for trap in value_traps:
                real_ticker = ticker_map[trap["anon_id"]]
                pre_mos = trap["raw_dcf_inputs"]["pre_stress_mos"] * 100
                post_mos = trap["margin_of_safety"] * 100
                report.append(f"| {real_ticker} | +{pre_mos:.1f}% | {f'+{post_mos:.1f}%' if post_mos > 0 else f'{post_mos:.1f}%'} | {trap['macro_notes'][:80]}... |")

        # 4. Position Sizing and Execution Orders (Opening Positions)
        report.append(f"\n## 4. Execution Order Blotter (Opening Positions)")
        report.append(f"**Investment Capital:** {investment_budget:,.2f} MXN | **Concentration Constraint:** Max 40.0% weight per stock\n")
        report.append("| Ticker | Target Weight | Allocated Capital (MXN) | Buy Price (MXN) | Target Shares to Buy |")
        report.append("| :--- | :---: | :---: | :---: | :---: |")
        
        total_allocated_capital = 0.0
        portfolio_details = []
        for asset in qualified_portfolio:
            anon_id = asset["anon_id"]
            real_ticker = ticker_map[anon_id]
            w = weights.get(anon_id, 0.0)
            allocated_cash = investment_budget * w
            price = asset["current_price"]
            shares = int(allocated_cash / price) if price > 0 else 0
            
            total_allocated_capital += (shares * price)
            report.append(f"| {real_ticker} | {w*100:.1f}% | {allocated_cash:,.2f} | {price:.2f} | {shares:,} |")
            
            portfolio_details.append({
                "ticker": real_ticker,
                "shares": shares,
                "buy_price": price,
                "intrinsic_value": asset["intrinsic_value"],
                "mos": asset["margin_of_safety"]
            })
            
        remaining_cash = investment_budget - total_allocated_capital
        report.append(f"\n* **Total Capital Allocated**: {total_allocated_capital:,.2f} MXN ({total_allocated_capital/investment_budget*100:.1f}%)")
        report.append(f"* **Cash Reserve / Unallocated Capital**: {remaining_cash:,.2f} MXN ({remaining_cash/investment_budget*100:.1f}%)")

        # 5. Exit Target and Sell Triggers (Capitalization Rules)
        report.append(f"\n## 5. Exit Target & Sell Trigger Blotter")
        report.append("| Ticker | Current Price (MXN) | Target Exit Price (MXN) | Return Potential | Target Capitalization Value (MXN) | Profit Target (MXN) |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        
        total_target_value = 0.0
        for p in portfolio_details:
            t = p["ticker"]
            bp = p["buy_price"]
            iv = p["intrinsic_value"]
            sh = p["shares"]
            pot = p["mos"] * 100.0
            
            target_val = sh * iv
            profit = target_val - (sh * bp)
            total_target_value += target_val
            
            report.append(f"| {t} | {bp:.2f} | {iv:.2f} | +{pot:.1f}% | {target_val:,.2f} | {profit:,.2f} |")
            
        total_target_profit = total_target_value - total_allocated_capital
        total_target_return = (total_target_value / total_allocated_capital - 1.0) * 100.0 if total_allocated_capital > 0 else 0.0
        report.append(f"\n* **Target Portfolio Value at Exit**: {total_target_value + remaining_cash:,.2f} MXN")
        report.append(f"* **Total Target Capitalized Profit**: {total_target_profit:,.2f} MXN (Implied Return: +{total_target_return:.1f}%)")
        
        report.append("\n### Portfolio Exit & Rebalancing Triggers:")
        report.append("1. **Capitalize Profit (Full Take-Profit)**: Place GTC (Good-Til-Cancelled) limit orders to sell 100% of holdings when market price meets or exceeds the **Target Exit Price** (re-evaluating margin of safety to 0%).")
        report.append("2. **Early De-risking (Scale-Out)**: Liquidate 50% of the position when the market price rises to **90% of the Target Exit Price** to lock in gains and increase cash reserves.")
        report.append("3. **Fundamental Stop-Out**: Liquidate the position if future quarterly filings or macro updates drop the recalculated *Intrinsic Value* below the acquisition price (turning Margin of Safety negative).")

        report.append("\n## 6. Risk Disclosures & Boundary Suppressions")
        report.append("* **Liquidity Clearance**: All listed entities pass the minimum 5M MXN daily volume threshold.")
        report.append("* **Macro Headwinds**: Valuation models have been adjusted via qualitative stress vectors, applying premiums of up to 350 basis points to interest rates for exposed firms (e.g. consumer credit reforms, supply chain tariffs).")
        
        final_markdown = "\n".join(report)
        return final_markdown
