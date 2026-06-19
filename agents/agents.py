import os
import json
import datetime
import numpy as np
import pandas as pd
from hmmlearn import hmm
from arch import arch_model

# Import V4 Quantitative Modules
from skills.nlp_sentiment import NLPSentimentEngine
from skills.statistical_arbitrage import StatisticalArbitrageEngine
from skills.rl_execution_agent import optimize_order_execution


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
        
        # Train HMM on SPY returns once to determine global market regime
        spy_hmm_state = 0 # Default to Sideways
        try:
            if len(universe_data) > 0:
                first_asset_data = next(iter(universe_data.values()))
                exog = np.array(first_asset_data["exogenous"])
                # SPY daily return is the first column in exogenous regressors
                spy_rets = exog[:, 0]
                if len(spy_rets) >= 20:
                    obs_spy = spy_rets.reshape(-1, 1)
                    model_spy = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
                    model_spy.fit(obs_spy)
                    spy_states = model_spy.predict(obs_spy)
                    
                    spy_means = model_spy.means_[:, 0]
                    bear_idx = np.argmin(spy_means)
                    bull_idx = np.argmax(spy_means)
                    sideways_idx = [idx for idx in range(3) if idx not in (bear_idx, bull_idx)][0]
                    
                    state_map = {bear_idx: -1, bull_idx: 1, sideways_idx: 0}
                    spy_hmm_state = int(state_map[spy_states[-1]])
                    print(f"  |-- [SPY Market Regime] Fitted HMM on SPY. Current state: {spy_hmm_state} "
                          f"(Bull/Sideways/Bear: {bull_idx}/{sideways_idx}/{bear_idx})")
        except Exception as spy_err:
            print(f"  |-- [WARN] Failed to fit HMM on SPY: {spy_err}")
            
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
                    "current_price": float(precios[-1]),
                    "spy_hmm_state": spy_hmm_state
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
        print(f"\n[Agent 2: Macro/Sovereign Risk Analyst] Refining signals with qualitative risk factors and NLP Sentiment...")
        
        # Instantiate NLP Sentiment Engine and fetch adjustments
        nlp_engine = NLPSentimentEngine()
        tickers = list(quantitative_metrics.keys())
        nlp_adjustments = nlp_engine.get_black_litterman_adjustments(tickers)
        
        adjusted_metrics = {}
        for ticker, metrics in quantitative_metrics.items():
            lookup_ticker = ticker.split(".")[0]
            
            risk_data = MACRO_RISK_REGISTRY.get(
                lookup_ticker, 
                {"description": "No macro adjustments.", "wacc_adjustment": 0.0, "growth_adjustment": 0.0}
            )
            
            zg_t = nlp_adjustments.get(ticker, 0.0)
            
            garch_vol = metrics["garch_vol"]
            dcs = metrics["dcs"]
            
            # NLP Sentiment modifies the WACC (risk) and Growth multipliers
            # Positive ZG_t sentiment reduces risk and increases growth signal
            nlp_wacc_mod = -0.005 * zg_t
            nlp_growth_mod = 0.05 * zg_t
            
            adjusted_vol = garch_vol * (1.0 + (risk_data["wacc_adjustment"] + nlp_wacc_mod) * 5.0)
            adjusted_dcs = np.clip(dcs + risk_data["growth_adjustment"] + nlp_growth_mod, -1.0, 1.0)
            
            adjusted_metrics[ticker] = {
                **metrics,
                "garch_vol_adjusted": float(adjusted_vol),
                "dcs_adjusted": float(adjusted_dcs),
                "macro_description": risk_data["description"],
                "wacc_adjustment": risk_data["wacc_adjustment"],
                "growth_adjustment": risk_data["growth_adjustment"],
                "zg_t": float(zg_t)
            }
            
            if risk_data["wacc_adjustment"] != 0.0 or risk_data["growth_adjustment"] != 0.0 or zg_t != 0.0:
                print(f"  |-- {ticker}: Adjusted DCS {dcs:.4f} -> {adjusted_dcs:.4f} | Vol {garch_vol:.4f} -> {adjusted_vol:.4f} (zg_t={zg_t:+.2f})")
                
        return adjusted_metrics


