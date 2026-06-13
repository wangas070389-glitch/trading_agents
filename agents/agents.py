import os
import json
import datetime
import numpy as np
import pandas as pd
from hmmlearn import hmm
from arch import arch_model

# Qualitative macro news feeds representing forward-looking risks
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
    },
    "NVDA": {
        "description": "Global AI chip leader. Strong growth catalyst from hyperscaler capex, but high volatility and exposure to international export restrictions.",
        "wacc_adjustment": 0.005,  # +50 bps regulatory/valuation risk premium
        "growth_adjustment": 0.015 # +150 bps growth rate bump due to AI demand
    },
    "AAPL": {
        "description": "Consumer hardware giant. Highly stable premium pricing cash flows, but faces antitrust lawsuits and longer smartphone replacement cycles.",
        "wacc_adjustment": 0.00,   # Baseline risk
        "growth_adjustment": 0.00  # Baseline growth
    },
    "MSFT": {
        "description": "Enterprise software and cloud infrastructure leader. Solid recurring SaaS revenues, defensive positioning with low leverage.",
        "wacc_adjustment": -0.002, # -20 bps (defensive play)
        "growth_adjustment": 0.005  # +50 bps growth adjustment from AI integration
    },
    "AMZN": {
        "description": "E-commerce and cloud (AWS) giant. Exposed to consumer spending cycles, but AWS margins provide substantial cash flow buffer.",
        "wacc_adjustment": 0.002,  # +20 bps
        "growth_adjustment": 0.00
    },
    "GOOGL": {
        "description": "Search and digital ads leader. Highly cash-generative search monopoly, but faces regulatory antitrust breaking-up risks.",
        "wacc_adjustment": 0.005,  # +50 bps antitrust premium
        "growth_adjustment": -0.005 # -50 bps growth drag from antitrust pressure
    }
}

