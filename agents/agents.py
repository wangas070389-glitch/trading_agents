import os
import json
import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from arch import arch_model
from skills.dcf_valuation_engine import calculate_cost_of_equity, calculate_wacc, calculate_dcf_intrinsic_value
from connectors.mock_data_connector import get_filing_data

_mbono_cache = None
_us_yield_cache = None

def get_mbono_yield_series():
    global _mbono_cache
    if _mbono_cache is not None:
        return _mbono_cache
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IRLTLT01MXM156N"
        df = pd.read_csv(url, parse_dates=['DATE'], index_col='DATE')
        # Clean any missing indicators
        df = df[df['IRLTLT01MXM156N'] != '.']
        _mbono_cache = pd.to_numeric(df['IRLTLT01MXM156N']) / 100.0
    except Exception as e:
        print(f"Error downloading Mbono yield from FRED: {e}. Falling back to default 0.095.")
        dates = pd.date_range("2020-01-01", "2027-01-01", freq="ME")
        _mbono_cache = pd.Series(0.095, index=dates)
    return _mbono_cache

def get_mbono_yield_at(date_val) -> float:
    series = get_mbono_yield_series()
    try:
        dt = pd.to_datetime(date_val)
        past_dates = series.index[series.index <= dt]
        if len(past_dates) > 0:
            val = series.loc[past_dates[-1]]
            if not np.isnan(val):
                return float(val)
        return float(series.iloc[-1])
    except Exception:
        return 0.095

def get_us_yield_series():
    global _us_yield_cache
    if _us_yield_cache is not None:
        return _us_yield_cache
    try:
        tnx = yf.Ticker("^TNX").history(period="5y")
        tnx.index = tnx.index.tz_localize(None)
        _us_yield_cache = tnx["Close"] / 100.0
    except Exception as e:
        print(f"Error downloading US yield from yfinance: {e}. Falling back to default 0.04.")
        dates = pd.date_range("2020-01-01", "2027-01-01", freq="D")
        _us_yield_cache = pd.Series(0.04, index=dates)
    return _us_yield_cache

def get_us_yield_at(date_val) -> float:
    series = get_us_yield_series()
    try:
        dt = pd.to_datetime(date_val)
        past_dates = series.index[series.index <= dt]
        if len(past_dates) > 0:
            val = series.loc[past_dates[-1]]
            if not np.isnan(val):
                return float(val)
        return float(series.iloc[-1])
    except Exception:
        return 0.04