class PortfolioReconciler:
    """
    Agent 3: Rebalances the portfolio based on Black-Litterman weights and V4 optimizations.
    - Filters by DCS >= 0.25 and VR >= 1.2, dynamically adjusted by learning context with exit hysteresis.
    - Performs inverse-volatility weighting scaled by the DCS strength and learned confidence levels.
    - Integrates Engle-Granger Cointegration & Regime Arbitrage on historical price graphs.
    - Enforces a hard 20% concentration limit (reduced from 40% to improve diversification).
    - Applies a 5% Dead-Zone threshold to avoid fee churn on marginal target weight deviations.
    - Invokes DQN Reinforcement Learning agent to route order books and minimize trade slippage.
    - Deducts execution friction fees and interest earned on deferred cash.
    - Automatically routes cash to Bondia overnight sweeps.
    """
    def __init__(self):
        self.system_prompt = (
            "SYSTEM PROMPT: You are the Portfolio Reconciler Agent (V4). Your objective is to run "
            "Black-Litterman optimization, apply dynamic Cointegration Regime Arbitrage offsets, "
            "optimize execution routing via DQN RL agent, and draft the production execution report."
        )

    def reconcile(self, adjusted_metrics: dict, portfolio: dict, execution_date: str,
                  learning_context: dict = None, universe_prices_dict: dict = None) -> tuple[dict, str, list]:
        print(f"\n[Agent 3: Portfolio Reconciler] Starting unified portfolio reconciliation and optimization...")

        # V3 Adaptive learning context (all optional, safe defaults)
        ctx = learning_context or {}
        umbral_histeresis_entrada = ctx.get("dcs_threshold", 0.25)
        umbral_vr = ctx.get("vr_threshold", 1.2)
        confidence = ctx.get("confidence", {})          # ticker -> multiplier
        exposure_scalar = ctx.get("exposure_scalar", 1.0)
        
        if exposure_scalar < 1.0:
            print(f"  |-- [Drawdown Governor] Gross exposure scaled to {exposure_scalar:.0%} "
                  f"(strategy drawdown brake active).")

        # Extract SPY HMM state from adjusted_metrics to apply the Broad Market Overlay
        spy_state = 0
        for met in adjusted_metrics.values():
            if "spy_hmm_state" in met:
                spy_state = met["spy_hmm_state"]
                break

        # 1a. Broad Market HMM Overlay (Dynamic Exposure Capping)
        if spy_state == 1:
            max_equity_exposure = 0.95
            regime_name = "BULL"
        elif spy_state == -1:
            max_equity_exposure = 0.10
            regime_name = "BEAR"
        else:
            max_equity_exposure = 0.50
            regime_name = "SIDEWAYS"
        print(f"  |-- [SPY HMM Regime Overlay] Regime: {regime_name} | Max Equity Exposure capped at {max_equity_exposure:.0%}")

        # 1b. Adaptive Screener Gates (Dynamic Percentile-based Thresholds)
        all_dcs = [met["dcs_adjusted"] for met in adjusted_metrics.values()]
        all_vr = [met["relative_vol"] for met in adjusted_metrics.values()]
        
        if len(all_dcs) > 0:
            adaptive_dcs_threshold = max(0.05, float(np.percentile(all_dcs, 30)))
        else:
            adaptive_dcs_threshold = umbral_histeresis_entrada
            
        if len(all_vr) > 0:
            adaptive_vr_threshold = max(0.90, float(np.percentile(all_vr, 30)))
        else:
            adaptive_vr_threshold = umbral_vr
            
        print(f"  |-- [Adaptive Screener Gates] Dynamic DCS Threshold: {adaptive_dcs_threshold:.4f} | Dynamic VR Threshold: {adaptive_vr_threshold:.2f}")

        # Determine active eligible assets based on adaptive percentile gates with exit hysteresis
        activos_elegibles = []
        currently_held = {h["ticker"] for h in portfolio.get("holdings", []) if h.get("shares", 0) > 0}
        max_posiciones = ctx.get("max_positions", 6)
        
        for t, met in adjusted_metrics.items():
            required_dcs = (adaptive_dcs_threshold - 0.05) if t in currently_held else adaptive_dcs_threshold
            if t in currently_held:
                # HOLD CONDITION: signal only. Relative volume is an entry confirmation.
                if met["dcs_adjusted"] >= required_dcs:
                    activos_elegibles.append(t)
            else:
                # ENTRY CONDITION: signal strength and volume confirmation.
                if met["dcs_adjusted"] >= required_dcs and met["relative_vol"] >= adaptive_vr_threshold:
                    activos_elegibles.append(t)
                    
        # TOP-N SELECTION: cap total positions at max_posiciones, prioritizing held positions.
        if len(activos_elegibles) > max_posiciones:
            held_eligible = [t for t in activos_elegibles if t in currently_held]
            new_eligible = sorted(
                (t for t in activos_elegibles if t not in currently_held),
                key=lambda t: adjusted_metrics[t]["dcs_adjusted"],
                reverse=True
            )
            slots_for_new = max(0, max_posiciones - len(held_eligible))
            activos_elegibles = held_eligible + new_eligible[:slots_for_new]
            print(f"  |-- [Top-N] Kept {len(held_eligible)} held + "
                  f"{min(slots_for_new, len(new_eligible))} new entries "
                  f"(cap {max_posiciones}).")

        # Sort eligible assets by DCS descending
        activos_elegibles = sorted(activos_elegibles, key=lambda t: adjusted_metrics[t]["dcs_adjusted"], reverse=True)
        print(f"  |-- Eligible assets for long positions: {activos_elegibles}")
        
        # 2. Black-Litterman Sizing with SLSQP and Turnover Penalties
        pesos_asignados = {}
        CONCENTRATION_CAP_HARD = ctx.get("concentration_cap", 0.20)
        
        # Pre-calculate portfolio value for optimization sizing
        cash = portfolio["cash_balance"]
        holdings_dict = {h["ticker"]: h for h in portfolio["holdings"]}
        holdings_value_opt = sum(h["shares"] * adjusted_metrics.get(t, {}).get("current_price", h["last_price"]) for t, h in holdings_dict.items())
        total_value = cash + holdings_value_opt

        if len(activos_elegibles) == 0:
            print("  |-- No assets met the eligibility thresholds. Portfolio will hold 100% Cash.")
            for t in adjusted_metrics:
                pesos_asignados[t] = 0.0
        else:
            from scipy.optimize import minimize
            
            n = len(activos_elegibles)
            
            # Initial guess: inverse-volatility weights
            inv_vol = {t: 1.0 / max(adjusted_metrics[t]["garch_vol_adjusted"], 1e-4) for t in activos_elegibles}
            suma_inv_vol = sum(inv_vol.values())
            w0 = np.array([(inv_vol[t] / suma_inv_vol) * adjusted_metrics[t]["dcs_adjusted"] * exposure_scalar for t in activos_elegibles])
            if ctx.get("sizing_profile") == "asymmetric":
                caps = [0.50, 0.30, 0.20]
                w0 = np.array([min(w0[idx], caps[idx] if idx < len(caps) else 0.0) for idx in range(n)])
            else:
                w0 = np.clip(w0, 0.0, CONCENTRATION_CAP_HARD)
            sum_w0 = sum(w0)
            if sum_w0 > max_equity_exposure:
                w0 = w0 * (max_equity_exposure / sum_w0)
                
            # Current weights for eligible assets
            w_curr = np.zeros(n)
            for i, t in enumerate(activos_elegibles):
                current_shares = holdings_dict.get(t, {}).get("shares", 0)
                current_price = adjusted_metrics[t]["current_price"]
                w_curr[i] = (current_shares * current_price) / total_value if total_value > 0 else 0.0
                
            # Objective: Maximize expected return minus turnover penalty
            dcs_arr = np.array([adjusted_metrics[t]["dcs_adjusted"] for t in activos_elegibles])
            lambda_penalty = 3.0  # Turnover penalty scaling factor
            fee_rate = 0.0029
            
            def objective(w):
                expected_return = np.sum(w * dcs_arr)
                turnover_cost = np.sum(np.abs(w - w_curr)) * fee_rate
                utility = expected_return - lambda_penalty * turnover_cost
                return -utility  # Minimize negative utility
                
            # Constraint: sum(w) <= max_equity_exposure
            cons = ({'type': 'ineq', 'fun': lambda w: max_equity_exposure - np.sum(w)})
            
            # Bounds: 0 <= w_i <= CONCENTRATION_CAP_HARD (or asymmetric caps)
            if ctx.get("sizing_profile") == "asymmetric":
                caps = [0.50, 0.30, 0.20]
                bounds = [(0.0, caps[i]) if i < len(caps) else (0.0, 0.0) for i in range(n)]
            else:
                bounds = [(0.0, CONCENTRATION_CAP_HARD) for _ in range(n)]
            
            # Optimize weights
            res = minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=cons)
            
            if res.success:
                opt_weights = res.x
                print("  |-- SLSQP Weight Optimization converged successfully.")
            else:
                opt_weights = w0
                print("  |-- [WARN] SLSQP optimization failed to converge. Falling back to initial inv-vol weights.")
                
            for i, t in enumerate(activos_elegibles):
                pesos_asignados[t] = float(opt_weights[i])
                
            for t in adjusted_metrics:
                if t not in pesos_asignados:
                    pesos_asignados[t] = 0.0
                
        # 3. Dynamic Cointegration & Regime Arbitrage Adjustments (V4 Upgrade)
        arbitrage_reports = []
        if universe_prices_dict:
            arb_engine = StatisticalArbitrageEngine()
            arb_engine.update_cointegration_graph(universe_prices_dict)
            active_regimes = {t: met["hmm_state"] for t, met in adjusted_metrics.items()}
            pesos_asignados, arbitrage_reports = arb_engine.apply_regime_arbitrage(pesos_asignados, active_regimes)

        # 3b. HARD POST-CONDITION: enforce concentration cap after ALL adjustments
        if ctx.get("sizing_profile") == "asymmetric":
            caps = {"TICKER_RANK_0": 0.50, "TICKER_RANK_1": 0.30, "TICKER_RANK_2": 0.20}
            # Sort active tickers by assigned weights descending
            sorted_assigned = sorted([t for t in pesos_asignados.keys() if pesos_asignados[t] > 0.0], key=lambda t: pesos_asignados[t], reverse=True)
            for idx, t in enumerate(sorted_assigned):
                cap_t = caps.get(f"TICKER_RANK_{idx}", 0.0)
                if pesos_asignados[t] > cap_t:
                    print(f"  |-- [CAP] {t} weight {pesos_asignados[t]:.1%} -> {cap_t:.0%} (asymmetric cap enforced)")
                    pesos_asignados[t] = cap_t
        else:
            CONCENTRATION_CAP_HARD = ctx.get("concentration_cap", 0.20)
            for t in list(pesos_asignados.keys()):
                if pesos_asignados[t] > CONCENTRATION_CAP_HARD:
                    print(f"  |-- [CAP] {t} weight {pesos_asignados[t]:.1%} -> {CONCENTRATION_CAP_HARD:.0%} (hard cap enforced)")
                    pesos_asignados[t] = CONCENTRATION_CAP_HARD

        # 4. Calculate portfolio value and execute trades
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
        total_slippage_savings = 0.0
        rl_traces = []
        
        # Dead-zone threshold to prevent excessive fee churn
        DEAD_ZONE_THRESHOLD = ctx.get("dead_zone_threshold", 0.05)
        
        # First Phase: Execute Sells (frees up cash)
        new_holdings_dict = {}
        cash_after_sells = cash

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
            
            # Rebalance dead-zone: skip if weight delta < 5% (except when liquidating)
            current_weight = (current_shares * current_price) / total_value if total_value > 0 else 0.0
            weight_delta = abs(peso - current_weight)
            if weight_delta < DEAD_ZONE_THRESHOLD and current_shares > 0 and peso > 0.0:
                new_holdings_dict[ticker] = {
                    "ticker": ticker,
                    "shares": current_shares,
                    "buy_price": holdings[ticker]["buy_price"],
                    "last_price": current_price,
                    "target_weight": peso,
                    "dcs": adjusted_metrics[ticker]["dcs_adjusted"],
                    "garch_vol": adjusted_metrics[ticker]["garch_vol_adjusted"],
                    "hmm_state": adjusted_metrics[ticker]["hmm_state"],
                    "vol_relative": adjusted_metrics[ticker]["relative_vol"],
                    "zg_t": adjusted_metrics[ticker].get("zg_t", 0.0)
                }
                print(f"  |-- [HOLD] {ticker}: weight delta {weight_delta:.1%} < {DEAD_ZONE_THRESHOLD:.0%} dead-zone. No trade.")
                continue
            
            if current_shares > target_shares:
                # Execute Sell
                shares_to_sell = current_shares - target_shares
                revenue = shares_to_sell * current_price
                
                # DQN Order Execution Routing Optimization
                est_spread = max(0.002, min(0.015, adjusted_metrics[ticker]["garch_vol_adjusted"] * 0.5))
                rl_results = optimize_order_execution(shares_to_sell, est_spread, market_volume_15m=shares_to_sell * 2.0)
                
                fee = rl_results["fees"]
                net_revenue = revenue - fee + rl_results["interest_earned"]
                cash_after_sells += net_revenue
                total_slippage_savings += rl_results["slippage_savings"]
                
                rl_traces.append(f"**{ticker} SELL (DQN Optimization)**:")
                for step_line in rl_results["trace"]:
                    rl_traces.append(f"  * {step_line}")
                
                note = f"V4 DQN Execution (Target Weight: {peso:.1%}, DCS: {adjusted_metrics[ticker]['dcs_adjusted']:.2f}, Saved: ${rl_results['slippage_savings']:.2f} MXN)"
                rebalancing_trades.append({
                    "ticker": ticker,
                    "action": "SELL",
                    "shares": shares_to_sell,
                    "price": current_price,
                    "fee": fee,
                    "net_cash": net_revenue,
                    "note": note
                })
                print(f"  +-- [SELL] {ticker}: {shares_to_sell} shares @ {current_price:.2f} (Net: +{net_revenue:,.2f} MXN, Saved: +{rl_results['slippage_savings']:.2f} MXN)")
                
                if target_shares > 0:
                    new_holdings_dict[ticker] = {
                        "ticker": ticker,
                        "shares": target_shares,
                        "buy_price": holdings[ticker]["buy_price"],
                        "last_price": current_price,
                        "target_weight": peso,
                        "dcs": adjusted_metrics[ticker]["dcs_adjusted"],
                        "garch_vol": adjusted_metrics[ticker]["garch_vol_adjusted"],
                        "hmm_state": adjusted_metrics[ticker]["hmm_state"],
                        "vol_relative": adjusted_metrics[ticker]["relative_vol"],
                        "zg_t": adjusted_metrics[ticker].get("zg_t", 0.0)
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
                    "vol_relative": adjusted_metrics[ticker]["relative_vol"],
                    "zg_t": adjusted_metrics[ticker].get("zg_t", 0.0)
                }
                
        # Second Phase: Execute Buys
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
            
            # Dead-zone check for buys
            current_weight = (current_shares * current_price) / total_value if total_value > 0 else 0.0
            weight_delta = abs(peso - current_weight)
            if weight_delta < DEAD_ZONE_THRESHOLD and current_shares > 0 and peso > 0.0:
                continue  # Already handled in first loop
            
            if target_shares > current_shares:
                # Calculate maximum buyable shares within cash constraints
                shares_to_buy = target_shares - current_shares
                cost = shares_to_buy * current_price
                fee = cost * 0.0029
                total_cost = cost + fee
                
                if total_cost > cash_after_buys:
                    shares_to_buy = int(cash_after_buys // (current_price * 1.0029))
                    
                if shares_to_buy > 0:
                    # DQN execution optimization
                    est_spread = max(0.002, min(0.015, adjusted_metrics[ticker]["garch_vol_adjusted"] * 0.5))
                    rl_results = optimize_order_execution(shares_to_buy, est_spread, market_volume_15m=shares_to_buy * 2.0)
                    
                    fee = rl_results["fees"]
                    dqn_cost = shares_to_buy * current_price + fee - rl_results["interest_earned"]
                    cash_after_buys -= dqn_cost
                    total_slippage_savings += rl_results["slippage_savings"]
                    
                    rl_traces.append(f"**{ticker} BUY (DQN Optimization)**:")
                    for step_line in rl_results["trace"]:
                        rl_traces.append(f"  * {step_line}")
                    
                    # Update cost basis
                    old_buy_price = holdings.get(ticker, {}).get("buy_price", 0.0)
                    new_buy_price = ((current_shares * old_buy_price) + (shares_to_buy * current_price)) / (current_shares + shares_to_buy)
                    
                    note = f"V4 DQN Execution (Target Weight: {peso:.1%}, DCS: {adjusted_metrics[ticker]['dcs_adjusted']:.2f}, Saved: ${rl_results['slippage_savings']:.2f} MXN)"
                    rebalancing_trades.append({
                        "ticker": ticker,
                        "action": "BUY",
                        "shares": shares_to_buy,
                        "price": current_price,
                        "fee": fee,
                        "net_cash": -dqn_cost,
                        "note": note
                    })
                    print(f"  +-- [BUY] {ticker}: {shares_to_buy} shares @ {current_price:.2f} (Total Cost: {dqn_cost:,.2f} MXN, Saved: +{rl_results['slippage_savings']:.2f} MXN)")
                    
                    new_holdings_dict[ticker] = {
                        "ticker": ticker,
                        "shares": current_shares + shares_to_buy,
                        "buy_price": round(new_buy_price, 2),
                        "last_price": current_price,
                        "target_weight": peso,
                        "dcs": adjusted_metrics[ticker]["dcs_adjusted"],
                        "garch_vol": adjusted_metrics[ticker]["garch_vol_adjusted"],
                        "hmm_state": adjusted_metrics[ticker]["hmm_state"],
                        "vol_relative": adjusted_metrics[ticker]["relative_vol"],
                        "zg_t": adjusted_metrics[ticker].get("zg_t", 0.0)
                    }
                elif current_shares > 0:
                    new_holdings_dict[ticker] = {
                        "ticker": ticker,
                        "shares": current_shares,
                        "buy_price": holdings[ticker]["buy_price"],
                        "last_price": current_price,
                        "target_weight": peso,
                        "dcs": adjusted_metrics[ticker]["dcs_adjusted"],
                        "garch_vol": adjusted_metrics[ticker]["garch_vol_adjusted"],
                        "hmm_state": adjusted_metrics[ticker]["hmm_state"],
                        "vol_relative": adjusted_metrics[ticker]["relative_vol"],
                        "zg_t": adjusted_metrics[ticker].get("zg_t", 0.0)
                    }
                    
        # Update portfolio object
        updated_portfolio = {
            "total_capital": total_capital,
            "cash_balance": round(cash_after_buys, 2),
            "holdings": list(new_holdings_dict.values()),
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "slippage_savings": round(total_slippage_savings, 2)
        }
        
        # 5. Generate Markdown V4 Execution Report
        report = []
        report.append("# QUANTITATIVE PLATFORM REPORT (V4)")
        report.append(f"**Execution Date:** {execution_date} | **System Version:** Alpha Generation V4\n")
        
        report.append("## 1. Top Quantitative Signals (HMM Regime + 2nd-Order Markov + GARCH)")
        report.append("| Ticker | DCS | ZG_t Sentiment | GARCH Vol | Relative Vol | HMM State | Target Weight | Price |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        
        sorted_tickers = sorted(adjusted_metrics.keys(), key=lambda x: adjusted_metrics[x]["dcs_adjusted"], reverse=True)
        for t in sorted_tickers:
            met = adjusted_metrics[t]
            state_str = "Bull (1)" if met["hmm_state"] == 1 else ("Bear (-1)" if met["hmm_state"] == -1 else "Sideways (0)")
            weight_str = f"{pesos_asignados[t]:.1%}"
            report.append(f"| {t} | {met['dcs_adjusted']:.4f} | {met['zg_t']:+.2f} | {met['garch_vol_adjusted']:.4f} | {met['relative_vol']:.2f} | {state_str} | {weight_str} | {met['current_price']:.2f} |")
            
        if arbitrage_reports:
            report.append("\n## 2. Statistical Cointegration Regime Arbitrage")
            for r_line in arbitrage_reports:
                report.append(f"* {r_line}")
                
        report.append("\n## 3. Macro Sentiment & Catalyst Overrides")
        for t in sorted_tickers:
            met = adjusted_metrics[t]
            if met["wacc_adjustment"] != 0.0 or met["growth_adjustment"] != 0.0 or met["zg_t"] != 0.0:
                report.append(f"* **{t}**: {met['macro_description']} Adjusted signal strength by {met['growth_adjustment']*100:+.1f}%. Adjusted volatility by {met['wacc_adjustment']*500:+.1f}%.")
                
        report.append("\n## 4. Discarded Assets (Signal or Volume Suppressed)")
        discarded_assets = [t for t in sorted_tickers if pesos_asignados[t] == 0.0]
        if discarded_assets:
            report.append("| Ticker | DCS Adjusted | Relative Vol | Reason |")
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
            
        report.append("\n## 5. Rebalancing Trade Blotter (DQN Optimized)")
        if rebalancing_trades:
            report.append("| Ticker | Action | Shares | Execution Price | Fee Paid | Net Capital Impact | Note |")
            report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
            total_fees = 0.0
            for r in rebalancing_trades:
                total_fees += r["fee"]
                cap_impact = f"{r['net_cash']:+,.2f} MXN"
                report.append(f"| {r['ticker']} | {r['action']} | {r['shares']:,} | ${r['price']:.2f} | ${r['fee']:.2f} | {cap_impact} | {r['note']} |")
            report.append(f"\n* **Total Transaction Fees Paid**: ${total_fees:,.2f} MXN")
            report.append(f"* **DQN Slippage Reduction Savings**: ${total_slippage_savings:,.2f} MXN")
        else:
            report.append("*No trades required. Portfolio holdings match optimal target allocations.*")
            
        if rl_traces:
            report.append("\n## 6. DQN Reinforcement Order Routing Traces")
            for trace_line in rl_traces:
                report.append(trace_line)
            
        # Capital Reconciliation
        invested_capital = sum(h["shares"] * h["last_price"] for h in updated_portfolio["holdings"])
        eff_ratio = invested_capital / total_value
        report.append(f"\n## 7. Active Cash Routing & Capital Allocation")
        report.append(f"* **Total Capital Value**: ${total_value:,.2f} MXN")
        report.append(f"* **Total Invested in Equities**: ${invested_capital:,.2f} MXN ({eff_ratio:.2%})")
        report.append(f"* **Bondia Cash Routing Reserves (11% APR)**: ${cash_after_buys:,.2f} MXN ({1.0 - eff_ratio:.2%})")
        report.append(f"* **Expected Nightly Yield on Cash**: ${cash_after_buys * (0.11 / 252):,.4f} MXN")
        
        final_markdown = "\n".join(report)
        return updated_portfolio, final_markdown, rebalancing_trades