class FundamentalScreener:
    """
    Agent 1: Runs the quantitative V3 model on historical prices and volumes.
    Computes daily returns, standardizes returns via GARCH(1,1), fits a Multivariate HMM 
    with SPY and USD/MXN returns, and calculates second-order Markov transition probabilities (DCS).
    """
    def __init__(self):
        self.system_prompt = (
            "SYSTEM PROMPT: You are the Quantitative Screener Agent (V3). Your objective is to run "
            "advanced mathematical models (GARCH(1,1), Multivariate HMM, 2nd-Order Markov transitions) "
            "to extract volatility and trend signals (DCS) for each BMV stock relative to global macro drivers."
        )

    def calcular_retornos_estandarizados_garch(self, precios):
        # Calculate daily log returns
        retornos = np.log(precios / np.roll(precios, 1))
        retornos[0] = 0.0
        
        # Fit GARCH(1,1) model
        # NOTE: `show_warning` is NOT a valid kwarg of arch_model() (it belongs to .fit()).
        # The previous code raised TypeError on every call, silently forcing the
        # rolling-std fallback for ALL tickers — GARCH never actually ran.
        try:
            am = arch_model(retornos * 100, vol='Garch', p=1, q=1, dist='Normal')
            res = am.fit(update_freq=0, disp='off', show_warning=False)
            vol_condicional = np.asarray(res.conditional_volatility) / 100
            # Guard against zero/NaN conditional volatility
            vol_condicional = np.where(
                np.isfinite(vol_condicional) & (vol_condicional > 1e-8),
                vol_condicional, 0.015
            )
            retornos_estandarizados = retornos / vol_condicional
        except Exception as e:
            # Fallback to rolling standard deviation if GARCH fitting fails
            print(f"  [GARCH Fallback] Falling back to rolling volatility for calculations: {e}")
            rolling_vol = pd.Series(retornos).rolling(20, min_periods=1).std().fillna(0.015).values
            # Ensure no divide by zero
            rolling_vol = np.where(rolling_vol == 0, 0.015, rolling_vol)
            vol_condicional = rolling_vol
            retornos_estandarizados = retornos / vol_condicional
            
        return retornos, retornos_estandarizados, vol_condicional

    def entrenar_hmm_multivariado(self, retornos_asset, exogenos):
        obs = np.column_stack([retornos_asset, exogenos])
        model_hmm = None
        try:
            model_hmm = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
            model_hmm.fit(obs)
            estados_inferidos = model_hmm.predict(obs)
            
            # Map states: argmin of means (Bear), argmax (Bull), others (Sideways)
            means = model_hmm.means_[:, 0]
            mapa_estados = {np.argmin(means): -1, np.argmax(means): 1}
            for idx in range(3):
                if idx not in mapa_estados:
                    mapa_estados[idx] = 0
            
            estados_mapeados = np.array([mapa_estados[e] for e in estados_inferidos])
        except Exception as e:
            # Fallback: simple sign classification of asset returns
            print(f"  [HMM Fallback] Classifying states based on returns: {e}")
            estados_mapeados = np.zeros(len(retornos_asset), dtype=int)
            for i in range(len(retornos_asset)):
                val = retornos_asset[i]
                if val > 0.004:
                    estados_mapeados[i] = 1
                elif val < -0.004:
                    estados_mapeados[i] = -1
            
        return estados_mapeados, model_hmm

    def calcular_matriz_markov_segundo_orden(self, estados):
        mapa_llaves = {
            (1,1):0, (1,0):1, (1,-1):2, 
            (0,1):3, (0,0):4, (0,-1):5, 
            (-1,1):6, (-1,0):7, (-1,-1):8
        }
        matriz_conteo = np.zeros((9, 3)) # 9 combinations of origin, 3 of destination [1, 0, -1]
        
        for t in range(len(estados) - 2):
            estado_ant = estados[t]
            estado_act = estados[t+1]
            estado_sig = estados[t+2]
            
            key = (estado_ant, estado_act)
            if key in mapa_llaves:
                fila_idx = mapa_llaves[key]
                col_idx = 1 if estado_sig == 0 else (0 if estado_sig == 1 else 2)
                matriz_conteo[fila_idx, col_idx] += 1
                
        # Laplace smoothing (+1) and normalization
        matriz_suavizada = matriz_conteo + 1
        matriz_transicion_2da = matriz_suavizada / matriz_suavizada.sum(axis=1, keepdims=True)
        return matriz_transicion_2da, mapa_llaves

    def screen(self, universe_data: dict) -> dict:
        print(f"\n[Agent 1: Quantitative Screener] Screening {len(universe_data)} assets in the universe...")
        
        quantitative_results = {}
        for ticker, data in universe_data.items():
            try:
                precios = np.array(data["prices"])
                volumenes = np.array(data["volumes"])
                exogenos = np.array(data["exogenous"])
                
                # Check data length
                if len(precios) < 20:
                    print(f"  |-- {ticker}: Skipping (insufficient price history: {len(precios)} days)")
                    continue
                
                # 1. GARCH Modeling
                ret, ret_est, vol_cond = self.calcular_retornos_estandarizados_garch(precios)
                garch_vol_final = vol_cond[-1]
                
                # 2. HMM State Inference and DCS v2 calculation
                estados_hist, model_hmm = self.entrenar_hmm_multivariado(ret_est, exogenos)
                
                dcs = None
                current_state = None
                
                if model_hmm is not None:
                    try:
                        obs = np.column_stack([ret_est, exogenos])
                        gamma_T = model_hmm.predict_proba(obs)[-1]
                        pi_next = gamma_T @ model_hmm.transmat_
                        mu = model_hmm.means_[:, 0]
                        e_ret = pi_next @ mu
                        
                        # Normalize expected return to [-1, 1]
                        max_mu = max(abs(mu.min()), abs(mu.max()))
                        dcs = e_ret / max_mu if max_mu > 0 else 0.0
                        
                        # Map argmax of gamma_T to regime label mapped through means
                        bear_idx = np.argmin(mu)
                        bull_idx = np.argmax(mu)
                        sideways_idx = [idx for idx in range(3) if idx not in (bear_idx, bull_idx)][0]
                        mapa_estados = {bear_idx: -1, bull_idx: 1, sideways_idx: 0}
                        current_state = int(mapa_estados[np.argmax(gamma_T)])
                    except Exception as inference_error:
                        print(f"  [HMM Inference Fallback] Inference failed for {ticker}: {inference_error}")
                        model_hmm = None
                        
                if model_hmm is None:
                    # Fallback path (mean of last 10 standardized returns)
                    dcs = float(np.clip(np.mean(ret_est[-10:]), -1.0, 1.0))
                    current_state = int(estados_hist[-1])
                
                # 4. Volume Confirmation (Relative Volume)
                vr = volumenes[-1] / np.mean(volumenes[-20:])
                
                quantitative_results[ticker] = {
                    "dcs": float(dcs),
                    "garch_vol": float(garch_vol_final),
                    "relative_vol": float(vr),
                    "hmm_state": int(current_state),
                    "current_price": float(precios[-1])
                }
                
                print(f"  +-- {ticker}: DCS={dcs:.4f} | VR={vr:.2f} | Vol={garch_vol_final:.4f} | HMM State={current_state}")
                
            except Exception as e:
                print(f"  |-- [ERROR] Failed to run quantitative screening for {ticker}: {e}")
                continue
                
        return quantitative_results