class FundamentalScreener:
    """
    Agent 1: Runs the quantitative V3 model on historical prices and volumes.
    Computes daily returns, standardizes returns via GARCH(1,1), fits a dynamic multi-stage DCF Model
    using sovereign risk yields (Mbonos) and exchange rate sensitivities.
    """
    def __init__(self):
        self.system_prompt = (
            "SYSTEM PROMPT: You are the Quantitative Screener Agent (V3). Your objective is to run "
            "advanced mathematical models (GARCH(1,1) and multi-stage DCF Intrinsic Value) "
            "to extract volatility and valuation signals (DCS) for each BMV stock relative to global macro drivers."
        )

    def calcular_retornos_estandarizados_garch(self, precios):
        # Calculate daily log returns
        retornos = np.log(precios / np.roll(precios, 1))
        retornos[0] = 0.0
        
        # Fit GARCH(1,1) model
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

    def screen(self, universe_data: dict, execution_date: str = None) -> dict:
        print(f"\n[Agent 1: Quantitative Screener] Screening {len(universe_data)} assets in the universe...")
        
        if execution_date is None:
            execution_date = datetime.date.today().strftime("%Y-%m-%d")
            
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
                exogenous = np.array(data["exogenous"])
                
                # Clean non-positive or non-finite prices to avoid log return NaN/inf
                valid_mask = (precios > 0) & np.isfinite(precios)
                if np.sum(valid_mask) < 20:
                    print(f"  |-- {ticker}: Skipping (insufficient positive price history: {np.sum(valid_mask)} days)")
                    continue
                precios = precios[valid_mask]
                volumenes = volumenes[valid_mask]
                exogenous = exogenous[valid_mask]
                
                # 1. GARCH Modeling
                ret, ret_est, vol_cond = self.calcular_retornos_estandarizados_garch(precios)
                garch_vol_final = vol_cond[-1]
                
                # 2. Estimate SPY and USD/MXN beta over a 252-day trailing window
                ret_len = len(ret)
                lb = min(ret_len, 252)
                ret_slice = ret[-lb:]
                spy_ret = exogenous[-lb:, 0]
                usdmxn_ret = exogenous[-lb:, 1]
                
                cov_spy = np.cov(ret_slice[1:], spy_ret[1:])
                beta_spy = cov_spy[0, 1] / cov_spy[1, 1] if cov_spy[1, 1] > 1e-8 else 1.0
                
                cov_fx = np.cov(ret_slice[1:], usdmxn_ret[1:])
                beta_fx = cov_fx[0, 1] / cov_fx[1, 1] if cov_fx[1, 1] > 1e-8 else 0.0
                
                usd_mxn_vol = np.std(usdmxn_ret[-20:])
                usd_mxn_ret_recent = np.sum(usdmxn_ret[-20:])
                
                # 3. Dynamic DCF Valuation
                current_price = precios[-1]
                if not (np.isfinite(current_price) and current_price > 0):
                    print(f"  +-- [SKIP] {ticker}: sin precio valido (mercado cerrado / feed vacio)")
                    continue
                
                if "raw_dcf_inputs" in data:
                    # Blind pipeline support
                    raw_dcf = data["raw_dcf_inputs"]
                    tax_rate = raw_dcf.get("tax_rate", 0.30)
                    cost_of_debt = raw_dcf.get("cost_of_debt", 0.08)
                    total_debt = raw_dcf["total_debt"]
                    shares_outstanding = raw_dcf["shares_outstanding"]
                    base_fcff = raw_dcf["base_fcff"]
                    cash_and_equivalents = raw_dcf["cash_and_equivalents"]
                    growth_rate_stage1 = raw_dcf["growth_rate_stage1"]
                    total_assets = raw_dcf.get("total_assets", 1.0)
                    total_liabilities = raw_dcf.get("total_liabilities", 0.0)
                else:
                    # Normal pipeline support
                    lookup_ticker = ticker.split(".")[0]
                    filing = get_filing_data(lookup_ticker)
                    tax_rate = filing["tax_rate"]
                    cost_of_debt = filing["cost_of_debt"]
                    total_debt = filing["total_debt"]
                    shares_outstanding = filing["shares_outstanding"]
                    base_fcff = filing["base_fcff"]
                    cash_and_equivalents = filing["cash_and_equivalents"]
                    growth_rate_stage1 = filing["growth_rate_stage1"]
                    total_assets = filing["total_assets"]
                    total_liabilities = filing["total_liabilities"]
                    
                # Dynamic interest rates and sovereign spread
                us_yield = get_us_yield_at(execution_date)
                mbono_yield = get_mbono_yield_at(execution_date)
                sovereign_risk_premium = max(0.0, mbono_yield - us_yield)
                
                # Leverage risk adjustment
                equity_val = total_assets - total_liabilities
                if equity_val > 1e-4:
                    debt_to_equity = total_debt / equity_val
                    leverage_premium = max(0.0, (debt_to_equity - 1.0) * 0.015)
                else:
                    leverage_premium = 0.05  # high penalty for insolvent/negative equity
                
                cost_of_equity = calculate_cost_of_equity(
                    risk_free_rate=us_yield,
                    beta=beta_spy,
                    equity_risk_premium=0.055,
                    sovereign_risk_premium=sovereign_risk_premium + leverage_premium
                )
                
                wacc = calculate_wacc(
                    cost_of_equity=cost_of_equity,
                    cost_of_debt=cost_of_debt,
                    total_debt=total_debt,
                    market_cap=current_price * shares_outstanding,
                    tax_rate=tax_rate
                )
                
                dcf_results = calculate_dcf_intrinsic_value(
                    current_price=current_price,
                    shares_outstanding=shares_outstanding,
                    base_fcff=base_fcff,
                    wacc=wacc,
                    total_debt=total_debt,
                    cash_and_equivalents=cash_and_equivalents,
                    growth_rate_stage1=growth_rate_stage1,
                    terminal_growth=min(0.03, growth_rate_stage1 * 0.6)
                )
                
                margin_of_safety = dcf_results["margin_of_safety"]
                # Clip to [-1.0, 1.0] for DCS compatibility
                dcs = float(np.clip(margin_of_safety, -1.0, 1.0))
                
                # Map conviction to state: 1 (Bull/Buy), -1 (Bear/Sell), 0 (Sideways/Neutral)
                current_state = 1 if dcs >= 0.25 else (-1 if dcs <= -0.10 else 0)
                
                # 4. Volume Confirmation (Relative Volume)
                vr = volumenes[-1] / np.mean(volumenes[-20:])
                
                quantitative_results[ticker] = {
                    "dcs": dcs,
                    "garch_vol": float(garch_vol_final),
                    "relative_vol": float(vr),
                    "hmm_state": int(current_state),
                    "current_price": float(current_price),
                    "spy_hmm_state": spy_hmm_state,
                    "beta_fx": float(beta_fx),
                    "beta_spy": float(beta_spy),
                    "usd_mxn_vol": float(usd_mxn_vol),
                    "usd_mxn_ret_recent": float(usd_mxn_ret_recent)
                }
                
                print(f"  +-- {ticker}: DCS={dcs:.4f} | VR={vr:.2f} | Vol={garch_vol_final:.4f} | Conviction State={current_state}")
                
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
            "quantitative screener outputs (DCS and GARCH Volatility) based on dynamic currency and sovereign rate sensitivities."
        )

    def stress_test(self, quantitative_metrics: dict, ticker_map: dict) -> dict:
        print(f"\n[Agent 2: Macro/Sovereign Risk Analyst] Refining signals with dynamic currency and rate sensitivities...")
        
        adjusted_metrics = {}
        for ticker, metrics in quantitative_metrics.items():
            garch_vol = metrics["garch_vol"]
            dcs = metrics["dcs"]
            beta_fx = metrics.get("beta_fx", 0.0)
            usd_mxn_vol = metrics.get("usd_mxn_vol", 0.01)
            usd_mxn_ret_recent = metrics.get("usd_mxn_ret_recent", 0.0)
            
            # Dynamic adjustments based on USD/MXN beta and volatility
            vol_penalty = abs(beta_fx) * usd_mxn_vol * 2.0
            adjusted_vol = garch_vol * (1.0 + vol_penalty)
            
            dcs_adjustment = beta_fx * usd_mxn_ret_recent * 5.0
            adjusted_dcs = np.clip(dcs + dcs_adjustment, -1.0, 1.0)
            
            description = (
                f"Dynamic FX Sensitivity: beta_fx={beta_fx:.2f}. "
                f"Recent USD/MXN ret={usd_mxn_ret_recent*100:+.2f}%, "
                f"vol={usd_mxn_vol*100:.2f}%. "
                f"Vol penalization: {vol_penalty*100:+.1f}%. "
                f"DCS adjustment: {dcs_adjustment*100:+.1f}%."
            )
            
            adjusted_metrics[ticker] = {
                **metrics,
                "garch_vol_adjusted": float(adjusted_vol),
                "dcs_adjusted": float(adjusted_dcs),
                "macro_description": description,
                "wacc_adjustment": float(vol_penalty / 5.0),  # Backwards compatibility translation
                "growth_adjustment": float(dcs_adjustment)
            }
            
            if vol_penalty != 0.0 or dcs_adjustment != 0.0:
                print(f"  |-- {ticker}: Adjusted DCS {dcs:.4f} -> {adjusted_dcs:.4f} | Vol {garch_vol:.4f} -> {adjusted_vol:.4f} ({description})")
                
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
                  learning_context: dict = None, universe_prices_dict: dict = None) -> tuple[dict, str, list]:
        print(f"\n[Agent 3: Portfolio Reconciler] Starting portfolio reconciliation and optimization...")

        # Adaptive learning context (all optional, safe defaults = old behavior)
        ctx = learning_context or {}
        umbral_histeresis_entrada = ctx.get("dcs_threshold", 0.25)
        umbral_vr = ctx.get("vr_threshold", 1.2)
        confidence = ctx.get("confidence", {})          # ticker -> multiplier
        exposure_scalar = ctx.get("exposure_scalar", 1.0)
        normalize_weights = ctx.get("normalize_weights", False)
        min_fx_scalar = ctx.get("min_fx_scalar", 0.4)
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
            # Dynamic exposure scaling based on USD/MXN volatility
            first_ticker = activos_elegibles[0]
            usd_mxn_vol = adjusted_metrics[first_ticker].get("usd_mxn_vol", 0.005)
            fx_vol_scalar = max(min_fx_scalar, 1.0 - max(0.0, (usd_mxn_vol - 0.005) / 0.005))
            if fx_vol_scalar < 1.0:
                print(f"  |-- [Volatility Governor] USD/MXN volatility is elevated ({usd_mxn_vol*100:.2f}%). Scaling gross exposure by {fx_vol_scalar:.1%}")

            if normalize_weights:
                # Raw weights: inverse-volatility, optionally normalized to sum to 1.0 (fully invested)
                raw_weights = {}
                for t in activos_elegibles:
                    raw_weights[t] = (inv_vol[t] / suma_inv_vol) * exposure_scalar * fx_vol_scalar
                
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
                            
                for t in activos_elegibles:
                    pesos_asignados[t] = final_weights[t]
            else:
                # SLSQP Weight Optimization
                w0_list = []
                for t in activos_elegibles:
                    mult = confidence.get(t, 1.0)
                    if mult != 1.0:
                        print(f"  |-- [Learned Confidence] {t}: weight factor x{mult:.2f} (historical bucket expectancy)")
                    w0_val = (inv_vol[t] / suma_inv_vol) * adjusted_metrics[t]["dcs_adjusted"] * mult * exposure_scalar * fx_vol_scalar
                    w0_list.append(w0_val)
                w0 = np.array(w0_list)
                
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
                dcs_arr = np.array([adjusted_metrics[t]["dcs_adjusted"] * confidence.get(t, 1.0) for t in activos_elegibles])
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
        
        # Define structural hysteresis deadband (rebalancing tolerance)
        REBALANCE_TOLERANCE = ctx.get("dead_zone_threshold", 0.05)
        
        # Adjust target weights using hysteresis BEFORE executing trade calculations
        for ticker in list(pesos_asignados.keys()):
            current_price = adjusted_metrics[ticker]["current_price"]
            current_shares = holdings.get(ticker, {}).get("shares", 0)
            current_weight = (current_shares * current_price) / total_value if total_value > 0 else 0.0
            target_weight = pesos_asignados[ticker]
            
            # If the stock is already held, target weight is positive, and the change in weight is within tolerance, suppress rebalancing
            if current_shares > 0 and target_weight > 0.0 and abs(target_weight - current_weight) < REBALANCE_TOLERANCE:
                pesos_asignados[ticker] = current_weight
        
        # Target shares and rebalancing trade vector
        rebalancing_trades = []
        costo_corretaje = 0.0029 # 0.29% fee
        
        # Dead-zone threshold to prevent excessive fee churn
        DEAD_ZONE_THRESHOLD = REBALANCE_TOLERANCE
        
        # First Phase: Execute Sells (frees up cash, proceeds go to T+1 unsettled cash)
        new_holdings_dict = {}
        cash_available_for_buys = cash
        unsettled_cash_from_sells = 0.0
        
        # Handle tickers held but missing from current adjusted metrics
        for ticker, h in holdings.items():
            if ticker not in adjusted_metrics:
                print(f"  +-- [WARN] {ticker} held but absent from today's metrics. Carrying position at last price {h['last_price']:.2f}")
                new_holdings_dict[ticker] = {**h, "target_weight": h.get("target_weight", 0.0)}

        for ticker, peso in pesos_asignados.items():
            current_price = adjusted_metrics[ticker]["current_price"]
            monto_teorico = total_value * peso
            target_shares = int(monto_teorico // current_price)
            current_shares = holdings.get(ticker, {}).get("shares", 0)
            
            if current_shares > target_shares:
                shares_to_sell = current_shares - target_shares
                revenue = shares_to_sell * current_price
                fee = revenue * costo_corretaje
                net_revenue = revenue - fee
                unsettled_cash_from_sells += net_revenue
                
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
                        "buy_price": holdings[ticker]["buy_price"],
                        "last_price": current_price,
                        "target_weight": peso,
                        "dcs": adjusted_metrics[ticker]["dcs_adjusted"],
                        "garch_vol": adjusted_metrics[ticker]["garch_vol_adjusted"],
                        "hmm_state": adjusted_metrics[ticker]["hmm_state"],
                        "vol_relative": adjusted_metrics[ticker]["relative_vol"]
                    }
            elif current_shares > 0 and current_shares == target_shares:
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
                
        # Second Phase: Execute Buys (restrict to settled cash balance)
        cash_after_buys = cash_available_for_buys
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
                shares_to_buy = target_shares - current_shares
                cost = shares_to_buy * current_price
                fee = cost * costo_corretaje
                total_cost = cost + fee
                
                if total_cost > cash_after_buys:
                    shares_to_buy = int(cash_after_buys // (current_price * (1.0 + costo_corretaje)))
                    cost = shares_to_buy * current_price
                    fee = cost * costo_corretaje
                    total_cost = cost + fee
                    
                if shares_to_buy > 0:
                    cash_after_buys -= total_cost
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
                    
        total_cash_balance = cash_after_buys + unsettled_cash_from_sells
        updated_portfolio = {
            "total_capital": total_capital,
            "cash_balance": round(total_cash_balance, 2),
            "settled_cash": round(cash_after_buys, 2),
            "unsettled_cash": round(unsettled_cash_from_sells, 2),
            "holdings": list(new_holdings_dict.values()),
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 4. Generate Markdown Execution Report
        report = []
        report.append("# MEXICAN QUANTITATIVE REPORT (V3)")
        report.append(f"**Execution Date:** {execution_date} | **System Version:** Hedge Fund Method V3\n")
        
        report.append("## 1. Top Quantitative Signals (DCF + GARCH)")
        report.append("| Ticker | DCS Adjusted | GARCH Vol | Relative Vol | Conviction State | Target Weight | Price |")
        report.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
        
        sorted_tickers = sorted(adjusted_metrics.keys(), key=lambda x: adjusted_metrics[x]["dcs_adjusted"], reverse=True)
        for t in sorted_tickers:
            met = adjusted_metrics[t]
            state_str = "Bull (1)" if met["hmm_state"] == 1 else ("Bear (-1)" if met["hmm_state"] == -1 else "Sideways (0)")
            weight_str = f"{pesos_asignados.get(t, 0.0):.1%}"
            report.append(f"| {t} | {met['dcs_adjusted']:.4f} | {met['garch_vol_adjusted']:.4f} | {met['relative_vol']:.2f} | {state_str} | {weight_str} | {met['current_price']:.2f} |")
            
        report.append("\n## 2. Macro Catalyst Adjustments")
        for t in sorted_tickers:
            met = adjusted_metrics[t]
            if met["wacc_adjustment"] != 0.0 or met["growth_adjustment"] != 0.0:
                report.append(f"* **{t}**: {met['macro_description']}")
                
        report.append("\n## 3. Discarded Assets (Signal or Volume Suppressed)")
        discarded_assets = [t for t in sorted_tickers if pesos_asignados.get(t, 0.0) == 0.0]
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
            
        invested_capital = sum(h["shares"] * h["last_price"] for h in updated_portfolio["holdings"])
        eff_ratio = invested_capital / total_value
        report.append(f"\n## 5. Active Cash Routing & Capital Allocation")
        report.append(f"* **Total Capital Value**: ${total_value:,.2f} MXN")
        report.append(f"* **Total Invested in Equities**: ${invested_capital:,.2f} MXN ({eff_ratio:.2%})")
        report.append(f"* **Settled Cash (Available Now)**: ${cash_after_buys:,.2f} MXN")
        report.append(f"* **Unsettled Cash (T+1 from today's sells)**: ${unsettled_cash_from_sells:,.2f} MXN")
        report.append(f"* **Total Cash Reserves (Bondia, 11% APR)**: ${total_cash_balance:,.2f} MXN ({1.0 - eff_ratio:.2%})")
        report.append(f"* **Expected Nightly Yield on Cash**: ${total_cash_balance * (0.11 / 252):,.4f} MXN")
        
        final_markdown = "\n".join(report)
        return updated_portfolio, final_markdown, rebalancing_trades