class MacroRiskAnalyst:
    """
    Agent 2: Adjusts quantitative metrics based on the qualitative macro risk factors.
    - Scales up the volatility for high-risk assets (reducing allocation).
    - Modifies DCS strength based on positive/negative growth catalysts.
    """
    def __init__(self):
        self.system_prompt = (
            "SYSTEM PROMPT: You are the Macro Risk Analyst Agent (V3). Your objective is to adjust "
            "quantitative screener outputs (DCS and GARCH Volatility) based on macro-specific tailwinds or regulatory headwinds."
        )

    def stress_test(self, quantitative_metrics: dict, ticker_map: dict) -> dict:
        print(f"\n[Agent 2: Macro/Sovereign Risk Analyst] Refining signals with qualitative risk factors...")
        
        adjusted_metrics = {}
        for ticker, metrics in quantitative_metrics.items():
            lookup_ticker = ticker.split(".")[0]
            
            risk_data = MACRO_RISK_REGISTRY.get(
                lookup_ticker, 
                {"description": "No macro adjustments.", "wacc_adjustment": 0.0, "growth_adjustment": 0.0}
            )
            
            garch_vol = metrics["garch_vol"]
            dcs = metrics["dcs"]
            
            # Volatility risk adjustment: scale up by risk factors (e.g. +1% WACC scales vol up by 5%)
            adjusted_vol = garch_vol * (1.0 + risk_data["wacc_adjustment"] * 5.0)
            
            # Signal strength adjustment (growth bump/penalty)
            adjusted_dcs = np.clip(dcs + risk_data["growth_adjustment"], -1.0, 1.0)
            
            adjusted_metrics[ticker] = {
                **metrics,
                "garch_vol_adjusted": float(adjusted_vol),
                "dcs_adjusted": float(adjusted_dcs),
                "macro_description": risk_data["description"],
                "wacc_adjustment": risk_data["wacc_adjustment"],
                "growth_adjustment": risk_data["growth_adjustment"]
            }
            
            if risk_data["wacc_adjustment"] != 0.0 or risk_data["growth_adjustment"] != 0.0:
                print(f"  |-- {ticker}: Adjusted DCS {dcs:.4f} -> {adjusted_dcs:.4f} | Vol {garch_vol:.4f} -> {adjusted_vol:.4f} ({risk_data['description']})")
                
        return adjusted_metrics


class PortfolioReconciler:
    """
    Agent 3: Rebalances the portfolio based on Black-Litterman weights and generates the execution report.
    - Filters by DCS >= 0.25 and VR >= 1.2
    - Performs inverse-volatility weighting scaled by the DCS strength
    - Enforces 40% concentration limit
    - Computes buying/selling transactions to adjust to target holdings
    - Deducts 0.29% transaction fees on all operations
    - Automatically routes cash to Bondia
    """
    def __init__(self):
        self.system_prompt = (
            "SYSTEM PROMPT: You are the Portfolio Reconciler Agent (V3). Your objective is to run "
            "Black-Litterman optimization, compute trade rebalancing vectors, apply execution friction "
            "costs, and draft the final production report."
        )

    def reconcile(self, adjusted_metrics: dict, portfolio: dict, execution_date: str,
                  learning_context: dict = None) -> tuple[dict, str, list]:
        print(f"\n[Agent 3: Portfolio Reconciler] Starting portfolio reconciliation and optimization...")

        # Adaptive learning context (all optional, safe defaults = old behavior)
        ctx = learning_context or {}
        umbral_histeresis_entrada = ctx.get("dcs_threshold", 0.25)
        umbral_vr = ctx.get("vr_threshold", 1.2)
        confidence = ctx.get("confidence", {})          # ticker -> multiplier
        exposure_scalar = ctx.get("exposure_scalar", 1.0)
        if exposure_scalar < 1.0:
            print(f"  |-- [Drawdown Governor] Gross exposure scaled to {exposure_scalar:.0%} "
                  f"(strategy drawdown brake active).")

        # 1. Determine active eligible assets based on (learned) threshold rules with hysteresis
        activos_elegibles = []
        currently_held = {h["ticker"] for h in portfolio.get("holdings", []) if h.get("shares", 0) > 0}
        umbral_histeresis_salida = ctx.get("dcs_threshold_out", umbral_histeresis_entrada - 0.10)

        for t, met in adjusted_metrics.items():
            required_dcs = umbral_histeresis_salida if t in currently_held else umbral_histeresis_entrada
            if met["dcs_adjusted"] >= required_dcs and met["relative_vol"] >= umbral_vr:
                activos_elegibles.append(t)
                
        print(f"  |-- Eligible assets for long positions: {activos_elegibles}")
        
        # 2. Black-Litterman Sizing
        pesos_asignados = {}
        if len(activos_elegibles) == 0:
            print("  |-- No assets met the eligibility thresholds. Portfolio will hold 100% Cash.")
            for t in adjusted_metrics:
                pesos_asignados[t] = 0.0
        else:
            # Inverse volatility weights
            inv_vol = {t: 1.0 / adjusted_metrics[t]["garch_vol_adjusted"] for t in activos_elegibles}
            suma_inv_vol = sum(inv_vol.values())
            
            # Raw weights scaled by DCS view strength, then by the learned
            # confidence multiplier for this signal bucket (1.0 = no evidence
            # yet), then by the drawdown-governor exposure scalar.
            raw_weights = {}
            for t in activos_elegibles:
                mult = confidence.get(t, 1.0)
                raw_weights[t] = (inv_vol[t] / suma_inv_vol) * adjusted_metrics[t]["dcs_adjusted"] * mult * exposure_scalar
                if mult != 1.0:
                    print(f"  |-- [Learned Confidence] {t}: weight x{mult:.2f} "
                          f"(historical bucket expectancy)")
                
            # Enforce 40% concentration limit (and redistribute excess)
            final_weights = {}
            excess = 0.0
            under_cap_sum = 0.0
            
            for t, w in raw_weights.items():
                if w > 0.40:
                    final_weights[t] = 0.40
                    excess += (w - 0.40)
                else:
                    final_weights[t] = w
                    under_cap_sum += w
                    
            if excess > 0 and under_cap_sum > 0:
                for t in list(final_weights.keys()):
                    if final_weights[t] < 0.40:
                        share = raw_weights[t] / under_cap_sum
                        extra = excess * share
                        final_weights[t] = min(0.40, final_weights[t] + extra)
                        
            # Set final optimized weights
            for t in adjusted_metrics:
                pesos_asignados[t] = final_weights.get(t, 0.0)
                
        # 3. Calculate portfolio value and execute trades
        cash = portfolio["cash_balance"]
        holdings = {h["ticker"]: h for h in portfolio["holdings"]}
        total_capital = portfolio["total_capital"]
        
        # Compute current value of holdings
        holdings_value = 0.0
        for ticker, h in holdings.items():
            current_price = adjusted_metrics.get(ticker, {}).get("current_price", h["last_price"])
            holdings_value += h["shares"] * current_price
            
        total_value = cash + holdings_value
        print(f"  |-- Portfolio Value: {total_value:,.2f} MXN (Cash: {cash:,.2f} MXN, Stocks: {holdings_value:,.2f} MXN)")
        
        # Target shares and rebalancing trade vector
        rebalancing_trades = []
        costo_corretaje = 0.0029 # 0.29% fee
        
        # First Phase: Execute Sells (frees up cash)
        new_holdings_dict = {}
        cash_after_sells = cash

        # BUGFIX: previously, any held ticker missing from adjusted_metrics
        # (yfinance failure, liquidity gate rejection, screening error) simply
        # vanished from the new portfolio — no SELL was logged and no cash was
        # credited. The position's value evaporated from portfolio.json.
        # Data unavailability is NOT a sell signal: carry the position at its
        # last known price and flag it for review.
        for ticker, h in holdings.items():
            if ticker not in adjusted_metrics:
                print(f"  +-- [WARN] {ticker} held but absent from today's metrics. "
                      f"Carrying position at last price {h['last_price']:.2f} (review manually).")
                new_holdings_dict[ticker] = {**h, "target_weight": h.get("target_weight", 0.0)}

        for ticker, peso in pesos_asignados.items():
            current_price = adjusted_metrics[ticker]["current_price"]
            monto_teorico = total_value * peso
            target_shares = int(monto_teorico // current_price)
            
            current_shares = holdings.get(ticker, {}).get("shares", 0)
            
            if current_shares > target_shares:
                # Execute Sell
                shares_to_sell = current_shares - target_shares
                revenue = shares_to_sell * current_price
                fee = revenue * costo_corretaje
                net_revenue = revenue - fee
                cash_after_sells += net_revenue
                
                note = f"V3 Dynamic Rebalance (Target Weight: {peso:.1%}, DCS: {adjusted_metrics[ticker]['dcs_adjusted']:.2f})"
                rebalancing_trades.append({
                    "ticker": ticker,
                    "action": "SELL",
                    "shares": shares_to_sell,
                    "price": current_price,
                    "fee": fee,
                    "net_cash": net_revenue,
                    "note": note
                })
                print(f"  +-- [SELL] {ticker}: {shares_to_sell} shares @ {current_price:.2f} (Net: +{net_revenue:,.2f} MXN)")
                
                if target_shares > 0:
                    new_holdings_dict[ticker] = {
                        "ticker": ticker,
                        "shares": target_shares,
                        "buy_price": holdings[ticker]["buy_price"], # cost basis remains unchanged on sell
                        "last_price": current_price,
                        "target_weight": peso,
                        "dcs": adjusted_metrics[ticker]["dcs_adjusted"],
                        "garch_vol": adjusted_metrics[ticker]["garch_vol_adjusted"],
                        "hmm_state": adjusted_metrics[ticker]["hmm_state"],
                        "vol_relative": adjusted_metrics[ticker]["relative_vol"]
                    }
            elif current_shares > 0 and current_shares == target_shares:
                # Keep holding
                new_holdings_dict[ticker] = {
                    "ticker": ticker,
                    "shares": current_shares,
                    "buy_price": holdings[ticker]["buy_price"],
                    "last_price": current_price,
                    "target_weight": peso,
                    "dcs": adjusted_metrics[ticker]["dcs_adjusted"],
                    "garch_vol": adjusted_metrics[ticker]["garch_vol_adjusted"],
                    "hmm_state": adjusted_metrics[ticker]["hmm_state"],
                    "vol_relative": adjusted_metrics[ticker]["relative_vol"]
                }
                
        # Second Phase: Execute Buys
        # BUGFIX: dict order is insertion order (ingestion order), so when cash ran
        # out, low-conviction names ingested earlier got filled while the strongest
        # signals were scaled down. Fill highest adjusted DCS first.
        cash_after_buys = cash_after_sells
        buy_order = sorted(
            pesos_asignados.keys(),
            key=lambda t: adjusted_metrics[t]["dcs_adjusted"],
            reverse=True
        )
        for ticker in buy_order:
            peso = pesos_asignados[ticker]
            current_price = adjusted_metrics[ticker]["current_price"]
            monto_teorico = total_value * peso
            target_shares = int(monto_teorico // current_price)
            
            current_shares = holdings.get(ticker, {}).get("shares", 0)
            
            if target_shares > current_shares:
                # Calculate maximum buyable shares within cash constraints
                shares_to_buy = target_shares - current_shares
                cost = shares_to_buy * current_price
                fee = cost * costo_corretaje
                total_cost = cost + fee
                
                if total_cost > cash_after_buys:
                    # Scale down buy
                    shares_to_buy = int(cash_after_buys // (current_price * (1.0 + costo_corretaje)))
                    cost = shares_to_buy * current_price
                    fee = cost * costo_corretaje
                    total_cost = cost + fee
                    
                if shares_to_buy > 0:
                    cash_after_buys -= total_cost
                    
                    # Update cost basis
                    old_buy_price = holdings.get(ticker, {}).get("buy_price", 0.0)
                    new_buy_price = ((current_shares * old_buy_price) + (shares_to_buy * current_price)) / (current_shares + shares_to_buy)
                    
                    note = f"V3 Dynamic Rebalance (Target Weight: {peso:.1%}, DCS: {adjusted_metrics[ticker]['dcs_adjusted']:.2f})"
                    rebalancing_trades.append({
                        "ticker": ticker,
                        "action": "BUY",
                        "shares": shares_to_buy,
                        "price": current_price,
                        "fee": fee,
                        "net_cash": -total_cost,
                        "note": note
                    })
                    print(f"  +-- [BUY] {ticker}: {shares_to_buy} shares @ {current_price:.2f} (Total Cost: {total_cost:,.2f} MXN)")
                    
                    new_holdings_dict[ticker] = {
                        "ticker": ticker,
                        "shares": current_shares + shares_to_buy,
                        "buy_price": round(new_buy_price, 2),
                        "last_price": current_price,
                        "target_weight": peso,
                        "dcs": adjusted_metrics[ticker]["dcs_adjusted"],
                        "garch_vol": adjusted_metrics[ticker]["garch_vol_adjusted"],
                        "hmm_state": adjusted_metrics[ticker]["hmm_state"],
                        "vol_relative": adjusted_metrics[ticker]["relative_vol"]
                    }
                elif current_shares > 0:
                    # Fallback to keep existing shares if we can't buy any more
                    new_holdings_dict[ticker] = {
                        "ticker": ticker,
                        "shares": current_shares,
                        "buy_price": holdings[ticker]["buy_price"],
                        "last_price": current_price,
                        "target_weight": peso,
                        "dcs": adjusted_metrics[ticker]["dcs_adjusted"],
                        "garch_vol": adjusted_metrics[ticker]["garch_vol_adjusted"],
                        "hmm_state": adjusted_metrics[ticker]["hmm_state"],
                        "vol_relative": adjusted_metrics[ticker]["relative_vol"]
                    }
                    
        # Update portfolio object
        updated_portfolio = {
            "total_capital": total_capital,
            "cash_balance": round(cash_after_buys, 2),
            "holdings": list(new_holdings_dict.values()),
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 4. Generate Markdown Execution Report
        report = []
        report.append("# MEXICAN QUANTITATIVE REPORT (V3)")
        report.append(f"**Execution Date:** {execution_date} | **System Version:** Hedge Fund Method V3\n")
        
        report.append("## 1. Top Quantitative Signals (HMM + GARCH)")
        report.append("| Ticker | DCS v2 | GARCH Vol | Relative Vol | HMM State | Target Weight | Price |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
        
        # Sort tickers by DCS adjusted descending
        sorted_tickers = sorted(adjusted_metrics.keys(), key=lambda x: adjusted_metrics[x]["dcs_adjusted"], reverse=True)
        for t in sorted_tickers:
            met = adjusted_metrics[t]
            state_str = "Bull (1)" if met["hmm_state"] == 1 else ("Bear (-1)" if met["hmm_state"] == -1 else "Sideways (0)")
            weight_str = f"{pesos_asignados[t]:.1%}"
            report.append(f"| {t} | {met['dcs_adjusted']:.4f} | {met['garch_vol_adjusted']:.4f} | {met['relative_vol']:.2f} | {state_str} | {weight_str} | {met['current_price']:.2f} |")
            
        report.append("\n## 2. Macro Catalyst Adjustments")
        for t in sorted_tickers:
            met = adjusted_metrics[t]
            if met["wacc_adjustment"] != 0.0 or met["growth_adjustment"] != 0.0:
                report.append(f"* **{t}**: {met['macro_description']} Adjusted signal strength by {met['growth_adjustment']*100:+.1f}%. Adjusted volatility by {met['wacc_adjustment']*500:+.1f}%.")
                
        report.append("\n## 3. Discarded Assets (Signal or Volume Suppressed)")
        discarded_assets = [t for t in sorted_tickers if pesos_asignados[t] == 0.0]
        if discarded_assets:
            report.append("| Ticker | DCS v2 Adjusted | Relative Vol | Reason |")
            report.append("| :--- | :---: | :---: | :--- |")
            for t in discarded_assets:
                met = adjusted_metrics[t]
                reasons = []
                if met["dcs_adjusted"] < umbral_histeresis_entrada:
                    reasons.append(f"DCS below entry threshold ({met['dcs_adjusted']:.2f} < {umbral_histeresis_entrada:.2f})")
                if met["relative_vol"] < umbral_vr:
                    reasons.append(f"Relative volume below threshold ({met['relative_vol']:.2f} < {umbral_vr:.2f})")
                report.append(f"| {t} | {met['dcs_adjusted']:.4f} | {met['relative_vol']:.2f} | {', '.join(reasons)} |")
        else:
            report.append("*No assets were discarded this run.*")
            
        report.append("\n## 4. Rebalancing Trade Blotter")
        if rebalancing_trades:
            report.append("| Ticker | Action | Shares | Execution Price | Fee Paid | Net Capital Impact | Note |")
            report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
            total_fees = 0.0
            for r in rebalancing_trades:
                total_fees += r["fee"]
                cap_impact = f"{r['net_cash']:+,.2f} MXN"
                report.append(f"| {r['ticker']} | {r['action']} | {r['shares']:,} | ${r['price']:.2f} | ${r['fee']:.2f} | {cap_impact} | {r['note']} |")
            report.append(f"\n* **Total Transaction Fees Paid**: ${total_fees:,.2f} MXN (0.29% flat rate)")
        else:
            report.append("*No trades required. Portfolio holdings match optimal target allocations.*")
            
        # Capital Reconciliation
        invested_capital = sum(h["shares"] * h["last_price"] for h in updated_portfolio["holdings"])
        eff_ratio = invested_capital / total_value
        report.append(f"\n## 5. Active Cash Routing & Capital Allocation")
        report.append(f"* **Total Capital Value**: ${total_value:,.2f} MXN")
        report.append(f"* **Total Invested in Equities**: ${invested_capital:,.2f} MXN ({eff_ratio:.2%})")
        report.append(f"* **Bondia Cash Routing Reserves (11% APR)**: ${cash_after_buys:,.2f} MXN ({1.0 - eff_ratio:.2%})")
        report.append(f"* **Expected Nightly Yield on Cash**: ${cash_after_buys * (0.11 / 252):,.4f} MXN")
        
        final_markdown = "\n".join(report)
        
        # Return the trade blotter so callers log EXACTLY the executed trades
        # (with fees) instead of re-deriving them by diffing holdings.
        return updated_portfolio, final_markdown, rebalancing_trades
